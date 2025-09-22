"""
장기 임상 결과 기반 검증
실제 임상 결과를 통해 AI 예측을 검증하고 Ground Truth 생성
"""

from typing import Dict, Any, Optional, List
from dataclasses import dataclass, field
from datetime import datetime, timedelta
import logging
import json

logger = logging.getLogger(__name__)


@dataclass
class PredictionRecord:
    """예측 기록"""
    user_id: str
    data_id: str
    prediction: Dict[str, Any]
    timestamp: datetime
    follow_up_date: datetime
    metadata: Dict = field(default_factory=dict)


@dataclass
class ValidationResult:
    """검증 결과"""
    user_id: str
    data_id: str
    original_prediction: Dict[str, Any]
    actual_outcome: Dict[str, Any]
    match_score: float
    time_delta_days: int
    is_validated: bool
    validation_details: Dict = field(default_factory=dict)


class OutcomeTracker:
    """실제 임상 결과 추적 및 검증"""
    
    def __init__(self, validation_window_days: int = 180):
        """
        Args:
            validation_window_days: 검증 기간 (일)
        """
        self.validation_window = validation_window_days
        self.predictions_cache = {}  # 메모리 캐시 (실제로는 DB 사용)
        self.validation_results = []
        self.ground_truth_data = []
        
        logger.info(f"Outcome Tracker initialized with {validation_window_days} days validation window")
    
    async def track_prediction(self, user_id: str, data_id: str, 
                              prediction: Dict[str, Any]) -> PredictionRecord:
        """
        예측 저장 및 추적 시작
        
        Args:
            user_id: 사용자 ID
            data_id: 데이터 ID
            prediction: AI 예측 결과
            
        Returns:
            예측 기록
        """
        record = PredictionRecord(
            user_id=user_id,
            data_id=data_id,
            prediction=prediction,
            timestamp=datetime.now(),
            follow_up_date=datetime.now() + timedelta(days=self.validation_window),
            metadata={
                'model_version': prediction.get('model_version', 'unknown'),
                'confidence': prediction.get('confidence', 0.0)
            }
        )
        
        # 캐시에 저장
        self.predictions_cache[user_id] = record
        
        logger.info(f"Tracking prediction for user {user_id}, follow-up scheduled for {record.follow_up_date}")
        
        # TODO: Firestore에 저장
        await self._save_to_firestore(record)
        
        return record
    
    async def validate_with_outcome(self, user_id: str, 
                                   clinical_outcome: Dict[str, Any]) -> Optional[ValidationResult]:
        """
        실제 임상 결과와 비교
        
        Args:
            user_id: 사용자 ID
            clinical_outcome: 실제 임상 결과
            
        Returns:
            검증 결과 또는 None
        """
        if user_id not in self.predictions_cache:
            # DB에서 조회
            record = await self._load_from_firestore(user_id)
            if not record:
                logger.warning(f"No prediction found for user {user_id}")
                return None
        else:
            record = self.predictions_cache[user_id]
        
        # 검증 수행
        match_score = self.calculate_match(record.prediction, clinical_outcome)
        time_delta = (datetime.now() - record.timestamp).days
        
        validation_result = ValidationResult(
            user_id=user_id,
            data_id=record.data_id,
            original_prediction=record.prediction,
            actual_outcome=clinical_outcome,
            match_score=match_score,
            time_delta_days=time_delta,
            is_validated=match_score > 0.7,  # 70% 이상 일치시 검증됨
            validation_details=self._create_validation_details(record.prediction, clinical_outcome)
        )
        
        # 결과 저장
        self.validation_results.append(validation_result)
        
        # Ground Truth로 저장 (높은 일치도)
        if validation_result.is_validated:
            await self.save_as_ground_truth(validation_result)
        
        logger.info(f"Validation for user {user_id}: match score {match_score:.2f}")
        
        return validation_result
    
    def calculate_match(self, prediction: Dict[str, Any], 
                       clinical_outcome: Dict[str, Any]) -> float:
        """
        예측과 실제 결과 일치도 계산
        
        Args:
            prediction: AI 예측
            clinical_outcome: 실제 임상 결과
            
        Returns:
            일치도 점수 (0-1)
        """
        score = 0.0
        weights = {
            'primary_diagnosis': 0.5,
            'severity': 0.2,
            'symptoms': 0.2,
            'treatment_response': 0.1
        }
        
        # 1. 주 진단 일치도
        if 'diagnosis' in prediction and 'diagnosis' in clinical_outcome:
            pred_diagnosis = prediction['diagnosis']
            actual_diagnosis = clinical_outcome['diagnosis']
            
            if pred_diagnosis == actual_diagnosis:
                score += weights['primary_diagnosis']
            elif self._are_related_diagnoses(pred_diagnosis, actual_diagnosis):
                score += weights['primary_diagnosis'] * 0.5
        
        # 2. 심각도 일치도
        if 'severity' in prediction and 'severity' in clinical_outcome:
            pred_severity = prediction['severity']
            actual_severity = clinical_outcome['severity']
            
            severity_diff = abs(self._severity_to_numeric(pred_severity) - 
                              self._severity_to_numeric(actual_severity))
            
            if severity_diff == 0:
                score += weights['severity']
            elif severity_diff == 1:
                score += weights['severity'] * 0.5
        
        # 3. 증상 일치도
        if 'symptoms' in prediction and 'symptoms' in clinical_outcome:
            pred_symptoms = set(prediction.get('symptoms', []))
            actual_symptoms = set(clinical_outcome.get('symptoms', []))
            
            if pred_symptoms and actual_symptoms:
                overlap = len(pred_symptoms & actual_symptoms)
                total = len(pred_symptoms | actual_symptoms)
                symptom_score = overlap / total if total > 0 else 0
                score += weights['symptoms'] * symptom_score
        
        # 4. 치료 반응 예측 정확도 (있는 경우)
        if 'treatment_response' in clinical_outcome:
            # 치료 반응이 좋았는지 확인
            if clinical_outcome['treatment_response'] == 'positive':
                # 예측이 정확했다면 보너스
                if prediction.get('confidence', 0) > 0.7:
                    score += weights['treatment_response']
        
        return min(score, 1.0)
    
    def _are_related_diagnoses(self, diag1: str, diag2: str) -> bool:
        """
        관련된 진단인지 확인
        
        Args:
            diag1: 진단 1
            diag2: 진단 2
            
        Returns:
            관련 여부
        """
        related_groups = [
            {'depression', 'major_depression', 'moderate_depression', 'mild_depression'},
            {'anxiety', 'generalized_anxiety', 'panic_disorder', 'social_anxiety'},
            {'bipolar', 'bipolar_1', 'bipolar_2', 'cyclothymia'},
            {'ptsd', 'acute_stress', 'adjustment_disorder'}
        ]
        
        for group in related_groups:
            if diag1 in group and diag2 in group:
                return True
        
        return False
    
    def _severity_to_numeric(self, severity: str) -> int:
        """심각도를 숫자로 변환"""
        severity_map = {
            'minimal': 1,
            'mild': 2,
            'moderate': 3,
            'moderately_severe': 4,
            'severe': 5
        }
        return severity_map.get(severity, 0)
    
    def _create_validation_details(self, prediction: Dict, outcome: Dict) -> Dict:
        """
        검증 상세 정보 생성
        
        Args:
            prediction: 예측
            outcome: 실제 결과
            
        Returns:
            상세 검증 정보
        """
        details = {
            'diagnosis_match': prediction.get('diagnosis') == outcome.get('diagnosis'),
            'severity_match': prediction.get('severity') == outcome.get('severity'),
            'confidence_was': prediction.get('confidence', 0),
            'actual_diagnosis': outcome.get('diagnosis'),
            'predicted_diagnosis': prediction.get('diagnosis'),
            'clinical_notes': outcome.get('notes', '')
        }
        
        # 증상 비교
        if 'symptoms' in prediction and 'symptoms' in outcome:
            pred_symptoms = set(prediction['symptoms'])
            actual_symptoms = set(outcome['symptoms'])
            
            details['symptoms_comparison'] = {
                'correctly_predicted': list(pred_symptoms & actual_symptoms),
                'missed': list(actual_symptoms - pred_symptoms),
                'false_positives': list(pred_symptoms - actual_symptoms)
            }
        
        return details
    
    async def save_as_ground_truth(self, validation_result: ValidationResult):
        """
        검증된 데이터를 Ground Truth로 저장
        
        Args:
            validation_result: 검증 결과
        """
        ground_truth = {
            'data_id': validation_result.data_id,
            'user_id': validation_result.user_id,
            'label': validation_result.actual_outcome.get('diagnosis'),
            'severity': validation_result.actual_outcome.get('severity'),
            'symptoms': validation_result.actual_outcome.get('symptoms', []),
            'source': 'clinical_validation',
            'confidence': 1.0,  # 실제 임상 결과는 최고 신뢰도
            'validation_date': datetime.now().isoformat(),
            'original_prediction': validation_result.original_prediction,
            'match_score': validation_result.match_score,
            'time_to_validation_days': validation_result.time_delta_days
        }
        
        self.ground_truth_data.append(ground_truth)
        
        # TODO: Firestore/BigQuery에 저장
        await self._save_ground_truth_to_db(ground_truth)
        
        logger.info(f"Saved ground truth for data_id {validation_result.data_id}")
    
    async def get_pending_validations(self) -> List[PredictionRecord]:
        """
        검증 대기 중인 예측들 조회
        
        Returns:
            검증 대기 예측 리스트
        """
        pending = []
        current_date = datetime.now()
        
        for user_id, record in self.predictions_cache.items():
            if record.follow_up_date <= current_date:
                pending.append(record)
        
        # TODO: DB에서도 조회
        db_pending = await self._load_pending_from_firestore(current_date)
        pending.extend(db_pending)
        
        logger.info(f"Found {len(pending)} predictions pending validation")
        return pending
    
    def get_validation_statistics(self) -> Dict:
        """검증 통계 반환"""
        if not self.validation_results:
            return {
                'total_validations': 0,
                'validated_count': 0,
                'validation_rate': 0.0,
                'avg_match_score': 0.0
            }
        
        validated = [v for v in self.validation_results if v.is_validated]
        match_scores = [v.match_score for v in self.validation_results]
        
        return {
            'total_validations': len(self.validation_results),
            'validated_count': len(validated),
            'validation_rate': len(validated) / len(self.validation_results),
            'avg_match_score': sum(match_scores) / len(match_scores),
            'ground_truth_generated': len(self.ground_truth_data),
            'avg_time_to_validation': sum(v.time_delta_days for v in self.validation_results) / len(self.validation_results)
        }
    
    # DB 연동 메서드들 (구현 필요)
    async def _save_to_firestore(self, record: PredictionRecord):
        """Firestore에 예측 기록 저장"""
        # TODO: 실제 Firestore 연동
        pass
    
    async def _load_from_firestore(self, user_id: str) -> Optional[PredictionRecord]:
        """Firestore에서 예측 기록 로드"""
        # TODO: 실제 Firestore 연동
        return None
    
    async def _save_ground_truth_to_db(self, ground_truth: Dict):
        """Ground Truth DB 저장"""
        # TODO: 실제 DB 연동
        pass
    
    async def _load_pending_from_firestore(self, current_date: datetime) -> List[PredictionRecord]:
        """Firestore에서 검증 대기 예측 로드"""
        # TODO: 실제 Firestore 연동
        return []