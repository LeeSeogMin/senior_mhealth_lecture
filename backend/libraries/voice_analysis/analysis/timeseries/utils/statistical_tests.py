import numpy as np
from scipy import stats
from scipy.stats import jarque_bera, shapiro, anderson, kstest, levene, bartlett
from scipy.stats import kruskal, mannwhitneyu, wilcoxon
from statsmodels.stats.diagnostic import acorr_ljungbox
from statsmodels.tsa.stattools import adfuller, kpss
from typing import Dict, List, Tuple, Optional
import warnings
import logging

class StatisticalTests:
    """
    시계열 분석을 위한 통계적 테스트 모음
    
    정규성, 정상성, 자기상관성, 동질성 등 다양한 통계적 특성을 
    검정하는 기능을 제공합니다.
    """
    
    def __init__(self, significance_level: float = 0.05):
        """
        Args:
            significance_level: 통계적 유의성 판단 기준
        """
        self.alpha = significance_level
        self.logger = logging.getLogger(__name__)
    
    def comprehensive_test_suite(self, data: List[float]) -> Dict:
        """
        포괄적인 통계 테스트 수행
        
        Args:
            data: 분석할 시계열 데이터
            
        Returns:
            모든 테스트 결과를 포함한 딕셔너리
        """
        if len(data) < 3:
            return {'error': 'insufficient_data', 'minimum_required': 3}
        
        results = {
            'data_summary': self._calculate_summary_statistics(data),
            'normality_tests': self.test_normality(data),
            'stationarity_tests': self.test_stationarity(data),
            'autocorrelation_tests': self.test_autocorrelation(data),
            'outlier_detection': self.detect_outliers(data),
            'homogeneity_assessment': self._assess_homogeneity(data)
        }
        
        # 종합적인 평가 추가
        results['overall_assessment'] = self._generate_overall_assessment(results)
        
        return results
    
    def test_normality(self, data: List[float]) -> Dict:
        """
        정규성 검정 수행
        
        여러 정규성 테스트를 통해 데이터의 정규분포 적합성을 평가합니다.
        """
        data = np.array(data)
        
        if len(data) < 3:
            return {'error': 'insufficient_data_for_normality_test'}
        
        results = {}
        
        # 1. Shapiro-Wilk 테스트 (n <= 5000에 적합)
        if len(data) <= 5000:
            try:
                sw_stat, sw_p = shapiro(data)
                results['shapiro_wilk'] = {
                    'statistic': sw_stat,
                    'p_value': sw_p,
                    'is_normal': sw_p > self.alpha,
                    'interpretation': 'normal' if sw_p > self.alpha else 'non_normal'
                }
            except Exception as e:
                results['shapiro_wilk'] = {'error': str(e)}
        
        # 2. Jarque-Bera 테스트
        if len(data) >= 7:  # JB 테스트는 최소 7개 샘플 필요
            try:
                jb_stat, jb_p = jarque_bera(data)
                results['jarque_bera'] = {
                    'statistic': jb_stat,
                    'p_value': jb_p,
                    'is_normal': jb_p > self.alpha,
                    'interpretation': 'normal' if jb_p > self.alpha else 'non_normal'
                }
            except Exception as e:
                results['jarque_bera'] = {'error': str(e)}
        
        # 3. Anderson-Darling 테스트
        try:
            ad_result = anderson(data, dist='norm')
            # 5% 유의수준에서의 임계값과 비교
            critical_value_5pct = ad_result.critical_values[2]  # 5% 수준
            results['anderson_darling'] = {
                'statistic': ad_result.statistic,
                'critical_values': ad_result.critical_values,
                'significance_levels': ad_result.significance_level,
                'is_normal': ad_result.statistic < critical_value_5pct,
                'interpretation': 'normal' if ad_result.statistic < critical_value_5pct else 'non_normal'
            }
        except Exception as e:
            results['anderson_darling'] = {'error': str(e)}
        
        # 4. Kolmogorov-Smirnov 테스트 (정규분포와 비교)
        try:
            # 표준화된 데이터로 표준정규분포와 비교
            standardized_data = (data - np.mean(data)) / np.std(data)
            ks_stat, ks_p = kstest(standardized_data, 'norm')
            results['kolmogorov_smirnov'] = {
                'statistic': ks_stat,
                'p_value': ks_p,
                'is_normal': ks_p > self.alpha,
                'interpretation': 'normal' if ks_p > self.alpha else 'non_normal'
            }
        except Exception as e:
            results['kolmogorov_smirnov'] = {'error': str(e)}
        
        # 5. 종합 판단
        normal_count = sum(1 for test in results.values() 
                          if isinstance(test, dict) and test.get('is_normal', False))
        total_tests = sum(1 for test in results.values() 
                         if isinstance(test, dict) and 'is_normal' in test)
        
        if total_tests > 0:
            confidence = normal_count / total_tests
            results['overall_normality'] = {
                'consensus': 'normal' if confidence >= 0.5 else 'non_normal',
                'confidence': confidence,
                'tests_passed': normal_count,
                'total_tests': total_tests
            }
        
        return results
    
    def test_stationarity(self, data: List[float]) -> Dict:
        """
        정상성(stationarity) 검정 수행
        
        ADF와 KPSS 테스트를 통해 시계열의 정상성을 평가합니다.
        """
        data = np.array(data)
        
        if len(data) < 10:
            return {'error': 'insufficient_data_for_stationarity_test', 'minimum_required': 10}
        
        results = {}
        
        # 1. Augmented Dickey-Fuller (ADF) 테스트
        try:
            adf_result = adfuller(data, autolag='AIC')
            results['adf'] = {
                'statistic': adf_result[0],
                'p_value': adf_result[1],
                'critical_values': adf_result[4],
                'used_lag': adf_result[2],
                'n_observations': adf_result[3],
                'is_stationary': adf_result[1] < self.alpha,
                'interpretation': 'stationary' if adf_result[1] < self.alpha else 'non_stationary'
            }
        except Exception as e:
            results['adf'] = {'error': str(e)}
        
        # 2. KPSS 테스트
        try:
            kpss_result = kpss(data, regression='c', nlags='auto')
            results['kpss'] = {
                'statistic': kpss_result[0],
                'p_value': kpss_result[1],
                'critical_values': kpss_result[3],
                'used_lag': kpss_result[2],
                'is_stationary': kpss_result[1] > self.alpha,  # KPSS에서는 p > α이면 정상성
                'interpretation': 'stationary' if kpss_result[1] > self.alpha else 'non_stationary'
            }
        except Exception as e:
            results['kpss'] = {'error': str(e)}
        
        # 3. 종합 판단 (ADF와 KPSS 결과 조합)
        adf_stationary = results.get('adf', {}).get('is_stationary', None)
        kpss_stationary = results.get('kpss', {}).get('is_stationary', None)
        
        if adf_stationary is not None and kpss_stationary is not None:
            if adf_stationary and kpss_stationary:
                consensus = 'stationary'
                confidence = 'high'
            elif not adf_stationary and not kpss_stationary:
                consensus = 'non_stationary'
                confidence = 'high'
            else:
                consensus = 'inconclusive'
                confidence = 'low'
        else:
            consensus = 'insufficient_tests'
            confidence = 'unknown'
        
        results['overall_stationarity'] = {
            'consensus': consensus,
            'confidence': confidence,
            'recommendation': self._get_stationarity_recommendation(consensus)
        }
        
        return results
    
    def test_autocorrelation(self, data: List[float], max_lags: Optional[int] = None) -> Dict:
        """
        자기상관성 검정 수행
        
        Ljung-Box 테스트를 통해 시계열의 자기상관성을 평가합니다.
        """
        data = np.array(data)
        
        if len(data) < 10:
            return {'error': 'insufficient_data_for_autocorrelation_test'}
        
        if max_lags is None:
            max_lags = min(10, len(data) // 4)
        
        results = {}
        
        try:
            # Ljung-Box 테스트
            lb_result = acorr_ljungbox(data, lags=max_lags, return_df=True)
            
            # 각 지연(lag)에 대한 결과
            lag_results = []
            for lag in lb_result.index:
                lag_results.append({
                    'lag': lag,
                    'statistic': lb_result.loc[lag, 'lb_stat'],
                    'p_value': lb_result.loc[lag, 'lb_pvalue'],
                    'has_autocorrelation': lb_result.loc[lag, 'lb_pvalue'] < self.alpha
                })
            
            results['ljung_box'] = {
                'lag_results': lag_results,
                'max_lags_tested': max_lags,
                'significant_lags': [r['lag'] for r in lag_results if r['has_autocorrelation']]
            }
            
            # 전체적인 자기상관성 평가
            significant_count = len(results['ljung_box']['significant_lags'])
            if significant_count == 0:
                overall_assessment = 'no_autocorrelation'
            elif significant_count <= max_lags // 3:
                overall_assessment = 'weak_autocorrelation'
            else:
                overall_assessment = 'strong_autocorrelation'
            
            results['overall_autocorrelation'] = {
                'assessment': overall_assessment,
                'significant_lags_count': significant_count,
                'total_lags_tested': max_lags
            }
            
        except Exception as e:
            results['ljung_box'] = {'error': str(e)}
        
        return results
    
    def detect_outliers(self, data: List[float]) -> Dict:
        """
        이상치 탐지
        
        여러 방법을 사용하여 이상치를 탐지합니다.
        """
        data = np.array(data)
        
        if len(data) < 3:
            return {'error': 'insufficient_data_for_outlier_detection'}
        
        results = {}
        
        # 1. Z-score 방법
        z_scores = np.abs(stats.zscore(data))
        z_threshold = 3.0
        z_outliers = np.where(z_scores > z_threshold)[0].tolist()
        
        results['z_score'] = {
            'threshold': z_threshold,
            'outlier_indices': z_outliers,
            'outlier_values': [data[i] for i in z_outliers],
            'z_scores': z_scores.tolist()
        }
        
        # 2. IQR (Interquartile Range) 방법
        q1, q3 = np.percentile(data, [25, 75])
        iqr = q3 - q1
        iqr_lower = q1 - 1.5 * iqr
        iqr_upper = q3 + 1.5 * iqr
        iqr_outliers = np.where((data < iqr_lower) | (data > iqr_upper))[0].tolist()
        
        results['iqr'] = {
            'q1': q1,
            'q3': q3,
            'iqr': iqr,
            'lower_bound': iqr_lower,
            'upper_bound': iqr_upper,
            'outlier_indices': iqr_outliers,
            'outlier_values': [data[i] for i in iqr_outliers]
        }
        
        # 3. Modified Z-score (Median Absolute Deviation 기반)
        if len(data) > 1:
            median = np.median(data)
            mad = np.median(np.abs(data - median))
            modified_z_scores = 0.6745 * (data - median) / mad if mad > 0 else np.zeros_like(data)
            mad_threshold = 3.5
            mad_outliers = np.where(np.abs(modified_z_scores) > mad_threshold)[0].tolist()
            
            results['modified_z_score'] = {
                'threshold': mad_threshold,
                'outlier_indices': mad_outliers,
                'outlier_values': [data[i] for i in mad_outliers],
                'modified_z_scores': modified_z_scores.tolist()
            }
        
        # 4. 종합 평가
        all_outlier_indices = set()
        if 'z_score' in results:
            all_outlier_indices.update(results['z_score']['outlier_indices'])
        if 'iqr' in results:
            all_outlier_indices.update(results['iqr']['outlier_indices'])
        if 'modified_z_score' in results:
            all_outlier_indices.update(results['modified_z_score']['outlier_indices'])
        
        results['consensus'] = {
            'all_outlier_indices': sorted(list(all_outlier_indices)),
            'outlier_count': len(all_outlier_indices),
            'outlier_percentage': len(all_outlier_indices) / len(data) * 100,
            'assessment': self._assess_outlier_severity(len(all_outlier_indices), len(data))
        }
        
        return results
    
    def compare_distributions(self, group1: List[float], group2: List[float]) -> Dict:
        """
        두 그룹 간 분포 비교
        
        모수적/비모수적 테스트를 통해 두 그룹의 분포를 비교합니다.
        """
        if len(group1) < 3 or len(group2) < 3:
            return {'error': 'insufficient_data_for_comparison'}
        
        results = {}
        
        # 1. t-테스트 (정규성 가정)
        try:
            t_stat, t_p = stats.ttest_ind(group1, group2)
            results['t_test'] = {
                'statistic': t_stat,
                'p_value': t_p,
                'significant_difference': t_p < self.alpha
            }
        except Exception as e:
            results['t_test'] = {'error': str(e)}
        
        # 2. Mann-Whitney U 테스트 (비모수적)
        try:
            u_stat, u_p = mannwhitneyu(group1, group2, alternative='two-sided')
            results['mann_whitney'] = {
                'statistic': u_stat,
                'p_value': u_p,
                'significant_difference': u_p < self.alpha
            }
        except Exception as e:
            results['mann_whitney'] = {'error': str(e)}
        
        # 3. 분산 동질성 테스트 (Levene's test)
        try:
            levene_stat, levene_p = levene(group1, group2)
            results['levene_variance'] = {
                'statistic': levene_stat,
                'p_value': levene_p,
                'equal_variances': levene_p > self.alpha
            }
        except Exception as e:
            results['levene_variance'] = {'error': str(e)}
        
        return results
    
    def _calculate_summary_statistics(self, data: List[float]) -> Dict:
        """기본 통계량 계산"""
        data = np.array(data)
        
        return {
            'n': len(data),
            'mean': np.mean(data),
            'median': np.median(data),
            'std': np.std(data, ddof=1),
            'var': np.var(data, ddof=1),
            'min': np.min(data),
            'max': np.max(data),
            'skewness': stats.skew(data),
            'kurtosis': stats.kurtosis(data),
            'range': np.max(data) - np.min(data),
            'cv': np.std(data, ddof=1) / np.mean(data) if np.mean(data) != 0 else 0
        }
    
    def _assess_homogeneity(self, data: List[float]) -> Dict:
        """데이터 동질성 평가"""
        if len(data) < 6:
            return {'assessment': 'insufficient_data'}
        
        # 데이터를 전반부와 후반부로 나누어 비교
        mid_point = len(data) // 2
        first_half = data[:mid_point]
        second_half = data[mid_point:]
        
        comparison = self.compare_distributions(first_half, second_half)
        
        # 변동성의 변화 확인
        first_half_std = np.std(first_half)
        second_half_std = np.std(second_half)
        variance_ratio = second_half_std / first_half_std if first_half_std > 0 else 1
        
        return {
            'temporal_comparison': comparison,
            'variance_ratio': variance_ratio,
            'variance_change': 'increased' if variance_ratio > 1.2 else 'decreased' if variance_ratio < 0.8 else 'stable',
            'assessment': 'homogeneous' if not comparison.get('mann_whitney', {}).get('significant_difference', True) else 'heterogeneous'
        }
    
    def _generate_overall_assessment(self, results: Dict) -> Dict:
        """종합적인 데이터 품질 평가"""
        assessment = {
            'data_quality': 'good',
            'issues': [],
            'recommendations': []
        }
        
        # 정규성 확인
        normality = results.get('normality_tests', {}).get('overall_normality', {})
        if normality.get('consensus') == 'non_normal':
            assessment['issues'].append('non_normal_distribution')
            assessment['recommendations'].append('Consider non-parametric methods')
        
        # 정상성 확인
        stationarity = results.get('stationarity_tests', {}).get('overall_stationarity', {})
        if stationarity.get('consensus') == 'non_stationary':
            assessment['issues'].append('non_stationary_series')
            assessment['recommendations'].append('Consider differencing or detrending')
        
        # 자기상관성 확인
        autocorr = results.get('autocorrelation_tests', {}).get('overall_autocorrelation', {})
        if autocorr.get('assessment') in ['strong_autocorrelation']:
            assessment['issues'].append('strong_autocorrelation')
            assessment['recommendations'].append('Account for temporal dependencies')
        
        # 이상치 확인
        outliers = results.get('outlier_detection', {}).get('consensus', {})
        if outliers.get('assessment') in ['high', 'severe']:
            assessment['issues'].append('significant_outliers')
            assessment['recommendations'].append('Consider outlier treatment')
        
        # 전체 품질 평가
        if len(assessment['issues']) == 0:
            assessment['data_quality'] = 'excellent'
        elif len(assessment['issues']) <= 2:
            assessment['data_quality'] = 'good'
        elif len(assessment['issues']) <= 3:
            assessment['data_quality'] = 'fair'
        else:
            assessment['data_quality'] = 'poor'
        
        return assessment
    
    def _get_stationarity_recommendation(self, consensus: str) -> str:
        """정상성 검정 결과에 따른 권고사항"""
        recommendations = {
            'stationary': 'Data appears stationary. Proceed with analysis.',
            'non_stationary': 'Consider differencing, detrending, or log transformation.',
            'inconclusive': 'Results are mixed. Visual inspection recommended.',
            'insufficient_tests': 'Unable to determine stationarity. More data needed.'
        }
        return recommendations.get(consensus, 'Unknown status')
    
    def _assess_outlier_severity(self, outlier_count: int, total_count: int) -> str:
        """이상치 심각도 평가"""
        percentage = outlier_count / total_count * 100
        
        if percentage == 0:
            return 'none'
        elif percentage < 5:
            return 'low'
        elif percentage < 10:
            return 'moderate'
        elif percentage < 20:
            return 'high'
        else:
            return 'severe' 