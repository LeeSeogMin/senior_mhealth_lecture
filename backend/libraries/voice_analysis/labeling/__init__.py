"""
스마트 레이블링 시스템
Ground Truth 생성을 위한 다층적 레이블링 전략
"""

from .smart_labeling_system import (
    SmartLabelingSystem,
    LabeledData,
    LabelSource,
    ConfidenceLevel
)
from .weak_supervision import WeakSupervision, WeakLabel
from .active_learning import ActiveLearning, QueuedSample
from .pseudo_labeling import PseudoLabeling, PseudoLabel
from .outcome_validation import OutcomeTracker, ValidationResult

__all__ = [
    'SmartLabelingSystem',
    'LabeledData',
    'LabelSource',
    'ConfidenceLevel',
    'WeakSupervision',
    'WeakLabel',
    'ActiveLearning',
    'QueuedSample',
    'PseudoLabeling',
    'PseudoLabel',
    'OutcomeTracker',
    'ValidationResult'
]

__version__ = '1.0.0'