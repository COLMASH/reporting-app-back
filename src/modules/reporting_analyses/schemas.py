"""
Pydantic schemas for reporting analysis module.

Request/Response Models:
- AnalysisCreateRequest: Request to create a new analysis
- AnalysisResponse: Analysis details with metadata
- AnalysisListResponse: List of analyses with pagination info

Validation:
- UUID validation for file_id
- Optional parameters validation
- Proper datetime handling
"""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from src.modules.reporting_analyses.models import AnalysisStatus


# Request schemas
class AnalysisCreateRequest(BaseModel):
    """Request to create a new analysis."""

    file_id: UUID = Field(
        ...,
        description="UUID of the file to analyze",
        examples=["550e8400-e29b-41d4-a716-446655440000"],
    )
    parameters: dict | None = Field(
        None,
        description="Optional parameters for the analysis agent. Use 'focus' to provide custom instructions.",
        examples=[
            {
                "focus": (
                    "Please analyze the financial data and focus on revenue trends, "
                    "profit margins, and year-over-year growth. Also identify any "
                    "seasonal patterns in the sales data."
                )
            }
        ],
    )

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "file_id": "550e8400-e29b-41d4-a716-446655440000",
                "parameters": {
                    "focus": (
                        "Please analyze the financial data and focus on revenue trends, "
                        "profit margins, and year-over-year growth. Also identify any "
                        "seasonal patterns in the sales data."
                    )
                },
            }
        }
    )


# Response schemas
class AnalysisResponse(BaseModel):
    """Response with analysis information."""

    id: UUID = Field(
        ...,
        description="Unique identifier for the analysis",
        examples=["550e8400-e29b-41d4-a716-446655440000"],
    )
    file_id: UUID = Field(
        ...,
        description="UUID of the analyzed file",
        examples=["550e8400-e29b-41d4-a716-446655440000"],
    )
    agent_version: str = Field(
        ...,
        description="Version of the analysis agent used",
        examples=["1.0.0"],
    )
    parameters: dict | None = Field(
        None,
        description="Parameters used for the analysis",
        examples=[
            {
                "focus": (
                    "Please analyze the financial data and focus on revenue trends, "
                    "profit margins, and year-over-year growth. Also identify any "
                    "seasonal patterns in the sales data."
                )
            }
        ],
    )
    status: AnalysisStatus = Field(
        ...,
        description="Current status of the analysis",
        examples=["completed"],
    )
    error_message: str | None = Field(
        None,
        description="Error message if analysis failed",
        examples=["Analysis execution failed: timeout"],
    )
    tokens_used: int | None = Field(
        None,
        description="Number of AI tokens consumed",
        examples=[1234],
        ge=0,
    )
    processing_time_seconds: float | None = Field(
        None,
        description="Time taken to process the analysis",
        examples=[12.5],
        ge=0,
    )
    created_at: datetime = Field(
        ...,
        description="Timestamp when analysis was created",
        examples=["2025-07-17T10:30:00Z"],
    )
    started_at: datetime | None = Field(
        None,
        description="Timestamp when analysis execution started",
        examples=["2025-07-17T10:30:01Z"],
    )
    completed_at: datetime | None = Field(
        None,
        description="Timestamp when analysis was completed",
        examples=["2025-07-17T10:30:15Z"],
    )

    model_config = ConfigDict(
        from_attributes=True,
        json_schema_extra={
            "example": {
                "id": "550e8400-e29b-41d4-a716-446655440000",
                "file_id": "550e8400-e29b-41d4-a716-446655440001",
                "agent_version": "1.0.0",
                "parameters": {"focus": "financial_data"},
                "status": "completed",
                "error_message": None,
                "tokens_used": 1234,
                "processing_time_seconds": 12.5,
                "created_at": "2025-07-17T10:30:00Z",
                "started_at": "2025-07-17T10:30:01Z",
                "completed_at": "2025-07-17T10:30:15Z",
            }
        },
    )


class AnalysisListResponse(BaseModel):
    """Response with list of analyses."""

    analyses: list[AnalysisResponse] = Field(
        ...,
        description="List of analyses",
    )
    total: int = Field(
        ...,
        description="Total number of analyses",
        examples=[10],
        ge=0,
    )

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "analyses": [
                    {
                        "id": "550e8400-e29b-41d4-a716-446655440000",
                        "file_id": "550e8400-e29b-41d4-a716-446655440001",
                        "agent_version": "1.0.0",
                        "parameters": {"focus": "financial_data"},
                        "status": "completed",
                        "error_message": None,
                        "tokens_used": 1234,
                        "processing_time_seconds": 12.5,
                        "created_at": "2025-07-17T10:30:00Z",
                        "started_at": "2025-07-17T10:30:01Z",
                        "completed_at": "2025-07-17T10:30:15Z",
                    }
                ],
                "total": 1,
            }
        }
    )
