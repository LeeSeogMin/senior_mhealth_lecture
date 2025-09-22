"""
음성 분석 핵심 모듈
Librosa를 활용한 음성 특징 추출 및 분석
"""

import numpy as np
import warnings
import librosa
import logging
from typing import Dict, Optional, Tuple, Any
from dataclasses import dataclass

# Suppress librosa deprecation warnings
warnings.filterwarnings('ignore', message='.*__audioread_load.*')
warnings.filterwarnings('ignore', category=FutureWarning, module='librosa')

logger = logging.getLogger(__name__)

@dataclass
class VoiceFeatures:
    """음성 특징 데이터 클래스"""
    pitch_mean: float
    pitch_std: float
    energy_mean: float
    energy_std: float
    speaking_rate: float
    pause_ratio: float
    voice_quality: float
    spectral_centroid: float
    spectral_rolloff: float
    mfcc_features: np.ndarray
    tremor_amplitude: Optional[float] = None
    tremor_frequency: Optional[float] = None

class VoiceAnalyzer:
    """Librosa 기반 음성 분석기 (대용량 파일 지원)"""
    
    def __init__(self, sample_rate: int = 16000):
        self.sample_rate = sample_rate
        self.frame_length = 2048
        self.hop_length = 512
        # 파일 크기별 처리 전략 (실제 통화 녹음 고려)
        self.quick_threshold_mb = 1      # 1MB 이하: 전체 분석 (1분 이하)
        self.medium_threshold_mb = 3     # 1-3MB: 간소화 분석 (1-3분)
        self.large_threshold_mb = 10     # 3MB 이상: 청킹 분석 (3분 이상)
        
    def analyze(self, audio_path: str) -> Dict[str, Any]:
        """
        음성 파일 분석 (파일 크기에 따른 적응형 처리)
        
        Args:
            audio_path: 오디오 파일 경로
            
        Returns:
            분석된 음성 특징 딕셔너리
        """
        from pathlib import Path
        
        # 파일 크기 확인
        file_size_mb = Path(audio_path).stat().st_size / (1024 * 1024)
        
        logger.info(f"음성 분석 시작: {file_size_mb:.1f}MB 파일")
        
        # 파일 크기별 처리 전략
        if file_size_mb <= self.quick_threshold_mb:
            # 1분 이하: 전체 분석
            logger.info("Quick 모드: 전체 분석 수행")
            return self._analyze_small_file(audio_path, file_size_mb)
        elif file_size_mb <= self.medium_threshold_mb:
            # 1-3분: 간소화 분석
            logger.info("Medium 모드: 최적화된 분석 수행")
            return self._analyze_medium_file(audio_path, file_size_mb)
        else:
            # 3분 이상: 청킹 방식
            logger.info(f"Large 모드: 청킹 방식 사용 ({file_size_mb:.1f}MB)")
            return self._analyze_large_file(audio_path, file_size_mb)
    
    def _analyze_small_file(self, audio_path: str, file_size_mb: float) -> Dict[str, Any]:
        """작은 파일 분석 (1분 이하) - 전체 분석"""
        try:
            # 오디오 로드
            y, sr = librosa.load(audio_path, sr=self.sample_rate)
            
            # 음성 특징 추출
            features = self._extract_features(y, sr)
            
            # 시니어 특화 분석
            senior_features = self._analyze_senior_specific(y, sr)
            features.update(senior_features)
            
            return {
                'status': 'success',
                'features': features,
                'sample_rate': sr,
                'duration': len(y) / sr,
                'analysis_method': 'full',
                'file_size_mb': file_size_mb
            }
            
        except Exception as e:
            logger.error(f"음성 분석 실패: {e}")
            return {
                'status': 'error',
                'error': str(e)
            }
    
    def _analyze_medium_file(self, audio_path: str, file_size_mb: float) -> Dict[str, Any]:
        """중간 크기 파일 분석 (1-3분) - 최적화된 분석"""
        try:
            # 파일 길이만 먼저 확인
            duration = librosa.get_duration(path=audio_path)
            logger.info(f"Medium 파일 분석: {duration:.1f}초, {file_size_mb:.1f}MB")
            
            # 다운샘플링으로 빠른 로드 (16kHz -> 8kHz)
            y, sr = librosa.load(audio_path, sr=8000)
            
            # 빠른 피치 추출 (더 큰 홉 길이)
            hop_length = self.hop_length * 8  # 더 큰 홉으로 빠르게
            pitches, magnitudes = librosa.piptrack(
                y=y, sr=sr, 
                hop_length=hop_length,
                fmin=50, fmax=400
            )
            
            # 피치 통계
            max_indices = np.argmax(magnitudes, axis=0)
            pitch_values = pitches[max_indices, np.arange(pitches.shape[1])]
            pitch_values = pitch_values[pitch_values > 0]
            
            # 에너지 계산
            energy = librosa.feature.rms(y=y, hop_length=hop_length)[0]
            
            # 간소화된 MFCC (더 적은 계수)
            mfccs = librosa.feature.mfcc(y=y, sr=sr, n_mfcc=6, hop_length=hop_length)
            
            # 기본 스펙트럴 특징
            spectral_centroids = librosa.feature.spectral_centroid(y=y, sr=sr, hop_length=hop_length)[0]
            spectral_rolloff = librosa.feature.spectral_rolloff(y=y, sr=sr, hop_length=hop_length)[0]
            zcr = librosa.feature.zero_crossing_rate(y, hop_length=hop_length)[0]
            
            # 빠른 발화 속도 계산 (음성 활동 비율)
            intervals = librosa.effects.split(y, top_db=25)
            speech_time = sum((end - start) for start, end in intervals) / sr
            pause_ratio = 1 - (speech_time / duration) if duration > 0 else 0
            
            # 간소화된 발화 속도 추정 (음절 수 기반)
            syllable_count = 0
            for interval in intervals:
                interval_duration = (interval[1] - interval[0]) / sr
                syllable_count += interval_duration / 0.2  # 한국어 평균 음절 길이
            speaking_rate = syllable_count / duration if duration > 0 else 0
            
            # 피치 값 검증
            if len(pitch_values) == 0:
                logger.warning("Medium 모드: 피치 추출 실패 - 무음/노이즈 구간으로 추정")
            
            features = {
                'pitch_mean': float(np.mean(pitch_values)) if len(pitch_values) > 0 else 0.0,
                'pitch_std': float(np.std(pitch_values)) if len(pitch_values) > 0 else 0.0,
                'energy_mean': float(np.mean(energy)),
                'energy_std': float(np.std(energy)),
                'mfcc_mean': np.mean(mfccs, axis=1).tolist(),
                'mfcc_std': np.std(mfccs, axis=1).tolist(),
                'spectral_centroid_mean': float(np.mean(spectral_centroids)),
                'spectral_rolloff_mean': float(np.mean(spectral_rolloff)),
                'zcr_mean': float(np.mean(zcr)),
                'speaking_rate': float(speaking_rate),
                'pause_ratio': float(pause_ratio),
                # 간소화 분석에서는 복잡한 특징 생략 (키는 제거)
            }
            
            return {
                'status': 'success',
                'features': features,
                'sample_rate': sr,
                'duration': duration,
                'analysis_method': 'optimized',
                'file_size_mb': file_size_mb
            }
            
        except Exception as e:
            logger.error(f"중간 파일 분석 실패: {e}")
            return {'status': 'error', 'error': str(e)}
    
    def _extract_features(self, y: np.ndarray, sr: int) -> Dict[str, Any]:
        """기본 음성 특징 추출 (최적화된 버전)"""
        
        # 피치 추출 (최적화: 더 적은 프레임으로 빠르게)
        # piptrack 대신 더 빠른 방법 사용
        hop_length = self.hop_length * 4  # 더 큰 홉 길이로 빠르게
        pitches, magnitudes = librosa.piptrack(
            y=y, sr=sr, 
            hop_length=hop_length,
            fmin=50,  # 최소 주파수 제한
            fmax=400  # 최대 주파수 제한 (음성 범위)
        )
        
        # 벡터화된 방식으로 피치 추출 (루프 제거)
        max_indices = np.argmax(magnitudes, axis=0)
        pitch_values = pitches[max_indices, np.arange(pitches.shape[1])]
        pitch_values = pitch_values[pitch_values > 0]  # 유효한 피치만
        
        # 피치 값 검증 - 경고 후 처리
        if len(pitch_values) == 0:
            logger.warning("피치 추출 실패: 유효한 피치 값이 없습니다 - 무음 구간으로 추정")
            pitch_mean = 0.0  # 무음 구간 표시
            pitch_std = 0.0
        else:
            pitch_mean = np.mean(pitch_values)
            pitch_std = np.std(pitch_values)
        
        # 에너지 계산
        energy = librosa.feature.rms(y=y)[0]
        energy_mean = np.mean(energy)
        energy_std = np.std(energy)
        
        # MFCC 추출 (최적화: 더 적은 계수)
        mfccs = librosa.feature.mfcc(
            y=y, sr=sr, 
            n_mfcc=8,  # 13에서 8로 줄임
            hop_length=hop_length  # 동일한 홉 길이 사용
        )
        mfcc_mean = np.mean(mfccs, axis=1)
        mfcc_std = np.std(mfccs, axis=1)
        
        # 스펙트럴 특징 (최적화: 동일한 홉 길이)
        spectral_centroids = librosa.feature.spectral_centroid(
            y=y, sr=sr, hop_length=hop_length
        )[0]
        spectral_rolloff = librosa.feature.spectral_rolloff(
            y=y, sr=sr, hop_length=hop_length
        )[0]
        
        # Zero Crossing Rate (음성 품질 지표)
        zcr = librosa.feature.zero_crossing_rate(y)[0]
        
        # 발화 속도 계산 (청크에서도 필요)
        speaking_rate = self._calculate_speaking_rate(y, sr)
        
        # 휴지 비율 계산 (청크에서도 필요)
        pause_ratio = self._calculate_pause_ratio(y, sr)
        
        # 음성 명료도 (청크에서도 필요)
        voice_clarity = self._analyze_voice_clarity(y, sr)
        
        return {
            'pitch_mean': float(pitch_mean),
            'pitch_std': float(pitch_std),
            'energy_mean': float(energy_mean),
            'energy_std': float(energy_std),
            'mfcc_mean': mfcc_mean.tolist(),
            'mfcc_std': mfcc_std.tolist(),
            'spectral_centroid_mean': float(np.mean(spectral_centroids)),
            'spectral_rolloff_mean': float(np.mean(spectral_rolloff)),
            'zcr_mean': float(np.mean(zcr)),
            'speaking_rate': float(speaking_rate),
            'pause_ratio': float(pause_ratio),
            'voice_quality': float(voice_clarity)
        }
    
    def _analyze_senior_specific(self, y: np.ndarray, sr: int) -> Dict[str, Any]:
        """시니어 특화 음성 분석"""
        
        # 음성 떨림 (tremor) 분석
        tremor_features = self._analyze_tremor(y, sr)
        
        # 발화 속도 분석
        speaking_rate = self._calculate_speaking_rate(y, sr)
        
        # 휴지(pause) 비율 계산
        pause_ratio = self._calculate_pause_ratio(y, sr)
        
        # 음성 명료도 분석
        clarity_score = self._analyze_voice_clarity(y, sr)
        
        return {
            'tremor_amplitude': tremor_features.get('amplitude', 0),
            'tremor_frequency': tremor_features.get('frequency', 0),
            'speaking_rate': speaking_rate,
            'pause_ratio': pause_ratio,
            'voice_clarity': clarity_score
        }
    
    def _analyze_tremor(self, y: np.ndarray, sr: int) -> Dict[str, float]:
        """음성 떨림 분석"""
        try:
            # 단시간 에너지 계산
            frame_length = int(0.025 * sr)  # 25ms
            hop_length = int(0.010 * sr)    # 10ms
            
            energy = []
            for i in range(0, len(y) - frame_length, hop_length):
                frame = y[i:i + frame_length]
                energy.append(np.sum(frame ** 2))
            
            energy = np.array(energy)
            
            # 에너지 변동 분석 (3-8Hz 범위의 떨림 검출)
            fft_energy = np.fft.fft(energy)
            freqs = np.fft.fftfreq(len(energy), d=hop_length/sr)
            
            # 3-8Hz 범위의 주파수 성분 추출
            tremor_range = (freqs >= 3) & (freqs <= 8)
            tremor_power = np.abs(fft_energy[tremor_range])
            
            if len(tremor_power) > 0:
                max_idx = np.argmax(tremor_power)
                tremor_freq = freqs[tremor_range][max_idx]
                tremor_amp = tremor_power[max_idx] / len(energy)
                
                return {
                    'frequency': float(tremor_freq),
                    'amplitude': float(tremor_amp)
                }
        except Exception as e:
            logger.warning(f"떨림 분석 실패: {e}")
            # 떨림 분석 실패 시 기본값 반환 (완전 실패보다 나음)
            return {'frequency': 0.0, 'amplitude': 0.0}
    
    def _calculate_speaking_rate(self, y: np.ndarray, sr: int) -> float:
        """발화 속도 계산"""
        try:
            # 음성 활동 구간 검출
            intervals = librosa.effects.split(y, top_db=20)
            
            # 음절 수 추정 (한국어 기준)
            syllable_count = 0
            for interval in intervals:
                duration = (interval[1] - interval[0]) / sr
                # 한국어 평균 음절 지속 시간: 약 0.2초
                syllable_count += duration / 0.2
            
            total_duration = len(y) / sr
            speaking_rate = syllable_count / total_duration if total_duration > 0 else 0
            
            return float(speaking_rate)
        except Exception as e:
            logger.warning(f"발화 속도 계산 실패: {e}")
            return 0.0  # 실패 시 0 반환
    
    def _calculate_pause_ratio(self, y: np.ndarray, sr: int) -> float:
        """휴지 비율 계산"""
        try:
            # 음성 활동 구간 검출
            intervals = librosa.effects.split(y, top_db=20)
            
            # 총 음성 시간 계산
            speech_time = sum((end - start) for start, end in intervals) / sr
            total_time = len(y) / sr
            
            # 휴지 비율
            pause_ratio = 1 - (speech_time / total_time) if total_time > 0 else 0
            
            return float(pause_ratio)
        except Exception as e:
            logger.warning(f"휴지 비율 계산 실패: {e}")
            return 0.0  # 실패 시 0 반환
    
    def _analyze_voice_clarity(self, y: np.ndarray, sr: int) -> float:
        """음성 명료도 분석"""
        try:
            # 스펙트럴 엔트로피 (낮을수록 명료)
            spectral_entropy = self._calculate_spectral_entropy(y, sr)
            
            # Harmonics-to-Noise Ratio (HNR)
            hnr = self._calculate_hnr(y, sr)
            
            # 명료도 점수 계산 (0-1 범위)
            clarity_score = (hnr / 20) * (1 - spectral_entropy)
            clarity_score = np.clip(clarity_score, 0, 1)
            
            return float(clarity_score)
        except Exception as e:
            logger.warning(f"명료도 분석 실패: {e}")
            return 0.5  # 실패 시 중간값 반환
    
    def _calculate_spectral_entropy(self, y: np.ndarray, sr: int) -> float:
        """스펙트럴 엔트로피 계산"""
        try:
            # STFT
            D = librosa.stft(y)
            magnitude = np.abs(D)
            
            # 정규화
            magnitude_norm = magnitude / np.sum(magnitude, axis=0, keepdims=True)
            
            # 엔트로피 계산
            entropy = -np.sum(magnitude_norm * np.log2(magnitude_norm + 1e-10), axis=0)
            
            return float(np.mean(entropy) / np.log2(magnitude.shape[0]))
        except Exception as e:
            logger.warning(f"스펙트럴 엔트로피 계산 실패: {e}")
            return 0.5  # 실패 시 중간값 반환
    
    def _analyze_large_file(self, audio_path: str, file_size_mb: float) -> Dict[str, Any]:
        """
        대용량 파일 분석 (개선된 청킹 방식)
        
        Args:
            audio_path: 오디오 파일 경로
            file_size_mb: 파일 크기 (MB)
            
        Returns:
            분석 결과
        """
        import gc
        from concurrent.futures import ThreadPoolExecutor, as_completed
        
        try:
            # 파일 크기에 따른 적응형 청크 설정 (메모리 최적화)
            if file_size_mb < 5:
                chunk_duration = 10.0  # 10초 청크 (작은 파일)
            elif file_size_mb < 10:
                chunk_duration = 5.0   # 5초 청크 (중간 파일)
            else:
                chunk_duration = 3.0   # 3초 청크 (큰 파일, 메모리 절약)
            
            overlap = 0.5  # 오버랩 최소화 (2초 -> 0.5초)
            
            # 파일 정보 가져오기
            info = librosa.get_duration(path=audio_path)
            total_duration = info
            
            logger.info(f"대용량 파일 분석 시작: {total_duration:.1f}초, {file_size_mb:.1f}MB")
            
            # 청크별 특징 저장
            chunk_features = []
            current_offset = 0

            while current_offset < total_duration:
                # 청크 로드
                duration = min(chunk_duration, total_duration - current_offset)
                try:
                    # ffmpeg를 백엔드로 명시적 지정
                    import audioread
                    with audioread.audio_open(audio_path) as f:
                        # librosa 로드 (ffmpeg 사용)
                        y_chunk, sr = librosa.load(
                            audio_path,
                            sr=self.sample_rate,
                            offset=current_offset,
                            duration=duration,
                            mono=True,  # 모노로 강제 변환 (메모리 절약)
                            res_type='kaiser_fast'  # 빠른 리샘플링
                        )
                except Exception as e:
                    logger.warning(f"청크 로드 실패 (offset={current_offset}): {e}")
                    current_offset += chunk_duration
                    continue

                # 청크 분석
                if len(y_chunk) > 0:
                    features = self._extract_features(y_chunk, sr)
                    chunk_features.append(features)

                # 즉시 메모리 정리
                del y_chunk
                if len(chunk_features) % 10 == 0:  # 10청크마다 강제 GC
                    gc.collect()

                # 다음 청크 위치
                current_offset += (chunk_duration - overlap)
                
                # 진행 상황 로깅
                progress = min(100, (current_offset / total_duration) * 100)
                logger.info(f"분석 진행: {progress:.1f}%")
            
            # 청크 결과 통합
            if not chunk_features:
                raise ValueError("청크 분석 실패")
            
            # 가중 평균으로 최종 특징 계산
            final_features = self._aggregate_chunk_features(chunk_features)
            
            return {
                'status': 'success',
                'duration': total_duration,
                'sample_rate': self.sample_rate,
                'features': final_features,
                'analysis_method': 'chunked',
                'chunk_count': len(chunk_features),
                'file_size_mb': file_size_mb
            }
            
        except Exception as e:
            logger.error(f"대용량 파일 분석 실패: {e}")
            return {
                'status': 'error',
                'error': str(e),
                'file_size_mb': file_size_mb
            }
    
    def _aggregate_chunk_features(self, chunk_features: list) -> Dict[str, Any]:
        """청크 특징들을 통합"""
        
        # 각 특징의 평균 계산
        aggregated = {}
        
        # 숫자형 특징들 (업데이트된 키 목록)
        numeric_keys = [
            'pitch_mean', 'pitch_std', 'energy_mean', 'energy_std',
            'speaking_rate', 'pause_ratio', 'voice_quality',
            'spectral_centroid_mean', 'spectral_rolloff_mean', 'zcr_mean'
        ]
        
        for key in numeric_keys:
            values = [f.get(key, 0) for f in chunk_features if key in f]
            if not values:
                logger.warning(f"청크 특징 통합: {key}에 대한 값이 없습니다")
                aggregated[key] = 0.0  # 값이 없으면 0
            else:
                aggregated[key] = float(np.mean(values))
        
        # 호환성을 위한 별칭 추가
        if 'spectral_centroid_mean' in aggregated:
            aggregated['spectral_centroid'] = aggregated['spectral_centroid_mean']
        if 'spectral_rolloff_mean' in aggregated:
            aggregated['spectral_rolloff'] = aggregated['spectral_rolloff_mean']
        
        # MFCC는 평균
        mfcc_arrays = [f.get('mfcc_mean', []) for f in chunk_features if 'mfcc_mean' in f]
        if mfcc_arrays:
            aggregated['mfcc_mean'] = np.mean(mfcc_arrays, axis=0).tolist()
        
        # 떨림 분석
        tremor_amps = [f.get('tremor_amplitude', 0) for f in chunk_features if 'tremor_amplitude' in f]
        if tremor_amps:
            aggregated['tremor_amplitude'] = float(np.mean(tremor_amps))
            
        tremor_freqs = [f.get('tremor_frequency', 0) for f in chunk_features if 'tremor_frequency' in f]
        if tremor_freqs:
            aggregated['tremor_frequency'] = float(np.mean(tremor_freqs))
        
        # voice_clarity 별칭 추가 (호환성)
        if 'voice_quality' in aggregated:
            aggregated['voice_clarity'] = aggregated['voice_quality']
        
        return aggregated
    
    def _calculate_hnr(self, y: np.ndarray, sr: int) -> float:
        """Harmonics-to-Noise Ratio 계산"""
        try:
            # 자기상관 함수
            autocorr = np.correlate(y, y, mode='full')
            autocorr = autocorr[len(autocorr)//2:]
            
            # 첫 번째 피크 찾기
            peak_idx = np.argmax(autocorr[int(sr/500):int(sr/50)]) + int(sr/500)
            
            if peak_idx > 0 and peak_idx < len(autocorr):
                harmonics = autocorr[peak_idx]
                noise = np.mean(np.abs(y)) - harmonics
                
                if noise > 0:
                    hnr = 20 * np.log10(harmonics / noise)
                    return float(np.clip(hnr, 0, 20))
                else:
                    logger.warning("노이즈 값이 0 이하입니다")
                    return 10.0  # 기본 HNR 값
        except Exception as e:
            logger.warning(f"HNR 계산 실패: {e}")
            return 10.0  # 실패 시 기본값 반환