"""Database Engine and Session Management."""

import logging
from typing import Generator
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import settings

logger = logging.getLogger("campusiq.db")

# Create PostgreSQL database engine
engine = create_engine(
    settings.DATABASE_URL,
    pool_pre_ping=True,
    pool_size=10,
    max_overflow=20,
    echo=settings.DEBUG and False,  # Set to True if detailed SQL queries needed
)

# Session factory
SessionLocal = sessionmaker(
    bind=engine,
    autocommit=False,
    autoflush=False,
    expire_on_commit=False,
)


def get_db() -> Generator[Session, None, None]:
    """FastAPI Dependency providing a database session per request."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
