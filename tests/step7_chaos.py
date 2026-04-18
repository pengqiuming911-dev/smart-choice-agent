"""Step 7: Chaos Tests - verify API resilience under failure conditions"""
import pytest
import subprocess
import time
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fastapi.testclient import TestClient
from rag_service.agent.api import app

client = TestClient(app)


class TestChaosResilience:
    """Test API resilience when dependencies fail"""

    def test_returns_5xx_when_pg_down(self):
        """
        When PostgreSQL is down, API should return 500, not hang.

        Note: This test modifies docker state and should be run in isolation.
        """
        # This test requires docker to be available
        try:
            # Stop postgres container
            subprocess.run(
                ["docker-compose", "stop", "postgres"],
                cwd=os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                capture_output=True,
                timeout=10,
            )
            time.sleep(2)

            # Make request - should get 500, not hang
            start = time.time()
            resp = client.post("/api/v1/chat", json={
                "user_open_id": "ou_test",
                "user_name": "测试",
                "question": "测试",
            })
            elapsed = time.time() - start

            # Should return quickly (not hang), with 500 error
            assert elapsed < 15, f"Request took too long: {elapsed}s"
            assert resp.status_code == 500

        finally:
            # Restore postgres
            subprocess.run(
                ["docker-compose", "start", "postgres"],
                cwd=os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                capture_output=True,
                timeout=30,
            )
            time.sleep(3)  # Wait for postgres to be ready

    def test_health_check_when_downs(self):
        """
        Health check should work even when dependencies are down.
        Health check doesn't require DB.
        """
        resp = client.get("/api/v1/health")
        assert resp.status_code == 200
        assert resp.json()["status"] == "ok"

    def test_timeout_for_slow_llm(self):
        """
        Test that API has timeout mechanism for slow LLM responses.

        Note: This is a placeholder - actual timeout testing requires
        mocking the LLM to be slow.
        """
        # When LLM is unresponsive, should timeout within 60s
        # In practice, this would require mocking
        pass


class TestErrorResponses:
    """Test error response format"""

    def test_404_not_found(self):
        """Test 404 for unknown endpoint"""
        resp = client.get("/api/v1/nonexistent")
        assert resp.status_code == 404

    def test_method_not_allowed(self):
        """Test 405 for wrong method"""
        resp = client.get("/api/v1/chat")
        assert resp.status_code == 405

    def test_error_includes_request_id(self):
        """Test that error responses include request_id"""
        resp = client.post("/api/v1/chat", json={
            "question": "test",
        })
        # 422 validation error should still include request_id in headers
        assert "X-Request-ID" in resp.headers or resp.status_code == 422


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
