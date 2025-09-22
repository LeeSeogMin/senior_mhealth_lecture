"""
패턴 감지 모듈
시계열 데이터에서 특정 패턴을 감지하고 분석
"""

import numpy as np
import pandas as pd
from scipy import signal
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime, timedelta
import logging

logger = logging.getLogger(__name__)

class PatternDetector:
    """시계열 패턴 감지기"""
    
    def __init__(self):
        self.patterns = {
            'sudden_decline': self._detect_sudden_decline,
            'gradual_decline': self._detect_gradual_decline,
            'cyclic': self._detect_cyclic_pattern,
            'irregular': self._detect_irregular_pattern,
            'recovery': self._detect_recovery_pattern
        }
    
    def detect_patterns(
        self,
        time_series: pd.Series,
        indicator_name: str
    ) -> Dict[str, Any]:
        """
        시계열 데이터에서 패턴 감지
        
        Args:
            time_series: 시계열 데이터
            indicator_name: 지표 이름
            
        Returns:
            감지된 패턴 정보
        """
        
        if len(time_series) < 3:
            return {
                'status': 'insufficient_data',
                'patterns': []
            }
        
        detected_patterns = []
        
        # 각 패턴 감지 실행
        for pattern_name, detector_func in self.patterns.items():
            result = detector_func(time_series)
            if result['detected']:
                detected_patterns.append({
                    'type': pattern_name,
                    'confidence': result['confidence'],
                    'details': result.get('details', {}),
                    'risk_level': self._assess_pattern_risk(pattern_name, result)
                })
        
        # 복합 패턴 분석
        compound_patterns = self._detect_compound_patterns(detected_patterns)
        
        return {
            'status': 'success',
            'indicator': indicator_name,
            'patterns': detected_patterns,
            'compound_patterns': compound_patterns,
            'overall_pattern': self._determine_overall_pattern(detected_patterns),
            'recommendations': self._generate_pattern_recommendations(detected_patterns)
        }
    
    def _detect_sudden_decline(self, series: pd.Series) -> Dict[str, Any]:
        """급격한 하락 패턴 감지"""
        
        if len(series) < 2:
            return {'detected': False}
        
        # 차분 계산
        diff = series.diff()
        
        # 급격한 하락 임계값 (20% 이상 하락)
        threshold = -0.2
        
        sudden_drops = diff[diff < threshold]
        
        if len(sudden_drops) > 0:
            max_drop = sudden_drops.min()
            drop_index = sudden_drops.idxmin()
            
            return {
                'detected': True,
                'confidence': min(abs(max_drop) / 0.2, 1.0),
                'details': {
                    'max_drop': float(max_drop),
                    'drop_date': drop_index,
                    'drop_magnitude': abs(float(max_drop))
                }
            }
        
        return {'detected': False}
    
    def _detect_gradual_decline(self, series: pd.Series) -> Dict[str, Any]:
        """점진적 하락 패턴 감지"""
        
        if len(series) < 5:
            return {'detected': False}
        
        # 선형 회귀로 추세 확인
        x = np.arange(len(series))
        y = series.values
        
        # 기울기 계산
        slope = np.polyfit(x, y, 1)[0]
        
        # 점진적 하락 기준: 기울기가 음수이고 일정 이상
        if slope < -0.01:
            # R-squared 계산으로 일관성 확인
            y_pred = np.poly1d(np.polyfit(x, y, 1))(x)
            r_squared = 1 - (np.sum((y - y_pred)**2) / np.sum((y - y.mean())**2))
            
            if r_squared > 0.5:  # 어느 정도 일관된 하락
                return {
                    'detected': True,
                    'confidence': r_squared,
                    'details': {
                        'slope': float(slope),
                        'r_squared': float(r_squared),
                        'decline_rate': float(abs(slope) * 100)  # 백분율
                    }
                }
        
        return {'detected': False}
    
    def _detect_cyclic_pattern(self, series: pd.Series) -> Dict[str, Any]:
        """주기적 패턴 감지"""
        
        if len(series) < 7:
            return {'detected': False}
        
        try:
            # FFT를 통한 주기성 감지
            values = series.values
            fft = np.fft.fft(values)
            power = np.abs(fft)**2
            
            # DC 성분 제거
            power[0] = 0
            
            # 주요 주파수 찾기
            freq_idx = np.argmax(power[:len(power)//2])
            
            if freq_idx > 0:
                period = len(values) / freq_idx
                
                # 주기성 강도 계산
                total_power = np.sum(power)
                cyclic_power = power[freq_idx]
                strength = cyclic_power / total_power if total_power > 0 else 0
                
                if strength > 0.2:  # 20% 이상의 파워가 주기성에서 나옴
                    return {
                        'detected': True,
                        'confidence': min(strength * 2, 1.0),
                        'details': {
                            'period': float(period),
                            'strength': float(strength),
                            'frequency': float(freq_idx / len(values))
                        }
                    }
        except Exception as e:
            logger.warning(f"주기 패턴 감지 실패: {e}")
        
        return {'detected': False}
    
    def _detect_irregular_pattern(self, series: pd.Series) -> Dict[str, Any]:
        """불규칙 패턴 감지"""
        
        if len(series) < 3:
            return {'detected': False}
        
        # 변동성 계산
        volatility = series.std()
        mean_val = series.mean()
        
        # 변동 계수 (Coefficient of Variation)
        cv = volatility / mean_val if mean_val != 0 else 0
        
        # 차분의 표준편차
        diff_std = series.diff().std()
        
        # 불규칙성 기준: 높은 변동성
        if cv > 0.3 or diff_std > 0.15:
            return {
                'detected': True,
                'confidence': min(cv / 0.3, 1.0),
                'details': {
                    'volatility': float(volatility),
                    'coefficient_variation': float(cv),
                    'diff_std': float(diff_std)
                }
            }
        
        return {'detected': False}
    
    def _detect_recovery_pattern(self, series: pd.Series) -> Dict[str, Any]:
        """회복 패턴 감지"""
        
        if len(series) < 4:
            return {'detected': False}
        
        # 최근 데이터와 과거 데이터 비교
        recent = series.iloc[-len(series)//3:]
        past = series.iloc[:len(series)//3]
        
        recent_mean = recent.mean()
        past_mean = past.mean()
        
        # 중간 지점 확인 (V자 회복 패턴)
        if len(series) >= 6:
            middle = series.iloc[len(series)//3:2*len(series)//3]
            middle_mean = middle.mean()
            
            # V자 패턴: 중간이 낮고 최근이 회복
            if middle_mean < past_mean and recent_mean > middle_mean:
                recovery_rate = (recent_mean - middle_mean) / max(abs(middle_mean), 0.01)
                
                return {
                    'detected': True,
                    'confidence': min(recovery_rate, 1.0),
                    'details': {
                        'recovery_rate': float(recovery_rate),
                        'lowest_point': float(middle_mean),
                        'current_level': float(recent_mean),
                        'recovery_type': 'V-shaped'
                    }
                }
        
        # 단순 상승 패턴
        if recent_mean > past_mean * 1.1:  # 10% 이상 상승
            improvement = (recent_mean - past_mean) / past_mean
            
            return {
                'detected': True,
                'confidence': min(improvement, 1.0),
                'details': {
                    'improvement': float(improvement),
                    'past_level': float(past_mean),
                    'current_level': float(recent_mean),
                    'recovery_type': 'gradual'
                }
            }
        
        return {'detected': False}
    
    def _detect_compound_patterns(self, patterns: List[Dict]) -> List[Dict]:
        """복합 패턴 감지"""
        
        compound = []
        
        # 패턴 조합 확인
        pattern_types = [p['type'] for p in patterns]
        
        # 위험한 조합: 급격한 하락 + 불규칙
        if 'sudden_decline' in pattern_types and 'irregular' in pattern_types:
            compound.append({
                'type': 'crisis',
                'description': '급격한 악화와 불안정성',
                'risk_level': 'high'
            })
        
        # 점진적 악화
        if 'gradual_decline' in pattern_types and 'cyclic' not in pattern_types:
            compound.append({
                'type': 'chronic_decline',
                'description': '지속적인 악화 추세',
                'risk_level': 'moderate'
            })
        
        # 회복 중
        if 'recovery' in pattern_types:
            compound.append({
                'type': 'improving',
                'description': '회복 진행 중',
                'risk_level': 'low'
            })
        
        return compound
    
    def _assess_pattern_risk(self, pattern_type: str, result: Dict) -> str:
        """패턴 위험도 평가"""
        
        risk_levels = {
            'sudden_decline': 'high',
            'gradual_decline': 'moderate',
            'irregular': 'moderate',
            'cyclic': 'low',
            'recovery': 'positive'
        }
        
        base_risk = risk_levels.get(pattern_type, 'unknown')
        
        # 신뢰도에 따른 조정
        confidence = result.get('confidence', 0)
        if confidence < 0.5 and base_risk != 'positive':
            return 'low'
        
        return base_risk
    
    def _determine_overall_pattern(self, patterns: List[Dict]) -> str:
        """전체 패턴 결정"""
        
        if not patterns:
            return 'stable'
        
        # 가장 높은 신뢰도의 패턴
        highest_confidence = max(patterns, key=lambda x: x['confidence'])
        
        return highest_confidence['type']
    
    def _generate_pattern_recommendations(self, patterns: List[Dict]) -> List[str]:
        """패턴 기반 권고사항"""
        
        recommendations = []
        
        for pattern in patterns:
            if pattern['type'] == 'sudden_decline':
                recommendations.append("급격한 변화 감지 - 즉시 상태 확인 필요")
            elif pattern['type'] == 'gradual_decline':
                recommendations.append("점진적 악화 추세 - 조기 개입 프로그램 권장")
            elif pattern['type'] == 'irregular':
                recommendations.append("불규칙 패턴 - 일일 모니터링 강화")
            elif pattern['type'] == 'recovery':
                recommendations.append("회복 징후 - 현재 치료/관리 유지")
        
        return recommendations