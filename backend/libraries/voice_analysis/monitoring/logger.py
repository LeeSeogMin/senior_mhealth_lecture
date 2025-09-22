# 제7강: AI 모델 이해와 로컬 테스트 - 로깅 시스템
"""
고급 로깅 시스템
구조화된 로그, 로그 레벨 관리, 로그 파일 로테이션 제공
"""

import os
import sys
import json
import logging
import logging.handlers
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional, Union
from dataclasses import dataclass
import traceback


@dataclass
class LogConfig:
    """로깅 설정"""
    log_level: str = "INFO"
    log_dir: str = "logs"
    log_file: str = "mhealth_ai.log"
    max_file_size: int = 10 * 1024 * 1024  # 10MB
    backup_count: int = 5
    console_output: bool = True
    json_format: bool = True
    enable_structured_logging: bool = True


class StructuredFormatter(logging.Formatter):
    """구조화된 JSON 로그 포매터"""
    
    def format(self, record: logging.LogRecord) -> str:
        """로그 레코드를 JSON 형태로 포맷팅"""
        log_data = {
            'timestamp': datetime.fromtimestamp(record.created).isoformat(),
            'level': record.levelname,
            'logger': record.name,
            'message': record.getMessage(),
            'module': record.module,
            'function': record.funcName,
            'line': record.lineno,
            'thread': record.thread,
            'thread_name': record.threadName,
            'process': record.process
        }
        
        # 추가 컨텍스트 정보
        if hasattr(record, 'extra_data'):
            log_data.update(record.extra_data)
        
        # 예외 정보 추가
        if record.exc_info:
            log_data['exception'] = {
                'type': record.exc_info[0].__name__,
                'message': str(record.exc_info[1]),
                'traceback': traceback.format_exception(*record.exc_info)
            }
        
        # 스택 정보 추가
        if record.stack_info:
            log_data['stack_info'] = record.stack_info
        
        return json.dumps(log_data, ensure_ascii=False)


class ColoredFormatter(logging.Formatter):
    """컬러 콘솔 출력을 위한 포매터"""
    
    COLORS = {
        'DEBUG': '\033[36m',    # 청록색
        'INFO': '\033[32m',     # 녹색
        'WARNING': '\033[33m',  # 노란색
        'ERROR': '\033[31m',    # 빨간색
        'CRITICAL': '\033[35m', # 마젠타
        'RESET': '\033[0m'      # 리셋
    }
    
    def format(self, record: logging.LogRecord) -> str:
        """컬러 포맷팅된 로그 출력"""
        color = self.COLORS.get(record.levelname, self.COLORS['RESET'])
        reset = self.COLORS['RESET']
        
        # 기본 포맷
        formatted_time = datetime.fromtimestamp(record.created).strftime('%Y-%m-%d %H:%M:%S')
        
        formatted_log = (
            f"{color}[{formatted_time}] "
            f"{record.levelname:8} "
            f"{record.name}:{record.lineno} - "
            f"{record.getMessage()}{reset}"
        )
        
        # 예외 정보 추가
        if record.exc_info:
            formatted_log += f"\n{color}{traceback.format_exception(*record.exc_info)[-1].strip()}{reset}"
        
        return formatted_log


class ContextLogger:
    """컨텍스트 정보를 포함한 로거 래퍼"""
    
    def __init__(self, logger: logging.Logger, context: Dict[str, Any] = None):
        self.logger = logger
        self.context = context or {}
    
    def _log_with_context(self, level: int, msg: str, *args, **kwargs):
        """컨텍스트 정보와 함께 로그 출력"""
        extra = kwargs.get('extra', {})
        extra['extra_data'] = {**self.context, **extra.get('extra_data', {})}
        kwargs['extra'] = extra
        self.logger.log(level, msg, *args, **kwargs)
    
    def debug(self, msg: str, *args, **kwargs):
        self._log_with_context(logging.DEBUG, msg, *args, **kwargs)
    
    def info(self, msg: str, *args, **kwargs):
        self._log_with_context(logging.INFO, msg, *args, **kwargs)
    
    def warning(self, msg: str, *args, **kwargs):
        self._log_with_context(logging.WARNING, msg, *args, **kwargs)
    
    def error(self, msg: str, *args, **kwargs):
        self._log_with_context(logging.ERROR, msg, *args, **kwargs)
    
    def critical(self, msg: str, *args, **kwargs):
        self._log_with_context(logging.CRITICAL, msg, *args, **kwargs)
    
    def exception(self, msg: str, *args, **kwargs):
        kwargs['exc_info'] = True
        self._log_with_context(logging.ERROR, msg, *args, **kwargs)
    
    def add_context(self, **kwargs):
        """컨텍스트 정보 추가"""
        self.context.update(kwargs)
    
    def remove_context(self, *keys):
        """컨텍스트 정보 제거"""
        for key in keys:
            self.context.pop(key, None)
    
    def clear_context(self):
        """모든 컨텍스트 정보 제거"""
        self.context.clear()


class LoggerManager:
    """로거 관리자"""
    
    def __init__(self, config: LogConfig = None):
        self.config = config or LogConfig()
        self._loggers = {}
        self._setup_logging()
    
    def _setup_logging(self):
        """로깅 시스템 초기화"""
        # 로그 디렉토리 생성
        log_dir = Path(self.config.log_dir)
        log_dir.mkdir(parents=True, exist_ok=True)
        
        # 루트 로거 설정
        root_logger = logging.getLogger()
        root_logger.setLevel(getattr(logging, self.config.log_level.upper()))
        
        # 기존 핸들러 제거
        for handler in root_logger.handlers[:]:
            root_logger.removeHandler(handler)
        
        # 파일 핸들러 설정
        file_handler = logging.handlers.RotatingFileHandler(
            filename=log_dir / self.config.log_file,
            maxBytes=self.config.max_file_size,
            backupCount=self.config.backup_count,
            encoding='utf-8'
        )
        
        if self.config.json_format:
            file_handler.setFormatter(StructuredFormatter())
        else:
            file_handler.setFormatter(
                logging.Formatter(
                    '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                    datefmt='%Y-%m-%d %H:%M:%S'
                )
            )
        
        root_logger.addHandler(file_handler)
        
        # 콘솔 핸들러 설정
        if self.config.console_output:
            console_handler = logging.StreamHandler(sys.stdout)
            console_handler.setFormatter(ColoredFormatter())
            root_logger.addHandler(console_handler)
        
        # 외부 라이브러리 로그 레벨 조정
        self._configure_third_party_loggers()
    
    def _configure_third_party_loggers(self):
        """외부 라이브러리 로거 설정"""
        # 일반적으로 시끄러운 로거들 조정
        logging.getLogger('urllib3').setLevel(logging.WARNING)
        logging.getLogger('requests').setLevel(logging.WARNING)
        logging.getLogger('torch').setLevel(logging.WARNING)
        logging.getLogger('matplotlib').setLevel(logging.WARNING)
        logging.getLogger('PIL').setLevel(logging.WARNING)
    
    def get_logger(self, name: str, context: Dict[str, Any] = None) -> ContextLogger:
        """컨텍스트 로거 생성/반환"""
        if name not in self._loggers:
            base_logger = logging.getLogger(name)
            self._loggers[name] = ContextLogger(base_logger, context)
        
        return self._loggers[name]
    
    def set_level(self, level: str):
        """로그 레벨 변경"""
        root_logger = logging.getLogger()
        root_logger.setLevel(getattr(logging, level.upper()))
        self.config.log_level = level
    
    def add_custom_handler(self, handler: logging.Handler):
        """사용자 정의 핸들러 추가"""
        root_logger = logging.getLogger()
        root_logger.addHandler(handler)
    
    def get_log_stats(self) -> Dict[str, Any]:
        """로그 통계 정보 반환"""
        log_file_path = Path(self.config.log_dir) / self.config.log_file
        
        stats = {
            'log_file': str(log_file_path),
            'file_exists': log_file_path.exists(),
            'file_size': 0,
            'last_modified': None,
            'active_loggers': list(self._loggers.keys()),
            'log_level': self.config.log_level
        }
        
        if log_file_path.exists():
            stat = log_file_path.stat()
            stats['file_size'] = stat.st_size
            stats['last_modified'] = datetime.fromtimestamp(stat.st_mtime).isoformat()
        
        return stats


# 전역 로거 관리자
_logger_manager = None


def setup_logging(config: LogConfig = None) -> LoggerManager:
    """로깅 시스템 설정"""
    global _logger_manager
    _logger_manager = LoggerManager(config)
    return _logger_manager


def get_logger(name: str, context: Dict[str, Any] = None) -> ContextLogger:
    """로거 인스턴스 반환"""
    global _logger_manager
    
    if _logger_manager is None:
        _logger_manager = LoggerManager()
    
    return _logger_manager.get_logger(name, context)


class PerformanceLogger:
    """성능 측정 및 로깅"""
    
    def __init__(self, logger: ContextLogger, operation_name: str):
        self.logger = logger
        self.operation_name = operation_name
        self.start_time = None
        self.context = {}
    
    def __enter__(self):
        self.start_time = datetime.now()
        self.logger.info(f"{self.operation_name} 시작", extra={'extra_data': {
            'operation': self.operation_name,
            'start_time': self.start_time.isoformat(),
            'event_type': 'operation_start'
        }})
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        end_time = datetime.now()
        duration = (end_time - self.start_time).total_seconds()
        
        log_data = {
            'operation': self.operation_name,
            'duration_seconds': duration,
            'start_time': self.start_time.isoformat(),
            'end_time': end_time.isoformat(),
            'event_type': 'operation_end',
            **self.context
        }
        
        if exc_type is not None:
            log_data['event_type'] = 'operation_error'
            log_data['error_type'] = exc_type.__name__
            log_data['error_message'] = str(exc_val)
            self.logger.error(f"{self.operation_name} 실패: {exc_val}", extra={'extra_data': log_data})
        else:
            self.logger.info(f"{self.operation_name} 완료 ({duration:.3f}초)", extra={'extra_data': log_data})
    
    def add_context(self, **kwargs):
        """컨텍스트 정보 추가"""
        self.context.update(kwargs)
    
    def checkpoint(self, checkpoint_name: str, **kwargs):
        """중간 체크포인트 로깅"""
        current_time = datetime.now()
        elapsed = (current_time - self.start_time).total_seconds()
        
        log_data = {
            'operation': self.operation_name,
            'checkpoint': checkpoint_name,
            'elapsed_seconds': elapsed,
            'timestamp': current_time.isoformat(),
            'event_type': 'operation_checkpoint',
            **kwargs
        }
        
        self.logger.debug(f"{self.operation_name} - {checkpoint_name} ({elapsed:.3f}초)", 
                         extra={'extra_data': log_data})


# 데코레이터 함수들
def log_performance(operation_name: str = None):
    """성능 측정 데코레이터"""
    def decorator(func):
        def wrapper(*args, **kwargs):
            name = operation_name or f"{func.__module__}.{func.__name__}"
            logger = get_logger(func.__module__)
            
            with PerformanceLogger(logger, name) as perf_logger:
                perf_logger.add_context(
                    function=func.__name__,
                    args_count=len(args),
                    kwargs_count=len(kwargs)
                )
                result = func(*args, **kwargs)
                perf_logger.add_context(result_type=type(result).__name__)
                return result
        
        return wrapper
    return decorator


def log_exceptions(logger_name: str = None):
    """예외 로깅 데코레이터"""
    def decorator(func):
        def wrapper(*args, **kwargs):
            name = logger_name or func.__module__
            logger = get_logger(name)
            
            try:
                return func(*args, **kwargs)
            except Exception as e:
                logger.exception(f"{func.__name__}에서 예외 발생", extra={'extra_data': {
                    'function': func.__name__,
                    'args_count': len(args),
                    'kwargs_count': len(kwargs),
                    'exception_type': type(e).__name__,
                    'exception_message': str(e)
                }})
                raise
        
        return wrapper
    return decorator