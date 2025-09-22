"""
화자 식별 모듈
시니어 화자를 식별하고 분리하는 기능
"""

import numpy as np
import logging
from typing import Dict, List, Any, Optional, Tuple
from collections import Counter

logger = logging.getLogger(__name__)

class SpeakerIdentifier:
    """시니어 화자 식별기"""
    
    def __init__(self):
        # 시니어 음성 특징 기준값
        self.senior_criteria = {
            'pitch_range': (80, 250),  # Hz
            'speaking_rate_range': (2.0, 4.0),  # 음절/초
            'pause_ratio_range': (0.2, 0.6),
            'tremor_threshold': 0.05,
            'age_keywords': [
                '할머니', '할아버지', '어르신', '연세', '나이',
                '옛날', '젊었을', '손자', '손녀', '며느리',
                # 가족 호칭 (존대말 포함)
                '어머니', '아버지', '어머님', '아버님'
            ],
            # 존대말 패턴
            'honorific_patterns': [
                '세요', '십니다', '시다', '시고', '시는', '시는지',
                '시면', '시며', '시나', '시니', '시니라'
            ]
        }
    
    def identify(
        self,
        segments: List[Dict],
        voice_features: Optional[Dict] = None,
        user_profile: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """
        화자 식별 및 시니어 화자 판별
        
        Args:
            segments: STT 세그먼트 리스트
            voice_features: 음성 특징 (선택적)
            
        Returns:
            화자 식별 결과
        """
        
        if not segments:
            logger.warning("화자 식별: 세그먼트가 없음")
            return {
                'status': 'no_segments',
                'senior_speaker_id': None,
                'confidence': 0.0
            }
        
        # 화자별 세그먼트 그룹화
        speaker_groups = self._group_by_speaker(segments)
        logger.info(f"화자 식별: {len(speaker_groups)}명의 화자 감지")
        
        # 각 화자 분석
        speaker_analysis = {}
        for speaker_id, speaker_segments in speaker_groups.items():
            analysis = self._analyze_speaker(speaker_segments, voice_features)
            speaker_analysis[speaker_id] = analysis
            logger.info(f"화자 {speaker_id}: 세그먼트={len(speaker_segments)}, 점수={analysis['senior_score']:.3f}")
        
        # 프로필 정보가 있으면 활용
        if user_profile:
            senior_profile = user_profile.get('senior', {})
            user_data = user_profile.get('user', {})
            
            if senior_profile:
                logger.info(f"시니어 프로필 활용: {senior_profile.get('age')}세, {senior_profile.get('gender')}")
                # 프로필 기반 분석 향상
                speaker_analysis = self._enhance_with_profile(speaker_analysis, senior_profile, user_data)
        
        # 시니어 화자 판별
        senior_speaker = self._identify_senior(speaker_analysis)
        logger.info(f"시니어 화자 선택: ID={senior_speaker['id']}, 신뢰도={senior_speaker['confidence']:.3f}")
        
        return {
            'status': 'success',
            'total_speakers': len(speaker_groups),
            'speaker_analysis': speaker_analysis,
            'senior_speaker_id': senior_speaker['id'],
            'confidence': senior_speaker['confidence'],
            'reasoning': senior_speaker['reasoning']
        }
    
    def _group_by_speaker(self, segments: List[Dict]) -> Dict[str, List[Dict]]:
        """화자별로 세그먼트 그룹화"""
        
        groups = {}
        for seg in segments:
            speaker_id = seg.get('speaker_id', 'unknown')
            if speaker_id not in groups:
                groups[speaker_id] = []
            groups[speaker_id].append(seg)
        
        return groups
    
    def _analyze_speaker(
        self,
        segments: List[Dict],
        voice_features: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """개별 화자 분석"""
        
        # 텍스트 결합
        full_text = ' '.join([seg.get('text', '') for seg in segments])
        
        # 발화 시간 계산
        total_duration = sum([
            seg.get('duration', 0) for seg in segments
        ])
        
        # 단어 수 계산
        word_count = len(full_text.split())
        
        # 발화 속도 계산
        if total_duration <= 0:
            logger.warning(f"화자 분석: 발화 시간이 0 ({total_duration})")
            speaking_rate = 0.0
        else:
            speaking_rate = word_count / total_duration
        
        # 휴지 비율 계산
        pause_ratio = self._calculate_pause_ratio(segments)
        
        # 나이 관련 키워드 및 존대말 패턴 검출
        age_patterns = self._detect_age_keywords(full_text)
        
        # 시니어 점수 계산
        senior_score = self._calculate_senior_score(
            speaking_rate=speaking_rate,
            pause_ratio=pause_ratio,
            age_keywords=len(age_patterns['keywords']),
            honorific_ratio=age_patterns['honorific_ratio'],
            voice_features=voice_features
        )
        
        return {
            'segment_count': len(segments),
            'total_duration': total_duration,
            'word_count': word_count,
            'speaking_rate': speaking_rate,
            'pause_ratio': pause_ratio,
            'age_keywords': age_patterns['keywords'],
            'honorific_patterns': age_patterns['honorific_patterns'],
            'honorific_ratio': age_patterns['honorific_ratio'],
            'senior_score': senior_score,
            'text_sample': full_text[:200] if full_text else ""
        }
    
    def _calculate_pause_ratio(self, segments: List[Dict]) -> float:
        """휴지 비율 계산"""
        
        if len(segments) < 2:
            return 0.0
        
        # 세그먼트 간 간격 계산
        gaps = []
        for i in range(1, len(segments)):
            start_current = segments[i].get('start_time', 0)
            end_previous = segments[i-1].get('end_time', 0)
            gap = start_current - end_previous
            if gap > 0:
                gaps.append(gap)
        
        if not gaps:
            return 0.0
        
        total_gap = sum(gaps)
        total_duration = segments[-1].get('end_time', 0) - segments[0].get('start_time', 0)
        
        if total_duration <= 0:
            logger.warning(f"휴지 비율 계산: 총 시간이 0 ({total_duration})")
            return 0.0
        return total_gap / total_duration
    
    def _detect_age_keywords(self, text: str) -> Dict[str, Any]:
        """나이 관련 키워드 및 존대말 패턴 검출"""
        
        found_keywords = []
        text_lower = text.lower()
        
        # 나이 관련 키워드 검출
        for keyword in self.senior_criteria['age_keywords']:
            if keyword in text_lower:
                found_keywords.append(keyword)
        
        # 존대말 패턴 검출
        honorific_patterns_found = []
        for pattern in self.senior_criteria['honorific_patterns']:
            if pattern in text_lower:
                honorific_patterns_found.append(pattern)
        
        # 존대말 사용 빈도 계산
        honorific_count = len(honorific_patterns_found)
        total_sentences = len(text.split('.')) + len(text.split('?')) + len(text.split('!'))
        honorific_ratio = honorific_count / max(total_sentences, 1)
        
        return {
            'keywords': found_keywords,
            'honorific_patterns': honorific_patterns_found,
            'honorific_count': honorific_count,
            'honorific_ratio': honorific_ratio,
            'total_sentences': total_sentences
        }
    
    def _calculate_senior_score(
        self,
        speaking_rate: float,
        pause_ratio: float,
        age_keywords: int,
        honorific_ratio: float = 0.0,
        voice_features: Optional[Dict] = None
    ) -> float:
        """시니어 점수 계산 (0-1) - 존대말과 가족 호칭에 높은 가중치"""
        
        score = 0.0
        weights = {
            'speaking_rate': 0.15,      # 발화 속도
            'pause_ratio': 0.15,        # 휴지 비율  
            'age_keywords': 0.35,       # 가족 호칭 (가장 중요!)
            'honorific_usage': 0.25,    # 존대말 사용 (두 번째로 중요!)
            'voice_features': 0.1       # 음성 특징
        }
        
        # 발화 속도 점수
        rate_min, rate_max = self.senior_criteria['speaking_rate_range']
        if rate_min <= speaking_rate <= rate_max:
            score += weights['speaking_rate']
        elif speaking_rate < rate_min:
            # 너무 느린 것도 시니어 특징
            score += weights['speaking_rate'] * 0.7
        
        # 휴지 비율 점수
        pause_min, pause_max = self.senior_criteria['pause_ratio_range']
        if pause_min <= pause_ratio <= pause_max:
            score += weights['pause_ratio']
        elif pause_ratio > pause_max:
            # 휴지가 많은 것도 시니어 특징
            score += weights['pause_ratio'] * 0.8
        
        # 나이 키워드 점수 (가족 호칭)
        if age_keywords > 0:
            keyword_score = min(age_keywords / 3, 1.0)  # 3개 이상이면 만점
            score += weights['age_keywords'] * keyword_score
        
        # 존대말 사용 점수 (두 번째로 높은 가중치)
        if honorific_ratio > 0.3:  # 30% 이상 존대말 사용
            score += weights['honorific_usage']
        elif honorific_ratio > 0.1:  # 10% 이상
            score += weights['honorific_usage'] * 0.7
        elif honorific_ratio > 0.05:  # 5% 이상
            score += weights['honorific_usage'] * 0.4
        
        # 음성 특징 점수 (있는 경우)
        if voice_features and voice_features.get('status') == 'success':
            features = voice_features.get('features', {})
            
            # 피치 범위 확인
            pitch = features.get('pitch_mean', 150)
            pitch_min, pitch_max = self.senior_criteria['pitch_range']
            if pitch_min <= pitch <= pitch_max:
                score += weights['voice_features'] * 0.5
            
            # 떨림 확인
            tremor = features.get('tremor_amplitude', 0)
            if tremor > self.senior_criteria['tremor_threshold']:
                score += weights['voice_features'] * 0.5
        
        return min(score, 1.0)
    
    def _identify_senior(self, speaker_analysis: Dict) -> Dict[str, Any]:
        """시니어 화자 식별"""
        
        if not speaker_analysis:
            return {
                'id': None,
                'confidence': 0.0,
                'reasoning': '화자 정보 없음'
            }
        
        # 시니어 점수가 가장 높은 화자 선택 (무조건 하나는 선택)
        best_speaker = None
        best_score = -1.0  # 음수로 초기화하여 0점이라도 선택되도록
        
        for speaker_id, analysis in speaker_analysis.items():
            score = analysis['senior_score']
            if score > best_score:
                best_score = score
                best_speaker = speaker_id
        
        # 점수가 너무 낮으면 기본 화자 선택
        if best_score < 0.1 and len(speaker_analysis) > 0:
            # 발화량이 가장 많은 화자를 시니어로 추정
            max_segments = 0
            for speaker_id, analysis in speaker_analysis.items():
                segment_count = analysis.get('segment_count', 0)
                if segment_count > max_segments:
                    max_segments = segment_count
                    best_speaker = speaker_id
                    best_score = 0.3  # 기본 신뢰도
        
        # 신뢰도 및 근거 생성
        reasoning = []
        confidence = max(best_score, 0.3)  # 최소 신뢰도 보장
        
        if best_speaker:
            analysis = speaker_analysis[best_speaker]
            
            if analysis['age_keywords']:
                reasoning.append(f"가족 호칭/나이 키워드 {len(analysis['age_keywords'])}개 검출")
            
            if analysis.get('honorific_patterns'):
                reasoning.append(f"존대말 패턴 {len(analysis['honorific_patterns'])}개 검출")
            
            if analysis.get('honorific_ratio', 0) > 0.1:
                reasoning.append(f"존대말 사용 비율 {analysis['honorific_ratio']:.1%}")
            
            if analysis['speaking_rate'] < 4:
                reasoning.append(f"느린 발화 속도 ({analysis['speaking_rate']:.1f} 단어/초)")
            
            if analysis['pause_ratio'] > 0.3:
                reasoning.append(f"높은 휴지 비율 ({analysis['pause_ratio']:.1%})")
            
            if analysis['senior_score'] > 0.6:
                reasoning.append("시니어 음성 패턴과 높은 일치도")
            elif analysis['senior_score'] < 0.3:
                reasoning.append("낮은 시니어 점수 - 발화량 기준으로 선택")
        
        # 화자가 선택되지 않은 경우 첫 번째 화자 선택
        if not best_speaker and len(speaker_analysis) > 0:
            best_speaker = list(speaker_analysis.keys())[0]
            confidence = 0.2
            reasoning.append("기본 화자 선택 (첫 번째 화자)")
        
        return {
            'id': best_speaker,
            'confidence': confidence,
            'reasoning': ' / '.join(reasoning) if reasoning else '기본 패턴 매칭'
        }
    
    def _enhance_with_profile(
        self,
        speaker_analysis: Dict,
        senior_profile: Dict,
        user_profile: Dict
    ) -> Dict:
        """프로필 정보를 활용하여 화자 분석 향상"""
        
        senior_age = senior_profile.get('age', 0)
        senior_gender = senior_profile.get('gender', '')
        user_age = user_profile.get('age', 0)
        
        # 나이 차이 기반 점수 조정
        for speaker_id, analysis in speaker_analysis.items():
            boost = 0.0
            
            # 나이 기반 조정
            if senior_age > 65:
                # 고령자 패턴 감지 시 가산점
                if analysis['speaking_rate'] < 3.5:
                    boost += 0.2
                if analysis['pause_ratio'] > 0.3:
                    boost += 0.15
            
            # 성별 기반 피치 범위 조정
            if senior_gender == 'female':
                # 여성 시니어는 높은 피치 예상
                expected_pitch = (150, 300)
            elif senior_gender == 'male':
                # 남성 시니어는 낮은 피치 예상
                expected_pitch = (80, 180)
            else:
                expected_pitch = self.senior_criteria['pitch_range']
            
            # 관계 정보 활용
            relationship = senior_profile.get('relationship', '')
            if relationship in ['할머니', '어머니'] and senior_gender == 'female':
                boost += 0.1
            elif relationship in ['할아버지', '아버지'] and senior_gender == 'male':
                boost += 0.1
            
            # 점수 업데이트
            original_score = analysis['senior_score']
            analysis['senior_score'] = min(original_score + boost, 1.0)
            analysis['profile_boost'] = boost
            
            if boost > 0:
                logger.info(f"화자 {speaker_id}: 프로필 기반 점수 향상 +{boost:.2f}")
        
        return speaker_analysis
    
    def validate_identification(
        self,
        identification_result: Dict,
        ground_truth: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        화자 식별 결과 검증
        
        Args:
            identification_result: 식별 결과
            ground_truth: 실제 시니어 화자 ID (있는 경우)
            
        Returns:
            검증 결과
        """
        
        validation = {
            'identified_speaker': identification_result.get('senior_speaker_id'),
            'confidence': identification_result.get('confidence', 0),
            'validation_status': 'unverified'
        }
        
        if ground_truth:
            is_correct = validation['identified_speaker'] == ground_truth
            validation['validation_status'] = 'correct' if is_correct else 'incorrect'
            validation['ground_truth'] = ground_truth
        
        # 신뢰도 기반 품질 평가
        if validation['confidence'] >= 0.7:
            validation['quality'] = 'high'
        elif validation['confidence'] >= 0.4:
            validation['quality'] = 'moderate'
        else:
            validation['quality'] = 'low'
        
        return validation