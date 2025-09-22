"""
Senior MHealth API Service - 기본 테스트
"""

import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock


@pytest.fixture
def client():
    """테스트 클라이언트 fixture"""
    with patch('app.main.initializeApp') as mock_init:
        mock_init.return_value = MagicMock()
        from app.main import app
        return TestClient(app)


def test_health_check(client):
    """헬스체크 엔드포인트 테스트"""
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert "timestamp" in data
    assert "version" in data


def test_api_v1_health_status(client):
    """API v1 헬스 상태 테스트"""
    response = client.get("/api/v1/health/status")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert "services" in data
    assert data["services"]["api"] == "running"


def test_voice_analyze_no_auth(client):
    """인증 없이 음성 분석 요청 테스트"""
    response = client.post("/api/v1/voice/analyze")
    assert response.status_code == 401


def test_404_handler(client):
    """404 에러 핸들러 테스트"""
    response = client.get("/nonexistent-endpoint")
    assert response.status_code == 404
    data = response.json()
    assert "error" in data
    assert data["error"] == "Not Found"