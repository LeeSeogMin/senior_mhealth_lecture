"""
시스템 모니터링 및 알림
성능 지표, 오류 추적, 자동화된 알림 시스템
"""

import asyncio
import logging
import time
from typing import Dict, Any, List, Callable, Optional
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from collections import defaultdict, deque
import json

logger = logging.getLogger(__name__)

@dataclass
class MetricPoint:
    """메트릭 데이터 포인트"""
    timestamp: float
    value: float
    tags: Dict[str, str] = field(default_factory=dict)

@dataclass
class Alert:
    """알림 정보"""
    alert_id: str
    severity: str  # INFO, WARNING, ERROR, CRITICAL
    message: str
    timestamp: float
    source: str
    metadata: Dict[str, Any] = field(default_factory=dict)

class MetricsCollector:
    """메트릭 수집기"""

    def __init__(self, max_points: int = 10000):
        self.metrics = defaultdict(lambda: deque(maxlen=max_points))
        self.counters = defaultdict(int)
        self.timers = {}

    def record_metric(self, name: str, value: float, tags: Dict[str, str] = None):
        """메트릭 기록"""
        point = MetricPoint(
            timestamp=time.time(),
            value=value,
            tags=tags or {}
        )
        self.metrics[name].append(point)

    def increment_counter(self, name: str, value: int = 1):
        """카운터 증가"""
        self.counters[name] += value

    def start_timer(self, name: str) -> str:
        """타이머 시작"""
        timer_id = f"{name}_{time.time()}"
        self.timers[timer_id] = time.time()
        return timer_id

    def end_timer(self, timer_id: str) -> float:
        """타이머 종료 및 기록"""
        if timer_id not in self.timers:
            logger.warning(f"Timer {timer_id} not found")
            return 0.0

        start_time = self.timers.pop(timer_id)
        duration = time.time() - start_time

        # Extract metric name from timer_id
        metric_name = timer_id.rsplit('_', 1)[0]
        self.record_metric(f"{metric_name}_duration", duration)

        return duration

    def get_metric_stats(self, name: str, window_seconds: int = 300) -> Dict[str, float]:
        """메트릭 통계 조회"""
        if name not in self.metrics:
            return {}

        cutoff_time = time.time() - window_seconds
        recent_points = [
            point for point in self.metrics[name]
            if point.timestamp > cutoff_time
        ]

        if not recent_points:
            return {}

        values = [point.value for point in recent_points]
        return {
            'count': len(values),
            'sum': sum(values),
            'avg': sum(values) / len(values),
            'min': min(values),
            'max': max(values)
        }

class AlertManager:
    """알림 관리자"""

    def __init__(self):
        self.alerts = deque(maxlen=1000)
        self.alert_handlers = []
        self.suppression_rules = {}

    def add_handler(self, handler: Callable[[Alert], None]):
        """알림 핸들러 추가"""
        self.alert_handlers.append(handler)

    def fire_alert(self, severity: str, message: str, source: str, **metadata):
        """알림 발생"""
        alert = Alert(
            alert_id=f"{source}_{time.time()}",
            severity=severity,
            message=message,
            timestamp=time.time(),
            source=source,
            metadata=metadata
        )

        # 중복 알림 억제 체크
        if self._should_suppress_alert(alert):
            return

        self.alerts.append(alert)

        # 핸들러 실행
        for handler in self.alert_handlers:
            try:
                handler(alert)
            except Exception as e:
                logger.error(f"Alert handler failed: {e}")

    def _should_suppress_alert(self, alert: Alert) -> bool:
        """알림 억제 여부 판단"""
        key = f"{alert.source}_{alert.severity}_{alert.message}"

        if key in self.suppression_rules:
            last_time, count = self.suppression_rules[key]
            # 5분 이내 동일한 알림이 5회 이상 발생하면 억제
            if time.time() - last_time < 300 and count >= 5:
                return True

        self.suppression_rules[key] = (time.time(),
                                       self.suppression_rules.get(key, (0, 0))[1] + 1)
        return False

    def get_recent_alerts(self, minutes: int = 60) -> List[Alert]:
        """최근 알림 조회"""
        cutoff_time = time.time() - (minutes * 60)
        return [alert for alert in self.alerts if alert.timestamp > cutoff_time]

class SystemMonitor:
    """시스템 종합 모니터"""

    def __init__(self):
        self.metrics = MetricsCollector()
        self.alerts = AlertManager()
        self.health_checks = {}
        self._monitoring_tasks = []

    def start_monitoring(self):
        """모니터링 시작"""
        # API 응답 시간 모니터링
        asyncio.create_task(self._monitor_api_response_times())

        # 오류율 모니터링
        asyncio.create_task(self._monitor_error_rates())

        # 시스템 리소스 모니터링
        asyncio.create_task(self._monitor_system_resources())

    async def _monitor_api_response_times(self):
        """API 응답 시간 모니터링"""
        while True:
            try:
                # OpenAI API 응답 시간 체크
                stats = self.metrics.get_metric_stats('openai_api_duration', window_seconds=300)

                if stats and stats['avg'] > 10.0:  # 10초 이상이면 경고
                    self.alerts.fire_alert(
                        'WARNING',
                        f"OpenAI API 응답 시간 지연: {stats['avg']:.2f}초",
                        'api_monitor',
                        stats=stats
                    )

                await asyncio.sleep(60)  # 1분마다 체크

            except Exception as e:
                logger.error(f"API response time monitoring error: {e}")
                await asyncio.sleep(60)

    async def _monitor_error_rates(self):
        """오류율 모니터링"""
        while True:
            try:
                # 오류 카운트 체크
                error_count = self.metrics.counters.get('api_errors', 0)
                success_count = self.metrics.counters.get('api_success', 0)

                total = error_count + success_count
                if total > 0:
                    error_rate = error_count / total

                    if error_rate > 0.1:  # 10% 이상 오류율
                        self.alerts.fire_alert(
                            'ERROR',
                            f"API 오류율 증가: {error_rate:.1%}",
                            'error_monitor',
                            error_count=error_count,
                            total_count=total
                        )

                await asyncio.sleep(300)  # 5분마다 체크

            except Exception as e:
                logger.error(f"Error rate monitoring error: {e}")
                await asyncio.sleep(300)

    async def _monitor_system_resources(self):
        """시스템 리소스 모니터링"""
        while True:
            try:
                import psutil

                # CPU 사용률
                cpu_percent = psutil.cpu_percent(interval=1)
                self.metrics.record_metric('cpu_usage', cpu_percent)

                if cpu_percent > 90:
                    self.alerts.fire_alert(
                        'WARNING',
                        f"CPU 사용률 높음: {cpu_percent:.1f}%",
                        'system_monitor'
                    )

                # 메모리 사용률
                memory = psutil.virtual_memory()
                memory_percent = memory.percent
                self.metrics.record_metric('memory_usage', memory_percent)

                if memory_percent > 90:
                    self.alerts.fire_alert(
                        'WARNING',
                        f"메모리 사용률 높음: {memory_percent:.1f}%",
                        'system_monitor'
                    )

                await asyncio.sleep(60)  # 1분마다 체크

            except ImportError:
                # psutil이 없으면 시스템 모니터링 비활성화
                logger.warning("psutil not available, system monitoring disabled")
                break
            except Exception as e:
                logger.error(f"System monitoring error: {e}")
                await asyncio.sleep(60)

# 로그 핸들러
def log_alert_handler(alert: Alert):
    """로그로 알림 출력"""
    log_level = {
        'INFO': logging.INFO,
        'WARNING': logging.WARNING,
        'ERROR': logging.ERROR,
        'CRITICAL': logging.CRITICAL
    }.get(alert.severity, logging.INFO)

    logger.log(log_level, f"[ALERT] {alert.source}: {alert.message}")

# 글로벌 모니터 인스턴스
global_monitor = SystemMonitor()
global_monitor.alerts.add_handler(log_alert_handler)

# API 호출 추적 데코레이터
def track_api_call(api_name: str):
    """API 호출 추적 데코레이터"""
    def decorator(func: Callable):
        async def async_wrapper(*args, **kwargs):
            timer_id = global_monitor.metrics.start_timer(f"{api_name}_api")

            try:
                result = await func(*args, **kwargs)
                global_monitor.metrics.increment_counter('api_success')
                return result
            except Exception as e:
                global_monitor.metrics.increment_counter('api_errors')
                global_monitor.alerts.fire_alert(
                    'ERROR',
                    f"{api_name} API 호출 실패: {str(e)}",
                    'api_tracker',
                    error_type=type(e).__name__
                )
                raise
            finally:
                global_monitor.metrics.end_timer(timer_id)

        def sync_wrapper(*args, **kwargs):
            timer_id = global_monitor.metrics.start_timer(f"{api_name}_api")

            try:
                result = func(*args, **kwargs)
                global_monitor.metrics.increment_counter('api_success')
                return result
            except Exception as e:
                global_monitor.metrics.increment_counter('api_errors')
                global_monitor.alerts.fire_alert(
                    'ERROR',
                    f"{api_name} API 호출 실패: {str(e)}",
                    'api_tracker',
                    error_type=type(e).__name__
                )
                raise
            finally:
                global_monitor.metrics.end_timer(timer_id)

        return async_wrapper if asyncio.iscoroutinefunction(func) else sync_wrapper
    return decorator