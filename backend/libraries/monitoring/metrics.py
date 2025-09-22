"""
Senior MHealth - 메트릭 수집 시스템
Prometheus metrics collection and monitoring
"""

from prometheus_client import (
    Counter, Histogram, Gauge, Summary,
    CollectorRegistry, generate_latest,
    CONTENT_TYPE_LATEST
)
from fastapi import FastAPI, Request, Response
from fastapi.responses import PlainTextResponse
import time
from typing import Callable
import functools


# 메트릭 레지스트리
registry = CollectorRegistry()

# === HTTP 메트릭 ===
http_requests_total = Counter(
    'http_requests_total',
    'Total HTTP requests',
    ['method', 'endpoint', 'status'],
    registry=registry
)

http_request_duration_seconds = Histogram(
    'http_request_duration_seconds',
    'HTTP request duration in seconds',
    ['method', 'endpoint'],
    registry=registry
)

http_request_size_bytes = Summary(
    'http_request_size_bytes',
    'HTTP request size in bytes',
    ['method', 'endpoint'],
    registry=registry
)

# === 음성 분석 메트릭 ===
voice_analysis_total = Counter(
    'voice_analysis_total',
    'Total voice analysis requests',
    ['status', 'analysis_type'],
    registry=registry
)

voice_analysis_duration_seconds = Histogram(
    'voice_analysis_duration_seconds',
    'Voice analysis duration in seconds',
    ['analysis_type'],
    buckets=[1, 5, 10, 30, 60, 120, 300],
    registry=registry
)

audio_file_size_bytes = Histogram(
    'audio_file_size_bytes',
    'Audio file size in bytes',
    buckets=[1e6, 5e6, 10e6, 50e6, 100e6],  # 1MB, 5MB, 10MB, 50MB, 100MB
    registry=registry
)

# === 시스템 메트릭 ===
active_connections = Gauge(
    'active_connections',
    'Number of active connections',
    registry=registry
)

memory_usage_bytes = Gauge(
    'memory_usage_bytes',
    'Memory usage in bytes',
    registry=registry
)

cpu_usage_percent = Gauge(
    'cpu_usage_percent',
    'CPU usage percentage',
    registry=registry
)

# === ML 모델 메트릭 ===
model_prediction_total = Counter(
    'model_prediction_total',
    'Total model predictions',
    ['model_name', 'status'],
    registry=registry
)

model_prediction_duration_seconds = Histogram(
    'model_prediction_duration_seconds',
    'Model prediction duration in seconds',
    ['model_name'],
    registry=registry
)

model_accuracy = Gauge(
    'model_accuracy',
    'Model accuracy score',
    ['model_name'],
    registry=registry
)

# === 데이터베이스 메트릭 ===
db_operations_total = Counter(
    'db_operations_total',
    'Total database operations',
    ['operation', 'collection', 'status'],
    registry=registry
)

db_operation_duration_seconds = Histogram(
    'db_operation_duration_seconds',
    'Database operation duration in seconds',
    ['operation', 'collection'],
    registry=registry
)


class MetricsMiddleware:
    """FastAPI 메트릭 미들웨어"""
    
    def __init__(self, app: FastAPI):
        self.app = app
    
    async def __call__(self, request: Request, call_next: Callable):
        # 요청 시작 시간
        start_time = time.time()
        
        # 활성 연결 증가
        active_connections.inc()
        
        try:
            # 요청 처리
            response = await call_next(request)
            
            # 메트릭 기록
            duration = time.time() - start_time
            endpoint = request.url.path
            method = request.method
            status = response.status_code
            
            # HTTP 메트릭 업데이트
            http_requests_total.labels(
                method=method,
                endpoint=endpoint,
                status=status
            ).inc()
            
            http_request_duration_seconds.labels(
                method=method,
                endpoint=endpoint
            ).observe(duration)
            
            if hasattr(request, 'content_length') and request.content_length:
                http_request_size_bytes.labels(
                    method=method,
                    endpoint=endpoint
                ).observe(request.content_length)
            
            return response
            
        finally:
            # 활성 연결 감소
            active_connections.dec()


def track_voice_analysis(analysis_type: str):
    """음성 분석 추적 데코레이터"""
    def decorator(func):
        @functools.wraps(func)
        async def async_wrapper(*args, **kwargs):
            start_time = time.time()
            
            try:
                result = await func(*args, **kwargs)
                
                # 성공 메트릭
                voice_analysis_total.labels(
                    status='success',
                    analysis_type=analysis_type
                ).inc()
                
                duration = time.time() - start_time
                voice_analysis_duration_seconds.labels(
                    analysis_type=analysis_type
                ).observe(duration)
                
                return result
                
            except Exception as e:
                # 실패 메트릭
                voice_analysis_total.labels(
                    status='failure',
                    analysis_type=analysis_type
                ).inc()
                raise
        
        @functools.wraps(func)
        def sync_wrapper(*args, **kwargs):
            start_time = time.time()
            
            try:
                result = func(*args, **kwargs)
                
                # 성공 메트릭
                voice_analysis_total.labels(
                    status='success',
                    analysis_type=analysis_type
                ).inc()
                
                duration = time.time() - start_time
                voice_analysis_duration_seconds.labels(
                    analysis_type=analysis_type
                ).observe(duration)
                
                return result
                
            except Exception as e:
                # 실패 메트릭
                voice_analysis_total.labels(
                    status='failure',
                    analysis_type=analysis_type
                ).inc()
                raise
        
        import asyncio
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        return sync_wrapper
    
    return decorator


def track_db_operation(operation: str, collection: str):
    """데이터베이스 작업 추적 데코레이터"""
    def decorator(func):
        @functools.wraps(func)
        async def async_wrapper(*args, **kwargs):
            start_time = time.time()
            
            try:
                result = await func(*args, **kwargs)
                
                # 성공 메트릭
                db_operations_total.labels(
                    operation=operation,
                    collection=collection,
                    status='success'
                ).inc()
                
                duration = time.time() - start_time
                db_operation_duration_seconds.labels(
                    operation=operation,
                    collection=collection
                ).observe(duration)
                
                return result
                
            except Exception as e:
                # 실패 메트릭
                db_operations_total.labels(
                    operation=operation,
                    collection=collection,
                    status='failure'
                ).inc()
                raise
        
        @functools.wraps(func)
        def sync_wrapper(*args, **kwargs):
            start_time = time.time()
            
            try:
                result = func(*args, **kwargs)
                
                # 성공 메트릭
                db_operations_total.labels(
                    operation=operation,
                    collection=collection,
                    status='success'
                ).inc()
                
                duration = time.time() - start_time
                db_operation_duration_seconds.labels(
                    operation=operation,
                    collection=collection
                ).observe(duration)
                
                return result
                
            except Exception as e:
                # 실패 메트릭
                db_operations_total.labels(
                    operation=operation,
                    collection=collection,
                    status='failure'
                ).inc()
                raise
        
        import asyncio
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        return sync_wrapper
    
    return decorator


def update_system_metrics():
    """시스템 메트릭 업데이트"""
    import psutil
    
    # 메모리 사용량
    memory = psutil.virtual_memory()
    memory_usage_bytes.set(memory.used)
    
    # CPU 사용률
    cpu_percent = psutil.cpu_percent(interval=1)
    cpu_usage_percent.set(cpu_percent)


async def metrics_endpoint(request: Request) -> Response:
    """Prometheus 메트릭 엔드포인트"""
    # 시스템 메트릭 업데이트
    update_system_metrics()
    
    # 메트릭 생성
    metrics = generate_latest(registry)
    
    return PlainTextResponse(
        content=metrics.decode('utf-8'),
        media_type=CONTENT_TYPE_LATEST
    )