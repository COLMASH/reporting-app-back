"""
Database configuration and session management.
"""

from collections.abc import Generator
from typing import Annotated, Any

from fastapi import Depends
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, declarative_base, sessionmaker
from sqlalchemy.pool import NullPool

from src.config import settings

# Database engine configuration
engine_kwargs: dict[str, Any] = {}
if settings.is_production:
    # Use connection pooling in production
    engine_kwargs = {
        "pool_size": 10,
        "max_overflow": 20,
        "pool_pre_ping": True,
        "pool_recycle": 3600,
    }
else:
    # Disable pooling in development for easier debugging
    engine_kwargs = {"poolclass": NullPool}

# Create database engine
engine = create_engine(
    settings.database_url,
    echo=settings.debug,
    **engine_kwargs,  # Log SQL queries in debug mode
)

# Create session factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Create declarative base for models
Base = declarative_base()


def get_db() -> Generator[Session, None, None]:
    """
    Dependency to get database session.
    Ensures session is closed after request.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# Type alias for dependency injection
DbSession = Annotated[Session, Depends(get_db)]
