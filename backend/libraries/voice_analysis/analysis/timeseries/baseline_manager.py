import numpy as np
from datetime import datetime
from typing import Dict, List, Tuple
import logging

class BaselineManager:
    """개인별 베이스라인 관리 시스템"""
    def __init__(self, min_data_points: int = 5):
        self.min_data_points = min_data_points
        self.logger = logging.getLogger(__name__)

    def establish_baseline(self, senior_id: str, historical_data: List[Dict]) -> Dict:
        """초기 베이스라인 설정"""
        if len(historical_data) < self.min_data_points:
            raise ValueError(f"베이스라인 설정을 위해 최소 {self.min_data_points}개의 데이터가 필요합니다.")

        # 정신건강 지표별 통계 계산
        depression_scores = [data['mentalHealthAnalysis']['depression']['score'] 
                           for data in historical_data]
        cognitive_scores = [data['mentalHealthAnalysis']['cognitive']['score'] 
                          for data in historical_data]

        # 지표 추출 - 없으면 기본값 사용
        speech_rates = [data.get('voicePatterns', {}).get('speechRate', 120) for data in historical_data]
        pause_ratios = [data.get('voicePatterns', {}).get('pauseRatio', 0.3) for data in historical_data]

        baseline = {
            'senior_id': senior_id,
            'established_date': datetime.now().isoformat(),
            'data_points_used': len(historical_data),
            'mental_health': {
                'depression': {
                    'mean': np.mean(depression_scores),
                    'std': np.std(depression_scores),
                    'range': [np.min(depression_scores), np.max(depression_scores)],
                    'normal_range': self._calculate_normal_range(depression_scores)
                },
                'cognitive': {
                    'mean': np.mean(cognitive_scores),
                    'std': np.std(cognitive_scores),
                    'range': [np.min(cognitive_scores), np.max(cognitive_scores)],
                    'normal_range': self._calculate_normal_range(cognitive_scores)
                }
            },
            'removed_patterns': {
                'speech_rate': {
                    'mean': np.mean(speech_rates),
                    'std': np.std(speech_rates),
                    'normal_range': self._calculate_normal_range(speech_rates)
                },
                'pause_ratio': {
                    'mean': np.mean(pause_ratios),
                    'std': np.std(pause_ratios),
                    'normal_range': self._calculate_normal_range(pause_ratios)
                }
            },
            'confidence_level': self._calculate_confidence(len(historical_data))
        }

        self.logger.info(f"베이스라인 설정 완료 - Senior ID: {senior_id}")
        return baseline

    def update_baseline(self, baseline: Dict, new_data: Dict, adaptation_rate: float = 0.1) -> Dict:
        """베이스라인 적응적 업데이트"""
        updated_baseline = baseline.copy()

        # 새로운 데이터로 점진적 업데이트
        new_depression = new_data['mentalHealthAnalysis']['depression']['score']
        new_cognitive = new_data['mentalHealthAnalysis']['cognitive']['score']

        # 지수 이동 평균을 사용한 업데이트
        updated_baseline['mental_health']['depression']['mean'] = \
            self._exponential_moving_average(
                baseline['mental_health']['depression']['mean'],
                new_depression, adaptation_rate
            )

        updated_baseline['mental_health']['cognitive']['mean'] = \
            self._exponential_moving_average(
                baseline['mental_health']['cognitive']['mean'],
                new_cognitive, adaptation_rate
            )

        updated_baseline['last_updated'] = datetime.now().isoformat()
        updated_baseline['data_points_used'] += 1

        return updated_baseline

    def _calculate_normal_range(self, values: List[float], z_score_threshold: float = 1.96) -> Tuple[float, float]:
        """정상 범위 계산 (95% 신뢰구간)"""
        mean_val = np.mean(values)
        std_val = np.std(values)
        lower_bound = mean_val - (z_score_threshold * std_val)
        upper_bound = mean_val + (z_score_threshold * std_val)
        return (lower_bound, upper_bound)

    def _exponential_moving_average(self, old_value: float, new_value: float, alpha: float) -> float:
        """지수 이동 평균 계산"""
        return alpha * new_value + (1 - alpha) * old_value

    def _calculate_confidence(self, data_points: int) -> float:
        """베이스라인 신뢰도 계산"""
        if data_points < 3:
            return 0.3
        elif data_points < 5:
            return 0.6
        elif data_points < 10:
            return 0.8
        else:
            return 0.95 