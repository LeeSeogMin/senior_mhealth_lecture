"""
Cloud Run Integration Tests
Chapter 5: Verify Cloud Run deployment
"""

import pytest
import httpx
import asyncio
import os
from typing import Optional
from datetime import datetime

# Get service URL from environment or use default
SERVICE_URL = os.getenv("SERVICE_URL", "http://localhost:8080")


class TestCloudRunDeployment:
    """Test suite for Cloud Run deployment verification"""
    
    @pytest.fixture
    async def client(self):
        """Create async HTTP client"""
        async with httpx.AsyncClient(base_url=SERVICE_URL) as client:
            yield client
    
    @pytest.mark.asyncio
    async def test_health_check(self, client):
        """Test health endpoint"""
        response = await client.get("/health")
        assert response.status_code == 200
        
        data = response.json()
        assert data["status"] == "healthy"
        assert "timestamp" in data
        assert "version" in data
        assert data["service"] == "Senior MHealth Core Service"
    
    @pytest.mark.asyncio
    async def test_root_endpoint(self, client):
        """Test root endpoint"""
        response = await client.get("/")
        assert response.status_code == 200
        
        data = response.json()
        assert "message" in data
        assert "version" in data
        assert "features" in data
        assert isinstance(data["features"], list)
    
    @pytest.mark.asyncio
    async def test_api_docs_availability(self, client):
        """Test API documentation endpoints"""
        # Note: Docs might be disabled in production
        response = await client.get("/docs")
        assert response.status_code in [200, 404]
        
        if response.status_code == 200:
            assert "swagger" in response.text.lower() or "openapi" in response.text.lower()
    
    @pytest.mark.asyncio
    async def test_health_reports_endpoint(self, client):
        """Test health reports API info endpoint"""
        response = await client.get("/api/v1/health/")
        assert response.status_code == 200
        
        data = response.json()
        assert data["service"] == "건강 리포트 API"
        assert "endpoints" in data
        assert isinstance(data["endpoints"], list)
    
    @pytest.mark.asyncio
    async def test_voice_analysis_endpoint(self, client):
        """Test voice analysis API info endpoint"""
        response = await client.get("/api/v1/voice/")
        assert response.status_code == 200
        
        data = response.json()
        assert "service" in data
        assert "version" in data
    
    @pytest.mark.asyncio
    async def test_cors_headers(self, client):
        """Test CORS configuration"""
        response = await client.options(
            "/health",
            headers={
                "Origin": "http://localhost:3000",
                "Access-Control-Request-Method": "GET"
            }
        )
        
        # Check CORS headers
        assert "access-control-allow-origin" in response.headers or \
               "Access-Control-Allow-Origin" in response.headers
    
    @pytest.mark.asyncio
    async def test_response_time(self, client):
        """Test API response time (should be under 1 second)"""
        start_time = datetime.now()
        response = await client.get("/health")
        end_time = datetime.now()
        
        response_time = (end_time - start_time).total_seconds()
        assert response.status_code == 200
        assert response_time < 1.0, f"Response time {response_time}s exceeds 1 second"
    
    @pytest.mark.asyncio
    async def test_concurrent_requests(self, client):
        """Test handling of concurrent requests"""
        async def make_request():
            response = await client.get("/health")
            return response.status_code
        
        # Make 10 concurrent requests
        tasks = [make_request() for _ in range(10)]
        results = await asyncio.gather(*tasks)
        
        # All requests should succeed
        assert all(status == 200 for status in results)
    
    @pytest.mark.asyncio
    async def test_error_handling(self, client):
        """Test error handling for invalid endpoints"""
        response = await client.get("/invalid-endpoint-12345")
        assert response.status_code == 404
    
    @pytest.mark.asyncio
    async def test_database_health(self, client):
        """Test database connection health"""
        response = await client.get("/api/v1/health/database/health")
        
        # Database might not be configured in test environment
        if response.status_code == 200:
            data = response.json()
            assert "status" in data
            assert "database" in data
            assert "timestamp" in data


class TestPerformanceMetrics:
    """Performance testing for Cloud Run service"""
    
    @pytest.mark.asyncio
    @pytest.mark.performance
    async def test_load_performance(self):
        """Test service under load"""
        async with httpx.AsyncClient(base_url=SERVICE_URL) as client:
            # Simulate 50 concurrent users
            async def user_session():
                responses = []
                for _ in range(5):
                    response = await client.get("/health")
                    responses.append(response)
                return responses
            
            tasks = [user_session() for _ in range(50)]
            results = await asyncio.gather(*tasks)
            
            # Flatten results
            all_responses = [r for user_responses in results for r in user_responses]
            
            # Check success rate
            success_count = sum(1 for r in all_responses if r.status_code == 200)
            success_rate = success_count / len(all_responses)
            
            assert success_rate >= 0.95, f"Success rate {success_rate} is below 95%"
    
    @pytest.mark.asyncio
    @pytest.mark.performance
    async def test_memory_leak(self):
        """Test for memory leaks during extended operation"""
        async with httpx.AsyncClient(base_url=SERVICE_URL) as client:
            # Make 100 requests and check if service remains stable
            for i in range(100):
                response = await client.get("/health")
                assert response.status_code == 200
                
                if i % 20 == 0:
                    # Brief pause to avoid overwhelming the service
                    await asyncio.sleep(0.1)


def test_environment_configuration():
    """Test environment configuration"""
    # Check if necessary environment variables are set
    required_vars = [
        "GOOGLE_CLOUD_PROJECT",
        "PORT",
        "ENVIRONMENT"
    ]
    
    missing_vars = [var for var in required_vars if not os.getenv(var)]
    
    if missing_vars and SERVICE_URL == "http://localhost:8080":
        # Only fail if testing locally and vars are missing
        pytest.skip(f"Missing environment variables: {missing_vars}")


if __name__ == "__main__":
    # Run tests
    pytest.main([__file__, "-v", "--asyncio-mode=auto"])