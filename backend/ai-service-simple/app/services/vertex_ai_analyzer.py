"""
Vertex AI Gemini API 기반 텍스트 분석 서비스
GCP 내부에서 제공하는 Vertex AI의 Gemini 모델 사용
"""

import os
import json
import logging
from typing import Dict, Any
from datetime import datetime
import vertexai
from vertexai.generative_models import GenerativeModel, ChatSession
from google.cloud import aiplatform
from pydantic import BaseModel, Field

# 로깅 설정
logger = logging.getLogger(__name__)


class AnalysisRequest(BaseModel):
    """분석 요청 모델"""
    text: str = Field(..., description="분석할 텍스트")
    user_id: str = Field(default="anonymous", description="사용자 ID")
    session_id: str = Field(default="", description="세션 ID")


class AnalysisResponse(BaseModel):
    """분석 응답 모델"""
    depression_score: float = Field(..., ge=0, le=100, description="우울도 점수 (0-100)")
    anxiety_score: float = Field(..., ge=0, le=100, description="불안도 점수 (0-100)")
    cognitive_score: float = Field(..., ge=0, le=100, description="인지기능 점수 (0-100)")
    emotional_state: str = Field(..., description="감정 상태")
    key_concerns: list[str] = Field(default_factory=list, description="주요 우려사항")
    recommendations: list[str] = Field(default_factory=list, description="권장사항")
    confidence: float = Field(..., ge=0, le=1, description="분석 신뢰도")
    timestamp: str = Field(default_factory=lambda: datetime.utcnow().isoformat())


class VertexAIAnalyzer:
    """Vertex AI Gemini를 사용한 텍스트 기반 정신건강 분석기"""

    def __init__(self):
        """Vertex AI 분석기 초기화"""
        # GCP 프로젝트 설정
        project_id = os.getenv('GCP_PROJECT_ID')
        location = os.getenv('GCP_LOCATION', 'asia-northeast3')  # 서울 리전

        if not project_id:
            raise ValueError("GCP_PROJECT_ID 환경변수가 설정되지 않았습니다")

        # Vertex AI 초기화
        vertexai.init(project=project_id, location=location)

        # Gemini 모델 초기화
        # Vertex AI에서 사용 가능한 최신 모델 사용
        self.model = GenerativeModel(
            model_name="gemini-1.5-flash",  # 또는 "gemini-1.5-pro"
            generation_config={
                'temperature': 0.7,
                'top_p': 0.95,
                'top_k': 40,
                'max_output_tokens': 1024,
            }
        )

        logger.info(f"Vertex AI Gemini 분석기 초기화 완료 - 프로젝트: {project_id}, 리전: {location}")

    def _build_prompt(self, text: str) -> str:
        """분석용 프롬프트 생성"""
        return f"""
        다음 텍스트를 분석하여 사용자의 정신건강 상태를 평가해주세요.
        화자 구분 없이 전체 내용을 종합적으로 분석합니다.

        분석할 텍스트:
        "{text}"

        다음 형식의 JSON으로 응답해주세요:
        {{
            "depression_score": 0-100 사이의 우울증 가능성 점수,
            "anxiety_score": 0-100 사이의 불안 수준 점수,
            "cognitive_score": 0-100 사이의 인지기능 점수 (100이 정상),
            "emotional_state": "현재 감정 상태 요약 (예: 안정적, 불안정, 우울, 희망적)",
            "key_concerns": ["주요 우려사항 리스트"],
            "recommendations": ["권장사항 리스트"],
            "confidence": 0-1 사이의 분석 신뢰도
        }}

        주의사항:
        - 의학적 진단이 아닌 참고 지표임을 명시
        - 점수는 객관적이고 일관되게 평가
        - 텍스트가 짧거나 애매한 경우 confidence를 낮게 설정
        - 한국어로 응답
        """

    async def analyze_mental_health(self, request: AnalysisRequest) -> AnalysisResponse:
        """텍스트 기반 정신건강 분석 수행 (비동기)"""
        try:
            logger.info(f"분석 시작 - 사용자: {request.user_id}, 텍스트 길이: {len(request.text)}")

            # 텍스트가 너무 짧은 경우
            if len(request.text) < 10:
                return AnalysisResponse(
                    depression_score=0,
                    anxiety_score=0,
                    cognitive_score=100,
                    emotional_state="분석 불가",
                    key_concerns=["텍스트가 너무 짧음"],
                    recommendations=["더 자세한 설명이 필요합니다"],
                    confidence=0.1
                )

            # 프롬프트 생성
            prompt = self._build_prompt(request.text)

            # Vertex AI Gemini API 호출
            response = await self.model.generate_content_async(prompt)

            # 응답 파싱
            result = self._parse_response(response.text)

            logger.info(f"분석 완료 - 신뢰도: {result.confidence}")
            return result

        except Exception as e:
            logger.error(f"분석 중 오류 발생: {str(e)}")
            # 오류 시 기본값 반환
            return AnalysisResponse(
                depression_score=0,
                anxiety_score=0,
                cognitive_score=100,
                emotional_state="분석 실패",
                key_concerns=["분석 중 오류 발생"],
                recommendations=["시스템 관리자에게 문의하세요"],
                confidence=0
            )

    def _parse_response(self, response_text: str) -> AnalysisResponse:
        """Gemini 응답을 AnalysisResponse로 파싱"""
        try:
            # JSON 부분만 추출
            start_idx = response_text.find('{')
            end_idx = response_text.rfind('}') + 1

            if start_idx == -1 or end_idx == 0:
                raise ValueError("JSON 형식을 찾을 수 없습니다")

            json_str = response_text[start_idx:end_idx]
            data = json.loads(json_str)

            # AnalysisResponse 모델로 변환
            return AnalysisResponse(
                depression_score=float(data.get('depression_score', 0)),
                anxiety_score=float(data.get('anxiety_score', 0)),
                cognitive_score=float(data.get('cognitive_score', 100)),
                emotional_state=str(data.get('emotional_state', '알 수 없음')),
                key_concerns=list(data.get('key_concerns', [])),
                recommendations=list(data.get('recommendations', [])),
                confidence=float(data.get('confidence', 0.5))
            )

        except Exception as e:
            logger.error(f"응답 파싱 오류: {str(e)}")
            # 파싱 실패 시 기본값
            return AnalysisResponse(
                depression_score=0,
                anxiety_score=0,
                cognitive_score=100,
                emotional_state="파싱 오류",
                key_concerns=["응답 형식 오류"],
                recommendations=["재시도 필요"],
                confidence=0
            )

    def analyze_mental_health_sync(self, request: AnalysisRequest) -> AnalysisResponse:
        """동기 버전의 정신건강 분석"""
        try:
            logger.info(f"동기 분석 시작 - 사용자: {request.user_id}")

            # 텍스트가 너무 짧은 경우
            if len(request.text) < 10:
                return AnalysisResponse(
                    depression_score=0,
                    anxiety_score=0,
                    cognitive_score=100,
                    emotional_state="분석 불가",
                    key_concerns=["텍스트가 너무 짧음"],
                    recommendations=["더 자세한 설명이 필요합니다"],
                    confidence=0.1
                )

            # 프롬프트 생성
            prompt = self._build_prompt(request.text)

            # Vertex AI Gemini API 호출 (동기)
            response = self.model.generate_content(prompt)

            # 응답 파싱
            result = self._parse_response(response.text)

            logger.info(f"동기 분석 완료 - 신뢰도: {result.confidence}")
            return result

        except Exception as e:
            logger.error(f"동기 분석 중 오류: {str(e)}")
            return AnalysisResponse(
                depression_score=0,
                anxiety_score=0,
                cognitive_score=100,
                emotional_state="분석 실패",
                key_concerns=["분석 중 오류 발생"],
                recommendations=["시스템 관리자에게 문의하세요"],
                confidence=0
            )

    def start_chat_session(self) -> ChatSession:
        """대화형 세션 시작 (Vertex AI의 채팅 기능 활용)"""
        chat = self.model.start_chat()
        logger.info("Vertex AI 채팅 세션 시작")
        return chat

    def analyze_with_context(self, text: str, chat_session: ChatSession) -> AnalysisResponse:
        """이전 대화 컨텍스트를 고려한 분석"""
        try:
            prompt = self._build_prompt(text)
            response = chat_session.send_message(prompt)
            return self._parse_response(response.text)
        except Exception as e:
            logger.error(f"컨텍스트 분석 중 오류: {str(e)}")
            return AnalysisResponse(
                depression_score=0,
                anxiety_score=0,
                cognitive_score=100,
                emotional_state="분석 실패",
                key_concerns=["분석 중 오류 발생"],
                recommendations=["시스템 관리자에게 문의하세요"],
                confidence=0
            )