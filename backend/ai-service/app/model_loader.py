"""
모델 및 VectorStore 로더
GCS에서 모델을 다운로드하고 캐싱하는 유틸리티
"""

import os
import json
import logging
from pathlib import Path
from typing import Optional, Dict, Any
import hashlib
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

class ModelLoader:
    """GCS에서 모델을 로드하고 로컬 캐싱을 관리"""
    
    def __init__(self, cache_dir: str = "/tmp/models_cache"):
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.bucket_name = os.getenv('MODELS_BUCKET', 'senior-mhealth-models-production')
        
    def load_vectorstore(self, force_download: bool = False) -> Path:
        """VectorStore embeddings 로드"""
        
        local_path = self.cache_dir / "vectorstore" / "embeddings.jsonl"
        
        # 로컬 캐시 확인
        if local_path.exists() and not force_download:
            # 캐시 유효성 검사 (24시간)
            if self._is_cache_valid(local_path, hours=24):
                logger.info(f"Using cached vectorstore: {local_path}")
                return local_path
        
        # GCS에서 다운로드
        logger.info(f"Downloading vectorstore from GCS...")
        gcs_path = f"gs://{self.bucket_name}/vectorstore/embeddings.jsonl"
        
        try:
            # gsutil 사용하여 다운로드
            local_path.parent.mkdir(parents=True, exist_ok=True)
            os.system(f"gsutil cp {gcs_path} {local_path}")
            logger.info(f"Downloaded vectorstore to {local_path}")
            return local_path
        except Exception as e:
            logger.error(f"Failed to download vectorstore: {e}")
            # 폴백: 로컬 파일 사용
            fallback_path = Path("/app/libraries/voice_analysis/analysis/vector_store/embeddings.jsonl")
            if fallback_path.exists():
                logger.info(f"Using fallback vectorstore: {fallback_path}")
                return fallback_path
            raise
    
    def load_sincnet_model(self, model_name: str = "sincnet_senior.pth", force_download: bool = False) -> Path:
        """SincNet 모델 로드"""
        
        local_path = self.cache_dir / "sincnet" / model_name
        
        # 로컬 캐시 확인
        if local_path.exists() and not force_download:
            if self._is_cache_valid(local_path, hours=168):  # 1주일
                logger.info(f"Using cached SincNet model: {local_path}")
                return local_path
        
        # GCS에서 다운로드
        logger.info(f"Downloading SincNet model from GCS...")
        gcs_path = f"gs://{self.bucket_name}/sincnet/{model_name}"
        
        try:
            local_path.parent.mkdir(parents=True, exist_ok=True)
            os.system(f"gsutil cp {gcs_path} {local_path}")
            logger.info(f"Downloaded SincNet model to {local_path}")
            return local_path
        except Exception as e:
            logger.error(f"Failed to download SincNet model: {e}")
            # 폴백: 로컬 모델 사용
            fallback_path = Path(f"/app/models/sincnet/{model_name}")
            if fallback_path.exists():
                logger.info(f"Using fallback SincNet model: {fallback_path}")
                return fallback_path
            # SincNet은 선택적이므로 None 반환
            logger.warning("SincNet model not available, proceeding without it")
            return None
    
    def _is_cache_valid(self, file_path: Path, hours: int = 24) -> bool:
        """캐시 파일 유효성 검사"""
        if not file_path.exists():
            return False
        
        # 파일 수정 시간 확인
        mtime = datetime.fromtimestamp(file_path.stat().st_mtime)
        age = datetime.now() - mtime
        
        return age < timedelta(hours=hours)
    
    def get_model_metadata(self) -> Dict[str, Any]:
        """모델 메타데이터 조회"""
        try:
            metadata_path = self.cache_dir / "metadata.json"
            
            # 캐시된 메타데이터 확인
            if metadata_path.exists() and self._is_cache_valid(metadata_path, hours=1):
                with open(metadata_path, 'r') as f:
                    return json.load(f)
            
            # GCS에서 메타데이터 다운로드
            gcs_path = f"gs://{self.bucket_name}/metadata.json"
            os.system(f"gsutil cp {gcs_path} {metadata_path}")
            
            with open(metadata_path, 'r') as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Failed to load model metadata: {e}")
            return {
                "status": "fallback",
                "message": "Using local models",
                "timestamp": datetime.now().isoformat()
            }

# 싱글톤 인스턴스
model_loader = ModelLoader()