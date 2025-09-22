"""
Senior MHealth - 통합 로깅 시스템
Structured logging with correlation IDs and context
"""

import logging
import sys
import json
from datetime import datetime
from typing import Any, Dict, Optional
import structlog
from pythonjsonlogger import jsonlogger
from contextvars import ContextVar

# Context variables for request tracking
request_id_var: ContextVar[Optional[str]] = ContextVar('request_id', default=None)
user_id_var: ContextVar[Optional[str]] = ContextVar('user_id', default=None)


class CustomJSONFormatter(jsonlogger.JsonFormatter):
    """커스텀 JSON 포매터"""
    
    def add_fields(self, log_record, record, message_dict):
        super().add_fields(log_record, record, message_dict)
        
        # 타임스탬프 추가
        log_record['timestamp'] = datetime.utcnow().isoformat()
        
        # 로그 레벨 추가
        log_record['level'] = record.levelname
        
        # 컨텍스트 변수 추가
        if request_id := request_id_var.get():
            log_record['request_id'] = request_id
        if user_id := user_id_var.get():
            log_record['user_id'] = user_id
        
        # 소스 정보 추가
        log_record['source'] = {
            'file': record.pathname,
            'line': record.lineno,
            'function': record.funcName
        }


def setup_logging(
    service_name: str,
    log_level: str = "INFO",
    log_format: str = "json"
) -> logging.Logger:
    """
    통합 로깅 설정
    
    Args:
        service_name: 서비스 이름
        log_level: 로그 레벨
        log_format: 로그 포맷 (json/console)
    
    Returns:
        설정된 로거
    """
    
    # 기본 로거 설정
    logger = logging.getLogger(service_name)
    logger.setLevel(getattr(logging, log_level.upper()))
    
    # 기존 핸들러 제거
    logger.handlers.clear()
    
    # 핸들러 생성
    handler = logging.StreamHandler(sys.stdout)
    
    # 포맷 설정
    if log_format == "json":
        formatter = CustomJSONFormatter()
    else:
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
    
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    
    return logger


def setup_structured_logging(service_name: str) -> structlog.BoundLogger:
    """
    Structlog 설정 (고급 구조화 로깅)
    
    Args:
        service_name: 서비스 이름
    
    Returns:
        Structlog 로거
    """
    
    structlog.configure(
        processors=[
            structlog.stdlib.filter_by_level,
            structlog.stdlib.add_logger_name,
            structlog.stdlib.add_log_level,
            structlog.stdlib.PositionalArgumentsFormatter(),
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            structlog.processors.UnicodeDecoder(),
            structlog.processors.JSONRenderer()
        ],
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )
    
    return structlog.get_logger(service_name)


class LoggerContext:
    """로깅 컨텍스트 관리"""
    
    def __init__(self, **kwargs):
        self.context = kwargs
        self.tokens = []
    
    def __enter__(self):
        for key, value in self.context.items():
            if key == 'request_id':
                token = request_id_var.set(value)
            elif key == 'user_id':
                token = user_id_var.set(value)
            else:
                continue
            self.tokens.append((key, token))
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        for key, token in self.tokens:
            if key == 'request_id':
                request_id_var.reset(token)
            elif key == 'user_id':
                user_id_var.reset(token)


def log_performance(func):
    """성능 로깅 데코레이터"""
    import time
    import functools
    
    @functools.wraps(func)
    async def async_wrapper(*args, **kwargs):
        start_time = time.time()
        logger = structlog.get_logger()
        
        try:
            result = await func(*args, **kwargs)
            elapsed = time.time() - start_time
            logger.info(
                "function_completed",
                function=func.__name__,
                elapsed_time=elapsed,
                status="success"
            )
            return result
        except Exception as e:
            elapsed = time.time() - start_time
            logger.error(
                "function_failed",
                function=func.__name__,
                elapsed_time=elapsed,
                status="error",
                error=str(e)
            )
            raise
    
    @functools.wraps(func)
    def sync_wrapper(*args, **kwargs):
        start_time = time.time()
        logger = structlog.get_logger()
        
        try:
            result = func(*args, **kwargs)
            elapsed = time.time() - start_time
            logger.info(
                "function_completed",
                function=func.__name__,
                elapsed_time=elapsed,
                status="success"
            )
            return result
        except Exception as e:
            elapsed = time.time() - start_time
            logger.error(
                "function_failed", 
                function=func.__name__,
                elapsed_time=elapsed,
                status="error",
                error=str(e)
            )
            raise
    
    if asyncio.iscoroutinefunction(func):
        return async_wrapper
    return sync_wrapper


# 전역 로거 인스턴스
import asyncio
logger = setup_structured_logging("senior_mhealth")