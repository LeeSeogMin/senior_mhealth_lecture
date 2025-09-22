"""
Pydantic models for request/response validation
"""
from pydantic import BaseModel, Field, validator
from typing import Dict, List, Optional, Any
from datetime import datetime
from enum import Enum

class AudioFormat(str, Enum):
    """Supported audio formats"""
    WAV = "wav"
    MP3 = "mp3"
    M4A = "m4a"
    WEBM = "webm"
    OGG = "ogg"
    FLAC = "flac"

class ProcessingMode(str, Enum):
    """Processing mode options"""
    REAL_TIME = "real_time"
    BATCH = "batch"
    STREAMING = "streaming"

class AnalysisType(str, Enum):
    """Types of analysis to perform"""
    EMOTION = "emotion"
    MENTAL_HEALTH = "mental_health"
    VOICE_BIOMARKERS = "voice_biomarkers"
    COMPREHENSIVE = "comprehensive"

class PredictionRequest(BaseModel):
    """Audio analysis request model"""
    audio_url: str = Field(..., description="URL to audio file (gs:// or https://)")
    audio_format: AudioFormat = Field(AudioFormat.WAV, description="Audio file format")
    analysis_type: AnalysisType = Field(AnalysisType.COMPREHENSIVE, description="Type of analysis")
    processing_mode: ProcessingMode = Field(ProcessingMode.REAL_TIME, description="Processing mode")
    language: str = Field("ko", description="Language code (ko, en, ja, zh)")
    user_id: Optional[str] = Field(None, description="User identifier for tracking")
    session_id: Optional[str] = Field(None, description="Session identifier")
    metadata: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Additional metadata")
    options: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Processing options")
    
    @validator('audio_url')
    def validate_url(cls, v):
        if not (v.startswith('gs://') or v.startswith('https://') or v.startswith('http://')):
            raise ValueError('URL must start with gs://, https://, or http://')
        return v
    
    @validator('language')
    def validate_language(cls, v):
        supported_languages = ['ko', 'en', 'ja', 'zh']
        if v not in supported_languages:
            raise ValueError(f'Language must be one of {supported_languages}')
        return v

class EmotionScore(BaseModel):
    """Emotion analysis scores"""
    happiness: float = Field(..., ge=0, le=1, description="Happiness score")
    sadness: float = Field(..., ge=0, le=1, description="Sadness score")
    anger: float = Field(..., ge=0, le=1, description="Anger score")
    fear: float = Field(..., ge=0, le=1, description="Fear score")
    surprise: float = Field(..., ge=0, le=1, description="Surprise score")
    disgust: float = Field(..., ge=0, le=1, description="Disgust score")
    neutral: float = Field(..., ge=0, le=1, description="Neutral score")
    
    @property
    def dominant_emotion(self) -> str:
        """Get the dominant emotion"""
        emotions = self.dict()
        return max(emotions, key=emotions.get)
    
    @property
    def emotional_intensity(self) -> float:
        """Calculate overall emotional intensity"""
        emotions = self.dict()
        del emotions['neutral']
        return sum(emotions.values())

class MentalHealthIndicators(BaseModel):
    """Mental health assessment indicators"""
    depression_risk: float = Field(..., ge=0, le=1, description="Depression risk score")
    anxiety_level: float = Field(..., ge=0, le=1, description="Anxiety level score")
    stress_level: float = Field(..., ge=0, le=1, description="Stress level score")
    cognitive_load: float = Field(..., ge=0, le=1, description="Cognitive load indicator")
    emotional_stability: float = Field(..., ge=0, le=1, description="Emotional stability score")
    social_engagement: float = Field(..., ge=0, le=1, description="Social engagement indicator")
    
    @property
    def overall_risk_score(self) -> float:
        """Calculate overall mental health risk score"""
        weights = {
            'depression_risk': 0.3,
            'anxiety_level': 0.25,
            'stress_level': 0.2,
            'cognitive_load': 0.15,
            'emotional_stability': -0.1,  # Higher is better
            'social_engagement': -0.1      # Higher is better
        }
        score = sum(getattr(self, key) * weight for key, weight in weights.items())
        return max(0, min(1, score))

class VoiceFeatures(BaseModel):
    """Acoustic and prosodic voice features"""
    pitch_mean: float = Field(..., description="Mean pitch (Hz)")
    pitch_std: float = Field(..., description="Pitch standard deviation")
    pitch_range: float = Field(..., description="Pitch range (Hz)")
    energy_mean: float = Field(..., description="Mean energy level")
    energy_std: float = Field(..., description="Energy standard deviation")
    speaking_rate: float = Field(..., description="Speaking rate (syllables/sec)")
    pause_ratio: float = Field(..., ge=0, le=1, description="Ratio of pause time")
    voice_quality: float = Field(..., ge=0, le=1, description="Voice quality score")
    articulation_clarity: float = Field(..., ge=0, le=1, description="Articulation clarity")
    
class VoiceBiomarkers(BaseModel):
    """Voice-based biomarkers for health assessment"""
    respiratory_pattern: Dict[str, float] = Field(..., description="Respiratory indicators")
    vocal_tremor: float = Field(..., ge=0, le=1, description="Vocal tremor indicator")
    voice_breaks: int = Field(..., ge=0, description="Number of voice breaks")
    jitter: float = Field(..., description="Voice jitter percentage")
    shimmer: float = Field(..., description="Voice shimmer percentage")
    harmonic_noise_ratio: float = Field(..., description="Harmonic to noise ratio (dB)")

class PredictionResponse(BaseModel):
    """Comprehensive analysis response"""
    request_id: str = Field(..., description="Unique request identifier")
    timestamp: datetime = Field(..., description="Analysis timestamp")
    status: str = Field("success", description="Processing status")
    
    # Core analysis results
    emotions: Optional[EmotionScore] = Field(None, description="Emotion analysis results")
    mental_health: Optional[MentalHealthIndicators] = Field(None, description="Mental health indicators")
    voice_features: Optional[VoiceFeatures] = Field(None, description="Voice feature analysis")
    voice_biomarkers: Optional[VoiceBiomarkers] = Field(None, description="Voice biomarkers")
    
    # Metadata
    confidence: float = Field(..., ge=0, le=1, description="Overall confidence score")
    processing_time_ms: int = Field(..., description="Processing time in milliseconds")
    model_version: str = Field(..., description="Model version used")
    analysis_type: AnalysisType = Field(..., description="Type of analysis performed")
    
    # Additional insights
    recommendations: Optional[List[str]] = Field(None, description="Personalized recommendations")
    risk_alerts: Optional[List[str]] = Field(None, description="Risk alerts if any")
    trends: Optional[Dict[str, Any]] = Field(None, description="Trend analysis if available")

class BatchPredictionRequest(BaseModel):
    """Batch processing request"""
    requests: List[PredictionRequest] = Field(..., description="List of prediction requests")
    batch_options: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Batch processing options")

class BatchPredictionResponse(BaseModel):
    """Batch processing response"""
    batch_id: str = Field(..., description="Batch processing identifier")
    total_requests: int = Field(..., description="Total number of requests")
    successful: int = Field(..., description="Number of successful predictions")
    failed: int = Field(..., description="Number of failed predictions")
    results: List[PredictionResponse] = Field(..., description="Individual prediction results")
    processing_time_ms: int = Field(..., description="Total processing time")

class HealthCheckResponse(BaseModel):
    """Service health check response"""
    status: str = Field(..., description="Service status")
    model_loaded: bool = Field(..., description="Model loading status")
    model_version: str = Field(..., description="Current model version")
    environment: str = Field(..., description="Deployment environment")
    uptime_seconds: int = Field(..., description="Service uptime in seconds")
    last_prediction: Optional[datetime] = Field(None, description="Last prediction timestamp")
    gpu_available: bool = Field(..., description="GPU availability status")
    memory_usage_mb: int = Field(..., description="Current memory usage in MB")
    
class ErrorResponse(BaseModel):
    """Error response model"""
    error: str = Field(..., description="Error message")
    error_code: str = Field(..., description="Error code")
    details: Optional[Dict[str, Any]] = Field(None, description="Additional error details")
    request_id: Optional[str] = Field(None, description="Request identifier")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="Error timestamp")