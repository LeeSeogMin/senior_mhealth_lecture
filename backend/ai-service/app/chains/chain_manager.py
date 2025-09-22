"""
Chain Manager for Sequential Prompt Chaining
순차 프롬프트 체이닝을 위한 체인 관리자
"""

import asyncio
import logging
from typing import Dict, Any, List, Optional, Union
from datetime import datetime
import json
from pathlib import Path

from .base_step import BaseChainStep

logger = logging.getLogger(__name__)


class ChainManager:
    """체인 실행을 관리하는 오케스트레이터"""
    
    def __init__(self, cache_enabled: bool = True):
        """
        Args:
            cache_enabled: 중간 결과 캐싱 활성화 여부
        """
        self.steps: List[BaseChainStep] = []
        self.cache: Dict[str, Any] = {}
        self.cache_enabled = cache_enabled
        self.execution_history: List[Dict[str, Any]] = []
        
    def add_step(self, step: BaseChainStep) -> 'ChainManager':
        """
        체인에 단계 추가
        
        Args:
            step: 추가할 체인 단계
            
        Returns:
            self (메서드 체이닝용)
        """
        self.steps.append(step)
        logger.info(f"Added step: {step.name}")
        return self
    
    def add_steps(self, steps: List[BaseChainStep]) -> 'ChainManager':
        """
        여러 단계를 한번에 추가
        
        Args:
            steps: 추가할 체인 단계 리스트
            
        Returns:
            self (메서드 체이닝용)
        """
        for step in steps:
            self.add_step(step)
        return self
    
    async def execute(self, 
                     audio_data: Union[str, Path, Any],
                     initial_context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        체인 실행
        
        Args:
            audio_data: 오디오 데이터 또는 경로
            initial_context: 초기 컨텍스트
            
        Returns:
            최종 실행 결과 컨텍스트
        """
        start_time = datetime.now()
        context = initial_context or {}
        context['chain_start_time'] = start_time.isoformat()
        context['audio_data'] = audio_data
        
        # 실행 메타데이터 초기화
        execution_metadata = {
            'start_time': start_time.isoformat(),
            'steps_executed': [],
            'steps_skipped': [],
            'errors': [],
            'total_time': 0
        }
        
        logger.info(f"Starting chain execution with {len(self.steps)} steps")
        
        for step in self.steps:
            step_start = datetime.now()
            
            try:
                # 스킵 조건 확인
                if step.should_skip(context):
                    execution_metadata['steps_skipped'].append({
                        'name': step.name,
                        'reason': 'Conditional skip',
                        'timestamp': datetime.now().isoformat()
                    })
                    logger.info(f"Skipped step: {step.name}")
                    continue
                
                # 캐시 확인
                if self.cache_enabled and step.name in self.cache:
                    logger.info(f"Using cached result for: {step.name}")
                    context.update(self.cache[step.name])
                    execution_metadata['steps_executed'].append({
                        'name': step.name,
                        'cached': True,
                        'duration': 0,
                        'timestamp': datetime.now().isoformat()
                    })
                    continue
                
                # 단계 실행
                logger.info(f"Executing step: {step.name}")
                context = await step.process(audio_data, context)
                
                # 캐싱
                if self.cache_enabled:
                    self.cache[step.name] = self._extract_step_results(step.name, context)
                
                # 실행 메타데이터 기록
                step_duration = (datetime.now() - step_start).total_seconds()
                execution_metadata['steps_executed'].append({
                    'name': step.name,
                    'cached': False,
                    'duration': step_duration,
                    'timestamp': datetime.now().isoformat()
                })
                
                # 위기 상황 시 조기 종료 확인
                if self._should_early_exit(context):
                    logger.warning("Early exit triggered due to critical situation")
                    execution_metadata['early_exit'] = True
                    break
                    
            except Exception as e:
                logger.error(f"Error in step {step.name}: {str(e)}")
                
                # 에러 처리
                context = await step.handle_error(e, context)
                execution_metadata['errors'].append({
                    'step': step.name,
                    'error': str(e),
                    'timestamp': datetime.now().isoformat()
                })
                
                # Critical 단계에서 에러 발생 시 중단
                if step.is_critical:
                    logger.error(f"Critical step {step.name} failed, stopping chain")
                    execution_metadata['critical_failure'] = True
                    break
        
        # 최종 메타데이터 업데이트
        total_time = (datetime.now() - start_time).total_seconds()
        execution_metadata['total_time'] = total_time
        execution_metadata['end_time'] = datetime.now().isoformat()
        
        context['chain_metadata'] = execution_metadata
        
        # 실행 이력 저장
        self.execution_history.append({
            'timestamp': start_time.isoformat(),
            'metadata': execution_metadata,
            'success': len(execution_metadata['errors']) == 0
        })
        
        logger.info(f"Chain execution completed in {total_time:.2f}s")
        
        return context
    
    def _should_early_exit(self, context: Dict[str, Any]) -> bool:
        """
        조기 종료 조건 확인
        
        Args:
            context: 현재 컨텍스트
            
        Returns:
            True면 조기 종료
        """
        # 위기 상황이 critical이고 즉시 조치가 필요한 경우
        crisis = context.get('crisis', {})
        if crisis.get('severity') == 'critical' and crisis.get('immediate_action_required'):
            return True
        
        # 치명적 에러 발생
        if context.get('fatal_error'):
            return True
            
        return False
    
    def _extract_step_results(self, step_name: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        특정 단계의 결과만 추출하여 캐싱
        
        Args:
            step_name: 단계 이름
            context: 전체 컨텍스트
            
        Returns:
            해당 단계의 결과
        """
        # 단계별로 관련 키만 추출
        step_keys = {
            'crisis_detection': ['crisis', 'alert_triggered'],
            'basic_screening': ['mental_health_score', 'risk_level'],
            'detailed_analysis': ['detailed_scores', 'recommendations'],
            'result_integration': ['final_indicators', 'summary']
        }
        
        keys_to_cache = step_keys.get(step_name, [step_name])
        cached_data = {}
        
        for key in keys_to_cache:
            if key in context:
                cached_data[key] = context[key]
        
        return cached_data
    
    def clear_cache(self):
        """캐시 초기화"""
        self.cache.clear()
        logger.info("Cache cleared")
    
    def get_execution_stats(self) -> Dict[str, Any]:
        """
        실행 통계 반환
        
        Returns:
            실행 통계 정보
        """
        if not self.execution_history:
            return {
                'total_executions': 0,
                'success_rate': 0,
                'average_duration': 0
            }
        
        total = len(self.execution_history)
        successes = sum(1 for h in self.execution_history if h['success'])
        avg_duration = sum(h['metadata']['total_time'] for h in self.execution_history) / total
        
        return {
            'total_executions': total,
            'success_rate': successes / total,
            'average_duration': avg_duration,
            'last_execution': self.execution_history[-1] if self.execution_history else None
        }
    
    async def execute_with_fallback(self,
                                   audio_data: Union[str, Path, Any],
                                   initial_context: Optional[Dict[str, Any]] = None,
                                   fallback_handler: Optional[callable] = None) -> Dict[str, Any]:
        """
        Fallback 처리를 포함한 체인 실행
        
        Args:
            audio_data: 오디오 데이터
            initial_context: 초기 컨텍스트
            fallback_handler: 실패 시 호출할 fallback 함수
            
        Returns:
            실행 결과 또는 fallback 결과
        """
        try:
            return await self.execute(audio_data, initial_context)
        except Exception as e:
            logger.error(f"Chain execution failed: {e}")
            
            if fallback_handler:
                logger.info("Executing fallback handler")
                return await fallback_handler(audio_data, initial_context, e)
            else:
                # 기본 fallback 응답
                return {
                    'error': str(e),
                    'fallback': True,
                    'message': 'Chain execution failed, using default response',
                    'timestamp': datetime.now().isoformat()
                }
    
    def get_step_by_name(self, name: str) -> Optional[BaseChainStep]:
        """
        이름으로 단계 찾기
        
        Args:
            name: 단계 이름
            
        Returns:
            해당 단계 또는 None
        """
        for step in self.steps:
            if step.name == name:
                return step
        return None
    
    def remove_step(self, name: str) -> bool:
        """
        단계 제거
        
        Args:
            name: 제거할 단계 이름
            
        Returns:
            제거 성공 여부
        """
        for i, step in enumerate(self.steps):
            if step.name == name:
                self.steps.pop(i)
                logger.info(f"Removed step: {name}")
                return True
        return False
    
    def reorder_steps(self, order: List[str]):
        """
        단계 순서 재정렬
        
        Args:
            order: 새로운 순서 (단계 이름 리스트)
        """
        new_steps = []
        for name in order:
            step = self.get_step_by_name(name)
            if step:
                new_steps.append(step)
        
        self.steps = new_steps
        logger.info(f"Reordered steps: {order}")