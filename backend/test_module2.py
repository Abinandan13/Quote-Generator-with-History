import asyncio
import httpx
from unittest.mock import AsyncMock, patch, MagicMock
import sys
import os

# Ensure backend directory is in path
sys.path.insert(0, os.path.dirname(__file__))
import main
from main import app

async def run_tests():
    print("=== RUNNING MODULE 2 BACKEND TESTS ===")
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as test_client:
        # 1. Health check
        res = await test_client.get("/health")
        assert res.status_code == 200, f"Health endpoint failed: {res.status_code}"
        print(f"[PASS] GET /health -> {res.status_code} {res.json()}")

        # 2. Real quote fetching from DummyJSON
        res = await test_client.get("/api/quotes/random")
        assert res.status_code == 200, f"Quote endpoint failed: {res.status_code}"
        data = res.json()
        assert "quote" in data and len(data["quote"]) > 0, "Missing or empty quote"
        assert "author" in data, "Missing author field"
        assert "external_id" in data, "Missing external_id field"
        print(f"[PASS] GET /api/quotes/random -> {res.status_code}")
        print(f"       Quote: \"{data['quote']}\"")
        print(f"       Author: {data['author']}")
        print(f"       External ID: {data['external_id']}")

        # 3. Timeout handling (504)
        mock_timeout_client = MagicMock()
        mock_timeout_client.__aenter__.return_value.get = AsyncMock(side_effect=httpx.TimeoutException("Connection timed out"))
        with patch("main.httpx.AsyncClient", return_value=mock_timeout_client):
            res_timeout = await test_client.get("/api/quotes/random")
            assert res_timeout.status_code == 504, f"Expected 504, got {res_timeout.status_code}"
            print(f"[PASS] Timeout Exception -> {res_timeout.status_code} {res_timeout.json()}")

        # 4. Connection / Network failure handling (502)
        mock_conn_client = MagicMock()
        mock_conn_client.__aenter__.return_value.get = AsyncMock(side_effect=httpx.ConnectError("Connection refused"))
        with patch("main.httpx.AsyncClient", return_value=mock_conn_client):
            res_conn = await test_client.get("/api/quotes/random")
            assert res_conn.status_code == 502, f"Expected 502, got {res_conn.status_code}"
            print(f"[PASS] Network ConnectError -> {res_conn.status_code} {res_conn.json()}")

        # 5. Upstream HTTP 500 error handling (502)
        dummy_req = httpx.Request("GET", "https://dummyjson.com/quotes/random")
        dummy_resp = httpx.Response(500, request=dummy_req)
        mock_http_err_client = MagicMock()
        mock_http_err_client.__aenter__.return_value.get = AsyncMock(side_effect=httpx.HTTPStatusError("Server Error", request=dummy_req, response=dummy_resp))
        with patch("main.httpx.AsyncClient", return_value=mock_http_err_client):
            res_status = await test_client.get("/api/quotes/random")
            assert res_status.status_code == 502, f"Expected 502, got {res_status.status_code}"
            print(f"[PASS] Upstream HTTPStatusError 500 -> {res_status.status_code} {res_status.json()}")

    print("=== ALL BACKEND TESTS PASSED SUCCESSFULLY ===")

if __name__ == "__main__":
    asyncio.run(run_tests())
