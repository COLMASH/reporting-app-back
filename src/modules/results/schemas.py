"""
Pydantic schemas for results module.
"""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


# Response schemas
class ResultResponse(BaseModel):
    """Individual result information."""

    id: UUID = Field(..., description="Unique identifier for the result")
    analysis_id: UUID = Field(..., description="Parent analysis ID")
    result_type: str = Field(..., description="Type: visualization, metrics, summary, data_quality, or recommendations")
    title: str = Field(..., description="Display title")
    description: str | None = Field(None, description="Optional description")

    # Content fields
    insight_text: str | None = Field(None, description="Text content (for summary/recommendations)")
    insight_data: dict | None = Field(None, description="Structured data (for visualizations/metrics)")

    order_index: int = Field(..., description="Display order within analysis")
    created_at: datetime = Field(..., description="Creation timestamp")

    model_config = ConfigDict(from_attributes=True)


class ResultListResponse(BaseModel):
    """Paginated list of results."""

    results: list[ResultResponse] = Field(..., description="List of result objects")
    total: int = Field(..., description="Total count of results (for pagination)")
