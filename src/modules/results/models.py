"""
Database models for results module.
"""

import uuid
from datetime import UTC, datetime

from sqlalchemy import (
    JSON,
    Column,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from src.core.database.core import Base


class Result(Base):
    """Individual analysis results (charts, insights, etc.)."""

    __tablename__ = "results"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    analysis_id = Column(UUID(as_uuid=True), ForeignKey("reporting_analyses.id", ondelete="CASCADE"), nullable=False)

    # Result metadata
    # Result types: "visualization", "metrics", "summary", "data_quality", "recommendations"
    result_type = Column(String, nullable=False)
    title = Column(String, nullable=False)
    description = Column(Text, nullable=True)

    # Content fields (use one based on result_type)
    insight_text = Column(Text, nullable=True)  # For text-based results (summary, recommendations)
    insight_data = Column(JSON, nullable=True)  # For structured data

    # Display configuration
    order_index = Column(Integer, default=0, nullable=False)  # For ordering results

    # Timestamps
    created_at = Column(DateTime, nullable=False, default=lambda: datetime.now(UTC))

    # Relationships
    analysis = relationship("Analysis", back_populates="results")

    def __repr__(self) -> str:
        return f"<Result(type='{self.result_type}', title='{self.title}')>"
