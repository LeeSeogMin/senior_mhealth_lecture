"""
Crisis Detection Chain
위기 상황 감지 체인 - 3-5초 내 긴급 상황 감지
"""

import asyncio
import os
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime
import json

from .base_step import BaseChainStep, CrisisResult

# OpenAI와 Google AI 모듈 임포트
try:
    from openai import AsyncOpenAI
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False
    
try:
    import google.generativeai as genai
    GEMINI_AVAILABLE = True
except ImportError:
    GEMINI_AVAILABLE = False

logger = logging.getLogger(__name__)


class CrisisDetector(BaseChainStep):
    """위기 감지 체인 단계"""
    
    # 위기 감지 키워드 패턴
    CRISIS_KEYWORDS = {
        'suicide': ['자살', '죽고 싶', '삶을 끝내', '더 이상 살고 싶지 않', '목숨을 끊'],
        'self_harm': ['자해', '상처를 내', '아프게 하고 싶'],
        'severe_depression': ['너무 우울', '삶이 무의미', '아무것도 하고 싶지 않', '절망적'],
        'emergency_medical': ['심장이 아파', '숨을 못 쉬', '가슴 통증', '머리가 너무 아파'],
        'severe_anxiety': ['공황', '죽을 것 같', '미칠 것 같']
    }
    
    def __init__(self, model_type: str = 'gemini'):
        """
        Args:
            model_type: 사용할 모델 ('gemini' 또는 'openai')
        """
        super().__init__(name="crisis_detection", timeout=5.0)  # 5초 타임아웃
        self.is_critical = True  # 위기 감지는 critical 단계
        self.model_type = model_type
        
        # 모델 초기화
        if model_type == 'openai' and OPENAI_AVAILABLE:
            self.client = AsyncOpenAI(api_key=os.getenv('OPENAI_API_KEY'))
            self.model = 'gpt-4o'
        elif model_type == 'gemini' and GEMINI_AVAILABLE:
            genai.configure(api_key=os.getenv('GEMINI_API_KEY'))
            self.model = genai.GenerativeModel('gemini-pro')
        else:
            logger.warning(f"Model {model_type} not available, using keyword detection only")
            self.model = None
    
    async def process(self, audio_data: Any, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        위기 상황 감지 처리
        
        Args:
            audio_data: 오디오 데이터 또는 경로
            context: 실행 컨텍스트 (transcript 포함 필요)
            
        Returns:
            위기 감지 결과가 추가된 컨텍스트
        """
        start_time = datetime.now()
        
        # transcript 확인
        transcript = context.get('transcript', '')
        if not transcript:
            logger.warning("No transcript available for crisis detection")
            context['crisis'] = CrisisResult(
                severity='unknown',
                confidence=0.0,
                detected_patterns=[],
                message="No transcript available"
            ).to_dict()
            return context
        
        try:
            # 타임아웃 설정으로 빠른 감지
            crisis_result = await asyncio.wait_for(
                self._detect_crisis(transcript),
                timeout=self.timeout
            )
            
            # 처리 시간 기록
            processing_time = (datetime.now() - start_time).total_seconds()
            crisis_result['processing_time'] = processing_time
            
            context['crisis'] = crisis_result
            
            # 위기 상황 감지 시 즉시 알림
            if crisis_result['severity'] in ['critical', 'high']:
                await self._trigger_alert(crisis_result, context)
            
            logger.info(f"Crisis detection completed in {processing_time:.2f}s: {crisis_result['severity']}")
            
        except asyncio.TimeoutError:
            logger.error("Crisis detection timeout")
            context['crisis'] = CrisisResult(
                severity='timeout',
                confidence=0.0,
                detected_patterns=[],
                message="Detection timeout - using fallback"
            ).to_dict()
        except Exception as e:
            context = await self.handle_error(e, context)
            context['crisis'] = CrisisResult(
                severity='error',
                confidence=0.0,
                detected_patterns=[],
                message=str(e)
            ).to_dict()
        
        return context
    
    async def _detect_crisis(self, transcript: str) -> Dict[str, Any]:
        """
        실제 위기 감지 로직
        
        Args:
            transcript: 텍스트 전사
            
        Returns:
            위기 감지 결과
        """
        # 1단계: 키워드 기반 빠른 감지
        keyword_patterns = self._detect_keywords(transcript)
        
        # 긴급 키워드 발견 시 즉시 반환
        if any(pattern in ['suicide', 'self_harm'] for pattern, _ in keyword_patterns):
            return CrisisResult(
                severity='critical',
                confidence=0.95,
                detected_patterns=[p[0] for p in keyword_patterns],
                immediate_action_required=True,
                message="Critical keywords detected - immediate intervention required"
            ).to_dict()
        
        # 2단계: AI 모델 기반 상세 분석 (모델 사용 가능한 경우)
        if self.model:
            try:
                ai_result = await self._ai_analysis(transcript, keyword_patterns)
                return ai_result
            except Exception as e:
                logger.error(f"AI analysis failed: {e}")
        
        # 3단계: 키워드 기반 fallback
        if keyword_patterns:
            severity = self._determine_severity(keyword_patterns)
            return CrisisResult(
                severity=severity,
                confidence=0.7,
                detected_patterns=[p[0] for p in keyword_patterns],
                immediate_action_required=(severity == 'high'),
                message="Keyword-based detection"
            ).to_dict()
        
        return CrisisResult(
            severity='none',
            confidence=0.8,
            detected_patterns=[],
            immediate_action_required=False,
            message="No crisis indicators detected"
        ).to_dict()
    
    def _detect_keywords(self, text: str) -> List[tuple]:
        """
        키워드 기반 위기 패턴 감지
        
        Args:
            text: 검사할 텍스트
            
        Returns:
            감지된 패턴과 키워드 튜플 리스트
        """
        detected = []
        text_lower = text.lower()
        
        for pattern, keywords in self.CRISIS_KEYWORDS.items():
            for keyword in keywords:
                if keyword in text_lower:
                    detected.append((pattern, keyword))
        
        return detected
    
    async def _ai_analysis(self, transcript: str, keyword_patterns: List[tuple]) -> Dict[str, Any]:
        """
        AI 모델을 사용한 상세 분석
        
        Args:
            transcript: 텍스트 전사
            keyword_patterns: 감지된 키워드 패턴
            
        Returns:
            AI 분석 결과
        """
        prompt = f"""
        다음 대화를 분석하여 정신건강 위기 상황을 평가해주세요.
        즉각적인 개입이 필요한 위험 신호를 우선적으로 확인하세요.
        
        대화 내용:
        {transcript[:1000]}  # 토큰 절약을 위해 처음 1000자만
        
        다음 형식으로 JSON 응답:
        {{
            "severity": "critical/high/medium/low/none",
            "confidence": 0.0-1.0,
            "patterns": ["pattern1", "pattern2"],
            "immediate_action": true/false,
            "reasoning": "간단한 이유"
        }}
        """
        
        try:
            if self.model_type == 'openai' and OPENAI_AVAILABLE:
                response = await self._openai_analysis(prompt)
            elif self.model_type == 'gemini' and GEMINI_AVAILABLE:
                response = await self._gemini_analysis(prompt)
            else:
                raise ValueError("No AI model available")
            
            # JSON 파싱
            result_data = json.loads(response)
            
            return CrisisResult(
                severity=result_data.get('severity', 'unknown'),
                confidence=result_data.get('confidence', 0.5),
                detected_patterns=result_data.get('patterns', []) + [p[0] for p in keyword_patterns],
                immediate_action_required=result_data.get('immediate_action', False),
                message=result_data.get('reasoning', '')
            ).to_dict()
            
        except Exception as e:
            logger.error(f"AI analysis error: {e}")
            # Fallback to keyword results
            severity = self._determine_severity(keyword_patterns)
            return CrisisResult(
                severity=severity,
                confidence=0.6,
                detected_patterns=[p[0] for p in keyword_patterns],
                immediate_action_required=(severity in ['critical', 'high']),
                message="AI analysis failed, keyword detection used"
            ).to_dict()
    
    async def _openai_analysis(self, prompt: str) -> str:
        """OpenAI API 호출"""
        if not OPENAI_AVAILABLE:
            raise ValueError("OpenAI not available")

        response = await self.client.chat.completions.create(
            model=self.model,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.3,
            max_tokens=200
        )
        return response.choices[0].message.content
    
    async def _gemini_analysis(self, prompt: str) -> str:
        """Google Gemini API 호출"""
        if not GEMINI_AVAILABLE:
            raise ValueError("Gemini not available")
            
        response = await asyncio.to_thread(
            self.model.generate_content,
            prompt
        )
        return response.text
    
    def _determine_severity(self, patterns: List[tuple]) -> str:
        """
        패턴 기반 위험도 결정
        
        Args:
            patterns: 감지된 패턴 리스트
            
        Returns:
            위험도 수준
        """
        pattern_types = [p[0] for p in patterns]
        
        if 'suicide' in pattern_types:
            return 'critical'
        elif 'self_harm' in pattern_types or 'emergency_medical' in pattern_types:
            return 'high'
        elif 'severe_depression' in pattern_types or 'severe_anxiety' in pattern_types:
            return 'medium'
        else:
            return 'low'
    
    async def _trigger_alert(self, crisis_result: Dict[str, Any], context: Dict[str, Any]):
        """
        위기 상황 알림 트리거
        
        Args:
            crisis_result: 위기 감지 결과
            context: 실행 컨텍스트
        """
        logger.critical(f"CRISIS ALERT: {crisis_result['severity']} - {crisis_result['message']}")
        
        # TODO: 실제 알림 시스템 연동
        # - Firebase Cloud Messaging
        # - SMS/Email 알림
        # - 의료진 알림 시스템
        
        context['alert_triggered'] = {
            'timestamp': datetime.now().isoformat(),
            'severity': crisis_result['severity'],
            'notified': True
        }