"""
RAG 성능 모니터링 및 최적화 모듈
"""

import time
import logging
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict
import json
import os
from collections import defaultdict, deque

logger = logging.getLogger(__name__)

@dataclass
class RAGMetrics:
    """RAG 성능 메트릭"""
    query_text: str
    search_time: float
    context_length: int
    source_count: int
    relevance_score: Optional[float] = None
    cache_hit: bool = False
    timestamp: str = None
    
    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now().isoformat()

class RAGPerformanceMonitor:
    """RAG 성능 모니터링 시스템"""
    
    def __init__(self, cache_size: int = 100, metrics_file: Optional[str] = None):
        """
        Args:
            cache_size: 캐시 크기
            metrics_file: 메트릭 저장 파일 경로
        """
        self.cache_size = cache_size
        self.metrics_file = metrics_file or "ai/analysis/logs/rag_metrics.jsonl"
        
        # 성능 메트릭 저장소
        self.metrics: deque = deque(maxlen=1000)
        self.cache: Dict[str, Any] = {}
        self.cache_hits = 0
        self.cache_misses = 0
        
        # 통계 데이터
        self.stats = {
            'total_queries': 0,
            'avg_search_time': 0.0,
            'avg_context_length': 0,
            'avg_source_count': 0,
            'cache_hit_rate': 0.0
        }
        
        # 메트릭 파일 디렉토리 생성
        os.makedirs(os.path.dirname(self.metrics_file), exist_ok=True)
    
    def start_query(self, query_text: str) -> str:
        """쿼리 시작 및 ID 반환"""
        query_id = f"{int(time.time() * 1000)}_{hash(query_text) % 10000}"
        self.cache[f"start_{query_id}"] = time.time()
        return query_id
    
    def end_query(self, query_id: str, context: str, source_ids: List[str], 
                  relevance_score: Optional[float] = None) -> RAGMetrics:
        """쿼리 종료 및 메트릭 생성"""
        start_time = self.cache.pop(f"start_{query_id}", time.time())
        search_time = time.time() - start_time
        
        metrics = RAGMetrics(
            query_text=query_id,  # 보안상 실제 텍스트는 저장하지 않음
            search_time=search_time,
            context_length=len(context),
            source_count=len(source_ids),
            relevance_score=relevance_score,
            cache_hit=False
        )
        
        self._add_metrics(metrics)
        return metrics
    
    def cache_query(self, query_text: str, context: str, source_ids: List[str]) -> None:
        """쿼리 결과 캐싱"""
        query_hash = str(hash(query_text))
        self.cache[query_hash] = {
            'context': context,
            'source_ids': source_ids,
            'timestamp': datetime.now().isoformat()
        }
        
        # 캐시 크기 제한
        if len(self.cache) > self.cache_size:
            oldest_key = next(iter(self.cache))
            self.cache.pop(oldest_key)
    
    def get_cached_result(self, query_text: str) -> Optional[Dict[str, Any]]:
        """캐시된 결과 조회"""
        query_hash = str(hash(query_text))
        result = self.cache.get(query_hash)
        
        if result:
            self.cache_hits += 1
            return result
        else:
            self.cache_misses += 1
            return None
    
    def _add_metrics(self, metrics: RAGMetrics) -> None:
        """메트릭 추가"""
        self.metrics.append(metrics)
        self._update_stats()
        self._save_metrics(metrics)
    
    def _update_stats(self) -> None:
        """통계 업데이트"""
        if not self.metrics:
            return
        
        total_queries = len(self.metrics)
        total_search_time = sum(m.search_time for m in self.metrics)
        total_context_length = sum(m.context_length for m in self.metrics)
        total_source_count = sum(m.source_count for m in self.metrics)
        
        self.stats.update({
            'total_queries': total_queries,
            'avg_search_time': total_search_time / total_queries,
            'avg_context_length': total_context_length / total_queries,
            'avg_source_count': total_source_count / total_queries,
            'cache_hit_rate': self.cache_hits / max(self.cache_hits + self.cache_misses, 1)
        })
    
    def _save_metrics(self, metrics: RAGMetrics) -> None:
        """메트릭을 파일에 저장"""
        try:
            with open(self.metrics_file, 'a', encoding='utf-8') as f:
                f.write(json.dumps(asdict(metrics), ensure_ascii=False) + '\n')
        except Exception as e:
            logger.error(f"메트릭 저장 실패: {e}")
    
    def get_performance_report(self) -> Dict[str, Any]:
        """성능 리포트 생성"""
        recent_metrics = list(self.metrics)[-100:]  # 최근 100개
        
        if not recent_metrics:
            return self.stats
        
        # 최근 성능 분석
        recent_stats = {
            'recent_avg_search_time': sum(m.search_time for m in recent_metrics) / len(recent_metrics),
            'recent_avg_context_length': sum(m.context_length for m in recent_metrics) / len(recent_metrics),
            'recent_avg_source_count': sum(m.source_count for m in recent_metrics) / len(recent_metrics),
            'slow_queries_count': sum(1 for m in recent_metrics if m.search_time > 2.0),
            'large_context_count': sum(1 for m in recent_metrics if m.context_length > 2000)
        }
        
        return {**self.stats, **recent_stats}
    
    def get_optimization_suggestions(self) -> List[str]:
        """최적화 제안사항 생성"""
        suggestions = []
        report = self.get_performance_report()
        
        # 검색 시간 최적화
        if report.get('recent_avg_search_time', 0) > 1.0:
            suggestions.append("검색 시간이 1초를 초과합니다. 임베딩 인덱스 최적화를 고려하세요.")
        
        # 캐시 히트율 최적화
        if report.get('cache_hit_rate', 0) < 0.3:
            suggestions.append("캐시 히트율이 낮습니다. 캐시 크기 증가를 고려하세요.")
        
        # 컨텍스트 길이 최적화
        if report.get('recent_avg_context_length', 0) > 2000:
            suggestions.append("컨텍스트 길이가 너무 깁니다. top_k 값을 줄이거나 청크 크기를 조정하세요.")
        
        # 느린 쿼리 최적화
        if report.get('slow_queries_count', 0) > 10:
            suggestions.append("느린 쿼리가 많습니다. 검색 알고리즘 최적화를 고려하세요.")
        
        return suggestions

class RAGOptimizer:
    """RAG 성능 최적화 시스템"""
    
    def __init__(self, monitor: RAGPerformanceMonitor):
        self.monitor = monitor
        self.optimization_history = []
    
    def optimize_search_parameters(self, current_params: Dict[str, Any]) -> Dict[str, Any]:
        """검색 파라미터 최적화"""
        report = self.monitor.get_performance_report()
        optimized_params = current_params.copy()
        
        # 검색 시간 기반 최적화
        if report.get('recent_avg_search_time', 0) > 1.0:
            # top_k 감소
            if 'top_k' in optimized_params:
                optimized_params['top_k'] = max(3, optimized_params['top_k'] - 2)
            
            # 청크 크기 감소
            if 'max_chars_per_chunk' in optimized_params:
                optimized_params['max_chars_per_chunk'] = max(400, optimized_params['max_chars_per_chunk'] - 200)
        
        # 컨텍스트 길이 기반 최적화
        if report.get('recent_avg_context_length', 0) > 2000:
            if 'max_chars_per_chunk' in optimized_params:
                optimized_params['max_chars_per_chunk'] = max(300, optimized_params['max_chars_per_chunk'] - 300)
        
        # 최적화 기록
        self.optimization_history.append({
            'timestamp': datetime.now().isoformat(),
            'original_params': current_params,
            'optimized_params': optimized_params,
            'reason': 'performance_optimization'
        })
        
        return optimized_params
    
    def get_optimization_history(self) -> List[Dict[str, Any]]:
        """최적화 히스토리 반환"""
        return self.optimization_history
