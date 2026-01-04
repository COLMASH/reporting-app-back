"""
Database models for portfolio reports module.
"""

import enum
import uuid
from datetime import UTC, datetime

from sqlalchemy import (
    Boolean,
    Column,
    Date,
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


class ReportStatus(str, enum.Enum):
    """Report processing status."""

    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"


class ReportScope(str, enum.Enum):
    """Report scope selection."""

    SINGLE_DATE = "single_date"
    ALL_DATES = "all_dates"


class PortfolioReport(Base):
    """Portfolio PDF report job tracking."""

    __tablename__ = "portfolio_reports"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )

    # Report configuration
    title = Column(String(255), nullable=False, default="Portfolio Analysis Report")
    scope = Column(Enum(ReportScope), default=ReportScope.SINGLE_DATE, nullable=False)
    report_date = Column(Date, nullable=True)  # For SINGLE_DATE scope

    # Filter parameters (optional)
    entity_filter = Column(String(100), nullable=True)
    asset_type_filter = Column(String(100), nullable=True)
    holding_company_filter = Column(String(100), nullable=True)

    # User prompts
    user_prompt = Column(Text, nullable=True)  # Optional focus/instructions
    research_enabled = Column(Boolean, default=False, nullable=False)

    # Processing tracking
    status = Column(Enum(ReportStatus), default=ReportStatus.PENDING, nullable=False)
    agent_version = Column(String(20), default="1.0.0", nullable=False)

    # Results
    markdown_content = Column(Text, nullable=True)  # Generated markdown

    # Error handling
    error_message = Column(Text, nullable=True)

    # Performance metrics
    tokens_used = Column(Integer, nullable=True)
    input_tokens = Column(Integer, nullable=True)
    output_tokens = Column(Integer, nullable=True)
    processing_time_seconds = Column(Float, nullable=True)

    # Timestamps
    created_at = Column(DateTime, nullable=False, default=lambda: datetime.now(UTC))
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)

    # Relationships
    user = relationship("User", back_populates="portfolio_reports")

    def __repr__(self) -> str:
        return f"<PortfolioReport(id='{self.id}', status='{self.status}')>"
