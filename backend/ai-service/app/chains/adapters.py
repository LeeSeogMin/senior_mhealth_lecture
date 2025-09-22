"""
Adapters for integrating existing analyzers with chain system
기존 분석기를 체인 시스템과 통합하기 위한 어댑터
"""

import logging
from typing import Dict, Any, Optional
from datetime import datetime
import asyncio
import sys
from pathlib import Path

# 분석 모듈 경로 추가
sys.path.append(str(Path(__file__).parent.parent.parent.parent / "libraries" / "voice_analysis"))

from .base_step import BaseChainStep

logger = logging.getLogger(__name__)


class VoiceAnalysisAdapter(BaseChainStep):
    """음성 분석기 어댑터 (30% 가중치)"""
    
    def __init__(self, existing_analyzer=None):
        """
        Args:
            existing_analyzer: 기존 음성 분석기 인스턴스
        """
        super().__init__(name="voice_analysis", timeout=30.0)
        self.analyzer = existing_analyzer
        self.weight = 0.3  # 30% 가중치
        
    async def process(self, audio_data: Any, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        음성 특징 분석 처리
        
        Args:
            audio_data: 오디오 데이터 또는 경로
            context: 실행 컨텍스트
            
        Returns:
            음성 분석 결과가 추가된 컨텍스트
        """
        try:
            logger.info("Starting voice analysis")
            start_time = datetime.now()
            
            # 기존 분석기가 없으면 동적 로드
            if not self.analyzer:
                from analysis.core.voice_analyzer import VoiceAnalyzer
                self.analyzer = VoiceAnalyzer()
            
            # 음성 분석 실행 (비동기 래핑)
            result = await asyncio.to_thread(
                self.analyzer.analyze,
                audio_data
            )
            
            # 결과를 컨텍스트에 저장
            context['voice_features'] = {
                'result': result,
                'weight': self.weight,
                'processing_time': (datetime.now() - start_time).total_seconds(),
                'timestamp': datetime.now().isoformat()
            }
            
            # 주요 특징 추출
            if isinstance(result, dict):
                context['voice_summary'] = {
                    'pitch_variation': result.get('pitch_variation'),
                    'speech_rate': result.get('speech_rate'),
                    'pause_ratio': result.get('pause_ratio'),
                    'energy_level': result.get('energy_level')
                }
            
            logger.info(f"Voice analysis completed in {context['voice_features']['processing_time']:.2f}s")
            
        except Exception as e:
            logger.error(f"Voice analysis failed: {e}")
            context = await self.handle_error(e, context)
            context['voice_features'] = {
                'error': str(e),
                'weight': self.weight,
                'timestamp': datetime.now().isoformat()
            }
        
        return context


class TextAnalysisAdapter(BaseChainStep):
    """텍스트 감정 분석 어댑터 (40% 가중치)"""
    
    def __init__(self, existing_analyzer=None):
        """
        Args:
            existing_analyzer: 기존 텍스트 분석기 인스턴스
        """
        super().__init__(name="text_analysis", timeout=20.0)
        self.analyzer = existing_analyzer
        self.weight = 0.4  # 40% 가중치
        
    async def process(self, audio_data: Any, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        텍스트 감정 분석 처리
        
        Args:
            audio_data: 오디오 데이터 또는 경로
            context: 실행 컨텍스트 (transcript 필요)
            
        Returns:
            텍스트 분석 결과가 추가된 컨텍스트
        """
        try:
            logger.info("Starting text analysis")
            start_time = datetime.now()
            
            # transcript 확인
            transcript = context.get('transcript', '')
            if not transcript:
                logger.warning("No transcript available for text analysis")
                context['text_analysis'] = {
                    'error': 'No transcript available',
                    'weight': self.weight,
                    'timestamp': datetime.now().isoformat()
                }
                return context
            
            # 기존 분석기가 없으면 동적 로드
            if not self.analyzer:
                from analysis.core.text_analyzer import TextAnalyzer
                self.analyzer = TextAnalyzer()
            
            # 텍스트 분석 실행 (비동기 래핑)
            result = await asyncio.to_thread(
                self.analyzer.analyze,
                transcript
            )
            
            # 결과를 컨텍스트에 저장
            context['text_analysis'] = {
                'result': result,
                'weight': self.weight,
                'processing_time': (datetime.now() - start_time).total_seconds(),
                'timestamp': datetime.now().isoformat()
            }
            
            # 주요 감정 추출
            if isinstance(result, dict):
                context['text_summary'] = {
                    'sentiment': result.get('sentiment'),
                    'emotions': result.get('emotions', {}),
                    'keywords': result.get('keywords', []),
                    'mental_state': result.get('mental_state')
                }
            
            logger.info(f"Text analysis completed in {context['text_analysis']['processing_time']:.2f}s")
            
        except Exception as e:
            logger.error(f"Text analysis failed: {e}")
            context = await self.handle_error(e, context)
            context['text_analysis'] = {
                'error': str(e),
                'weight': self.weight,
                'timestamp': datetime.now().isoformat()
            }
        
        return context


class SincNetAdapter(BaseChainStep):
    """SincNet 딥러닝 분석 어댑터 (30% 가중치)"""
    
    def __init__(self, existing_analyzer=None):
        """
        Args:
            existing_analyzer: 기존 SincNet 분석기 인스턴스
        """
        super().__init__(name="sincnet_analysis", timeout=40.0)
        self.analyzer = existing_analyzer
        self.weight = 0.3  # 30% 가중치
        
    async def process(self, audio_data: Any, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        SincNet 딥러닝 분석 처리
        
        Args:
            audio_data: 오디오 데이터 또는 경로
            context: 실행 컨텍스트
            
        Returns:
            SincNet 분석 결과가 추가된 컨텍스트
        """
        try:
            logger.info("Starting SincNet analysis")
            start_time = datetime.now()
            
            # 위기 상황에서는 SincNet 스킵 가능
            if context.get('crisis', {}).get('severity') in ['critical', 'high']:
                logger.info("Skipping SincNet due to crisis situation")
                context['sincnet_analysis'] = {
                    'skipped': True,
                    'reason': 'Crisis situation detected',
                    'weight': self.weight,
                    'timestamp': datetime.now().isoformat()
                }
                return context
            
            # 기존 분석기가 없으면 동적 로드
            if not self.analyzer:
                from analysis.sincnet.sincnet_analyzer import SincNetAnalyzer
                self.analyzer = SincNetAnalyzer()
            
            # SincNet 분석 실행 (비동기 래핑)
            result = await asyncio.to_thread(
                self.analyzer.analyze,
                audio_data
            )
            
            # 결과를 컨텍스트에 저장
            context['sincnet_analysis'] = {
                'result': result,
                'weight': self.weight,
                'processing_time': (datetime.now() - start_time).total_seconds(),
                'timestamp': datetime.now().isoformat()
            }
            
            # 주요 특징 추출
            if isinstance(result, dict):
                context['sincnet_summary'] = {
                    'depression_score': result.get('depression_score'),
                    'anxiety_score': result.get('anxiety_score'),
                    'stress_level': result.get('stress_level'),
                    'confidence': result.get('confidence')
                }
            
            logger.info(f"SincNet analysis completed in {context['sincnet_analysis']['processing_time']:.2f}s")
            
        except Exception as e:
            logger.error(f"SincNet analysis failed: {e}")
            context = await self.handle_error(e, context)
            context['sincnet_analysis'] = {
                'error': str(e),
                'weight': self.weight,
                'timestamp': datetime.now().isoformat()
            }
        
        return context


class TranscriptionAdapter(BaseChainStep):
    """STT 전사 어댑터"""
    
    def __init__(self, stt_service=None):
        """
        Args:
            stt_service: STT 서비스 인스턴스
        """
        super().__init__(name="transcription", timeout=15.0)
        self.stt_service = stt_service
        self.is_critical = True  # 전사는 필수 단계
        
    async def process(self, audio_data: Any, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        음성을 텍스트로 전사
        
        Args:
            audio_data: 오디오 데이터 또는 경로
            context: 실행 컨텍스트
            
        Returns:
            전사 결과가 추가된 컨텍스트
        """
        try:
            logger.info("Starting transcription")
            start_time = datetime.now()
            
            # 기존 STT 서비스가 없으면 동적 로드
            if not self.stt_service:
                from analysis.core.speech_to_text import SpeechToText
                self.stt_service = SpeechToText()
            
            # 전사 실행 (비동기 래핑)
            transcript = await asyncio.to_thread(
                self.stt_service.transcribe,
                audio_data
            )
            
            # 결과를 컨텍스트에 저장
            context['transcript'] = transcript
            context['transcription_metadata'] = {
                'length': len(transcript),
                'word_count': len(transcript.split()),
                'processing_time': (datetime.now() - start_time).total_seconds(),
                'timestamp': datetime.now().isoformat()
            }
            
            logger.info(f"Transcription completed in {context['transcription_metadata']['processing_time']:.2f}s")
            
        except Exception as e:
            logger.error(f"Transcription failed: {e}")
            context = await self.handle_error(e, context)
            # 전사 실패는 치명적이므로 빈 transcript 제공
            context['transcript'] = ''
            context['transcription_metadata'] = {
                'error': str(e),
                'timestamp': datetime.now().isoformat()
            }
        
        return context


class BasicScreeningAdapter(BaseChainStep):
    """기본 정신건강 스크리닝 어댑터"""
    
    def __init__(self):
        """초기화"""
        super().__init__(name="basic_screening", timeout=10.0)
        
    async def process(self, audio_data: Any, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        기본 정신건강 스크리닝
        
        Args:
            audio_data: 오디오 데이터
            context: 실행 컨텍스트
            
        Returns:
            스크리닝 결과가 추가된 컨텍스트
        """
        try:
            logger.info("Starting basic screening")
            
            # 위기 상황이면 간소화된 스크리닝
            if context.get('crisis', {}).get('severity') == 'critical':
                context['basic_screening'] = {
                    'status': 'crisis_mode',
                    'priority': 'immediate_intervention',
                    'timestamp': datetime.now().isoformat()
                }
                return context
            
            # 기본 지표 계산 (간단한 규칙 기반)
            mental_health_score = 0
            risk_factors = []
            
            # 음성 특징 기반 평가
            if 'voice_summary' in context:
                voice = context['voice_summary']
                if voice.get('speech_rate', 1.0) < 0.8:
                    mental_health_score += 20
                    risk_factors.append('slow_speech')
                if voice.get('pause_ratio', 0) > 0.3:
                    mental_health_score += 15
                    risk_factors.append('long_pauses')
            
            # 텍스트 감정 기반 평가
            if 'text_summary' in context:
                text = context['text_summary']
                if text.get('sentiment') == 'negative':
                    mental_health_score += 30
                    risk_factors.append('negative_sentiment')
                emotions = text.get('emotions', {})
                if emotions.get('sadness', 0) > 0.5:
                    mental_health_score += 20
                    risk_factors.append('high_sadness')
            
            # 위험 수준 결정
            if mental_health_score >= 70:
                risk_level = 'high'
            elif mental_health_score >= 40:
                risk_level = 'medium'
            else:
                risk_level = 'low'
            
            context['basic_screening'] = {
                'mental_health_score': mental_health_score,
                'risk_level': risk_level,
                'risk_factors': risk_factors,
                'timestamp': datetime.now().isoformat()
            }
            
            logger.info(f"Basic screening completed: {risk_level} risk")
            
        except Exception as e:
            logger.error(f"Basic screening failed: {e}")
            context = await self.handle_error(e, context)
            context['basic_screening'] = {
                'error': str(e),
                'timestamp': datetime.now().isoformat()
            }
        
        return context