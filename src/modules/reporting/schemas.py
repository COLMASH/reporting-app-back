"""
Pydantic schemas for reporting module.
"""

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field

from src.modules.reporting.models import AgentType, AnalysisStatus, FileStatus


# File Upload Schemas
class FileUploadResponse(BaseModel):
    """Response after file upload."""

    id: str = Field(..., description="Unique file identifier")
    filename: str = Field(..., description="Stored filename")
    status: FileStatus = Field(..., description="File processing status")
    message: str = Field(..., description="Upload status message")

    model_config = {
        "json_schema_extra": {
            "example": {
                "id": "550e8400-e29b-41d4-a716-446655440000",
                "filename": "550e8400-e29b-41d4-a716-446655440000.xlsx",
                "status": "uploaded",
                "message": "File uploaded successfully",
            }
        }
    }


class FileInfo(BaseModel):
    """File information."""

    id: UUID
    filename: str
    original_filename: str
    file_size: int | None
    company_name: str
    department: str | None
    data_classification: str | None
    status: FileStatus
    created_at: datetime
    processing_started_at: datetime | None
    processing_completed_at: datetime | None

    model_config = {"from_attributes": True}


# Analysis Schemas
class AnalysisRequest(BaseModel):
    """Request to create new analysis."""

    file_id: UUID
    agent_type: AgentType = Field(..., description="Type of analysis agent to use")
    parameters: dict[str, Any] | None = Field(default=None, description="Agent-specific parameters")

    model_config = {
        "json_schema_extra": {
            "example": {
                "file_id": "550e8400-e29b-41d4-a716-446655440000",
                "agent_type": "excel_analyzer",
                "parameters": {"include_charts": True},
            }
        }
    }


class AnalysisResponse(BaseModel):
    """Response after creating analysis."""

    id: str
    file_id: UUID
    status: AnalysisStatus
    agent_type: AgentType
    message: str


class AnalysisInfo(BaseModel):
    """Detailed analysis information."""

    id: UUID
    file_id: UUID
    agent_type: AgentType
    status: AnalysisStatus
    progress: float = Field(ge=0.0, le=1.0, description="Analysis progress from 0.0 to 1.0")
    progress_message: str | None
    created_at: datetime
    started_at: datetime | None
    completed_at: datetime | None
    error_message: str | None

    model_config = {"from_attributes": True}


# Result Schemas
class ResultInfo(BaseModel):
    """Basic result information."""

    id: UUID
    analysis_id: UUID
    result_type: str
    title: str
    description: str | None
    chart_type: str | None
    order_index: int
    is_primary: bool
    created_at: datetime

    model_config = {"from_attributes": True}


class ResultDetail(BaseModel):
    """Detailed result with data."""

    id: UUID
    analysis_id: UUID
    result_type: str
    title: str
    description: str | None
    chart_type: str | None
    chart_data: dict[str, Any] | None
    chart_config: dict[str, Any] | None
    insight_text: str | None
    confidence_score: float | None = Field(None, ge=0.0, le=1.0)
    order_index: int
    is_primary: bool
    display_size: str
    extra_metadata: dict[str, Any] | None
    created_at: datetime

    model_config = {"from_attributes": True}


# Combined Schemas for Complex Operations
class FileWithAnalyses(BaseModel):
    """File information with associated analyses."""

    file: FileInfo
    analyses: list[AnalysisInfo]


class AnalysisWithResults(BaseModel):
    """Analysis information with all results."""

    analysis: AnalysisInfo
    results: list[ResultDetail]
