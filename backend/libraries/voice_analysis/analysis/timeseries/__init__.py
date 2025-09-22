"""
시계열 분석 모듈

이 모듈은 시니어의 정신건강 지표 변화를 시계열 분석하여 추세와 이상을 감지합니다.
"""

from .baseline_manager import BaselineManager
from .change_detector import ChangeDetector
from .risk_predictor import RiskPredictor
from .early_warning import EarlyWarningSystem
from .trend_analyzer import TrendAnalyzer
from datetime import datetime
from typing import Dict, List, Optional
import logging

class TimeSeriesAnalysisSystem:
    """시계열 분석 통합 시스템"""
    def __init__(self):
        self.baseline_manager = BaselineManager()
        self.change_detector = ChangeDetector()
        self.risk_predictor = RiskPredictor()
        self.early_warning = EarlyWarningSystem()
        self.trend_analyzer = TrendAnalyzer()
        self.logger = logging.getLogger(__name__)

    async def analyze_timeline(self, senior_id: str, historical_data: List[Dict], new_analysis: Optional[Dict] = None) -> Dict:
        try:
            if len(historical_data) >= 5:
                baseline = self.baseline_manager.establish_baseline(senior_id, historical_data)
            else:
                baseline = None
            change_detection = None
            if baseline:
                all_data = historical_data + ([new_analysis] if new_analysis else [])
                change_detection = self.change_detector.detect_changes(all_data, baseline)
            trend_analysis = None
            if len(historical_data) >= 5:
                analysis_data = historical_data + ([new_analysis] if new_analysis else [])
                trend_analysis = self.trend_analyzer.analyze_trends(analysis_data, baseline)
            prediction_data = historical_data + ([new_analysis] if new_analysis else [])
            risk_prediction = self.risk_predictor.predict_risk(prediction_data)
            alerts = self.early_warning.generate_alerts(
                risk_prediction.get('risk_assessment', {}),
                change_detection
            )
            return {
                'senior_id': senior_id,
                'analysis_timestamp': datetime.now().isoformat(),
                'baseline': baseline,
                'change_detection': change_detection,
                'trend_analysis': trend_analysis,
                'risk_prediction': risk_prediction,
                'alerts': alerts,
                'data_points_analyzed': len(prediction_data),
                'analysis_quality': self._assess_analysis_quality(prediction_data)
            }
        except Exception as e:
            self.logger.error(f"시계열 분석 오류: {str(e)}")
            return self._error_response(str(e))

    def _assess_analysis_quality(self, data: List[Dict]) -> Dict:
        return {
            'data_sufficiency': 'sufficient' if len(data) >= 5 else 'limited',
            'temporal_coverage': self._calculate_temporal_coverage(data),
            'confidence_level': min(len(data) / 10.0, 1.0)
        }

    def _calculate_temporal_coverage(self, data: List[Dict]) -> str:
        if len(data) < 2:
            return 'insufficient'
        timestamps = [datetime.fromisoformat(d['analysis_timestamp'].replace('Z', '+00:00')) for d in data]
        time_span = (max(timestamps) - min(timestamps)).days
        if time_span >= 30:
            return 'excellent'
        elif time_span >= 14:
            return 'good'
        elif time_span >= 7:
            return 'fair'
        else:
            return 'limited'

    def _error_response(self, error_message: str) -> Dict:
        return {
            'status': 'error',
            'message': error_message,
            'timestamp': datetime.now().isoformat()
        }
