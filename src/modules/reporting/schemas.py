"""
Pydantic schemas for reporting analysis module.
"""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict

from src.modules.reporting.models import AgentType, AnalysisStatus


# Request schemas
class AnalysisCreateRequest(BaseModel):
    """Request to create a new analysis."""

    file_id: UUID
    agent_type: AgentType
    parameters: dict | None = None


# Response schemas
class AnalysisResponse(BaseModel):
    """Response with analysis information."""

    id: UUID
    file_id: UUID
    agent_type: AgentType
    agent_version: str
    parameters: dict | None
    status: AnalysisStatus
    progress: float
    progress_message: str | None
    error_message: str | None
    error_details: dict | None
    tokens_used: int | None
    processing_time_seconds: float | None
    created_at: datetime
    started_at: datetime | None
    completed_at: datetime | None

    model_config = ConfigDict(from_attributes=True)


class AnalysisListResponse(BaseModel):
    """Response with list of analyses."""

    analyses: list[AnalysisResponse]
    total: int
