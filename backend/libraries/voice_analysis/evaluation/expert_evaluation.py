"""
전문가 평가 시스템
==================

AI 평가와 전문가 검증을 통합하는 하이브리드 평가 시스템.
개발 단계에서 점진적으로 전문가 평가를 도입.
"""

from enum import Enum
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass, field
from datetime import datetime
import numpy as np
import logging

logger = logging.getLogger(__name__)


class EvaluationSource(Enum):
    """평가 출처"""
    AI_ONLY = "ai"  # AI만 사용 (개발 단계)
    EXPERT_VALIDATED = "expert_validated"  # 전문가 검증된 AI 결과
    EXPERT_LABELED = "expert_labeled"  # 전문가가 직접 레이블링
    CLINICAL_TRIAL = "clinical_trial"  # 임상시험 데이터
    HYBRID = "hybrid"  # AI + 전문가 혼합


class EvaluationLevel(Enum):
    """평가 단계"""
    LEVEL_1 = "ai_screening"  # AI 초기 스크리닝
    LEVEL_2 = "psychologist_review"  # 임상심리사 검토
    LEVEL_3 = "psychiatrist_confirm"  # 정신과 전문의 확인
    LEVEL_4 = "consensus"  # 합의 도출


class RiskLevel(Enum):
    """위험도 수준"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class StandardizedAssessment:
    """표준화된 평가 도구"""
    phq9_score: Optional[int] = None  # PHQ-9 (우울증, 0-27)
    gad7_score: Optional[int] = None  # GAD-7 (불안, 0-21)
    gds_score: Optional[int] = None  # GDS (노인우울, 0-30)
    mmse_score: Optional[int] = None  # MMSE (인지기능, 0-30)
    
    def get_phq9_severity(self) -> Optional[str]:
        """PHQ-9 심각도 해석"""
        if self.phq9_score is None:
            return None
        if self.phq9_score < 5:
            return "minimal"
        elif self.phq9_score < 10:
            return "mild"
        elif self.phq9_score < 15:
            return "moderate"
        elif self.phq9_score < 20:
            return "moderately_severe"
        else:
            return "severe"
    
    def get_gad7_severity(self) -> Optional[str]:
        """GAD-7 심각도 해석"""
        if self.gad7_score is None:
            return None
        if self.gad7_score < 5:
            return "minimal"
        elif self.gad7_score < 10:
            return "mild"
        elif self.gad7_score < 15:
            return "moderate"
        else:
            return "severe"


@dataclass
class EvaluationResult:
    """평가 결과"""
    evaluation_id: str
    timestamp: datetime
    
    # 평가 값
    value: Dict[str, float]
    confidence: float
    
    # 출처 정보
    source: EvaluationSource
    evaluation_level: EvaluationLevel
    
    # 위험도
    risk_level: RiskLevel
    requires_expert_review: bool
    
    # 표준화 평가
    standardized_assessment: Optional[StandardizedAssessment] = None
    
    # 메타데이터
    development_phase: bool = True
    not_for_clinical_use: bool = True
    
    # 전문가 정보 (있을 경우)
    expert_id: Optional[str] = None
    expert_notes: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """딕셔너리 변환"""
        return {
            'evaluation_id': self.evaluation_id,
            'timestamp': self.timestamp.isoformat(),
            'value': self.value,
            'confidence': self.confidence,
            'source': self.source.value,
            'evaluation_level': self.evaluation_level.value,
            'risk_level': self.risk_level.value,
            'requires_expert_review': self.requires_expert_review,
            'development_phase': self.development_phase,
            'not_for_clinical_use': self.not_for_clinical_use,
            'standardized_scores': {
                'phq9': self.standardized_assessment.phq9_score if self.standardized_assessment else None,
                'gad7': self.standardized_assessment.gad7_score if self.standardized_assessment else None,
            } if self.standardized_assessment else None
        }


class ExpertEvaluationSystem:
    """다층적 전문가 평가 시스템"""
    
    def __init__(self):
        self.evaluation_levels = {
            EvaluationLevel.LEVEL_1: 'AI 초기 스크리닝',
            EvaluationLevel.LEVEL_2: '임상심리사 검토',
            EvaluationLevel.LEVEL_3: '정신과 전문의 확인',
            EvaluationLevel.LEVEL_4: '합의 도출'
        }
        
        # 평가 임계값
        self.confidence_threshold = 0.7  # 신뢰도 임계값
        self.agreement_threshold = 0.8  # 평가자 간 일치도
        self.expert_review_threshold = 0.5  # 전문가 검토 필요 임계값
        
        # 통계
        self.evaluation_stats = {
            'total_evaluations': 0,
            'ai_only': 0,
            'expert_reviewed': 0,
            'expert_overridden': 0
        }
    
    def evaluate(
        self,
        audio_features: Dict[str, float],
        ai_predictions: Dict[str, float],
        force_expert: bool = False
    ) -> EvaluationResult:
        """
        하이브리드 평가 수행
        
        Args:
            audio_features: 음향 특징
            ai_predictions: AI 예측값
            force_expert: 전문가 평가 강제
            
        Returns:
            평가 결과
        """
        
        # AI 신뢰도 계산
        ai_confidence = self._calculate_confidence(ai_predictions)
        
        # 위험도 평가
        risk_level = self._assess_risk_level(ai_predictions)
        
        # 전문가 평가 필요 여부 결정
        requires_expert = self._requires_expert_review(
            ai_confidence, risk_level, force_expert
        )
        
        # 평가 수행
        if requires_expert:
            result = self._perform_expert_evaluation(
                audio_features, ai_predictions, ai_confidence
            )
        else:
            result = self._create_ai_only_result(
                ai_predictions, ai_confidence, risk_level
            )
        
        # 통계 업데이트
        self._update_statistics(result)
        
        return result
    
    def _calculate_confidence(self, predictions: Dict[str, float]) -> float:
        """AI 신뢰도 계산"""
        
        # 예측값의 분산이 낮을수록 신뢰도 높음
        values = list(predictions.values())
        if not values:
            return 0.0
        
        std_dev = np.std(values)
        mean_val = np.mean(values)
        
        # 변동계수 (Coefficient of Variation) 기반
        cv = std_dev / mean_val if mean_val != 0 else 1.0
        
        # 신뢰도 = 1 - 정규화된 CV
        confidence = max(0, min(1, 1 - cv))
        
        return confidence
    
    def _assess_risk_level(self, predictions: Dict[str, float]) -> RiskLevel:
        """위험도 평가"""
        
        # 간단한 규칙 기반 평가 (실제로는 더 정교한 로직 필요)
        high_risk_indicators = 0
        
        # 우울 위험도 체크
        if 'depression_risk' in predictions:
            if predictions['depression_risk'] > 0.7:
                high_risk_indicators += 2
            elif predictions['depression_risk'] > 0.5:
                high_risk_indicators += 1
        
        # 인지 기능 체크
        if 'cognitive_decline' in predictions:
            if predictions['cognitive_decline'] > 0.6:
                high_risk_indicators += 1
        
        # 위험도 결정
        if high_risk_indicators >= 3:
            return RiskLevel.CRITICAL
        elif high_risk_indicators >= 2:
            return RiskLevel.HIGH
        elif high_risk_indicators >= 1:
            return RiskLevel.MEDIUM
        else:
            return RiskLevel.LOW
    
    def _requires_expert_review(
        self,
        confidence: float,
        risk_level: RiskLevel,
        force: bool
    ) -> bool:
        """전문가 검토 필요 여부"""
        
        if force:
            return True
        
        # 낮은 신뢰도
        if confidence < self.confidence_threshold:
            logger.info(f"낮은 신뢰도 ({confidence:.2f}) - 전문가 검토 필요")
            return True
        
        # 고위험
        if risk_level in [RiskLevel.HIGH, RiskLevel.CRITICAL]:
            logger.info(f"고위험 ({risk_level.value}) - 전문가 검토 필요")
            return True
        
        # 랜덤 샘플링 (개발 단계에서 10% 검증)
        if np.random.random() < 0.1:
            logger.info("랜덤 샘플링 - 전문가 검토")
            return True
        
        return False
    
    def _perform_expert_evaluation(
        self,
        audio_features: Dict[str, float],
        ai_predictions: Dict[str, float],
        ai_confidence: float
    ) -> EvaluationResult:
        """전문가 평가 수행 (시뮬레이션)"""
        
        # 실제로는 전문가 인터페이스로 연결
        # 개발 단계에서는 시뮬레이션
        
        logger.info("전문가 평가 요청 (개발 단계 시뮬레이션)")
        
        # 시뮬레이션: AI 예측값을 약간 조정
        expert_adjustments = {}
        for key, value in ai_predictions.items():
            # ±10% 범위에서 조정 (시뮬레이션)
            adjustment = np.random.uniform(-0.1, 0.1)
            expert_adjustments[key] = max(0, min(1, value + adjustment))
        
        # 표준화 평가 도구 점수 (시뮬레이션)
        standardized = StandardizedAssessment(
            phq9_score=int(expert_adjustments.get('depression_risk', 0.5) * 27),
            gad7_score=int(expert_adjustments.get('anxiety_level', 0.3) * 21)
        )
        
        return EvaluationResult(
            evaluation_id=self._generate_id(),
            timestamp=datetime.now(),
            value=expert_adjustments,
            confidence=min(0.9, ai_confidence + 0.2),  # 전문가 검토로 신뢰도 상승
            source=EvaluationSource.EXPERT_VALIDATED,
            evaluation_level=EvaluationLevel.LEVEL_2,
            risk_level=self._assess_risk_level(expert_adjustments),
            requires_expert_review=False,
            standardized_assessment=standardized,
            expert_id="expert_001",  # 시뮬레이션
            expert_notes="AI 예측 검토 및 조정 완료"
        )
    
    def _create_ai_only_result(
        self,
        predictions: Dict[str, float],
        confidence: float,
        risk_level: RiskLevel
    ) -> EvaluationResult:
        """AI 전용 결과 생성"""
        
        return EvaluationResult(
            evaluation_id=self._generate_id(),
            timestamp=datetime.now(),
            value=predictions,
            confidence=confidence,
            source=EvaluationSource.AI_ONLY,
            evaluation_level=EvaluationLevel.LEVEL_1,
            risk_level=risk_level,
            requires_expert_review=False,
            development_phase=True,
            not_for_clinical_use=True
        )
    
    def _update_statistics(self, result: EvaluationResult):
        """통계 업데이트"""
        self.evaluation_stats['total_evaluations'] += 1
        
        if result.source == EvaluationSource.AI_ONLY:
            self.evaluation_stats['ai_only'] += 1
        elif result.source in [EvaluationSource.EXPERT_VALIDATED, EvaluationSource.EXPERT_LABELED]:
            self.evaluation_stats['expert_reviewed'] += 1
    
    def _generate_id(self) -> str:
        """평가 ID 생성"""
        import uuid
        return f"eval_{uuid.uuid4().hex[:8]}"
    
    def get_statistics(self) -> Dict[str, Any]:
        """평가 통계 조회"""
        total = self.evaluation_stats['total_evaluations']
        if total == 0:
            return self.evaluation_stats
        
        return {
            **self.evaluation_stats,
            'ai_only_percentage': self.evaluation_stats['ai_only'] / total * 100,
            'expert_review_rate': self.evaluation_stats['expert_reviewed'] / total * 100
        }


class HybridEvaluationPipeline:
    """하이브리드 평가 파이프라인"""
    
    def __init__(self):
        self.expert_system = ExpertEvaluationSystem()
        self.development_mode = True  # 개발 모드
        
    def process(
        self,
        audio_path: str,
        ai_model_output: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        전체 평가 파이프라인
        
        Args:
            audio_path: 오디오 파일 경로
            ai_model_output: AI 모델 출력
            
        Returns:
            통합 평가 결과
        """
        
        # AI 예측 추출
        ai_predictions = ai_model_output.get('predictions', {})
        audio_features = ai_model_output.get('features', {})
        
        # 하이브리드 평가
        evaluation = self.expert_system.evaluate(
            audio_features=audio_features,
            ai_predictions=ai_predictions,
            force_expert=False  # 개발 단계에서는 선택적
        )
        
        # 결과 포맷팅
        result = {
            'evaluation': evaluation.to_dict(),
            'metadata': {
                'pipeline_version': '2.0.0',
                'development_mode': self.development_mode,
                'timestamp': datetime.now().isoformat(),
                'audio_path': audio_path
            },
            'warnings': self._generate_warnings(evaluation)
        }
        
        return result
    
    def _generate_warnings(self, evaluation: EvaluationResult) -> List[str]:
        """경고 메시지 생성"""
        warnings = []
        
        if evaluation.development_phase:
            warnings.append("⚠️ 개발 단계 - 임상 사용 불가")
        
        if evaluation.source == EvaluationSource.AI_ONLY:
            warnings.append("⚠️ AI 전용 평가 - 전문가 검증 필요")
        
        if evaluation.confidence < 0.7:
            warnings.append("⚠️ 낮은 신뢰도 - 결과 해석 주의")
        
        if evaluation.risk_level in [RiskLevel.HIGH, RiskLevel.CRITICAL]:
            warnings.append("⚠️ 고위험 지표 - 즉시 전문가 상담 권장")
        
        return warnings


def create_development_evaluation() -> HybridEvaluationPipeline:
    """개발용 평가 파이프라인 생성"""
    pipeline = HybridEvaluationPipeline()
    pipeline.development_mode = True
    
    logger.info("개발용 하이브리드 평가 파이프라인 생성")
    logger.warning("⚠️ 이 시스템은 개발 단계이며 임상 사용이 불가합니다")
    
    return pipeline