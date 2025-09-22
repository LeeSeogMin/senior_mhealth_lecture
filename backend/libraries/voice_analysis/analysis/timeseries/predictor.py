"""
예측 모델 모듈
시계열 데이터 기반 미래 값 예측
"""

import numpy as np
import pandas as pd
from sklearn.linear_model import LinearRegression
from sklearn.preprocessing import StandardScaler
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime, timedelta
import logging

logger = logging.getLogger(__name__)

class MentalHealthPredictor:
    """정신건강 지표 예측기"""
    
    def __init__(self):
        self.models = {}
        self.scalers = {}
        self.min_training_points = 5
        
    def predict(
        self,
        historical_data: List[Dict],
        prediction_horizon: int = 7,
        indicator: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        미래 값 예측
        
        Args:
            historical_data: 과거 데이터
            prediction_horizon: 예측 기간 (일)
            indicator: 특정 지표만 예측 (None이면 전체)
            
        Returns:
            예측 결과
        """
        
        if len(historical_data) < self.min_training_points:
            return {
                'status': 'insufficient_data',
                'message': f'최소 {self.min_training_points}개의 데이터 필요'
            }
        
        # 데이터 준비
        df = self._prepare_data(historical_data)
        
        # 예측할 지표 선택
        indicators = [indicator] if indicator else ['DRI', 'SDI', 'CFL', 'ES', 'OV']
        
        predictions = {}
        for ind in indicators:
            if ind in df.columns:
                pred_result = self._predict_indicator(
                    df[ind],
                    prediction_horizon,
                    ind
                )
                predictions[ind] = pred_result
        
        # 종합 위험도 예측
        risk_prediction = self._predict_risk_trajectory(predictions)
        
        return {
            'status': 'success',
            'prediction_horizon': prediction_horizon,
            'predictions': predictions,
            'risk_trajectory': risk_prediction,
            'confidence_metrics': self._calculate_confidence(df, predictions),
            'recommendations': self._generate_predictive_recommendations(predictions, risk_prediction)
        }
    
    def _prepare_data(self, historical_data: List[Dict]) -> pd.DataFrame:
        """데이터 준비"""
        
        data = []
        for record in historical_data:
            row = {
                'timestamp': pd.to_datetime(record['timestamp'])
            }
            if 'indicators' in record:
                row.update(record['indicators'])
            data.append(row)
        
        df = pd.DataFrame(data)
        df.set_index('timestamp', inplace=True)
        df.sort_index(inplace=True)
        
        # 결측값 처리
        df.fillna(method='ffill', inplace=True)
        df.fillna(0.5, inplace=True)
        
        return df
    
    def _predict_indicator(
        self,
        series: pd.Series,
        horizon: int,
        indicator_name: str
    ) -> Dict[str, Any]:
        """개별 지표 예측"""
        
        # 특징 생성
        X, y = self._create_features(series)
        
        if len(X) < 3:
            return {
                'status': 'insufficient_data',
                'current_value': float(series.iloc[-1])
            }
        
        # 모델 학습
        model = LinearRegression()
        scaler = StandardScaler()
        
        X_scaled = scaler.fit_transform(X)
        model.fit(X_scaled, y)
        
        # 예측
        predictions = []
        last_values = series.iloc[-3:].values
        
        for i in range(horizon):
            # 다음 값 예측을 위한 특징
            next_features = self._extract_features(last_values)
            next_features_scaled = scaler.transform([next_features])
            
            # 예측
            next_value = model.predict(next_features_scaled)[0]
            
            # 범위 제한 (0-1)
            next_value = np.clip(next_value, 0, 1)
            
            predictions.append(float(next_value))
            
            # 슬라이딩 윈도우 업데이트
            last_values = np.append(last_values[1:], next_value)
        
        # 신뢰 구간 계산
        confidence_interval = self._calculate_confidence_interval(
            series, predictions
        )
        
        # 추세 분석
        trend = self._analyze_prediction_trend(predictions)
        
        return {
            'status': 'success',
            'current_value': float(series.iloc[-1]),
            'predictions': predictions,
            'confidence_interval': confidence_interval,
            'trend': trend,
            'model_score': float(model.score(X_scaled, y))
        }
    
    def _create_features(self, series: pd.Series) -> Tuple[np.ndarray, np.ndarray]:
        """특징 생성"""
        
        features = []
        targets = []
        
        # 슬라이딩 윈도우 (3일)
        window_size = 3
        
        for i in range(window_size, len(series)):
            window = series.iloc[i-window_size:i].values
            feature_vector = self._extract_features(window)
            
            features.append(feature_vector)
            targets.append(series.iloc[i])
        
        return np.array(features), np.array(targets)
    
    def _extract_features(self, window: np.ndarray) -> np.ndarray:
        """윈도우에서 특징 추출"""
        
        features = [
            np.mean(window),           # 평균
            np.std(window),            # 표준편차
            window[-1],                # 마지막 값
            window[-1] - window[0],    # 변화량
            np.max(window),            # 최대값
            np.min(window)             # 최소값
        ]
        
        # 추세 (선형 회귀 기울기)
        if len(window) > 1:
            x = np.arange(len(window))
            slope = np.polyfit(x, window, 1)[0]
            features.append(slope)
        else:
            features.append(0)
        
        return np.array(features)
    
    def _calculate_confidence_interval(
        self,
        series: pd.Series,
        predictions: List[float]
    ) -> Dict[str, List[float]]:
        """신뢰 구간 계산"""
        
        # 과거 데이터의 표준편차
        std = series.std()
        
        # 예측이 멀어질수록 불확실성 증가
        upper_bound = []
        lower_bound = []
        
        for i, pred in enumerate(predictions):
            # 시간에 따른 불확실성 증가
            uncertainty = std * np.sqrt(1 + i * 0.1)
            
            upper = min(1.0, pred + uncertainty)
            lower = max(0.0, pred - uncertainty)
            
            upper_bound.append(float(upper))
            lower_bound.append(float(lower))
        
        return {
            'upper': upper_bound,
            'lower': lower_bound
        }
    
    def _analyze_prediction_trend(self, predictions: List[float]) -> Dict[str, Any]:
        """예측 추세 분석"""
        
        if len(predictions) < 2:
            return {'direction': 'unknown'}
        
        # 전체 추세
        first = predictions[0]
        last = predictions[-1]
        
        change = last - first
        change_rate = change / max(abs(first), 0.01)
        
        if change > 0.05:
            direction = 'improving'
        elif change < -0.05:
            direction = 'declining'
        else:
            direction = 'stable'
        
        # 변동성
        volatility = np.std(predictions) if len(predictions) > 1 else 0
        
        return {
            'direction': direction,
            'total_change': float(change),
            'change_rate': float(change_rate),
            'volatility': float(volatility),
            'final_value': float(last)
        }
    
    def _predict_risk_trajectory(self, predictions: Dict) -> Dict[str, Any]:
        """위험도 궤적 예측"""
        
        if not predictions:
            return {'status': 'no_predictions'}
        
        # 각 시점의 위험도 계산
        risk_trajectory = []
        
        # 예측 기간 길이
        horizon = len(next(iter(predictions.values()))['predictions'])
        
        for i in range(horizon):
            # 각 지표의 예측값
            point_values = {}
            for ind, pred_data in predictions.items():
                if pred_data['status'] == 'success':
                    point_values[ind] = pred_data['predictions'][i]
            
            # 위험도 계산
            risk_score = self._calculate_risk_score(point_values)
            risk_trajectory.append(risk_score)
        
        # 위험도 변화 분석
        if risk_trajectory:
            initial_risk = risk_trajectory[0]
            final_risk = risk_trajectory[-1]
            
            risk_trend = 'increasing' if final_risk > initial_risk else 'decreasing'
            
            # 위험 임계값 초과 시점
            high_risk_threshold = 0.7
            critical_points = [
                i for i, risk in enumerate(risk_trajectory) 
                if risk > high_risk_threshold
            ]
            
            return {
                'trajectory': risk_trajectory,
                'trend': risk_trend,
                'initial_risk': float(initial_risk),
                'final_risk': float(final_risk),
                'critical_points': critical_points,
                'max_risk': float(max(risk_trajectory)),
                'average_risk': float(np.mean(risk_trajectory))
            }
        
        return {'status': 'calculation_failed'}
    
    def _calculate_risk_score(self, indicators: Dict) -> float:
        """위험도 점수 계산"""
        
        if not indicators:
            return 0.5
        
        # 가중치
        weights = {
            'DRI': 0.25,  # 우울
            'SDI': 0.20,  # 수면
            'CFL': 0.25,  # 인지
            'ES': 0.15,   # 정서
            'OV': 0.15    # 활력
        }
        
        risk_score = 0
        total_weight = 0
        
        for ind, value in indicators.items():
            if ind in weights:
                # 낮은 값일수록 위험도 높음
                risk = 1 - value
                risk_score += risk * weights[ind]
                total_weight += weights[ind]
        
        if total_weight > 0:
            risk_score = risk_score / total_weight
        
        return float(risk_score)
    
    def _calculate_confidence(self, df: pd.DataFrame, predictions: Dict) -> Dict[str, float]:
        """예측 신뢰도 계산"""
        
        confidence_scores = []
        
        for ind, pred_data in predictions.items():
            if pred_data.get('status') == 'success':
                # 모델 점수
                model_score = pred_data.get('model_score', 0)
                
                # 데이터 품질 (결측값 비율)
                if ind in df.columns:
                    data_quality = 1 - (df[ind].isna().sum() / len(df))
                else:
                    data_quality = 0
                
                # 데이터 충분성
                data_sufficiency = min(len(df) / 30, 1.0)  # 30일 기준
                
                # 종합 신뢰도
                confidence = (model_score * 0.5 + data_quality * 0.3 + data_sufficiency * 0.2)
                confidence_scores.append(confidence)
        
        if confidence_scores:
            return {
                'overall': float(np.mean(confidence_scores)),
                'min': float(np.min(confidence_scores)),
                'max': float(np.max(confidence_scores))
            }
        
        return {'overall': 0.0, 'min': 0.0, 'max': 0.0}
    
    def _generate_predictive_recommendations(
        self,
        predictions: Dict,
        risk_trajectory: Dict
    ) -> List[str]:
        """예측 기반 권고사항"""
        
        recommendations = []
        
        # 위험도 추세 기반
        if risk_trajectory.get('trend') == 'increasing':
            recommendations.append("위험도 상승 예상 - 예방적 개입 필요")
        
        if risk_trajectory.get('max_risk', 0) > 0.8:
            recommendations.append("높은 위험도 예측 - 전문가 상담 예약 권장")
        
        # 개별 지표 예측 기반
        for ind, pred_data in predictions.items():
            if pred_data.get('status') == 'success':
                trend = pred_data.get('trend', {})
                
                if trend.get('direction') == 'declining':
                    if ind == 'DRI':
                        recommendations.append("우울 위험 증가 예상 - 정신건강 프로그램 참여")
                    elif ind == 'CFL':
                        recommendations.append("인지 기능 저하 예상 - 인지 훈련 시작")
                    elif ind == 'SDI':
                        recommendations.append("수면 문제 악화 예상 - 수면 관리 강화")
        
        # 중복 제거
        recommendations = list(set(recommendations))
        
        return recommendations[:5]  # 상위 5개만