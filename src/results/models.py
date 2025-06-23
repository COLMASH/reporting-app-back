"""
Database models for results module.
"""

import enum
import uuid
from datetime import UTC, datetime

from sqlalchemy import (
    JSON,
    Boolean,
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

from src.database.core import Base


class ChartType(str, enum.Enum):
    """Supported chart types for visualization."""

    BAR = "bar"
    LINE = "line"
    PIE = "pie"
    SCATTER = "scatter"
    HEATMAP = "heatmap"
    TABLE = "table"
    KPI = "kpi"
    AREA = "area"
    RADAR = "radar"
    TREEMAP = "treemap"


class Result(Base):
    """Individual analysis results (charts, insights, etc.)."""

    __tablename__ = "results"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    analysis_id = Column(
        UUID(as_uuid=True), ForeignKey("analyses.id", ondelete="CASCADE"), nullable=False
    )

    # Result metadata
    result_type = Column(String, nullable=False)  # "chart", "insight", "summary", "metric"
    title = Column(String, nullable=False)
    description = Column(Text, nullable=True)

    # Chart-specific fields
    chart_type: Column[ChartType | None] = Column(Enum(ChartType), nullable=True)
    chart_data = Column(JSON, nullable=True)  # Structured data for chart rendering
    chart_config = Column(JSON, nullable=True)  # Chart configuration (colors, labels, etc.)

    # Insight-specific fields
    insight_text = Column(Text, nullable=True)
    confidence_score = Column(Float, nullable=True)  # 0.0 to 1.0

    # Display configuration
    order_index = Column(Integer, default=0, nullable=False)  # For ordering results
    is_primary = Column(Boolean, default=False, nullable=False)  # Primary/featured result
    display_size = Column(String, default="medium", nullable=False)  # small, medium, large, full

    # Additional metadata
    extra_metadata = Column(JSON, nullable=True)  # Flexible field for additional data

    # Timestamps
    created_at = Column(DateTime, nullable=False, default=lambda: datetime.now(UTC))

    # Relationships
    analysis = relationship("Analysis", back_populates="results")

    def __repr__(self) -> str:
        return f"<Result(type='{self.result_type}', title='{self.title}')>"
