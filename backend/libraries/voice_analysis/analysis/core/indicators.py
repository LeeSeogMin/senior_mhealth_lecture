"""
5대 정신건강 지표 계산 및 통합 모듈
DRI, SDI, CFL, ES, OV 지표 계산 및 검증
"""

import numpy as np
import logging
from typing import Dict, Any, Optional, List, Tuple
from dataclasses import dataclass
from datetime import datetime

logger = logging.getLogger(__name__)

@dataclass
class MentalHealthIndicators:
    """5대 정신건강 지표"""
    DRI: float  # Depression Risk Indicator (우울 위험도) 0-1
    SDI: float  # Sleep Disorder Indicator (수면 장애 지표) 0-1
    CFL: float  # Cognitive Function Level (인지 기능 수준) 0-1
    ES: float   # Emotional Stability (정서적 안정성) 0-1
    OV: float   # Overall Vitality (전반적 활력도) 0-1
    
    def to_dict(self) -> Dict[str, float]:
        return {
            'DRI': self.DRI,
            'SDI': self.SDI,
            'CFL': self.CFL,
            'ES': self.ES,
            'OV': self.OV
        }
    
    def get_risk_level(self) -> str:
        """전체 위험도 수준 반환"""
        avg_score = (self.DRI + self.SDI + self.CFL + self.ES + self.OV) / 5
        
        if avg_score >= 0.7:
            return 'low'  # 낮은 위험
        elif avg_score >= 0.4:
            return 'moderate'  # 중간 위험
        else:
            return 'high'  # 높은 위험

class IndicatorCalculator:
    """지표 계산 및 통합 클래스 (개선된 버전)"""
    
    def __init__(self):
        # 가중치 설정 (3가지 분석 방법론)
        self.weights = {
            'librosa': 0.3,    # Librosa 음성 분석
            'gpt4o': 0.4,      # GPT-4o 텍스트 분석
            'sincnet': 0.3     # SincNet 딥러닝 분석
        }
        
        # 지표별 임계값 (정확한 위험도 판정)
        self.thresholds = {
            'DRI': {'critical': 0.2, 'high': 0.4, 'moderate': 0.6, 'low': 0.8},
            'SDI': {'critical': 0.2, 'high': 0.4, 'moderate': 0.6, 'low': 0.8},
            'CFL': {'critical': 0.2, 'high': 0.4, 'moderate': 0.6, 'low': 0.8},
            'ES': {'critical': 0.2, 'high': 0.4, 'moderate': 0.6, 'low': 0.8},
            'OV': {'critical': 0.2, 'high': 0.4, 'moderate': 0.6, 'low': 0.8}
        }
        
        # 지표 간 상관관계 매트릭스
        self.correlation_matrix = {
            'DRI': {'SDI': 0.6, 'CFL': 0.4, 'ES': 0.7, 'OV': 0.8},
            'SDI': {'DRI': 0.6, 'CFL': 0.3, 'ES': 0.5, 'OV': 0.6},
            'CFL': {'DRI': 0.4, 'SDI': 0.3, 'ES': 0.4, 'OV': 0.5},
            'ES': {'DRI': 0.7, 'SDI': 0.5, 'CFL': 0.4, 'OV': 0.7},
            'OV': {'DRI': 0.8, 'SDI': 0.6, 'CFL': 0.5, 'ES': 0.7}
        }
    
    def calculate(
        self,
        voice_features: Optional[Dict] = None,
        text_analysis: Optional[Dict] = None,
        sincnet_results: Optional[Dict] = None,
        adaptive_weights: Optional[Dict] = None
    ) -> MentalHealthIndicators:
        """
        통합 지표 계산

        Args:
            voice_features: 음성 분석 결과
            text_analysis: 텍스트 분석 결과
            sincnet_results: SincNet 분석 결과
            adaptive_weights: 적응형 가중치 (옵션)

        Returns:
            5대 정신건강 지표
        """

        # 적응형 가중치 사용 여부 결정
        use_adaptive = adaptive_weights is not None

        if use_adaptive:
            logger.info("적응형 가중치 모드로 지표 계산")
            # 적응형 가중치를 사용하여 지표별로 계산
            return self._calculate_with_adaptive_weights(
                voice_features, text_analysis, sincnet_results, adaptive_weights
            )
        else:
            logger.info("고정 가중치 모드로 지표 계산")

        indicators = {
            'DRI': [],
            'SDI': [],
            'CFL': [],
            'ES': [],
            'OV': []
        }

        weights = []
        
        # Librosa 음성 기반 지표 계산
        if voice_features:
            librosa_indicators = self._calculate_librosa_indicators(voice_features)
            for key in indicators:
                indicators[key].append(librosa_indicators.get(key, 0.5))
            weights.append(self.weights['librosa'])
        
        # GPT-4o 텍스트 기반 지표 계산
        if text_analysis:
            gpt4o_indicators = self._extract_gpt4o_indicators(text_analysis)
            for key in indicators:
                indicators[key].append(gpt4o_indicators.get(key, 0.5))
            weights.append(self.weights['gpt4o'])
        
        # SincNet 딥러닝 기반 지표 계산
        if sincnet_results:
            sincnet_indicators = self._calculate_sincnet_indicators(sincnet_results)
            for key in indicators:
                indicators[key].append(sincnet_indicators.get(key, 0.5))
            weights.append(self.weights['sincnet'])
        
        # 가중 평균 계산
        final_indicators = {}
        for key in indicators:
            if indicators[key] and weights:
                # 정규화된 가중치
                norm_weights = np.array(weights) / sum(weights)
                final_indicators[key] = float(np.average(indicators[key], weights=norm_weights))
            else:
                final_indicators[key] = 0.5  # 기본값
        
        # 검증 및 보정
        final_indicators = self._validate_and_adjust(final_indicators)
        
        return MentalHealthIndicators(**final_indicators)
    
    def _calculate_librosa_indicators(self, features: Dict) -> Dict[str, float]:
        """Librosa 음성 특징으로부터 지표 계산 (개선된 버전)"""
        
        indicators = {}
        
        # DRI (우울 위험도) - 피치, 에너지, 발화 속도 기반
        pitch_score = self._normalize_value(features.get('pitch_mean', 150), 100, 200)
        energy_score = self._normalize_value(features.get('energy_mean', 0.1), 0.01, 0.2)
        rate_score = self._normalize_value(features.get('speaking_rate', 3), 2, 4)
        
        indicators['DRI'] = (pitch_score * 0.3 + energy_score * 0.4 + rate_score * 0.3)
        
        # SDI (수면 장애) - 음성 피로도, 떨림 기반
        tremor_score = 1 - self._normalize_value(features.get('tremor_amplitude', 0), 0, 0.1)
        clarity_score = features.get('voice_clarity', 0.5)
        
        indicators['SDI'] = (tremor_score * 0.5 + clarity_score * 0.5)
        
        # CFL (인지 기능) - 발화 일관성, 휴지 비율 기반
        pause_score = 1 - self._normalize_value(features.get('pause_ratio', 0.3), 0, 0.6)
        zcr_score = self._normalize_value(features.get('zcr_mean', 0.05), 0.02, 0.08)
        
        indicators['CFL'] = (pause_score * 0.6 + zcr_score * 0.4)
        
        # ES (정서적 안정성) - 피치 변동성, 에너지 변동성 기반
        pitch_std_score = 1 - self._normalize_value(features.get('pitch_std', 30), 0, 60)
        energy_std_score = 1 - self._normalize_value(features.get('energy_std', 0.05), 0, 0.1)
        
        indicators['ES'] = (pitch_std_score * 0.5 + energy_std_score * 0.5)
        
        # OV (전반적 활력도) - 종합 점수 (다른 지표들이 모두 계산된 후에 계산)
        indicators['OV'] = np.mean([
            indicators['DRI'],
            indicators['SDI'],
            indicators['CFL'],
            indicators['ES']
        ])
        
        return indicators
    
    def _extract_gpt4o_indicators(self, analysis: Dict) -> Dict[str, float]:
        """GPT-4o 텍스트 분석 결과에서 지표 추출 (개선된 버전)"""
        
        # GPT-4o 분석 결과에서 직접 추출
        if 'analysis' in analysis and 'indicators' in analysis['analysis']:
            return analysis['analysis']['indicators']
        
        # 분석 실패 시 None 반환
        return {
            'DRI': None,
            'SDI': None,
            'CFL': None,
            'ES': None,
            'OV': None
        }
    
    def _calculate_sincnet_indicators(self, results: Dict) -> Dict[str, float]:
        """SincNet 결과로부터 지표 계산"""
        
        indicators = {}
        
        # SincNet은 주로 우울과 수면 장애 탐지에 특화
        depression_score = results.get('depression_probability', 0.5)
        insomnia_score = results.get('insomnia_probability', 0.5)

        # None 값 처리 - 모델을 사용할 수 없는 경우 기본값 사용
        if depression_score is None:
            depression_score = 0.5
        if insomnia_score is None:
            insomnia_score = 0.5

        # DRI와 SDI는 SincNet 결과 직접 반영
        indicators['DRI'] = 1 - depression_score  # 확률의 역수
        indicators['SDI'] = 1 - insomnia_score
        
        # 나머지 지표는 간접 추정
        indicators['CFL'] = 0.5 + (indicators['DRI'] - 0.5) * 0.3
        indicators['ES'] = (indicators['DRI'] + indicators['SDI']) / 2
        indicators['OV'] = np.mean([indicators['DRI'], indicators['SDI']]) * 0.8 + 0.1
        
        return indicators
    
    def _normalize_value(self, value: float, min_val: float, max_val: float) -> float:
        """값을 0-1 범위로 정규화"""
        if max_val == min_val:
            return 0.5
        
        normalized = (value - min_val) / (max_val - min_val)
        return float(np.clip(normalized, 0, 1))
    
    def _validate_and_adjust(self, indicators: Dict[str, float]) -> Dict[str, float]:
        """지표 검증 및 보정 (개선된 상관관계 적용)"""
        
        # 범위 검증 (0-1)
        for key in indicators:
            indicators[key] = float(np.clip(indicators[key], 0, 1))
        
        # 상호 일관성 검증 (상관관계 매트릭스 기반)
        for key1 in indicators:
            for key2, correlation in self.correlation_matrix.get(key1, {}).items():
                if key2 in indicators:
                    # 높은 상관관계가 있는 지표들 간의 일관성 유지
                    if correlation > 0.6:
                        diff = abs(indicators[key1] - indicators[key2])
                        if diff > 0.4:  # 너무 큰 차이가 나면 조정
                            avg = (indicators[key1] + indicators[key2]) / 2
                            indicators[key1] = indicators[key1] * 0.7 + avg * 0.3
                            indicators[key2] = indicators[key2] * 0.7 + avg * 0.3
        
        # OV (전반적 활력도)는 다른 지표들의 가중 평균으로 재계산
        indicators['OV'] = (
            indicators['DRI'] * 0.3 +
            indicators['SDI'] * 0.2 +
            indicators['CFL'] * 0.2 +
            indicators['ES'] * 0.3
        )
        
        return indicators
    
    def get_indicator_level(self, value: float, indicator_type: str) -> str:
        """지표 값에 대한 위험 수준 반환"""
        thresholds = self.thresholds.get(indicator_type, self.thresholds['OV'])
        
        if value < thresholds['critical']:
            return 'critical'
        elif value < thresholds['high']:
            return 'high'
        elif value < thresholds['moderate']:
            return 'moderate'
        elif value < thresholds['low']:
            return 'low'
        else:
            return 'normal'
    
    def calculate_risk_scores(self, indicators: MentalHealthIndicators) -> Dict[str, Any]:
        """위험도 점수 계산"""
        
        risk_scores = {}
        
        # 개별 지표 위험도
        for key in ['DRI', 'SDI', 'CFL', 'ES', 'OV']:
            value = getattr(indicators, key)
            if value < self.thresholds[key]['high']:
                risk_scores[key] = 'high'
            elif value < self.thresholds[key]['moderate']:
                risk_scores[key] = 'moderate'
            else:
                risk_scores[key] = 'low'
        
        # 종합 위험도
        high_risk_count = sum(1 for v in risk_scores.values() if v == 'high')
        moderate_risk_count = sum(1 for v in risk_scores.values() if v == 'moderate')
        
        if high_risk_count >= 2:
            overall_risk = 'high'
        elif high_risk_count >= 1 or moderate_risk_count >= 3:
            overall_risk = 'moderate'
        else:
            overall_risk = 'low'
        
        return {
            'individual_risks': risk_scores,
            'overall_risk': overall_risk,
            'high_risk_indicators': [k for k, v in risk_scores.items() if v == 'high'],
            'recommendations': self._generate_recommendations(risk_scores, overall_risk)
        }
    
    def _generate_recommendations(self, risk_scores: Dict, overall_risk: str) -> List[str]:
        """위험도 기반 권고사항 생성"""
        
        recommendations = []
        
        if overall_risk == 'high':
            recommendations.append("즉시 전문의 상담을 권장합니다.")
        elif overall_risk == 'moderate':
            recommendations.append("정기적인 모니터링이 필요합니다.")
        
        # 개별 지표별 권고사항
        if risk_scores.get('DRI') in ['high', 'moderate']:
            recommendations.append("우울증 선별 검사를 받아보시기 바랍니다.")
        
        if risk_scores.get('SDI') in ['high', 'moderate']:
            recommendations.append("수면 패턴 개선을 위한 수면 위생 교육이 필요합니다.")
        
        if risk_scores.get('CFL') in ['high', 'moderate']:
            recommendations.append("인지 기능 평가 및 인지 훈련 프로그램 참여를 고려하세요.")
        
        if risk_scores.get('ES') in ['high', 'moderate']:
            recommendations.append("스트레스 관리 및 정서 조절 프로그램이 도움될 수 있습니다.")
        
        if risk_scores.get('OV') in ['high', 'moderate']:
            recommendations.append("신체 활동 증진 및 사회 활동 참여를 늘려보세요.")
        
        return recommendations
    
    def track_changes(
        self,
        previous: MentalHealthIndicators,
        current: MentalHealthIndicators,
        time_delta_hours: float = 24
    ) -> Dict[str, Any]:
        """지표 변화 추적"""
        
        changes = {}
        
        for key in ['DRI', 'SDI', 'CFL', 'ES', 'OV']:
            prev_val = getattr(previous, key)
            curr_val = getattr(current, key)
            
            change = curr_val - prev_val
            change_rate = change / max(time_delta_hours / 24, 1)  # 일일 변화율
            
            changes[key] = {
                'previous': prev_val,
                'current': curr_val,
                'change': change,
                'change_rate': change_rate,
                'trend': 'improving' if change > 0.05 else 'declining' if change < -0.05 else 'stable'
            }
        
        # 주요 변화 감지
        significant_changes = []
        for key, data in changes.items():
            if abs(data['change']) > 0.1:
                significant_changes.append({
                    'indicator': key,
                    'change': data['change'],
                    'trend': data['trend']
                })
        
        return {
            'changes': changes,
            'significant_changes': significant_changes,
            'overall_trend': self._determine_overall_trend(changes)
        }
    
    def _determine_overall_trend(self, changes: Dict) -> str:
        """전체 추세 판단"""
        
        improving = sum(1 for v in changes.values() if v['trend'] == 'improving')
        declining = sum(1 for v in changes.values() if v['trend'] == 'declining')
        
        if improving > declining:
            return 'improving'
        elif declining > improving:
            return 'declining'
        else:
            return 'stable'
    
    def calculate_indicator_confidence(
        self,
        indicator_type: str,
        librosa_data: Optional[Dict] = None,
        gpt4o_data: Optional[Dict] = None,
        sincnet_data: Optional[Dict] = None
    ) -> float:
        """각 지표에 대한 신뢰도 계산"""
        
        confidences = []
        weights = []
        
        # Librosa 신뢰도
        if librosa_data:
            if indicator_type in ['DRI', 'ES', 'OV']:
                # 음성 분석이 강한 지표들
                confidences.append(0.8)
            else:
                confidences.append(0.6)
            weights.append(self.weights['librosa'])
        
        # GPT-4o 신뢰도
        if gpt4o_data:
            if indicator_type in ['DRI', 'CFL', 'ES']:
                # 텍스트 분석이 강한 지표들
                confidences.append(0.85)
            else:
                confidences.append(0.7)
            weights.append(self.weights['gpt4o'])
        
        # SincNet 신뢰도
        if sincnet_data:
            if indicator_type in ['DRI', 'SDI']:
                # 딥러닝이 강한 지표들
                confidences.append(0.9)
            else:
                confidences.append(0.65)
            weights.append(self.weights['sincnet'])
        
        if confidences and weights:
            # 가중 평균 신뢰도
            norm_weights = np.array(weights) / sum(weights)
            return float(np.average(confidences, weights=norm_weights))
        else:
            return 0.5  # 기본 신뢰도

    def _calculate_with_adaptive_weights(
        self,
        voice_features: Optional[Dict],
        text_analysis: Optional[Dict],
        sincnet_results: Optional[Dict],
        adaptive_weights: Dict
    ) -> MentalHealthIndicators:
        """적응형 가중치를 사용한 지표 계산"""

        final_indicators = {}

        # 각 지표에 대해 적응형 가중치 적용
        for indicator_name in ['DRI', 'SDI', 'CFL', 'ES', 'OV']:
            # IndicatorType enum이 있는 경우 처리
            from ..mental_health.optimized_weight_calculator import IndicatorType
            indicator_key = IndicatorType[indicator_name] if indicator_name in [e.name for e in IndicatorType] else indicator_name

            # 적응형 가중치 가져오기
            if indicator_key in adaptive_weights:
                weight_obj = adaptive_weights[indicator_key]
                voice_weight = weight_obj.voice if hasattr(weight_obj, 'voice') else weight_obj.get('voice', 0.3)
                text_weight = weight_obj.text if hasattr(weight_obj, 'text') else weight_obj.get('text', 0.4)
                deep_weight = weight_obj.deep if hasattr(weight_obj, 'deep') else weight_obj.get('deep', 0.3)
            else:
                # 기본 가중치 사용
                voice_weight = 0.3
                text_weight = 0.4
                deep_weight = 0.3

            values = []
            weights = []

            # Librosa 음성 기반 지표
            if voice_features:
                librosa_indicators = self._calculate_librosa_indicators(voice_features)
                value = librosa_indicators.get(indicator_name, 0.5)
                values.append(value)
                weights.append(voice_weight)

            # GPT-4o 텍스트 기반 지표
            if text_analysis:
                gpt4o_indicators = self._extract_gpt4o_indicators(text_analysis)
                value = gpt4o_indicators.get(indicator_name, 0.5)
                values.append(value)
                weights.append(text_weight)

            # SincNet 딥러닝 기반 지표
            if sincnet_results:
                sincnet_indicators = self._calculate_sincnet_indicators(sincnet_results)
                value = sincnet_indicators.get(indicator_name, 0.5)
                values.append(value)
                weights.append(deep_weight)

            # 가중 평균 계산
            if values and weights:
                total_weight = sum(weights)
                if total_weight > 0:
                    norm_weights = np.array(weights) / total_weight
                    final_indicators[indicator_name] = float(np.average(values, weights=norm_weights))
                else:
                    final_indicators[indicator_name] = 0.5
            else:
                final_indicators[indicator_name] = 0.5

            logger.info(f"{indicator_name}: 값={values}, 가중치={weights}, 최종={final_indicators[indicator_name]:.3f}")

        # 검증 및 보정
        final_indicators = self._validate_and_adjust(final_indicators)

        return MentalHealthIndicators(**final_indicators)