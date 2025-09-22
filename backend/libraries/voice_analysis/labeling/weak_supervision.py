"""
약한 지도학습 레이블링 함수들
PHQ-9, GAD-7 등 검증된 척도와 규칙 기반 레이블링
"""

from typing import Optional, List, Tuple, Dict, Any
from dataclasses import dataclass
import re
import numpy as np
import logging

logger = logging.getLogger(__name__)


@dataclass
class WeakLabel:
    """약한 레이블 결과"""
    label: str
    confidence: float
    rules_applied: List[str]
    details: Dict[str, Any]


class WeakSupervision:
    """규칙 기반 약한 레이블링"""
    
    def __init__(self, confidence_threshold: float = 0.8):
        """
        Args:
            confidence_threshold: 레이블 적용 최소 신뢰도
        """
        self.confidence_threshold = confidence_threshold
        
        # 레이블링 함수 등록
        self.labeling_functions = [
            self.lf_phq9_based,
            self.lf_gad7_based,
            self.lf_keyword_based,
            self.lf_pattern_based,
            self.lf_temporal_based,
            self.lf_voice_features_based
        ]
        
        # 레이블링 규칙 가중치
        self.weights = {
            'phq9': 0.9,      # 검증된 척도 높은 가중치
            'gad7': 0.9,
            'keyword': 0.7,
            'pattern': 0.6,
            'temporal': 0.5,
            'voice': 0.6
        }
        
        logger.info(f"Weak Supervision initialized with {len(self.labeling_functions)} labeling functions")
    
    def generate_label(self, data: Dict[str, Any]) -> Optional[WeakLabel]:
        """
        여러 레이블링 함수를 조합하여 최종 레이블 생성
        
        Args:
            data: 레이블링할 데이터
            
        Returns:
            약한 레이블 또는 None
        """
        labels = []
        rules_applied = []
        
        # 모든 레이블링 함수 실행
        for lf in self.labeling_functions:
            result = lf(data)
            if result:
                label, confidence, rule_name = result
                labels.append((label, confidence, rule_name))
                rules_applied.append(rule_name)
        
        if not labels:
            return None
        
        # 레이블 조합 (투표 또는 가중 평균)
        combined_label = self._combine_labels(labels)
        
        if combined_label and combined_label.confidence >= self.confidence_threshold:
            combined_label.rules_applied = rules_applied
            return combined_label
        
        return None
    
    def lf_phq9_based(self, data: Dict) -> Optional[Tuple[str, float, str]]:
        """
        PHQ-9 (Patient Health Questionnaire-9) 점수 기반 레이블링
        우울증 선별 표준 도구
        """
        if 'phq9_score' not in data:
            return None
        
        score = data['phq9_score']
        
        # PHQ-9 표준 해석
        if score >= 20:
            return ('severe_depression', 0.95, 'phq9')
        elif score >= 15:
            return ('moderately_severe_depression', 0.90, 'phq9')
        elif score >= 10:
            return ('moderate_depression', 0.85, 'phq9')
        elif score >= 5:
            return ('mild_depression', 0.80, 'phq9')
        else:
            return ('minimal_depression', 0.85, 'phq9')
    
    def lf_gad7_based(self, data: Dict) -> Optional[Tuple[str, float, str]]:
        """
        GAD-7 (Generalized Anxiety Disorder-7) 점수 기반 레이블링
        불안 장애 선별 표준 도구
        """
        if 'gad7_score' not in data:
            return None
        
        score = data['gad7_score']
        
        # GAD-7 표준 해석
        if score >= 15:
            return ('severe_anxiety', 0.95, 'gad7')
        elif score >= 10:
            return ('moderate_anxiety', 0.90, 'gad7')
        elif score >= 5:
            return ('mild_anxiety', 0.85, 'gad7')
        else:
            return ('minimal_anxiety', 0.85, 'gad7')
    
    def lf_keyword_based(self, data: Dict) -> Optional[Tuple[str, float, str]]:
        """
        위험 키워드 기반 레이블링
        텍스트에서 정신건강 관련 키워드 탐지
        """
        if 'text' not in data and 'transcription' not in data:
            return None
        
        text = data.get('text', data.get('transcription', '')).lower()
        
        # 위험 키워드 사전
        high_risk_keywords = {
            'suicide': ['자살', '죽고싶', '죽고 싶', '사라지고싶', '사라지고 싶',
                       'suicide', 'kill myself', 'end it all', 'not worth living'],
            'self_harm': ['자해', 'self harm', 'cutting', 'hurt myself'],
            'hopelessness': ['희망이 없', '포기', '의미없', '무의미', 'hopeless', 'no hope', 'give up']
        }
        
        depression_keywords = {
            'mood': ['우울', '슬픔', '슬퍼', 'depressed', 'sad', 'blue', 'down'],
            'anhedonia': ['재미없', '흥미없', '무감각', 'no interest', 'no pleasure', 'numb'],
            'fatigue': ['피곤', '지친', '무기력', 'tired', 'exhausted', 'no energy']
        }
        
        anxiety_keywords = {
            'worry': ['걱정', '불안', '초조', 'worried', 'anxious', 'nervous'],
            'panic': ['공황', '숨막히', '심장이', 'panic', 'can\'t breathe', 'heart racing'],
            'fear': ['무서워', '두려워', '겁나', 'scared', 'afraid', 'fearful']
        }
        
        # 키워드 매칭
        for risk_type, keywords in high_risk_keywords.items():
            if any(keyword in text for keyword in keywords):
                return ('high_risk', 0.95, 'keyword')
        
        depression_count = sum(1 for keywords in depression_keywords.values() 
                              for keyword in keywords if keyword in text)
        anxiety_count = sum(1 for keywords in anxiety_keywords.values() 
                           for keyword in keywords if keyword in text)
        
        if depression_count >= 3:
            return ('depression_likely', 0.75, 'keyword')
        elif anxiety_count >= 3:
            return ('anxiety_likely', 0.75, 'keyword')
        
        return None
    
    def lf_pattern_based(self, data: Dict) -> Optional[Tuple[str, float, str]]:
        """
        행동 패턴 기반 레이블링
        사용 패턴, 수면, 활동량 등
        """
        if 'usage_patterns' not in data:
            return None
        
        patterns = data['usage_patterns']
        
        # 수면 문제 패턴
        if patterns.get('night_usage_hours', 0) > 3:
            if patterns.get('sleep_hours', 8) < 5:
                return ('insomnia_likely', 0.70, 'pattern')
        
        # 활동 감소 패턴 (우울증 지표)
        if patterns.get('activity_drop_percent', 0) > 50:
            return ('depression_sign', 0.65, 'pattern')
        
        # 불규칙한 패턴 (불안 지표)
        if patterns.get('usage_variance', 0) > 0.7:
            return ('anxiety_sign', 0.60, 'pattern')
        
        return None
    
    def lf_temporal_based(self, data: Dict) -> Optional[Tuple[str, float, str]]:
        """
        시간적 패턴 기반 레이블링
        시간대별 사용 패턴 분석
        """
        if 'temporal_features' not in data:
            return None
        
        temporal = data['temporal_features']
        
        # 새벽 시간대 집중 사용 (불면증/우울증)
        if temporal.get('peak_hour', 12) in range(2, 6):
            return ('sleep_disorder_likely', 0.65, 'temporal')
        
        # 주말/주중 패턴 차이 (사회적 고립)
        weekend_diff = temporal.get('weekend_weekday_diff', 0)
        if weekend_diff > 0.5:
            return ('social_isolation_sign', 0.60, 'temporal')
        
        return None
    
    def lf_voice_features_based(self, data: Dict) -> Optional[Tuple[str, float, str]]:
        """
        음성 특징 기반 레이블링
        피치, 에너지, 속도 등 음성 바이오마커
        """
        if 'voice_features' not in data:
            return None
        
        voice = data['voice_features']
        
        # 우울증 음성 특징
        # - 낮은 피치 변화 (단조로운 톤)
        # - 낮은 에너지
        # - 느린 말 속도
        if (voice.get('pitch_variance', 1.0) < 0.3 and 
            voice.get('energy_mean', 1.0) < 0.4 and
            voice.get('speech_rate', 1.0) < 0.7):
            return ('depression_voice_marker', 0.70, 'voice')
        
        # 불안 음성 특징
        # - 높은 피치
        # - 빠른 말 속도
        # - 불규칙한 리듬
        if (voice.get('pitch_mean', 0.5) > 0.7 and
            voice.get('speech_rate', 1.0) > 1.3 and
            voice.get('rhythm_variance', 0.5) > 0.7):
            return ('anxiety_voice_marker', 0.65, 'voice')
        
        return None
    
    def _combine_labels(self, labels: List[Tuple[str, float, str]]) -> Optional[WeakLabel]:
        """
        여러 레이블링 함수 결과 조합
        
        Args:
            labels: (레이블, 신뢰도, 규칙이름) 튜플 리스트
            
        Returns:
            조합된 최종 레이블
        """
        if not labels:
            return None
        
        # 레이블별 가중 점수 계산
        label_scores = {}
        label_details = {}
        
        for label, confidence, rule_name in labels:
            weight = self.weights.get(rule_name, 0.5)
            score = confidence * weight
            
            if label not in label_scores:
                label_scores[label] = []
                label_details[label] = []
            
            label_scores[label].append(score)
            label_details[label].append({
                'rule': rule_name,
                'confidence': confidence,
                'weight': weight
            })
        
        # 최고 점수 레이블 선택
        best_label = None
        best_score = 0
        
        for label, scores in label_scores.items():
            # 평균 점수 계산
            avg_score = np.mean(scores)
            
            # 다수 규칙이 동의하면 보너스
            if len(scores) > 1:
                avg_score *= (1 + 0.1 * len(scores))
            
            if avg_score > best_score:
                best_score = avg_score
                best_label = label
        
        if best_label:
            return WeakLabel(
                label=best_label,
                confidence=min(best_score, 1.0),  # 최대 1.0
                rules_applied=[],  # 나중에 채워짐
                details={'label_details': label_details[best_label]}
            )
        
        return None
    
    def update_rules_with_expert_label(self, expert_label):
        """
        전문가 레이블로 규칙 가중치 업데이트
        
        Args:
            expert_label: 전문가가 레이블링한 데이터
        """
        # 전문가 레이블과 일치한 규칙의 가중치 증가
        # 불일치한 규칙의 가중치 감소
        # Implementation: Rule weight adjustment pending
        # Placeholder for future statistical analysis
        pass
    
    def get_rule_statistics(self) -> Dict:
        """규칙별 통계 반환"""
        # Implementation: Statistical analysis module pending
        return {
            'rule_weights': self.weights,
            'rule_counts': {},
            'rule_accuracy': {}
        }