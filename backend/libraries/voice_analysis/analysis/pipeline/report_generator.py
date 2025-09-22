"""
리포트 생성 모듈
분석 결과를 기반으로 종합 리포트 생성
"""

import json
import logging
from typing import Dict, Any, Optional, List
from datetime import datetime
from pathlib import Path

logger = logging.getLogger(__name__)

class ReportGenerator:
    """분석 리포트 생성기"""
    
    def __init__(self, language: str = 'ko'):
        """
        Args:
            language: 리포트 언어 ('ko', 'en')
        """
        self.language = language
        self.templates = self._load_templates()
    
    def _load_templates(self) -> Dict[str, str]:
        """리포트 템플릿 로드"""
        
        if self.language == 'ko':
            return {
                'title': '시니어 정신건강 분석 리포트',
                'summary': '종합 평가',
                'indicators': '5대 정신건강 지표',
                'risk': '위험도 평가',
                'trends': '추세 분석',
                'recommendations': '권고사항',
                'details': '상세 분석'
            }
        else:
            return {
                'title': 'Senior Mental Health Analysis Report',
                'summary': 'Overall Assessment',
                'indicators': 'Five Mental Health Indicators',
                'risk': 'Risk Assessment',
                'trends': 'Trend Analysis',
                'recommendations': 'Recommendations',
                'details': 'Detailed Analysis'
            }
    
    def generate(
        self,
        indicators: Any,  # MentalHealthIndicators 객체
        risk_assessment: Dict,
        trend_analysis: Optional[Dict] = None,
        user_info: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """
        종합 리포트 생성
        
        Args:
            indicators: 5대 지표 객체
            risk_assessment: 위험도 평가 결과
            trend_analysis: 추세 분석 결과
            user_info: 사용자 정보
            
        Returns:
            구조화된 리포트
        """
        
        report = {
            'metadata': self._generate_metadata(user_info),
            'summary': self._generate_summary(indicators, risk_assessment),
            'indicators': self._format_indicators(indicators),
            'risk_assessment': self._format_risk_assessment(risk_assessment),
            'trend_analysis': self._format_trend_analysis(trend_analysis) if trend_analysis else None,
            'recommendations': self._generate_recommendations(
                indicators, risk_assessment, trend_analysis
            ),
            'narrative': self._generate_narrative(
                indicators, risk_assessment, trend_analysis
            )
        }
        
        return report
    
    def _generate_metadata(self, user_info: Optional[Dict]) -> Dict[str, Any]:
        """메타데이터 생성"""
        
        metadata = {
            'report_id': datetime.now().strftime('%Y%m%d_%H%M%S'),
            'generated_at': datetime.now().isoformat(),
            'language': self.language,
            'version': '1.0'
        }
        
        if user_info:
            metadata['user'] = {
                'age': user_info.get('age'),
                'gender': user_info.get('gender'),
                'id': user_info.get('user_id')
            }
        
        return metadata
    
    def _generate_summary(self, indicators: Any, risk_assessment: Dict) -> Dict[str, Any]:
        """요약 정보 생성"""
        
        # 지표 평균 계산
        indicator_dict = indicators.to_dict()
        avg_score = sum(indicator_dict.values()) / len(indicator_dict)
        
        # 상태 판단
        if avg_score >= 0.7:
            status = '양호' if self.language == 'ko' else 'Good'
            status_color = 'green'
        elif avg_score >= 0.4:
            status = '주의' if self.language == 'ko' else 'Caution'
            status_color = 'yellow'
        else:
            status = '위험' if self.language == 'ko' else 'Risk'
            status_color = 'red'
        
        summary = {
            'overall_status': status,
            'status_color': status_color,
            'average_score': round(avg_score, 2),
            'risk_level': risk_assessment.get('overall_risk', 'unknown'),
            'primary_concerns': risk_assessment.get('high_risk_indicators', []),
            'strengths': self._identify_strengths(indicator_dict)
        }
        
        return summary
    
    def _identify_strengths(self, indicators: Dict) -> List[str]:
        """강점 식별"""
        
        strengths = []
        
        indicator_names = {
            'DRI': '우울 관리' if self.language == 'ko' else 'Depression Management',
            'SDI': '수면 건강' if self.language == 'ko' else 'Sleep Health',
            'CFL': '인지 기능' if self.language == 'ko' else 'Cognitive Function',
            'ES': '정서 안정' if self.language == 'ko' else 'Emotional Stability',
            'OV': '전반적 활력' if self.language == 'ko' else 'Overall Vitality'
        }
        
        for key, value in indicators.items():
            if value >= 0.7:
                strengths.append(indicator_names.get(key, key))
        
        return strengths
    
    def _format_indicators(self, indicators: Any) -> Dict[str, Any]:
        """지표 포맷팅"""
        
        indicator_dict = indicators.to_dict()
        
        formatted = {}
        for key, value in indicator_dict.items():
            formatted[key] = {
                'value': round(value, 2),
                'percentage': round(value * 100, 1),
                'status': self._get_indicator_status(value),
                'description': self._get_indicator_description(key)
            }
        
        return formatted
    
    def _get_indicator_status(self, value: float) -> str:
        """지표 상태 판단"""
        
        if self.language == 'ko':
            if value >= 0.7:
                return '양호'
            elif value >= 0.4:
                return '보통'
            else:
                return '주의필요'
        else:
            if value >= 0.7:
                return 'Good'
            elif value >= 0.4:
                return 'Moderate'
            else:
                return 'Needs Attention'
    
    def _get_indicator_description(self, key: str) -> str:
        """지표 설명"""
        
        descriptions = {
            'ko': {
                'DRI': '우울 위험도 - 낮을수록 우울 위험이 높음',
                'SDI': '수면 장애 지표 - 낮을수록 수면 문제 심각',
                'CFL': '인지 기능 수준 - 낮을수록 인지 기능 저하',
                'ES': '정서적 안정성 - 낮을수록 정서 불안정',
                'OV': '전반적 활력도 - 낮을수록 활력 저하'
            },
            'en': {
                'DRI': 'Depression Risk - Lower indicates higher depression risk',
                'SDI': 'Sleep Disorder - Lower indicates more sleep problems',
                'CFL': 'Cognitive Function - Lower indicates cognitive decline',
                'ES': 'Emotional Stability - Lower indicates emotional instability',
                'OV': 'Overall Vitality - Lower indicates reduced vitality'
            }
        }
        
        return descriptions.get(self.language, descriptions['en']).get(key, key)
    
    def _format_risk_assessment(self, risk_assessment: Dict) -> Dict[str, Any]:
        """위험도 평가 포맷팅"""
        
        formatted = {
            'overall_risk': risk_assessment.get('overall_risk'),
            'risk_factors': risk_assessment.get('high_risk_indicators', []),
            'individual_risks': risk_assessment.get('individual_risks', {}),
            'action_required': self._determine_action_level(
                risk_assessment.get('overall_risk')
            )
        }
        
        return formatted
    
    def _determine_action_level(self, risk_level: str) -> str:
        """필요 조치 수준 결정"""
        
        actions = {
            'ko': {
                'high': '즉시 전문가 상담 필요',
                'moderate': '정기 모니터링 권장',
                'low': '현재 상태 유지'
            },
            'en': {
                'high': 'Immediate professional consultation needed',
                'moderate': 'Regular monitoring recommended',
                'low': 'Maintain current status'
            }
        }
        
        return actions.get(self.language, actions['en']).get(
            risk_level, '상태 확인 필요' if self.language == 'ko' else 'Status check needed'
        )
    
    def _format_trend_analysis(self, trend_analysis: Dict) -> Dict[str, Any]:
        """추세 분석 포맷팅"""
        
        if not trend_analysis or trend_analysis.get('status') != 'success':
            return None
        
        formatted = {
            'period': trend_analysis.get('period'),
            'trends': {},
            'overall_direction': None,
            'significant_changes': []
        }
        
        # 각 지표 추세
        trends = trend_analysis.get('trends', {})
        for key, trend in trends.items():
            formatted['trends'][key] = {
                'direction': trend.get('direction'),
                'current': round(trend.get('current_value', 0), 2),
                'change_rate': round(trend.get('slope', 0) * 100, 1),
                'description': self._describe_trend(key, trend)
            }
        
        # 전체 방향성
        improving = sum(1 for t in trends.values() if t.get('direction') == 'improving')
        declining = sum(1 for t in trends.values() if t.get('direction') == 'declining')
        
        if improving > declining:
            formatted['overall_direction'] = '개선 중' if self.language == 'ko' else 'Improving'
        elif declining > improving:
            formatted['overall_direction'] = '악화 중' if self.language == 'ko' else 'Declining'
        else:
            formatted['overall_direction'] = '안정적' if self.language == 'ko' else 'Stable'
        
        return formatted
    
    def _describe_trend(self, indicator: str, trend: Dict) -> str:
        """추세 설명 생성"""
        
        direction = trend.get('direction', 'stable')
        change_rate = abs(trend.get('slope', 0) * 100)
        
        if self.language == 'ko':
            if direction == 'improving':
                return f"{change_rate:.1f}% 개선 추세"
            elif direction == 'declining':
                return f"{change_rate:.1f}% 악화 추세"
            else:
                return "안정적 유지"
        else:
            if direction == 'improving':
                return f"{change_rate:.1f}% improvement trend"
            elif direction == 'declining':
                return f"{change_rate:.1f}% decline trend"
            else:
                return "Stable"
    
    def _generate_recommendations(
        self,
        indicators: Any,
        risk_assessment: Dict,
        trend_analysis: Optional[Dict]
    ) -> List[Dict[str, str]]:
        """권고사항 생성"""
        
        recommendations = []
        indicator_dict = indicators.to_dict()
        
        # 위험도 기반 권고
        risk_level = risk_assessment.get('overall_risk')
        if risk_level == 'high':
            recommendations.append({
                'priority': 'high',
                'category': 'medical',
                'text': '즉시 정신건강 전문의 상담을 받으시기 바랍니다.' if self.language == 'ko' 
                       else 'Immediate consultation with a mental health professional is recommended.'
            })
        
        # 지표별 권고
        for key, value in indicator_dict.items():
            if value < 0.4:
                rec = self._get_indicator_recommendation(key, value)
                if rec:
                    recommendations.append(rec)
        
        # 추세 기반 권고
        if trend_analysis and trend_analysis.get('status') == 'success':
            trend_rec = self._get_trend_recommendations(trend_analysis)
            recommendations.extend(trend_rec)
        
        # 일반 권고
        recommendations.extend(self._get_general_recommendations(indicator_dict))
        
        # 우선순위 정렬
        priority_order = {'high': 0, 'medium': 1, 'low': 2}
        recommendations.sort(key=lambda x: priority_order.get(x['priority'], 3))
        
        return recommendations[:5]  # 상위 5개만 반환
    
    def _get_indicator_recommendation(self, indicator: str, value: float) -> Optional[Dict]:
        """지표별 권고사항"""
        
        recs = {
            'ko': {
                'DRI': {
                    'text': '우울증 선별 검사 및 상담 프로그램 참여를 권장합니다.',
                    'category': 'mental_health'
                },
                'SDI': {
                    'text': '수면 위생 교육 및 수면 패턴 개선 프로그램이 필요합니다.',
                    'category': 'sleep'
                },
                'CFL': {
                    'text': '인지 기능 평가 및 인지 훈련 프로그램 참여를 고려하세요.',
                    'category': 'cognitive'
                },
                'ES': {
                    'text': '스트레스 관리 및 정서 조절 프로그램이 도움될 수 있습니다.',
                    'category': 'emotional'
                },
                'OV': {
                    'text': '신체 활동 증진 및 사회 활동 참여를 늘려보세요.',
                    'category': 'lifestyle'
                }
            },
            'en': {
                'DRI': {
                    'text': 'Depression screening and counseling program participation recommended.',
                    'category': 'mental_health'
                },
                'SDI': {
                    'text': 'Sleep hygiene education and sleep pattern improvement needed.',
                    'category': 'sleep'
                },
                'CFL': {
                    'text': 'Consider cognitive assessment and training programs.',
                    'category': 'cognitive'
                },
                'ES': {
                    'text': 'Stress management and emotional regulation programs may help.',
                    'category': 'emotional'
                },
                'OV': {
                    'text': 'Increase physical activity and social participation.',
                    'category': 'lifestyle'
                }
            }
        }
        
        rec_data = recs.get(self.language, recs['en']).get(indicator)
        if rec_data:
            return {
                'priority': 'high' if value < 0.3 else 'medium',
                'category': rec_data['category'],
                'text': rec_data['text']
            }
        
        return None
    
    def _get_trend_recommendations(self, trend_analysis: Dict) -> List[Dict]:
        """추세 기반 권고사항"""
        
        recommendations = []
        risk = trend_analysis.get('risk_assessment', {})
        
        if risk.get('risk_level') == 'high':
            recommendations.append({
                'priority': 'high',
                'category': 'monitoring',
                'text': '급격한 변화가 감지되었습니다. 집중 모니터링이 필요합니다.' if self.language == 'ko'
                       else 'Rapid changes detected. Intensive monitoring needed.'
            })
        
        return recommendations
    
    def _get_general_recommendations(self, indicators: Dict) -> List[Dict]:
        """일반 권고사항"""
        
        avg_score = sum(indicators.values()) / len(indicators)
        
        if avg_score >= 0.7:
            return [{
                'priority': 'low',
                'category': 'maintenance',
                'text': '현재의 건강한 생활 습관을 유지하시기 바랍니다.' if self.language == 'ko'
                       else 'Maintain your current healthy lifestyle habits.'
            }]
        else:
            return [{
                'priority': 'medium',
                'category': 'lifestyle',
                'text': '규칙적인 운동과 사회 활동 참여를 권장합니다.' if self.language == 'ko'
                       else 'Regular exercise and social participation recommended.'
            }]
    
    def _generate_narrative(
        self,
        indicators: Any,
        risk_assessment: Dict,
        trend_analysis: Optional[Dict]
    ) -> str:
        """서술형 리포트 생성"""
        
        indicator_dict = indicators.to_dict()
        avg_score = sum(indicator_dict.values()) / len(indicator_dict)
        
        if self.language == 'ko':
            narrative = f"""
분석 결과, 전반적인 정신건강 점수는 {avg_score:.1%}입니다.
            
5대 지표 중 가장 양호한 영역은 {self._get_best_indicator(indicator_dict)}이며,
가장 주의가 필요한 영역은 {self._get_worst_indicator(indicator_dict)}입니다.
            
위험도 평가 결과는 '{risk_assessment.get('overall_risk', '미평가')}'이며,
{len(risk_assessment.get('recommendations', []))}개의 권고사항이 도출되었습니다.
            """
        else:
            narrative = f"""
Analysis shows an overall mental health score of {avg_score:.1%}.
            
Among the five indicators, the best performing area is {self._get_best_indicator(indicator_dict)},
while {self._get_worst_indicator(indicator_dict)} requires the most attention.
            
Risk assessment level is '{risk_assessment.get('overall_risk', 'not assessed')}',
with {len(risk_assessment.get('recommendations', []))} recommendations provided.
            """
        
        if trend_analysis and trend_analysis.get('status') == 'success':
            trend_summary = self._summarize_trends(trend_analysis)
            narrative += f"\n{trend_summary}"
        
        return narrative.strip()
    
    def _get_best_indicator(self, indicators: Dict) -> str:
        """최고 점수 지표"""
        
        best_key = max(indicators, key=indicators.get)
        return self._get_indicator_name(best_key)
    
    def _get_worst_indicator(self, indicators: Dict) -> str:
        """최저 점수 지표"""
        
        worst_key = min(indicators, key=indicators.get)
        return self._get_indicator_name(worst_key)
    
    def _get_indicator_name(self, key: str) -> str:
        """지표 이름"""
        
        names = {
            'ko': {
                'DRI': '우울 관리',
                'SDI': '수면 건강',
                'CFL': '인지 기능',
                'ES': '정서 안정성',
                'OV': '전반적 활력'
            },
            'en': {
                'DRI': 'Depression Management',
                'SDI': 'Sleep Health',
                'CFL': 'Cognitive Function',
                'ES': 'Emotional Stability',
                'OV': 'Overall Vitality'
            }
        }
        
        return names.get(self.language, names['en']).get(key, key)
    
    def _summarize_trends(self, trend_analysis: Dict) -> str:
        """추세 요약"""
        
        period = trend_analysis.get('period', {})
        data_points = period.get('data_points', 0)
        
        if self.language == 'ko':
            return f"최근 {data_points}회 측정 데이터를 기반으로 한 추세 분석이 포함되었습니다."
        else:
            return f"Trend analysis based on {data_points} recent measurements is included."
    
    def export_to_json(self, report: Dict, filepath: str):
        """JSON 파일로 리포트 저장"""
        
        try:
            path = Path(filepath)
            path.parent.mkdir(parents=True, exist_ok=True)
            
            with open(path, 'w', encoding='utf-8') as f:
                json.dump(report, f, ensure_ascii=False, indent=2, default=str)
            
            logger.info(f"리포트 저장 완료: {filepath}")
            return True
            
        except Exception as e:
            logger.error(f"리포트 저장 실패: {e}")
            return False