from datetime import datetime
from typing import Dict, List
import logging

class EarlyWarningSystem:
    """조기 경고 시스템"""
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.warning_thresholds = {
            'depression': {'mild': 4, 'moderate': 6, 'severe': 8},
            'cognitive': {'mild': 6, 'moderate': 4, 'severe': 2},
            'rapid_change': 2.0,
            'trend_significance': 0.05
        }

    def generate_alerts(self, risk_assessment: Dict, change_detection: Dict = None) -> List[Dict]:
        alerts = []
        risk_alerts = self._generate_risk_alerts(risk_assessment)
        alerts.extend(risk_alerts)
        if change_detection:
            change_alerts = self._generate_change_alerts(change_detection)
            alerts.extend(change_alerts)
        alerts.sort(key=lambda x: x['priority'], reverse=True)
        return alerts

    def _generate_risk_alerts(self, risk_assessment: Dict) -> List[Dict]:
        alerts = []
        overall_risk = risk_assessment.get('overall', {})
        depression_risk = risk_assessment.get('depression', {})
        cognitive_risk = risk_assessment.get('cognitive', {})
        if overall_risk.get('level') in ['moderate', 'high']:
            alerts.append({
                'type': 'overall_risk',
                'level': overall_risk['level'],
                'priority': overall_risk['priority'],
                'message': self._get_risk_message(overall_risk['level']),
                'recommendations': self._get_risk_recommendations(overall_risk['level']),
                'timestamp': datetime.now().isoformat()
            })
        if depression_risk.get('level') in ['moderate', 'high']:
            alerts.append({
                'type': 'depression_risk',
                'level': depression_risk['level'],
                'priority': self._get_depression_priority(depression_risk['level']),
                'message': f"우울증 위험도가 {depression_risk['level']} 수준입니다.",
                'score': depression_risk['score'],
                'recommendations': self._get_depression_recommendations(depression_risk['level']),
                'timestamp': datetime.now().isoformat()
            })
        if cognitive_risk.get('level') in ['moderate_concern', 'severe_concern']:
            alerts.append({
                'type': 'cognitive_risk',
                'level': cognitive_risk['level'],
                'priority': self._get_cognitive_priority(cognitive_risk['level']),
                'message': f"인지기능이 {cognitive_risk['level']} 수준입니다.",
                'score': cognitive_risk['score'],
                'recommendations': self._get_cognitive_recommendations(cognitive_risk['level']),
                'timestamp': datetime.now().isoformat()
            })
        return alerts

    def _generate_change_alerts(self, change_detection: Dict) -> List[Dict]:
        alerts = []
        for change_point in change_detection.get('change_points', []):
            alerts.append({
                'type': 'change_point',
                'metric': change_point['metric'],
                'priority': 3,
                'message': f"{change_point['metric']} 지표에서 유의미한 변화가 감지되었습니다.",
                'timestamp': change_point['timestamp'],
                'value': change_point['value'],
                'recommendations': ['전문가 상담을 고려해보세요.']
            })
        for metric, trend_info in change_detection.get('trend_analysis', {}).items():
            if trend_info.get('significance', False):
                if trend_info['trend'] == 'decreasing' and metric == 'cognitive':
                    alerts.append({
                        'type': 'declining_trend',
                        'metric': metric,
                        'priority': 4,
                        'message': f"{metric} 지표가 지속적으로 감소하고 있습니다.",
                        'trend_rate': trend_info.get('rate_of_change', 0),
                        'recommendations': ['정기적인 인지 활동을 늘려보세요.'],
                        'timestamp': datetime.now().isoformat()
                    })
                elif trend_info['trend'] == 'increasing' and metric == 'depression':
                    alerts.append({
                        'type': 'increasing_trend',
                        'metric': metric,
                        'priority': 4,
                        'message': f"{metric} 지표가 지속적으로 증가하고 있습니다.",
                        'trend_rate': trend_info.get('rate_of_change', 0),
                        'recommendations': ['전문가 상담을 받아보세요.'],
                        'timestamp': datetime.now().isoformat()
                    })
        return alerts

    def _get_risk_message(self, level: str) -> str:
        messages = {
            'low': '정신건강 상태가 양호합니다.',
            'mild': '경미한 주의가 필요합니다.',
            'moderate': '중등도의 관심이 필요합니다.',
            'high': '즉시 전문가 상담이 권장됩니다.'
        }
        return messages.get(level, '')

    def _get_risk_recommendations(self, level: str) -> List[str]:
        recs = {
            'low': ['정기적인 건강 관리를 유지하세요.'],
            'mild': ['생활 습관 개선을 시도해보세요.'],
            'moderate': ['가족 및 전문가와 상담을 권장합니다.'],
            'high': ['즉시 전문가 상담을 받으세요.']
        }
        return recs.get(level, [])

    def _get_depression_priority(self, level: str) -> int:
        return {'mild': 2, 'moderate': 3, 'high': 4}.get(level, 1)

    def _get_depression_recommendations(self, level: str) -> List[str]:
        recs = {
            'mild': ['가벼운 운동, 취미 활동을 늘려보세요.'],
            'moderate': ['가족과 대화, 전문가 상담을 권장합니다.'],
            'high': ['즉시 전문가 상담을 받으세요.']
        }
        return recs.get(level, [])

    def _get_cognitive_priority(self, level: str) -> int:
        return {'mild_concern': 2, 'moderate_concern': 3, 'severe_concern': 4}.get(level, 1)

    def _get_cognitive_recommendations(self, level: str) -> List[str]:
        recs = {
            'mild_concern': ['두뇌 자극 활동을 늘려보세요.'],
            'moderate_concern': ['인지 훈련, 전문가 상담을 권장합니다.'],
            'severe_concern': ['즉시 전문가 상담을 받으세요.']
        }
        return recs.get(level, []) 