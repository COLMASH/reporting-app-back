"""
Database models for files module.
"""

import enum
import uuid
from datetime import UTC, datetime

from sqlalchemy import (
    Column,
    DateTime,
    Enum,
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


class File(Base):
    """File upload tracking and metadata."""

    __tablename__ = "files"

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

    # Anthropic file storage
    anthropic_file_id = Column(String, nullable=True)  # File ID from Anthropic API

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
        return f"<File(filename='{self.filename}', status='{self.status}')>"
