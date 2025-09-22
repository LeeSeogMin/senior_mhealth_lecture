# 제7강: AI 모델 이해와 로컬 테스트 - 서버 모듈
"""
FastAPI 서버 모듈
모델 서빙 및 API 엔드포인트 제공
"""

from .model_server import ModelServer, create_app

__all__ = ['ModelServer', 'create_app']