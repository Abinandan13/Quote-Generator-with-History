"""
Comprehensive backend test suite for Module 4.
Validates endpoints, status codes, schemas, timeout/failure handling,
database persistence, and empty history conditions.
"""

import asyncio
import os
import sys
from datetime import datetime, timezone
import httpx
from unittest.mock import AsyncMock, patch, MagicMock

# Ensure backend directory is in path
sys.path.insert(0, os.path.dirname(__file__))
import main
from main import app
from database import engine, Base, SessionLocal, DB_PATH, get_db
from models import Quote

async def run_tests():
    print("=== STARTING MODULE 4 BACKEND TEST SUITE ===")

    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:

        # ── Test 1: GET /health (Healthy state) ───────────────────
        res_health = await client.get("/health")
        assert res_health.status_code == 200, f"Expected 200, got {res_health.status_code}"
        health_json = res_health.json()
        assert health_json["status"] == "healthy"
        assert health_json["database"] == "connected"
        assert "module" in health_json
        print(f"[PASS] 1. GET /health -> Status 200, DB connected: {health_json}")

        # ── Test 2: GET /health (DB failure handling -> 503) ───────
        def failing_db():
            mock = MagicMock()
            mock.execute.side_effect = Exception("Simulated DB connection failure")
            try:
                yield mock
            finally:
                pass

        app.dependency_overrides[get_db] = failing_db
        try:
            res_health_fail = await client.get("/health")
            assert res_health_fail.status_code == 503, f"Expected 503 on DB failure, got {res_health_fail.status_code}"
            print(f"[PASS] 2. GET /health on DB failure -> Status 503 ({res_health_fail.json()['detail']})")
        finally:
            app.dependency_overrides.clear()

        # ── Test 3: GET /api/quotes/random (Real fetch & persist) ──
        db = SessionLocal()
        count_before = db.query(Quote).count()
        db.close()

        res_quote = await client.get("/api/quotes/random")
        assert res_quote.status_code == 200, f"Expected 200, got {res_quote.status_code}"
        quote_json = res_quote.json()

        # Verify response structure
        assert "id" in quote_json and quote_json["id"] is not None
        assert "quote" in quote_json and len(quote_json["quote"]) > 0
        assert "author" in quote_json and len(quote_json["author"]) > 0
        assert "created_at" in quote_json and quote_json["created_at"] is not None

        db = SessionLocal()
        count_after = db.query(Quote).count()
        saved_record = db.query(Quote).filter(Quote.id == quote_json["id"]).first()
        db.close()

        assert count_after == count_before + 1, "Database count did not increase by 1"
        assert saved_record is not None, "Saved quote record not found in SQLite"
        print(f"[PASS] 3. GET /api/quotes/random -> Status 200, Saved ID #{quote_json['id']} by '{quote_json['author']}'")

        # ── Test 4: External API Timeout Handling (504) ────────────
        mock_timeout_client = MagicMock()
        mock_timeout_client.__aenter__.return_value.get = AsyncMock(
            side_effect=httpx.TimeoutException("Connection to DummyJSON timed out")
        )
        with patch("main.httpx.AsyncClient", return_value=mock_timeout_client):
            res_timeout = await client.get("/api/quotes/random")
            assert res_timeout.status_code == 504, f"Expected 504, got {res_timeout.status_code}"
            assert "detail" in res_timeout.json()
            print(f"[PASS] 4. External API Timeout -> Status 504 ({res_timeout.json()['detail']})")

        # ── Test 5: External API Failure Handling (502) ────────────
        # 5a. Network connection drop
        mock_conn_client = MagicMock()
        mock_conn_client.__aenter__.return_value.get = AsyncMock(
            side_effect=httpx.ConnectError("Network unreachable")
        )
        with patch("main.httpx.AsyncClient", return_value=mock_conn_client):
            res_conn = await client.get("/api/quotes/random")
            assert res_conn.status_code == 502, f"Expected 502, got {res_conn.status_code}"
            print(f"[PASS] 5a. External API ConnectError -> Status 502 ({res_conn.json()['detail']})")

        # 5b. Upstream HTTP 500 error
        dummy_req = httpx.Request("GET", "https://dummyjson.com/quotes/random")
        dummy_resp = httpx.Response(500, request=dummy_req)
        mock_status_client = MagicMock()
        mock_status_client.__aenter__.return_value.get = AsyncMock(
            side_effect=httpx.HTTPStatusError("Server Error", request=dummy_req, response=dummy_resp)
        )
        with patch("main.httpx.AsyncClient", return_value=mock_status_client):
            res_upstream = await client.get("/api/quotes/random")
            assert res_upstream.status_code == 502, f"Expected 502, got {res_upstream.status_code}"
            print(f"[PASS] 5b. External API Upstream 500 -> Status 502 ({res_upstream.json()['detail']})")

        # 5c. Invalid / empty quote content
        mock_empty_resp = MagicMock()
        mock_empty_resp.status_code = 200
        mock_empty_resp.json.return_value = {"id": 12, "quote": "", "author": "Nobody"}
        mock_empty_resp.raise_for_status = MagicMock()
        mock_empty_client = MagicMock()
        mock_empty_client.__aenter__.return_value.get = AsyncMock(return_value=mock_empty_resp)
        with patch("main.httpx.AsyncClient", return_value=mock_empty_client):
            res_empty = await client.get("/api/quotes/random")
            assert res_empty.status_code == 502, f"Expected 502, got {res_empty.status_code}"
            print(f"[PASS] 5c. Empty quote validation -> Status 502 ({res_empty.json()['detail']})")

        # ── Test 6: Verify Failed Requests Don't Persist ───────────
        db = SessionLocal()
        count_final = db.query(Quote).count()
        db.close()
        assert count_final == count_after, "Failed external requests incorrectly inserted records into database!"
        print(f"[PASS] 6. Safety Verified: Database count unchanged during failed requests (Count: {count_final})")

        # ── Test 7: GET /api/quotes/history (Non-empty & order) ────
        res_history = await client.get("/api/quotes/history")
        assert res_history.status_code == 200, f"Expected 200, got {res_history.status_code}"
        history_list = res_history.json()
        assert isinstance(history_list, list)
        assert len(history_list) >= 1
        # Check newest first
        if len(history_list) >= 2:
            assert history_list[0]["id"] > history_list[1]["id"]
        print(f"[PASS] 7. GET /api/quotes/history -> Status 200, Returned {len(history_list)} records newest first")

        # ── Test 8: GET /api/quotes/history (Empty condition) ──────
        def empty_db():
            mock = MagicMock()
            mock_query = MagicMock()
            mock_query.order_by.return_value.all.return_value = []
            mock.query.return_value = mock_query
            try:
                yield mock
            finally:
                pass

        app.dependency_overrides[get_db] = empty_db
        try:
            res_empty_hist = await client.get("/api/quotes/history")
            assert res_empty_hist.status_code == 200
            assert res_empty_hist.json() == [], "Expected empty list []"
            print(f"[PASS] 8. Empty history handling -> Status 200, returned empty array []")
        finally:
            app.dependency_overrides.clear()

        # ── Test 9: GET /api/quotes/history (DB Exception 500) ─────
        def error_db():
            mock = MagicMock()
            mock.query.side_effect = main.SQLAlchemyError("Query error")
            try:
                yield mock
            finally:
                pass

        app.dependency_overrides[get_db] = error_db
        try:
            res_hist_err = await client.get("/api/quotes/history")
            assert res_hist_err.status_code == 500, f"Expected 500, got {res_hist_err.status_code}"
            print(f"[PASS] 9. History DB error handling -> Status 500 ({res_hist_err.json()['detail']})")
        finally:
            app.dependency_overrides.clear()

    print("=== ALL MODULE 4 BACKEND TESTS PASSED SUCCESSFULLY ===")

if __name__ == "__main__":
    asyncio.run(run_tests())
