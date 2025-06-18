"""
File management schemas/models.
"""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel


class FileUploadResponse(BaseModel):
    """Response after file upload."""

    id: str
    filename: str
    status: str
    message: str


class FileInfo(BaseModel):
    """File information."""

    id: UUID
    filename: str
    original_filename: str
    file_size: int | None
    company_name: str
    department: str | None
    data_classification: str | None
    status: str
    created_at: datetime
    processing_started_at: datetime | None
    processing_completed_at: datetime | None

    model_config = {"from_attributes": True}
