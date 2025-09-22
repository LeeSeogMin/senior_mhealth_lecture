"""
레이블링 데이터 스키마 정의
Firestore 문서 구조 및 BigQuery 테이블 스키마
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, Optional, List, Any
from enum import Enum


class DataSource(Enum):
    """데이터 출처"""
    AI_GENERATED = "ai_generated"
    EXPERT_VALIDATED = "expert_validated"
    CLINICAL_VALIDATED = "clinical_validated"
    WEAK_SUPERVISION = "weak_supervision"
    PSEUDO_LABEL = "pseudo_label"


@dataclass
class LabeledDataSchema:
    """Firestore 문서 구조"""
    
    # === Primary Fields ===
    data_id: str  # UUID
    user_id: str  # 익명화된 사용자 ID
    session_id: str
    
    # === Raw Data ===
    raw_audio_path: str  # GCS path: gs://senior-mhealth/audio/{user_id}/{timestamp}.wav
    transcription: str
    audio_features: Dict[str, Any]  # MFCC, pitch, energy 등
    
    # === Labels ===
    label: str  # 'depression', 'anxiety', 'normal' 등
    label_source: str  # DataSource enum value
    label_confidence: float
    label_timestamp: datetime
    
    # === Clinical Scores (if available) ===
    phq9_score: Optional[int] = None
    gad7_score: Optional[int] = None
    other_scores: Dict[str, float] = field(default_factory=dict)
    
    # === Metadata ===
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    version: int = 1
    
    # === Validation ===
    is_validated: bool = False
    validation_method: Optional[str] = None
    validator_id: Optional[str] = None
    clinical_outcome: Optional[Dict] = None
    
    # === Quality Metrics ===
    quality_score: float = 0.0
    requires_review: bool = False
    review_notes: Optional[str] = None
    
    # === Development Flags ===
    development_only: bool = True  # 개발용 데이터 명시
    can_use_for_training: bool = False
    
    def to_firestore_dict(self) -> Dict:
        """Firestore 저장용 딕셔너리 변환"""
        return {
            'data_id': self.data_id,
            'user_id': self.user_id,
            'session_id': self.session_id,
            'raw_audio_path': self.raw_audio_path,
            'transcription': self.transcription,
            'audio_features': self.audio_features,
            'label': self.label,
            'label_source': self.label_source,
            'label_confidence': self.label_confidence,
            'label_timestamp': self.label_timestamp.isoformat(),
            'phq9_score': self.phq9_score,
            'gad7_score': self.gad7_score,
            'other_scores': self.other_scores,
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat(),
            'version': self.version,
            'is_validated': self.is_validated,
            'validation_method': self.validation_method,
            'validator_id': self.validator_id,
            'clinical_outcome': self.clinical_outcome,
            'quality_score': self.quality_score,
            'requires_review': self.requires_review,
            'review_notes': self.review_notes,
            'development_only': self.development_only,
            'can_use_for_training': self.can_use_for_training
        }
    
    @classmethod
    def from_firestore_dict(cls, data: Dict) -> 'LabeledDataSchema':
        """Firestore 문서에서 객체 생성"""
        return cls(
            data_id=data['data_id'],
            user_id=data['user_id'],
            session_id=data['session_id'],
            raw_audio_path=data['raw_audio_path'],
            transcription=data['transcription'],
            audio_features=data['audio_features'],
            label=data['label'],
            label_source=data['label_source'],
            label_confidence=data['label_confidence'],
            label_timestamp=datetime.fromisoformat(data['label_timestamp']),
            phq9_score=data.get('phq9_score'),
            gad7_score=data.get('gad7_score'),
            other_scores=data.get('other_scores', {}),
            created_at=datetime.fromisoformat(data['created_at']),
            updated_at=datetime.fromisoformat(data['updated_at']),
            version=data['version'],
            is_validated=data['is_validated'],
            validation_method=data.get('validation_method'),
            validator_id=data.get('validator_id'),
            clinical_outcome=data.get('clinical_outcome'),
            quality_score=data['quality_score'],
            requires_review=data['requires_review'],
            review_notes=data.get('review_notes'),
            development_only=data.get('development_only', True),
            can_use_for_training=data.get('can_use_for_training', False)
        )


@dataclass
class LabelingQueueSchema:
    """Active Learning 큐 스키마"""
    queue_id: str
    data_id: str
    priority_score: float
    uncertainty_score: float
    diversity_score: float
    requested_at: datetime
    assigned_to: Optional[str] = None
    status: str = 'pending'  # pending, assigned, completed, expired
    
    def to_firestore_dict(self) -> Dict:
        return {
            'queue_id': self.queue_id,
            'data_id': self.data_id,
            'priority_score': self.priority_score,
            'uncertainty_score': self.uncertainty_score,
            'diversity_score': self.diversity_score,
            'requested_at': self.requested_at.isoformat(),
            'assigned_to': self.assigned_to,
            'status': self.status
        }


@dataclass
class ValidationTrackingSchema:
    """장기 추적 검증 스키마"""
    tracking_id: str
    user_id: str
    predictions: List[Dict[str, Any]]
    follow_up_date: datetime
    clinical_appointments: List[Dict[str, Any]]
    validation_status: str = 'pending'  # pending, in_progress, completed
    
    def to_firestore_dict(self) -> Dict:
        return {
            'tracking_id': self.tracking_id,
            'user_id': self.user_id,
            'predictions': self.predictions,
            'follow_up_date': self.follow_up_date.isoformat(),
            'clinical_appointments': self.clinical_appointments,
            'validation_status': self.validation_status
        }


class FirestoreCollections:
    """Firestore 컬렉션 이름"""
    LABELED_DATA = 'labeled_data'
    LABELING_QUEUE = 'labeling_queue'
    VALIDATION_TRACKING = 'validation_tracking'
    LABEL_HISTORY = 'label_history'
    QUALITY_REVIEWS = 'quality_reviews'


def get_bigquery_schema():
    """BigQuery 테이블 스키마 반환"""
    return [
        {'name': 'data_id', 'type': 'STRING', 'mode': 'REQUIRED'},
        {'name': 'user_id', 'type': 'STRING', 'mode': 'REQUIRED'},
        {'name': 'session_id', 'type': 'STRING', 'mode': 'NULLABLE'},
        {'name': 'audio_gcs_path', 'type': 'STRING', 'mode': 'REQUIRED'},
        {'name': 'audio_duration_seconds', 'type': 'FLOAT64', 'mode': 'NULLABLE'},
        {'name': 'transcription', 'type': 'STRING', 'mode': 'NULLABLE'},
        {'name': 'mfcc_features', 'type': 'FLOAT64', 'mode': 'REPEATED'},
        {'name': 'pitch_mean', 'type': 'FLOAT64', 'mode': 'NULLABLE'},
        {'name': 'pitch_std', 'type': 'FLOAT64', 'mode': 'NULLABLE'},
        {'name': 'energy_mean', 'type': 'FLOAT64', 'mode': 'NULLABLE'},
        {'name': 'energy_std', 'type': 'FLOAT64', 'mode': 'NULLABLE'},
        {'name': 'label', 'type': 'STRING', 'mode': 'REQUIRED'},
        {'name': 'label_source', 'type': 'STRING', 'mode': 'REQUIRED'},
        {'name': 'label_confidence', 'type': 'FLOAT64', 'mode': 'REQUIRED'},
        {'name': 'label_timestamp', 'type': 'TIMESTAMP', 'mode': 'REQUIRED'},
        {'name': 'phq9_score', 'type': 'INT64', 'mode': 'NULLABLE'},
        {'name': 'gad7_score', 'type': 'INT64', 'mode': 'NULLABLE'},
        {'name': 'is_validated', 'type': 'BOOL', 'mode': 'REQUIRED'},
        {'name': 'validation_method', 'type': 'STRING', 'mode': 'NULLABLE'},
        {'name': 'quality_score', 'type': 'FLOAT64', 'mode': 'REQUIRED'},
        {'name': 'development_only', 'type': 'BOOL', 'mode': 'REQUIRED'},
        {'name': 'can_use_for_training', 'type': 'BOOL', 'mode': 'REQUIRED'},
        {'name': 'created_at', 'type': 'TIMESTAMP', 'mode': 'REQUIRED'},
        {'name': 'updated_at', 'type': 'TIMESTAMP', 'mode': 'REQUIRED'},
        {'name': 'partition_date', 'type': 'DATE', 'mode': 'REQUIRED'}
    ]