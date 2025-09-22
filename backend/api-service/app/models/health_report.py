from pydantic import BaseModel, Field, validator
from typing import Optional, List, Dict, Any
from datetime import datetime, date
from enum import Enum
import uuid

class PeriodType(str, Enum):
    WEEKLY = "weekly"
    MONTHLY = "monthly"
    QUARTERLY = "quarterly"

class AnalysisType(str, Enum):
    VOICE_ANALYSIS = "voice_analysis"
    EMOTION_DETECTION = "emotion_detection"
    DEPRESSION_SCREENING = "depression_screening"
    TREND_ANALYSIS = "trend_analysis"

class HealthReportRequest(BaseModel):
    senior_id: str = Field(..., description="시니어 고유 ID")
    period: PeriodType = Field(..., description="리포트 기간")
    include_details: bool = Field(True, description="상세 정보 포함 여부")
    analysis_type: Optional[AnalysisType] = Field(None, description="분석 유형")
    
    class Config:
        schema_extra = {
            "example": {
                "senior_id": "senior_001",
                "period": "monthly",
                "include_details": True,
                "analysis_type": "depression_screening"
            }
        }

# 건강 지표 모델
class HealthIndicator(BaseModel):
    """건강 지표 데이터 모델"""
    name: str = Field(..., description="지표 명")
    value: float = Field(..., description="지표 값")
    unit: str = Field(..., description="단위")
    status: str = Field(..., description="상태 (normal, warning, critical)")
    trend: Optional[str] = Field(None, description="추세 (improving, stable, declining)")

class MentalHealthScore(BaseModel):
    """정신건강 점수 모델"""
    depression_risk: float = Field(..., ge=0, le=1, description="우울증 위험도 (0-1)")
    anxiety_level: float = Field(..., ge=0, le=1, description="불안 수준 (0-1)")
    stress_level: float = Field(..., ge=0, le=1, description="스트레스 수준 (0-1)")
    overall_mood: str = Field(..., description="전반적 기분 상태")
    confidence_score: float = Field(..., ge=0, le=1, description="분석 신뢰도")

class VoiceAnalysisResult(BaseModel):
    """음성 분석 결과 모델"""
    analysis_id: str
    call_duration: float = Field(..., description="통화 시간(초)")
    speech_rate: float = Field(..., description="발화 속도")
    pause_frequency: float = Field(..., description="휴지 빈도")
    voice_quality_score: float = Field(..., ge=0, le=1, description="음성 품질 점수")
    emotional_indicators: Dict[str, float] = Field(..., description="감정 지표들")

class HealthReportResponse(BaseModel):
    """건강 리포트 응답 모델"""
    report_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    senior_id: str
    period: PeriodType
    period_start: date = Field(..., description="분석 시작일")
    period_end: date = Field(..., description="분석 종료일")
    generated_at: datetime = Field(default_factory=datetime.utcnow)
    
    # 주요 건강 지표
    mental_health_score: MentalHealthScore
    health_indicators: List[HealthIndicator]
    
    # 분석 결과
    voice_analysis_count: int = Field(..., description="분석된 음성 통화 수")
    recent_voice_analyses: List[VoiceAnalysisResult] = Field(..., max_items=10)
    
    # 요약 및 추천
    summary: Dict[str, Any] = Field(..., description="리포트 요약")
    trends: Dict[str, Any] = Field(..., description="변화 추이")
    recommendations: List[str] = Field(..., description="권장사항")
    alerts: List[str] = Field(default_factory=list, description="주의사항")
    
    # 파일 정보
    pdf_url: Optional[str] = Field(None, description="PDF 리포트 URL")
    file_size: Optional[int] = Field(None, description="파일 크기(bytes)")
    
    class Config:
        schema_extra = {
            "example": {
                "report_id": "report_001",
                "senior_id": "senior_001",
                "period": "monthly",
                "period_start": "2024-01-01",
                "period_end": "2024-01-31",
                "mental_health_score": {
                    "depression_risk": 0.3,
                    "anxiety_level": 0.2,
                    "stress_level": 0.4,
                    "overall_mood": "stable",
                    "confidence_score": 0.85
                },
                "voice_analysis_count": 15,
                "summary": {"total_calls": 15, "average_mood": "positive"},
                "recommendations": ["정기적인 운동을 권장합니다"]
            }
        }

class BatchAnalysisRequest(BaseModel):
    senior_ids: List[str] = Field(..., min_items=1, max_items=100)
    start_date: datetime
    end_date: datetime
    analysis_type: AnalysisType

class BatchAnalysisResponse(BaseModel):
    batch_id: str
    total_seniors: int
    processing_status: str
    results: List[dict]
    created_at: datetime
