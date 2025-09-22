# 제7강: AI 모델 이해와 로컬 테스트 - 메트릭 수집기
"""
성능 메트릭 수집 및 모니터링
시스템 리소스, 모델 성능, 처리 속도 등 메트릭 수집
"""

import os
import psutil
import time
import threading
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List, Tuple
from dataclasses import dataclass, asdict
from collections import defaultdict, deque
import json
import torch
import numpy as np

from .logger import get_logger, PerformanceLogger


logger = get_logger(__name__)


@dataclass
class SystemMetrics:
    """시스템 메트릭"""
    timestamp: str
    cpu_percent: float
    memory_percent: float
    memory_available_gb: float
    memory_used_gb: float
    disk_usage_percent: float
    disk_free_gb: float
    gpu_count: int
    gpu_memory_used_gb: float
    gpu_memory_total_gb: float
    gpu_utilization_percent: float


@dataclass
class ModelMetrics:
    """모델 성능 메트릭"""
    timestamp: str
    model_name: str
    prediction_count: int
    avg_inference_time_ms: float
    min_inference_time_ms: float
    max_inference_time_ms: float
    error_count: int
    success_rate: float
    cache_hit_rate: float
    throughput_per_minute: float


@dataclass
class AudioMetrics:
    """오디오 처리 메트릭"""
    timestamp: str
    total_audio_processed: int
    avg_audio_duration_sec: float
    total_processing_time_sec: float
    feature_extraction_time_ms: float
    preprocessing_time_ms: float
    postprocessing_time_ms: float


class MetricsBuffer:
    """메트릭 버퍼 관리"""
    
    def __init__(self, max_size: int = 1000):
        self.max_size = max_size
        self.buffer = deque(maxlen=max_size)
        self.lock = threading.RLock()
    
    def add(self, metric: Dict[str, Any]):
        """메트릭 추가"""
        with self.lock:
            metric['_buffer_timestamp'] = time.time()
            self.buffer.append(metric)
    
    def get_recent(self, count: int = None) -> List[Dict[str, Any]]:
        """최근 메트릭 조회"""
        with self.lock:
            if count is None:
                return list(self.buffer)
            return list(self.buffer)[-count:] if self.buffer else []
    
    def get_range(self, start_time: float, end_time: float) -> List[Dict[str, Any]]:
        """시간 범위별 메트릭 조회"""
        with self.lock:
            return [
                metric for metric in self.buffer
                if start_time <= metric.get('_buffer_timestamp', 0) <= end_time
            ]
    
    def clear(self):
        """버퍼 비우기"""
        with self.lock:
            self.buffer.clear()
    
    def size(self) -> int:
        """버퍼 크기 반환"""
        with self.lock:
            return len(self.buffer)


class MetricsCollector:
    """종합 메트릭 수집기"""
    
    def __init__(self, collection_interval: int = 10, buffer_size: int = 1000):
        """
        Args:
            collection_interval: 수집 간격 (초)
            buffer_size: 버퍼 크기
        """
        self.collection_interval = collection_interval
        self.buffer_size = buffer_size
        
        # 메트릭 버퍼들
        self.system_buffer = MetricsBuffer(buffer_size)
        self.model_buffer = MetricsBuffer(buffer_size)
        self.audio_buffer = MetricsBuffer(buffer_size)
        self.custom_buffer = MetricsBuffer(buffer_size)
        
        # 컬렉션 상태
        self.is_collecting = False
        self.collection_thread = None
        self.start_time = None
        
        # 통계 데이터
        self.stats = {
            'total_predictions': 0,
            'total_errors': 0,
            'total_audio_processed': 0,
            'total_processing_time': 0.0
        }
        
        self.stats_lock = threading.RLock()
        
        logger.info("MetricsCollector 초기화 완료")
    
    def start_collection(self):
        """메트릭 수집 시작"""
        if self.is_collecting:
            logger.warning("메트릭 수집이 이미 시작되었습니다")
            return
        
        self.is_collecting = True
        self.start_time = datetime.now()
        
        self.collection_thread = threading.Thread(
            target=self._collection_loop,
            name="MetricsCollection",
            daemon=True
        )
        self.collection_thread.start()
        
        logger.info(f"메트릭 수집 시작 (간격: {self.collection_interval}초)")
    
    def stop_collection(self):
        """메트릭 수집 중지"""
        if not self.is_collecting:
            logger.warning("메트릭 수집이 실행되고 있지 않습니다")
            return
        
        self.is_collecting = False
        
        if self.collection_thread and self.collection_thread.is_alive():
            self.collection_thread.join(timeout=5)
        
        logger.info("메트릭 수집 중지")
    
    def _collection_loop(self):
        """메트릭 수집 루프"""
        logger.info("메트릭 수집 루프 시작")
        
        while self.is_collecting:
            try:
                # 시스템 메트릭 수집
                system_metrics = self._collect_system_metrics()
                self.system_buffer.add(asdict(system_metrics))
                
                # 주기적으로 통계 로깅
                if int(time.time()) % 60 == 0:  # 1분마다
                    self._log_summary_stats()
                
            except Exception as e:
                logger.error(f"메트릭 수집 중 오류: {str(e)}")
            
            time.sleep(self.collection_interval)
        
        logger.info("메트릭 수집 루프 종료")
    
    def _collect_system_metrics(self) -> SystemMetrics:
        """시스템 메트릭 수집"""
        # CPU 사용률
        cpu_percent = psutil.cpu_percent(interval=1)
        
        # 메모리 정보
        memory = psutil.virtual_memory()
        memory_percent = memory.percent
        memory_available_gb = memory.available / (1024**3)
        memory_used_gb = memory.used / (1024**3)
        
        # 디스크 정보
        disk = psutil.disk_usage('/')
        disk_usage_percent = disk.percent
        disk_free_gb = disk.free / (1024**3)
        
        # GPU 정보 (PyTorch 사용)
        gpu_count = 0
        gpu_memory_used_gb = 0.0
        gpu_memory_total_gb = 0.0
        gpu_utilization_percent = 0.0
        
        if torch.cuda.is_available():
            gpu_count = torch.cuda.device_count()
            for i in range(gpu_count):
                gpu_memory_used_gb += torch.cuda.memory_allocated(i) / (1024**3)
                gpu_memory_total_gb += torch.cuda.get_device_properties(i).total_memory / (1024**3)
        
        return SystemMetrics(
            timestamp=datetime.now().isoformat(),
            cpu_percent=cpu_percent,
            memory_percent=memory_percent,
            memory_available_gb=round(memory_available_gb, 2),
            memory_used_gb=round(memory_used_gb, 2),
            disk_usage_percent=disk_usage_percent,
            disk_free_gb=round(disk_free_gb, 2),
            gpu_count=gpu_count,
            gpu_memory_used_gb=round(gpu_memory_used_gb, 2),
            gpu_memory_total_gb=round(gpu_memory_total_gb, 2),
            gpu_utilization_percent=gpu_utilization_percent
        )
    
    def record_prediction(
        self, 
        model_name: str, 
        inference_time_ms: float, 
        success: bool = True,
        cache_hit: bool = False
    ):
        """예측 메트릭 기록"""
        with self.stats_lock:
            self.stats['total_predictions'] += 1
            if not success:
                self.stats['total_errors'] += 1
        
        # 모델별 메트릭 업데이트
        self._update_model_metrics(model_name, inference_time_ms, success, cache_hit)
    
    def record_audio_processing(
        self,
        audio_duration_sec: float,
        processing_time_sec: float,
        feature_extraction_time_ms: float = 0.0,
        preprocessing_time_ms: float = 0.0,
        postprocessing_time_ms: float = 0.0
    ):
        """오디오 처리 메트릭 기록"""
        with self.stats_lock:
            self.stats['total_audio_processed'] += 1
            self.stats['total_processing_time'] += processing_time_sec
        
        audio_metrics = AudioMetrics(
            timestamp=datetime.now().isoformat(),
            total_audio_processed=self.stats['total_audio_processed'],
            avg_audio_duration_sec=round(audio_duration_sec, 3),
            total_processing_time_sec=round(processing_time_sec, 3),
            feature_extraction_time_ms=round(feature_extraction_time_ms, 2),
            preprocessing_time_ms=round(preprocessing_time_ms, 2),
            postprocessing_time_ms=round(postprocessing_time_ms, 2)
        )
        
        self.audio_buffer.add(asdict(audio_metrics))
    
    def record_custom_metric(self, name: str, value: Any, metadata: Dict[str, Any] = None):
        """사용자 정의 메트릭 기록"""
        custom_metric = {
            'timestamp': datetime.now().isoformat(),
            'name': name,
            'value': value,
            'metadata': metadata or {}
        }
        
        self.custom_buffer.add(custom_metric)
    
    def _update_model_metrics(
        self, 
        model_name: str, 
        inference_time_ms: float, 
        success: bool,
        cache_hit: bool
    ):
        """모델 메트릭 업데이트"""
        # 최근 예측들의 통계 계산
        recent_predictions = []
        recent_times = []
        recent_cache_hits = 0
        recent_errors = 0
        
        # 최근 1분간 데이터 수집
        current_time = time.time()
        one_minute_ago = current_time - 60
        
        for metric in self.model_buffer.get_range(one_minute_ago, current_time):
            if metric.get('model_name') == model_name:
                recent_predictions.append(metric)
                if 'inference_time_ms' in metric:
                    recent_times.append(metric['inference_time_ms'])
                if metric.get('cache_hit', False):
                    recent_cache_hits += 1
                if metric.get('success', True) is False:
                    recent_errors += 1
        
        # 새로운 데이터 추가
        recent_times.append(inference_time_ms)
        if cache_hit:
            recent_cache_hits += 1
        if not success:
            recent_errors += 1
        
        # 통계 계산
        total_recent = len(recent_times)
        avg_time = np.mean(recent_times) if recent_times else 0
        min_time = np.min(recent_times) if recent_times else 0
        max_time = np.max(recent_times) if recent_times else 0
        success_rate = (total_recent - recent_errors) / total_recent if total_recent > 0 else 1.0
        cache_hit_rate = recent_cache_hits / total_recent if total_recent > 0 else 0.0
        throughput = total_recent  # 1분간 처리량
        
        model_metrics = ModelMetrics(
            timestamp=datetime.now().isoformat(),
            model_name=model_name,
            prediction_count=total_recent,
            avg_inference_time_ms=round(avg_time, 2),
            min_inference_time_ms=round(min_time, 2),
            max_inference_time_ms=round(max_time, 2),
            error_count=recent_errors,
            success_rate=round(success_rate, 3),
            cache_hit_rate=round(cache_hit_rate, 3),
            throughput_per_minute=throughput
        )
        
        # 모델 메트릭에 추가 정보 포함
        model_metric_dict = asdict(model_metrics)
        model_metric_dict.update({
            'inference_time_ms': inference_time_ms,
            'success': success,
            'cache_hit': cache_hit
        })
        
        self.model_buffer.add(model_metric_dict)
    
    def _log_summary_stats(self):
        """요약 통계 로깅"""
        with self.stats_lock:
            uptime = (datetime.now() - self.start_time).total_seconds() if self.start_time else 0
            
            # 최근 시스템 메트릭
            recent_system = self.system_buffer.get_recent(1)
            system_info = recent_system[0] if recent_system else {}
            
            summary = {
                'uptime_seconds': round(uptime, 1),
                'total_predictions': self.stats['total_predictions'],
                'total_errors': self.stats['total_errors'],
                'total_audio_processed': self.stats['total_audio_processed'],
                'avg_processing_time': (
                    round(self.stats['total_processing_time'] / self.stats['total_audio_processed'], 3)
                    if self.stats['total_audio_processed'] > 0 else 0
                ),
                'cpu_percent': system_info.get('cpu_percent', 0),
                'memory_percent': system_info.get('memory_percent', 0),
                'gpu_memory_used_gb': system_info.get('gpu_memory_used_gb', 0),
                'buffer_sizes': {
                    'system': self.system_buffer.size(),
                    'model': self.model_buffer.size(),
                    'audio': self.audio_buffer.size(),
                    'custom': self.custom_buffer.size()
                }
            }
            
            logger.info("메트릭 요약", extra={'extra_data': summary})
    
    def get_summary_report(self) -> Dict[str, Any]:
        """요약 리포트 생성"""
        with self.stats_lock:
            # 기본 통계
            uptime = (datetime.now() - self.start_time).total_seconds() if self.start_time else 0
            
            # 최근 시스템 메트릭
            recent_system = self.system_buffer.get_recent(5)
            system_stats = {}
            if recent_system:
                cpu_values = [m.get('cpu_percent', 0) for m in recent_system]
                memory_values = [m.get('memory_percent', 0) for m in recent_system]
                
                system_stats = {
                    'avg_cpu_percent': round(np.mean(cpu_values), 2),
                    'max_cpu_percent': round(np.max(cpu_values), 2),
                    'avg_memory_percent': round(np.mean(memory_values), 2),
                    'max_memory_percent': round(np.max(memory_values), 2),
                    'current_gpu_memory_gb': recent_system[-1].get('gpu_memory_used_gb', 0)
                }
            
            # 모델 성능 통계
            recent_models = self.model_buffer.get_recent(100)
            model_stats = defaultdict(list)
            
            for metric in recent_models:
                model_name = metric.get('model_name')
                if model_name and 'inference_time_ms' in metric:
                    model_stats[model_name].append(metric['inference_time_ms'])
            
            model_performance = {}
            for model_name, times in model_stats.items():
                model_performance[model_name] = {
                    'avg_inference_time_ms': round(np.mean(times), 2),
                    'min_inference_time_ms': round(np.min(times), 2),
                    'max_inference_time_ms': round(np.max(times), 2),
                    'prediction_count': len(times)
                }
            
            return {
                'collection_status': {
                    'is_collecting': self.is_collecting,
                    'uptime_seconds': round(uptime, 1),
                    'collection_interval': self.collection_interval,
                    'start_time': self.start_time.isoformat() if self.start_time else None
                },
                'overall_stats': dict(self.stats),
                'system_performance': system_stats,
                'model_performance': model_performance,
                'buffer_status': {
                    'system_buffer_size': self.system_buffer.size(),
                    'model_buffer_size': self.model_buffer.size(),
                    'audio_buffer_size': self.audio_buffer.size(),
                    'custom_buffer_size': self.custom_buffer.size(),
                    'max_buffer_size': self.buffer_size
                },
                'generated_at': datetime.now().isoformat()
            }
    
    def export_metrics(self, output_file: str, format: str = 'json') -> bool:
        """메트릭 데이터 내보내기"""
        try:
            export_data = {
                'metadata': {
                    'export_time': datetime.now().isoformat(),
                    'collection_start': self.start_time.isoformat() if self.start_time else None,
                    'collection_interval': self.collection_interval,
                    'buffer_size': self.buffer_size
                },
                'system_metrics': self.system_buffer.get_recent(),
                'model_metrics': self.model_buffer.get_recent(),
                'audio_metrics': self.audio_buffer.get_recent(),
                'custom_metrics': self.custom_buffer.get_recent(),
                'summary_stats': dict(self.stats)
            }
            
            if format.lower() == 'json':
                with open(output_file, 'w', encoding='utf-8') as f:
                    json.dump(export_data, f, indent=2, ensure_ascii=False)
            else:
                raise ValueError(f"지원하지 않는 형식: {format}")
            
            logger.info(f"메트릭 데이터 내보내기 완료: {output_file}")
            return True
            
        except Exception as e:
            logger.error(f"메트릭 내보내기 실패: {str(e)}")
            return False
    
    def clear_all_buffers(self):
        """모든 버퍼 비우기"""
        self.system_buffer.clear()
        self.model_buffer.clear()
        self.audio_buffer.clear()
        self.custom_buffer.clear()
        
        with self.stats_lock:
            self.stats = {
                'total_predictions': 0,
                'total_errors': 0,
                'total_audio_processed': 0,
                'total_processing_time': 0.0
            }
        
        logger.info("모든 메트릭 버퍼 정리 완료")


class PerformanceMonitor:
    """성능 모니터링 도구"""
    
    def __init__(self, metrics_collector: MetricsCollector = None):
        self.metrics_collector = metrics_collector
        self.monitoring_sessions = {}
        self.alert_thresholds = {
            'cpu_percent': 80.0,
            'memory_percent': 85.0,
            'inference_time_ms': 1000.0,
            'error_rate': 0.1,
            'gpu_memory_percent': 90.0
        }
    
    def start_monitoring_session(self, session_name: str) -> str:
        """모니터링 세션 시작"""
        session_id = f"{session_name}_{int(time.time())}"
        self.monitoring_sessions[session_id] = {
            'name': session_name,
            'start_time': datetime.now(),
            'metrics': []
        }
        
        logger.info(f"모니터링 세션 시작: {session_id}")
        return session_id
    
    def end_monitoring_session(self, session_id: str) -> Dict[str, Any]:
        """모니터링 세션 종료"""
        if session_id not in self.monitoring_sessions:
            logger.warning(f"존재하지 않는 세션: {session_id}")
            return {}
        
        session = self.monitoring_sessions.pop(session_id)
        session['end_time'] = datetime.now()
        session['duration'] = (session['end_time'] - session['start_time']).total_seconds()
        
        logger.info(f"모니터링 세션 종료: {session_id} (지속시간: {session['duration']:.1f}초)")
        return session
    
    def check_system_health(self) -> Dict[str, Any]:
        """시스템 건강성 검사"""
        if not self.metrics_collector:
            return {'status': 'unknown', 'message': 'MetricsCollector가 설정되지 않음'}
        
        # 최근 시스템 메트릭 확인
        recent_system = self.metrics_collector.system_buffer.get_recent(1)
        if not recent_system:
            return {'status': 'unknown', 'message': '시스템 메트릭 데이터 없음'}
        
        current_metrics = recent_system[0]
        alerts = []
        
        # CPU 사용률 검사
        cpu_percent = current_metrics.get('cpu_percent', 0)
        if cpu_percent > self.alert_thresholds['cpu_percent']:
            alerts.append(f"높은 CPU 사용률: {cpu_percent:.1f}%")
        
        # 메모리 사용률 검사
        memory_percent = current_metrics.get('memory_percent', 0)
        if memory_percent > self.alert_thresholds['memory_percent']:
            alerts.append(f"높은 메모리 사용률: {memory_percent:.1f}%")
        
        # GPU 메모리 검사 (가능한 경우)
        gpu_memory_used = current_metrics.get('gpu_memory_used_gb', 0)
        gpu_memory_total = current_metrics.get('gpu_memory_total_gb', 0)
        if gpu_memory_total > 0:
            gpu_memory_percent = (gpu_memory_used / gpu_memory_total) * 100
            if gpu_memory_percent > self.alert_thresholds['gpu_memory_percent']:
                alerts.append(f"높은 GPU 메모리 사용률: {gpu_memory_percent:.1f}%")
        
        # 모델 성능 검사
        recent_models = self.metrics_collector.model_buffer.get_recent(10)
        if recent_models:
            avg_inference_time = np.mean([
                m.get('inference_time_ms', 0) for m in recent_models
                if 'inference_time_ms' in m
            ])
            
            if avg_inference_time > self.alert_thresholds['inference_time_ms']:
                alerts.append(f"느린 추론 속도: {avg_inference_time:.1f}ms")
        
        # 상태 판정
        if not alerts:
            status = 'healthy'
            message = '모든 시스템이 정상 상태입니다'
        elif len(alerts) <= 2:
            status = 'warning'
            message = f"주의 필요: {'; '.join(alerts)}"
        else:
            status = 'critical'
            message = f"심각한 문제: {'; '.join(alerts)}"
        
        health_report = {
            'status': status,
            'message': message,
            'alerts': alerts,
            'metrics': current_metrics,
            'checked_at': datetime.now().isoformat()
        }
        
        if status != 'healthy':
            logger.warning(f"시스템 건강성 검사: {message}")
        
        return health_report
    
    def set_alert_threshold(self, metric_name: str, threshold: float):
        """알림 임계값 설정"""
        self.alert_thresholds[metric_name] = threshold
        logger.info(f"알림 임계값 설정: {metric_name} = {threshold}")
    
    def get_performance_trend(self, hours: int = 1) -> Dict[str, Any]:
        """성능 트렌드 분석"""
        if not self.metrics_collector:
            return {}
        
        # 시간 범위 설정
        end_time = time.time()
        start_time = end_time - (hours * 3600)
        
        # 데이터 수집
        system_metrics = self.metrics_collector.system_buffer.get_range(start_time, end_time)
        model_metrics = self.metrics_collector.model_buffer.get_range(start_time, end_time)
        
        if not system_metrics:
            return {'message': '분석할 데이터가 부족합니다'}
        
        # 시스템 성능 트렌드
        cpu_values = [m.get('cpu_percent', 0) for m in system_metrics]
        memory_values = [m.get('memory_percent', 0) for m in system_metrics]
        
        # 모델 성능 트렌드
        inference_times = [
            m.get('inference_time_ms', 0) for m in model_metrics
            if 'inference_time_ms' in m
        ]
        
        trend_analysis = {
            'time_range_hours': hours,
            'data_points': len(system_metrics),
            'system_performance': {
                'cpu': {
                    'avg': round(np.mean(cpu_values), 2),
                    'min': round(np.min(cpu_values), 2),
                    'max': round(np.max(cpu_values), 2),
                    'std': round(np.std(cpu_values), 2)
                },
                'memory': {
                    'avg': round(np.mean(memory_values), 2),
                    'min': round(np.min(memory_values), 2),
                    'max': round(np.max(memory_values), 2),
                    'std': round(np.std(memory_values), 2)
                }
            },
            'model_performance': {
                'inference_time': {
                    'avg': round(np.mean(inference_times), 2) if inference_times else 0,
                    'min': round(np.min(inference_times), 2) if inference_times else 0,
                    'max': round(np.max(inference_times), 2) if inference_times else 0,
                    'std': round(np.std(inference_times), 2) if inference_times else 0,
                    'count': len(inference_times)
                }
            },
            'generated_at': datetime.now().isoformat()
        }
        
        return trend_analysis