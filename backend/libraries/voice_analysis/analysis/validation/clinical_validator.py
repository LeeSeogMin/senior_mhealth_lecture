"""
임상 검증 모듈
5대 지표의 임상적 타당성 검증
"""

import numpy as np
import logging
from typing import Dict, Any, List, Tuple, Optional
from datetime import datetime

logger = logging.getLogger(__name__)

class ClinicalValidator:
    """임상 검증기"""
    
    def __init__(self):
        # 임상 기준값 (연구 및 문헌 기반)
        self.clinical_thresholds = {
            'DRI': {
                'normal': (0.7, 1.0),
                'mild': (0.5, 0.7),
                'moderate': (0.3, 0.5),
                'severe': (0.0, 0.3)
            },
            'SDI': {
                'normal': (0.7, 1.0),
                'mild': (0.5, 0.7),
                'moderate': (0.3, 0.5),
                'severe': (0.0, 0.3)
            },
            'CFL': {
                'normal': (0.8, 1.0),
                'mci': (0.6, 0.8),  # Mild Cognitive Impairment
                'moderate': (0.4, 0.6),
                'severe': (0.0, 0.4)
            },
            'ES': {
                'stable': (0.7, 1.0),
                'mild_instability': (0.5, 0.7),
                'moderate_instability': (0.3, 0.5),
                'severe_instability': (0.0, 0.3)
            },
            'OV': {
                'high': (0.7, 1.0),
                'moderate': (0.4, 0.7),
                'low': (0.2, 0.4),
                'very_low': (0.0, 0.2)
            }
        }
        
        # 임상 진단 기준
        self.diagnostic_criteria = {
            'major_depression': {
                'DRI': (0.0, 0.3),
                'ES': (0.0, 0.4),
                'OV': (0.0, 0.3)
            },
            'insomnia': {
                'SDI': (0.0, 0.3)
            },
            'cognitive_impairment': {
                'CFL': (0.0, 0.6)
            }
        }
    
    def validate(
        self,
        indicators: Dict[str, float],
        clinical_data: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """
        지표의 임상적 타당성 검증
        
        Args:
            indicators: 5대 지표 값
            clinical_data: 추가 임상 데이터 (선택)
            
        Returns:
            검증 결과
        """
        
        validation_result = {
            'timestamp': datetime.now().isoformat(),
            'clinical_classification': self._classify_indicators(indicators),
            'diagnostic_screening': self._screen_conditions(indicators),
            'validity_check': self._check_validity(indicators),
            'consistency_check': self._check_consistency(indicators),
            'recommendations': []
        }
        
        # 임상 데이터와 비교 (있는 경우)
        if clinical_data:
            validation_result['clinical_comparison'] = self._compare_with_clinical(
                indicators, clinical_data
            )
        
        # 권고사항 생성
        validation_result['recommendations'] = self._generate_clinical_recommendations(
            validation_result
        )
        
        return validation_result
    
    def _classify_indicators(self, indicators: Dict) -> Dict[str, str]:
        """지표별 임상 분류"""
        
        classification = {}
        
        for key, value in indicators.items():
            if key in self.clinical_thresholds:
                for category, (min_val, max_val) in self.clinical_thresholds[key].items():
                    if min_val <= value < max_val:
                        classification[key] = category
                        break
            else:
                classification[key] = 'unknown'
        
        return classification
    
    def _screen_conditions(self, indicators: Dict) -> List[Dict]:
        """임상 조건 선별"""
        
        screening_results = []
        
        for condition, criteria in self.diagnostic_criteria.items():
            meets_criteria = True
            matching_indicators = []
            
            for indicator, (min_val, max_val) in criteria.items():
                if indicator in indicators:
                    if not (min_val <= indicators[indicator] < max_val):
                        meets_criteria = False
                        break
                    else:
                        matching_indicators.append(indicator)
            
            if meets_criteria and matching_indicators:
                screening_results.append({
                    'condition': condition,
                    'probability': self._calculate_condition_probability(
                        indicators, criteria
                    ),
                    'matching_indicators': matching_indicators,
                    'severity': self._assess_severity(indicators, matching_indicators)
                })
        
        return screening_results
    
    def _calculate_condition_probability(
        self,
        indicators: Dict,
        criteria: Dict
    ) -> float:
        """조건 확률 계산"""
        
        probabilities = []
        
        for indicator, (min_val, max_val) in criteria.items():
            if indicator in indicators:
                value = indicators[indicator]
                # 범위 내에서 얼마나 심각한지 계산
                if max_val > min_val:
                    severity = 1 - (value - min_val) / (max_val - min_val)
                else:
                    severity = 0.5
                probabilities.append(severity)
        
        return float(np.mean(probabilities)) if probabilities else 0.0
    
    def _assess_severity(self, indicators: Dict, relevant_indicators: List) -> str:
        """심각도 평가"""
        
        severities = []
        for indicator in relevant_indicators:
            value = indicators.get(indicator, 0.5)
            if value < 0.2:
                severities.append(3)  # 매우 심각
            elif value < 0.4:
                severities.append(2)  # 심각
            elif value < 0.6:
                severities.append(1)  # 보통
            else:
                severities.append(0)  # 경미
        
        avg_severity = np.mean(severities) if severities else 0
        
        if avg_severity >= 2.5:
            return 'very_severe'
        elif avg_severity >= 1.5:
            return 'severe'
        elif avg_severity >= 0.5:
            return 'moderate'
        else:
            return 'mild'
    
    def _check_validity(self, indicators: Dict) -> Dict[str, Any]:
        """타당성 검사"""
        
        validity = {
            'is_valid': True,
            'issues': []
        }
        
        # 범위 검사
        for key, value in indicators.items():
            if not (0 <= value <= 1):
                validity['is_valid'] = False
                validity['issues'].append(f"{key} 값이 유효 범위를 벗어남: {value}")
        
        # 논리적 일관성 검사
        # 예: DRI가 매우 낮은데 OV가 높을 수 없음
        if indicators.get('DRI', 0.5) < 0.3 and indicators.get('OV', 0.5) > 0.7:
            validity['is_valid'] = False
            validity['issues'].append("DRI와 OV 값의 논리적 불일치")
        
        # CFL이 낮은데 ES가 매우 높을 수 없음
        if indicators.get('CFL', 0.5) < 0.3 and indicators.get('ES', 0.5) > 0.8:
            validity['is_valid'] = False
            validity['issues'].append("CFL과 ES 값의 논리적 불일치")
        
        return validity
    
    def _check_consistency(self, indicators: Dict) -> Dict[str, Any]:
        """일관성 검사"""
        
        # 지표 간 상관관계 확인
        consistency = {
            'overall_consistency': 0.0,
            'correlations': {},
            'anomalies': []
        }
        
        # 예상 상관관계
        expected_correlations = [
            ('DRI', 'OV', 'positive'),  # DRI 높으면 OV도 높아야 함
            ('DRI', 'ES', 'positive'),
            ('CFL', 'ES', 'positive'),
            ('SDI', 'OV', 'positive')
        ]
        
        for ind1, ind2, expected_direction in expected_correlations:
            if ind1 in indicators and ind2 in indicators:
                val1 = indicators[ind1]
                val2 = indicators[ind2]
                
                # 간단한 상관 확인
                if expected_direction == 'positive':
                    if (val1 > 0.5 and val2 < 0.5) or (val1 < 0.5 and val2 > 0.5):
                        consistency['anomalies'].append(
                            f"{ind1}와 {ind2}의 관계가 예상과 다름"
                        )
                
                consistency['correlations'][f"{ind1}-{ind2}"] = abs(val1 - val2)
        
        # 전체 일관성 점수
        if consistency['anomalies']:
            consistency['overall_consistency'] = max(0, 1 - len(consistency['anomalies']) * 0.2)
        else:
            consistency['overall_consistency'] = 1.0
        
        return consistency
    
    def _compare_with_clinical(
        self,
        indicators: Dict,
        clinical_data: Dict
    ) -> Dict[str, Any]:
        """임상 데이터와 비교"""
        
        comparison = {
            'matches': [],
            'discrepancies': [],
            'correlation': 0.0
        }
        
        # 임상 진단과 비교
        if 'diagnosis' in clinical_data:
            diagnosis = clinical_data['diagnosis'].lower()
            
            # 우울증 진단과 DRI 비교
            if 'depression' in diagnosis or '우울' in diagnosis:
                if indicators.get('DRI', 0.5) < 0.4:
                    comparison['matches'].append("DRI가 우울증 진단과 일치")
                else:
                    comparison['discrepancies'].append("DRI가 우울증 진단과 불일치")
            
            # 인지장애 진단과 CFL 비교
            if 'cognitive' in diagnosis or '인지' in diagnosis or 'dementia' in diagnosis:
                if indicators.get('CFL', 0.5) < 0.6:
                    comparison['matches'].append("CFL이 인지장애 진단과 일치")
                else:
                    comparison['discrepancies'].append("CFL이 인지장애 진단과 불일치")
        
        # 임상 점수와 비교 (있는 경우)
        if 'clinical_scores' in clinical_data:
            # 예: GDS (Geriatric Depression Scale) 점수와 DRI 비교
            if 'GDS' in clinical_data['clinical_scores']:
                gds = clinical_data['clinical_scores']['GDS']
                # GDS 정규화 (0-30 → 0-1)
                gds_normalized = 1 - (gds / 30)
                dri_diff = abs(indicators.get('DRI', 0.5) - gds_normalized)
                
                if dri_diff < 0.2:
                    comparison['matches'].append(f"DRI가 GDS 점수와 유사 (차이: {dri_diff:.2f})")
                else:
                    comparison['discrepancies'].append(f"DRI가 GDS 점수와 차이 (차이: {dri_diff:.2f})")
        
        # 상관도 계산
        if comparison['matches'] and not comparison['discrepancies']:
            comparison['correlation'] = 1.0
        elif comparison['matches'] and comparison['discrepancies']:
            comparison['correlation'] = len(comparison['matches']) / (
                len(comparison['matches']) + len(comparison['discrepancies'])
            )
        else:
            comparison['correlation'] = 0.0
        
        return comparison
    
    def _generate_clinical_recommendations(
        self,
        validation_result: Dict
    ) -> List[str]:
        """임상 권고사항 생성"""
        
        recommendations = []
        
        # 진단 선별 결과 기반
        for screening in validation_result.get('diagnostic_screening', []):
            condition = screening['condition']
            probability = screening['probability']
            severity = screening['severity']
            
            if probability > 0.7:
                if condition == 'major_depression':
                    recommendations.append(
                        f"주요우울장애 가능성 높음 ({probability:.1%}). "
                        "정신건강의학과 전문의 상담 필요"
                    )
                elif condition == 'insomnia':
                    recommendations.append(
                        f"불면증 가능성 높음 ({probability:.1%}). "
                        "수면클리닉 방문 권장"
                    )
                elif condition == 'cognitive_impairment':
                    recommendations.append(
                        f"인지장애 가능성 ({probability:.1%}). "
                        "신경과 또는 정신건강의학과 평가 필요"
                    )
        
        # 타당성 문제
        validity = validation_result.get('validity_check', {})
        if not validity.get('is_valid', True):
            recommendations.append(
                "측정값에 이상이 감지됨. 재검사 권장"
            )
        
        # 일관성 문제
        consistency = validation_result.get('consistency_check', {})
        if consistency.get('overall_consistency', 1.0) < 0.7:
            recommendations.append(
                "지표 간 일관성이 낮음. 추가 평가 필요"
            )
        
        return recommendations
    
    def generate_clinical_report(
        self,
        validation_result: Dict
    ) -> str:
        """임상 보고서 생성"""
        
        report = []
        report.append("=== 임상 검증 보고서 ===\n")
        report.append(f"검증 시간: {validation_result['timestamp']}\n")
        
        # 임상 분류
        report.append("\n[지표별 임상 분류]")
        for indicator, classification in validation_result['clinical_classification'].items():
            report.append(f"- {indicator}: {classification}")
        
        # 진단 선별
        report.append("\n[진단 선별 결과]")
        for screening in validation_result['diagnostic_screening']:
            report.append(
                f"- {screening['condition']}: "
                f"가능성 {screening['probability']:.1%}, "
                f"심각도 {screening['severity']}"
            )
        
        # 권고사항
        report.append("\n[임상 권고사항]")
        for i, rec in enumerate(validation_result['recommendations'], 1):
            report.append(f"{i}. {rec}")
        
        return '\n'.join(report)