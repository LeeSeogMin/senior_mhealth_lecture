"""
음성 분석 API 엔드포인트
제5강: Cloud Run과 FastAPI로 확장된 백엔드 구현
"""

from fastapi import APIRouter, HTTPException, UploadFile, File, Depends
from typing import Optional
import os
from datetime import datetime

from ..models.voice_analysis import (
    VoiceAnalysisRequest, 
    VoiceAnalysisResponse,
    VoiceUploadRequest,
    VoiceUploadResponse,
    AnalysisStatus
)
from ..services.voice_analysis_service import VoiceAnalysisService
from ..core.config import get_settings
from ..core.logging import get_logger

# 로깅 설정
logger = get_logger(__name__)

# APIRouter 생성
router = APIRouter()

# 서비스 인스턴스 (의존성 주입용)
def get_voice_analysis_service() -> VoiceAnalysisService:
    return VoiceAnalysisService()

@router.get("/")
async def voice_analysis_info():
    """음성 분석 서비스 정보"""
    return {
        "service": "음성 분석 API",
        "version": "2.0.0",
        "description": "노인 음성 분석을 위한 AI 서비스",
        "endpoints": [
            "POST /analyze - 음성 분석 요청",
            "POST /upload - 오디오 파일 업로드",
            "GET /status/{analysis_id} - 분석 상태 조회"
        ]
    }

@router.post("/analyze", response_model=VoiceAnalysisResponse)
async def analyze_voice(
    request: VoiceAnalysisRequest,
    service: VoiceAnalysisService = Depends(get_voice_analysis_service),
    settings = Depends(get_settings)
):
    """
    음성 분석 API 엔드포인트
    실제 AI 분석 파이프라인과 연동
    """
    try:
        logger.info(f"음성 분석 요청: type={request.analysis_type}, call_id={request.call_id}")
        
        # 서비스 활성화 확인
        if not settings.voice_analysis_enabled:
            raise HTTPException(
                status_code=503,
                detail="음성 분석 서비스가 현재 비활성화되어 있습니다"
            )
        
        # 실제 분석 실행
        result = await service.analyze_voice(request)
        
        logger.info(f"음성 분석 완료: {result.analysis_id}")
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"음성 분석 API 오류: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"음성 분석 처리 중 오류가 발생했습니다: {str(e)}"
        )

@router.post("/upload", response_model=VoiceUploadResponse)
async def upload_audio(
    file: UploadFile = File(...),
    user_id: Optional[str] = None,
    senior_id: Optional[str] = None,
    settings = Depends(get_settings)
):
    """오디오 파일 업로드 엔드포인트"""
    try:
        logger.info(f"오디오 파일 업로드: {file.filename}, size: {file.size}")
        
        # 파일 크기 제한 (100MB)
        max_size = 100 * 1024 * 1024
        if file.size and file.size > max_size:
            raise HTTPException(
                status_code=400, 
                detail=f"파일 크기는 {max_size // (1024*1024)}MB를 초과할 수 없습니다"
            )
        
        # 파일 형식 검증
        allowed_extensions = ['.wav', '.mp3', '.flac', '.m4a', '.ogg']
        file_extension = os.path.splitext(file.filename or '')[1].lower()
        
        if file_extension not in allowed_extensions:
            raise HTTPException(
                status_code=400, 
                detail=f"지원되지 않는 파일 형식입니다. 지원 형식: {', '.join(allowed_extensions)}"
            )
        
        # Content-Type 검증
        allowed_content_types = [
            'audio/wav', 'audio/mp3', 'audio/mpeg', 
            'audio/flac', 'audio/m4a', 'audio/ogg'
        ]
        
        content_type = file.content_type or 'audio/wav'
        if content_type not in allowed_content_types:
            logger.warning(f"Unknown content type: {content_type}, defaulting to audio/wav")
            content_type = 'audio/wav'
        
        # 응답 생성 (실제 구현에서는 Cloud Storage 업로드)
        response = VoiceUploadResponse(
            success=True,
            message="파일 업로드가 완료되었습니다",
            filename=file.filename or "unknown.wav",
            file_size=file.size,
            content_type=content_type,
            storage_url=f"gs://{settings.storage_bucket_name or 'mock-bucket'}/uploads/{file.filename}" if settings.storage_bucket_name else None
        )
        
        logger.info(f"파일 업로드 성공: {response.upload_id}")
        return response
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"파일 업로드 중 오류 발생: {e}")
        raise HTTPException(
            status_code=500, 
            detail=f"파일 업로드 중 오류가 발생했습니다: {str(e)}"
        )

@router.get("/status/{analysis_id}", response_model=AnalysisStatus)
async def get_analysis_status(analysis_id: str):
    """분석 상태 조회 엔드포인트"""
    try:
        logger.info(f"분석 상태 조회: {analysis_id}")
        
        # 실제 구현에서는 데이터베이스나 캐시에서 상태 조회
        # 현재는 분석 ID 기반으로 모의 응답 생성
        if analysis_id.startswith("error_"):
            status = AnalysisStatus(
                analysis_id=analysis_id,
                status="failed",
                progress=0,
                message="분석 중 오류가 발생했습니다",
                error_message="분석 파이프라인 오류"
            )
        elif analysis_id.startswith("disabled_"):
            status = AnalysisStatus(
                analysis_id=analysis_id,
                status="disabled",
                progress=0,
                message="서비스가 비활성화되어 있습니다"
            )
        elif analysis_id.startswith("analysis_"):
            # 정상 완료 상태
            status = AnalysisStatus(
                analysis_id=analysis_id,
                status="completed",
                progress=100,
                message="분석이 성공적으로 완료되었습니다",
                completed_at=datetime.utcnow()
            )
        else:
            # 기타 경우
            status = AnalysisStatus(
                analysis_id=analysis_id,
                status="processing",
                progress=75,
                message="분석이 진행 중입니다..."
            )
        
        logger.info(f"상태 조회 완료: {analysis_id} -> {status.status}")
        return status
        
    except Exception as e:
        logger.error(f"상태 조회 중 오류 발생: {e}")
        raise HTTPException(
            status_code=500, 
            detail=f"상태 조회 중 오류가 발생했습니다: {str(e)}"
        )