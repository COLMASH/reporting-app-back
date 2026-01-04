"""
Pydantic schemas for portfolio reports module.

Request/Response Models:
- ReportCreateRequest: Request to create a new portfolio report
- ReportResponse: Report details with metadata and content
- ReportListResponse: List of reports with pagination info

Validation:
- UUID validation for report_id
- Date validation for report_date
- Proper datetime handling
"""

from datetime import date, datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from src.modules.portfolio_reports.models import ReportScope, ReportStatus

# ============================================================
# REQUEST SCHEMAS
# ============================================================


class ReportCreateRequest(BaseModel):
    """Request to create a new portfolio analysis report."""

    title: str | None = Field(
        default="Portfolio Analysis Report",
        description="Report title",
        max_length=255,
        examples=["Q4 2024 Portfolio Analysis"],
    )
    scope: ReportScope = Field(
        default=ReportScope.SINGLE_DATE,
        description="Report scope - single date or all dates for trend analysis",
    )
    report_date: date | None = Field(
        default=None,
        description="Report date for SINGLE_DATE scope. If None, uses latest available date.",
        examples=["2024-12-31"],
    )

    # Optional filters
    entity_filter: str | None = Field(
        default=None,
        description="Filter by ownership_holding_entity",
        examples=["Family Trust"],
    )
    asset_type_filter: str | None = Field(
        default=None,
        description="Filter by asset_type",
        examples=["Private Equity"],
    )
    holding_company_filter: str | None = Field(
        default=None,
        description="Filter by holding_company",
        examples=["Main Holdings LLC"],
    )

    # Analysis options
    user_prompt: str | None = Field(
        default=None,
        description="Optional instructions or focus areas for the analysis",
        examples=["Focus on private equity performance and real estate exposure. Highlight any concentration risks."],
    )
    research_enabled: bool = Field(
        default=False,
        description="Enable internet research for market data and news about assets",
    )

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "title": "Q4 2024 Portfolio Analysis",
                "scope": "single_date",
                "report_date": "2024-12-31",
                "user_prompt": "Focus on asset allocation changes and performance attribution.",
                "research_enabled": True,
            }
        }
    )


# ============================================================
# RESPONSE SCHEMAS
# ============================================================


class ReportResponse(BaseModel):
    """Response with portfolio report information."""

    id: UUID = Field(
        ...,
        description="Unique identifier for the report",
        examples=["550e8400-e29b-41d4-a716-446655440000"],
    )
    user_id: UUID = Field(
        ...,
        description="UUID of the user who created the report",
        examples=["550e8400-e29b-41d4-a716-446655440001"],
    )
    title: str = Field(
        ...,
        description="Report title",
        examples=["Q4 2024 Portfolio Analysis"],
    )
    scope: ReportScope = Field(
        ...,
        description="Report scope",
        examples=["single_date"],
    )
    report_date: date | None = Field(
        None,
        description="Report date for SINGLE_DATE scope",
        examples=["2024-12-31"],
    )

    # Filters
    entity_filter: str | None = Field(
        None,
        description="Entity filter applied",
    )
    asset_type_filter: str | None = Field(
        None,
        description="Asset type filter applied",
    )
    holding_company_filter: str | None = Field(
        None,
        description="Holding company filter applied",
    )

    # Options
    user_prompt: str | None = Field(
        None,
        description="User-provided instructions for the analysis",
    )
    research_enabled: bool = Field(
        ...,
        description="Whether internet research was enabled",
    )

    # Status
    status: ReportStatus = Field(
        ...,
        description="Current status of the report generation",
        examples=["completed"],
    )
    agent_version: str = Field(
        ...,
        description="Version of the agent used",
        examples=["1.0.0"],
    )
    error_message: str | None = Field(
        None,
        description="Error message if report generation failed",
    )

    # Results
    markdown_content: str | None = Field(
        None,
        description="Generated markdown report content",
    )

    # Metrics
    tokens_used: int | None = Field(
        None,
        description="Total tokens used (input + output)",
        ge=0,
    )
    input_tokens: int | None = Field(
        None,
        description="Input tokens used",
        ge=0,
    )
    output_tokens: int | None = Field(
        None,
        description="Output tokens used",
        ge=0,
    )
    processing_time_seconds: float | None = Field(
        None,
        description="Processing time in seconds",
        ge=0,
    )

    # Timestamps
    created_at: datetime = Field(
        ...,
        description="Timestamp when report was created",
    )
    started_at: datetime | None = Field(
        None,
        description="Timestamp when processing started",
    )
    completed_at: datetime | None = Field(
        None,
        description="Timestamp when processing completed",
    )

    model_config = ConfigDict(
        from_attributes=True,
        json_schema_extra={
            "example": {
                "id": "550e8400-e29b-41d4-a716-446655440000",
                "user_id": "550e8400-e29b-41d4-a716-446655440001",
                "title": "Q4 2024 Portfolio Analysis",
                "scope": "single_date",
                "report_date": "2024-12-31",
                "entity_filter": None,
                "asset_type_filter": None,
                "holding_company_filter": None,
                "user_prompt": "Focus on performance attribution.",
                "research_enabled": True,
                "status": "completed",
                "agent_version": "1.0.0",
                "error_message": None,
                "markdown_content": "# Portfolio Analysis Report\n\n## Executive Summary\n...",
                "tokens_used": 5000,
                "input_tokens": 2000,
                "output_tokens": 3000,
                "processing_time_seconds": 45.5,
                "created_at": "2024-12-31T10:00:00Z",
                "started_at": "2024-12-31T10:00:01Z",
                "completed_at": "2024-12-31T10:00:46Z",
            }
        },
    )


class ReportListResponse(BaseModel):
    """Response with list of portfolio reports."""

    reports: list[ReportResponse] = Field(
        ...,
        description="List of reports",
    )
    total: int = Field(
        ...,
        description="Total number of reports",
        ge=0,
    )

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "reports": [],
                "total": 0,
            }
        }
    )
