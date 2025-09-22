"""
Base interface for chain steps
체인 단계의 기본 인터페이스 정의
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


class BaseChainStep(ABC):
    """체인 단계 기본 인터페이스"""
    
    def __init__(self, name: str, timeout: float = 30.0):
        """
        Args:
            name: 단계 이름
            timeout: 타임아웃 시간 (초)
        """
        self.name = name
        self.timeout = timeout
        self.is_critical = False  # 위기 상황 감지 시 조기 종료 여부
        
    @abstractmethod
    async def process(self, audio_data: Any, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        단계 처리 메서드
        
        Args:
            audio_data: 오디오 데이터 또는 경로
            context: 이전 단계들의 실행 컨텍스트
            
        Returns:
            업데이트된 컨텍스트
        """
        pass
    
    def should_skip(self, context: Dict[str, Any]) -> bool:
        """
        이 단계를 건너뛸지 여부 결정
        
        Args:
            context: 현재 컨텍스트
            
        Returns:
            True면 건너뛰기, False면 실행
        """
        # 위기 상황이 감지되고 이 단계가 critical이 아니면 건너뛰기
        if context.get('crisis', {}).get('severity') == 'critical' and not self.is_critical:
            logger.info(f"Skipping {self.name} due to critical situation")
            return True
        return False
    
    async def handle_error(self, error: Exception, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        에러 처리 메서드
        
        Args:
            error: 발생한 에러
            context: 현재 컨텍스트
            
        Returns:
            에러 정보가 추가된 컨텍스트
        """
        logger.error(f"Error in {self.name}: {str(error)}")
        context[f'{self.name}_error'] = {
            'error': str(error),
            'timestamp': datetime.now().isoformat()
        }
        return context


class CrisisResult:
    """위기 감지 결과 모델"""
    
    def __init__(self, 
                 severity: str,
                 confidence: float,
                 detected_patterns: list,
                 immediate_action_required: bool = False,
                 message: Optional[str] = None):
        """
        Args:
            severity: 위험도 (critical/high/medium/low/none)
            confidence: 신뢰도 (0.0-1.0)
            detected_patterns: 감지된 위험 패턴 리스트
            immediate_action_required: 즉시 조치 필요 여부
            message: 추가 메시지
        """
        self.severity = severity
        self.confidence = confidence
        self.detected_patterns = detected_patterns
        self.immediate_action_required = immediate_action_required
        self.message = message
        self.timestamp = datetime.now().isoformat()
    
    def to_dict(self) -> Dict[str, Any]:
        """딕셔너리로 변환"""
        return {
            'severity': self.severity,
            'confidence': self.confidence,
            'detected_patterns': self.detected_patterns,
            'immediate_action_required': self.immediate_action_required,
            'message': self.message,
            'timestamp': self.timestamp
        }