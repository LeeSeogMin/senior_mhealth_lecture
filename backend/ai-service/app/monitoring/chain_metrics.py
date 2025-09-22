"""
Chain Performance Metrics Collection
체인 성능 메트릭 수집 시스템
"""

import logging
import asyncio
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
import json
import os
from collections import deque
import statistics

logger = logging.getLogger(__name__)


class ChainMetrics:
    """체인 실행 메트릭 수집 및 분석"""
    
    def __init__(self, max_history: int = 1000):
        """
        Args:
            max_history: 보관할 최대 메트릭 개수
        """
        self.max_history = max_history
        self.metrics_history = deque(maxlen=max_history)
        self.real_time_metrics = {}
        self.aggregated_metrics = {}
        self.start_time = datetime.now()
        
        # 메트릭 카테고리
        self.metric_categories = {
            'performance': ['execution_time', 'api_latency', 'step_durations'],
            'quality': ['accuracy', 'confidence', 'indicator_scores'],
            'cost': ['api_calls', 'tokens_used', 'estimated_cost'],
            'reliability': ['success_rate', 'error_count', 'timeout_count']
        }
    
    async def record_execution(self, 
                              chain_name: str,
                              execution_time: float,
                              api_calls: int,
                              cost: float,
                              mode: str,
                              context: Dict[str, Any],
                              success: bool = True):
        """
        체인 실행 메트릭 기록
        
        Args:
            chain_name: 체인 이름
            execution_time: 실행 시간 (초)
            api_calls: API 호출 횟수
            cost: 예상 비용
            mode: 실행 모드 ('chaining' 또는 'legacy')
            context: 실행 컨텍스트
            success: 성공 여부
        """
        metrics = {
            'timestamp': datetime.now().isoformat(),
            'chain_name': chain_name,
            'execution_time_ms': execution_time * 1000,
            'api_calls_count': api_calls,
            'estimated_cost': cost,
            'mode': mode,
            'success': success,
            'user_id': context.get('user_id', 'unknown')
        }
        
        # 단계별 시간 추출
        if 'chain_metadata' in context:
            metadata = context['chain_metadata']
            metrics['steps_executed'] = len(metadata.get('steps_executed', []))
            metrics['steps_skipped'] = len(metadata.get('steps_skipped', []))
            metrics['total_steps'] = metrics['steps_executed'] + metrics['steps_skipped']
            
            # 단계별 상세 시간
            step_durations = {}
            for step in metadata.get('steps_executed', []):
                step_durations[step['name']] = step.get('duration', 0)
            metrics['step_durations'] = step_durations
        
        # 5대 지표 점수 추출
        if 'final_indicators' in context:
            indicators = context['final_indicators']
            metrics['indicator_scores'] = {
                key: value.get('score', 0) 
                for key, value in indicators.items()
            }
            metrics['average_confidence'] = statistics.mean([
                value.get('confidence', 0) 
                for value in indicators.values()
            ])
        
        # 위기 감지 정보
        if 'crisis' in context:
            crisis = context['crisis']
            metrics['crisis_detected'] = crisis.get('severity') != 'none'
            metrics['crisis_severity'] = crisis.get('severity')
            metrics['crisis_detection_time'] = crisis.get('processing_time', 0)
        
        # 메트릭 저장
        self.metrics_history.append(metrics)
        self.real_time_metrics = metrics
        
        # 비동기로 BigQuery 전송 (있다면)
        if os.getenv('ENABLE_BIGQUERY', 'false').lower() == 'true':
            await self._send_to_bigquery(metrics)
        
        # 집계 메트릭 업데이트
        self._update_aggregated_metrics(metrics)
        
        logger.info(f"Metrics recorded: {chain_name} - {execution_time:.2f}s - {mode}")
    
    def _update_aggregated_metrics(self, metrics: Dict[str, Any]):
        """
        집계 메트릭 업데이트
        
        Args:
            metrics: 새로운 메트릭
        """
        mode = metrics['mode']
        
        if mode not in self.aggregated_metrics:
            self.aggregated_metrics[mode] = {
                'count': 0,
                'total_time': 0,
                'total_cost': 0,
                'total_api_calls': 0,
                'errors': 0,
                'crisis_detections': 0,
                'indicator_scores_sum': {'DRI': 0, 'SDI': 0, 'CFL': 0, 'ES': 0, 'OV': 0}
            }
        
        agg = self.aggregated_metrics[mode]
        agg['count'] += 1
        agg['total_time'] += metrics['execution_time_ms']
        agg['total_cost'] += metrics['estimated_cost']
        agg['total_api_calls'] += metrics['api_calls_count']
        
        if not metrics['success']:
            agg['errors'] += 1
        
        if metrics.get('crisis_detected'):
            agg['crisis_detections'] += 1
        
        # 지표 점수 누적
        if 'indicator_scores' in metrics:
            for key, score in metrics['indicator_scores'].items():
                if key in agg['indicator_scores_sum']:
                    agg['indicator_scores_sum'][key] += score
    
    def get_real_time_metrics(self) -> Dict[str, Any]:
        """
        실시간 메트릭 반환
        
        Returns:
            최신 메트릭
        """
        return self.real_time_metrics
    
    def get_comparison_metrics(self) -> Dict[str, Any]:
        """
        체이닝 vs 레거시 비교 메트릭
        
        Returns:
            비교 분석 결과
        """
        comparison = {
            'timestamp': datetime.now().isoformat(),
            'duration': (datetime.now() - self.start_time).total_seconds()
        }
        
        # 각 모드별 통계
        for mode in ['chaining', 'legacy']:
            if mode not in self.aggregated_metrics:
                continue
            
            agg = self.aggregated_metrics[mode]
            count = agg['count']
            
            if count == 0:
                continue
            
            comparison[mode] = {
                'count': count,
                'avg_execution_time': agg['total_time'] / count,
                'avg_cost': agg['total_cost'] / count,
                'avg_api_calls': agg['total_api_calls'] / count,
                'error_rate': agg['errors'] / count,
                'crisis_detection_rate': agg['crisis_detections'] / count,
                'avg_indicators': {
                    key: value / count 
                    for key, value in agg['indicator_scores_sum'].items()
                }
            }
        
        # 개선율 계산
        if 'chaining' in comparison and 'legacy' in comparison:
            chaining = comparison['chaining']
            legacy = comparison['legacy']
            
            comparison['improvement'] = {
                'execution_time': self._calculate_improvement(
                    legacy['avg_execution_time'], 
                    chaining['avg_execution_time']
                ),
                'cost': self._calculate_improvement(
                    legacy['avg_cost'], 
                    chaining['avg_cost']
                ),
                'api_calls': self._calculate_improvement(
                    legacy['avg_api_calls'], 
                    chaining['avg_api_calls']
                ),
                'error_rate': self._calculate_improvement(
                    legacy['error_rate'], 
                    chaining['error_rate']
                )
            }
            
            # 체이닝 권장 여부
            comparison['recommendation'] = self._get_recommendation(comparison['improvement'])
        
        return comparison
    
    def _calculate_improvement(self, baseline: float, new_value: float) -> float:
        """
        개선율 계산
        
        Args:
            baseline: 기준값
            new_value: 새로운 값
            
        Returns:
            개선율 (%)
        """
        if baseline == 0:
            return 0
        return ((baseline - new_value) / baseline) * 100
    
    def _get_recommendation(self, improvement: Dict[str, float]) -> str:
        """
        개선율 기반 권장사항
        
        Args:
            improvement: 개선율 딕셔너리
            
        Returns:
            권장사항
        """
        # 실행 시간 30% 이상 개선 AND 에러율 증가 없음
        if improvement['execution_time'] > 30 and improvement['error_rate'] >= 0:
            return 'strongly_recommend'
        
        # 실행 시간 10% 이상 개선 AND 비용 절감
        if improvement['execution_time'] > 10 and improvement['cost'] > 0:
            return 'recommend'
        
        # 성능 저하 또는 에러율 증가
        if improvement['execution_time'] < -10 or improvement['error_rate'] < -20:
            return 'not_recommend'
        
        return 'neutral'
    
    def get_percentile_metrics(self, percentiles: List[int] = [50, 90, 95, 99]) -> Dict[str, Any]:
        """
        백분위수 메트릭 계산
        
        Args:
            percentiles: 계산할 백분위수 리스트
            
        Returns:
            백분위수 메트릭
        """
        if not self.metrics_history:
            return {}
        
        # 실행 시간 추출
        execution_times = [m['execution_time_ms'] for m in self.metrics_history]
        
        result = {}
        for p in percentiles:
            result[f'p{p}'] = statistics.quantiles(execution_times, n=100)[p-1] if len(execution_times) > 1 else execution_times[0]
        
        result['min'] = min(execution_times)
        result['max'] = max(execution_times)
        result['mean'] = statistics.mean(execution_times)
        result['median'] = statistics.median(execution_times)
        
        if len(execution_times) > 1:
            result['stdev'] = statistics.stdev(execution_times)
        
        return result
    
    def get_time_series_metrics(self, interval_minutes: int = 5) -> List[Dict[str, Any]]:
        """
        시계열 메트릭 반환
        
        Args:
            interval_minutes: 집계 간격 (분)
            
        Returns:
            시계열 메트릭 리스트
        """
        if not self.metrics_history:
            return []
        
        # 시간 구간별 그룹화
        time_buckets = {}
        interval = timedelta(minutes=interval_minutes)
        
        for metric in self.metrics_history:
            timestamp = datetime.fromisoformat(metric['timestamp'])
            bucket = timestamp.replace(second=0, microsecond=0)
            bucket = bucket - timedelta(minutes=bucket.minute % interval_minutes)
            
            if bucket not in time_buckets:
                time_buckets[bucket] = []
            time_buckets[bucket].append(metric)
        
        # 구간별 집계
        time_series = []
        for bucket, metrics in sorted(time_buckets.items()):
            aggregated = {
                'timestamp': bucket.isoformat(),
                'count': len(metrics),
                'avg_execution_time': statistics.mean([m['execution_time_ms'] for m in metrics]),
                'error_rate': sum(1 for m in metrics if not m['success']) / len(metrics),
                'modes': {}
            }
            
            # 모드별 분리
            for mode in ['chaining', 'legacy']:
                mode_metrics = [m for m in metrics if m['mode'] == mode]
                if mode_metrics:
                    aggregated['modes'][mode] = {
                        'count': len(mode_metrics),
                        'avg_time': statistics.mean([m['execution_time_ms'] for m in mode_metrics])
                    }
            
            time_series.append(aggregated)
        
        return time_series
    
    async def _send_to_bigquery(self, metrics: Dict[str, Any]):
        """
        BigQuery로 메트릭 전송
        
        Args:
            metrics: 전송할 메트릭
        """
        try:
            # TODO: BigQuery 클라이언트 구현
            # from google.cloud import bigquery
            # client = bigquery.Client()
            # table = client.table('senior-mhealth.metrics.chain_executions')
            # await client.insert_rows_json(table, [metrics])
            
            logger.debug(f"Would send to BigQuery: {metrics['chain_name']}")
        except Exception as e:
            logger.error(f"Failed to send metrics to BigQuery: {e}")
    
    def export_metrics(self, format: str = 'json') -> str:
        """
        메트릭 내보내기
        
        Args:
            format: 출력 형식 ('json' 또는 'csv')
            
        Returns:
            포맷된 메트릭 문자열
        """
        if format == 'json':
            return json.dumps({
                'summary': self.get_comparison_metrics(),
                'percentiles': self.get_percentile_metrics(),
                'time_series': self.get_time_series_metrics(),
                'history': list(self.metrics_history)[-100:]  # 최근 100개
            }, indent=2, default=str)
        
        elif format == 'csv':
            # CSV 형식 구현
            lines = ['timestamp,chain_name,mode,execution_time_ms,api_calls,cost,success']
            for m in self.metrics_history:
                line = f"{m['timestamp']},{m['chain_name']},{m['mode']},"
                line += f"{m['execution_time_ms']},{m['api_calls_count']},"
                line += f"{m['estimated_cost']},{m['success']}"
                lines.append(line)
            return '\n'.join(lines)
        
        return ""
    
    def reset_metrics(self):
        """메트릭 초기화"""
        self.metrics_history.clear()
        self.real_time_metrics = {}
        self.aggregated_metrics = {}
        self.start_time = datetime.now()
        logger.info("Metrics reset")