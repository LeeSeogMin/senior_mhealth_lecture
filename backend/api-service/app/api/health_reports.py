"""
건강 리포트 API 엔드포인트
제5강: Cloud Run과 FastAPI로 확장된 백엔드 구현
"""

from fastapi import APIRouter, HTTPException, Depends, BackgroundTasks, Query
from typing import List, Optional
from datetime import datetime

from ..models.health_report import (
    HealthReportRequest,
    HealthReportResponse,
    BatchAnalysisRequest,
    BatchAnalysisResponse,
    PeriodType
)
from ..services.health_report_service import HealthReportService
from ..core.config import get_settings
from ..core.logging import get_logger
from ..core.database import get_database_manager

# 로깅 설정
logger = get_logger(__name__)

# APIRouter 생성
router = APIRouter()

# 서비스 인스턴스 (의존성 주입용)
def get_health_report_service() -> HealthReportService:
    return HealthReportService()

@router.get("/")
async def health_reports_info():
    """건강 리포트 서비스 정보"""
    return {
        "service": "건강 리포트 API",
        "version": "2.0.0", 
        "description": "시니어 건강 리포트 생성 및 관리 서비스",
        "endpoints": [
            "POST /generate - 건강 리포트 생성",
            "GET /status/{report_id} - 리포트 상태 조회",
            "GET /history/{senior_id} - 리포트 히스토리 조회",
            "POST /batch - 배치 분석 요청"
        ]
    }

@router.post("/generate", response_model=HealthReportResponse)
async def generate_health_report(
    request: HealthReportRequest,
    background_tasks: BackgroundTasks,
    service: HealthReportService = Depends(get_health_report_service),
    settings = Depends(get_settings)
):
    """
    건강 리포트 생성 API
    음성 분석 데이터를 기반으로 종합 건강 리포트 생성
    """
    try:
        logger.info(f"건강 리포트 생성 요청: senior_id={request.senior_id}, period={request.period}")
        
        # 서비스 활성화 확인
        if not settings.report_generation_enabled:
            raise HTTPException(
                status_code=503,
                detail="건강 리포트 생성 서비스가 현재 비활성화되어 있습니다"
            )
        
        # 리포트 생성 실행
        result = await service.generate_health_report(request)
        
        logger.info(f"건강 리포트 생성 완료: {result.report_id}")
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"건강 리포트 생성 API 오류: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"건강 리포트 생성 중 오류가 발생했습니다: {str(e)}"
        )

@router.get("/status/{report_id}")
async def get_report_status(
    report_id: str,
    service: HealthReportService = Depends(get_health_report_service)
):
    """리포트 생성 상태 조회"""
    try:
        logger.info(f"리포트 상태 조회: {report_id}")
        
        status = await service.get_report_status(report_id)
        
        if status is None:
            raise HTTPException(
                status_code=404,
                detail=f"리포트를 찾을 수 없습니다: {report_id}"
            )
        
        return status
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"리포트 상태 조회 오류: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"리포트 상태 조회 중 오류가 발생했습니다: {str(e)}"
        )

@router.get("/history/{senior_id}")
async def get_report_history(
    senior_id: str,
    limit: Optional[int] = 10,
    offset: Optional[int] = 0,
    period: Optional[PeriodType] = None,
    service: HealthReportService = Depends(get_health_report_service)
):
    """시니어 리포트 히스토리 조회"""
    try:
        logger.info(f"리포트 히스토리 조회: senior_id={senior_id}, limit={limit}")
        
        history = await service.get_report_history(senior_id, limit, offset, period)
        
        return {
            "senior_id": senior_id,
            "total_reports": len(history),
            "reports": history,
            "pagination": {
                "limit": limit,
                "offset": offset
            }
        }
        
    except Exception as e:
        logger.error(f"리포트 히스토리 조회 오류: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"리포트 히스토리 조회 중 오류가 발생했습니다: {str(e)}"
        )

@router.post("/batch", response_model=BatchAnalysisResponse)
async def create_batch_analysis(
    request: BatchAnalysisRequest,
    background_tasks: BackgroundTasks,
    service: HealthReportService = Depends(get_health_report_service),
    settings = Depends(get_settings)
):
    """배치 분석 요청"""
    try:
        logger.info(f"배치 분석 요청: {len(request.senior_ids)}명의 시니어")
        
        # 서비스 활성화 확인
        if not settings.report_generation_enabled:
            raise HTTPException(
                status_code=503,
                detail="리포트 생성 서비스가 현재 비활성화되어 있습니다"
            )
        
        # 배치 분석 실행 (백그라운드 태스크로 처리)
        batch_result = await service.create_batch_analysis(request)
        
        # 실제 처리를 백그라운드에서 수행
        background_tasks.add_task(
            service.process_batch_analysis,
            batch_result.batch_id,
            request
        )
        
        logger.info(f"배치 분석 시작: {batch_result.batch_id}")
        return batch_result
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"배치 분석 요청 오류: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"배치 분석 요청 중 오류가 발생했습니다: {str(e)}"
        )

@router.get("/database/health")
async def check_database_health(
    db_manager = Depends(get_database_manager)
):
    """데이터베이스 연결 상태 확인"""
    try:
        health_status = await db_manager.health_check()
        return {
            "status": "healthy" if "error" not in health_status else "unhealthy",
            "database": health_status,
            "timestamp": datetime.utcnow().isoformat() + "Z"
        }
    except Exception as e:
        logger.error(f"데이터베이스 헬스체크 오류: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"데이터베이스 상태 확인 중 오류가 발생했습니다: {str(e)}"
        )
