"""
Cloud SQL Database Client
Cloud SQL 데이터베이스 연결 및 관리
"""

import os
import logging
from typing import Optional, Dict, Any, List
from contextlib import asynccontextmanager
import asyncpg
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy import text
import json

logger = logging.getLogger(__name__)


class CloudSQLClient:
    """Cloud SQL 비동기 클라이언트"""
    
    def __init__(self):
        """Cloud SQL 연결 초기화"""
        self.project_id = os.getenv("GOOGLE_CLOUD_PROJECT", "senior-mhealth-472007")
        self.instance_name = os.getenv("CLOUD_SQL_INSTANCE", "senior-mhealth-db")
        self.database_name = os.getenv("DB_NAME", "senior_mhealth")
        self.region = os.getenv("DB_REGION", "asia-northeast3")
        
        # 연결 방식 선택 (Unix Socket or TCP)
        if os.getenv("USE_CLOUD_SQL_AUTH_PROXY", "false").lower() == "true":
            # Cloud SQL Proxy 사용
            self.connection_string = self._get_proxy_connection_string()
        else:
            # 직접 연결 (Cloud Run에서)
            self.connection_string = self._get_direct_connection_string()
        
        self.engine = None
        self.session_factory = None
        
    def _get_proxy_connection_string(self) -> str:
        """Cloud SQL Proxy 연결 문자열"""
        return (
            f"postgresql+asyncpg://{os.getenv('DB_USER', 'postgres')}:"
            f"{os.getenv('DB_PASSWORD', '')}@"
            f"127.0.0.1:5432/{self.database_name}"
        )
    
    def _get_direct_connection_string(self) -> str:
        """Cloud Run에서 Unix Socket 직접 연결"""
        socket_dir = os.getenv("DB_SOCKET_DIR", "/cloudsql")
        instance_connection = f"{self.project_id}:{self.region}:{self.instance_name}"
        
        return (
            f"postgresql+asyncpg://{os.getenv('DB_USER', 'postgres')}:"
            f"{os.getenv('DB_PASSWORD', '')}@/"
            f"{self.database_name}"
            f"?host={socket_dir}/{instance_connection}"
        )
    
    async def initialize(self):
        """데이터베이스 연결 초기화"""
        try:
            self.engine = create_async_engine(
                self.connection_string,
                pool_size=20,
                max_overflow=10,
                pool_pre_ping=True,
                echo=False
            )
            
            self.session_factory = sessionmaker(
                self.engine,
                class_=AsyncSession,
                expire_on_commit=False
            )
            
            # 연결 테스트
            async with self.engine.begin() as conn:
                await conn.execute(text("SELECT 1"))
            
            logger.info(f"Connected to Cloud SQL: {self.instance_name}")
            
        except Exception as e:
            logger.error(f"Failed to connect to Cloud SQL: {e}")
            raise
    
    @asynccontextmanager
    async def get_session(self):
        """데이터베이스 세션 컨텍스트 매니저"""
        async with self.session_factory() as session:
            try:
                yield session
                await session.commit()
            except Exception:
                await session.rollback()
                raise
            finally:
                await session.close()
    
    async def save_analysis_result(self, 
                                  user_id: str,
                                  analysis_type: str,
                                  audio_data: Dict[str, Any],
                                  ai_results: Dict[str, Any],
                                  sincnet_results: Optional[Dict[str, Any]] = None):
        """
        분석 결과를 Cloud SQL에 저장
        
        Args:
            user_id: 사용자 ID
            analysis_type: 분석 유형 (depression/insomnia/comprehensive)
            audio_data: 오디오 메타데이터
            ai_results: AI 분석 결과
            sincnet_results: SincNet 분석 결과
        """
        async with self.get_session() as session:
            try:
                query = text("""
                    INSERT INTO analysis_results 
                    (user_id, analysis_type, audio_metadata, ai_results, sincnet_results, created_at)
                    VALUES (:user_id, :analysis_type, :audio_metadata, :ai_results, :sincnet_results, NOW())
                    RETURNING id
                """)
                
                result = await session.execute(
                    query,
                    {
                        "user_id": user_id,
                        "analysis_type": analysis_type,
                        "audio_metadata": json.dumps(audio_data),
                        "ai_results": json.dumps(ai_results),
                        "sincnet_results": json.dumps(sincnet_results) if sincnet_results else None
                    }
                )
                
                analysis_id = result.scalar()
                logger.info(f"Analysis result saved to Cloud SQL with ID: {analysis_id}")
                return analysis_id
                
            except Exception as e:
                logger.error(f"Failed to save analysis result: {e}")
                raise
    
    async def get_user_analysis_history(self, 
                                       user_id: str,
                                       limit: int = 10) -> List[Dict[str, Any]]:
        """
        사용자의 분석 기록 조회
        
        Args:
            user_id: 사용자 ID
            limit: 조회할 레코드 수
            
        Returns:
            분석 기록 리스트
        """
        async with self.get_session() as session:
            try:
                query = text("""
                    SELECT id, analysis_type, ai_results, sincnet_results, created_at
                    FROM analysis_results
                    WHERE user_id = :user_id
                    ORDER BY created_at DESC
                    LIMIT :limit
                """)
                
                result = await session.execute(
                    query,
                    {"user_id": user_id, "limit": limit}
                )
                
                rows = result.fetchall()
                
                history = []
                for row in rows:
                    history.append({
                        "id": row.id,
                        "analysis_type": row.analysis_type,
                        "ai_results": json.loads(row.ai_results) if row.ai_results else {},
                        "sincnet_results": json.loads(row.sincnet_results) if row.sincnet_results else None,
                        "created_at": row.created_at.isoformat()
                    })
                
                return history
                
            except Exception as e:
                logger.error(f"Failed to get analysis history: {e}")
                raise
    
    async def get_aggregated_metrics(self, 
                                    start_date: str,
                                    end_date: str) -> Dict[str, Any]:
        """
        집계된 메트릭 조회
        
        Args:
            start_date: 시작 날짜
            end_date: 종료 날짜
            
        Returns:
            집계된 메트릭
        """
        async with self.get_session() as session:
            try:
                query = text("""
                    SELECT 
                        COUNT(*) as total_analyses,
                        analysis_type,
                        AVG((ai_results->>'confidence')::float) as avg_confidence,
                        COUNT(DISTINCT user_id) as unique_users
                    FROM analysis_results
                    WHERE created_at BETWEEN :start_date AND :end_date
                    GROUP BY analysis_type
                """)
                
                result = await session.execute(
                    query,
                    {"start_date": start_date, "end_date": end_date}
                )
                
                rows = result.fetchall()
                
                metrics = {
                    "period": {
                        "start": start_date,
                        "end": end_date
                    },
                    "by_type": {}
                }
                
                for row in rows:
                    metrics["by_type"][row.analysis_type] = {
                        "total": row.total_analyses,
                        "avg_confidence": float(row.avg_confidence) if row.avg_confidence else 0,
                        "unique_users": row.unique_users
                    }
                
                return metrics
                
            except Exception as e:
                logger.error(f"Failed to get aggregated metrics: {e}")
                raise
    
    async def close(self):
        """데이터베이스 연결 종료"""
        if self.engine:
            await self.engine.dispose()
            logger.info("Cloud SQL connection closed")


# 싱글톤 인스턴스
cloud_sql_client = CloudSQLClient()


async def get_cloud_sql_client() -> CloudSQLClient:
    """Cloud SQL 클라이언트 의존성 주입"""
    return cloud_sql_client