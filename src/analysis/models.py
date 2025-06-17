"""
Analysis schemas/models.
"""

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field


class AnalysisRequest(BaseModel):
    """Request to create new analysis."""

    file_id: UUID
    agent_type: str = Field(..., description="Type of analysis agent to use")
    parameters: dict[str, Any] | None = Field(default=None, description="Agent-specific parameters")


class AnalysisResponse(BaseModel):
    """Response after creating analysis."""

    id: str
    file_id: UUID
    status: str
    agent_type: str
    message: str


class AnalysisInfo(BaseModel):
    """Detailed analysis information."""

    id: UUID
    file_id: UUID
    agent_type: str
    status: str
    progress: float = Field(ge=0.0, le=1.0)
    progress_message: str | None
    created_at: datetime
    started_at: datetime | None
    completed_at: datetime | None
    error_message: str | None

    class Config:
        from_attributes = True
