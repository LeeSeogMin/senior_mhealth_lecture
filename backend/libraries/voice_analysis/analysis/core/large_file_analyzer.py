"""
대용량 오디오 파일 분석 모듈
청킹과 스트리밍 방식으로 메모리 효율적인 처리
"""

import numpy as np
import librosa
import soundfile as sf
import logging
from typing import Dict, Any, List, Generator, Optional, Tuple
from pathlib import Path
import gc
from dataclasses import dataclass
import warnings
warnings.filterwarnings('ignore')

logger = logging.getLogger(__name__)

@dataclass
class ChunkResult:
    """청크 분석 결과"""
    start_time: float
    end_time: float
    features: Dict[str, float]
    duration: float

class LargeFileVoiceAnalyzer:
    """대용량 파일용 음성 분석기"""
    
    def __init__(
        self,
        chunk_duration: float = 30.0,  # 30초 단위 처리
        overlap: float = 2.0,  # 2초 겹침
        max_memory_mb: float = 500.0  # 최대 메모리 사용량
    ):
        """
        Args:
            chunk_duration: 각 청크의 길이 (초)
            overlap: 청크 간 겹침 (초)
            max_memory_mb: 최대 메모리 사용량 (MB)
        """
        self.chunk_duration = chunk_duration
        self.overlap = overlap
        self.max_memory_mb = max_memory_mb
        self.target_sr = 16000
        
    def analyze_large_file(self, audio_path: str) -> Dict[str, Any]:
        """
        대용량 오디오 파일 분석
        
        Args:
            audio_path: 오디오 파일 경로
            
        Returns:
            종합 분석 결과
        """
        try:
            file_info = self._get_file_info(audio_path)
            logger.info(f"파일 분석 시작: {file_info['duration']:.1f}초, {file_info['size_mb']:.1f}MB")
            
            # 파일 크기에 따라 처리 방식 결정
            if file_info['size_mb'] < 100:
                # 100MB 미만: 일반 처리
                return self._analyze_normal(audio_path)
            elif file_info['size_mb'] < 500:
                # 500MB 미만: 청킹 처리
                return self._analyze_chunked(audio_path, file_info)
            else:
                # 500MB 이상: 스트리밍 처리
                return self._analyze_streaming(audio_path, file_info)
                
        except Exception as e:
            logger.error(f"대용량 파일 분석 실패: {e}")
            return {
                'status': 'error',
                'error': str(e)
            }
    
    def _get_file_info(self, audio_path: str) -> Dict[str, Any]:
        """파일 정보 획득"""
        path = Path(audio_path)
        
        with sf.SoundFile(audio_path) as f:
            duration = len(f) / f.samplerate
            channels = f.channels
            samplerate = f.samplerate
        
        return {
            'path': audio_path,
            'size_mb': path.stat().st_size / (1024 * 1024),
            'duration': duration,
            'channels': channels,
            'samplerate': samplerate
        }
    
    def _analyze_normal(self, audio_path: str) -> Dict[str, Any]:
        """일반 분석 (작은 파일)"""
        from .voice_analysis import VoiceAnalyzer
        analyzer = VoiceAnalyzer()
        return analyzer.analyze(audio_path)
    
    def _analyze_chunked(self, audio_path: str, file_info: Dict) -> Dict[str, Any]:
        """청킹 방식 분석"""
        logger.info("청킹 방식으로 분석 시작")
        
        chunk_results = []
        total_duration = file_info['duration']
        
        # 청크 단위로 처리
        for chunk_data in self._generate_chunks(audio_path, file_info):
            result = self._analyze_chunk(chunk_data)
            chunk_results.append(result)
            
            # 메모리 정리
            gc.collect()
            
            # 진행상황 로깅
            progress = (chunk_data['end_time'] / total_duration) * 100
            logger.info(f"분석 진행: {progress:.1f}%")
        
        # 결과 통합
        return self._aggregate_chunk_results(chunk_results, file_info)
    
    def _analyze_streaming(self, audio_path: str, file_info: Dict) -> Dict[str, Any]:
        """스트리밍 방식 분석"""
        logger.info("스트리밍 방식으로 분석 시작")
        
        # 스트리밍 분석 결과 누적
        accumulated_features = {
            'pitch_values': [],
            'energy_values': [],
            'mfcc_values': [],
            'spectral_values': []
        }
        
        # 스트림 처리
        with sf.SoundFile(audio_path) as f:
            block_size = int(self.chunk_duration * f.samplerate)
            
            while True:
                audio_block = f.read(block_size, dtype='float32')
                
                if len(audio_block) == 0:
                    break
                
                # 모노로 변환
                if len(audio_block.shape) > 1:
                    audio_block = np.mean(audio_block, axis=1)
                
                # 블록 분석
                block_features = self._analyze_audio_block(audio_block, f.samplerate)
                
                # 특징 누적
                for key, value in block_features.items():
                    if key in accumulated_features:
                        accumulated_features[key].append(value)
                
                # 메모리 정리
                del audio_block
                gc.collect()
        
        # 최종 특징 계산
        return self._calculate_final_features(accumulated_features, file_info)
    
    def _generate_chunks(self, audio_path: str, file_info: Dict) -> Generator[Dict, None, None]:
        """청크 생성기"""
        duration = file_info['duration']
        chunk_duration = self.chunk_duration
        overlap = self.overlap
        
        start_time = 0
        while start_time < duration:
            end_time = min(start_time + chunk_duration, duration)
            
            # 오디오 청크 로드
            y, sr = librosa.load(
                audio_path,
                sr=self.target_sr,
                offset=start_time,
                duration=end_time - start_time
            )
            
            yield {
                'audio': y,
                'sr': sr,
                'start_time': start_time,
                'end_time': end_time
            }
            
            # 다음 청크 시작점 (겹침 고려)
            start_time = end_time - overlap if end_time < duration else duration
    
    def _analyze_chunk(self, chunk_data: Dict) -> ChunkResult:
        """개별 청크 분석"""
        y = chunk_data['audio']
        sr = chunk_data['sr']
        
        # 피치 분석
        pitches, magnitudes = librosa.piptrack(y=y, sr=sr)
        pitch_values = []
        for t in range(pitches.shape[1]):
            index = magnitudes[:, t].argmax()
            pitch = pitches[index, t]
            if pitch > 0:
                pitch_values.append(pitch)
        
        # 에너지 분석
        energy = np.sum(y ** 2) / len(y)
        
        # MFCC
        mfccs = librosa.feature.mfcc(y=y, sr=sr, n_mfcc=13)
        mfcc_mean = np.mean(mfccs, axis=1)
        
        # 스펙트럴 특징
        spectral_centroid = np.mean(librosa.feature.spectral_centroid(y=y, sr=sr))
        
        return ChunkResult(
            start_time=chunk_data['start_time'],
            end_time=chunk_data['end_time'],
            duration=chunk_data['end_time'] - chunk_data['start_time'],
            features={
                'pitch_mean': float(np.mean(pitch_values)) if pitch_values else 0.0,
                'pitch_std': float(np.std(pitch_values)) if pitch_values else 0.0,
                'energy_mean': float(energy),
                'mfcc_mean': mfcc_mean.tolist(),
                'spectral_centroid': float(spectral_centroid)
            }
        )
    
    def _analyze_audio_block(self, audio_block: np.ndarray, sr: int) -> Dict[str, Any]:
        """오디오 블록 분석 (스트리밍용)"""
        features = {}
        
        # 리샘플링 (필요시)
        if sr != self.target_sr:
            audio_block = librosa.resample(audio_block, orig_sr=sr, target_sr=self.target_sr)
            sr = self.target_sr
        
        # 피치
        pitches, magnitudes = librosa.piptrack(y=audio_block, sr=sr)
        pitch_values = []
        for t in range(pitches.shape[1]):
            index = magnitudes[:, t].argmax()
            pitch = pitches[index, t]
            if pitch > 0:
                pitch_values.append(pitch)
        
        features['pitch_values'] = np.mean(pitch_values) if pitch_values else 0.0
        
        # 에너지
        features['energy_values'] = np.sum(audio_block ** 2) / len(audio_block)
        
        # MFCC
        mfccs = librosa.feature.mfcc(y=audio_block, sr=sr, n_mfcc=13)
        features['mfcc_values'] = np.mean(mfccs, axis=1)
        
        # 스펙트럴
        features['spectral_values'] = np.mean(
            librosa.feature.spectral_centroid(y=audio_block, sr=sr)
        )
        
        return features
    
    def _aggregate_chunk_results(self, chunk_results: List[ChunkResult], file_info: Dict) -> Dict[str, Any]:
        """청크 결과 통합"""
        
        # 가중 평균 계산 (청크 길이 기준)
        total_duration = sum(r.duration for r in chunk_results)
        
        aggregated_features = {}
        feature_keys = ['pitch_mean', 'pitch_std', 'energy_mean', 'spectral_centroid']
        
        for key in feature_keys:
            weighted_sum = sum(
                r.features.get(key, 0) * r.duration 
                for r in chunk_results
            )
            aggregated_features[key] = weighted_sum / total_duration if total_duration > 0 else 0
        
        # MFCC는 평균
        mfcc_arrays = [r.features.get('mfcc_mean', []) for r in chunk_results if 'mfcc_mean' in r.features]
        if mfcc_arrays:
            aggregated_features['mfcc_mean'] = np.mean(mfcc_arrays, axis=0).tolist()
        
        # 추가 통계
        aggregated_features['speaking_rate'] = self._estimate_speaking_rate(chunk_results)
        aggregated_features['pause_ratio'] = self._estimate_pause_ratio(chunk_results)
        
        return {
            'status': 'success',
            'duration': file_info['duration'],
            'sample_rate': self.target_sr,
            'features': aggregated_features,
            'analysis_method': 'chunked',
            'chunk_count': len(chunk_results),
            'file_size_mb': file_info['size_mb']
        }
    
    def _calculate_final_features(self, accumulated_features: Dict, file_info: Dict) -> Dict[str, Any]:
        """누적된 특징으로부터 최종 특징 계산"""
        
        final_features = {}
        
        # 각 특징의 평균 계산
        for key, values in accumulated_features.items():
            if values and key != 'mfcc_values':
                final_features[key.replace('_values', '_mean')] = float(np.mean(values))
                final_features[key.replace('_values', '_std')] = float(np.std(values))
        
        # MFCC 특별 처리
        if accumulated_features.get('mfcc_values'):
            final_features['mfcc_mean'] = np.mean(accumulated_features['mfcc_values'], axis=0).tolist()
        
        # 기본값 추가
        final_features['speaking_rate'] = 3.0  # 기본값
        final_features['pause_ratio'] = 0.3  # 기본값
        
        return {
            'status': 'success',
            'duration': file_info['duration'],
            'sample_rate': self.target_sr,
            'features': final_features,
            'analysis_method': 'streaming',
            'file_size_mb': file_info['size_mb']
        }
    
    def _estimate_speaking_rate(self, chunk_results: List[ChunkResult]) -> float:
        """청크 결과로부터 발화 속도 추정"""
        # 간단한 추정: 에너지가 높은 구간의 비율로 계산
        high_energy_chunks = sum(
            1 for r in chunk_results 
            if r.features.get('energy_mean', 0) > 0.01
        )
        return (high_energy_chunks / len(chunk_results)) * 5.0 if chunk_results else 3.0
    
    def _estimate_pause_ratio(self, chunk_results: List[ChunkResult]) -> float:
        """청크 결과로부터 휴지 비율 추정"""
        # 간단한 추정: 낮은 에너지 구간의 비율
        low_energy_chunks = sum(
            1 for r in chunk_results 
            if r.features.get('energy_mean', 0) < 0.01
        )
        return low_energy_chunks / len(chunk_results) if chunk_results else 0.3


class AdaptiveVoiceAnalyzer:
    """파일 크기에 따라 자동으로 적절한 분석기를 선택하는 어댑터"""
    
    def __init__(self):
        self.small_file_threshold_mb = 50  # 50MB 미만은 일반 분석
        self.large_file_analyzer = LargeFileVoiceAnalyzer()
        
    def analyze(self, audio_path: str) -> Dict[str, Any]:
        """
        파일 크기에 따라 적절한 분석 방법 자동 선택
        
        Args:
            audio_path: 오디오 파일 경로
            
        Returns:
            분석 결과
        """
        file_size_mb = Path(audio_path).stat().st_size / (1024 * 1024)
        
        if file_size_mb < self.small_file_threshold_mb:
            # 작은 파일: 기존 분석기 사용
            from .voice_analysis import VoiceAnalyzer
            analyzer = VoiceAnalyzer()
            result = analyzer.analyze(audio_path)
            result['analysis_method'] = 'normal'
        else:
            # 큰 파일: 대용량 분석기 사용
            result = self.large_file_analyzer.analyze_large_file(audio_path)
        
        result['file_size_mb'] = file_size_mb
        return result