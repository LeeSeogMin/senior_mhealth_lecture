"""
견고성 및 복원력 유틸리티
API 연결 실패, 네트워크 오류에 대한 체계적인 대응
"""

import asyncio
import logging
import time
from functools import wraps
from typing import Callable, Any, Optional, Dict, List
from dataclasses import dataclass
from enum import Enum

logger = logging.getLogger(__name__)

class RetryStrategy(Enum):
    EXPONENTIAL_BACKOFF = "exponential_backoff"
    FIXED_DELAY = "fixed_delay"
    IMMEDIATE = "immediate"

@dataclass
class RetryConfig:
    """재시도 설정"""
    max_attempts: int = 3
    base_delay: float = 1.0
    max_delay: float = 60.0
    backoff_factor: float = 2.0
    strategy: RetryStrategy = RetryStrategy.EXPONENTIAL_BACKOFF
    retryable_exceptions: List[type] = None

def with_retry(config: RetryConfig):
    """재시도 데코레이터"""
    def decorator(func: Callable):
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            last_exception = None

            for attempt in range(config.max_attempts):
                try:
                    return await func(*args, **kwargs)
                except Exception as e:
                    last_exception = e

                    # 재시도 가능한 예외인지 확인
                    if config.retryable_exceptions and not any(
                        isinstance(e, exc_type) for exc_type in config.retryable_exceptions
                    ):
                        logger.error(f"Non-retryable exception: {e}")
                        raise e

                    if attempt < config.max_attempts - 1:
                        delay = _calculate_delay(attempt, config)
                        logger.warning(f"Attempt {attempt + 1} failed: {e}. Retrying in {delay:.2f}s...")
                        await asyncio.sleep(delay)
                    else:
                        logger.error(f"All {config.max_attempts} attempts failed. Last error: {e}")

            raise last_exception

        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            last_exception = None

            for attempt in range(config.max_attempts):
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    last_exception = e

                    if config.retryable_exceptions and not any(
                        isinstance(e, exc_type) for exc_type in config.retryable_exceptions
                    ):
                        logger.error(f"Non-retryable exception: {e}")
                        raise e

                    if attempt < config.max_attempts - 1:
                        delay = _calculate_delay(attempt, config)
                        logger.warning(f"Attempt {attempt + 1} failed: {e}. Retrying in {delay:.2f}s...")
                        time.sleep(delay)
                    else:
                        logger.error(f"All {config.max_attempts} attempts failed. Last error: {e}")

            raise last_exception

        return async_wrapper if asyncio.iscoroutinefunction(func) else sync_wrapper
    return decorator

def _calculate_delay(attempt: int, config: RetryConfig) -> float:
    """재시도 딜레이 계산"""
    if config.strategy == RetryStrategy.FIXED_DELAY:
        return config.base_delay
    elif config.strategy == RetryStrategy.IMMEDIATE:
        return 0
    else:  # EXPONENTIAL_BACKOFF
        delay = config.base_delay * (config.backoff_factor ** attempt)
        return min(delay, config.max_delay)

class CircuitBreaker:
    """회로 차단기 패턴 구현"""

    def __init__(self,
                 failure_threshold: int = 5,
                 recovery_timeout: float = 60.0,
                 expected_exception: type = Exception):
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.expected_exception = expected_exception

        self.failure_count = 0
        self.last_failure_time = None
        self.state = "CLOSED"  # CLOSED, OPEN, HALF_OPEN

    def call(self, func: Callable, *args, **kwargs):
        """함수 호출 with 회로 차단기"""
        if self.state == "OPEN":
            if self._should_attempt_reset():
                self.state = "HALF_OPEN"
            else:
                raise Exception(f"Circuit breaker is OPEN. Last failure: {self.last_failure_time}")

        try:
            result = func(*args, **kwargs)
            self._on_success()
            return result
        except self.expected_exception as e:
            self._on_failure()
            raise e

    def _should_attempt_reset(self) -> bool:
        """리셋 시도 여부 판단"""
        return (time.time() - self.last_failure_time) >= self.recovery_timeout

    def _on_success(self):
        """성공 처리"""
        self.failure_count = 0
        self.state = "CLOSED"

    def _on_failure(self):
        """실패 처리"""
        self.failure_count += 1
        self.last_failure_time = time.time()

        if self.failure_count >= self.failure_threshold:
            self.state = "OPEN"

class HealthChecker:
    """서비스 헬스체크 유틸리티"""

    def __init__(self):
        self.services = {}

    def register_service(self, name: str, check_func: Callable, timeout: float = 5.0):
        """서비스 등록"""
        self.services[name] = {
            'check_func': check_func,
            'timeout': timeout,
            'last_check': None,
            'status': 'UNKNOWN'
        }

    async def check_service(self, name: str) -> Dict[str, Any]:
        """개별 서비스 헬스체크"""
        if name not in self.services:
            return {'status': 'NOT_REGISTERED', 'error': f'Service {name} not registered'}

        service = self.services[name]
        start_time = time.time()

        try:
            await asyncio.wait_for(
                service['check_func'](),
                timeout=service['timeout']
            )

            status = {
                'status': 'HEALTHY',
                'response_time': time.time() - start_time,
                'last_check': time.time()
            }

            service['status'] = 'HEALTHY'
            service['last_check'] = time.time()

            return status

        except asyncio.TimeoutError:
            status = {
                'status': 'TIMEOUT',
                'error': f'Health check timed out after {service["timeout"]}s',
                'last_check': time.time()
            }
            service['status'] = 'TIMEOUT'
            return status

        except Exception as e:
            status = {
                'status': 'UNHEALTHY',
                'error': str(e),
                'last_check': time.time()
            }
            service['status'] = 'UNHEALTHY'
            return status

    async def check_all_services(self) -> Dict[str, Dict[str, Any]]:
        """모든 서비스 헬스체크"""
        results = {}

        for service_name in self.services:
            results[service_name] = await self.check_service(service_name)

        return results