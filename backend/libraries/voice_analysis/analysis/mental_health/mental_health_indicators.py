"""
노인 정신건강 5대 지표 계산 시스템
Phase별 가중치 시스템 포함
전문가 평가 통합 지원
"""

import numpy as np
import logging
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass
from enum import Enum
from datetime import datetime

logger = logging.getLogger(__name__)


class Phase(Enum):
    """구현 단계"""
    MVP = "mvp"  # Librosa + GPT-4o
    ENHANCED = "enhanced"  # + SincNet
    OPTIMIZED = "optimized"  # Fine-tuned
    CLINICAL = "clinical"  # 임상 검증 단계


class IndicatorType(Enum):
    """5대 핵심 지표"""
    DRI = "Depression Risk Index"  # 우울 위험도
    SDI = "Sleep Disorder Index"  # 수면 장애 지수
    CFL = "Cognitive Function Level"  # 인지 기능 수준
    ES = "Emotional Stability"  # 감정 안정성
    OV = "Overall Vitality"  # 전반적 활력도


class DataSource(Enum):
    """데이터 출처"""
    AI_GENERATED = "ai_generated"  # AI 생성 (개발용)
    EXPERT_VALIDATED = "expert_validated"  # 전문가 검증됨
    EXPERT_LABELED = "expert_labeled"  # 전문가 레이블링
    CLINICAL_VALIDATED = "clinical_validated"  # 임상 검증됨
    SYNTHETIC = "synthetic"  # 합성 데이터 (테스트용)


@dataclass
class IndicatorWeights:
    """지표별 가중치"""
    librosa: float
    gpt4o: float
    sincnet: float = 0.0  # Phase 2부터


@dataclass
class IndicatorResult:
    """지표 계산 결과"""
    value: float
    level: str  # low, medium, high
    confidence: float
    source: DataSource
    timestamp: datetime
    requires_validation: bool
    development_only: bool = True
    expert_notes: Optional[str] = None
    

class MentalHealthIndicatorCalculator:
    """정신건강 지표 계산기"""
    
    def __init__(self, phase: Phase = Phase.MVP, data_source: DataSource = DataSource.AI_GENERATED):
        """
        초기화
        
        Args:
            phase: 구현 단계
            data_source: 데이터 출처
        """
        self.phase = phase
        self.data_source = data_source
        self.weights = self._initialize_weights()
        
        # 지표별 임계값
        self.thresholds = {
            IndicatorType.DRI: {'low': 0.3, 'medium': 0.6, 'high': 0.8},
            IndicatorType.SDI: {'low': 0.3, 'medium': 0.6, 'high': 0.8},
            IndicatorType.CFL: {'low': 0.4, 'medium': 0.7, 'high': 0.9},  # 역방향
            IndicatorType.ES: {'low': 0.4, 'medium': 0.7, 'high': 0.9},  # 역방향
            IndicatorType.OV: {'low': 0.4, 'medium': 0.7, 'high': 0.9}  # 역방향
        }
    
    def _initialize_weights(self) -> Dict[IndicatorType, IndicatorWeights]:
        """단계별 가중치 초기화"""
        weights = {}
        
        if self.phase == Phase.MVP:
            # Phase 1: Librosa + GPT-4o만 사용
            weights[IndicatorType.DRI] = IndicatorWeights(librosa=0.4, gpt4o=0.6, sincnet=0.0)
            weights[IndicatorType.SDI] = IndicatorWeights(librosa=0.4, gpt4o=0.6, sincnet=0.0)
            weights[IndicatorType.CFL] = IndicatorWeights(librosa=0.15, gpt4o=0.85, sincnet=0.0)
            weights[IndicatorType.ES] = IndicatorWeights(librosa=0.4, gpt4o=0.6, sincnet=0.0)
            weights[IndicatorType.OV] = IndicatorWeights(librosa=0.5, gpt4o=0.5, sincnet=0.0)
            
        elif self.phase == Phase.ENHANCED:
            # Phase 2: SincNet 추가
            weights[IndicatorType.DRI] = IndicatorWeights(librosa=0.2, gpt4o=0.3, sincnet=0.5)
            weights[IndicatorType.SDI] = IndicatorWeights(librosa=0.25, gpt4o=0.25, sincnet=0.5)
            weights[IndicatorType.CFL] = IndicatorWeights(librosa=0.15, gpt4o=0.85, sincnet=0.0)  # SincNet 미지원
            weights[IndicatorType.ES] = IndicatorWeights(librosa=0.3, gpt4o=0.5, sincnet=0.2)
            weights[IndicatorType.OV] = IndicatorWeights(librosa=0.4, gpt4o=0.4, sincnet=0.2)
            
        else:  # Phase.OPTIMIZED
            # Phase 3: 최적화된 가중치
            weights[IndicatorType.DRI] = IndicatorWeights(librosa=0.15, gpt4o=0.25, sincnet=0.6)
            weights[IndicatorType.SDI] = IndicatorWeights(librosa=0.2, gpt4o=0.2, sincnet=0.6)
            weights[IndicatorType.CFL] = IndicatorWeights(librosa=0.1, gpt4o=0.9, sincnet=0.0)
            weights[IndicatorType.ES] = IndicatorWeights(librosa=0.25, gpt4o=0.45, sincnet=0.3)
            weights[IndicatorType.OV] = IndicatorWeights(librosa=0.35, gpt4o=0.35, sincnet=0.3)
        
        return weights
    
    def calculate_dri(
        self,
        librosa_features: Dict[str, float],
        gpt4o_analysis: Optional[Dict[str, float]] = None,
        sincnet_result: Optional[float] = None
    ) -> Tuple[float, Dict[str, Any]]:
        """
        우울 위험도 (Depression Risk Index) 계산
        
        측정 요소:
        - 말속도 저하
        - 에너지 감소
        - 침묵 증가
        - 부정적 감정
        
        Returns:
            (DRI 점수 0-1, 상세 정보)
        """
        weights = self.weights[IndicatorType.DRI]
        components = {}
        
        # Librosa 기반 점수
        librosa_score = 0.0
        if librosa_features:
            # 말속도 저하
            speech_rate = librosa_features.get('speech_rate', 3.0)
            if speech_rate < 2.5:
                librosa_score += 0.3
            elif speech_rate < 3.0:
                librosa_score += 0.15
            
            # 에너지 감소
            energy = librosa_features.get('energy_mean', 0.02)
            if energy < 0.015:
                librosa_score += 0.35
            elif energy < 0.02:
                librosa_score += 0.2
            
            # 침묵 증가
            pause_ratio = librosa_features.get('pause_ratio', 0.3)
            if pause_ratio > 0.5:
                librosa_score += 0.35
            elif pause_ratio > 0.4:
                librosa_score += 0.2
            
            components['librosa'] = min(librosa_score, 1.0)
        else:
            logger.warning("DRI: Librosa 분석 결과 없음")
            components['librosa'] = None
        
        # GPT-4o 기반 점수 (API 호출 불가시 스텁)
        if gpt4o_analysis:
            components['gpt4o'] = gpt4o_analysis.get('depression_score', 0.5)
        else:
            logger.warning("DRI: GPT-4o 분석 결과 없음")
            components['gpt4o'] = None
        
        # SincNet 기반 점수 (Phase 2+)
        if self.phase != Phase.MVP and sincnet_result is not None:
            components['sincnet'] = sincnet_result
        else:
            components['sincnet'] = 0.0
        
        # 가중 평균 계산
        total_score = (
            components['librosa'] * weights.librosa +
            components['gpt4o'] * weights.gpt4o +
            components['sincnet'] * weights.sincnet
        )
        
        # 위험 수준 판정
        risk_level = self._get_risk_level(total_score, IndicatorType.DRI)
        
        # 신뢰도 계산
        confidence = self._calculate_confidence(components)
        
        # 결과 생성
        result = IndicatorResult(
            value=total_score,
            level=risk_level,
            confidence=confidence,
            source=self.data_source,
            timestamp=datetime.now(),
            requires_validation=(self.data_source == DataSource.AI_GENERATED),
            development_only=(self.phase != Phase.CLINICAL)
        )
        
        return total_score, {
            'components': components,
            'weights': {'librosa': weights.librosa, 'gpt4o': weights.gpt4o, 'sincnet': weights.sincnet},
            'risk_level': risk_level,
            'interpretation': self._interpret_dri(total_score, risk_level),
            'result_metadata': result
        }
    
    def calculate_sdi(
        self,
        librosa_features: Dict[str, float],
        gpt4o_analysis: Optional[Dict[str, float]] = None,
        sincnet_result: Optional[float] = None
    ) -> Tuple[float, Dict[str, Any]]:
        """
        수면 장애 지수 (Sleep Disorder Index) 계산
        
        측정 요소:
        - 피로한 음성
        - 응답 지연
        - 집중력 저하
        
        Returns:
            (SDI 점수 0-1, 상세 정보)
        """
        weights = self.weights[IndicatorType.SDI]
        components = {}
        
        # Librosa 기반 점수
        librosa_score = 0.0
        if librosa_features:
            # 에너지 레벨 (피로)
            energy = librosa_features.get('energy_mean', 0.02)
            if energy < 0.01:
                librosa_score += 0.5
            elif energy < 0.015:
                librosa_score += 0.3
            
            # 음성 변동성 감소 (피로)
            energy_std = librosa_features.get('energy_std', 0.01)
            if energy_std < 0.005:
                librosa_score += 0.3
            
            # 느린 말속도 (피로)
            speech_rate = librosa_features.get('speech_rate', 3.0)
            if speech_rate < 2.0:
                librosa_score += 0.2
            
            components['librosa'] = min(librosa_score, 1.0)
        else:
            logger.warning("SDI: Librosa 분석 결과 없음")
            components['librosa'] = None
        
        # GPT-4o 기반 점수
        if gpt4o_analysis:
            components['gpt4o'] = gpt4o_analysis.get('fatigue_score', 0.5)
        else:
            logger.warning("SDI: GPT-4o 분석 결과 없음")
            components['gpt4o'] = None
        
        # SincNet 기반 점수
        if self.phase != Phase.MVP and sincnet_result is not None:
            components['sincnet'] = sincnet_result
        else:
            components['sincnet'] = 0.0
        
        # 가중 평균
        total_score = (
            components['librosa'] * weights.librosa +
            components['gpt4o'] * weights.gpt4o +
            components['sincnet'] * weights.sincnet
        )
        
        risk_level = self._get_risk_level(total_score, IndicatorType.SDI)
        
        return total_score, {
            'components': components,
            'weights': {'librosa': weights.librosa, 'gpt4o': weights.gpt4o, 'sincnet': weights.sincnet},
            'risk_level': risk_level,
            'interpretation': self._interpret_sdi(total_score, risk_level)
        }
    
    def calculate_cfl(
        self,
        librosa_features: Dict[str, float],
        gpt4o_analysis: Optional[Dict[str, float]] = None
    ) -> Tuple[float, Dict[str, Any]]:
        """
        인지 기능 수준 (Cognitive Function Level) 계산
        
        측정 요소:
        - 문장 완성도
        - 논리 일관성
        - 단어 찾기
        - 주제 유지
        
        Returns:
            (CFL 점수 0-1, 상세 정보)
        """
        weights = self.weights[IndicatorType.CFL]
        components = {}
        
        # Librosa 기반 점수 (제한적)
        librosa_score = 0.0
        if librosa_features:
            # 말속도 일관성
            speech_rate = librosa_features.get('speech_rate', 3.0)
            if 2.5 <= speech_rate <= 4.0:
                librosa_score += 0.2
            
            # 침묵 비율 (너무 많으면 인지 저하)
            pause_ratio = librosa_features.get('pause_ratio', 0.3)
            if pause_ratio < 0.4:
                librosa_score += 0.3
            
            components['librosa'] = min(librosa_score, 1.0)
        else:
            logger.warning("CFL: Librosa 분석 결과 없음")
            components['librosa'] = None
        
        # GPT-4o 기반 점수 (주요)
        if gpt4o_analysis:
            components['gpt4o'] = gpt4o_analysis.get('cognitive_score', 0.7)
        else:
            logger.warning("CFL: GPT-4o 분석 결과 없음")
            components['gpt4o'] = None
        
        # 가중 평균 (SincNet 미지원)
        total_score = (
            components['librosa'] * weights.librosa +
            components['gpt4o'] * weights.gpt4o
        )
        
        risk_level = self._get_risk_level(total_score, IndicatorType.CFL, reverse=True)
        
        return total_score, {
            'components': components,
            'weights': {'librosa': weights.librosa, 'gpt4o': weights.gpt4o},
            'risk_level': risk_level,
            'interpretation': self._interpret_cfl(total_score, risk_level)
        }
    
    def calculate_es(
        self,
        librosa_features: Dict[str, float],
        gpt4o_analysis: Optional[Dict[str, float]] = None,
        sincnet_result: Optional[float] = None
    ) -> Tuple[float, Dict[str, Any]]:
        """
        감정 안정성 (Emotional Stability) 계산
        
        측정 요소:
        - 감정 변동성
        - 음성-텍스트 일치도
        - 톤 안정성
        
        Returns:
            (ES 점수 0-1, 상세 정보)
        """
        weights = self.weights[IndicatorType.ES]
        components = {}
        
        # Librosa 기반 점수
        librosa_score = None
        if librosa_features:
            # 피치 안정성
            pitch_std = librosa_features.get('pitch_std', 20.0)
            if pitch_std < 15:
                librosa_score += 0.25
            elif pitch_std < 25:
                librosa_score += 0.15
            
            # 에너지 안정성
            energy_std = librosa_features.get('energy_std', 0.01)
            if energy_std < 0.02:
                librosa_score += 0.25
            
            components['librosa'] = min(librosa_score, 1.0)
        else:
            logger.warning("ES: Librosa 분석 결과 없음")
            components['librosa'] = None
        
        # GPT-4o 기반 점수
        if gpt4o_analysis:
            components['gpt4o'] = gpt4o_analysis.get('emotion_stability', 0.7)
        else:
            logger.warning("ES: GPT-4o 분석 결과 없음")
            components['gpt4o'] = None
        
        # SincNet 기반 점수 (역산)
        if self.phase != Phase.MVP and sincnet_result is not None:
            # 우울/불면이 낮으면 감정 안정성 높음
            components['sincnet'] = 1.0 - sincnet_result
        else:
            components['sincnet'] = 0.0
        
        # 가중 평균
        total_score = (
            components['librosa'] * weights.librosa +
            components['gpt4o'] * weights.gpt4o +
            components['sincnet'] * weights.sincnet
        )
        
        risk_level = self._get_risk_level(total_score, IndicatorType.ES, reverse=True)
        
        return total_score, {
            'components': components,
            'weights': {'librosa': weights.librosa, 'gpt4o': weights.gpt4o, 'sincnet': weights.sincnet},
            'risk_level': risk_level,
            'interpretation': self._interpret_es(total_score, risk_level)
        }
    
    def calculate_ov(
        self,
        librosa_features: Dict[str, float],
        gpt4o_analysis: Optional[Dict[str, float]] = None,
        health_data: Optional[Dict[str, float]] = None
    ) -> Tuple[float, Dict[str, Any]]:
        """
        전반적 활력도 (Overall Vitality) 계산
        
        측정 요소:
        - 음성 에너지
        - 참여도
        - 긍정성
        - 건강 상태
        
        Returns:
            (OV 점수 0-1, 상세 정보)
        """
        weights = self.weights[IndicatorType.OV]
        components = {}
        
        # Librosa 기반 점수
        librosa_score = 0.0
        if librosa_features:
            # 음성 에너지
            energy = librosa_features.get('energy_mean', 0.02)
            librosa_score += min(energy * 30, 0.5)  # 정규화
            
            # 말속도 활력
            speech_rate = librosa_features.get('speech_rate', 3.0)
            if speech_rate > 3.0:
                librosa_score += 0.3
            elif speech_rate > 2.5:
                librosa_score += 0.2
            
            # 음성 활동 비율
            voice_activity = 1 - librosa_features.get('pause_ratio', 0.3)
            librosa_score += voice_activity * 0.2
            
            components['librosa'] = min(librosa_score, 1.0)
        else:
            logger.warning("OV: Librosa 분석 결과 없음")
            components['librosa'] = None
        
        # GPT-4o 기반 점수
        if gpt4o_analysis:
            components['gpt4o'] = gpt4o_analysis.get('engagement_score', 0.6)
        else:
            components['gpt4o'] = 0.6
        
        # 건강 데이터 (추가 입력)
        if health_data:
            components['health'] = health_data.get('vitality', 0.7)
        else:
            logger.warning("OV: 건강 데이터 없음")
            components['health'] = None
        
        # 가중 평균 (건강 데이터는 40% 가중치)
        total_score = (
            components['librosa'] * weights.librosa * 0.6 +
            components['gpt4o'] * weights.gpt4o * 0.6 +
            components['health'] * 0.4
        )
        
        risk_level = self._get_risk_level(total_score, IndicatorType.OV, reverse=True)
        
        return total_score, {
            'components': components,
            'weights': {'librosa': weights.librosa, 'gpt4o': weights.gpt4o, 'health': 0.4},
            'risk_level': risk_level,
            'interpretation': self._interpret_ov(total_score, risk_level)
        }
    
    def calculate_all_indicators(
        self,
        librosa_features: Dict[str, float],
        gpt4o_analysis: Optional[Dict[str, float]] = None,
        sincnet_results: Optional[Dict[str, float]] = None,
        health_data: Optional[Dict[str, float]] = None
    ) -> Dict[IndicatorType, Tuple[float, Dict[str, Any]]]:
        """
        모든 지표 계산
        
        Returns:
            지표별 점수와 상세 정보
        """
        results = {}
        
        # SincNet 결과 파싱
        sincnet_depression = sincnet_results.get('depression', None) if sincnet_results else None
        sincnet_insomnia = sincnet_results.get('insomnia', None) if sincnet_results else None
        
        # 각 지표 계산
        results[IndicatorType.DRI] = self.calculate_dri(librosa_features, gpt4o_analysis, sincnet_depression)
        results[IndicatorType.SDI] = self.calculate_sdi(librosa_features, gpt4o_analysis, sincnet_insomnia)
        results[IndicatorType.CFL] = self.calculate_cfl(librosa_features, gpt4o_analysis)
        results[IndicatorType.ES] = self.calculate_es(librosa_features, gpt4o_analysis, sincnet_depression)
        results[IndicatorType.OV] = self.calculate_ov(librosa_features, gpt4o_analysis, health_data)
        
        return results
    
    def _get_risk_level(self, score: Optional[float], indicator: IndicatorType, reverse: bool = False) -> str:
        """위험 수준 판정"""
        if score is None:
            return 'unknown'
            
        thresholds = self.thresholds[indicator]
        
        if reverse:  # CFL, ES, OV는 높을수록 좋음
            if score >= thresholds['high']:
                return 'good'
            elif score >= thresholds['medium']:
                return 'normal'
            elif score >= thresholds['low']:
                return 'caution'
            else:
                return 'warning'
        else:  # DRI, SDI는 낮을수록 좋음
            if score <= thresholds['low']:
                return 'good'
            elif score <= thresholds['medium']:
                return 'caution'
            elif score <= thresholds['high']:
                return 'warning'
            else:
                return 'critical'
    
    def _interpret_dri(self, score: Optional[float], risk_level: str) -> str:
        """DRI 해석"""
        interpretations = {
            'good': '우울 위험이 낮습니다. 정신건강이 양호합니다.',
            'caution': '경미한 우울 증상이 관찰됩니다. 주의 관찰이 필요합니다.',
            'warning': '중등도 우울 위험이 있습니다. 전문가 상담을 권장합니다.',
            'critical': '높은 우울 위험이 감지됩니다. 즉시 전문가 진료가 필요합니다.',
            'unknown': '분석 데이터 부족으로 평가할 수 없습니다.'
        }
        return interpretations.get(risk_level, '평가 중')
    
    def _interpret_sdi(self, score: Optional[float], risk_level: str) -> str:
        """SDI 해석"""
        interpretations = {
            'good': '수면 상태가 양호합니다.',
            'caution': '가벼운 수면 문제가 있을 수 있습니다.',
            'warning': '수면 장애 가능성이 있습니다. 수면 습관 개선이 필요합니다.',
            'critical': '심각한 수면 문제가 의심됩니다. 수면 클리닉 방문을 권장합니다.',
            'unknown': '분석 데이터 부족으로 평가할 수 없습니다.'
        }
        return interpretations.get(risk_level, '평가 중')
    
    def _interpret_cfl(self, score: Optional[float], risk_level: str) -> str:
        """CFL 해석"""
        interpretations = {
            'good': '인지 기능이 정상입니다.',
            'normal': '인지 기능이 대체로 양호합니다.',
            'caution': '경미한 인지 저하가 관찰됩니다.',
            'warning': '인지 기능 검사가 필요할 수 있습니다.',
            'unknown': '분석 데이터 부족으로 평가할 수 없습니다.'
        }
        return interpretations.get(risk_level, '평가 중')
    
    def _interpret_es(self, score: Optional[float], risk_level: str) -> str:
        """ES 해석"""
        interpretations = {
            'good': '감정 상태가 안정적입니다.',
            'normal': '감정 변화가 정상 범위입니다.',
            'caution': '감정 기복이 다소 있습니다.',
            'warning': '감정 조절에 어려움이 있을 수 있습니다.',
            'unknown': '분석 데이터 부족으로 평가할 수 없습니다.'
        }
        return interpretations.get(risk_level, '평가 중')
    
    def _interpret_ov(self, score: Optional[float], risk_level: str) -> str:
        """OV 해석"""
        interpretations = {
            'good': '전반적으로 활력이 넘칩니다.',
            'normal': '일상 활동에 적절한 에너지를 보입니다.',
            'caution': '활력이 다소 저하되어 있습니다.',
            'warning': '전반적인 활력 저하가 관찰됩니다.',
            'unknown': '분석 데이터 부족으로 평가할 수 없습니다.'
        }
        return interpretations.get(risk_level, '평가 중')
    
    def _calculate_confidence(self, components: Dict[str, Any]) -> float:
        """신뢰도 계산"""
        # 사용 가능한 컴포넌트 수에 따른 신뢰도
        available_components = sum(1 for v in components.values() if v is not None and v > 0)
        total_components = len(components)
        
        base_confidence = available_components / total_components if total_components > 0 else 0
        
        # 데이터 출처에 따른 조정
        source_multiplier = {
            DataSource.CLINICAL_VALIDATED: 1.0,
            DataSource.EXPERT_LABELED: 0.9,
            DataSource.EXPERT_VALIDATED: 0.8,
            DataSource.AI_GENERATED: 0.6,
            DataSource.SYNTHETIC: 0.4
        }
        
        return min(1.0, base_confidence * source_multiplier.get(self.data_source, 0.5))