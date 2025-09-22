"""
스마트 레이블링 통합 시스템
데이터 축적 및 Ground Truth 생성을 위한 다층적 레이블링 전략
"""

from enum import Enum
from typing import Dict, List, Optional, Tuple, Any
import numpy as np
from dataclasses import dataclass, field
from datetime import datetime
import logging
import json

logger = logging.getLogger(__name__)


class LabelSource(Enum):
    """레이블 출처 명시"""
    EXPERT = "expert"              # 전문가 직접 레이블
    WEAK_SUPERVISION = "weak"       # 약한 지도학습
    PSEUDO = "pseudo"               # 모델 예측 (고신뢰도)
    ACTIVE_LEARNING = "active"      # 능동 학습 선택
    OUTCOME_BASED = "outcome"       # 임상 결과 기반
    LLM_CONSENSUS = "llm_consensus" # LLM 합의 기반 (준전문가)


class ConfidenceLevel(Enum):
    """신뢰도 수준"""
    VERY_HIGH = 0.95   # 즉시 사용 가능
    HIGH = 0.90        # 검토 후 사용
    MEDIUM = 0.80      # 추가 검증 필요
    LOW = 0.70         # 참고용
    VERY_LOW = 0.50    # 사용 불가


@dataclass
class LabeledData:
    """레이블링된 데이터 구조"""
    data_id: str
    raw_data: Dict[str, Any]
    label: str
    source: LabelSource
    confidence: float
    timestamp: datetime = field(default_factory=datetime.now)
    validator_id: Optional[str] = None
    clinical_outcome: Optional[Dict] = None
    metadata: Dict = field(default_factory=dict)
    
    def to_dict(self) -> Dict:
        """Firestore 저장용 딕셔너리 변환"""
        return {
            'data_id': self.data_id,
            'raw_data': self.raw_data,
            'label': self.label,
            'source': self.source.value,
            'confidence': self.confidence,
            'timestamp': self.timestamp.isoformat(),
            'validator_id': self.validator_id,
            'clinical_outcome': self.clinical_outcome,
            'metadata': self.metadata
        }
    
    def is_high_quality(self) -> bool:
        """고품질 레이블 여부 판단"""
        if self.source == LabelSource.EXPERT:
            return True
        if self.source == LabelSource.OUTCOME_BASED:
            return True
        if self.confidence >= ConfidenceLevel.VERY_HIGH.value:
            return True
        return False


class SmartLabelingSystem:
    """통합 스마트 레이블링 시스템"""
    
    def __init__(self, config: Optional[Dict] = None):
        """
        Args:
            config: 레이블링 시스템 설정
        """
        self.config = config or self._get_default_config()
        
        # 레이블링 전략 컴포넌트 초기화
        from .weak_supervision import WeakSupervision
        from .active_learning import ActiveLearning
        from .pseudo_labeling import PseudoLabeling
        from .outcome_validation import OutcomeTracker
        from .llm_consensus_labeling import LLMConsensusLabeling
        
        self.weak_supervisor = WeakSupervision(
            confidence_threshold=self.config['weak_supervision']['confidence_threshold']
        )
        self.active_learner = ActiveLearning(
            budget_per_batch=self.config['active_learning']['budget_per_batch']
        )
        self.pseudo_labeler = PseudoLabeling(
            confidence_threshold=self.config['pseudo_labeling']['confidence_threshold']
        )
        self.outcome_tracker = OutcomeTracker()
        
        # LLM 합의 레이블링 (선택적)
        if self.config.get('llm_consensus', {}).get('enabled', False):
            self.llm_consensus = LLMConsensusLabeling(
                rag_knowledge_base=self.config['llm_consensus'].get('rag_kb')
            )
        else:
            self.llm_consensus = None
        
        # 통계 추적
        self.stats = {
            'total_processed': 0,
            'labeled': 0,
            'queued_for_expert': 0,
            'by_source': {source.value: 0 for source in LabelSource}
        }
        
        logger.info("Smart Labeling System initialized")
    
    def _get_default_config(self) -> Dict:
        """기본 설정값"""
        return {
            'weak_supervision': {
                'enabled': True,
                'confidence_threshold': 0.85
            },
            'pseudo_labeling': {
                'enabled': True,
                'confidence_threshold': 0.95
            },
            'active_learning': {
                'enabled': True,
                'budget_per_batch': 10,
                'uncertainty_threshold': 0.7
            },
            'outcome_validation': {
                'enabled': True,
                'follow_up_window_days': 180
            },
            'llm_consensus': {
                'enabled': True,  # LLM 합의 활성화
                'min_consensus': 0.75,  # 최소 75% 합의
                'require_unanimous_for_high_risk': True,  # 고위험은 만장일치 필요
                'rag_kb': None  # RAG 지식베이스 경로
            }
        }
    
    def process_new_data(self, data: Dict[str, Any]) -> Optional[LabeledData]:
        """
        새 데이터 처리 및 레이블링 전략 결정
        
        Args:
            data: 처리할 원시 데이터
            
        Returns:
            레이블링된 데이터 또는 None (레이블링 불가)
        """
        self.stats['total_processed'] += 1
        
        # 데이터 ID 생성
        data_id = self._generate_data_id(data)
        
        # 1. Weak Supervision 시도
        if self.config['weak_supervision']['enabled']:
            weak_label = self.weak_supervisor.generate_label(data)
            if weak_label and weak_label.confidence >= self.config['weak_supervision']['confidence_threshold']:
                labeled = LabeledData(
                    data_id=data_id,
                    raw_data=data,
                    label=weak_label.label,
                    source=LabelSource.WEAK_SUPERVISION,
                    confidence=weak_label.confidence,
                    metadata={'weak_rules_applied': weak_label.rules_applied}
                )
                self._update_stats(labeled)
                logger.info(f"Data {data_id} labeled via weak supervision: {weak_label.label} (conf: {weak_label.confidence:.2f})")
                return labeled
        
        # 2. LLM Consensus 시도 (Pseudo Labeling 전에)
        if self.llm_consensus and self.config['llm_consensus']['enabled']:
            import asyncio
            consensus = asyncio.run(self.llm_consensus.get_consensus_label(data))
            
            if consensus and consensus.consensus_level >= self.config['llm_consensus']['min_consensus']:
                # 고위험 케이스는 만장일치 필요
                if consensus.requires_expert_review and self.config['llm_consensus']['require_unanimous_for_high_risk']:
                    if not consensus.is_unanimous:
                        logger.info(f"High-risk case {data_id} requires unanimous consensus, queuing for expert")
                        self.active_learner.queue_for_expert(data_id, data, 1.0)
                        return None
                
                labeled = LabeledData(
                    data_id=data_id,
                    raw_data=data,
                    label=consensus.final_diagnosis,
                    source=LabelSource.LLM_CONSENSUS,
                    confidence=consensus.consensus_level,
                    metadata={
                        'severity': consensus.final_severity,
                        'num_llms': len(consensus.individual_judgments),
                        'is_unanimous': consensus.is_unanimous,
                        'requires_expert': consensus.requires_expert_review
                    }
                )
                self._update_stats(labeled)
                logger.info(f"Data {data_id} labeled via LLM consensus: {consensus.final_diagnosis} (consensus: {consensus.consensus_level:.2f})")
                return labeled
        
        # 3. Pseudo Labeling 시도
        if self.config['pseudo_labeling']['enabled']:
            pseudo_label = self.pseudo_labeler.predict(data)
            if pseudo_label and pseudo_label.confidence >= self.config['pseudo_labeling']['confidence_threshold']:
                labeled = LabeledData(
                    data_id=data_id,
                    raw_data=data,
                    label=pseudo_label.label,
                    source=LabelSource.PSEUDO,
                    confidence=pseudo_label.confidence,
                    metadata={'model_version': pseudo_label.model_version}
                )
                self._update_stats(labeled)
                logger.info(f"Data {data_id} labeled via pseudo labeling: {pseudo_label.label} (conf: {pseudo_label.confidence:.2f})")
                return labeled
        
        # 4. Active Learning 평가
        if self.config['active_learning']['enabled']:
            uncertainty = self.active_learner.calculate_uncertainty(data)
            if uncertainty > self.config['active_learning']['uncertainty_threshold']:
                self.active_learner.queue_for_expert(data_id, data, uncertainty)
                self.stats['queued_for_expert'] += 1
                logger.info(f"Data {data_id} queued for expert labeling (uncertainty: {uncertainty:.2f})")
                
                # Active Learning 큐에 추가했지만 일단 None 반환
                return None
        
        logger.warning(f"Data {data_id} could not be labeled by any strategy")
        return None
    
    def process_expert_label(self, data_id: str, data: Dict, label: str, expert_id: str) -> LabeledData:
        """
        전문가 레이블 처리
        
        Args:
            data_id: 데이터 ID
            data: 원시 데이터
            label: 전문가가 부여한 레이블
            expert_id: 전문가 ID
            
        Returns:
            레이블링된 데이터
        """
        labeled = LabeledData(
            data_id=data_id,
            raw_data=data,
            label=label,
            source=LabelSource.EXPERT,
            confidence=1.0,  # 전문가 레이블은 최고 신뢰도
            validator_id=expert_id,
            metadata={'expert_id': expert_id}
        )
        
        self._update_stats(labeled)
        logger.info(f"Expert label added for {data_id}: {label} by {expert_id}")
        
        # 전문가 레이블을 활용해 모델 개선
        self._improve_models_with_expert_label(labeled)
        
        return labeled
    
    def validate_with_outcome(self, data_id: str, clinical_outcome: Dict) -> Optional[LabeledData]:
        """
        임상 결과로 기존 레이블 검증
        
        Args:
            data_id: 데이터 ID
            clinical_outcome: 실제 임상 결과
            
        Returns:
            검증된 레이블 데이터
        """
        # 기존 예측 조회 (실제로는 DB에서 조회)
        original_prediction = self._get_original_prediction(data_id)
        
        if original_prediction:
            # 임상 결과와 비교
            match_score = self._calculate_outcome_match(
                original_prediction.label,
                clinical_outcome
            )
            
            if match_score > 0.8:  # 충분히 일치
                validated = LabeledData(
                    data_id=data_id,
                    raw_data=original_prediction.raw_data,
                    label=clinical_outcome.get('diagnosis', original_prediction.label),
                    source=LabelSource.OUTCOME_BASED,
                    confidence=1.0,  # 실제 결과는 최고 신뢰도
                    clinical_outcome=clinical_outcome,
                    metadata={
                        'original_label': original_prediction.label,
                        'original_source': original_prediction.source.value,
                        'match_score': match_score
                    }
                )
                
                self._update_stats(validated)
                logger.info(f"Outcome validation for {data_id}: match score {match_score:.2f}")
                return validated
        
        return None
    
    def get_training_data(self, min_confidence: float = 0.9) -> List[LabeledData]:
        """
        학습용 고품질 데이터 반환
        
        Args:
            min_confidence: 최소 신뢰도 임계값
            
        Returns:
            학습 가능한 레이블 데이터 리스트
        """
        # 실제로는 DB에서 조회
        training_data = []
        
        # 전문가 레이블 (모두 포함)
        # training_data.extend(self._get_expert_labels())
        
        # 고신뢰도 pseudo labels
        # training_data.extend(self._get_high_confidence_labels(min_confidence))
        
        # 검증된 outcome labels
        # training_data.extend(self._get_outcome_validated_labels())
        
        logger.info(f"Retrieved {len(training_data)} training samples")
        return training_data
    
    def get_statistics(self) -> Dict:
        """레이블링 통계 반환"""
        return {
            **self.stats,
            'confidence_distribution': self._get_confidence_distribution(),
            'label_distribution': self._get_label_distribution(),
            'quality_metrics': self._calculate_quality_metrics()
        }
    
    def _generate_data_id(self, data: Dict) -> str:
        """데이터 ID 생성"""
        import uuid
        # 실제로는 데이터 내용 기반 해시 등 사용
        return str(uuid.uuid4())
    
    def _update_stats(self, labeled: LabeledData):
        """통계 업데이트"""
        self.stats['labeled'] += 1
        self.stats['by_source'][labeled.source.value] += 1
    
    def _improve_models_with_expert_label(self, labeled: LabeledData):
        """전문가 레이블로 모델 개선"""
        # Weak supervision 규칙 업데이트
        self.weak_supervisor.update_rules_with_expert_label(labeled)
        
        # Pseudo labeling 모델 fine-tuning 트리거
        self.pseudo_labeler.add_to_fine_tuning_queue(labeled)
    
    def _get_original_prediction(self, data_id: str) -> Optional[LabeledData]:
        """기존 예측 조회 (DB 연동 필요)"""
        # Implementation needed: Firestore integration
        # For now, return None until Firestore connector is implemented
        return None
    
    def _calculate_outcome_match(self, predicted_label: str, clinical_outcome: Dict) -> float:
        """예측과 실제 결과 일치도 계산"""
        actual_label = clinical_outcome.get('diagnosis', '')
        
        # 단순 일치
        if predicted_label == actual_label:
            return 1.0
        
        # 유사도 계산 (실제로는 더 복잡한 로직)
        label_similarity = {
            ('depression', 'moderate_depression'): 0.8,
            ('anxiety', 'mild_anxiety'): 0.8,
            ('normal', 'subclinical'): 0.6
        }
        
        return label_similarity.get((predicted_label, actual_label), 0.0)
    
    def _get_confidence_distribution(self) -> Dict:
        """신뢰도 분포 (실제로는 DB 조회)"""
        return {
            'very_high': 0,
            'high': 0,
            'medium': 0,
            'low': 0
        }
    
    def _get_label_distribution(self) -> Dict:
        """레이블 분포 (실제로는 DB 조회)"""
        return {}
    
    def _calculate_quality_metrics(self) -> Dict:
        """품질 메트릭 계산"""
        total = self.stats['labeled']
        if total == 0:
            return {}
        
        return {
            'expert_ratio': self.stats['by_source'][LabelSource.EXPERT.value] / total,
            'pseudo_ratio': self.stats['by_source'][LabelSource.PSEUDO.value] / total,
            'weak_ratio': self.stats['by_source'][LabelSource.WEAK_SUPERVISION.value] / total
        }