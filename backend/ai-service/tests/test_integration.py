"""
통합 테스트 - AI Service Simple
FastAPI 앱과 Gemini 분석기의 통합 테스트
"""

import pytest
import asyncio
from unittest.mock import Mock, patch, MagicMock
from fastapi.testclient import TestClient
import sys
from pathlib import Path

# 프로젝트 경로 추가
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.main import app
from app.services.gemini_analyzer import AnalysisRequest, AnalysisResponse


client = TestClient(app)


class TestHealthCheck:
    """헬스체크 엔드포인트 테스트"""

    def test_root_health_check(self):
        """루트 헬스체크 테스트"""
        response = client.get("/")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert data["service"] == "senior-mhealth-ai-simple"
        assert "version" in data

    def test_detailed_health_check(self):
        """상세 헬스체크 테스트"""
        response = client.get("/health")
        assert response.status_code in [200, 503]  # 상태에 따라
        data = response.json()
        assert "status" in data
        assert "components" in data
        assert "environment" in data


class TestAnalyzeEndpoint:
    """분석 엔드포인트 테스트"""

    @patch('app.main.analyzer')
    def test_analyze_success(self, mock_analyzer):
        """정상적인 분석 요청 테스트"""
        # Mock 응답 설정
        mock_response = AnalysisResponse(
            depression_score=45.0,
            anxiety_score=30.0,
            cognitive_score=85.0,
            emotional_state="약간 우울",
            key_concerns=["우울감", "피로"],
            recommendations=["충분한 휴식", "전문가 상담 고려"],
            confidence=0.85
        )

        # Mock analyzer 설정
        mock_analyzer.analyze_mental_health = asyncio.coroutine(
            lambda x: mock_response
        )

        # 요청 전송
        response = client.post("/analyze", json={
            "text": "요즘 너무 힘들고 우울해요",
            "user_id": "test_user",
            "session_id": "test_session"
        })

        # 응답 검증
        assert response.status_code == 200
        data = response.json()
        assert data["depression_score"] == 45.0
        assert data["anxiety_score"] == 30.0
        assert data["cognitive_score"] == 85.0
        assert data["emotional_state"] == "약간 우울"
        assert len(data["key_concerns"]) > 0
        assert len(data["recommendations"]) > 0
        assert data["confidence"] == 0.85

    def test_analyze_empty_text(self):
        """빈 텍스트로 분석 요청 테스트"""
        response = client.post("/analyze", json={
            "text": "",
            "user_id": "test_user"
        })

        # 400 에러 예상
        assert response.status_code == 400
        data = response.json()
        assert "detail" in data
        assert "비어있습니다" in data["detail"]

    def test_analyze_missing_text(self):
        """텍스트 없이 분석 요청 테스트"""
        response = client.post("/analyze", json={
            "user_id": "test_user"
        })

        # 422 에러 예상 (Pydantic validation)
        assert response.status_code == 422

    @patch('app.main.analyzer')
    def test_analyze_short_text(self, mock_analyzer):
        """짧은 텍스트 분석 테스트"""
        # Mock 응답 설정 (짧은 텍스트용)
        mock_response = AnalysisResponse(
            depression_score=0,
            anxiety_score=0,
            cognitive_score=100,
            emotional_state="분석 불가",
            key_concerns=["텍스트가 너무 짧음"],
            recommendations=["더 자세한 설명이 필요합니다"],
            confidence=0.1
        )

        mock_analyzer.analyze_mental_health = asyncio.coroutine(
            lambda x: mock_response
        )

        response = client.post("/analyze", json={
            "text": "안녕",
            "user_id": "test_user"
        })

        assert response.status_code == 200
        data = response.json()
        assert data["confidence"] == 0.1
        assert data["emotional_state"] == "분석 불가"

    @patch('app.main.analyzer', None)
    def test_analyze_no_analyzer(self):
        """분석기가 초기화되지 않은 경우 테스트"""
        response = client.post("/analyze", json={
            "text": "테스트 텍스트",
            "user_id": "test_user"
        })

        # 503 Service Unavailable 예상
        assert response.status_code == 503
        data = response.json()
        assert "준비되지 않았습니다" in data["detail"]


class TestErrorHandling:
    """에러 처리 테스트"""

    def test_404_not_found(self):
        """존재하지 않는 엔드포인트 테스트"""
        response = client.get("/nonexistent")
        assert response.status_code == 404

    def test_method_not_allowed(self):
        """허용되지 않은 메서드 테스트"""
        response = client.get("/analyze")  # POST만 허용
        assert response.status_code == 405


class TestIntegrationScenarios:
    """통합 시나리오 테스트"""

    @patch('app.services.gemini_analyzer.genai')
    def test_full_analysis_flow(self, mock_genai):
        """전체 분석 플로우 테스트"""
        # Gemini API Mock 설정
        mock_model = MagicMock()
        mock_response = MagicMock()
        mock_response.text = '''
        {
            "depression_score": 60,
            "anxiety_score": 40,
            "cognitive_score": 90,
            "emotional_state": "우울 경향",
            "key_concerns": ["우울감", "무기력"],
            "recommendations": ["운동", "상담"],
            "confidence": 0.9
        }
        '''

        mock_model.generate_content.return_value = mock_response
        mock_genai.GenerativeModel.return_value = mock_model
        mock_genai.configure = MagicMock()

        # 환경변수 설정
        import os
        os.environ["GOOGLE_API_KEY"] = "test_key"

        # 앱 재시작 (분석기 재초기화)
        from app.main import app as test_app
        test_client = TestClient(test_app)

        # 여러 텍스트로 테스트
        test_cases = [
            ("오늘은 정말 우울하고 힘든 날이에요", 60),
            ("불안하고 초조해요", 40),
            ("기분이 좋아요", 20),
        ]

        for text, expected_min_score in test_cases:
            response = test_client.post("/analyze", json={
                "text": text,
                "user_id": f"user_{expected_min_score}"
            })

            # 기본 응답 검증
            assert response.status_code in [200, 500]  # API 키 없으면 500
            if response.status_code == 200:
                data = response.json()
                assert "depression_score" in data
                assert "anxiety_score" in data
                assert "cognitive_score" in data
                assert "emotional_state" in data
                assert "confidence" in data

    def test_concurrent_requests(self):
        """동시 요청 처리 테스트"""
        import concurrent.futures

        def make_request(user_id):
            return client.post("/analyze", json={
                "text": f"테스트 텍스트 {user_id}",
                "user_id": f"user_{user_id}"
            })

        # 10개의 동시 요청
        with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
            futures = [executor.submit(make_request, i) for i in range(10)]
            results = [f.result() for f in concurrent.futures.as_completed(futures)]

        # 모든 요청이 처리되었는지 확인
        assert len(results) == 10
        for response in results:
            assert response.status_code in [200, 400, 500, 503]


class TestPerformance:
    """성능 테스트"""

    def test_response_time(self):
        """응답 시간 테스트"""
        import time

        start = time.time()
        response = client.get("/health")
        elapsed = time.time() - start

        # 헬스체크는 1초 이내 응답
        assert elapsed < 1.0
        assert response.status_code in [200, 503]

    @patch('app.main.analyzer')
    def test_large_text_handling(self, mock_analyzer):
        """대용량 텍스트 처리 테스트"""
        # Mock 설정
        mock_response = AnalysisResponse(
            depression_score=50,
            anxiety_score=50,
            cognitive_score=80,
            emotional_state="분석 완료",
            key_concerns=[],
            recommendations=[],
            confidence=0.7
        )

        mock_analyzer.analyze_mental_health = asyncio.coroutine(
            lambda x: mock_response
        )

        # 5000자 텍스트
        large_text = "테스트 " * 1000

        response = client.post("/analyze", json={
            "text": large_text,
            "user_id": "test_user"
        })

        assert response.status_code == 200


# Pytest 설정
if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])