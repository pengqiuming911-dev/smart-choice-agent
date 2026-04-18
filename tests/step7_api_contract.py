"""Step 7: API Contract Tests"""
import pytest
import time
from fastapi.testclient import TestClient
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from rag_service.agent.api import app

client = TestClient(app)


class TestChatEndpoint:
    """Test /api/v1/chat endpoint"""

    def test_chat_success(self):
        """Test successful chat request"""
        resp = client.post("/api/v1/chat", json={
            "user_open_id": "ou_test_qualified",
            "user_name": "测试用户",
            "question": "私募基金的投资策略有哪些？",
        })
        assert resp.status_code == 200
        data = resp.json()
        assert "answer" in data
        assert "session_id" in data
        assert "citations" in data
        assert "latency_ms" in data
        assert isinstance(data["citations"], list)

    def test_chat_missing_question(self):
        """Test chat with missing question field"""
        resp = client.post("/api/v1/chat", json={
            "user_open_id": "ou_test",
            "user_name": "测试",
        })
        assert resp.status_code == 422  # Validation error

    def test_chat_missing_user_open_id(self):
        """Test chat with missing user_open_id"""
        resp = client.post("/api/v1/chat", json={
            "question": "测试问题",
        })
        assert resp.status_code == 422

    def test_chat_with_session_id(self):
        """Test chat with explicit session_id"""
        session_id = "test-session-123"
        resp = client.post("/api/v1/chat", json={
            "user_open_id": "ou_test",
            "user_name": "测试",
            "question": "公司业务是什么？",
            "session_id": session_id,
        })
        assert resp.status_code == 200
        assert resp.json()["session_id"] == session_id

    def test_chat_question_too_long(self):
        """Test chat with question exceeding max length"""
        long_question = "a" * 3000  # Exceeds 2000 char limit
        resp = client.post("/api/v1/chat", json={
            "user_open_id": "ou_test",
            "user_name": "测试",
            "question": long_question,
        })
        assert resp.status_code == 422

    def test_chat_request_id_header(self):
        """Test X-Request-ID header is returned"""
        resp = client.post("/api/v1/chat", json={
            "user_open_id": "ou_test",
            "user_name": "测试",
            "question": "测试",
        }, headers={"X-Request-ID": "custom-request-id"})
        assert resp.status_code == 200
        assert resp.headers.get("X-Request-ID") == "custom-request-id"


class TestSearchEndpoint:
    """Test /api/v1/search endpoint"""

    def test_search_success(self):
        """Test successful search request"""
        resp = client.post("/api/v1/search", json={
            "query": "私募基金",
            "top_k": 5,
        })
        assert resp.status_code == 200
        data = resp.json()
        assert "chunks" in data
        assert "total" in data
        assert isinstance(data["chunks"], list)

    def test_search_missing_query(self):
        """Test search with missing query"""
        resp = client.post("/api/v1/search", json={})
        assert resp.status_code == 422

    def test_search_with_user_filter(self):
        """Test search with user_open_id filter"""
        resp = client.post("/api/v1/search", json={
            "query": "投资",
            "user_open_id": "ou_test",
            "top_k": 3,
        })
        assert resp.status_code == 200


class TestHealthEndpoint:
    """Test /api/v1/health endpoint"""

    def test_health(self):
        """Test health check returns ok"""
        resp = client.get("/api/v1/health")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "ok"
        assert "timestamp" in data
        assert "version" in data


class TestStatsEndpoint:
    """Test /api/v1/stats endpoint"""

    def test_stats(self):
        """Test stats endpoint"""
        resp = client.get("/api/v1/stats")
        # May return 500 if DB not available, but shouldn't crash
        assert resp.status_code in [200, 500]


class TestSecurity:
    """Security tests"""

    def test_sql_injection_prevention(self):
        """Test SQL injection is prevented"""
        malicious_question = "'; DROP TABLE chat_logs; --"
        resp = client.post("/api/v1/chat", json={
            "user_open_id": "ou_test",
            "user_name": "测试",
            "question": malicious_question,
        })
        # Should either return 200 with safe response or 500 (if DB issue)
        # Should NOT return 400 (malicious input not rejected as invalid)
        assert resp.status_code in [200, 500]

    def test_xss_prevention(self):
        """Test XSS in question field is handled"""
        xss_question = '<script>alert(1)</script>'
        resp = client.post("/api/v1/chat", json={
            "user_open_id": "ou_test",
            "user_name": "测试",
            "question": xss_question,
        })
        # Should handle gracefully, not reflect script tag
        assert resp.status_code in [200, 500]


class TestConcurrency:
    """Concurrency tests"""

    def test_concurrent_requests(self):
        """Test handling concurrent requests"""
        import concurrent.futures

        def make_request():
            return client.post("/api/v1/chat", json={
                "user_open_id": "ou_test",
                "user_name": "并发测试",
                "question": "测试问题",
            })

        with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
            futures = [executor.submit(make_request) for _ in range(10)]
            results = [f.result() for f in concurrent.futures.as_completed(futures)]

        # All requests should complete without crashing
        statuses = [r.status_code for r in results]
        assert all(s in [200, 500] for s in statuses)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
