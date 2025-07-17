"""
Pydantic schemas for results module.
"""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


# Request schemas
class ResultCreateRequest(BaseModel):
    """Request to create a new result."""

    analysis_id: UUID
    result_type: str = Field(
        ...,
        description="Type: visualization, metrics, summary, data_quality, recommendations",
    )
    title: str
    description: str | None = None

    # Content fields
    insight_text: str | None = Field(None, description="Text content for summary/recommendations")
    insight_data: dict | None = Field(
        None,
        description="Structured data for metrics/visualizations/data_quality",
    )

    order_index: int = 0


# Response schemas
class ResultResponse(BaseModel):
    """Response with result information."""

    id: UUID
    analysis_id: UUID
    result_type: str
    title: str
    description: str | None

    # Content fields
    insight_text: str | None
    insight_data: dict | None

    order_index: int
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ResultListResponse(BaseModel):
    """Response with list of results."""

    results: list[ResultResponse]
    total: int
