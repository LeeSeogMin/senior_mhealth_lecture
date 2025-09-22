"""
음성 분석 데이터 모델
제5강: Cloud Run과 FastAPI로 확장된 백엔드 구현
"""

from pydantic import BaseModel, Field, validator
from typing import Optional, Dict, Any, List
from datetime import datetime
import uuid


class VoiceAnalysisRequest(BaseModel):
    """음성 분석 요청 모델"""
    audio_url: Optional[str] = Field(None, description="오디오 파일 URL 또는 Storage 경로")
    analysis_type: str = Field(default="comprehensive", description="분석 타입")
    user_id: Optional[str] = Field(None, description="사용자 ID")
    call_id: Optional[str] = Field(None, description="통화 ID")
    senior_id: Optional[str] = Field(None, description="시니어 ID")
    metadata: Optional[Dict[str, Any]] = Field(default_factory=dict, description="추가 메타데이터")
    
    @validator('analysis_type')
    def validate_analysis_type(cls, v):
        allowed_types = ['comprehensive', 'emotion_only', 'transcription_only', 'quick']
        if v not in allowed_types:
            raise ValueError(f'analysis_type must be one of {allowed_types}')
        return v
    
    class Config:
        schema_extra = {
            "example": {
                "audio_url": "https://storage.googleapis.com/bucket/audio.wav",
                "analysis_type": "comprehensive",
                "user_id": "user_123",
                "call_id": "call_456",
                "senior_id": "senior_789",
                "metadata": {
                    "call_duration": 180,
                    "call_quality": "good"
                }
            }
        }


class CoreIndicator(BaseModel):
    """핵심 지표 모델"""
    value: float = Field(..., ge=0, le=1, description="지표 값 (0-1)")
    level: str = Field(..., description="수준 (low, normal, high, very_positive 등)")
    description: Optional[str] = Field(None, description="지표 설명")


class VoiceFeatures(BaseModel):
    """음성 특징 모델"""
    speech_rate: float = Field(..., description="발화 속도 (단어/분)")
    pause_frequency: float = Field(..., description="휴지 빈도")
    voice_quality: float = Field(..., ge=0, le=1, description="음성 품질 점수")
    pitch_variation: Optional[float] = Field(None, description="피치 변화량")
    volume_stability: Optional[float] = Field(None, description="볼륨 안정성")


class TranscriptionResult(BaseModel):
    """음성-텍스트 변환 결과"""
    senior_text: str = Field(..., description="시니어 발화 텍스트")
    full_text: Optional[str] = Field(None, description="전체 대화 텍스트")
    confidence: float = Field(..., ge=0, le=1, description="변환 신뢰도")
    word_count: Optional[int] = Field(None, description="단어 수")
    speaking_time: Optional[float] = Field(None, description="발화 시간(초)")


class MentalHealthAnalysis(BaseModel):
    """정신건강 분석 결과"""
    DRI: CoreIndicator = Field(..., description="우울증 위험 지표")
    SDI: CoreIndicator = Field(..., description="자살 위험 지표")  
    CFL: CoreIndicator = Field(..., description="인지 유창성 지표")
    ES: CoreIndicator = Field(..., description="감정 상태 지표")
    OV: CoreIndicator = Field(..., description="전반적 평가 지표")


class SincNetAnalysis(BaseModel):
    """SincNet 분석 결과"""
    emotion: str = Field(..., description="감지된 감정")
    stress_level: float = Field(..., ge=0, le=1, description="스트레스 수준")
    fatigue_level: float = Field(..., ge=0, le=1, description="피로 수준")
    voice_health: Optional[float] = Field(None, ge=0, le=1, description="음성 건강도")


class AnalysisResults(BaseModel):
    """분석 결과 통합 모델"""
    transcription: TranscriptionResult
    mentalHealthAnalysis: MentalHealthAnalysis
    voicePatterns: VoiceFeatures
    sincnetAnalysis: Optional[SincNetAnalysis] = None
    summary: str = Field(..., description="분석 요약")
    recommendations: List[str] = Field(..., description="권장사항")
    interpretation: Optional[str] = Field(None, description="종합 해석")


class AnalysisMetadata(BaseModel):
    """분석 메타데이터"""
    analysis_type: str
    processing_time: float = Field(..., description="처리 시간(초)")
    model_version: str = Field(..., description="모델 버전")
    confidence: float = Field(..., ge=0, le=1, description="전체 신뢰도")
    mock_data: bool = Field(default=False, description="모의 데이터 여부")
    error: bool = Field(default=False, description="오류 발생 여부")
    error_message: Optional[str] = Field(None, description="오류 메시지")


class VoiceAnalysisResponse(BaseModel):
    """음성 분석 응답 모델"""
    success: bool = Field(..., description="성공 여부")
    analysis_id: str = Field(..., description="분석 ID")
    status: str = Field(..., description="상태 (completed, processing, error, disabled)")
    message: str = Field(..., description="응답 메시지")
    data: Dict[str, Any] = Field(..., description="분석 데이터")
    
    class Config:
        schema_extra = {
            "example": {
                "success": True,
                "analysis_id": "analysis_abc123",
                "status": "completed",
                "message": "음성 분석이 성공적으로 완료되었습니다",
                "data": {
                    "call_id": "call_456",
                    "results": {
                        "transcription": {
                            "senior_text": "안녕하세요, 오늘 기분이 좋습니다.",
                            "confidence": 0.95
                        },
                        "mentalHealthAnalysis": {
                            "DRI": {"value": 0.2, "level": "low"},
                            "ES": {"value": 0.8, "level": "positive"}
                        },
                        "summary": "전반적으로 안정된 정신건강 상태"
                    },
                    "metadata": {
                        "processing_time": 2.5,
                        "confidence": 0.87
                    }
                }
            }
        }


class VoiceUploadRequest(BaseModel):
    """음성 파일 업로드 요청"""
    filename: str = Field(..., description="파일명")
    content_type: str = Field(..., description="파일 타입")
    user_id: Optional[str] = Field(None, description="사용자 ID")
    senior_id: Optional[str] = Field(None, description="시니어 ID")
    
    @validator('content_type')
    def validate_content_type(cls, v):
        allowed_types = [
            'audio/wav', 'audio/mp3', 'audio/mpeg', 
            'audio/flac', 'audio/m4a', 'audio/ogg'
        ]
        if v not in allowed_types:
            raise ValueError(f'Unsupported content type: {v}')
        return v


class VoiceUploadResponse(BaseModel):
    """음성 파일 업로드 응답"""
    success: bool
    message: str
    upload_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    storage_url: Optional[str] = Field(None, description="저장된 파일 URL")
    filename: str
    file_size: Optional[int] = Field(None, description="파일 크기(bytes)")
    content_type: str
    
    class Config:
        schema_extra = {
            "example": {
                "success": True,
                "message": "파일 업로드가 완료되었습니다",
                "upload_id": "upload_123abc",
                "storage_url": "gs://bucket/uploads/audio.wav",
                "filename": "recording.wav",
                "file_size": 1024000,
                "content_type": "audio/wav"
            }
        }


class AnalysisStatus(BaseModel):
    """분석 상태 모델"""
    analysis_id: str
    status: str = Field(..., description="pending, processing, completed, failed")
    progress: int = Field(..., ge=0, le=100, description="진행률 (%)")
    message: str
    started_at: Optional[datetime] = Field(None, description="시작 시간")
    completed_at: Optional[datetime] = Field(None, description="완료 시간")
    error_message: Optional[str] = Field(None, description="오류 메시지")
    
    class Config:
        schema_extra = {
            "example": {
                "analysis_id": "analysis_abc123",
                "status": "completed",
                "progress": 100,
                "message": "분석이 완료되었습니다",
                "completed_at": "2024-01-15T10:30:00Z"
            }
        }