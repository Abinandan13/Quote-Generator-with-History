"""
Quote Generator – Module 4 (Backend, Error Handling & Persistence)

FastAPI server that:
1. Proxies random quotes from DummyJSON API with robust error handling.
2. Automatically saves fetched quotes to SQLite via SQLAlchemy.
3. Provides a history endpoint returning quotes newest first.
4. Comprehensive health checks and graceful failure handling.
"""

import os
from datetime import datetime, timezone
from typing import List, Optional
from fastapi import FastAPI, HTTPException, Depends, status
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import httpx
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy import select

from database import engine, Base, get_db
from models import Quote

# Ensure all database tables are created on application startup
Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="Quote Generator API",
    version="1.0.0",
    description="Backend for the Quote Generator with History application (Module 4 – Testing & Polish).",
)

# ── CORS ──────────────────────────────────────────────────────
# Allow frontend served from file://, localhost, or any static server
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Constants ─────────────────────────────────────────────────
DUMMYJSON_URL = "https://dummyjson.com/quotes/random"
REQUEST_TIMEOUT = 10.0  # seconds


# ── Pydantic Schemas ──────────────────────────────────────────

class QuoteResponse(BaseModel):
    id: Optional[int] = None
    external_id: Optional[int] = None
    external_quote_id: Optional[int] = None
    quote: str
    quote_text: str
    text: str
    author: str
    created_at: Optional[str] = None

    class Config:
        from_attributes = True


class HealthResponse(BaseModel):
    status: str
    module: str
    database: str


# ── Endpoints ─────────────────────────────────────────────────

@app.get("/health", response_model=HealthResponse)
async def health_check(db: Session = Depends(get_db)):
    """
    Check backend health and verify database connectivity.
    Returns 200 if healthy, 503 if database connection fails.
    """
    try:
        # Verify database read connectivity
        db.execute(select(Quote.id).limit(1))
        db_status = "connected"
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Database service unavailable: {str(exc)}",
        )

    return HealthResponse(
        status="healthy",
        module="Module 4 – Testing, Error Handling and Final Polish",
        database=db_status,
    )


@app.get("/api/quotes/random", response_model=QuoteResponse)
async def get_random_quote(db: Session = Depends(get_db)):
    """
    Fetch a random quote from DummyJSON, save it in SQLite, and return it.
    Failed external requests are not saved to the database.
    Each successful fetch creates a separate record even if duplicate text.
    """
    # 1. Fetch from DummyJSON API with timeout and error mapping
    try:
        async with httpx.AsyncClient(timeout=REQUEST_TIMEOUT) as client:
            response = await client.get(DUMMYJSON_URL)
            response.raise_for_status()
    except httpx.TimeoutException:
        raise HTTPException(
            status_code=status.HTTP_504_GATEWAY_TIMEOUT,
            detail="The external quote service timed out. Please try again.",
        )
    except httpx.HTTPStatusError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"External quote service returned an error (status {exc.response.status_code}).",
        )
    except httpx.RequestError:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Unable to reach the external quote service. Please verify internet connection.",
        )

    # 2. Parse and validate response
    try:
        data = response.json()
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="External quote service returned an invalid JSON response.",
        )

    quote_content = str(data.get("quote", "")).strip()
    author_name = str(data.get("author", "Unknown")).strip() or "Unknown"
    external_id = data.get("id")

    if not quote_content:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="External quote service returned an empty quote.",
        )

    # 3. Persist to SQLite using SQLAlchemy in a safe transaction
    try:
        new_quote = Quote(
            external_quote_id=external_id,
            quote_text=quote_content,
            author=author_name,
            created_at=datetime.now(timezone.utc),
        )
        db.add(new_quote)
        db.commit()
        db.refresh(new_quote)
    except SQLAlchemyError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to save quote to the database.",
        )

    # 4. Return saved quote with formatted fields
    created_iso = new_quote.created_at.isoformat() if new_quote.created_at else None
    return QuoteResponse(
        id=new_quote.id,
        external_id=new_quote.external_quote_id,
        external_quote_id=new_quote.external_quote_id,
        quote=new_quote.quote_text,
        quote_text=new_quote.quote_text,
        text=new_quote.quote_text,
        author=new_quote.author,
        created_at=created_iso,
    )


@app.get("/api/quotes/history", response_model=List[QuoteResponse])
async def get_quote_history(db: Session = Depends(get_db)):
    """
    Retrieve all saved quotes from SQLite, ordered newest first.
    Returns an empty array if no history exists.
    """
    try:
        quotes = (
            db.query(Quote)
            .order_by(Quote.created_at.desc(), Quote.id.desc())
            .all()
        )
    except SQLAlchemyError:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve quote history from database.",
        )

    return [
        QuoteResponse(
            id=q.id,
            external_id=q.external_quote_id,
            external_quote_id=q.external_quote_id,
            quote=q.quote_text,
            quote_text=q.quote_text,
            text=q.quote_text,
            author=q.author,
            created_at=q.created_at.isoformat() if q.created_at else None,
        )
        for q in quotes
    ]
