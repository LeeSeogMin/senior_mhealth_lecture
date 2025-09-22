import numpy as np
import pandas as pd
from scipy import stats
from scipy.stats import kendalltau
from sklearn.linear_model import LinearRegression
from sklearn.preprocessing import StandardScaler
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
import logging
import warnings
from statsmodels.tsa.seasonal import seasonal_decompose
from statsmodels.nonparametric.smoothers_lowess import lowess

class TrendAnalyzer:
    """
    고급 시계열 추세 분석기
    
    Mann-Kendall 추세 검정, Sen's slope 추정, 계절성 분해 등의
    통계적 기법을 활용한 포괄적인 추세 분석 기능을 제공합니다.
    """
    
    def __init__(self, significance_level: float = 0.05):
        """
        Args:
            significance_level: 통계적 유의성 판단 기준 (기본값: 0.05)
        """
        self.significance_level = significance_level
        self.logger = logging.getLogger(__name__)
        
    def analyze_trends(self, data: List[Dict], baseline: Optional[Dict] = None) -> Dict:
        """
        포괄적 추세 분석 수행
        
        Args:
            data: 시계열 데이터 리스트
            baseline: 베이스라인 정보 (선택사항)
            
        Returns:
            종합적인 추세 분석 결과
        """
        if len(data) < 5:
            return self._insufficient_data_response()
            
        # 시간 순으로 정렬
        sorted_data = sorted(data, key=lambda x: x['analysis_timestamp'])
        
        # 타임스탬프와 수치 데이터 추출
        timestamps = [datetime.fromisoformat(d['analysis_timestamp'].replace('Z', '+00:00')) 
                     for d in sorted_data]
        
        results = {
            'analysis_date': datetime.now().isoformat(),
            'data_points': len(sorted_data),
            'time_span_days': (timestamps[-1] - timestamps[0]).days,
            'trends': {}
        }
        
        # 각 지표별 추세 분석
        # 데이터 구조에 따라 유연하게 처리
        if sorted_data and 'indicators' in sorted_data[0]:
            # 새로운 형식 (indicators.DRI, SDI, etc.)
            metrics = ['DRI', 'SDI', 'CFL', 'ES', 'OV']
            for metric in metrics:
                values = [d['indicators'].get(metric, 0) for d in sorted_data]
                results['trends'][metric] = self._analyze_metric_trend(
                    timestamps, values, metric, baseline
                )
        elif sorted_data and 'mentalHealthAnalysis' in sorted_data[0]:
            # 기존 형식
            metrics = ['depression', 'cognitive']
            for metric in metrics:
                values = [d['mentalHealthAnalysis'][metric]['score'] for d in sorted_data]
                results['trends'][metric] = self._analyze_metric_trend(
                    timestamps, values, metric, baseline
                )
        else:
            # 기본 처리
            return self._insufficient_data_response()
        # 제거된 추세 분석
        removed_trends = self._analyze_removed_trends(sorted_data, timestamps)
        results['trends']['removed_patterns'] = removed_trends
        
        # 전체적인 추세 요약
        results['summary'] = self._generate_trend_summary(results['trends'])
        
        return results
    
    def _analyze_metric_trend(self, timestamps: List[datetime], values: List[float], 
                             metric: str, baseline: Optional[Dict]) -> Dict:
        """개별 지표의 추세 분석"""
        
        # 1. Mann-Kendall 추세 검정
        mk_result = self._mann_kendall_test(values)
        
        # 2. Sen's slope 추정
        sens_slope = self._calculate_sens_slope(values)
        
        # 3. 선형 회귀 추세
        linear_trend = self._linear_trend_analysis(timestamps, values)
        
        # 4. 변동성 분석
        volatility_analysis = self._analyze_volatility(values)
        
        # 5. 베이스라인과의 비교 (있는 경우)
        baseline_comparison = None
        if baseline and metric in baseline.get('mental_health', {}):
            baseline_comparison = self._compare_with_baseline(
                values, baseline['mental_health'][metric]
            )
        
        # 6. 계절성 분석 (데이터가 충분한 경우)
        seasonality = self._analyze_seasonality(values) if len(values) >= 12 else None
        
        return {
            'mann_kendall': mk_result,
            'sens_slope': sens_slope,
            'linear_trend': linear_trend,
            'volatility': volatility_analysis,
            'baseline_comparison': baseline_comparison,
            'seasonality': seasonality,
            'trend_strength': self._calculate_trend_strength(mk_result, sens_slope),
            'confidence_level': self._calculate_confidence(len(values), mk_result['p_value'])
        }
    
    def _mann_kendall_test(self, values: List[float]) -> Dict:
        """Mann-Kendall 추세 검정 수행"""
        n = len(values)
        
        # Kendall's S 통계량 계산
        s = 0
        for i in range(n-1):
            for j in range(i+1, n):
                s += np.sign(values[j] - values[i])
        
        # 분산 계산 (타이 값 보정 포함)
        unique_values, counts = np.unique(values, return_counts=True)
        tie_correction = sum(c * (c - 1) * (2 * c + 5) for c in counts if c > 1)
        var_s = (n * (n - 1) * (2 * n + 5) - tie_correction) / 18
        
        # Z 점수 계산
        if s > 0:
            z = (s - 1) / np.sqrt(var_s) if var_s > 0 else 0
        elif s < 0:
            z = (s + 1) / np.sqrt(var_s) if var_s > 0 else 0
        else:
            z = 0
        
        # p-value 계산
        p_value = 2 * (1 - stats.norm.cdf(abs(z)))
        
        # 추세 방향 결정
        if p_value < self.significance_level:
            trend = 'increasing' if s > 0 else 'decreasing'
        else:
            trend = 'no_trend'
        
        return {
            'statistic': s,
            'z_score': z,
            'p_value': p_value,
            'trend': trend,
            'significant': p_value < self.significance_level,
            'tau': s / (n * (n - 1) / 2)  # Kendall's tau 계산
        }
    
    def _calculate_sens_slope(self, values: List[float]) -> Dict:
        """Sen's slope 추정 (비모수적 기울기)"""
        n = len(values)
        slopes = []
        
        for i in range(n-1):
            for j in range(i+1, n):
                if j != i:
                    slope = (values[j] - values[i]) / (j - i)
                    slopes.append(slope)
        
        if not slopes:
            return {'slope': 0, 'confidence_interval': (0, 0)}
        
        # 중앙값이 Sen's slope
        sens_slope = np.median(slopes)
        
        # 95% 신뢰구간 계산
        slopes_sorted = np.sort(slopes)
        n_slopes = len(slopes_sorted)
        alpha = 1 - 0.95
        rank_lower = int(np.floor((n_slopes - 1.96 * np.sqrt(n_slopes)) / 2))
        rank_upper = int(np.ceil((n_slopes + 1.96 * np.sqrt(n_slopes)) / 2))
        
        rank_lower = max(0, rank_lower)
        rank_upper = min(n_slopes - 1, rank_upper)
        
        confidence_interval = (slopes_sorted[rank_lower], slopes_sorted[rank_upper])
        
        return {
            'slope': sens_slope,
            'confidence_interval': confidence_interval,
            'interpretation': self._interpret_slope(sens_slope)
        }
    
    def _linear_trend_analysis(self, timestamps: List[datetime], values: List[float]) -> Dict:
        """선형 회귀를 이용한 추세 분석"""
        # 시간을 수치로 변환 (첫 번째 시점을 0으로)
        time_numeric = [(t - timestamps[0]).total_seconds() / 86400 for t in timestamps]
        X = np.array(time_numeric).reshape(-1, 1)
        y = np.array(values)
        
        # 선형 회귀 적합
        model = LinearRegression()
        model.fit(X, y)
        
        # 예측값 계산
        y_pred = model.predict(X)
        
        # 통계 계산
        r_squared = model.score(X, y)
        mse = np.mean((y - y_pred) ** 2)
        slope_per_day = model.coef_[0]
        slope_per_month = slope_per_day * 30  # 월간 변화율
        
        # t-검정으로 기울기의 유의성 검증
        n = len(values)
        residuals = y - y_pred
        mse_residuals = np.sum(residuals**2) / (n - 2)
        se_slope = np.sqrt(mse_residuals / np.sum((time_numeric - np.mean(time_numeric))**2))
        t_stat = slope_per_day / se_slope if se_slope > 0 else 0
        p_value = 2 * (1 - stats.t.cdf(abs(t_stat), n - 2))
        
        return {
            'slope_per_day': slope_per_day,
            'slope_per_month': slope_per_month,
            'intercept': model.intercept_,
            'r_squared': r_squared,
            'mse': mse,
            't_statistic': t_stat,
            'p_value': p_value,
            'significant': p_value < self.significance_level
        }
    
    def _analyze_volatility(self, values: List[float]) -> Dict:
        """변동성 분석"""
        if len(values) < 3:
            return {'volatility': 0, 'stability': 'insufficient_data'}
        
        # 기본 변동성 지표들
        volatility = np.std(values)
        coefficient_of_variation = volatility / np.mean(values) if np.mean(values) != 0 else 0
        
        # 롤링 표준편차 (변동성의 변화)
        window_size = min(5, len(values) // 2)
        if window_size >= 2:
            rolling_std = []
            for i in range(window_size, len(values) + 1):
                window_std = np.std(values[i-window_size:i])
                rolling_std.append(window_std)
            
            volatility_trend = 'increasing' if len(rolling_std) > 1 and rolling_std[-1] > rolling_std[0] else 'stable'
        else:
            volatility_trend = 'insufficient_data'
        
        # 안정성 평가
        if coefficient_of_variation < 0.1:
            stability = 'very_stable'
        elif coefficient_of_variation < 0.2:
            stability = 'stable'
        elif coefficient_of_variation < 0.3:
            stability = 'moderately_stable'
        else:
            stability = 'unstable'
        
        return {
            'volatility': volatility,
            'coefficient_of_variation': coefficient_of_variation,
            'volatility_trend': volatility_trend,
            'stability': stability
        }
    
    def _compare_with_baseline(self, values: List[float], baseline_stats: Dict) -> Dict:
        """베이스라인과의 비교 분석"""
        current_mean = np.mean(values)
        baseline_mean = baseline_stats['mean']
        baseline_std = baseline_stats['std']
        
        # Z-점수 계산
        z_score = (current_mean - baseline_mean) / baseline_std if baseline_std > 0 else 0
        
        # 편차 정도 분류
        if abs(z_score) < 1:
            deviation_level = 'normal'
        elif abs(z_score) < 2:
            deviation_level = 'mild'
        elif abs(z_score) < 3:
            deviation_level = 'moderate'
        else:
            deviation_level = 'severe'
        
        # 변화 방향
        direction = 'above' if current_mean > baseline_mean else 'below'
        
        return {
            'current_mean': current_mean,
            'baseline_mean': baseline_mean,
            'difference': current_mean - baseline_mean,
            'z_score': z_score,
            'deviation_level': deviation_level,
            'direction': direction
        }
    
    def _analyze_seasonality(self, values: List[float]) -> Dict:
        """계절성 분석 (충분한 데이터가 있는 경우)"""
        try:
            # STL 분해 시도
            decomposition = seasonal_decompose(values, model='additive', period=min(12, len(values)//2))
            
            seasonal_strength = np.var(decomposition.seasonal) / np.var(values) if np.var(values) > 0 else 0
            
            return {
                'seasonal_strength': seasonal_strength,
                'has_seasonality': seasonal_strength > 0.1,
                'seasonal_pattern': 'detected' if seasonal_strength > 0.1 else 'not_detected'
            }
        except Exception as e:
            self.logger.warning(f"계절성 분석 중 오류: {str(e)}")
            return {'seasonal_pattern': 'analysis_failed'}
    
    def _analyze_removed_trends(self, data: List[Dict], timestamps: List[datetime]) -> Dict:
        """제거된 패턴 추세 분석"""
        removed_trends = {}
        
        removed_metrics = ['speechRate', 'pauseRatio']
        for metric in removed_metrics:
            try:
                values = [d.get('voicePatterns', {}).get(metric, 120 if metric == 'speechRate' else 0.3) for d in data]
                
                # Mann-Kendall 검정
                mk_result = self._mann_kendall_test(values)
                
                # Sen's slope
                sens_slope = self._calculate_sens_slope(values)
                
                removed_trends[metric] = {
                    'mann_kendall': mk_result,
                    'sens_slope': sens_slope,
                    'current_value': values[-1] if values else None,
                    'value_range': {'min': min(values), 'max': max(values)} if values else None
                }
                
            except KeyError as e:
                self.logger.warning(f"제거된 패턴 지표 {metric} 분석 중 오류: {str(e)}")
                removed_trends[metric] = {'error': str(e)}
                
        return removed_trends
    
    def _calculate_trend_strength(self, mk_result: Dict, sens_slope: Dict) -> str:
        """추세 강도 계산"""
        if not mk_result['significant']:
            return 'no_trend'
        
        tau = abs(mk_result['tau'])
        slope = abs(sens_slope['slope'])
        
        if tau > 0.5 and slope > 0.1:
            return 'strong'
        elif tau > 0.3 and slope > 0.05:
            return 'moderate'
        else:
            return 'weak'
    
    def _calculate_confidence(self, n_points: int, p_value: float) -> str:
        """분석 신뢰도 계산"""
        if n_points < 5:
            return 'very_low'
        elif n_points < 10:
            return 'low'
        elif n_points < 20:
            return 'medium'
        else:
            if p_value < 0.01:
                return 'very_high'
            elif p_value < 0.05:
                return 'high'
            else:
                return 'medium'
    
    def _interpret_slope(self, slope: float) -> str:
        """기울기 해석"""
        if abs(slope) < 0.01:
            return 'negligible_change'
        elif slope > 0.1:
            return 'strong_increase'
        elif slope > 0.05:
            return 'moderate_increase'
        elif slope > 0:
            return 'mild_increase'
        elif slope < -0.1:
            return 'strong_decrease'
        elif slope < -0.05:
            return 'moderate_decrease'
        else:
            return 'mild_decrease'
    
    def _generate_trend_summary(self, trends: Dict) -> Dict:
        """전체 추세 요약 생성"""
        summary = {
            'primary_concerns': [],
            'overall_trend': 'stable',
            'risk_indicators': [],
            'positive_indicators': []
        }
        
        # 우울증 추세 확인
        if 'depression' in trends:
            dep_trend = trends['depression']['mann_kendall']['trend']
            if dep_trend == 'increasing' and trends['depression']['mann_kendall']['significant']:
                summary['primary_concerns'].append('depression_worsening')
                summary['overall_trend'] = 'concerning'
                summary['risk_indicators'].append({
                    'type': 'depression_increase',
                    'severity': trends['depression']['trend_strength']
                })
        
        # 인지기능 추세 확인
        if 'cognitive' in trends:
            cog_trend = trends['cognitive']['mann_kendall']['trend']
            if cog_trend == 'decreasing' and trends['cognitive']['mann_kendall']['significant']:
                summary['primary_concerns'].append('cognitive_decline')
                if summary['overall_trend'] != 'concerning':
                    summary['overall_trend'] = 'concerning'
                summary['risk_indicators'].append({
                    'type': 'cognitive_decline',
                    'severity': trends['cognitive']['trend_strength']
                })
            elif cog_trend == 'increasing':
                summary['positive_indicators'].append('cognitive_improvement')
        
        return summary
    
    def _insufficient_data_response(self) -> Dict:
        """데이터 부족 시 반환할 응답"""
        return {
            'status': 'insufficient_data',
            'message': '추세 분석을 위해 최소 5개의 데이터 포인트가 필요합니다.',
            'analysis_date': datetime.now().isoformat()
        } 