"""
Database models for reporting module.
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

from src.core.database.core import Base


class FileStatus(str, enum.Enum):
    """File processing status."""

    UPLOADED = "uploaded"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class DataClassification(str, enum.Enum):
    """Data classification types."""

    PORTFOLIO = "portfolio"
    OPERATIONS = "operations"
    PROJECT_MANAGEMENT = "project_management"
    FINANCE = "finance"
    OTHER = "other"


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


class FileUpload(Base):
    """File upload tracking and metadata."""

    __tablename__ = "reporting_file_uploads"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)

    # File information
    filename = Column(String, nullable=False)
    original_filename = Column(String, nullable=False)
    file_size = Column(Integer, nullable=True)  # Size in bytes
    mime_type = Column(String, nullable=True)
    file_extension = Column(String, nullable=False)

    # Supabase storage
    supabase_bucket = Column(String, nullable=False)
    supabase_path = Column(String, nullable=False, unique=True)

    # Business metadata
    company_name = Column(String, nullable=False)
    department = Column(String, nullable=True)
    data_classification = Column(Enum(DataClassification), nullable=True)

    # Processing status
    status = Column(Enum(FileStatus), default=FileStatus.UPLOADED, nullable=False)
    error_message = Column(Text, nullable=True)
    processing_started_at = Column(DateTime, nullable=True)
    processing_completed_at = Column(DateTime, nullable=True)

    # Timestamps
    created_at = Column(DateTime, nullable=False, default=lambda: datetime.now(UTC))
    updated_at = Column(DateTime, nullable=True, onupdate=lambda: datetime.now(UTC))

    # Relationships
    user = relationship("User", back_populates="files")
    analyses = relationship("Analysis", back_populates="file", cascade="all, delete-orphan")

    def __repr__(self) -> str:
        return f"<FileUpload(filename='{self.filename}', status='{self.status}')>"


class Analysis(Base):
    """Analysis job tracking and results."""

    __tablename__ = "reporting_analyses"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    file_id = Column(
        UUID(as_uuid=True),
        ForeignKey("reporting_file_uploads.id", ondelete="CASCADE"),
        nullable=False,
    )

    # Analysis configuration
    agent_type = Column(Enum(AgentType), nullable=False)
    agent_version = Column(String, default="1.0.0", nullable=False)
    parameters = Column(JSON, nullable=True)  # Agent-specific parameters

    # Processing tracking
    status = Column(Enum(AnalysisStatus), default=AnalysisStatus.PENDING, nullable=False)
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


class Result(Base):
    """Individual analysis results (charts, insights, etc.)."""

    __tablename__ = "reporting_results"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    analysis_id = Column(
        UUID(as_uuid=True), ForeignKey("reporting_analyses.id", ondelete="CASCADE"), nullable=False
    )

    # Result metadata
    result_type = Column(String, nullable=False)  # "chart", "insight", "summary", "metric"
    title = Column(String, nullable=False)
    description = Column(Text, nullable=True)

    # Chart-specific fields
    chart_type = Column(Enum(ChartType), nullable=True)
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
