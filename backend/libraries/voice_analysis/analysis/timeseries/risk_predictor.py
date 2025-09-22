import numpy as np
from datetime import datetime
from typing import Dict, List
import logging

class RiskPredictor:
    """위험도 예측 시스템"""
    def __init__(self):
        self.logger = logging.getLogger(__name__)

    def predict_risk(self, historical_data: List[Dict], prediction_horizon: int = 7) -> Dict:
        """위험도 예측 수행"""
        if len(historical_data) < 5:
            return self._default_prediction("insufficient_data")
        features = self._extract_features(historical_data)
        statistical_prediction = self._statistical_prediction(historical_data, prediction_horizon)
        risk_assessment = self._assess_risk_level(statistical_prediction)
        return {
            'prediction_date': datetime.now().isoformat(),
            'prediction_horizon_days': prediction_horizon,
            'predictions': statistical_prediction,
            'risk_assessment': risk_assessment,
            'confidence_scores': self._calculate_confidence_scores(historical_data),
            'warning_indicators': self._identify_warning_indicators(historical_data),
            'method': 'statistical_analysis'
        }

    def _extract_features(self, data: List[Dict]) -> np.ndarray:
        features = []
        for item in data:
            # SincNet만 사용 - 기본값 설정
            depression_score = item.get('mentalHealthAnalysis', {}).get('depression', {}).get('score', 5.0)
            cognitive_score = item.get('mentalHealthAnalysis', {}).get('cognitive', {}).get('score', 5.0)
            
            # None 값 처리
            if depression_score is None:
                depression_score = 5.0
            if cognitive_score is None:
                cognitive_score = 5.0
            
            feature_vector = [
                depression_score,
                cognitive_score,
                120,  # 기본 speech_rate
                0.3,  # 기본 pause_ratio
                0,    # 기본 response_time
                0,    # 기본 voice_stability
                0     # 기본 participation
            ]
            features.append(feature_vector)
        return np.array(features)

    def _statistical_prediction(self, data: List[Dict], horizon: int) -> Dict:
        weights = np.exp(np.linspace(-1, 0, len(data)))
        weights = weights / np.sum(weights)
        depression_scores = [
            d.get('mentalHealthAnalysis', {}).get('depression', {}).get('score', 5.0) 
            if d.get('mentalHealthAnalysis', {}).get('depression', {}).get('score') is not None
            else 5.0
            for d in data
        ]
        cognitive_scores = [
            d.get('mentalHealthAnalysis', {}).get('cognitive', {}).get('score', 5.0)
            if d.get('mentalHealthAnalysis', {}).get('cognitive', {}).get('score') is not None
            else 5.0
            for d in data
        ]
        depression_trend = self._calculate_trend(depression_scores)
        cognitive_trend = self._calculate_trend(cognitive_scores)
        current_depression = np.average(depression_scores[-3:])
        current_cognitive = np.average(cognitive_scores[-3:])
        predicted_depression = current_depression + (depression_trend * horizon / 7)
        predicted_cognitive = current_cognitive + (cognitive_trend * horizon / 7)
        predicted_depression = np.clip(predicted_depression, 0, 10)
        predicted_cognitive = np.clip(predicted_cognitive, 0, 10)
        return {
            'depression': {
                'current': current_depression,
                'predicted': predicted_depression,
                'trend': depression_trend,
                'confidence': self._calculate_trend_confidence(depression_scores)
            },
            'cognitive': {
                'current': current_cognitive,
                'predicted': predicted_cognitive,
                'trend': cognitive_trend,
                'confidence': self._calculate_trend_confidence(cognitive_scores)
            }
        }

    def _calculate_trend(self, values: List[float]) -> float:
        if len(values) < 3:
            return 0.0
        x = np.arange(len(values))
        slope = np.polyfit(x, values, 1)[0]
        return slope

    def _calculate_trend_confidence(self, values: List[float]) -> float:
        if len(values) < 3:
            return 0.3
        std_dev = np.std(values)
        confidence = max(0.3, 1.0 - (std_dev / 5.0))
        return min(confidence, 0.95)

    def _assess_risk_level(self, predictions: Dict) -> Dict:
        depression_risk = self._get_depression_risk_level(predictions['depression']['predicted'])
        cognitive_risk = self._get_cognitive_risk_level(predictions['cognitive']['predicted'])
        overall_risk_score = (
            depression_risk['score'] * 0.6 + cognitive_risk['score'] * 0.4
        )
        overall_level = self._score_to_risk_level(overall_risk_score)
        return {
            'depression': depression_risk,
            'cognitive': cognitive_risk,
            'overall': {
                'score': overall_risk_score,
                'level': overall_level,
                'priority': self._get_priority_level(overall_level)
            }
        }

    def _get_depression_risk_level(self, score: float) -> Dict:
        if score <= 2:
            level = 'low'
            risk_score = 1
        elif score <= 4:
            level = 'mild'
            risk_score = 3
        elif score <= 6:
            level = 'moderate'
            risk_score = 6
        else:
            level = 'high'
            risk_score = 8
        return {'score': risk_score, 'level': level, 'raw_score': score}

    def _get_cognitive_risk_level(self, score: float) -> Dict:
        if score >= 8:
            level = 'normal'
            risk_score = 1
        elif score >= 6:
            level = 'mild_concern'
            risk_score = 4
        elif score >= 4:
            level = 'moderate_concern'
            risk_score = 7
        else:
            level = 'severe_concern'
            risk_score = 9
        return {'score': risk_score, 'level': level, 'raw_score': score}

    def _score_to_risk_level(self, score: float) -> str:
        if score <= 2:
            return 'low'
        elif score <= 4:
            return 'mild'
        elif score <= 6:
            return 'moderate'
        else:
            return 'high'

    def _get_priority_level(self, risk_level: str) -> int:
        priority_map = {'low': 1, 'mild': 2, 'moderate': 3, 'high': 4}
        return priority_map.get(risk_level, 2)

    def _calculate_confidence_scores(self, data: List[Dict]) -> Dict:
        return {
            'data_sufficiency': min(len(data) / 10.0, 1.0),
            'data_consistency': self._calculate_consistency(data),
            'recent_data_weight': 0.8 if len(data) >= 3 else 0.5
        }

    def _calculate_consistency(self, data: List[Dict]) -> float:
        if len(data) < 3:
            return 0.5
        depression_scores = [
            d.get('mentalHealthAnalysis', {}).get('depression', {}).get('score', 5.0) 
            if d.get('mentalHealthAnalysis', {}).get('depression', {}).get('score') is not None
            else 5.0
            for d in data
        ]
        coefficient_of_variation = np.std(depression_scores) / np.mean(depression_scores)
        consistency = max(0.3, 1.0 - coefficient_of_variation)
        return min(consistency, 0.95)

    def _identify_warning_indicators(self, data: List[Dict]) -> List[str]:
        warnings = []
        if len(data) < 3:
            return warnings
        recent_depression = [d['mentalHealthAnalysis']['depression']['score'] for d in data[-3:]]
        recent_cognitive = [d['mentalHealthAnalysis']['cognitive']['score'] for d in data[-3:]]
        if len(recent_depression) >= 2 and recent_depression[-1] > recent_depression[0] + 1:
            warnings.append('depression_increasing_trend')
        if len(recent_cognitive) >= 2 and recent_cognitive[-1] < recent_cognitive[0] - 1:
            warnings.append('cognitive_declining_trend')
        if len(data) >= 2:
            latest = data[-1]
            previous = data[-2]
            depression_change = (latest['mentalHealthAnalysis']['depression']['score'] - previous['mentalHealthAnalysis']['depression']['score'])
            if abs(depression_change) > 2:
                warnings.append('rapid_depression_change')
        return warnings

    def _default_prediction(self, reason: str) -> Dict:
        return {
            'prediction_date': datetime.now().isoformat(),
            'status': 'unavailable',
            'reason': reason,
            'recommendations': ['더 많은 데이터가 필요합니다.']
        } 