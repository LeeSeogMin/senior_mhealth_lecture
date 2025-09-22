"""
환경 변수 관리 유틸리티 모듈

프로젝트 루트의 .env.local 파일에서 환경 변수를 불러오고 관리합니다.
"""

import os
import logging
from pathlib import Path
from typing import Optional, Dict, Any
from dotenv import load_dotenv

# 로깅 설정
logger = logging.getLogger(__name__)


def load_env_vars(env_file: Optional[str] = None) -> Dict[str, str]:
    """
    지정된 환경 변수 파일 또는 기본 위치에서 환경 변수를 로드합니다.

    Args:
        env_file: 환경 변수 파일의 경로 (None인 경우 기본 위치에서 검색)

    Returns:
        Dict[str, str]: 로드된 환경 변수 사전
    """
    # 현재 파일 위치 기준으로 프로젝트 루트 디렉토리 찾기
    current_dir = Path(__file__).resolve().parent.parent.parent.parent

    # 환경 변수 파일 경로 우선순위
    env_paths = [
        env_file,
        os.path.join(current_dir, "ai", ".env.local"),  # ai/.env.local
        os.path.join(current_dir, ".env.local"),  # 프로젝트 루트의 .env.local
        os.path.join(current_dir, ".env"),  # 프로젝트 루트의 .env
        os.path.join(current_dir, "ai", "analysis", ".env"),  # 레거시 경로
    ]

    # 유효한 첫 번째 환경 변수 파일 로드
    loaded_file = None
    for path in env_paths:
        if path and os.path.isfile(path):
            load_dotenv(path)
            loaded_file = path
            logger.info(f"환경 변수를 로드했습니다: {path}")
            break

    if not loaded_file:
        logger.warning("환경 변수 파일을 찾을 수 없습니다.")

    # 로드된 환경 변수 반환 (os.environ의 복사본)
    return dict(os.environ)


def get_env(key: str, default: Any = None) -> Any:
    """
    환경 변수 값을 가져옵니다. 없는 경우 기본값 반환.

    Args:
        key: 환경 변수 키
        default: 기본값 (환경 변수가 없을 경우 반환)

    Returns:
        Any: 환경 변수 값 또는 기본값
    """
    return os.environ.get(key, default)


def check_required_env_vars(required_keys: list) -> bool:
    """
    필수 환경 변수가 설정되어 있는지 확인합니다.

    Args:
        required_keys: 필수 환경 변수 키 목록

    Returns:
        bool: 모든 필수 환경 변수가 설정되어 있으면 True
    """
    missing_keys = [key for key in required_keys if key not in os.environ]

    if missing_keys:
        logger.error(f"필수 환경 변수가 설정되지 않았습니다: {', '.join(missing_keys)}")
        return False

    return True


# 기본적으로 환경 변수 로드
env_vars = load_env_vars()

# 자주 사용되는 환경 변수
FIREBASE_PROJECT_ID = get_env("FIREBASE_PROJECT_ID")
FIREBASE_STORAGE_BUCKET = get_env("FIREBASE_STORAGE_BUCKET")

# AI 서비스 API 키들
OPENAI_API_KEY = get_env("OPENAI_API_KEY")
ANTHROPIC_API_KEY = get_env("ANTHROPIC_API_KEY")
GROK_API_KEY = get_env("GROK_API_KEY")

# Google Cloud 관련
GOOGLE_APPLICATION_CREDENTIALS = get_env("GOOGLE_APPLICATION_CREDENTIALS")
ENVIRONMENT = get_env("NODE_ENV", "development")
