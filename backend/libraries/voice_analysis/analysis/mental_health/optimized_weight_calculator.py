"""
최적화된 가중치 계산 시스템
데이터 품질 기반 적응형 가중치 체계
mental-health-2 프로젝트에서 이식 및 개선
"""

import numpy as np
import logging
from typing import Dict, Any, Optional, List, Tuple
from dataclasses import dataclass
from enum import Enum

logger = logging.getLogger(__name__)

class AnalysisMethod(Enum):
    """분석 방법론"""
    VOICE = "voice"      # Librosa 음성 분석
    TEXT = "text"        # GPT-4/Gemini 텍스트 분석
    DEEP = "deep"        # SincNet 딥러닝 분석

class IndicatorType(Enum):
    """5대 정신건강 지표"""
    DRI = "DRI"  # Depression Risk Indicator
    SDI = "SDI"  # Sleep Disorder Indicator
    CFL = "CFL"  # Cognitive Function Level
    ES = "ES"    # Emotional Stability
    OV = "OV"    # Overall Vitality

@dataclass
class OptimizedWeights:
    """최적화된 가중치"""
    voice: float
    text: float
    deep: float

    def __post_init__(self):
        # 가중치 합이 1.0이 되도록 정규화
        total = self.voice + self.text + self.deep
        if total > 0:
            self.voice /= total
            self.text /= total
            self.deep /= total

@dataclass
class DataQuality:
    """데이터 품질 정보"""
    voice_quality: float = 1.0    # 음성 품질 (0-1)
    text_quality: float = 1.0     # 텍스트 품질 (0-1)
    deep_quality: float = 1.0     # 딥러닝 품질 (0-1)
    audio_duration: float = 0.0   # 오디오 길이 (초)
    text_length: int = 0          # 텍스트 길이 (단어 수)

    @classmethod
    def from_analysis_results(cls, voice_analysis: Dict, text_analysis: Dict, audio_path: str = None):
        """분석 결과로부터 데이터 품질 생성"""
        import os
        from pathlib import Path

        # 음성 품질 평가
        voice_quality = 1.0
        if voice_analysis and voice_analysis.get('status') == 'success':
            features = voice_analysis.get('features', {})
            # 음성 특징이 있으면 품질 양호
            if features:
                voice_quality = 0.8
                # SNR이나 에너지 레벨로 품질 평가
                if 'energy_mean' in features:
                    energy = features['energy_mean']
                    if energy > 0.01:  # 적절한 에너지 레벨
                        voice_quality = 0.9
        else:
            voice_quality = 0.3

        # 텍스트 품질 평가
        text_quality = 1.0
        text_length = 0
        if text_analysis:
            # 지표가 있으면 품질 양호
            if 'indicators' in text_analysis:
                text_quality = 0.9
            # 텍스트 길이 계산
            if 'text_content' in text_analysis:
                text_length = len(text_analysis['text_content'].split())
            elif 'linguistic_features' in text_analysis:
                text_length = text_analysis['linguistic_features'].get('word_count', 0)
        else:
            text_quality = 0.3

        # 딥러닝 품질 (오디오 길이 기반)
        deep_quality = 0.7  # 기본값
        audio_duration = 0

        if audio_path and os.path.exists(audio_path):
            # 파일 크기로 대략적인 길이 추정
            file_size_mb = Path(audio_path).stat().st_size / (1024 * 1024)
            audio_duration = file_size_mb * 60  # 대략 1MB = 1분

            if audio_duration > 30:
                deep_quality = 0.9
            elif audio_duration > 10:
                deep_quality = 0.7
            else:
                deep_quality = 0.5

        if voice_analysis and 'duration' in voice_analysis:
            audio_duration = voice_analysis['duration']

        return cls(
            voice_quality=voice_quality,
            text_quality=text_quality,
            deep_quality=deep_quality,
            audio_duration=audio_duration,
            text_length=text_length
        )

class OptimizedWeightCalculator:
    """
    데이터 품질 기반 최적화된 가중치 계산기

    Senior_MHealth 프로젝트에 맞춰 조정:
    - GPT-4/Gemini 텍스트 분석 중심
    - RAG 지원 시 텍스트 가중치 증가
    - 시니어 음성 특성 고려
    """

    def __init__(self, use_rag: bool = False):
        self.use_rag = use_rag

        # 연구 기반 기본 가중치
        self.base_weights = {
            IndicatorType.DRI: OptimizedWeights(voice=0.3, text=0.4, deep=0.3),  # 우울: 텍스트 중심
            IndicatorType.SDI: OptimizedWeights(voice=0.4, text=0.3, deep=0.3),  # 수면: 음성 중심
            IndicatorType.CFL: OptimizedWeights(voice=0.2, text=0.6, deep=0.2),  # 인지: 텍스트 중심
            IndicatorType.ES: OptimizedWeights(voice=0.35, text=0.35, deep=0.3), # 정서: 균형
            IndicatorType.OV: OptimizedWeights(voice=0.4, text=0.3, deep=0.3)    # 활력: 음성 중심
        }

        # RAG 사용 시 텍스트 가중치 증가
        if self.use_rag:
            for indicator in self.base_weights:
                weight = self.base_weights[indicator]
                # 텍스트 가중치 10% 증가
                self.base_weights[indicator] = OptimizedWeights(
                    voice=weight.voice * 0.9,
                    text=weight.text * 1.1,
                    deep=weight.deep
                )

        # 데이터 품질 기반 조정 계수
        self.quality_adjustments = {
            'voice': {
                'low_quality': 0.7,      # 품질 낮으면 가중치 감소
                'high_quality': 1.2,     # 품질 높으면 가중치 증가
                'min_duration': 10.0,    # 최소 10초
                'optimal_duration': 60.0 # 최적 60초
            },
            'text': {
                'low_quality': 0.8,
                'high_quality': 1.1,
                'min_words': 20,         # 최소 20단어
                'optimal_words': 100     # 최적 100단어
            },
            'deep': {
                'low_quality': 0.6,
                'high_quality': 1.3,
                'min_duration': 30.0,    # 최소 30초
                'optimal_duration': 120.0 # 최적 120초
            }
        }

        # 지표 간 상관관계 (연구 기반)
        self.correlations = {
            IndicatorType.DRI: {
                IndicatorType.SDI: 0.6,  # 우울-수면 상관관계
                IndicatorType.ES: 0.7,   # 우울-정서 안정성
                IndicatorType.OV: 0.8    # 우울-전반적 활력
            },
            IndicatorType.SDI: {
                IndicatorType.DRI: 0.6,
                IndicatorType.CFL: 0.3,  # 수면-인지 기능
                IndicatorType.OV: 0.6
            },
            IndicatorType.CFL: {
                IndicatorType.DRI: 0.4,  # 인지-우울
                IndicatorType.SDI: 0.3,
                IndicatorType.ES: 0.4    # 인지-정서 안정성
            }
        }

    def calculate_adaptive_weights(
        self,
        data_quality: DataQuality,
        user_profile: Optional[Dict] = None
    ) -> Dict[IndicatorType, OptimizedWeights]:
        """
        데이터 품질과 사용자 프로필 기반 적응형 가중치 계산

        Args:
            data_quality: 데이터 품질 정보
            user_profile: 사용자 프로필 (나이, 성별, 건강 상태 등)

        Returns:
            지표별 최적화된 가중치
        """
        adaptive_weights = {}

        for indicator, base_weight in self.base_weights.items():
            # 1. 데이터 품질 기반 조정
            quality_adjusted = self._adjust_for_quality(base_weight, data_quality)

            # 2. 사용자 프로필 기반 조정
            profile_adjusted = self._adjust_for_profile(quality_adjusted, indicator, user_profile)

            # 3. 지표 간 상관관계 고려
            correlation_adjusted = self._adjust_for_correlations(profile_adjusted, indicator)

            adaptive_weights[indicator] = correlation_adjusted

            logger.info(f"{indicator.value} 적응형 가중치: voice={correlation_adjusted.voice:.3f}, "
                       f"text={correlation_adjusted.text:.3f}, deep={correlation_adjusted.deep:.3f}")

        return adaptive_weights

    def _adjust_for_quality(
        self,
        base_weight: OptimizedWeights,
        data_quality: DataQuality
    ) -> OptimizedWeights:
        """데이터 품질 기반 가중치 조정"""

        # 음성 품질 조정
        voice_quality = data_quality.voice_quality
        voice_duration = data_quality.audio_duration

        if voice_quality < 0.5:
            voice_multiplier = self.quality_adjustments['voice']['low_quality']
        elif voice_quality > 0.8:
            voice_multiplier = self.quality_adjustments['voice']['high_quality']
        else:
            voice_multiplier = 1.0

        # 오디오 길이 기반 추가 조정
        if voice_duration < self.quality_adjustments['voice']['min_duration']:
            voice_multiplier *= 0.8  # 너무 짧으면 가중치 감소
        elif voice_duration > self.quality_adjustments['voice']['optimal_duration']:
            voice_multiplier *= 1.1  # 충분히 길면 가중치 증가

        # 텍스트 품질 조정
        text_quality = data_quality.text_quality
        text_length = data_quality.text_length

        if text_quality < 0.5:
            text_multiplier = self.quality_adjustments['text']['low_quality']
        elif text_quality > 0.8:
            text_multiplier = self.quality_adjustments['text']['high_quality']
        else:
            text_multiplier = 1.0

        # 텍스트 길이 기반 추가 조정
        if text_length < self.quality_adjustments['text']['min_words']:
            text_multiplier *= 0.7  # 너무 짧으면 가중치 감소
        elif text_length > self.quality_adjustments['text']['optimal_words']:
            text_multiplier *= 1.1  # 충분히 길면 가중치 증가

        # 딥러닝 품질 조정
        deep_quality = data_quality.deep_quality

        if deep_quality < 0.5:
            deep_multiplier = self.quality_adjustments['deep']['low_quality']
        elif deep_quality > 0.8:
            deep_multiplier = self.quality_adjustments['deep']['high_quality']
        else:
            deep_multiplier = 1.0

        # 오디오 길이 기반 딥러닝 조정
        if voice_duration < self.quality_adjustments['deep']['min_duration']:
            deep_multiplier *= 0.5  # 딥러닝은 더 긴 오디오 필요
        elif voice_duration > self.quality_adjustments['deep']['optimal_duration']:
            deep_multiplier *= 1.2

        return OptimizedWeights(
            voice=base_weight.voice * voice_multiplier,
            text=base_weight.text * text_multiplier,
            deep=base_weight.deep * deep_multiplier
        )

    def _adjust_for_profile(
        self,
        weight: OptimizedWeights,
        indicator: IndicatorType,
        user_profile: Optional[Dict]
    ) -> OptimizedWeights:
        """사용자 프로필 기반 가중치 조정"""

        if not user_profile:
            return weight

        adjusted_weight = OptimizedWeights(
            voice=weight.voice,
            text=weight.text,
            deep=weight.deep
        )

        # 시니어 정보 추출
        senior_info = user_profile.get('senior', {})
        age = senior_info.get('age', 0)
        gender = senior_info.get('gender', '')
        health_conditions = senior_info.get('health_conditions', [])

        # 나이 기반 조정
        if age > 75:
            # 고령자는 음성 변화가 더 뚜렷
            if indicator in [IndicatorType.DRI, IndicatorType.SDI]:
                adjusted_weight.voice *= 1.2
                adjusted_weight.text *= 0.9
        elif age < 65:
            # 상대적으로 젊은 시니어는 텍스트 분석이 더 효과적
            adjusted_weight.text *= 1.1
            adjusted_weight.voice *= 0.9

        # 성별 기반 조정
        if gender == 'female':
            # 여성은 감정 표현이 더 뚜렷
            if indicator == IndicatorType.ES:
                adjusted_weight.text *= 1.1
        elif gender == 'male':
            # 남성은 음성 변화가 더 뚜렷할 수 있음
            if indicator in [IndicatorType.DRI, IndicatorType.OV]:
                adjusted_weight.voice *= 1.1

        # 건강 상태 기반 조정
        if 'hearing_impairment' in health_conditions:
            # 청각 장애가 있으면 음성 분석 신뢰도 감소
            adjusted_weight.voice *= 0.8
            adjusted_weight.text *= 1.2

        if 'speech_disorder' in health_conditions:
            # 언어 장애가 있으면 텍스트 분석 신뢰도 감소
            adjusted_weight.text *= 0.7
            adjusted_weight.voice *= 1.3

        return adjusted_weight

    def _adjust_for_correlations(
        self,
        weight: OptimizedWeights,
        indicator: IndicatorType
    ) -> OptimizedWeights:
        """지표 간 상관관계 고려한 가중치 조정"""

        # 현재는 기본 가중치 유지
        # 향후 다른 지표 결과를 고려한 동적 조정 가능
        return weight

    def calculate_confidence(
        self,
        weights: Dict[IndicatorType, OptimizedWeights],
        data_quality: DataQuality
    ) -> Dict[IndicatorType, float]:
        """가중치 기반 신뢰도 계산"""

        confidence = {}

        for indicator, weight in weights.items():
            # 각 방법론의 신뢰도 계산
            voice_confidence = weight.voice * data_quality.voice_quality
            text_confidence = weight.text * data_quality.text_quality
            deep_confidence = weight.deep * data_quality.deep_quality

            # 전체 신뢰도 (가중 평균)
            total_confidence = voice_confidence + text_confidence + deep_confidence
            confidence[indicator] = min(total_confidence, 1.0)

            logger.info(f"{indicator.value} 신뢰도: {confidence[indicator]:.3f}")

        return confidence

    def get_recommended_analysis_methods(
        self,
        data_quality: DataQuality
    ) -> List[AnalysisMethod]:
        """데이터 품질 기반 권장 분석 방법론"""

        methods = []

        # 음성 분석 권장 조건
        if (data_quality.voice_quality > 0.6 and
            data_quality.audio_duration >= 10.0):
            methods.append(AnalysisMethod.VOICE)

        # 텍스트 분석 권장 조건
        if (data_quality.text_quality > 0.5 and
            data_quality.text_length >= 20):
            methods.append(AnalysisMethod.TEXT)

        # 딥러닝 분석 권장 조건
        if (data_quality.deep_quality > 0.7 and
            data_quality.audio_duration >= 30.0):
            methods.append(AnalysisMethod.DEEP)

        logger.info(f"권장 분석 방법: {[m.value for m in methods]}")

        return methods

    def validate_weights(self, weights: Dict[IndicatorType, OptimizedWeights]) -> Dict[str, Any]:
        """가중치 유효성 검증"""

        validation = {
            'is_valid': True,
            'issues': [],
            'warnings': []
        }

        for indicator, weight in weights.items():
            # 가중치 합이 1.0에 가까운지 확인
            total = weight.voice + weight.text + weight.deep
            if abs(total - 1.0) > 0.01:
                validation['is_valid'] = False
                validation['issues'].append(f"{indicator.value} 가중치 합이 1.0이 아님: {total:.3f}")

            # 개별 가중치가 유효 범위인지 확인
            if not (0 <= weight.voice <= 1):
                validation['warnings'].append(f"{indicator.value} voice 가중치가 범위를 벗어남: {weight.voice}")

            if not (0 <= weight.text <= 1):
                validation['warnings'].append(f"{indicator.value} text 가중치가 범위를 벗어남: {weight.text}")

            if not (0 <= weight.deep <= 1):
                validation['warnings'].append(f"{indicator.value} deep 가중치가 범위를 벗어남: {weight.deep}")

        return validation