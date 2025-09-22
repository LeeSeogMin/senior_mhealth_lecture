"""
AI 기반 화자 식별 모듈
GPT-4o를 사용한 지능형 화자 판별
"""

import os
import logging
from typing import Dict, List, Any, Optional
from openai import AsyncOpenAI  # 비동기 클라이언트 사용
import json

logger = logging.getLogger(__name__)

class AISpeakerIdentifier:
    """AI 기반 시니어 화자 식별기"""
    
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.getenv('OPENAI_API_KEY')
        # 비동기 클라이언트 사용
        self.client = AsyncOpenAI(api_key=self.api_key) if self.api_key else None
        # 모델 설정 - gpt-4o 사용
        self.model = "gpt-4o"
        logger.info(f"AI 화자 식별기 초기화: 모델={self.model}")
    
    async def identify(
        self,
        segments: List[Dict],
        user_profile: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """
        GPT-4o를 사용한 화자 식별
        폴백 없이 AI 판단만 사용
        """
        
        if not segments:
            logger.warning("세그먼트가 없어 화자 식별 불가")
            return {
                'status': 'no_segments',
                'senior_speaker_id': None,
                'confidence': 0.0,
                'reasoning': '대화 내용 없음'
            }
        
        if not self.client:
            logger.error("OpenAI API 키가 설정되지 않음")
            # 폴백 없이 첫 번째 화자 선택
            first_speaker = segments[0].get('speaker_id', 'unknown')
            return {
                'status': 'no_api',
                'senior_speaker_id': first_speaker,
                'confidence': 0.1,
                'reasoning': 'API 키 없음 - 기본 선택'
            }
        
        # 화자별 대화 정리
        speaker_conversations = self._prepare_conversations(segments)
        
        # GPT-4o로 판단 요청
        identification = await self._ai_identify(speaker_conversations, user_profile)
        
        return identification
    
    def _prepare_conversations(self, segments: List[Dict]) -> Dict[str, str]:
        """화자별 대화 텍스트 정리"""
        
        conversations = {}
        for seg in segments:
            speaker_id = seg.get('speaker_id', 'unknown')
            if speaker_id not in conversations:
                conversations[speaker_id] = []
            conversations[speaker_id].append(seg.get('text', ''))
        
        # 각 화자의 전체 대화 생성 (최대 1000자)
        result = {}
        for speaker_id, texts in conversations.items():
            full_text = ' '.join(texts)
            result[speaker_id] = full_text[:1000]  # 토큰 절약
            logger.info(f"화자 {speaker_id}: {len(texts)}개 발화, {len(full_text)}자")
        
        return result
    
    async def _ai_identify(
        self, 
        conversations: Dict[str, str],
        user_profile: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """GPT-4o를 사용한 시니어 화자 판별"""
        
        # 프로필 정보 준비
        profile_context = ""
        if user_profile:
            senior = user_profile.get('senior', {})
            caregiver = user_profile.get('user', {})
            
            if senior:
                profile_context = f"""
시니어 정보:
- 나이: {senior.get('age', '?')}세
- 성별: {senior.get('gender', '?')}
- 관계: {senior.get('relationship', '?')}

보호자 정보:
- 나이: {caregiver.get('age', '?')}세
- 성별: {caregiver.get('gender', '?')}
"""
        
        # 대화 내용 준비
        conversation_text = "\n\n".join([
            f"화자 {speaker_id}:\n{text}"
            for speaker_id, text in conversations.items()
        ])
        
        # GPT-4o 프롬프트 (간결하게)
        prompt = f"""대화를 분석하여 시니어(노인) 화자를 찾아주세요.

{profile_context}

판별 기준:
1. 존댓말을 받는 사람
2. 어머님, 아버님, 할머니 등 호칭
3. 건강/약 관련 대화

대화:
{conversation_text}

JSON 형식 응답:
{{"senior_speaker_id": "화자ID", "confidence": 0.8, "reasoning": "이유"}}"""
        
        try:
            logger.info(f"AI 판별 요청: 모델={self.model}")
            
            # 비동기 클라이언트 직접 사용
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "대화에서 시니어를 찾는 전문가"},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.3,
                max_tokens=150,
                response_format={"type": "json_object"}  # JSON 응답 강제
            )
            
            result_text = response.choices[0].message.content
            result = json.loads(result_text)
            
            logger.info(f"AI 판별 완료: {result}")
            
            # 필수 필드 검증
            if 'senior_speaker_id' not in result:
                raise ValueError("AI 화자 식별 실패: senior_speaker_id가 없습니다")
            if 'confidence' not in result:
                raise ValueError("AI 화자 식별 실패: confidence가 없습니다")
            
            return {
                'status': 'success',
                'senior_speaker_id': result['senior_speaker_id'],
                'confidence': float(result['confidence']),
                'reasoning': result.get('reasoning', 'AI 판단'),
                'method': 'ai_gpt4o'
            }
            
        except Exception as e:
            logger.error(f"AI 판별 오류: {e}")
            # 폴백 없이 첫 번째 화자 선택
            first_speaker = list(conversations.keys())[0] if conversations else 'unknown'
            
            return {
                'status': 'error',
                'senior_speaker_id': first_speaker,
                'confidence': 0.2,
                'reasoning': f'AI 오류: {str(e)}',
                'method': 'error_default'
            }