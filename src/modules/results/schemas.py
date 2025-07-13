"""
Pydantic schemas for results module.
"""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from src.modules.results.models import ChartType


# Request schemas
class ResultCreateRequest(BaseModel):
    """Request to create a new result."""

    analysis_id: UUID
    result_type: str = Field(..., description="Type: chart, insight, summary, metric")
    title: str
    description: str | None = None
    chart_type: ChartType | None = None
    chart_data: dict | None = None
    chart_config: dict | None = None
    insight_text: str | None = None
    confidence_score: float | None = Field(None, ge=0.0, le=1.0)
    order_index: int = 0
    is_primary: bool = False
    display_size: str = "medium"
    extra_metadata: dict | None = None


# Response schemas
class ResultResponse(BaseModel):
    """Response with result information."""

    id: UUID
    analysis_id: UUID
    result_type: str
    title: str
    description: str | None
    chart_type: ChartType | None
    chart_data: dict | None
    chart_config: dict | None
    insight_text: str | None
    confidence_score: float | None
    order_index: int
    is_primary: bool
    display_size: str
    extra_metadata: dict | None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ResultListResponse(BaseModel):
    """Response with list of results."""

    results: list[ResultResponse]
    total: int
