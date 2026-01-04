"""
REST API endpoints for portfolio reports.

Main Functions:
- create_report: Create new portfolio analysis report
- get_report: Get specific report details
- list_reports: Get all reports for current user
- delete_report: Delete report

Dependencies:
- CurrentUser: Authenticated user from JWT token
- DbSession: Database session for queries
"""

from uuid import UUID

from fastapi import APIRouter, BackgroundTasks, Request

from src.core.decorators import log_endpoint
from src.core.exceptions import NotFoundError, ValidationError
from src.core.logging import get_logger
from src.modules.auth.dependencies import CurrentUser, DbSession
from src.modules.portfolio_reports import schemas
from src.modules.portfolio_reports import service as report_service

logger = get_logger(__name__)

# Create router with detailed metadata
router = APIRouter(
    prefix="/portfolio_reports",
    tags=["portfolio_reports"],
    responses={
        404: {"description": "Report not found"},
        403: {"description": "Access forbidden"},
        500: {"description": "Internal server error"},
    },
)


@router.post("/", response_model=schemas.ReportResponse)
@log_endpoint
async def create_report(
    request: schemas.ReportCreateRequest,
    background_tasks: BackgroundTasks,
    req: Request,
    current_user: CurrentUser,
    db: DbSession,
) -> schemas.ReportResponse:
    """
    Create a new portfolio analysis report.

    The report is generated asynchronously in the background.
    Returns immediately with PENDING status.
    Poll GET /portfolio_reports/{id} for status updates.
    """
    try:
        # Create report record (in PENDING status)
        report = report_service.create_report_record(
            db=db,
            user_id=current_user.id,
            title=request.title or "Portfolio Analysis Report",
            scope=request.scope,
            report_date=request.report_date,
            entity_filter=request.entity_filter,
            asset_type_filter=request.asset_type_filter,
            holding_company_filter=request.holding_company_filter,
            user_prompt=request.user_prompt,
            research_enabled=request.research_enabled,
        )

        # Queue the background task for processing
        background_tasks.add_task(
            report_service.process_report_background,
            report.id,
        )

        logger.info(
            "Portfolio report queued",
            report_id=str(report.id),
            user_id=str(current_user.id),
            scope=request.scope.value,
            research_enabled=request.research_enabled,
        )

        return report
    except ValueError as e:
        raise ValidationError(str(e)) from e
    except Exception as e:
        logger.error(
            "Failed to create report",
            error=str(e),
            user_id=str(current_user.id),
        )
        raise


@router.get("/{report_id}", response_model=schemas.ReportResponse)
@log_endpoint
async def get_report(
    report_id: str,
    req: Request,
    current_user: CurrentUser,
    db: DbSession,
) -> schemas.ReportResponse:
    """
    Get report details by ID.

    The user must own the report.
    Includes markdown_content when status is COMPLETED.
    """
    try:
        report_uuid = UUID(report_id)
    except ValueError:
        raise ValidationError("Invalid report ID format") from None

    report = report_service.get_report_by_id(db, report_uuid)
    if not report:
        raise NotFoundError(f"Report {report_id} not found")

    # Verify ownership
    if report.user_id != current_user.id:
        raise NotFoundError(f"Report {report_id} not found")

    return report


@router.get("/", response_model=schemas.ReportListResponse)
@log_endpoint
async def list_reports(
    req: Request,
    current_user: CurrentUser,
    db: DbSession,
    limit: int = 20,
    offset: int = 0,
) -> schemas.ReportListResponse:
    """
    Get all portfolio reports for the current user.

    Returns reports ordered by creation date (newest first).
    Supports pagination with limit and offset.
    """
    reports, total = report_service.get_user_reports(
        db=db,
        user_id=current_user.id,
        limit=limit,
        offset=offset,
    )

    logger.info(
        "Retrieved user reports",
        user_id=str(current_user.id),
        count=len(reports),
        total=total,
    )

    return schemas.ReportListResponse(
        reports=reports,
        total=total,
    )


@router.delete("/{report_id}", status_code=204)
@log_endpoint
async def delete_report(
    report_id: str,
    req: Request,
    current_user: CurrentUser,
    db: DbSession,
) -> None:
    """
    Delete a portfolio report.

    The user must own the report.
    This permanently removes the report.
    """
    try:
        report_uuid = UUID(report_id)
    except ValueError:
        raise ValidationError("Invalid report ID format") from None

    # Get the report
    report = report_service.get_report_by_id(db, report_uuid)
    if not report:
        raise NotFoundError(f"Report {report_id} not found")

    # Verify ownership
    if report.user_id != current_user.id:
        raise NotFoundError(f"Report {report_id} not found")

    # Delete the report
    report_service.delete_report(db, report_uuid)

    logger.info(
        "Report deleted",
        report_id=report_id,
        user_id=str(current_user.id),
    )
