import numpy as np
import pandas as pd
from scipy import stats, signal
from scipy.interpolate import interp1d
from sklearn.preprocessing import StandardScaler, MinMaxScaler, RobustScaler
from typing import Dict, List, Tuple, Optional, Union
import logging
from datetime import datetime, timedelta
import warnings

class DataPreprocessor:
    """
    시계열 데이터 전처리 클래스
    
    결측치 처리, 이상치 제거, 정규화, 스무딩, 변환 등
    시계열 분석을 위한 다양한 전처리 기능을 제공합니다.
    """
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.scaler = None
        self.preprocessing_history = []
    
    def preprocess_pipeline(self, data: List[Dict], 
                          options: Dict = None) -> Tuple[List[Dict], Dict]:
        """
        전처리 파이프라인 실행
        
        Args:
            data: 원본 시계열 데이터
            options: 전처리 옵션 딕셔너리
                - handle_missing: 결측치 처리 방법
                - outlier_treatment: 이상치 처리 방법
                - normalization: 정규화 방법
                - smoothing: 스무딩 적용 여부
                - detrend: 추세 제거 여부
                
        Returns:
            전처리된 데이터와 변환 정보
        """
        if not data:
            return [], {'error': 'empty_data'}
        
        # 기본 옵션 설정
        default_options = {
            'handle_missing': 'interpolate',
            'outlier_treatment': 'winsorize',
            'normalization': None,
            'smoothing': False,
            'detrend': False,
            'difference': False
        }
        
        if options:
            default_options.update(options)
        
        processed_data = data.copy()
        transformation_info = {
            'original_length': len(data),
            'steps_applied': [],
            'statistics': {}
        }
        
        # 1. 데이터 검증 및 기본 통계
        validation_result = self._validate_data(processed_data)
        transformation_info['validation'] = validation_result
        
        if not validation_result['is_valid']:
            return processed_data, transformation_info
        
        # 2. 결측치 처리
        if default_options['handle_missing']:
            processed_data, missing_info = self._handle_missing_values(
                processed_data, method=default_options['handle_missing']
            )
            transformation_info['steps_applied'].append('missing_values_handled')
            transformation_info['missing_treatment'] = missing_info
        
        # 3. 이상치 처리
        if default_options['outlier_treatment']:
            processed_data, outlier_info = self._handle_outliers(
                processed_data, method=default_options['outlier_treatment']
            )
            transformation_info['steps_applied'].append('outliers_handled')
            transformation_info['outlier_treatment'] = outlier_info
        
        # 4. 스무딩
        if default_options['smoothing']:
            processed_data, smoothing_info = self._apply_smoothing(processed_data)
            transformation_info['steps_applied'].append('smoothing_applied')
            transformation_info['smoothing'] = smoothing_info
        
        # 5. 추세 제거
        if default_options['detrend']:
            processed_data, detrend_info = self._detrend_data(processed_data)
            transformation_info['steps_applied'].append('detrending_applied')
            transformation_info['detrending'] = detrend_info
        
        # 6. 차분
        if default_options['difference']:
            processed_data, diff_info = self._apply_differencing(processed_data)
            transformation_info['steps_applied'].append('differencing_applied')
            transformation_info['differencing'] = diff_info
        
        # 7. 정규화
        if default_options['normalization']:
            processed_data, norm_info = self._normalize_data(
                processed_data, method=default_options['normalization']
            )
            transformation_info['steps_applied'].append('normalization_applied')
            transformation_info['normalization'] = norm_info
        
        # 최종 통계
        transformation_info['final_length'] = len(processed_data)
        transformation_info['final_statistics'] = self._calculate_statistics(processed_data)
        
        return processed_data, transformation_info
    
    def _validate_data(self, data: List[Dict]) -> Dict:
        """데이터 유효성 검증"""
        if not data:
            return {'is_valid': False, 'reason': 'empty_data'}
        
        required_fields = ['analysis_timestamp', 'mentalHealthAnalysis']
        missing_fields = []
        
        for item in data[:5]:  # 처음 5개 샘플만 검사
            for field in required_fields:
                if field not in item:
                    missing_fields.append(field)
        
        if missing_fields:
            return {
                'is_valid': False, 
                'reason': 'missing_required_fields',
                'missing_fields': list(set(missing_fields))
            }
        
        # 시간순 정렬 확인
        timestamps = []
        for item in data:
            try:
                ts = datetime.fromisoformat(item['analysis_timestamp'].replace('Z', '+00:00'))
                timestamps.append(ts)
            except:
                return {'is_valid': False, 'reason': 'invalid_timestamp_format'}
        
        is_sorted = all(timestamps[i] <= timestamps[i+1] for i in range(len(timestamps)-1))
        
        return {
            'is_valid': True,
            'time_span_days': (timestamps[-1] - timestamps[0]).days if len(timestamps) > 1 else 0,
            'is_time_sorted': is_sorted,
            'data_points': len(data)
        }
    
    def _handle_missing_values(self, data: List[Dict], method: str = 'interpolate') -> Tuple[List[Dict], Dict]:
        """결측치 처리"""
        missing_info = {
            'method': method,
            'missing_points': [],
            'interpolated_points': []
        }
        
        # 시계열 데이터를 DataFrame으로 변환
        df = self._convert_to_dataframe(data)
        
        # 결측치 식별
        missing_mask = df.isnull().any(axis=1)
        missing_indices = df[missing_mask].index.tolist()
        missing_info['missing_points'] = missing_indices
        
        if not missing_indices:
            return data, missing_info
        
        if method == 'interpolate':
            # 선형 보간
            df_interpolated = df.interpolate(method='linear', limit_direction='both')
            missing_info['interpolated_points'] = missing_indices
            
        elif method == 'forward_fill':
            # 전방향 채우기
            df_interpolated = df.fillna(method='ffill')
            
        elif method == 'backward_fill':
            # 후방향 채우기
            df_interpolated = df.fillna(method='bfill')
            
        elif method == 'mean':
            # 평균값으로 채우기
            df_interpolated = df.fillna(df.mean())
            
        elif method == 'median':
            # 중앙값으로 채우기
            df_interpolated = df.fillna(df.median())
            
        elif method == 'drop':
            # 결측치가 있는 행 삭제
            df_interpolated = df.dropna()
            missing_info['dropped_indices'] = missing_indices
            
        else:
            self.logger.warning(f"Unknown missing value method: {method}")
            return data, missing_info
        
        # DataFrame을 다시 딕셔너리 리스트로 변환
        processed_data = self._convert_from_dataframe(df_interpolated, data)
        
        return processed_data, missing_info
    
    def _handle_outliers(self, data: List[Dict], method: str = 'winsorize') -> Tuple[List[Dict], Dict]:
        """이상치 처리"""
        outlier_info = {
            'method': method,
            'outliers_detected': {},
            'outliers_treated': {}
        }
        
        processed_data = data.copy()
        metrics = ['depression', 'cognitive']
        
        for metric in metrics:
            values = [d['mentalHealthAnalysis'][metric]['score'] for d in processed_data]
            
            # 이상치 탐지
            outlier_indices = self._detect_outliers_iqr(values)
            outlier_info['outliers_detected'][metric] = outlier_indices
            
            if not outlier_indices:
                continue
            
            if method == 'winsorize':
                # Winsorization (극값을 특정 백분위수로 대체)
                treated_values = self._winsorize_values(values, limits=(0.05, 0.05))
                
            elif method == 'clip':
                # IQR 기반 클리핑
                q1, q3 = np.percentile(values, [25, 75])
                iqr = q3 - q1
                lower_bound = q1 - 1.5 * iqr
                upper_bound = q3 + 1.5 * iqr
                treated_values = np.clip(values, lower_bound, upper_bound)
                
            elif method == 'remove':
                # 이상치 제거 (해당 데이터포인트 전체 제거)
                mask = np.ones(len(values), dtype=bool)
                mask[outlier_indices] = False
                processed_data = [processed_data[i] for i in range(len(processed_data)) if mask[i]]
                outlier_info['outliers_treated'][metric] = 'removed'
                continue
                
            elif method == 'interpolate':
                # 이상치를 보간으로 대체
                treated_values = values.copy()
                for idx in outlier_indices:
                    if idx > 0 and idx < len(values) - 1:
                        treated_values[idx] = (treated_values[idx-1] + treated_values[idx+1]) / 2
                    elif idx == 0:
                        treated_values[idx] = treated_values[1]
                    else:
                        treated_values[idx] = treated_values[-2]
                        
            else:
                self.logger.warning(f"Unknown outlier method: {method}")
                continue
            
            # 처리된 값을 다시 데이터에 적용
            if method != 'remove':
                for i, new_value in enumerate(treated_values):
                    processed_data[i]['mentalHealthAnalysis'][metric]['score'] = float(new_value)
                
                outlier_info['outliers_treated'][metric] = len(outlier_indices)
        
        return processed_data, outlier_info
    
    def _apply_smoothing(self, data: List[Dict], method: str = 'moving_average', 
                        window: int = 3) -> Tuple[List[Dict], Dict]:
        """스무딩 적용"""
        smoothing_info = {
            'method': method,
            'window_size': window,
            'smoothed_metrics': []
        }
        
        processed_data = data.copy()
        metrics = ['depression', 'cognitive']
        
        for metric in metrics:
            values = [d['mentalHealthAnalysis'][metric]['score'] for d in processed_data]
            
            if method == 'moving_average':
                smoothed_values = self._moving_average(values, window)
            elif method == 'exponential':
                smoothed_values = self._exponential_smoothing(values, alpha=0.3)
            elif method == 'savgol':
                if len(values) >= window and window >= 3:
                    smoothed_values = signal.savgol_filter(values, window, 2)
                else:
                    smoothed_values = values
            else:
                self.logger.warning(f"Unknown smoothing method: {method}")
                continue
            
            # 스무딩된 값을 데이터에 적용
            for i, smoothed_value in enumerate(smoothed_values):
                processed_data[i]['mentalHealthAnalysis'][metric]['score'] = float(smoothed_value)
            
            smoothing_info['smoothed_metrics'].append(metric)
        
        return processed_data, smoothing_info
    
    def _detrend_data(self, data: List[Dict]) -> Tuple[List[Dict], Dict]:
        """추세 제거"""
        detrend_info = {
            'method': 'linear_detrend',
            'detrended_metrics': []
        }
        
        processed_data = data.copy()
        metrics = ['depression', 'cognitive']
        
        for metric in metrics:
            values = np.array([d['mentalHealthAnalysis'][metric]['score'] for d in processed_data])
            
            # 선형 추세 제거
            detrended_values = signal.detrend(values, type='linear')
            
            # 원래 평균 복원 (추세만 제거하고 수준은 유지)
            detrended_values += np.mean(values)
            
            # 처리된 값을 데이터에 적용
            for i, detrended_value in enumerate(detrended_values):
                processed_data[i]['mentalHealthAnalysis'][metric]['score'] = float(detrended_value)
            
            detrend_info['detrended_metrics'].append(metric)
        
        return processed_data, detrend_info
    
    def _apply_differencing(self, data: List[Dict], order: int = 1) -> Tuple[List[Dict], Dict]:
        """차분 적용"""
        diff_info = {
            'order': order,
            'differenced_metrics': [],
            'lost_observations': order
        }
        
        if len(data) <= order:
            return data, {'error': 'insufficient_data_for_differencing'}
        
        processed_data = data[order:].copy()  # 차분으로 인해 관측치 손실
        metrics = ['depression', 'cognitive']
        
        for metric in metrics:
            values = [d['mentalHealthAnalysis'][metric]['score'] for d in data]
            
            # 차분 계산
            diff_values = np.diff(values, n=order)
            
            # 차분된 값을 데이터에 적용
            for i, diff_value in enumerate(diff_values):
                processed_data[i]['mentalHealthAnalysis'][metric]['score'] = float(diff_value)
            
            diff_info['differenced_metrics'].append(metric)
        
        return processed_data, diff_info
    
    def _normalize_data(self, data: List[Dict], method: str = 'standardize') -> Tuple[List[Dict], Dict]:
        """데이터 정규화"""
        norm_info = {
            'method': method,
            'normalized_metrics': [],
            'scalers': {}
        }
        
        processed_data = data.copy()
        metrics = ['depression', 'cognitive']
        
        for metric in metrics:
            values = np.array([d['mentalHealthAnalysis'][metric]['score'] for d in processed_data]).reshape(-1, 1)
            
            if method == 'standardize':
                scaler = StandardScaler()
            elif method == 'minmax':
                scaler = MinMaxScaler()
            elif method == 'robust':
                scaler = RobustScaler()
            else:
                self.logger.warning(f"Unknown normalization method: {method}")
                continue
            
            # 정규화 적용
            normalized_values = scaler.fit_transform(values).flatten()
            
            # 정규화된 값을 데이터에 적용
            for i, norm_value in enumerate(normalized_values):
                processed_data[i]['mentalHealthAnalysis'][metric]['score'] = float(norm_value)
            
            norm_info['normalized_metrics'].append(metric)
            norm_info['scalers'][metric] = {
                'mean': getattr(scaler, 'mean_', [None])[0],
                'scale': getattr(scaler, 'scale_', [None])[0],
                'min': getattr(scaler, 'data_min_', [None])[0],
                'max': getattr(scaler, 'data_max_', [None])[0]
            }
        
        return processed_data, norm_info
    
    # 보조 메서드들
    def _convert_to_dataframe(self, data: List[Dict]) -> pd.DataFrame:
        """딕셔너리 리스트를 DataFrame으로 변환"""
        records = []
        for item in data:
            record = {
                'timestamp': item['analysis_timestamp'],
                'depression': item['mentalHealthAnalysis']['depression']['score'],
                'cognitive': item['mentalHealthAnalysis']['cognitive']['score']
            }
            # 제거됨 - SincNet만 사용
            record['speechRate'] = 0
            record['pauseRatio'] = 0
            records.append(record)
        
        return pd.DataFrame(records)
    
    def _convert_from_dataframe(self, df: pd.DataFrame, original_data: List[Dict]) -> List[Dict]:
        """DataFrame을 딕셔너리 리스트로 변환"""
        result = []
        for i, row in df.iterrows():
            if i >= len(original_data):
                break
                
            item = original_data[i].copy()
            item['mentalHealthAnalysis']['depression']['score'] = float(row['depression'])
            item['mentalHealthAnalysis']['cognitive']['score'] = float(row['cognitive'])
            
            # 제거됨 - SincNet만 사용
            
            result.append(item)
        
        return result
    
    def _detect_outliers_iqr(self, values: List[float]) -> List[int]:
        """IQR 방법으로 이상치 탐지"""
        q1, q3 = np.percentile(values, [25, 75])
        iqr = q3 - q1
        lower_bound = q1 - 1.5 * iqr
        upper_bound = q3 + 1.5 * iqr
        
        outliers = []
        for i, value in enumerate(values):
            if value < lower_bound or value > upper_bound:
                outliers.append(i)
        
        return outliers
    
    def _winsorize_values(self, values: List[float], limits: Tuple[float, float]) -> np.ndarray:
        """Winsorization 적용"""
        from scipy.stats import mstats
        return mstats.winsorize(values, limits=limits)
    
    def _moving_average(self, values: List[float], window: int) -> np.ndarray:
        """이동 평균 계산"""
        if window <= 1:
            return np.array(values)
        
        smoothed = []
        for i in range(len(values)):
            start_idx = max(0, i - window // 2)
            end_idx = min(len(values), i + window // 2 + 1)
            smoothed.append(np.mean(values[start_idx:end_idx]))
        
        return np.array(smoothed)
    
    def _exponential_smoothing(self, values: List[float], alpha: float = 0.3) -> np.ndarray:
        """지수 평활법 적용"""
        result = [values[0]]
        for i in range(1, len(values)):
            result.append(alpha * values[i] + (1 - alpha) * result[-1])
        return np.array(result)
    
    def _calculate_statistics(self, data: List[Dict]) -> Dict:
        """기본 통계량 계산"""
        if not data:
            return {}
        
        stats = {}
        metrics = ['depression', 'cognitive']
        
        for metric in metrics:
            values = [d['mentalHealthAnalysis'][metric]['score'] for d in data]
            stats[metric] = {
                'mean': np.mean(values),
                'std': np.std(values),
                'min': np.min(values),
                'max': np.max(values),
                'median': np.median(values)
            }
        
        return stats
    
    def reverse_normalization(self, data: List[Dict], norm_info: Dict) -> List[Dict]:
        """정규화 역변환"""
        if 'scalers' not in norm_info:
            return data
        
        result = data.copy()
        
        for metric in norm_info['normalized_metrics']:
            scaler_info = norm_info['scalers'][metric]
            values = [d['mentalHealthAnalysis'][metric]['score'] for d in result]
            
            # 역변환
            if norm_info['method'] == 'standardize':
                original_values = [v * scaler_info['scale'] + scaler_info['mean'] for v in values]
            elif norm_info['method'] == 'minmax':
                original_values = [v * (scaler_info['max'] - scaler_info['min']) + scaler_info['min'] for v in values]
            else:
                original_values = values  # 다른 방법들은 복잡한 역변환 필요
            
            # 역변환된 값을 적용
            for i, orig_value in enumerate(original_values):
                result[i]['mentalHealthAnalysis'][metric]['score'] = float(orig_value)
        
        return result 