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

    company_name: str
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
    data_classification: DataClassification | None
    status: FileStatus
    created_at: datetime
    supabase_path: str
    anthropic_file_id: str | None

    model_config = ConfigDict(from_attributes=True)


class FileListResponse(BaseModel):
    """Response with paginated list of files."""

    files: list[FileResponse] = Field(..., description="List of file objects")
    total: int = Field(..., description="Total count of files (for pagination)")
    page: int = Field(..., description="Current page number")
    page_size: int = Field(..., description="Number of items per page")
    total_pages: int = Field(..., description="Total number of pages")
