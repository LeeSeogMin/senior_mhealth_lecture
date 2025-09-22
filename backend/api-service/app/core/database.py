"""
데이터베이스 연결 및 관리
제5강: Cloud Run과 FastAPI로 확장된 백엔드 구현
"""

from typing import Optional
import logging
from datetime import datetime

# Optional Google Cloud imports (for production)
try:
    from google.cloud import firestore
    from google.cloud import storage
    GOOGLE_CLOUD_AVAILABLE = True
except ImportError:
    GOOGLE_CLOUD_AVAILABLE = False
    firestore = None
    storage = None

from .config import settings
from .logging import get_logger

logger = get_logger(__name__)

class DatabaseManager:
    """데이터베이스 연결 및 관리 클래스"""
    
    def __init__(self):
        self.db = None
        self.storage_client = None
        self.bucket_name = settings.storage_bucket_name or "senior-mhealth-storage"
        
        # Google Cloud 서비스 초기화
        if GOOGLE_CLOUD_AVAILABLE and settings.google_cloud_project:
            try:
                self.db = firestore.Client(project=settings.google_cloud_project)
                self.storage_client = storage.Client(project=settings.google_cloud_project)
                logger.info(f"Google Cloud services initialized for project: {settings.google_cloud_project}")
            except Exception as e:
                logger.warning(f"Google Cloud initialization failed: {e}")
                logger.info("Using mock database services for development")
                self.db = None
                self.storage_client = None
        else:
            logger.info("Using mock database services (Google Cloud not available or not configured)")

    async def health_check(self) -> dict:
        """데이터베이스 연결 상태 확인"""
        try:
            if self.db:
                # Firestore 연결 테스트
                test_doc = self.db.collection("_health_check").document("test")
                test_doc.set({"timestamp": datetime.utcnow(), "status": "ok"})
                
                return {
                    "firestore": "connected",
                    "storage": "connected" if self.storage_client else "not_configured",
                    "project": settings.google_cloud_project,
                    "bucket": self.bucket_name
                }
            else:
                return {
                    "firestore": "mock_mode",
                    "storage": "mock_mode", 
                    "project": None,
                    "bucket": self.bucket_name
                }
        except Exception as e:
            logger.error(f"Database health check failed: {e}")
            return {
                "firestore": "error",
                "storage": "error",
                "error": str(e)
            }

    def get_firestore_client(self):
        """Firestore 클라이언트 반환"""
        if self.db is None:
            raise RuntimeError("Firestore client not initialized. Check Google Cloud configuration.")
        return self.db

    def get_storage_client(self):
        """Storage 클라이언트 반환"""
        if self.storage_client is None:
            raise RuntimeError("Storage client not initialized. Check Google Cloud configuration.")
        return self.storage_client

    def is_production_mode(self) -> bool:
        """프로덕션 모드인지 확인"""
        return self.db is not None and self.storage_client is not None


# 전역 데이터베이스 매니저 인스턴스
db_manager = DatabaseManager()

def get_database_manager() -> DatabaseManager:
    """의존성 주입을 위한 데이터베이스 매니저 반환"""
    return db_manager