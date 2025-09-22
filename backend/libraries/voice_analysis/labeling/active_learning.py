"""
능동 학습 - 가장 가치있는 데이터 선택
불확실성이 높거나 모델 개선에 도움이 되는 샘플을 전문가 레이블링용으로 선택
"""

import numpy as np
from scipy.stats import entropy
from typing import List, Dict, Any, Tuple, Optional
from dataclasses import dataclass
import heapq
import logging

logger = logging.getLogger(__name__)


@dataclass
class QueuedSample:
    """전문가 레이블링 대기 샘플"""
    data_id: str
    data: Dict[str, Any]
    priority_score: float
    uncertainty: float
    diversity_score: float
    timestamp: str
    
    def __lt__(self, other):
        """우선순위 큐를 위한 비교 연산자"""
        return self.priority_score > other.priority_score  # 높은 점수가 우선


class ActiveLearning:
    """불확실성 기반 샘플 선택"""
    
    def __init__(self, budget_per_batch: int = 10):
        """
        Args:
            budget_per_batch: 배치당 전문가 레이블링 예산 (샘플 수)
        """
        self.budget = budget_per_batch
        self.expert_queue: List[QueuedSample] = []
        self.labeled_embeddings = []  # 이미 레이블된 데이터의 임베딩
        self.uncertainty_threshold = 0.7
        
        logger.info(f"Active Learning initialized with budget: {budget_per_batch} samples/batch")
    
    def calculate_uncertainty(self, data: Dict[str, Any], 
                            model_predictions: Optional[np.ndarray] = None) -> float:
        """
        예측 불확실성 계산
        
        Args:
            data: 평가할 데이터
            model_predictions: 모델 예측 확률 분포
            
        Returns:
            불확실성 점수 (0-1, 높을수록 불확실)
        """
        if model_predictions is None:
            # 실제로는 모델을 로드하여 예측
            model_predictions = self._get_model_predictions(data)
        
        if model_predictions is None or len(model_predictions) == 0:
            return 1.0  # 예측 불가능한 경우 최대 불확실성
        
        # Shannon entropy 계산
        uncertainty = entropy(model_predictions)
        
        # 정규화 (0-1 범위)
        max_entropy = np.log(len(model_predictions))
        if max_entropy > 0:
            uncertainty = uncertainty / max_entropy
        
        return float(uncertainty)
    
    def is_valuable(self, data: Dict[str, Any]) -> bool:
        """
        레이블링 가치 평가
        
        Args:
            data: 평가할 데이터
            
        Returns:
            전문가 레이블링이 필요한지 여부
        """
        # 1. 불확실성 평가
        uncertainty = self.calculate_uncertainty(data)
        
        if uncertainty > self.uncertainty_threshold:
            return True
        
        # 2. 대표성 평가 (다양성)
        if self.is_representative(data):
            return True
        
        # 3. 경계선 샘플 감지
        if self.is_boundary_sample(data):
            return True
        
        return False
    
    def queue_for_expert(self, data_id: str, data: Dict[str, Any], 
                        uncertainty: Optional[float] = None):
        """
        전문가 레이블링 큐에 추가
        
        Args:
            data_id: 데이터 ID
            data: 원시 데이터
            uncertainty: 불확실성 점수 (미리 계산된 경우)
        """
        if uncertainty is None:
            uncertainty = self.calculate_uncertainty(data)
        
        # 다양성 점수 계산
        diversity = self.calculate_diversity(data)
        
        # 예상 모델 개선도 계산
        impact = self.estimate_impact(data)
        
        # 종합 우선순위 점수
        priority_score = self._calculate_priority(uncertainty, diversity, impact)
        
        # 큐에 추가
        sample = QueuedSample(
            data_id=data_id,
            data=data,
            priority_score=priority_score,
            uncertainty=uncertainty,
            diversity_score=diversity,
            timestamp=str(np.datetime64('now'))
        )
        
        heapq.heappush(self.expert_queue, sample)
        logger.info(f"Queued {data_id} for expert labeling (priority: {priority_score:.3f})")
    
    def select_batch_for_labeling(self, unlabeled_pool: List[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """
        배치 선택 전략 - 가장 가치있는 샘플들 선택
        
        Args:
            unlabeled_pool: 레이블되지 않은 데이터 풀 (None이면 큐에서 선택)
            
        Returns:
            전문가 레이블링을 위한 샘플 리스트
        """
        if unlabeled_pool is not None:
            # 새로운 풀에서 선택
            scores = []
            
            for data in unlabeled_pool:
                # 1. Uncertainty sampling
                uncertainty = self.calculate_uncertainty(data)
                
                # 2. Diversity sampling
                diversity = self.calculate_diversity(data)
                
                # 3. Expected model change
                impact = self.estimate_impact(data)
                
                # Combined score
                score = self._calculate_priority(uncertainty, diversity, impact)
                scores.append((data, score))
            
            # Top-k selection
            scores.sort(key=lambda x: x[1], reverse=True)
            selected = [data for data, _ in scores[:self.budget]]
            
        else:
            # 기존 큐에서 선택
            selected = []
            for _ in range(min(self.budget, len(self.expert_queue))):
                if self.expert_queue:
                    sample = heapq.heappop(self.expert_queue)
                    selected.append(sample.data)
        
        logger.info(f"Selected {len(selected)} samples for expert labeling")
        return selected
    
    def is_representative(self, data: Dict[str, Any]) -> bool:
        """
        데이터가 전체 분포를 대표하는지 평가
        
        Args:
            data: 평가할 데이터
            
        Returns:
            대표성 여부
        """
        # 데이터의 임베딩 계산
        embedding = self._get_embedding(data)
        
        if embedding is None or len(self.labeled_embeddings) == 0:
            return True  # 초기에는 모든 샘플이 대표적
        
        # 기존 레이블 데이터와의 최소 거리
        min_distance = float('inf')
        for labeled_emb in self.labeled_embeddings:
            distance = np.linalg.norm(embedding - labeled_emb)
            min_distance = min(min_distance, distance)
        
        # 거리가 충분히 멀면 대표적 (새로운 영역)
        return min_distance > 0.5
    
    def is_boundary_sample(self, data: Dict[str, Any]) -> bool:
        """
        결정 경계 근처의 샘플인지 평가
        
        Args:
            data: 평가할 데이터
            
        Returns:
            경계선 샘플 여부
        """
        predictions = self._get_model_predictions(data)
        
        if predictions is None:
            return False
        
        # 상위 2개 클래스의 확률 차이
        sorted_probs = sorted(predictions, reverse=True)
        
        if len(sorted_probs) >= 2:
            margin = sorted_probs[0] - sorted_probs[1]
            # 차이가 작으면 경계선 샘플
            return margin < 0.2
        
        return False
    
    def calculate_diversity(self, data: Dict[str, Any]) -> float:
        """
        다양성 점수 계산 - 기존 데이터와 얼마나 다른지
        
        Args:
            data: 평가할 데이터
            
        Returns:
            다양성 점수 (0-1)
        """
        embedding = self._get_embedding(data)
        
        if embedding is None or len(self.labeled_embeddings) == 0:
            return 1.0
        
        # 평균 거리 계산
        distances = []
        for labeled_emb in self.labeled_embeddings[-100:]:  # 최근 100개만
            distance = np.linalg.norm(embedding - labeled_emb)
            distances.append(distance)
        
        avg_distance = np.mean(distances)
        
        # 정규화 (시그모이드 함수 사용)
        diversity = 2 / (1 + np.exp(-avg_distance)) - 1
        
        return float(diversity)
    
    def estimate_impact(self, data: Dict[str, Any]) -> float:
        """
        모델 개선 예상 효과 추정
        
        Args:
            data: 평가할 데이터
            
        Returns:
            예상 영향도 (0-1)
        """
        # 간단한 휴리스틱: 불확실성이 높고 빈도가 높은 패턴일수록 영향도 높음
        uncertainty = self.calculate_uncertainty(data)
        
        # 패턴 빈도 추정 (실제로는 클러스터링 등 사용)
        frequency = self._estimate_pattern_frequency(data)
        
        # 영향도 = 불확실성 × 빈도
        impact = uncertainty * frequency
        
        return float(impact)
    
    def _calculate_priority(self, uncertainty: float, diversity: float, impact: float) -> float:
        """
        종합 우선순위 점수 계산
        
        Args:
            uncertainty: 불확실성 점수
            diversity: 다양성 점수
            impact: 예상 영향도
            
        Returns:
            우선순위 점수
        """
        # 가중 평균
        priority = (0.5 * uncertainty + 
                   0.3 * diversity + 
                   0.2 * impact)
        
        return priority
    
    def _get_model_predictions(self, data: Dict[str, Any]) -> Optional[np.ndarray]:
        """
        모델 예측 확률 얻기
        
        Args:
            data: 예측할 데이터
            
        Returns:
            클래스별 확률 분포
        """
        # TODO: 실제 모델 로드 및 예측
        # 임시로 랜덤 확률 반환
        num_classes = 4  # depression, anxiety, normal, other
        predictions = np.random.dirichlet(np.ones(num_classes))
        return predictions
    
    def _get_embedding(self, data: Dict[str, Any]) -> Optional[np.ndarray]:
        """
        데이터의 임베딩 벡터 계산
        
        Args:
            data: 임베딩할 데이터
            
        Returns:
            임베딩 벡터
        """
        # TODO: 실제 임베딩 모델 사용
        # 임시로 랜덤 벡터 반환
        embedding_dim = 128
        return np.random.randn(embedding_dim)
    
    def _estimate_pattern_frequency(self, data: Dict[str, Any]) -> float:
        """
        패턴 빈도 추정
        
        Args:
            data: 평가할 데이터
            
        Returns:
            빈도 점수 (0-1)
        """
        # TODO: 실제 클러스터링 기반 빈도 계산
        # 임시로 랜덤 값 반환
        return np.random.random()
    
    def update_with_expert_label(self, data_id: str, label: str):
        """
        전문가 레이블 받은 후 업데이트
        
        Args:
            data_id: 레이블된 데이터 ID
            label: 전문가가 부여한 레이블
        """
        # 큐에서 제거
        self.expert_queue = [s for s in self.expert_queue if s.data_id != data_id]
        
        # TODO: 레이블된 데이터의 임베딩을 저장
        # self.labeled_embeddings.append(embedding)
        
        logger.info(f"Updated active learning with expert label for {data_id}: {label}")
    
    def get_queue_statistics(self) -> Dict:
        """큐 통계 반환"""
        if not self.expert_queue:
            return {
                'queue_size': 0,
                'avg_uncertainty': 0,
                'avg_priority': 0
            }
        
        uncertainties = [s.uncertainty for s in self.expert_queue]
        priorities = [s.priority_score for s in self.expert_queue]
        
        return {
            'queue_size': len(self.expert_queue),
            'avg_uncertainty': np.mean(uncertainties),
            'avg_priority': np.mean(priorities),
            'max_uncertainty': np.max(uncertainties),
            'min_uncertainty': np.min(uncertainties)
        }