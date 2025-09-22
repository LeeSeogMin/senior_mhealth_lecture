"""
AI 서비스 시작 시 모델 초기화
"""

import os
import logging
from pathlib import Path
from app.model_loader import model_loader

logger = logging.getLogger(__name__)

async def initialize_models():
    """서비스 시작 시 모델 초기화"""
    
    environment = os.getenv('ENVIRONMENT', 'development')
    logger.info(f"Initializing models for {environment} environment")
    
    # 프로덕션 환경에서는 미리 로드
    if environment == 'production':
        try:
            # VectorStore 미리 로드
            vectorstore_path = model_loader.load_vectorstore()
            logger.info(f"VectorStore loaded: {vectorstore_path}")
            
            # SincNet 모델 미리 로드
            sincnet_path = model_loader.load_sincnet_model()
            if sincnet_path:
                logger.info(f"SincNet model loaded: {sincnet_path}")
            else:
                logger.warning("SincNet model not available")
                
            # 메타데이터 로드
            metadata = model_loader.get_model_metadata()
            logger.info(f"Model metadata: {metadata}")
            
        except Exception as e:
            logger.error(f"Failed to initialize models: {e}")
            # 폴백 모드로 진행
            logger.info("Proceeding with fallback models")
    
    return {
        "environment": environment,
        "models_loaded": True,
        "cache_dir": str(model_loader.cache_dir)
    }

def get_vectorstore_path() -> Path:
    """VectorStore 경로 반환"""
    try:
        return model_loader.load_vectorstore()
    except Exception as e:
        logger.error(f"Failed to get vectorstore: {e}")
        # 기본 경로 반환
        return Path("/app/libraries/voice_analysis/analysis/vector_store/embeddings.jsonl")

def get_sincnet_model_path() -> Optional[Path]:
    """SincNet 모델 경로 반환"""
    try:
        return model_loader.load_sincnet_model()
    except Exception as e:
        logger.error(f"Failed to get SincNet model: {e}")
        return None