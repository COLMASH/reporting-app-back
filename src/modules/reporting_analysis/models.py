"""
Database models for analysis module.
"""

import enum
import uuid
from datetime import UTC, datetime

from sqlalchemy import JSON, Column, DateTime, Enum, Float, ForeignKey, Integer, String, Text
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


class AgentType(str, enum.Enum):
    """Types of AI agents available."""

    EXCEL_ANALYZER = "excel_analyzer"
    CHART_RECOMMENDER = "chart_recommender"
    DATA_CLASSIFIER = "data_classifier"
    INSIGHT_GENERATOR = "insight_generator"


class Analysis(Base):
    """Analysis job tracking and results."""

    __tablename__ = "reporting_analyses"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    file_id = Column(
        UUID(as_uuid=True),
        ForeignKey("reporting_file_uploads.id", ondelete="CASCADE"),
        nullable=False
    )

    # Analysis configuration
    agent_type: Column[AgentType] = Column(Enum(AgentType), nullable=False)
    agent_version = Column(String, default="1.0.0", nullable=False)
    parameters = Column(JSON, nullable=True)  # Agent-specific parameters

    # Processing tracking
    status: Column[AnalysisStatus] = Column(
        Enum(AnalysisStatus), default=AnalysisStatus.PENDING, nullable=False
    )
    progress = Column(Float, default=0.0, nullable=False)  # 0.0 to 1.0
    progress_message = Column(String, nullable=True)

    # Results and errors
    error_message = Column(Text, nullable=True)
    error_details = Column(JSON, nullable=True)

    # Performance metrics
    tokens_used = Column(Integer, nullable=True)
    processing_time_seconds = Column(Float, nullable=True)

    # Background job tracking
    celery_task_id = Column(String, nullable=True, unique=True)

    # Timestamps
    created_at = Column(DateTime, nullable=False, default=lambda: datetime.now(UTC))
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)

    # Relationships
    file = relationship("FileUpload", back_populates="analyses")
    results = relationship("Result", back_populates="analysis", cascade="all, delete-orphan")

    def __repr__(self) -> str:
        return f"<Analysis(agent_type='{self.agent_type}', status='{self.status}')>"
