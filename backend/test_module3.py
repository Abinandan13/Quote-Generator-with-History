import asyncio
import os
import sys
from datetime import datetime, timezone
import httpx
from unittest.mock import AsyncMock, patch, MagicMock

sys.path.insert(0, os.path.dirname(__file__))
import main
from main import app
from database import engine, Base, SessionLocal, DB_PATH
from models import Quote

async def run_tests():
    print("=== RUNNING MODULE 3 DATABASE & API TESTS ===")

    # Test 1: Database file & table creation
    assert os.path.exists(DB_PATH), f"Database file not found at {DB_PATH}"
    print(f"[PASS] Database file verified at: {DB_PATH}")

    # Inspect tables using SQLAlchemy
    Base.metadata.create_all(bind=engine)
    table_names = list(Base.metadata.tables.keys())
    assert "quotes" in table_names, "quotes table missing from metadata"
    print(f"[PASS] SQLAlchemy metadata tables: {table_names}")

    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
        # Test 2: Health check with database connectivity
        res_health = await client.get("/health")
        assert res_health.status_code == 200, f"Health check failed: {res_health.status_code}"
        health_data = res_health.json()
        assert health_data.get("database") == "connected", f"Database not connected: {health_data}"
        print(f"[PASS] GET /health -> {res_health.status_code} {health_data}")

        # Record initial count
        db = SessionLocal()
        initial_count = db.query(Quote).count()
        db.close()
        print(f"[INFO] Initial database quote count: {initial_count}")

        # Test 3: Save Quotes Automatically via GET /api/quotes/random
        res1 = await client.get("/api/quotes/random")
        assert res1.status_code == 200, f"Quote fetch failed: {res1.status_code}"
        q1_data = res1.json()
        assert q1_data.get("id") is not None, "Saved quote missing id"
        assert q1_data.get("quote"), "Missing quote text"
        assert q1_data.get("author"), "Missing author"
        assert q1_data.get("created_at"), "Missing created_at"
        print(f"[PASS] 1st Quote fetched & saved: ID={q1_data['id']}, Author='{q1_data['author']}'")

        # Verify DB count increased by 1
        db = SessionLocal()
        count_after_1 = db.query(Quote).count()
        db.close()
        assert count_after_1 == initial_count + 1, f"Expected count {initial_count + 1}, got {count_after_1}"
        print(f"[PASS] Database record inserted (Count: {count_after_1})")

        # Test 4: Fetch a second quote to verify multiple quotes and order
        res2 = await client.get("/api/quotes/random")
        assert res2.status_code == 200, f"Quote fetch 2 failed: {res2.status_code}"
        q2_data = res2.json()
        print(f"[PASS] 2nd Quote fetched & saved: ID={q2_data['id']}, Author='{q2_data['author']}'")

        # Test 5: Verify GET /api/quotes/history returns newest first
        res_hist = await client.get("/api/quotes/history")
        assert res_hist.status_code == 200, f"History fetch failed: {res_hist.status_code}"
        history = res_hist.json()
        assert isinstance(history, list), "History must be an array"
        assert len(history) >= 2, f"Expected at least 2 history items, got {len(history)}"

        # The newest quote (q2) must appear before the earlier quote (q1)
        first_in_hist = history[0]
        second_in_hist = history[1]
        assert first_in_hist["id"] == q2_data["id"], f"Expected newest ID {q2_data['id']} first, got {first_in_hist['id']}"
        assert second_in_hist["id"] == q1_data["id"], f"Expected earlier ID {q1_data['id']} second, got {second_in_hist['id']}"
        print(f"[PASS] GET /api/quotes/history correctly returns newest first:")
        print(f"       1st in history: ID={first_in_hist['id']} ({first_in_hist['author']})")
        print(f"       2nd in history: ID={second_in_hist['id']} ({second_in_hist['author']})")

        # Test 6: Verify duplicate quote text creates separate history records
        # Mock DummyJSON returning an identical quote
        mock_duplicate_resp = MagicMock()
        mock_duplicate_resp.status_code = 200
        mock_duplicate_resp.json.return_value = {
            "id": 9999,
            "quote": "Repeated wisdom is double wisdom.",
            "author": "Test Author"
        }
        mock_duplicate_resp.raise_for_status = MagicMock()

        mock_client = MagicMock()
        mock_client.__aenter__.return_value.get = AsyncMock(return_value=mock_duplicate_resp)

        with patch("main.httpx.AsyncClient", return_value=mock_client):
            # Fetch same quote twice
            dup1 = await client.get("/api/quotes/random")
            dup2 = await client.get("/api/quotes/random")
            assert dup1.status_code == 200 and dup2.status_code == 200
            d1_data = dup1.json()
            d2_data = dup2.json()
            assert d1_data["id"] != d2_data["id"], "Duplicate quotes must receive unique primary keys"
            assert d1_data["quote"] == d2_data["quote"], "Quote texts should match"
            print(f"[PASS] Duplicate quote saved as separate records: IDs {d1_data['id']} and {d2_data['id']}")

        # Test 7: API Failure does NOT create a database record
        db = SessionLocal()
        count_before_fail = db.query(Quote).count()
        db.close()

        mock_fail_client = MagicMock()
        mock_fail_client.__aenter__.return_value.get = AsyncMock(side_effect=httpx.TimeoutException("Timed out"))
        with patch("main.httpx.AsyncClient", return_value=mock_fail_client):
            res_fail = await client.get("/api/quotes/random")
            assert res_fail.status_code == 504, f"Expected 504, got {res_fail.status_code}"

        db = SessionLocal()
        count_after_fail = db.query(Quote).count()
        db.close()
        assert count_after_fail == count_before_fail, f"Failed API request created a record! Before: {count_before_fail}, After: {count_after_fail}"
        print(f"[PASS] External API failure (504) did NOT create any database record (Count: {count_after_fail})")

        # Test 8: Browser refresh simulation (data persists across new session queries)
        db_new = SessionLocal()
        persisted_quote = db_new.query(Quote).filter(Quote.id == q1_data["id"]).first()
        assert persisted_quote is not None, "Quote was not persisted in SQLite file"
        assert persisted_quote.quote_text == q1_data["quote"], "Persisted quote text mismatch"
        db_new.close()
        print(f"[PASS] Persistence verified across sessions in SQLite database file")

    print("=== ALL MODULE 3 DATABASE & API TESTS PASSED ===")

if __name__ == "__main__":
    asyncio.run(run_tests())
