"""
표준화된 정신건강 평가 도구
===========================

PHQ-9, GAD-7 등 검증된 임상 평가 도구 구현.
"""

from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from enum import Enum
import logging

logger = logging.getLogger(__name__)


class AssessmentType(Enum):
    """평가 도구 유형"""
    PHQ9 = "PHQ-9"  # Patient Health Questionnaire-9
    GAD7 = "GAD-7"  # Generalized Anxiety Disorder-7
    GDS = "GDS"  # Geriatric Depression Scale
    MMSE = "MMSE"  # Mini-Mental State Examination
    MoCA = "MoCA"  # Montreal Cognitive Assessment


@dataclass
class AssessmentQuestion:
    """평가 문항"""
    question_id: str
    text: str
    response_options: Dict[int, str]
    category: Optional[str] = None


class PHQ9Assessment:
    """PHQ-9 우울증 선별 도구"""
    
    def __init__(self):
        self.questions = self._initialize_questions()
        self.severity_thresholds = {
            'minimal': (0, 4),
            'mild': (5, 9),
            'moderate': (10, 14),
            'moderately_severe': (15, 19),
            'severe': (20, 27)
        }
    
    def _initialize_questions(self) -> List[AssessmentQuestion]:
        """PHQ-9 문항 초기화"""
        
        response_options = {
            0: "전혀 없음",
            1: "며칠",
            2: "1주일 이상",
            3: "거의 매일"
        }
        
        questions = [
            AssessmentQuestion(
                "phq9_1",
                "일을 하는 것에 대한 흥미나 재미가 거의 없음",
                response_options,
                "anhedonia"
            ),
            AssessmentQuestion(
                "phq9_2",
                "기분이 가라앉거나, 우울하거나, 희망이 없음",
                response_options,
                "mood"
            ),
            AssessmentQuestion(
                "phq9_3",
                "잠들기 어렵거나 자주 깨거나 너무 많이 잠",
                response_options,
                "sleep"
            ),
            AssessmentQuestion(
                "phq9_4",
                "피로감 또는 기력이 없음",
                response_options,
                "energy"
            ),
            AssessmentQuestion(
                "phq9_5",
                "식욕 저하 또는 과식",
                response_options,
                "appetite"
            ),
            AssessmentQuestion(
                "phq9_6",
                "자신이 실패자라고 느끼거나 자신과 가족을 실망시켰다고 느낌",
                response_options,
                "guilt"
            ),
            AssessmentQuestion(
                "phq9_7",
                "신문을 읽거나 TV를 보는 것과 같은 일에 집중하기 어려움",
                response_options,
                "concentration"
            ),
            AssessmentQuestion(
                "phq9_8",
                "다른 사람들이 알아챌 정도로 거동이나 말이 느림, 또는 반대로 안절부절 못함",
                response_options,
                "psychomotor"
            ),
            AssessmentQuestion(
                "phq9_9",
                "차라리 죽는 것이 낫겠다는 생각 또는 자해 생각",
                response_options,
                "suicidal_ideation"
            )
        ]
        
        return questions
    
    def calculate_score(self, responses: Dict[str, int]) -> Tuple[int, str, Dict]:
        """
        PHQ-9 점수 계산
        
        Args:
            responses: 문항별 응답 (0-3)
            
        Returns:
            (총점, 심각도, 상세정보)
        """
        
        # 총점 계산
        total_score = sum(responses.values())
        
        # 심각도 판정
        severity = self._get_severity(total_score)
        
        # 카테고리별 점수
        category_scores = self._calculate_category_scores(responses)
        
        # 위험 지표 확인
        risk_indicators = self._check_risk_indicators(responses)
        
        return total_score, severity, {
            'category_scores': category_scores,
            'risk_indicators': risk_indicators,
            'clinical_action': self._get_clinical_action(total_score, responses)
        }
    
    def _get_severity(self, score: int) -> str:
        """심각도 판정"""
        for severity, (min_score, max_score) in self.severity_thresholds.items():
            if min_score <= score <= max_score:
                return severity
        return 'unknown'
    
    def _calculate_category_scores(self, responses: Dict[str, int]) -> Dict[str, float]:
        """카테고리별 점수 계산"""
        categories = {
            'mood': ['phq9_1', 'phq9_2'],
            'physical': ['phq9_3', 'phq9_4', 'phq9_5'],
            'cognitive': ['phq9_6', 'phq9_7'],
            'behavioral': ['phq9_8'],
            'suicidal': ['phq9_9']
        }
        
        category_scores = {}
        for category, items in categories.items():
            scores = [responses.get(item, 0) for item in items]
            category_scores[category] = sum(scores) / len(scores) if scores else 0
        
        return category_scores
    
    def _check_risk_indicators(self, responses: Dict[str, int]) -> List[str]:
        """위험 지표 확인"""
        indicators = []
        
        # 자살 사고 확인 (문항 9)
        if responses.get('phq9_9', 0) > 0:
            indicators.append('suicidal_ideation')
        
        # 심각한 기능 장애 (여러 문항에서 3점)
        severe_items = sum(1 for score in responses.values() if score == 3)
        if severe_items >= 5:
            indicators.append('severe_functional_impairment')
        
        # 핵심 증상 (문항 1, 2 모두 높은 점수)
        if responses.get('phq9_1', 0) >= 2 and responses.get('phq9_2', 0) >= 2:
            indicators.append('core_symptoms_present')
        
        return indicators
    
    def _get_clinical_action(self, score: int, responses: Dict[str, int]) -> str:
        """임상 조치 권고"""
        
        # 자살 사고가 있는 경우
        if responses.get('phq9_9', 0) > 0:
            return "즉시 정신건강 전문가 상담 필요"
        
        if score >= 20:
            return "즉시 치료 시작 권장"
        elif score >= 15:
            return "치료 시작 고려, 1주 후 재평가"
        elif score >= 10:
            return "치료 계획 수립, 상담 권장"
        elif score >= 5:
            return "경과 관찰, 2-4주 후 재평가"
        else:
            return "특별한 조치 불필요, 정기 검진 유지"


class GAD7Assessment:
    """GAD-7 불안 장애 선별 도구"""
    
    def __init__(self):
        self.questions = self._initialize_questions()
        self.severity_thresholds = {
            'minimal': (0, 4),
            'mild': (5, 9),
            'moderate': (10, 14),
            'severe': (15, 21)
        }
    
    def _initialize_questions(self) -> List[AssessmentQuestion]:
        """GAD-7 문항 초기화"""
        
        response_options = {
            0: "전혀 없음",
            1: "며칠",
            2: "1주일 이상",
            3: "거의 매일"
        }
        
        questions = [
            AssessmentQuestion(
                "gad7_1",
                "초조하거나 불안하거나 조마조마함",
                response_options,
                "nervousness"
            ),
            AssessmentQuestion(
                "gad7_2",
                "걱정을 멈추거나 조절할 수 없음",
                response_options,
                "worry_control"
            ),
            AssessmentQuestion(
                "gad7_3",
                "여러 가지 것들에 대해 지나친 걱정",
                response_options,
                "excessive_worry"
            ),
            AssessmentQuestion(
                "gad7_4",
                "편하게 있기 어려움",
                response_options,
                "restlessness"
            ),
            AssessmentQuestion(
                "gad7_5",
                "너무 안절부절해서 가만히 있기 어려움",
                response_options,
                "restlessness_severe"
            ),
            AssessmentQuestion(
                "gad7_6",
                "쉽게 짜증이 나거나 화가 남",
                response_options,
                "irritability"
            ),
            AssessmentQuestion(
                "gad7_7",
                "무언가 끔찍한 일이 일어날 것 같은 두려움",
                response_options,
                "fear"
            )
        ]
        
        return questions
    
    def calculate_score(self, responses: Dict[str, int]) -> Tuple[int, str, Dict]:
        """
        GAD-7 점수 계산
        
        Args:
            responses: 문항별 응답 (0-3)
            
        Returns:
            (총점, 심각도, 상세정보)
        """
        
        # 총점 계산
        total_score = sum(responses.values())
        
        # 심각도 판정
        severity = self._get_severity(total_score)
        
        # 불안 유형 분석
        anxiety_types = self._analyze_anxiety_types(responses)
        
        return total_score, severity, {
            'anxiety_types': anxiety_types,
            'functional_impact': self._assess_functional_impact(total_score),
            'clinical_action': self._get_clinical_action(total_score)
        }
    
    def _get_severity(self, score: int) -> str:
        """심각도 판정"""
        for severity, (min_score, max_score) in self.severity_thresholds.items():
            if min_score <= score <= max_score:
                return severity
        return 'unknown'
    
    def _analyze_anxiety_types(self, responses: Dict[str, int]) -> Dict[str, bool]:
        """불안 유형 분석"""
        types = {
            'generalized_anxiety': responses.get('gad7_1', 0) >= 2 and responses.get('gad7_3', 0) >= 2,
            'panic_features': responses.get('gad7_7', 0) >= 2,
            'somatic_anxiety': responses.get('gad7_4', 0) >= 2 or responses.get('gad7_5', 0) >= 2,
            'irritability_prominent': responses.get('gad7_6', 0) >= 2
        }
        return types
    
    def _assess_functional_impact(self, score: int) -> str:
        """기능 영향 평가"""
        if score >= 15:
            return "심각한 기능 장애"
        elif score >= 10:
            return "중등도 기능 장애"
        elif score >= 5:
            return "경미한 기능 장애"
        else:
            return "기능 장애 없음"
    
    def _get_clinical_action(self, score: int) -> str:
        """임상 조치 권고"""
        if score >= 15:
            return "약물치료 및 심리치료 병행 권장"
        elif score >= 10:
            return "심리치료 권장, 약물치료 고려"
        elif score >= 5:
            return "경과 관찰, 심리교육 제공"
        else:
            return "특별한 조치 불필요"


class IntegratedAssessment:
    """통합 평가 시스템"""
    
    def __init__(self):
        self.phq9 = PHQ9Assessment()
        self.gad7 = GAD7Assessment()
        
    def perform_screening(
        self,
        phq9_responses: Optional[Dict[str, int]] = None,
        gad7_responses: Optional[Dict[str, int]] = None
    ) -> Dict:
        """
        통합 스크리닝 수행
        
        Args:
            phq9_responses: PHQ-9 응답
            gad7_responses: GAD-7 응답
            
        Returns:
            통합 평가 결과
        """
        
        results = {
            'screening_complete': False,
            'phq9': None,
            'gad7': None,
            'combined_risk': None,
            'recommendations': []
        }
        
        # PHQ-9 평가
        if phq9_responses:
            phq9_score, phq9_severity, phq9_details = self.phq9.calculate_score(phq9_responses)
            results['phq9'] = {
                'score': phq9_score,
                'severity': phq9_severity,
                'details': phq9_details
            }
        
        # GAD-7 평가
        if gad7_responses:
            gad7_score, gad7_severity, gad7_details = self.gad7.calculate_score(gad7_responses)
            results['gad7'] = {
                'score': gad7_score,
                'severity': gad7_severity,
                'details': gad7_details
            }
        
        # 통합 위험도 평가
        if results['phq9'] and results['gad7']:
            results['screening_complete'] = True
            results['combined_risk'] = self._assess_combined_risk(
                results['phq9'], results['gad7']
            )
            results['recommendations'] = self._generate_recommendations(
                results['phq9'], results['gad7'], results['combined_risk']
            )
        
        return results
    
    def _assess_combined_risk(self, phq9_result: Dict, gad7_result: Dict) -> str:
        """통합 위험도 평가"""
        
        # 자살 사고 확인
        if 'suicidal_ideation' in phq9_result['details'].get('risk_indicators', []):
            return 'critical'
        
        # 점수 기반 평가
        phq9_score = phq9_result['score']
        gad7_score = gad7_result['score']
        
        if phq9_score >= 15 or gad7_score >= 15:
            return 'high'
        elif phq9_score >= 10 or gad7_score >= 10:
            return 'moderate'
        elif phq9_score >= 5 or gad7_score >= 5:
            return 'mild'
        else:
            return 'low'
    
    def _generate_recommendations(
        self,
        phq9_result: Dict,
        gad7_result: Dict,
        combined_risk: str
    ) -> List[str]:
        """통합 권고사항 생성"""
        
        recommendations = []
        
        if combined_risk == 'critical':
            recommendations.append("⚨ 즉시 정신건강 응급 상담 필요")
            recommendations.append("24시간 위기상담 전화: 109")
        elif combined_risk == 'high':
            recommendations.append("정신과 전문의 진료 예약 (1주 이내)")
            recommendations.append("주 2-3회 운동 프로그램 참여")
        elif combined_risk == 'moderate':
            recommendations.append("심리상담사 상담 고려")
            recommendations.append("스트레스 관리 프로그램 참여")
        elif combined_risk == 'mild':
            recommendations.append("정기 모니터링 유지")
            recommendations.append("셀프케어 활동 증가")
        
        # 개별 증상별 권고
        if phq9_result['score'] >= 10:
            recommendations.append("우울증 관리: 규칙적인 수면, 사회 활동 증가")
        
        if gad7_result['score'] >= 10:
            recommendations.append("불안 관리: 이완 기법, 명상 프로그램")
        
        return recommendations


def create_assessment_from_audio_analysis(
    ai_predictions: Dict[str, float]
) -> Dict[str, int]:
    """
    AI 예측을 표준 평가 도구 형식으로 변환 (개발용)
    
    Args:
        ai_predictions: AI 예측값
        
    Returns:
        평가 도구 응답 형식
    """
    
    # 개발 단계에서만 사용 - 실제로는 사용자 입력 필요
    logger.warning("⚠️ 개발 모드: AI 예측을 평가 도구로 변환 중")
    
    phq9_responses = {}
    gad7_responses = {}
    
    # 간단한 매핑 (실제로는 더 정교한 변환 필요)
    depression_score = ai_predictions.get('depression_risk', 0.5)
    anxiety_score = ai_predictions.get('anxiety_level', 0.3)
    
    # PHQ-9 응답 시뮬레이션
    for i in range(1, 10):
        if i in [1, 2]:  # 핵심 우울 증상
            phq9_responses[f'phq9_{i}'] = min(3, int(depression_score * 4))
        else:
            phq9_responses[f'phq9_{i}'] = min(3, int(depression_score * 3))
    
    # GAD-7 응답 시뮬레이션
    for i in range(1, 8):
        gad7_responses[f'gad7_{i}'] = min(3, int(anxiety_score * 4))
    
    return {
        'phq9': phq9_responses,
        'gad7': gad7_responses,
        'development_mode': True,
        'warning': '실제 임상 평가가 아님 - 개발용 시뮬레이션'
    }