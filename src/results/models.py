"""
Results schemas/models.
"""

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field


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

    class Config:
        from_attributes = True


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

    class Config:
        from_attributes = True
