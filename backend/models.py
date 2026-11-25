"""
SQLAlchemy database models for the Quote Generator application.
"""

from datetime import datetime, timezone
from sqlalchemy import Column, Integer, String, Text, DateTime
from database import Base


class Quote(Base):
    """
    Quote model storing fetched quotes and timestamps.
    """
    __tablename__ = "quotes"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    external_quote_id = Column(Integer, nullable=True, index=True)
    quote_text = Column(Text, nullable=False)
    author = Column(String(255), nullable=False)
    created_at = Column(
        DateTime,
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
