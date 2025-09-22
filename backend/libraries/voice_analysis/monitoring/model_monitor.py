# 제7강: AI 모델 이해와 로컬 테스트 - 모델 모니터링
"""
AI 모델 전용 모니터링 시스템
모델 성능, 드리프트 감지, 건강성 검사 기능 제공
"""

import os
import json
import time
import threading
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List, Tuple, Callable
from dataclasses import dataclass, asdict
from collections import defaultdict, deque
from pathlib import Path
import numpy as np
import torch
import torch.nn as nn
from scipy import stats

from .logger import get_logger, PerformanceLogger
from .metrics_collector import MetricsCollector


logger = get_logger(__name__)


@dataclass
class ModelHealth:
    """모델 건강성 상태"""
    model_name: str
    timestamp: str
    overall_score: float  # 0-100
    performance_score: float
    stability_score: float
    resource_usage_score: float
    error_rate_score: float
    status: str  # healthy, warning, critical
    issues: List[str]
    recommendations: List[str]


@dataclass
class DriftAlert:
    """모델 드리프트 알림"""
    model_name: str
    timestamp: str
    drift_type: str  # data_drift, concept_drift, performance_drift
    severity: str  # low, medium, high
    metric_name: str
    current_value: float
    baseline_value: float
    drift_score: float
    description: str


class ModelPerformanceTracker:
    """모델 성능 추적기"""
    
    def __init__(self, model_name: str, baseline_metrics: Dict[str, float] = None):
        self.model_name = model_name
        self.baseline_metrics = baseline_metrics or {}
        self.prediction_history = deque(maxlen=1000)
        self.performance_history = deque(maxlen=100)
        self.lock = threading.RLock()
        
    def record_prediction(
        self, 
        prediction: Any, 
        confidence: float, 
        processing_time: float,
        features: Optional[np.ndarray] = None,
        ground_truth: Any = None
    ):
        """예측 결과 기록"""
        with self.lock:
            record = {
                'timestamp': time.time(),
                'prediction': prediction,
                'confidence': confidence,
                'processing_time': processing_time,
                'features_shape': features.shape if features is not None else None,
                'ground_truth': ground_truth,
                'datetime': datetime.now().isoformat()
            }
            
            self.prediction_history.append(record)
    
    def calculate_performance_metrics(self, window_size: int = 100) -> Dict[str, float]:
        """성능 메트릭 계산"""
        with self.lock:
            if len(self.prediction_history) == 0:
                return {}
            
            recent_predictions = list(self.prediction_history)[-window_size:]
            
            # 기본 통계
            confidences = [p['confidence'] for p in recent_predictions]
            processing_times = [p['processing_time'] for p in recent_predictions]
            
            metrics = {
                'avg_confidence': np.mean(confidences),
                'min_confidence': np.min(confidences),
                'max_confidence': np.max(confidences),
                'std_confidence': np.std(confidences),
                'avg_processing_time': np.mean(processing_times),
                'min_processing_time': np.min(processing_times),
                'max_processing_time': np.max(processing_times),
                'std_processing_time': np.std(processing_times),
                'prediction_count': len(recent_predictions)
            }
            
            # 신뢰도 분포
            high_confidence = sum(1 for c in confidences if c > 0.8)
            medium_confidence = sum(1 for c in confidences if 0.5 <= c <= 0.8)
            low_confidence = sum(1 for c in confidences if c < 0.5)
            
            total = len(confidences)
            metrics.update({
                'high_confidence_ratio': high_confidence / total if total > 0 else 0,
                'medium_confidence_ratio': medium_confidence / total if total > 0 else 0,
                'low_confidence_ratio': low_confidence / total if total > 0 else 0
            })
            
            # 정확도 (ground truth가 있는 경우)
            accurate_predictions = sum(
                1 for p in recent_predictions 
                if p['ground_truth'] is not None and p['prediction'] == p['ground_truth']
            )
            total_with_gt = sum(
                1 for p in recent_predictions 
                if p['ground_truth'] is not None
            )
            
            if total_with_gt > 0:
                metrics['accuracy'] = accurate_predictions / total_with_gt
            
            return metrics
    
    def detect_performance_drift(self, current_metrics: Dict[str, float]) -> List[DriftAlert]:
        """성능 드리프트 감지"""
        alerts = []
        
        if not self.baseline_metrics:
            return alerts
        
        for metric_name, current_value in current_metrics.items():
            if metric_name in self.baseline_metrics:
                baseline_value = self.baseline_metrics[metric_name]
                
                # 상대적 변화율 계산
                if baseline_value != 0:
                    change_ratio = abs((current_value - baseline_value) / baseline_value)
                else:
                    change_ratio = abs(current_value)
                
                # 드리프트 판정 임계값
                if change_ratio > 0.2:  # 20% 이상 변화
                    severity = 'high' if change_ratio > 0.5 else 'medium'
                    
                    alert = DriftAlert(
                        model_name=self.model_name,
                        timestamp=datetime.now().isoformat(),
                        drift_type='performance_drift',
                        severity=severity,
                        metric_name=metric_name,
                        current_value=current_value,
                        baseline_value=baseline_value,
                        drift_score=change_ratio,
                        description=f"{metric_name}이(가) 베이스라인 대비 {change_ratio:.1%} 변화"
                    )
                    
                    alerts.append(alert)
        
        return alerts
    
    def get_trend_analysis(self, hours: int = 24) -> Dict[str, Any]:
        """성능 트렌드 분석"""
        with self.lock:
            cutoff_time = time.time() - (hours * 3600)
            recent_predictions = [
                p for p in self.prediction_history 
                if p['timestamp'] > cutoff_time
            ]
            
            if not recent_predictions:
                return {'message': '분석할 데이터가 부족합니다'}
            
            # 시간별 그룹핑
            hourly_data = defaultdict(list)
            for pred in recent_predictions:
                hour = datetime.fromtimestamp(pred['timestamp']).strftime('%Y-%m-%d %H:00')
                hourly_data[hour].append(pred)
            
            # 시간별 통계
            hourly_stats = {}
            for hour, predictions in hourly_data.items():
                confidences = [p['confidence'] for p in predictions]
                processing_times = [p['processing_time'] for p in predictions]
                
                hourly_stats[hour] = {
                    'prediction_count': len(predictions),
                    'avg_confidence': np.mean(confidences),
                    'avg_processing_time': np.mean(processing_times),
                    'min_confidence': np.min(confidences),
                    'max_confidence': np.max(confidences)
                }
            
            # 전체 트렌드
            all_confidences = [p['confidence'] for p in recent_predictions]
            all_times = [p['processing_time'] for p in recent_predictions]
            
            # 선형 회귀를 통한 트렌드 분석
            if len(all_confidences) > 1:
                x = np.arange(len(all_confidences))
                confidence_slope, _, confidence_r, _, _ = stats.linregress(x, all_confidences)
                time_slope, _, time_r, _, _ = stats.linregress(x, all_times)
            else:
                confidence_slope = time_slope = confidence_r = time_r = 0
            
            return {
                'time_range_hours': hours,
                'total_predictions': len(recent_predictions),
                'hourly_breakdown': hourly_stats,
                'overall_trends': {
                    'confidence_trend': {
                        'slope': confidence_slope,
                        'correlation': confidence_r,
                        'direction': 'increasing' if confidence_slope > 0 else 'decreasing' if confidence_slope < 0 else 'stable'
                    },
                    'processing_time_trend': {
                        'slope': time_slope,
                        'correlation': time_r,
                        'direction': 'increasing' if time_slope > 0 else 'decreasing' if time_slope < 0 else 'stable'
                    }
                },
                'current_stats': {
                    'avg_confidence': np.mean(all_confidences),
                    'avg_processing_time': np.mean(all_times),
                    'confidence_std': np.std(all_confidences),
                    'processing_time_std': np.std(all_times)
                }
            }


class ModelHealthChecker:
    """모델 건강성 검사기"""
    
    def __init__(self, metrics_collector: MetricsCollector = None):
        self.metrics_collector = metrics_collector
        self.health_thresholds = {
            'min_confidence': 0.7,
            'max_processing_time': 500.0,  # ms
            'max_error_rate': 0.05,  # 5%
            'min_prediction_count': 10,
            'max_memory_usage_mb': 1000.0
        }
        
        self.model_trackers: Dict[str, ModelPerformanceTracker] = {}
        
    def register_model(self, model_name: str, baseline_metrics: Dict[str, float] = None):
        """모델 등록"""
        self.model_trackers[model_name] = ModelPerformanceTracker(model_name, baseline_metrics)
        logger.info(f"모델 등록 완료: {model_name}")
    
    def record_model_prediction(
        self,
        model_name: str,
        prediction: Any,
        confidence: float,
        processing_time: float,
        features: Optional[np.ndarray] = None,
        ground_truth: Any = None
    ):
        """모델 예측 결과 기록"""
        if model_name not in self.model_trackers:
            self.register_model(model_name)
        
        self.model_trackers[model_name].record_prediction(
            prediction, confidence, processing_time, features, ground_truth
        )
    
    def check_model_health(self, model_name: str) -> ModelHealth:
        """모델 건강성 검사"""
        if model_name not in self.model_trackers:
            return ModelHealth(
                model_name=model_name,
                timestamp=datetime.now().isoformat(),
                overall_score=0.0,
                performance_score=0.0,
                stability_score=0.0,
                resource_usage_score=0.0,
                error_rate_score=0.0,
                status='unknown',
                issues=['모델이 등록되지 않음'],
                recommendations=['모델을 먼저 등록하세요']
            )
        
        tracker = self.model_trackers[model_name]
        metrics = tracker.calculate_performance_metrics()
        
        if not metrics:
            return ModelHealth(
                model_name=model_name,
                timestamp=datetime.now().isoformat(),
                overall_score=0.0,
                performance_score=0.0,
                stability_score=0.0,
                resource_usage_score=0.0,
                error_rate_score=0.0,
                status='no_data',
                issues=['예측 데이터가 없음'],
                recommendations=['모델을 사용하여 예측을 수행하세요']
            )
        
        # 성능 점수 계산 (0-100)
        performance_score = self._calculate_performance_score(metrics)
        
        # 안정성 점수 계산
        stability_score = self._calculate_stability_score(metrics)
        
        # 리소스 사용량 점수 계산
        resource_usage_score = self._calculate_resource_score(metrics)
        
        # 오류율 점수 계산
        error_rate_score = self._calculate_error_rate_score(model_name)
        
        # 종합 점수 계산
        overall_score = (
            performance_score * 0.3 +
            stability_score * 0.25 +
            resource_usage_score * 0.25 +
            error_rate_score * 0.2
        )
        
        # 상태 판정
        if overall_score >= 80:
            status = 'healthy'
        elif overall_score >= 60:
            status = 'warning'
        else:
            status = 'critical'
        
        # 문제점 및 권장사항 생성
        issues, recommendations = self._generate_issues_and_recommendations(metrics, overall_score)
        
        return ModelHealth(
            model_name=model_name,
            timestamp=datetime.now().isoformat(),
            overall_score=round(overall_score, 1),
            performance_score=round(performance_score, 1),
            stability_score=round(stability_score, 1),
            resource_usage_score=round(resource_usage_score, 1),
            error_rate_score=round(error_rate_score, 1),
            status=status,
            issues=issues,
            recommendations=recommendations
        )
    
    def _calculate_performance_score(self, metrics: Dict[str, float]) -> float:
        """성능 점수 계산"""
        score = 100.0
        
        # 신뢰도 검사
        avg_confidence = metrics.get('avg_confidence', 0)
        if avg_confidence < self.health_thresholds['min_confidence']:
            penalty = (self.health_thresholds['min_confidence'] - avg_confidence) * 50
            score -= penalty
        
        # 처리 시간 검사
        avg_processing_time = metrics.get('avg_processing_time', 0)
        if avg_processing_time > self.health_thresholds['max_processing_time']:
            penalty = min(30, (avg_processing_time - self.health_thresholds['max_processing_time']) / 100)
            score -= penalty
        
        # 정확도 검사 (있는 경우)
        accuracy = metrics.get('accuracy')
        if accuracy is not None:
            if accuracy < 0.8:
                penalty = (0.8 - accuracy) * 50
                score -= penalty
        
        return max(0.0, score)
    
    def _calculate_stability_score(self, metrics: Dict[str, float]) -> float:
        """안정성 점수 계산"""
        score = 100.0
        
        # 신뢰도 변동성 검사
        confidence_std = metrics.get('std_confidence', 0)
        if confidence_std > 0.2:
            penalty = min(30, confidence_std * 100)
            score -= penalty
        
        # 처리 시간 변동성 검사
        time_std = metrics.get('std_processing_time', 0)
        time_avg = metrics.get('avg_processing_time', 1)
        if time_avg > 0:
            cv = time_std / time_avg  # 변동계수
            if cv > 0.3:
                penalty = min(25, cv * 50)
                score -= penalty
        
        # 저신뢰도 예측 비율 검사
        low_confidence_ratio = metrics.get('low_confidence_ratio', 0)
        if low_confidence_ratio > 0.1:
            penalty = min(20, low_confidence_ratio * 100)
            score -= penalty
        
        return max(0.0, score)
    
    def _calculate_resource_score(self, metrics: Dict[str, float]) -> float:
        """리소스 사용량 점수 계산"""
        score = 100.0
        
        # 처리 시간 기반 리소스 효율성
        avg_processing_time = metrics.get('avg_processing_time', 0)
        if avg_processing_time > 200:
            penalty = min(40, (avg_processing_time - 200) / 50)
            score -= penalty
        
        # 시스템 메트릭이 있는 경우 추가 검사
        if self.metrics_collector:
            recent_system = self.metrics_collector.system_buffer.get_recent(1)
            if recent_system:
                system_metrics = recent_system[0]
                
                # GPU 메모리 사용량 검사
                gpu_memory_used = system_metrics.get('gpu_memory_used_gb', 0)
                gpu_memory_total = system_metrics.get('gpu_memory_total_gb', 0)
                if gpu_memory_total > 0:
                    gpu_usage_ratio = gpu_memory_used / gpu_memory_total
                    if gpu_usage_ratio > 0.9:
                        score -= 20
                
                # CPU 사용량 검사
                cpu_percent = system_metrics.get('cpu_percent', 0)
                if cpu_percent > 80:
                    score -= 15
        
        return max(0.0, score)
    
    def _calculate_error_rate_score(self, model_name: str) -> float:
        """오류율 점수 계산"""
        score = 100.0
        
        if self.metrics_collector:
            # 최근 모델 메트릭에서 오류율 확인
            recent_models = self.metrics_collector.model_buffer.get_recent(50)
            model_metrics = [m for m in recent_models if m.get('model_name') == model_name]
            
            if model_metrics:
                error_counts = [m.get('error_count', 0) for m in model_metrics]
                prediction_counts = [m.get('prediction_count', 1) for m in model_metrics]
                
                total_errors = sum(error_counts)
                total_predictions = sum(prediction_counts)
                
                if total_predictions > 0:
                    error_rate = total_errors / total_predictions
                    if error_rate > self.health_thresholds['max_error_rate']:
                        penalty = min(50, error_rate * 500)
                        score -= penalty
        
        return max(0.0, score)
    
    def _generate_issues_and_recommendations(
        self, 
        metrics: Dict[str, float], 
        overall_score: float
    ) -> Tuple[List[str], List[str]]:
        """문제점 및 권장사항 생성"""
        issues = []
        recommendations = []
        
        # 신뢰도 문제
        avg_confidence = metrics.get('avg_confidence', 0)
        if avg_confidence < self.health_thresholds['min_confidence']:
            issues.append(f"낮은 평균 신뢰도: {avg_confidence:.3f}")
            recommendations.append("모델 재학습 또는 하이퍼파라미터 튜닝 검토")
        
        # 처리 시간 문제
        avg_processing_time = metrics.get('avg_processing_time', 0)
        if avg_processing_time > self.health_thresholds['max_processing_time']:
            issues.append(f"느린 처리 속도: {avg_processing_time:.1f}ms")
            recommendations.append("모델 최적화 또는 하드웨어 업그레이드 고려")
        
        # 안정성 문제
        confidence_std = metrics.get('std_confidence', 0)
        if confidence_std > 0.2:
            issues.append(f"신뢰도 변동이 큼: {confidence_std:.3f}")
            recommendations.append("입력 데이터 품질 검토 및 전처리 개선")
        
        # 정확도 문제 (있는 경우)
        accuracy = metrics.get('accuracy')
        if accuracy is not None and accuracy < 0.8:
            issues.append(f"낮은 정확도: {accuracy:.3f}")
            recommendations.append("라벨 품질 검토 및 모델 아키텍처 개선")
        
        # 전반적인 권장사항
        if overall_score < 60:
            recommendations.append("즉시 모델 점검 및 개선 조치 필요")
        elif overall_score < 80:
            recommendations.append("성능 모니터링 강화 및 개선 계획 수립")
        
        if not issues:
            issues.append("감지된 문제 없음")
        
        if not recommendations:
            recommendations.append("현재 상태 유지")
        
        return issues, recommendations
    
    def set_health_threshold(self, threshold_name: str, value: float):
        """건강성 임계값 설정"""
        self.health_thresholds[threshold_name] = value
        logger.info(f"건강성 임계값 설정: {threshold_name} = {value}")


class ModelMonitor:
    """종합 모델 모니터링 시스템"""
    
    def __init__(self, metrics_collector: MetricsCollector = None):
        self.metrics_collector = metrics_collector
        self.health_checker = ModelHealthChecker(metrics_collector)
        self.drift_alerts = deque(maxlen=100)
        self.monitoring_config = {
            'health_check_interval': 300,  # 5분
            'drift_check_interval': 600,   # 10분
            'alert_retention_hours': 24
        }
        
        self.is_monitoring = False
        self.monitoring_thread = None
        self.registered_models = set()
        
    def register_model(self, model_name: str, baseline_metrics: Dict[str, float] = None):
        """모델 등록"""
        self.registered_models.add(model_name)
        self.health_checker.register_model(model_name, baseline_metrics)
        logger.info(f"모델 모니터링 등록: {model_name}")
    
    def start_monitoring(self):
        """모니터링 시작"""
        if self.is_monitoring:
            logger.warning("모델 모니터링이 이미 시작되었습니다")
            return
        
        self.is_monitoring = True
        self.monitoring_thread = threading.Thread(
            target=self._monitoring_loop,
            name="ModelMonitoring",
            daemon=True
        )
        self.monitoring_thread.start()
        
        logger.info("모델 모니터링 시작")
    
    def stop_monitoring(self):
        """모니터링 중지"""
        if not self.is_monitoring:
            logger.warning("모델 모니터링이 실행되고 있지 않습니다")
            return
        
        self.is_monitoring = False
        
        if self.monitoring_thread and self.monitoring_thread.is_alive():
            self.monitoring_thread.join(timeout=10)
        
        logger.info("모델 모니터링 중지")
    
    def _monitoring_loop(self):
        """모니터링 루프"""
        logger.info("모델 모니터링 루프 시작")
        
        last_health_check = 0
        last_drift_check = 0
        
        while self.is_monitoring:
            try:
                current_time = time.time()
                
                # 건강성 검사
                if current_time - last_health_check >= self.monitoring_config['health_check_interval']:
                    self._perform_health_checks()
                    last_health_check = current_time
                
                # 드리프트 검사
                if current_time - last_drift_check >= self.monitoring_config['drift_check_interval']:
                    self._perform_drift_checks()
                    last_drift_check = current_time
                
            except Exception as e:
                logger.error(f"모델 모니터링 중 오류: {str(e)}")
            
            time.sleep(30)  # 30초 간격으로 체크
        
        logger.info("모델 모니터링 루프 종료")
    
    def _perform_health_checks(self):
        """모든 등록된 모델의 건강성 검사"""
        for model_name in self.registered_models:
            try:
                health = self.health_checker.check_model_health(model_name)
                
                # 심각한 상태인 경우 알림
                if health.status == 'critical':
                    logger.error(f"모델 상태 심각: {model_name} (점수: {health.overall_score})")
                    logger.error(f"문제점: {', '.join(health.issues)}")
                elif health.status == 'warning':
                    logger.warning(f"모델 상태 주의: {model_name} (점수: {health.overall_score})")
                else:
                    logger.debug(f"모델 상태 양호: {model_name} (점수: {health.overall_score})")
                
            except Exception as e:
                logger.error(f"모델 {model_name} 건강성 검사 실패: {str(e)}")
    
    def _perform_drift_checks(self):
        """모든 등록된 모델의 드리프트 검사"""
        for model_name in self.registered_models:
            try:
                tracker = self.health_checker.model_trackers.get(model_name)
                if tracker:
                    current_metrics = tracker.calculate_performance_metrics()
                    alerts = tracker.detect_performance_drift(current_metrics)
                    
                    for alert in alerts:
                        self.drift_alerts.append(alert)
                        
                        if alert.severity == 'high':
                            logger.error(f"높은 수준의 드리프트 감지: {alert.description}")
                        else:
                            logger.warning(f"드리프트 감지: {alert.description}")
                
            except Exception as e:
                logger.error(f"모델 {model_name} 드리프트 검사 실패: {str(e)}")
    
    def get_monitoring_summary(self) -> Dict[str, Any]:
        """모니터링 요약 정보"""
        summary = {
            'monitoring_status': 'active' if self.is_monitoring else 'inactive',
            'registered_models': list(self.registered_models),
            'model_count': len(self.registered_models),
            'recent_alerts': [],
            'overall_health': {},
            'configuration': self.monitoring_config,
            'generated_at': datetime.now().isoformat()
        }
        
        # 최근 알림 정보
        recent_cutoff = time.time() - (self.monitoring_config['alert_retention_hours'] * 3600)
        recent_alerts = [
            asdict(alert) for alert in self.drift_alerts 
            if datetime.fromisoformat(alert.timestamp).timestamp() > recent_cutoff
        ]
        summary['recent_alerts'] = recent_alerts
        
        # 각 모델의 건강성 정보
        for model_name in self.registered_models:
            try:
                health = self.health_checker.check_model_health(model_name)
                summary['overall_health'][model_name] = {
                    'status': health.status,
                    'score': health.overall_score,
                    'issues_count': len(health.issues)
                }
            except Exception as e:
                summary['overall_health'][model_name] = {
                    'status': 'error',
                    'error': str(e)
                }
        
        return summary
    
    def get_model_detailed_report(self, model_name: str) -> Dict[str, Any]:
        """특정 모델의 상세 리포트"""
        if model_name not in self.registered_models:
            return {'error': f'등록되지 않은 모델: {model_name}'}
        
        try:
            # 건강성 정보
            health = self.health_checker.check_model_health(model_name)
            
            # 성능 트렌드
            tracker = self.health_checker.model_trackers.get(model_name)
            trend_analysis = tracker.get_trend_analysis() if tracker else {}
            
            # 관련 드리프트 알림
            model_alerts = [
                asdict(alert) for alert in self.drift_alerts 
                if alert.model_name == model_name
            ]
            
            return {
                'model_name': model_name,
                'health_status': asdict(health),
                'performance_trends': trend_analysis,
                'drift_alerts': model_alerts[-10:],  # 최근 10개
                'generated_at': datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"모델 {model_name} 상세 리포트 생성 실패: {str(e)}")
            return {'error': f'리포트 생성 실패: {str(e)}'}
    
    def export_monitoring_data(self, output_file: str) -> bool:
        """모니터링 데이터 내보내기"""
        try:
            export_data = {
                'export_metadata': {
                    'export_time': datetime.now().isoformat(),
                    'monitoring_status': 'active' if self.is_monitoring else 'inactive',
                    'registered_models': list(self.registered_models)
                },
                'monitoring_summary': self.get_monitoring_summary(),
                'model_reports': {}
            }
            
            # 각 모델의 상세 리포트
            for model_name in self.registered_models:
                export_data['model_reports'][model_name] = self.get_model_detailed_report(model_name)
            
            # JSON 파일로 저장
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(export_data, f, indent=2, ensure_ascii=False)
            
            logger.info(f"모니터링 데이터 내보내기 완료: {output_file}")
            return True
            
        except Exception as e:
            logger.error(f"모니터링 데이터 내보내기 실패: {str(e)}")
            return False