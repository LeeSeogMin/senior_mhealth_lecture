import numpy as np
from scipy import stats
from datetime import datetime
from typing import Dict, List
import logging

class ChangeDetector:
    """시계열 변화점 감지 시스템"""
    def __init__(self, significance_level: float = 0.05):
        self.significance_level = significance_level
        self.logger = logging.getLogger(__name__)

    def detect_changes(self, time_series_data: List[Dict], baseline: Dict) -> Dict:
        """전체 변화점 감지 분석"""
        # 시계열 데이터 정렬
        sorted_data = sorted(time_series_data, key=lambda x: x['analysis_timestamp'])
        results = {
            'change_points': [],
            'trend_analysis': {},
            'statistical_tests': {},
            'significance_level': self.significance_level
        }
        # 정신건강 지표별 변화점 감지
        for metric in ['depression', 'cognitive']:
            metric_values = [data['mentalHealthAnalysis'][metric]['score'] for data in sorted_data]
            timestamps = [data['analysis_timestamp'] for data in sorted_data]
            # CUSUM 변화점 감지
            change_points = self._cusum_change_detection(metric_values)
            # 추세 분석
            trend_result = self._analyze_trend(metric_values, timestamps)
            # 베이스라인과의 비교
            baseline_comparison = self._compare_with_baseline(metric_values, baseline['mental_health'][metric])
            results['change_points'].extend([
                {
                    'metric': metric,
                    'timestamp': timestamps[cp],
                    'index': cp,
                    'value': metric_values[cp]
                } for cp in change_points
            ])
            results['trend_analysis'][metric] = trend_result
            results['statistical_tests'][metric] = baseline_comparison
        # 음성 패턴 변화 감지
        removed_changes = self._detect_removed_pattern_changes(sorted_data, baseline)
        results['removed_pattern_changes'] = removed_changes
        return results

    def _cusum_change_detection(self, values: List[float], threshold: float = 5.0) -> List[int]:
        """CUSUM 알고리즘을 사용한 변화점 감지"""
        if len(values) < 3:
            return []
        mean_val = np.mean(values)
        cusum_pos = 0
        cusum_neg = 0
        change_points = []
        for i, value in enumerate(values):
            deviation = value - mean_val
            cusum_pos = max(0, cusum_pos + deviation)
            cusum_neg = min(0, cusum_neg + deviation)
            if abs(cusum_pos) > threshold or abs(cusum_neg) > threshold:
                change_points.append(i)
                cusum_pos = 0
                cusum_neg = 0
        return change_points

    def _analyze_trend(self, values: List[float], timestamps: List[str]) -> Dict:
        """추세 분석 (선형 회귀)"""
        if len(values) < 3:
            return {'trend': 'insufficient_data'}
        time_numeric = [(datetime.fromisoformat(ts.replace('Z', '+00:00')) - datetime.fromisoformat(timestamps[0].replace('Z', '+00:00'))).days for ts in timestamps]
        slope, intercept, r_value, p_value, std_err = stats.linregress(time_numeric, values)
        if p_value < self.significance_level:
            if slope > 0:
                trend_direction = 'increasing'
            else:
                trend_direction = 'decreasing'
        else:
            trend_direction = 'stable'
        return {
            'trend': trend_direction,
            'slope': slope,
            'r_squared': r_value ** 2,
            'p_value': p_value,
            'significance': p_value < self.significance_level,
            'rate_of_change': abs(slope) * 30
        }

    def _compare_with_baseline(self, current_values: List[float], baseline_stats: Dict) -> Dict:
        """베이스라인과의 통계적 비교"""
        if len(current_values) < 2:
            return {'test': 'insufficient_data'}
        baseline_mean = baseline_stats['mean']
        baseline_std = baseline_stats['std']
        t_stat, p_value = stats.ttest_1samp(current_values, baseline_mean)
        current_mean = np.mean(current_values)
        z_score = (current_mean - baseline_mean) / baseline_std if baseline_std > 0 else 0
        return {
            'test': 'one_sample_t_test',
            't_statistic': t_stat,
            'p_value': p_value,
            'significant_change': p_value < self.significance_level,
            'z_score': z_score,
            'current_mean': current_mean,
            'baseline_mean': baseline_mean,
            'deviation_magnitude': abs(z_score)
        }

    def _detect_removed_pattern_changes(self, data: List[Dict], baseline: Dict) -> Dict:
        """패턴 변화 감지"""
        removed_changes = {}
        for pattern in ['speech_rate', 'pause_ratio']:
            # 카멜 케이스 키에 맞게 접근 (speechRate, pauseRatio)
            pattern_key = 'speechRate' if pattern == 'speech_rate' else 'pauseRatio'
            values = [d.get('voicePatterns', {}).get(pattern_key, 120 if pattern_key == 'speechRate' else 0.3) for d in data]
            baseline_stats = baseline.get('removed_patterns', {}).get(pattern, {
                'mean': 120 if pattern == 'speech_rate' else 0.3,
                'std': 10 if pattern == 'speech_rate' else 0.1
            })
            comparison = self._compare_with_baseline(values, baseline_stats)
            removed_changes[pattern] = comparison
        return removed_changes