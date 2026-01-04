"""
Business logic for portfolio reports module - functional approach.

Main Functions:
- create_report_record: Create report record in PENDING status
- get_portfolio_data_for_report: Query portfolio data from database
- process_report_background: Background task for report generation
- get_report_by_id: Retrieve report by ID
- get_user_reports: Get all reports for a user
- delete_report: Delete report

Error Handling:
- Uses custom exceptions from core.exceptions
- Handles AI service errors gracefully
"""

from datetime import UTC, date, datetime
from decimal import Decimal
from typing import Any
from uuid import UUID

from sqlalchemy.orm import Session

from src.core.logging import get_logger
from src.modules.portfolio.models import Asset
from src.modules.portfolio.service import (
    get_aggregation_by_asset_type,
    get_aggregation_by_entity,
    get_assets,
    get_filter_options,
    get_flexible_aggregation,
    get_historical_nav,
    get_latest_report_date,
    get_portfolio_summary,
)
from src.modules.portfolio_reports.models import (
    PortfolioReport,
    ReportScope,
    ReportStatus,
)

logger = get_logger(__name__)


def create_report_record(
    db: Session,
    user_id: UUID,
    title: str,
    scope: ReportScope,
    report_date: date | None = None,
    entity_filter: str | None = None,
    asset_type_filter: str | None = None,
    holding_company_filter: str | None = None,
    user_prompt: str | None = None,
    research_enabled: bool = False,
) -> PortfolioReport:
    """
    Create a new portfolio report record in PENDING status.

    Args:
        db: Database session
        user_id: UUID of the user creating the report
        title: Report title
        scope: SINGLE_DATE or ALL_DATES
        report_date: Date for SINGLE_DATE scope (None = latest)
        entity_filter: Optional filter by ownership_holding_entity
        asset_type_filter: Optional filter by asset_type
        holding_company_filter: Optional filter by holding_company
        user_prompt: Optional user instructions for focus
        research_enabled: Enable internet research

    Returns:
        PortfolioReport: The created report record
    """
    # Default to latest report_date if not specified and scope is SINGLE_DATE
    if scope == ReportScope.SINGLE_DATE and report_date is None:
        report_date = get_latest_report_date(db)

    report = PortfolioReport(
        user_id=user_id,
        title=title,
        scope=scope,
        report_date=report_date,
        entity_filter=entity_filter,
        asset_type_filter=asset_type_filter,
        holding_company_filter=holding_company_filter,
        user_prompt=user_prompt,
        research_enabled=research_enabled,
        status=ReportStatus.PENDING,
    )
    db.add(report)
    db.commit()
    db.refresh(report)

    logger.info(
        "Portfolio report record created",
        report_id=str(report.id),
        scope=scope.value,
        research_enabled=research_enabled,
    )

    return report


def get_portfolio_data_for_report(
    db: Session,
    scope: ReportScope,
    report_date: date | None = None,
    entity_filter: str | None = None,
    asset_type_filter: str | None = None,
    holding_company_filter: str | None = None,
) -> dict[str, Any]:
    """
    Query portfolio data from database for report generation.

    Returns structured data suitable for the AI agent.
    """
    # Get summary KPIs
    summary = get_portfolio_summary(
        db=db,
        entity=entity_filter,
        asset_type=asset_type_filter,
        holding_company=holding_company_filter,
        report_date=report_date if scope == ReportScope.SINGLE_DATE else None,
    )

    # Get aggregation by entity
    by_entity = get_aggregation_by_entity(
        db=db,
        entity=entity_filter,
        asset_type=asset_type_filter,
        holding_company=holding_company_filter,
        report_date=report_date if scope == ReportScope.SINGLE_DATE else None,
    )

    # Get aggregation by asset type
    by_asset_type = get_aggregation_by_asset_type(
        db=db,
        entity=entity_filter,
        asset_type=asset_type_filter,
        holding_company=holding_company_filter,
        report_date=report_date if scope == ReportScope.SINGLE_DATE else None,
    )

    # Get aggregation by geography
    by_geography = get_flexible_aggregation(
        db=db,
        group_by="geographic_focus",
        entity=entity_filter,
        asset_type=asset_type_filter,
        holding_company=holding_company_filter,
        report_date=report_date if scope == ReportScope.SINGLE_DATE else None,
    )

    # Get aggregation by currency
    by_currency = get_flexible_aggregation(
        db=db,
        group_by="denomination_currency",
        entity=entity_filter,
        asset_type=asset_type_filter,
        holding_company=holding_company_filter,
        report_date=report_date if scope == ReportScope.SINGLE_DATE else None,
    )

    # Get historical NAV if ALL_DATES scope
    historical_data = None
    if scope == ReportScope.ALL_DATES:
        historical_data = get_historical_nav(
            db=db,
            entity=entity_filter,
            asset_type=asset_type_filter,
            holding_company=holding_company_filter,
            group_by="holding_company",
        )

    # Get individual assets (limited for context)
    assets, total_assets = get_assets(
        db=db,
        entity=entity_filter,
        asset_type=asset_type_filter,
        holding_company=holding_company_filter,
        report_date=report_date if scope == ReportScope.SINGLE_DATE else None,
        page=1,
        page_size=100,
        sort_by="estimated_asset_value_usd",
        sort_order="desc",
    )

    # Serialize assets
    assets_list = _serialize_assets(assets)

    # Get filter options for context
    filter_options = get_filter_options(db)

    # Convert Decimal to float for JSON serialization
    return {
        "scope": scope.value,
        "report_date": str(report_date) if report_date else None,
        "filters_applied": {
            "entity": entity_filter,
            "asset_type": asset_type_filter,
            "holding_company": holding_company_filter,
        },
        "summary": _convert_decimals(summary),
        "by_entity": _convert_decimals(by_entity),
        "by_asset_type": _convert_decimals(by_asset_type),
        "by_geography": _convert_decimals(by_geography),
        "by_currency": _convert_decimals(by_currency),
        "historical_nav": _convert_decimals(historical_data) if historical_data else None,
        "top_assets": assets_list,
        "total_assets_count": total_assets,
        "available_filters": filter_options,
    }


def _serialize_assets(assets: list[Asset]) -> list[dict[str, Any]]:
    """Serialize asset list for JSON."""
    result = []
    for asset in assets:
        result.append(
            {
                "id": str(asset.id),
                "display_id": asset.display_id,
                "holding_company": asset.holding_company,
                "ownership_entity": asset.ownership_holding_entity,
                "managing_entity": asset.managing_entity,
                "asset_group": asset.asset_group,
                "asset_type": asset.asset_type,
                "asset_subtype": asset.asset_subtype,
                "asset_name": asset.asset_name,
                "asset_identifier": asset.asset_identifier,
                "geographic_focus": asset.geographic_focus,
                "asset_status": asset.asset_status,
                "currency": asset.denomination_currency,
                "initial_investment_date": str(asset.initial_investment_date) if asset.initial_investment_date else None,
                "shares": float(asset.number_of_shares or 0),
                "share_price": float(asset.current_share_price or 0),
                "estimated_value_usd": float(asset.estimated_asset_value_usd or 0),
                "estimated_value_eur": float(asset.estimated_asset_value_eur or 0),
                "paid_in_capital_usd": float(asset.paid_in_capital_usd or 0),
                "unfunded_commitment_usd": float(asset.unfunded_commitment_usd or 0),
                "unrealized_gain_usd": float(asset.unrealized_gain_usd or 0),
                "total_return_usd": float(asset.total_asset_return_usd or 0) if asset.total_asset_return_usd else None,
            }
        )
    return result


def _convert_decimals(data: Any) -> Any:
    """Recursively convert Decimal values to float for JSON serialization."""
    if isinstance(data, Decimal):
        return float(data)
    elif isinstance(data, dict):
        return {k: _convert_decimals(v) for k, v in data.items()}
    elif isinstance(data, list):
        return [_convert_decimals(item) for item in data]
    elif isinstance(data, date):
        return str(data)
    else:
        return data


async def process_report_background(report_id: UUID) -> None:
    """
    Process report generation in the background.

    Args:
        report_id: UUID of the report to process

    Note:
        This function manages its own database session and commits.
        All exceptions are caught and logged to ensure the report
        status is always updated.
    """
    from src.core.database.core import SessionLocal
    from src.modules.portfolio_reports.agent import generate_portfolio_report

    # Create a new database session for the background task
    db = SessionLocal()

    try:
        # Get the report record
        report = db.query(PortfolioReport).filter(PortfolioReport.id == report_id).first()
        if not report:
            logger.error("Report not found in background task", report_id=str(report_id))
            return

        # Update status to IN_PROGRESS
        report.status = ReportStatus.IN_PROGRESS
        report.started_at = datetime.now(UTC)
        db.commit()

        logger.info(
            "Starting report generation",
            report_id=str(report_id),
            scope=report.scope.value,
            research_enabled=report.research_enabled,
        )

        # Get portfolio data from database
        # Cast SQLAlchemy columns to proper Python types for mypy
        report_scope: ReportScope = report.scope  # type: ignore[assignment]
        portfolio_data = get_portfolio_data_for_report(
            db=db,
            scope=report_scope,
            report_date=report.report_date,  # type: ignore[arg-type]
            entity_filter=report.entity_filter,  # type: ignore[arg-type]
            asset_type_filter=report.asset_type_filter,  # type: ignore[arg-type]
            holding_company_filter=report.holding_company_filter,  # type: ignore[arg-type]
        )

        # Run the agent
        result = await generate_portfolio_report(
            portfolio_data=portfolio_data,
            user_prompt=str(report.user_prompt) if report.user_prompt else None,
            research_enabled=bool(report.research_enabled),
        )

        if result.get("success"):
            # Update report as completed
            report.status = ReportStatus.COMPLETED
            report.completed_at = datetime.now(UTC)
            report.markdown_content = result.get("markdown_report", "")

            # Calculate processing time
            if report.started_at and report.completed_at:
                started = report.started_at.replace(tzinfo=UTC) if report.started_at.tzinfo is None else report.started_at
                completed = report.completed_at
                time_diff = completed - started
                report.processing_time_seconds = time_diff.total_seconds()

            # Update token usage
            input_tokens = result.get("input_tokens", 0)
            output_tokens = result.get("output_tokens", 0)
            report.input_tokens = input_tokens
            report.output_tokens = output_tokens
            report.tokens_used = input_tokens + output_tokens

            logger.info(
                "Report generation completed",
                report_id=str(report_id),
                content_length=len(report.markdown_content or ""),
                tokens_used=report.tokens_used,
            )
        else:
            # Update report as failed
            report.status = ReportStatus.FAILED
            error_msg = result.get("error", "Unknown error")
            report.error_message = error_msg
            report.completed_at = datetime.now(UTC)

            if report.started_at and report.completed_at:
                started = report.started_at.replace(tzinfo=UTC) if report.started_at.tzinfo is None else report.started_at
                completed = report.completed_at
                time_diff = completed - started
                report.processing_time_seconds = time_diff.total_seconds()

            logger.error(
                "Report generation failed - agent returned error",
                report_id=str(report_id),
                error=error_msg,
            )

    except Exception as e:
        # Update report as failed
        try:
            report = db.query(PortfolioReport).filter(PortfolioReport.id == report_id).first()
            if report:
                report.status = ReportStatus.FAILED
                report.error_message = str(e)
                report.completed_at = datetime.now(UTC)

                if report.started_at and report.completed_at:
                    started = report.started_at.replace(tzinfo=UTC) if report.started_at.tzinfo is None else report.started_at
                    completed = report.completed_at
                    time_diff = completed - started
                    report.processing_time_seconds = time_diff.total_seconds()

                db.commit()
        except Exception as db_error:
            logger.error(
                "Failed to update report status after error",
                report_id=str(report_id),
                original_error=str(e),
                db_error=str(db_error),
            )

        logger.error(
            "Report generation failed - exception occurred",
            report_id=str(report_id),
            error=str(e),
            exc_info=True,
        )

    finally:
        # Always close the database session
        db.commit()
        db.close()


def get_report_by_id(db: Session, report_id: UUID) -> PortfolioReport | None:
    """
    Get report by ID.

    Args:
        db: Database session
        report_id: UUID of the report to retrieve

    Returns:
        PortfolioReport | None: The report if found, None otherwise
    """
    return db.query(PortfolioReport).filter(PortfolioReport.id == report_id).first()


def get_user_reports(
    db: Session,
    user_id: UUID,
    limit: int = 20,
    offset: int = 0,
) -> tuple[list[PortfolioReport], int]:
    """
    Get all reports for a user with pagination.

    Args:
        db: Database session
        user_id: UUID of the user
        limit: Maximum number of reports to return
        offset: Number of reports to skip

    Returns:
        Tuple of (list of reports, total count)
    """
    query = db.query(PortfolioReport).filter(PortfolioReport.user_id == user_id)
    total = query.count()
    reports = query.order_by(PortfolioReport.created_at.desc()).offset(offset).limit(limit).all()
    return reports, total


def delete_report(db: Session, report_id: UUID) -> None:
    """
    Delete a portfolio report.

    Args:
        db: Database session
        report_id: UUID of the report to delete
    """
    report = db.query(PortfolioReport).filter(PortfolioReport.id == report_id).first()
    if report:
        db.delete(report)
        db.commit()
        logger.info(
            "Report deleted",
            report_id=str(report_id),
        )
