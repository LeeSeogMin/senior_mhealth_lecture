"""
시니어 음성 특징 추출 및 분석 모듈
Librosa 기반 실시간 음성 분석 시스템
"""

import numpy as np
import librosa
import logging
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass, asdict
from pathlib import Path

logger = logging.getLogger(__name__)


@dataclass
class VoiceFeatures:
    """음성 특징 데이터 클래스"""
    # 기본 음향 특징
    pitch_mean: float
    pitch_std: float
    pitch_range: float
    
    # 에너지 특징
    energy_mean: float
    energy_std: float
    energy_range: float
    
    # 시간 특징
    speech_rate: float  # 음절/초
    pause_ratio: float  # 침묵 비율
    voice_activity_ratio: float  # 음성 활동 비율
    
    # 스펙트럼 특징
    spectral_centroid: float
    spectral_rolloff: float
    spectral_bandwidth: float
    zero_crossing_rate: float
    
    # MFCC 특징 (13차원)
    mfcc_mean: np.ndarray
    mfcc_std: np.ndarray
    
    # 포먼트 특징 (노인 음성 특성)
    formant_frequencies: Optional[List[float]] = None
    
    # 떨림 특징 (노인 특성)
    jitter: Optional[float] = None  # 피치 떨림
    shimmer: Optional[float] = None  # 진폭 떨림


class SeniorVoiceAnalyzer:
    """시니어 음성 특징 분석기"""
    
    def __init__(self, sample_rate: int = 16000):
        """
        초기화
        
        Args:
            sample_rate: 샘플링 레이트
        """
        self.sr = sample_rate
        
        # 시니어 음성 특성 임계값
        self.senior_thresholds = {
            'pitch_mean': (80, 180),  # Hz, 노인은 일반적으로 낮음
            'speech_rate': (2.0, 4.0),  # 음절/초, 노인은 느림
            'pause_ratio': (0.25, 0.6),  # 노인은 침묵이 많음
            'energy_std': (0.015, 0.05),  # 노인은 변동성이 큼
            'spectral_centroid': (1000, 2500),  # Hz, 노인은 낮음
            'jitter': (0.005, 0.02),  # 노인은 높음
            'shimmer': (0.03, 0.1)  # 노인은 높음
        }
        
    def extract_features(self, audio: np.ndarray, sr: int = None) -> VoiceFeatures:
        """
        음성 특징 추출
        
        Args:
            audio: 오디오 신호
            sr: 샘플링 레이트
            
        Returns:
            VoiceFeatures 객체
        """
        if sr is None:
            sr = self.sr
            
        # 무음 제거
        audio_trimmed, _ = librosa.effects.trim(audio, top_db=20)
        
        # 1. 피치 특징 추출
        pitch_features = self._extract_pitch_features(audio_trimmed, sr)
        
        # 2. 에너지 특징 추출
        energy_features = self._extract_energy_features(audio_trimmed)
        
        # 3. 시간 특징 추출
        temporal_features = self._extract_temporal_features(audio_trimmed, sr)
        
        # 4. 스펙트럼 특징 추출
        spectral_features = self._extract_spectral_features(audio_trimmed, sr)
        
        # 5. MFCC 특징 추출
        mfcc_features = self._extract_mfcc_features(audio_trimmed, sr)
        
        # 6. 떨림 특징 추출 (노인 특성)
        tremor_features = self._extract_tremor_features(audio_trimmed, sr)
        
        return VoiceFeatures(
            **pitch_features,
            **energy_features,
            **temporal_features,
            **spectral_features,
            **mfcc_features,
            **tremor_features
        )
    
    def _extract_pitch_features(self, audio: np.ndarray, sr: int) -> Dict[str, float]:
        """피치 특징 추출"""
        # 피치 추적
        pitches, magnitudes = librosa.piptrack(y=audio, sr=sr, threshold=0.1)
        
        # 유효한 피치 값만 추출
        pitch_values = []
        for t in range(pitches.shape[1]):
            index = magnitudes[:, t].argmax()
            pitch = pitches[index, t]
            if pitch > 0:
                pitch_values.append(pitch)
        
        if pitch_values:
            pitch_array = np.array(pitch_values)
            return {
                'pitch_mean': float(np.mean(pitch_array)),
                'pitch_std': float(np.std(pitch_array)),
                'pitch_range': float(np.max(pitch_array) - np.min(pitch_array))
            }
        else:
            return {
                'pitch_mean': 0.0,
                'pitch_std': 0.0,
                'pitch_range': 0.0
            }
    
    def _extract_energy_features(self, audio: np.ndarray) -> Dict[str, float]:
        """에너지 특징 추출"""
        # RMS 에너지
        rms = librosa.feature.rms(y=audio)[0]
        
        return {
            'energy_mean': float(np.mean(rms)),
            'energy_std': float(np.std(rms)),
            'energy_range': float(np.max(rms) - np.min(rms))
        }
    
    def _extract_temporal_features(self, audio: np.ndarray, sr: int) -> Dict[str, float]:
        """시간 특징 추출"""
        # 음성 활동 검출
        energy = librosa.feature.rms(y=audio)[0]
        threshold = np.mean(energy) * 0.2
        voice_activity = energy > threshold
        
        # 음성 활동 비율
        voice_activity_ratio = np.sum(voice_activity) / len(voice_activity)
        
        # 침묵 비율
        pause_ratio = 1 - voice_activity_ratio
        
        # 음절 검출 (onset detection을 통한 근사)
        onset_frames = librosa.onset.onset_detect(y=audio, sr=sr)
        duration = len(audio) / sr
        speech_rate = len(onset_frames) / duration if duration > 0 else 0
        
        return {
            'speech_rate': float(speech_rate),
            'pause_ratio': float(pause_ratio),
            'voice_activity_ratio': float(voice_activity_ratio)
        }
    
    def _extract_spectral_features(self, audio: np.ndarray, sr: int) -> Dict[str, float]:
        """스펙트럼 특징 추출"""
        # Spectral Centroid
        spectral_centroids = librosa.feature.spectral_centroid(y=audio, sr=sr)[0]
        
        # Spectral Rolloff
        spectral_rolloff = librosa.feature.spectral_rolloff(y=audio, sr=sr)[0]
        
        # Spectral Bandwidth
        spectral_bandwidth = librosa.feature.spectral_bandwidth(y=audio, sr=sr)[0]
        
        # Zero Crossing Rate
        zcr = librosa.feature.zero_crossing_rate(audio)[0]
        
        return {
            'spectral_centroid': float(np.mean(spectral_centroids)),
            'spectral_rolloff': float(np.mean(spectral_rolloff)),
            'spectral_bandwidth': float(np.mean(spectral_bandwidth)),
            'zero_crossing_rate': float(np.mean(zcr))
        }
    
    def _extract_mfcc_features(self, audio: np.ndarray, sr: int) -> Dict[str, np.ndarray]:
        """MFCC 특징 추출"""
        mfccs = librosa.feature.mfcc(y=audio, sr=sr, n_mfcc=13)
        
        return {
            'mfcc_mean': np.mean(mfccs, axis=1),
            'mfcc_std': np.std(mfccs, axis=1)
        }
    
    def _extract_tremor_features(self, audio: np.ndarray, sr: int) -> Dict[str, Optional[float]]:
        """떨림 특징 추출 (노인 특성)"""
        try:
            # 피치 추적
            pitches, magnitudes = librosa.piptrack(y=audio, sr=sr)
            
            # 유효한 피치 값 추출
            pitch_contour = []
            for t in range(pitches.shape[1]):
                index = magnitudes[:, t].argmax()
                pitch = pitches[index, t]
                if pitch > 0:
                    pitch_contour.append(pitch)
            
            if len(pitch_contour) > 10:
                pitch_array = np.array(pitch_contour)
                
                # Jitter: 연속된 피치 간의 변동
                pitch_diffs = np.abs(np.diff(pitch_array))
                jitter = np.mean(pitch_diffs) / np.mean(pitch_array) if np.mean(pitch_array) > 0 else 0
                
                # Shimmer: 진폭 변동 (RMS 에너지 사용)
                rms = librosa.feature.rms(y=audio)[0]
                rms_diffs = np.abs(np.diff(rms))
                shimmer = np.mean(rms_diffs) / np.mean(rms) if np.mean(rms) > 0 else 0
                
                return {
                    'jitter': float(jitter),
                    'shimmer': float(shimmer)
                }
            else:
                return {'jitter': None, 'shimmer': None}
                
        except Exception as e:
            logger.warning(f"떨림 특징 추출 실패: {e}")
            return {'jitter': None, 'shimmer': None}
    
    def calculate_senior_score(self, features: VoiceFeatures) -> Tuple[float, Dict[str, float]]:
        """
        시니어 점수 계산
        
        Args:
            features: 음성 특징
            
        Returns:
            (시니어 점수 0-1, 세부 점수)
        """
        scores = {}
        weights = {
            'pitch': 0.2,
            'speech_rate': 0.25,
            'pause': 0.2,
            'energy': 0.15,
            'spectral': 0.1,
            'tremor': 0.1
        }
        
        # 1. 피치 점수
        if self.senior_thresholds['pitch_mean'][0] <= features.pitch_mean <= self.senior_thresholds['pitch_mean'][1]:
            scores['pitch'] = 1.0
        else:
            # 범위를 벗어날수록 점수 감소
            if features.pitch_mean < self.senior_thresholds['pitch_mean'][0]:
                scores['pitch'] = features.pitch_mean / self.senior_thresholds['pitch_mean'][0]
            else:
                scores['pitch'] = max(0, 1 - (features.pitch_mean - self.senior_thresholds['pitch_mean'][1]) / 100)
        
        # 2. 말속도 점수
        if self.senior_thresholds['speech_rate'][0] <= features.speech_rate <= self.senior_thresholds['speech_rate'][1]:
            scores['speech_rate'] = 1.0
        else:
            scores['speech_rate'] = 0.5
        
        # 3. 침묵 비율 점수
        if self.senior_thresholds['pause_ratio'][0] <= features.pause_ratio <= self.senior_thresholds['pause_ratio'][1]:
            scores['pause'] = 1.0
        else:
            scores['pause'] = 0.5
        
        # 4. 에너지 변동성 점수
        if self.senior_thresholds['energy_std'][0] <= features.energy_std <= self.senior_thresholds['energy_std'][1]:
            scores['energy'] = 1.0
        else:
            scores['energy'] = 0.5
        
        # 5. 스펙트럼 점수
        if self.senior_thresholds['spectral_centroid'][0] <= features.spectral_centroid <= self.senior_thresholds['spectral_centroid'][1]:
            scores['spectral'] = 1.0
        else:
            scores['spectral'] = 0.5
        
        # 6. 떨림 점수
        if features.jitter is not None and features.shimmer is not None:
            jitter_score = 1.0 if features.jitter > self.senior_thresholds['jitter'][0] else 0.5
            shimmer_score = 1.0 if features.shimmer > self.senior_thresholds['shimmer'][0] else 0.5
            scores['tremor'] = (jitter_score + shimmer_score) / 2
        else:
            scores['tremor'] = 0.5  # 중립값
        
        # 가중 평균 계산
        total_score = sum(scores[key] * weights[key] for key in scores)
        
        return total_score, scores
    
    def analyze_segment(self, audio_path: str, start_time: float, end_time: float) -> Dict[str, Any]:
        """
        특정 세그먼트 분석
        
        Args:
            audio_path: 오디오 파일 경로
            start_time: 시작 시간 (초)
            end_time: 종료 시간 (초)
            
        Returns:
            분석 결과
        """
        try:
            # 오디오 로드 (특정 구간만)
            duration = end_time - start_time
            audio, sr = librosa.load(
                audio_path,
                sr=self.sr,
                offset=start_time,
                duration=duration
            )
            
            # 특징 추출
            features = self.extract_features(audio, sr)
            
            # 시니어 점수 계산
            senior_score, score_details = self.calculate_senior_score(features)
            
            return {
                'success': True,
                'features': asdict(features),
                'senior_score': senior_score,
                'score_details': score_details,
                'is_senior': senior_score > 0.6,
                'confidence': min(senior_score * 1.2, 1.0)  # 신뢰도 조정
            }
            
        except Exception as e:
            logger.error(f"세그먼트 분석 실패: {e}")
            return {
                'success': False,
                'error': str(e)
            }