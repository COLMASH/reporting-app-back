"""
Database models for reporting analysis module.
"""

import enum
import uuid
from datetime import UTC, datetime

from sqlalchemy import (
    JSON,
    Column,
    DateTime,
    Enum,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from src.core.database.core import Base


class AnalysisStatus(str, enum.Enum):
    """Analysis processing status."""

    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class Analysis(Base):
    """Analysis job tracking and results."""

    __tablename__ = "reporting_analyses"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    file_id = Column(
        UUID(as_uuid=True),
        ForeignKey("files.id", ondelete="CASCADE"),
        nullable=False,
    )

    # Analysis configuration
    agent_version = Column(String, default="1.0.0", nullable=False)
    parameters = Column(JSON, nullable=True)  # Agent-specific parameters

    # Processing tracking
    status = Column(Enum(AnalysisStatus), default=AnalysisStatus.PENDING, nullable=False)

    # Results and errors
    error_message = Column(Text, nullable=True)

    # Performance metrics
    tokens_used = Column(Integer, nullable=True)
    processing_time_seconds = Column(Float, nullable=True)

    # Timestamps
    created_at = Column(DateTime, nullable=False, default=lambda: datetime.now(UTC))
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)

    # Relationships
    file = relationship("File", back_populates="analyses")
    results = relationship("Result", back_populates="analysis", cascade="all, delete-orphan")

    def __repr__(self) -> str:
        return f"<Analysis(id='{self.id}', status='{self.status}')>"
