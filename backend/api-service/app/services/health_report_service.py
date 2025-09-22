from typing import List, Optional
from datetime import datetime, timedelta, date
import uuid
import logging
import asyncio
from concurrent.futures import ThreadPoolExecutor

# Optional Google Cloud imports (for production)
try:
    from google.cloud import firestore
    from google.cloud import storage
    GOOGLE_CLOUD_AVAILABLE = True
except ImportError:
    GOOGLE_CLOUD_AVAILABLE = False
    firestore = None
    storage = None

from ..models.health_report import (
    HealthReportRequest, 
    HealthReportResponse,
    BatchAnalysisRequest,
    BatchAnalysisResponse,
    HealthIndicator,
    MentalHealthScore,
    VoiceAnalysisResult,
    PeriodType
)
from ..core.config import settings
from ..core.logging import get_logger
from ..core.database import get_database_manager

logger = get_logger(__name__)

class HealthReportService:
    def __init__(self):
        self.enabled = settings.report_generation_enabled
        self.db_manager = get_database_manager()
        self.executor = ThreadPoolExecutor(max_workers=4)
    
    async def generate_health_report(self, request: HealthReportRequest) -> HealthReportResponse:
        """건강 리포트 생성"""
        try:
            # Firestore에서 분석 데이터 수집
            analyses = await self._get_analyses_for_period(
                request.senior_id, 
                request.period
            )
            
            if not analyses:
                raise ValueError(f"분석 데이터가 없습니다: {request.senior_id}")
            
            # 리포트 생성
            report_id = str(uuid.uuid4())
            summary = self._calculate_summary(analyses)
            trends = self._analyze_trends(analyses)
            recommendations = self._generate_recommendations(analyses)
            
            # PDF 생성 (선택사항)
            pdf_url = None
            if request.include_details:
                pdf_url = await self._generate_pdf_report(
                    report_id, request, summary, trends, recommendations
                )
            
            # Firestore에 리포트 저장
            report_data = {
                "report_id": report_id,
                "senior_id": request.senior_id,
                "period": request.period,
                "generated_at": datetime.now(),
                "summary": summary,
                "trends": trends,
                "recommendations": recommendations,
                "pdf_url": pdf_url,
                "analysis_type": request.analysis_type
            }
            
            await self._save_to_firestore(report_id, report_data)
            
            return HealthReportResponse(
                report_id=report_id,
                senior_id=request.senior_id,
                period=request.period,
                generated_at=datetime.now(),
                summary=summary,
                trends=trends,
                recommendations=recommendations,
                pdf_url=pdf_url,
                detailed_analyses=analyses if request.include_details else None
            )
            
        except Exception as e:
            logger.error(f"리포트 생성 실패: {e}")
            raise
    
    async def _get_analyses_for_period(self, senior_id: str, period: str) -> List[dict]:
        """기간별 분석 데이터 조회"""
        # Firestore에서 분석 데이터 조회
        analyses_ref = self.db.collection("analyses")
        query = analyses_ref.where("senior_id", "==", senior_id)
        
        # 기간에 따른 필터링
        if period == "weekly":
            start_date = datetime.now() - timedelta(days=7)
        elif period == "monthly":
            start_date = datetime.now() - timedelta(days=30)
        elif period == "quarterly":
            start_date = datetime.now() - timedelta(days=90)
        else:
            start_date = datetime.now() - timedelta(days=30)
        
        query = query.where("created_at", ">=", start_date)
        
        docs = query.stream()
        return [doc.to_dict() for doc in docs]
    
    def _calculate_summary(self, analyses: List[dict]) -> dict:
        """분석 데이터 요약 계산"""
        if not analyses:
            return {}
        
        # 기본 통계 계산
        total_analyses = len(analyses)
        avg_depression_score = sum(a.get("depression_score", 0) for a in analyses) / total_analyses
        avg_emotion_score = sum(a.get("emotion_score", 0) for a in analyses) / total_analyses
        
        return {
            "total_analyses": total_analyses,
            "avg_depression_score": round(avg_depression_score, 2),
            "avg_emotion_score": round(avg_emotion_score, 2),
            "risk_level": self._calculate_risk_level(avg_depression_score)
        }
    
    def _analyze_trends(self, analyses: List[dict]) -> dict:
        """트렌드 분석"""
        if len(analyses) < 2:
            return {"trend": "insufficient_data"}
        
        # 시간순 정렬
        sorted_analyses = sorted(analyses, key=lambda x: x.get("created_at", datetime.min))
        
        # 트렌드 계산
        recent_scores = [a.get("depression_score", 0) for a in sorted_analyses[-5:]]
        older_scores = [a.get("depression_score", 0) for a in sorted_analyses[:5]]
        
        recent_avg = sum(recent_scores) / len(recent_scores)
        older_avg = sum(older_scores) / len(older_scores)
        
        trend_direction = "improving" if recent_avg < older_avg else "worsening" if recent_avg > older_avg else "stable"
        
        return {
            "trend": trend_direction,
            "change_percentage": round(((recent_avg - older_avg) / older_avg * 100), 2) if older_avg > 0 else 0
        }
    
    def _generate_recommendations(self, analyses: List[dict]) -> List[str]:
        """권장사항 생성"""
        recommendations = []
        
        if not analyses:
            return ["분석 데이터가 부족합니다. 더 많은 데이터를 수집해주세요."]
        
        avg_depression_score = sum(a.get("depression_score", 0) for a in analyses) / len(analyses)
        
        if avg_depression_score > 0.7:
            recommendations.append("높은 우울증 위험도가 감지되었습니다. 전문의 상담을 권장합니다.")
        elif avg_depression_score > 0.5:
            recommendations.append("중간 수준의 우울증 위험이 있습니다. 정기적인 모니터링이 필요합니다.")
        else:
            recommendations.append("정신건강 상태가 양호합니다. 현재 상태를 유지하세요.")
        
        # 추가 권장사항
        recommendations.append("규칙적인 운동과 충분한 수면을 유지하세요.")
        recommendations.append("가족이나 친구와의 정기적인 소통을 권장합니다.")
        
        return recommendations
    
    def _calculate_risk_level(self, depression_score: float) -> str:
        """위험도 수준 계산"""
        if depression_score > 0.7:
            return "high"
        elif depression_score > 0.5:
            return "medium"
        else:
            return "low"
    
    async def _generate_pdf_report(
        self, 
        report_id: str, 
        request: HealthReportRequest,
        summary: dict,
        trends: dict, 
        recommendations: List[str]
    ) -> str:
        """PDF 리포트 생성 및 스토리지 업로드"""
        try:
            from reportlab.lib.pagesizes import letter
            from reportlab.pdfgen import canvas
            from reportlab.lib import colors
            from reportlab.lib.styles import getSampleStyleSheet
            from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
            import tempfile
            
            # 임시 PDF 파일 생성
            with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as tmp:
                # PDF 생성 로직
                doc = SimpleDocTemplate(tmp.name, pagesize=letter)
                styles = getSampleStyleSheet()
                elements = []
                
                # 제목
                title = f"건강 리포트: {request.senior_id}"
                elements.append(Paragraph(title, styles['Title']))
                elements.append(Spacer(1, 12))
                
                # 요약
                elements.append(Paragraph("요약", styles['Heading2']))
                elements.append(Paragraph(f"위험 수준: {summary['risk_level']}", styles['Normal']))
                elements.append(Paragraph(f"평균 우울증 점수: {summary['avg_depression_score']}", styles['Normal']))
                elements.append(Paragraph(f"평균 감정 점수: {summary['avg_emotion_score']}", styles['Normal']))
                elements.append(Spacer(1, 12))
                
                # 트렌드
                elements.append(Paragraph("트렌드 분석", styles['Heading2']))
                elements.append(Paragraph(f"추세: {trends['trend']}", styles['Normal']))
                elements.append(Paragraph(f"변화율: {trends['change_percentage']}%", styles['Normal']))
                elements.append(Spacer(1, 12))
                
                # 권장사항
                elements.append(Paragraph("권장사항", styles['Heading2']))
                for rec in recommendations:
                    elements.append(Paragraph(f"• {rec}", styles['Normal']))
                
                # PDF 빌드
                doc.build(elements)
            
            # Cloud Storage에 업로드
            bucket = self.storage_client.bucket(self.bucket_name)
            blob = bucket.blob(f"reports/{request.senior_id}/{report_id}.pdf")
            
            with open(tmp.name, "rb") as pdf_file:
                blob.upload_from_file(pdf_file, content_type="application/pdf")
            
            # 공개 URL 반환
            return blob.public_url
            
        except Exception as e:
            logger.error(f"PDF 생성 실패: {e}")
            return None
    
    async def _save_to_firestore(self, report_id: str, report_data: dict):
        """Firestore에 리포트 저장"""
        try:
            if self.db_manager.is_production_mode():
                db = self.db_manager.get_firestore_client()
                doc_ref = db.collection("health_reports").document(report_id)
                doc_ref.set(report_data)
                logger.info(f"리포트 저장 완료: {report_id}")
            else:
                # 개발 모드에서는 로그만 남김
                logger.info(f"[MOCK] 리포트 저장 완료: {report_id}")
        except Exception as e:
            logger.error(f"리포트 저장 실패: {e}")
            raise

    async def get_report_status(self, report_id: str) -> Optional[dict]:
        """리포트 상태 조회"""
        try:
            if self.db_manager.is_production_mode():
                db = self.db_manager.get_firestore_client()
                doc_ref = db.collection("health_reports").document(report_id)
                doc = doc_ref.get()
                
                if doc.exists:
                    data = doc.to_dict()
                    return {
                        "report_id": report_id,
                        "status": "completed" if data.get("generated_at") else "processing",
                        "generated_at": data.get("generated_at"),
                        "senior_id": data.get("senior_id"),
                        "period": data.get("period")
                    }
                else:
                    return None
            else:
                # Mock 데이터 반환
                return {
                    "report_id": report_id,
                    "status": "completed",
                    "generated_at": datetime.utcnow(),
                    "senior_id": "mock_senior",
                    "period": "monthly"
                }
        except Exception as e:
            logger.error(f"리포트 상태 조회 실패: {e}")
            return None

    async def get_report_history(
        self, 
        senior_id: str, 
        limit: int = 10, 
        offset: int = 0,
        period: Optional[PeriodType] = None
    ) -> List[dict]:
        """시니어 리포트 히스토리 조회"""
        try:
            if self.db_manager.is_production_mode():
                db = self.db_manager.get_firestore_client()
                query = db.collection("health_reports").where("senior_id", "==", senior_id)
                
                if period:
                    query = query.where("period", "==", period.value)
                
                query = query.order_by("generated_at", direction=firestore.Query.DESCENDING)
                query = query.limit(limit).offset(offset)
                
                docs = query.stream()
                return [doc.to_dict() for doc in docs]
            else:
                # Mock 데이터 반환
                mock_reports = []
                for i in range(min(limit, 3)):
                    mock_reports.append({
                        "report_id": f"mock_report_{i}",
                        "senior_id": senior_id,
                        "period": period.value if period else "monthly",
                        "generated_at": datetime.utcnow() - timedelta(days=i*7),
                        "summary": {"total_analyses": 10 + i, "avg_mood": "positive"}
                    })
                return mock_reports
        except Exception as e:
            logger.error(f"리포트 히스토리 조회 실패: {e}")
            return []

    async def create_batch_analysis(self, request: BatchAnalysisRequest) -> BatchAnalysisResponse:
        """배치 분석 생성"""
        try:
            batch_id = str(uuid.uuid4())
            
            # 배치 요청 저장
            batch_data = {
                "batch_id": batch_id,
                "senior_ids": request.senior_ids,
                "start_date": request.start_date,
                "end_date": request.end_date,
                "analysis_type": request.analysis_type.value,
                "created_at": datetime.utcnow(),
                "status": "processing",
                "total_seniors": len(request.senior_ids),
                "completed_count": 0
            }
            
            if self.db_manager.is_production_mode():
                db = self.db_manager.get_firestore_client()
                doc_ref = db.collection("batch_analyses").document(batch_id)
                doc_ref.set(batch_data)
            
            return BatchAnalysisResponse(
                batch_id=batch_id,
                total_seniors=len(request.senior_ids),
                processing_status="processing",
                results=[],
                created_at=datetime.utcnow()
            )
        except Exception as e:
            logger.error(f"배치 분석 생성 실패: {e}")
            raise

    async def process_batch_analysis(self, batch_id: str, request: BatchAnalysisRequest):
        """배치 분석 처리 (백그라운드 태스크)"""
        try:
            logger.info(f"배치 분석 시작: {batch_id}")
            
            results = []
            for senior_id in request.senior_ids:
                try:
                    # 각 시니어에 대해 개별 분석 수행
                    # 실제로는 여기서 복잡한 분석 로직이 실행됨
                    result = {
                        "senior_id": senior_id,
                        "status": "completed",
                        "analysis_summary": f"Mock analysis for {senior_id}",
                        "completed_at": datetime.utcnow()
                    }
                    results.append(result)
                    
                    # 진행률 업데이트
                    if self.db_manager.is_production_mode():
                        db = self.db_manager.get_firestore_client()
                        doc_ref = db.collection("batch_analyses").document(batch_id)
                        doc_ref.update({
                            "completed_count": len(results),
                            "results": results
                        })
                    
                    logger.info(f"배치 분석 진행: {len(results)}/{len(request.senior_ids)}")
                    
                except Exception as e:
                    logger.error(f"시니어 {senior_id} 분석 실패: {e}")
                    results.append({
                        "senior_id": senior_id,
                        "status": "failed",
                        "error": str(e),
                        "completed_at": datetime.utcnow()
                    })
            
            # 완료 상태로 업데이트
            if self.db_manager.is_production_mode():
                db = self.db_manager.get_firestore_client()
                doc_ref = db.collection("batch_analyses").document(batch_id)
                doc_ref.update({
                    "status": "completed",
                    "completed_at": datetime.utcnow(),
                    "results": results
                })
            
            logger.info(f"배치 분석 완료: {batch_id}")
            
        except Exception as e:
            logger.error(f"배치 분석 처리 실패: {e}")
            
            if self.db_manager.is_production_mode():
                try:
                    db = self.db_manager.get_firestore_client()
                    doc_ref = db.collection("batch_analyses").document(batch_id)
                    doc_ref.update({
                        "status": "failed",
                        "error": str(e),
                        "completed_at": datetime.utcnow()
                    })
                except Exception as update_error:
                    logger.error(f"배치 분석 상태 업데이트 실패: {update_error}")
