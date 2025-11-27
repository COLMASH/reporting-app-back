"""
Portfolio service module with functional programming approach.
All functions are pure - no classes per CLAUDE.md requirements.
"""

from datetime import date
from decimal import Decimal
from typing import cast
from uuid import UUID

from sqlalchemy import desc, distinct, func
from sqlalchemy.orm import Session, joinedload

from src.core.exceptions import NotFoundError, ValidationError
from src.modules.portfolio.models import Asset

# Constants
DEFAULT_PAGE_SIZE = 20
MAX_PAGE_SIZE = 100

# Allowed columns for sorting (security whitelist)
ALLOWED_SORT_COLUMNS = {
    "asset_name",
    "ownership_holding_entity",
    "asset_type",
    "asset_group",
    "denomination_currency",
    "report_date",
    "initial_investment_date",
    "estimated_asset_value_usd",
    "estimated_asset_value_eur",
    "paid_in_capital_usd",
    "unfunded_commitment_usd",
    "total_asset_return_usd",
    "created_at",
    "display_id",
}


# ============================================================
# HELPER FUNCTIONS
# ============================================================


def get_latest_report_date(db: Session) -> date | None:
    """Get the most recent report_date in the database."""
    result = db.query(func.max(Asset.report_date)).scalar()
    return cast(date | None, result)


# ============================================================
# FILTER OPTIONS
# ============================================================


def get_filter_options(db: Session) -> dict:
    """
    Get distinct values for all filter dimensions.
    Used to populate sidebar, navbar, and date picker dropdowns.
    """
    entities = db.query(distinct(Asset.ownership_holding_entity)).all()
    asset_types = db.query(distinct(Asset.asset_type)).all()
    report_dates = (
        db.query(distinct(Asset.report_date))
        .order_by(desc(Asset.report_date))
        .all()
    )

    return {
        "entities": sorted([e[0] for e in entities if e[0]]),
        "asset_types": sorted([t[0] for t in asset_types if t[0]]),
        "report_dates": [d[0] for d in report_dates if d[0]],
    }


# ============================================================
# ASSET LIST & DETAIL
# ============================================================


def get_assets(
    db: Session,
    entity: str | None = None,
    asset_type: str | None = None,
    report_date: date | None = None,
    search: str | None = None,
    page: int = 1,
    page_size: int = DEFAULT_PAGE_SIZE,
    sort_by: str = "asset_name",
    sort_order: str = "asc",
    include_extension: bool = False,
) -> tuple[list[Asset], int]:
    """
    Get filtered, paginated assets.

    Args:
        db: Database session
        entity: Filter by ownership_holding_entity (None = all)
        asset_type: Filter by asset_type (None = all)
        report_date: Filter by report_date (None = latest)
        search: Search in asset_name (case-insensitive)
        page: Page number (1-based)
        page_size: Results per page (max 100)
        sort_by: Column name to sort by
        sort_order: "asc" or "desc"
        include_extension: Include structured_note/real_estate data

    Returns:
        Tuple of (list of assets, total count)
    """
    page_size = min(page_size, MAX_PAGE_SIZE)
    page = max(1, page)

    query = db.query(Asset)

    # Eager load extensions if requested
    if include_extension:
        query = query.options(
            joinedload(Asset.structured_note),
            joinedload(Asset.real_estate),
        )

    # Default to latest report_date if not specified
    if report_date is None:
        report_date = get_latest_report_date(db)
    if report_date:
        query = query.filter(Asset.report_date == report_date)

    # Apply filters
    if entity:
        query = query.filter(Asset.ownership_holding_entity == entity)
    if asset_type:
        query = query.filter(Asset.asset_type == asset_type)
    if search:
        query = query.filter(Asset.asset_name.ilike(f"%{search}%"))

    # Get total count before pagination
    total = query.count()

    # Apply sorting (with whitelist validation)
    if sort_by not in ALLOWED_SORT_COLUMNS:
        sort_by = "asset_name"  # Default to safe column
    sort_column = getattr(Asset, sort_by)
    if sort_order == "desc":
        sort_column = desc(sort_column)
    query = query.order_by(sort_column)

    # Apply pagination
    offset = (page - 1) * page_size
    assets = query.offset(offset).limit(page_size).all()

    return assets, total


def get_asset_by_id(
    db: Session,
    asset_id: UUID,
    include_extension: bool = True,
) -> Asset:
    """
    Get a single asset by ID with optional extension data.

    Args:
        db: Database session
        asset_id: UUID of the asset
        include_extension: Include structured_note/real_estate data

    Returns:
        Asset object

    Raises:
        NotFoundError: If asset not found
    """
    query = db.query(Asset)

    if include_extension:
        query = query.options(
            joinedload(Asset.structured_note),
            joinedload(Asset.real_estate),
        )

    asset = query.filter(Asset.id == asset_id).first()

    if not asset:
        raise NotFoundError(f"Asset {asset_id} not found")

    return asset


# ============================================================
# AGGREGATIONS
# ============================================================


def get_portfolio_summary(
    db: Session,
    entity: str | None = None,
    asset_type: str | None = None,
    report_date: date | None = None,
) -> dict:
    """
    Calculate portfolio summary KPIs.

    Returns:
        Dict with total_assets, total_estimated_value_usd, etc.
    """
    if report_date is None:
        report_date = get_latest_report_date(db)

    query = db.query(
        func.count(Asset.id).label("total_assets"),
        func.sum(Asset.estimated_asset_value_usd).label("total_value_usd"),
        func.sum(Asset.paid_in_capital_usd).label("total_paid_in_usd"),
        func.sum(Asset.unfunded_commitment_usd).label("total_unfunded_usd"),
        func.sum(Asset.estimated_asset_value_eur).label("total_value_eur"),
        func.sum(Asset.paid_in_capital_eur).label("total_paid_in_eur"),
        func.sum(Asset.unfunded_commitment_eur).label("total_unfunded_eur"),
        func.avg(Asset.total_asset_return_usd).label("avg_return"),
    )

    if report_date:
        query = query.filter(Asset.report_date == report_date)
    if entity:
        query = query.filter(Asset.ownership_holding_entity == entity)
    if asset_type:
        query = query.filter(Asset.asset_type == asset_type)

    result = query.first()

    return {
        "report_date": report_date,
        "total_assets": result.total_assets or 0,
        "total_estimated_value_usd": result.total_value_usd or Decimal(0),
        "total_paid_in_capital_usd": result.total_paid_in_usd or Decimal(0),
        "total_unfunded_commitment_usd": result.total_unfunded_usd or Decimal(0),
        "total_estimated_value_eur": result.total_value_eur or Decimal(0),
        "total_paid_in_capital_eur": result.total_paid_in_eur or Decimal(0),
        "total_unfunded_commitment_eur": result.total_unfunded_eur or Decimal(0),
        "weighted_avg_return": result.avg_return,
    }


def get_aggregation_by_entity(
    db: Session,
    asset_type: str | None = None,
    report_date: date | None = None,
) -> dict:
    """
    Aggregate portfolio data by ownership_holding_entity.
    Used for entity donut chart.

    Returns:
        Dict with report_date, total_value_usd, and groups list
    """
    if report_date is None:
        report_date = get_latest_report_date(db)

    query = db.query(
        Asset.ownership_holding_entity.label("name"),
        func.sum(Asset.estimated_asset_value_usd).label("value_usd"),
        func.sum(Asset.estimated_asset_value_eur).label("value_eur"),
        func.count(Asset.id).label("count"),
    )

    if report_date:
        query = query.filter(Asset.report_date == report_date)
    if asset_type:
        query = query.filter(Asset.asset_type == asset_type)

    results = query.group_by(Asset.ownership_holding_entity).all()

    # Calculate totals and percentages
    total_usd = sum(r.value_usd or Decimal(0) for r in results)
    total_eur = sum(r.value_eur or Decimal(0) for r in results)
    groups = []

    for r in results:
        value_usd = r.value_usd or Decimal(0)
        value_eur = r.value_eur or Decimal(0)
        pct = float(value_usd / total_usd * 100) if total_usd > 0 else 0.0
        groups.append({
            "name": r.name,
            "value_usd": value_usd,
            "value_eur": value_eur,
            "percentage": round(pct, 2),
            "count": r.count,
        })

    # Sort by value descending
    groups.sort(key=lambda x: x["value_usd"], reverse=True)

    return {
        "report_date": report_date,
        "total_value_usd": total_usd,
        "total_value_eur": total_eur,
        "groups": groups,
    }


def get_aggregation_by_asset_type(
    db: Session,
    entity: str | None = None,
    report_date: date | None = None,
) -> dict:
    """
    Aggregate portfolio data by asset_type.
    Used for asset type donut chart and summary table.

    Returns:
        Dict with report_date, total_value_usd, and groups list
    """
    if report_date is None:
        report_date = get_latest_report_date(db)

    query = db.query(
        Asset.asset_type,
        func.sum(Asset.estimated_asset_value_usd).label("value_usd"),
        func.sum(Asset.estimated_asset_value_eur).label("value_eur"),
        func.count(Asset.id).label("count"),
        func.sum(Asset.paid_in_capital_usd).label("paid_in_usd"),
        func.sum(Asset.paid_in_capital_eur).label("paid_in_eur"),
        func.sum(Asset.unfunded_commitment_usd).label("unfunded_usd"),
        func.sum(Asset.unfunded_commitment_eur).label("unfunded_eur"),
    )

    if report_date:
        query = query.filter(Asset.report_date == report_date)
    if entity:
        query = query.filter(Asset.ownership_holding_entity == entity)

    results = query.group_by(Asset.asset_type).all()

    # Calculate totals and percentages
    total_usd = sum(r.value_usd or Decimal(0) for r in results)
    total_eur = sum(r.value_eur or Decimal(0) for r in results)
    groups = []

    for r in results:
        value_usd = r.value_usd or Decimal(0)
        value_eur = r.value_eur or Decimal(0)
        pct = float(value_usd / total_usd * 100) if total_usd > 0 else 0.0
        groups.append({
            "asset_type": r.asset_type,
            "value_usd": value_usd,
            "value_eur": value_eur,
            "percentage": round(pct, 2),
            "count": r.count,
            "paid_in_capital_usd": r.paid_in_usd or Decimal(0),
            "paid_in_capital_eur": r.paid_in_eur or Decimal(0),
            "unfunded_commitment_usd": r.unfunded_usd or Decimal(0),
            "unfunded_commitment_eur": r.unfunded_eur or Decimal(0),
        })

    # Sort by value descending
    groups.sort(key=lambda x: x["value_usd"], reverse=True)

    return {
        "report_date": report_date,
        "total_value_usd": total_usd,
        "total_value_eur": total_eur,
        "groups": groups,
    }


def get_historical_nav(
    db: Session,
    entity: str | None = None,
    asset_type: str | None = None,
    start_date: date | None = None,
    end_date: date | None = None,
    group_by_entity: bool = True,
) -> dict:
    """
    Get historical NAV time series data.
    Used for historical NAV chart (stacked bars by entity).

    Args:
        db: Database session
        entity: Filter by entity (ignored if group_by_entity=true)
        asset_type: Filter by asset_type
        start_date: Start of date range
        end_date: End of date range
        group_by_entity: Return separate series per entity (default: true)

    Returns:
        Dict with series list containing name and data points
    """
    if group_by_entity:
        # Group by date and entity
        query = db.query(
            Asset.report_date,
            Asset.ownership_holding_entity,
            func.sum(Asset.estimated_asset_value_usd).label("value_usd"),
            func.sum(Asset.estimated_asset_value_eur).label("value_eur"),
        )
    else:
        # Group by date only (single series)
        query = db.query(
            Asset.report_date,
            func.sum(Asset.estimated_asset_value_usd).label("value_usd"),
            func.sum(Asset.estimated_asset_value_eur).label("value_eur"),
        )
        if entity:
            query = query.filter(Asset.ownership_holding_entity == entity)

    # Apply filters
    if asset_type:
        query = query.filter(Asset.asset_type == asset_type)
    if start_date:
        query = query.filter(Asset.report_date >= start_date)
    if end_date:
        query = query.filter(Asset.report_date <= end_date)

    if group_by_entity:
        results = (
            query.group_by(Asset.report_date, Asset.ownership_holding_entity)
            .order_by(Asset.report_date)
            .all()
        )

        # Organize by entity
        series_by_entity: dict[str, list[dict]] = {}
        for r in results:
            entity_name = r.ownership_holding_entity
            if entity_name not in series_by_entity:
                series_by_entity[entity_name] = []
            series_by_entity[entity_name].append({
                "date": r.report_date,
                "value_usd": r.value_usd or Decimal(0),
                "value_eur": r.value_eur or Decimal(0),
            })

        # Convert to list format
        series = [
            {"name": name, "data": data}
            for name, data in sorted(series_by_entity.items())
        ]
    else:
        results = (
            query.group_by(Asset.report_date)
            .order_by(Asset.report_date)
            .all()
        )

        series = [
            {
                "name": entity or "Total",
                "data": [
                    {
                        "date": r.report_date,
                        "value_usd": r.value_usd or Decimal(0),
                        "value_eur": r.value_eur or Decimal(0),
                    }
                    for r in results
                ],
            }
        ]

    return {"series": series}


def get_flexible_aggregation(
    db: Session,
    group_by: str,
    entity: str | None = None,
    asset_type: str | None = None,
    report_date: date | None = None,
) -> dict:
    """
    Flexible aggregation by any valid column.
    Returns data suitable for any chart type (donut, bar, treemap, radar, bubble).

    Args:
        db: Database session
        group_by: Column name to group by (e.g., 'geographic_focus', 'denomination_currency')
        entity: Pre-filter by entity
        asset_type: Pre-filter by asset_type
        report_date: Filter by report_date (default: latest)

    Returns:
        Dict with report_date, group_by field name, totals, and groups list
    """
    if report_date is None:
        report_date = get_latest_report_date(db)

    # Get the column to group by dynamically (validated by enum in controller)
    group_column = getattr(Asset, group_by, None)
    if group_column is None:
        raise ValidationError(f"Invalid group_by field: {group_by}")

    query = db.query(
        group_column.label("label"),
        func.sum(Asset.estimated_asset_value_usd).label("value_usd"),
        func.sum(Asset.estimated_asset_value_eur).label("value_eur"),
        func.count(Asset.id).label("count"),
        func.sum(Asset.paid_in_capital_usd).label("paid_in"),
        func.sum(Asset.unfunded_commitment_usd).label("unfunded"),
        func.avg(Asset.total_asset_return_usd).label("avg_return"),
    )

    if report_date:
        query = query.filter(Asset.report_date == report_date)
    if entity:
        query = query.filter(Asset.ownership_holding_entity == entity)
    if asset_type:
        query = query.filter(Asset.asset_type == asset_type)

    results = query.group_by(group_column).all()

    # Calculate totals
    total_usd = sum(r.value_usd or Decimal(0) for r in results)
    total_eur = sum(r.value_eur or Decimal(0) for r in results)
    total_count = sum(r.count or 0 for r in results)

    # Build groups with percentages
    groups = []
    for r in results:
        value_usd = r.value_usd or Decimal(0)
        pct = float(value_usd / total_usd * 100) if total_usd > 0 else 0.0
        groups.append({
            "label": r.label or "Unknown",
            "value_usd": value_usd,
            "value_eur": r.value_eur or Decimal(0),
            "percentage": round(pct, 2),
            "count": r.count or 0,
            "paid_in_capital_usd": r.paid_in or Decimal(0),
            "unfunded_commitment_usd": r.unfunded or Decimal(0),
            "avg_return": r.avg_return,
        })

    # Sort by value descending
    groups.sort(key=lambda x: x["value_usd"], reverse=True)

    return {
        "report_date": report_date,
        "group_by": group_by,
        "total_value_usd": total_usd,
        "total_value_eur": total_eur,
        "total_count": total_count,
        "groups": groups,
    }
