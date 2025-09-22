"""
품질 체크 모듈
음성 및 분석 데이터의 품질 검증
"""

import numpy as np
import logging
from typing import Dict, Any, List, Tuple, Optional
from datetime import datetime
import librosa

logger = logging.getLogger(__name__)

class QualityChecker:
    """데이터 품질 검사기"""
    
    def __init__(self):
        # 품질 기준값
        self.quality_criteria = {
            'audio': {
                'min_duration': 3.0,      # 최소 3초
                'max_duration': 300.0,    # 최대 5분
                'min_sample_rate': 8000,  # 최소 8kHz
                'min_snr': 10.0,          # 최소 SNR 10dB
                'max_clipping': 0.01,     # 최대 1% 클리핑
                'min_speech_ratio': 0.2   # 최소 20% 음성
            },
            'text': {
                'min_words': 10,          # 최소 10단어
                'max_words': 10000,       # 최대 10000단어
                'min_unique_words': 5,    # 최소 5개 고유 단어
                'max_repetition': 0.5     # 최대 50% 반복
            },
            'indicators': {
                'valid_range': (0.0, 1.0),
                'min_variation': 0.001,    # 최소 변동
                'max_missing': 0.2        # 최대 20% 결측
            }
        }
        
    def check_audio_quality(self, audio_path: str) -> Dict[str, Any]:
        """
        오디오 품질 검사
        
        Args:
            audio_path: 오디오 파일 경로
            
        Returns:
            품질 검사 결과
        """
        
        try:
            # 오디오 로드
            y, sr = librosa.load(audio_path, sr=None)
            
            quality_checks = {
                'duration': self._check_duration(y, sr),
                'sample_rate': self._check_sample_rate(sr),
                'snr': self._check_snr(y),
                'clipping': self._check_clipping(y),
                'speech_ratio': self._check_speech_ratio(y, sr),
                'noise_level': self._check_noise_level(y, sr)
            }
            
            # 종합 품질 점수
            quality_score = self._calculate_audio_quality_score(quality_checks)
            
            # 품질 등급
            quality_grade = self._determine_quality_grade(quality_score)
            
            return {
                'status': 'success',
                'quality_score': quality_score,
                'quality_grade': quality_grade,
                'checks': quality_checks,
                'issues': self._identify_audio_issues(quality_checks),
                'recommendations': self._generate_audio_recommendations(quality_checks)
            }
            
        except Exception as e:
            logger.error(f"오디오 품질 검사 실패: {e}")
            return {
                'status': 'error',
                'error': str(e)
            }
    
    def check_text_quality(self, text: str) -> Dict[str, Any]:
        """
        텍스트 품질 검사
        
        Args:
            text: 검사할 텍스트
            
        Returns:
            품질 검사 결과
        """
        
        if not text:
            return {
                'status': 'error',
                'error': '빈 텍스트'
            }
        
        words = text.split()
        unique_words = set(words)
        
        quality_checks = {
            'word_count': {
                'value': len(words),
                'passed': self.quality_criteria['text']['min_words'] <= len(words) <= self.quality_criteria['text']['max_words']
            },
            'unique_words': {
                'value': len(unique_words),
                'passed': len(unique_words) >= self.quality_criteria['text']['min_unique_words']
            },
            'repetition_ratio': {
                'value': 1 - (len(unique_words) / max(len(words), 1)),
                'passed': (1 - (len(unique_words) / max(len(words), 1))) <= self.quality_criteria['text']['max_repetition']
            },
            'coherence': self._check_text_coherence(text),
            'completeness': self._check_text_completeness(text)
        }
        
        # 종합 품질 점수
        quality_score = self._calculate_text_quality_score(quality_checks)
        
        return {
            'status': 'success',
            'quality_score': quality_score,
            'quality_grade': self._determine_quality_grade(quality_score),
            'checks': quality_checks,
            'issues': self._identify_text_issues(quality_checks),
            'recommendations': self._generate_text_recommendations(quality_checks)
        }
    
    def check_indicators_quality(self, indicators: Dict[str, float]) -> Dict[str, Any]:
        """
        지표 품질 검사
        
        Args:
            indicators: 5대 지표 딕셔너리
            
        Returns:
            품질 검사 결과
        """
        
        quality_checks = {}
        
        for key, value in indicators.items():
            checks = {
                'in_range': self.quality_criteria['indicators']['valid_range'][0] <= value <= self.quality_criteria['indicators']['valid_range'][1],
                'not_null': value is not None,
                'reasonable': self._check_indicator_reasonable(key, value)
            }
            
            quality_checks[key] = {
                'value': value,
                'checks': checks,
                'passed': all(checks.values())
            }
        
        # 지표 간 일관성 검사
        consistency_check = self._check_indicators_consistency(indicators)
        
        # 종합 품질 점수
        passed_count = sum(1 for check in quality_checks.values() if check['passed'])
        quality_score = (passed_count / len(quality_checks)) * consistency_check['score']
        
        return {
            'status': 'success',
            'quality_score': quality_score,
            'quality_grade': self._determine_quality_grade(quality_score),
            'indicator_checks': quality_checks,
            'consistency': consistency_check,
            'issues': self._identify_indicator_issues(quality_checks, consistency_check),
            'recommendations': self._generate_indicator_recommendations(quality_checks)
        }
    
    def _check_duration(self, y: np.ndarray, sr: int) -> Dict[str, Any]:
        """오디오 길이 검사"""
        
        duration = len(y) / sr
        criteria = self.quality_criteria['audio']
        
        return {
            'value': duration,
            'passed': criteria['min_duration'] <= duration <= criteria['max_duration'],
            'message': f"Duration: {duration:.1f}s"
        }
    
    def _check_sample_rate(self, sr: int) -> Dict[str, Any]:
        """샘플링 레이트 검사"""
        
        return {
            'value': sr,
            'passed': sr >= self.quality_criteria['audio']['min_sample_rate'],
            'message': f"Sample rate: {sr}Hz"
        }
    
    def _check_snr(self, y: np.ndarray) -> Dict[str, Any]:
        """신호 대 잡음비 검사"""
        
        # 간단한 SNR 추정
        signal_power = np.mean(y**2)
        
        # 무음 구간을 잡음으로 간주
        silence_threshold = 0.01 * np.max(np.abs(y))
        noise = y[np.abs(y) < silence_threshold]
        
        if len(noise) > 0:
            noise_power = np.mean(noise**2)
            if noise_power > 0:
                snr = 10 * np.log10(signal_power / noise_power)
            else:
                snr = 40.0  # 매우 깨끗한 신호
        else:
            snr = 30.0  # 기본값
        
        return {
            'value': float(snr),
            'passed': snr >= self.quality_criteria['audio']['min_snr'],
            'message': f"SNR: {snr:.1f}dB"
        }
    
    def _check_clipping(self, y: np.ndarray) -> Dict[str, Any]:
        """클리핑 검사"""
        
        # 클리핑된 샘플 비율
        max_val = np.max(np.abs(y))
        if max_val > 0:
            clipped = np.sum(np.abs(y) > 0.99 * max_val) / len(y)
        else:
            clipped = 0
        
        return {
            'value': float(clipped),
            'passed': clipped <= self.quality_criteria['audio']['max_clipping'],
            'message': f"Clipping: {clipped*100:.2f}%"
        }
    
    def _check_speech_ratio(self, y: np.ndarray, sr: int) -> Dict[str, Any]:
        """음성 비율 검사"""
        
        # 음성 활동 구간 검출
        intervals = librosa.effects.split(y, top_db=20)
        
        if len(intervals) > 0:
            speech_samples = sum(end - start for start, end in intervals)
            speech_ratio = speech_samples / len(y)
        else:
            speech_ratio = 0
        
        return {
            'value': float(speech_ratio),
            'passed': speech_ratio >= self.quality_criteria['audio']['min_speech_ratio'],
            'message': f"Speech ratio: {speech_ratio*100:.1f}%"
        }
    
    def _check_noise_level(self, y: np.ndarray, sr: int) -> Dict[str, Any]:
        """잡음 수준 검사"""
        
        # 스펙트럴 센트로이드로 잡음 추정
        spectral_centroids = librosa.feature.spectral_centroid(y=y, sr=sr)[0]
        noise_indicator = np.std(spectral_centroids) / np.mean(spectral_centroids)
        
        # 낮을수록 좋음
        noise_level = min(noise_indicator, 1.0)
        
        return {
            'value': float(noise_level),
            'passed': noise_level < 0.5,
            'message': f"Noise level: {noise_level:.2f}"
        }
    
    def _check_text_coherence(self, text: str) -> Dict[str, Any]:
        """텍스트 일관성 검사"""
        
        sentences = text.split('.')
        
        # 문장 길이 변동성
        if len(sentences) > 1:
            lengths = [len(s.split()) for s in sentences if s.strip()]
            if lengths:
                coherence = 1 - (np.std(lengths) / max(np.mean(lengths), 1))
            else:
                coherence = 0.5
        else:
            coherence = 0.7
        
        return {
            'value': float(coherence),
            'passed': coherence > 0.5,
            'message': f"Coherence: {coherence:.2f}"
        }
    
    def _check_text_completeness(self, text: str) -> Dict[str, Any]:
        """텍스트 완성도 검사"""
        
        # 미완성 표현 검출
        incomplete_markers = ['...', '음', '어', '그', '저기']
        incomplete_count = sum(1 for marker in incomplete_markers if marker in text)
        
        words = text.split()
        if words:
            incompleteness = incomplete_count / len(words)
            completeness = 1 - min(incompleteness, 1)
        else:
            completeness = 0
        
        return {
            'value': float(completeness),
            'passed': completeness > 0.7,
            'message': f"Completeness: {completeness:.2f}"
        }
    
    def _check_indicator_reasonable(self, key: str, value: float) -> bool:
        """지표 값의 합리성 검사"""
        
        # 극단적 값 체크
        if value == 0.0 or value == 1.0:
            return False  # 정확히 0 또는 1은 비현실적
        
        return True
    
    def _check_indicators_consistency(self, indicators: Dict) -> Dict[str, Any]:
        """지표 간 일관성 검사"""
        
        inconsistencies = []
        
        # DRI와 OV는 일반적으로 상관관계
        if 'DRI' in indicators and 'OV' in indicators:
            if indicators['DRI'] < 0.3 and indicators['OV'] > 0.8:
                inconsistencies.append("DRI 낮은데 OV 높음")
        
        # CFL과 ES도 일반적으로 관련
        if 'CFL' in indicators and 'ES' in indicators:
            if indicators['CFL'] < 0.3 and indicators['ES'] > 0.8:
                inconsistencies.append("CFL 낮은데 ES 높음")
        
        consistency_score = 1 - (len(inconsistencies) * 0.3)
        consistency_score = max(0, consistency_score)
        
        return {
            'score': consistency_score,
            'inconsistencies': inconsistencies,
            'passed': consistency_score > 0.7
        }
    
    def _calculate_audio_quality_score(self, checks: Dict) -> float:
        """오디오 품질 점수 계산"""
        
        weights = {
            'duration': 0.15,
            'sample_rate': 0.15,
            'snr': 0.25,
            'clipping': 0.20,
            'speech_ratio': 0.15,
            'noise_level': 0.10
        }
        
        score = 0
        for key, weight in weights.items():
            if key in checks and checks[key].get('passed'):
                score += weight
        
        return score
    
    def _calculate_text_quality_score(self, checks: Dict) -> float:
        """텍스트 품질 점수 계산"""
        
        passed_count = sum(1 for check in checks.values() 
                          if isinstance(check, dict) and check.get('passed'))
        total_count = len(checks)
        
        return passed_count / total_count if total_count > 0 else 0
    
    def _determine_quality_grade(self, score: float) -> str:
        """품질 등급 결정"""
        
        if score >= 0.9:
            return 'excellent'
        elif score >= 0.75:
            return 'good'
        elif score >= 0.6:
            return 'acceptable'
        elif score >= 0.4:
            return 'poor'
        else:
            return 'unacceptable'
    
    def _identify_audio_issues(self, checks: Dict) -> List[str]:
        """오디오 문제 식별"""
        
        issues = []
        
        for key, check in checks.items():
            if not check.get('passed'):
                if key == 'duration':
                    issues.append("오디오 길이 부적절")
                elif key == 'snr':
                    issues.append("신호 대 잡음비 낮음")
                elif key == 'clipping':
                    issues.append("클리핑 감지됨")
                elif key == 'speech_ratio':
                    issues.append("음성 비율 낮음")
        
        return issues
    
    def _identify_text_issues(self, checks: Dict) -> List[str]:
        """텍스트 문제 식별"""
        
        issues = []
        
        if not checks.get('word_count', {}).get('passed'):
            issues.append("텍스트 길이 부적절")
        
        if not checks.get('unique_words', {}).get('passed'):
            issues.append("어휘 다양성 부족")
        
        if not checks.get('coherence', {}).get('passed'):
            issues.append("일관성 부족")
        
        return issues
    
    def _identify_indicator_issues(
        self,
        checks: Dict,
        consistency: Dict
    ) -> List[str]:
        """지표 문제 식별"""
        
        issues = []
        
        for key, check in checks.items():
            if not check['passed']:
                issues.append(f"{key} 지표 이상")
        
        if not consistency['passed']:
            issues.extend(consistency['inconsistencies'])
        
        return issues
    
    def _generate_audio_recommendations(self, checks: Dict) -> List[str]:
        """오디오 개선 권고사항"""
        
        recommendations = []
        
        if not checks.get('snr', {}).get('passed'):
            recommendations.append("조용한 환경에서 재녹음")
        
        if not checks.get('clipping', {}).get('passed'):
            recommendations.append("녹음 볼륨 조절 필요")
        
        if not checks.get('speech_ratio', {}).get('passed'):
            recommendations.append("더 많은 발화 필요")
        
        return recommendations
    
    def _generate_text_recommendations(self, checks: Dict) -> List[str]:
        """텍스트 개선 권고사항"""
        
        recommendations = []
        
        if not checks.get('word_count', {}).get('passed'):
            recommendations.append("더 충분한 대화 필요")
        
        if not checks.get('coherence', {}).get('passed'):
            recommendations.append("명확한 의사표현 유도")
        
        return recommendations
    
    def _generate_indicator_recommendations(self, checks: Dict) -> List[str]:
        """지표 개선 권고사항"""
        
        recommendations = []
        
        failed_indicators = [k for k, v in checks.items() if not v['passed']]
        
        if failed_indicators:
            recommendations.append(f"재측정 필요: {', '.join(failed_indicators)}")
        
        return recommendations