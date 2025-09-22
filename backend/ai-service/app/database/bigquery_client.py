"""
BigQuery Analytics Client
BigQuery 데이터 분석 및 저장
"""

import os
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
import json
from google.cloud import bigquery
from google.cloud.exceptions import GoogleCloudError
import asyncio
from concurrent.futures import ThreadPoolExecutor

logger = logging.getLogger(__name__)


class BigQueryClient:
    """BigQuery 비동기 클라이언트"""
    
    def __init__(self):
        """BigQuery 클라이언트 초기화"""
        self.project_id = os.getenv("GOOGLE_CLOUD_PROJECT", "senior-mhealth-472007")
        self.dataset_id = os.getenv("BIGQUERY_DATASET", "senior_mhealth_analytics")
        self.location = os.getenv("BIGQUERY_LOCATION", "asia-northeast3")
        
        # BigQuery 클라이언트
        self.client = None
        self.executor = ThreadPoolExecutor(max_workers=5)
        
        # 테이블 정의
        self.tables = {
            "analysis_events": f"{self.project_id}.{self.dataset_id}.analysis_events",
            "chain_metrics": f"{self.project_id}.{self.dataset_id}.chain_metrics",
            "user_insights": f"{self.project_id}.{self.dataset_id}.user_insights",
            "sincnet_predictions": f"{self.project_id}.{self.dataset_id}.sincnet_predictions"
        }
        
    async def initialize(self):
        """BigQuery 연결 초기화 및 데이터셋/테이블 생성"""
        try:
            self.client = bigquery.Client(
                project=self.project_id,
                location=self.location
            )
            
            # 데이터셋 생성 (없으면)
            await self._ensure_dataset_exists()
            
            # 테이블 생성 (없으면)
            await self._ensure_tables_exist()
            
            logger.info(f"Connected to BigQuery: {self.dataset_id}")
            
        except Exception as e:
            logger.error(f"Failed to initialize BigQuery client: {e}")
            raise
    
    async def _ensure_dataset_exists(self):
        """데이터셋이 없으면 생성"""
        dataset_id = f"{self.project_id}.{self.dataset_id}"
        
        try:
            dataset = await asyncio.get_event_loop().run_in_executor(
                self.executor,
                self.client.get_dataset,
                dataset_id
            )
            logger.info(f"Dataset exists: {dataset_id}")
        except Exception:
            # 데이터셋 생성
            dataset = bigquery.Dataset(dataset_id)
            dataset.location = self.location
            dataset.description = "Senior MHealth Analytics Dataset"
            
            dataset = await asyncio.get_event_loop().run_in_executor(
                self.executor,
                self.client.create_dataset,
                dataset
            )
            logger.info(f"Created dataset: {dataset_id}")
    
    async def _ensure_tables_exist(self):
        """필요한 테이블들이 없으면 생성"""
        
        # analysis_events 테이블 스키마
        analysis_events_schema = [
            bigquery.SchemaField("event_id", "STRING", mode="REQUIRED"),
            bigquery.SchemaField("user_id", "STRING", mode="REQUIRED"),
            bigquery.SchemaField("timestamp", "TIMESTAMP", mode="REQUIRED"),
            bigquery.SchemaField("analysis_type", "STRING", mode="REQUIRED"),
            bigquery.SchemaField("audio_duration", "FLOAT64"),
            bigquery.SchemaField("ai_model", "STRING"),
            bigquery.SchemaField("confidence_score", "FLOAT64"),
            bigquery.SchemaField("depression_score", "FLOAT64"),
            bigquery.SchemaField("insomnia_score", "FLOAT64"),
            bigquery.SchemaField("indicators", "JSON"),
            bigquery.SchemaField("metadata", "JSON"),
        ]
        
        # chain_metrics 테이블 스키마
        chain_metrics_schema = [
            bigquery.SchemaField("metric_id", "STRING", mode="REQUIRED"),
            bigquery.SchemaField("timestamp", "TIMESTAMP", mode="REQUIRED"),
            bigquery.SchemaField("chain_name", "STRING", mode="REQUIRED"),
            bigquery.SchemaField("execution_time", "FLOAT64"),
            bigquery.SchemaField("api_calls", "INTEGER"),
            bigquery.SchemaField("tokens_used", "INTEGER"),
            bigquery.SchemaField("estimated_cost", "FLOAT64"),
            bigquery.SchemaField("success", "BOOLEAN"),
            bigquery.SchemaField("error_message", "STRING"),
            bigquery.SchemaField("mode", "STRING"),
            bigquery.SchemaField("context", "JSON"),
        ]
        
        # sincnet_predictions 테이블 스키마
        sincnet_predictions_schema = [
            bigquery.SchemaField("prediction_id", "STRING", mode="REQUIRED"),
            bigquery.SchemaField("user_id", "STRING", mode="REQUIRED"),
            bigquery.SchemaField("timestamp", "TIMESTAMP", mode="REQUIRED"),
            bigquery.SchemaField("model_type", "STRING", mode="REQUIRED"),  # depression/insomnia
            bigquery.SchemaField("prediction", "FLOAT64", mode="REQUIRED"),
            bigquery.SchemaField("confidence", "FLOAT64"),
            bigquery.SchemaField("features", "JSON"),
            bigquery.SchemaField("audio_file_hash", "STRING"),
        ]
        
        # user_insights 테이블 스키마 (집계된 인사이트)
        user_insights_schema = [
            bigquery.SchemaField("user_id", "STRING", mode="REQUIRED"),
            bigquery.SchemaField("date", "DATE", mode="REQUIRED"),
            bigquery.SchemaField("total_analyses", "INTEGER"),
            bigquery.SchemaField("avg_depression_score", "FLOAT64"),
            bigquery.SchemaField("avg_insomnia_score", "FLOAT64"),
            bigquery.SchemaField("trend_depression", "STRING"),  # improving/stable/worsening
            bigquery.SchemaField("trend_insomnia", "STRING"),
            bigquery.SchemaField("risk_level", "STRING"),  # low/medium/high
            bigquery.SchemaField("recommendations", "JSON"),
        ]
        
        # 테이블 생성
        tables_to_create = {
            "analysis_events": analysis_events_schema,
            "chain_metrics": chain_metrics_schema,
            "sincnet_predictions": sincnet_predictions_schema,
            "user_insights": user_insights_schema
        }
        
        for table_name, schema in tables_to_create.items():
            table_id = self.tables[table_name]
            try:
                table = await asyncio.get_event_loop().run_in_executor(
                    self.executor,
                    self.client.get_table,
                    table_id
                )
                logger.info(f"Table exists: {table_id}")
            except Exception:
                # 테이블 생성
                table = bigquery.Table(table_id, schema=schema)
                
                # 파티셔닝 설정 (날짜별)
                if table_name in ["analysis_events", "chain_metrics", "sincnet_predictions"]:
                    table.time_partitioning = bigquery.TimePartitioning(
                        type_=bigquery.TimePartitioningType.DAY,
                        field="timestamp"
                    )
                elif table_name == "user_insights":
                    table.time_partitioning = bigquery.TimePartitioning(
                        type_=bigquery.TimePartitioningType.DAY,
                        field="date"
                    )
                
                table = await asyncio.get_event_loop().run_in_executor(
                    self.executor,
                    self.client.create_table,
                    table
                )
                logger.info(f"Created table: {table_id}")
    
    async def insert_analysis_event(self, event_data: Dict[str, Any]):
        """
        분석 이벤트를 BigQuery에 저장
        
        Args:
            event_data: 분석 이벤트 데이터
        """
        try:
            table = self.client.get_table(self.tables["analysis_events"])
            
            # 데이터 준비
            row = {
                "event_id": event_data.get("event_id"),
                "user_id": event_data.get("user_id"),
                "timestamp": datetime.now().isoformat(),
                "analysis_type": event_data.get("analysis_type"),
                "audio_duration": event_data.get("audio_duration"),
                "ai_model": event_data.get("ai_model", "gemini-pro"),
                "confidence_score": event_data.get("confidence_score"),
                "depression_score": event_data.get("depression_score"),
                "insomnia_score": event_data.get("insomnia_score"),
                "indicators": json.dumps(event_data.get("indicators", {})),
                "metadata": json.dumps(event_data.get("metadata", {}))
            }
            
            # 비동기 삽입
            errors = await asyncio.get_event_loop().run_in_executor(
                self.executor,
                self.client.insert_rows_json,
                table,
                [row]
            )
            
            if errors:
                logger.error(f"Failed to insert analysis event: {errors}")
            else:
                logger.info(f"Analysis event inserted: {row['event_id']}")
                
        except Exception as e:
            logger.error(f"Error inserting analysis event: {e}")
    
    async def insert_chain_metrics(self, metrics: Dict[str, Any]):
        """
        체인 실행 메트릭을 BigQuery에 저장
        
        Args:
            metrics: 체인 메트릭 데이터
        """
        try:
            table = self.client.get_table(self.tables["chain_metrics"])
            
            # 데이터 준비
            row = {
                "metric_id": metrics.get("metric_id"),
                "timestamp": datetime.now().isoformat(),
                "chain_name": metrics.get("chain_name"),
                "execution_time": metrics.get("execution_time"),
                "api_calls": metrics.get("api_calls"),
                "tokens_used": metrics.get("tokens_used"),
                "estimated_cost": metrics.get("cost"),
                "success": metrics.get("success", True),
                "error_message": metrics.get("error_message"),
                "mode": metrics.get("mode"),
                "context": json.dumps(metrics.get("context", {}))
            }
            
            # 비동기 삽입
            errors = await asyncio.get_event_loop().run_in_executor(
                self.executor,
                self.client.insert_rows_json,
                table,
                [row]
            )
            
            if errors:
                logger.error(f"Failed to insert chain metrics: {errors}")
            else:
                logger.debug(f"Chain metrics inserted: {row['metric_id']}")
                
        except Exception as e:
            logger.error(f"Error inserting chain metrics: {e}")
    
    async def insert_sincnet_prediction(self, prediction_data: Dict[str, Any]):
        """
        SincNet 예측 결과를 BigQuery에 저장
        
        Args:
            prediction_data: SincNet 예측 데이터
        """
        try:
            table = self.client.get_table(self.tables["sincnet_predictions"])
            
            # 데이터 준비
            row = {
                "prediction_id": prediction_data.get("prediction_id"),
                "user_id": prediction_data.get("user_id"),
                "timestamp": datetime.now().isoformat(),
                "model_type": prediction_data.get("model_type"),
                "prediction": prediction_data.get("prediction"),
                "confidence": prediction_data.get("confidence"),
                "features": json.dumps(prediction_data.get("features", {})),
                "audio_file_hash": prediction_data.get("audio_file_hash")
            }
            
            # 비동기 삽입
            errors = await asyncio.get_event_loop().run_in_executor(
                self.executor,
                self.client.insert_rows_json,
                table,
                [row]
            )
            
            if errors:
                logger.error(f"Failed to insert SincNet prediction: {errors}")
            else:
                logger.info(f"SincNet prediction inserted: {row['prediction_id']}")
                
        except Exception as e:
            logger.error(f"Error inserting SincNet prediction: {e}")
    
    async def query_user_analytics(self, 
                                  user_id: str,
                                  days: int = 30) -> Dict[str, Any]:
        """
        사용자의 분석 데이터 조회
        
        Args:
            user_id: 사용자 ID
            days: 조회할 기간 (일)
            
        Returns:
            분석 결과
        """
        try:
            query = f"""
            SELECT 
                COUNT(*) as total_analyses,
                AVG(depression_score) as avg_depression,
                AVG(insomnia_score) as avg_insomnia,
                MAX(depression_score) as max_depression,
                MAX(insomnia_score) as max_insomnia,
                MIN(depression_score) as min_depression,
                MIN(insomnia_score) as min_insomnia
            FROM `{self.tables['analysis_events']}`
            WHERE user_id = @user_id
                AND timestamp >= TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL @days DAY)
            """
            
            job_config = bigquery.QueryJobConfig(
                query_parameters=[
                    bigquery.ScalarQueryParameter("user_id", "STRING", user_id),
                    bigquery.ScalarQueryParameter("days", "INT64", days),
                ]
            )
            
            # 비동기 쿼리 실행
            query_job = await asyncio.get_event_loop().run_in_executor(
                self.executor,
                self.client.query,
                query,
                job_config
            )
            
            results = await asyncio.get_event_loop().run_in_executor(
                self.executor,
                query_job.result
            )
            
            # 결과 변환
            analytics = {}
            for row in results:
                analytics = {
                    "user_id": user_id,
                    "period_days": days,
                    "total_analyses": row.total_analyses,
                    "depression": {
                        "average": float(row.avg_depression) if row.avg_depression else 0,
                        "max": float(row.max_depression) if row.max_depression else 0,
                        "min": float(row.min_depression) if row.min_depression else 0
                    },
                    "insomnia": {
                        "average": float(row.avg_insomnia) if row.avg_insomnia else 0,
                        "max": float(row.max_insomnia) if row.max_insomnia else 0,
                        "min": float(row.min_insomnia) if row.min_insomnia else 0
                    }
                }
                break  # 단일 행 결과
            
            return analytics
            
        except Exception as e:
            logger.error(f"Error querying user analytics: {e}")
            return {}
    
    async def get_system_metrics(self, hours: int = 24) -> Dict[str, Any]:
        """
        시스템 전체 메트릭 조회
        
        Args:
            hours: 조회할 시간
            
        Returns:
            시스템 메트릭
        """
        try:
            query = f"""
            SELECT 
                COUNT(DISTINCT user_id) as unique_users,
                COUNT(*) as total_analyses,
                AVG(execution_time) as avg_execution_time,
                SUM(estimated_cost) as total_cost,
                AVG(CASE WHEN success THEN 1 ELSE 0 END) * 100 as success_rate
            FROM `{self.tables['chain_metrics']}`
            WHERE timestamp >= TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL @hours HOUR)
            """
            
            job_config = bigquery.QueryJobConfig(
                query_parameters=[
                    bigquery.ScalarQueryParameter("hours", "INT64", hours),
                ]
            )
            
            # 비동기 쿼리 실행
            query_job = await asyncio.get_event_loop().run_in_executor(
                self.executor,
                self.client.query,
                query,
                job_config
            )
            
            results = await asyncio.get_event_loop().run_in_executor(
                self.executor,
                query_job.result
            )
            
            # 결과 변환
            metrics = {}
            for row in results:
                metrics = {
                    "period_hours": hours,
                    "unique_users": row.unique_users,
                    "total_analyses": row.total_analyses,
                    "avg_execution_time": float(row.avg_execution_time) if row.avg_execution_time else 0,
                    "total_cost": float(row.total_cost) if row.total_cost else 0,
                    "success_rate": float(row.success_rate) if row.success_rate else 0
                }
                break
            
            return metrics
            
        except Exception as e:
            logger.error(f"Error getting system metrics: {e}")
            return {}
    
    async def close(self):
        """클라이언트 종료"""
        if self.executor:
            self.executor.shutdown(wait=True)
        logger.info("BigQuery client closed")


# 싱글톤 인스턴스
bigquery_client = BigQueryClient()


async def get_bigquery_client() -> BigQueryClient:
    """BigQuery 클라이언트 의존성 주입"""
    return bigquery_client