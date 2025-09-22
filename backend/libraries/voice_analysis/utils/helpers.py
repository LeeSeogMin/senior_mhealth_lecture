"""
AI 분석 서비스를 위한 유틸리티 함수들
"""

import os
import logging
from typing import Optional, Dict, Any

logger = logging.getLogger(__name__)

def validate_audio_file(filename: str) -> bool:
    """오디오 파일 형식 검증"""
    allowed_extensions = ['.wav', '.mp3', '.flac', '.m4a', '.ogg']
    file_extension = os.path.splitext(filename)[1].lower()
    return file_extension in allowed_extensions

def get_file_size_mb(file_path: str) -> Optional[float]:
    """파일 크기를 MB 단위로 반환"""
    try:
        size_bytes = os.path.getsize(file_path)
        return size_bytes / (1024 * 1024)
    except OSError:
        logger.error(f"파일 크기 확인 실패: {file_path}")
        return None

def create_analysis_id() -> str:
    """고유한 분석 ID 생성"""
    import time
    import random
    timestamp = int(time.time())
    random_suffix = random.randint(1000, 9999)
    return f"analysis_{timestamp}_{random_suffix}"

def format_timestamp(timestamp: float) -> str:
    """타임스탬프를 읽기 쉬운 형식으로 변환"""
    from datetime import datetime
    return datetime.fromtimestamp(timestamp).strftime("%Y-%m-%d %H:%M:%S")
