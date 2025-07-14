"""
Pydantic schemas for files module.
"""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from src.modules.files.models import DataClassification, FileStatus


# Request schemas
class FileUploadRequest(BaseModel):
    """Request for file upload metadata."""

    company_name: str = Field(..., min_length=1, max_length=255)
    department: str | None = Field(None, max_length=100)
    data_classification: DataClassification | None = None


# Response schemas
class FileResponse(BaseModel):
    """Response with file information."""

    id: UUID
    filename: str
    original_filename: str
    file_size: int | None
    mime_type: str | None
    file_extension: str
    company_name: str
    department: str | None
    data_classification: DataClassification | None
    status: FileStatus
    created_at: datetime
    supabase_path: str
    anthropic_file_id: str | None

    model_config = ConfigDict(from_attributes=True)


class FileListResponse(BaseModel):
    """Response with list of files."""

    files: list[FileResponse]
    total: int
