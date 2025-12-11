"""
Portfolio REST API endpoints for dashboard frontend.

Endpoints:
- GET /portfolio/filters: Filter dropdown options
- GET /portfolio/assets: Paginated asset list
- GET /portfolio/assets/{id}: Single asset detail
- GET /portfolio/aggregations/summary: Portfolio KPIs
- GET /portfolio/aggregations/by-entity: Entity distribution
- GET /portfolio/aggregations/by-asset-type: Asset type distribution
- GET /portfolio/aggregations/historical: Historical NAV time series
"""

from datetime import date
from uuid import UUID

from fastapi import APIRouter, Query, Request

from src.core.decorators import log_endpoint
from src.modules.auth.dependencies import CurrentUser, DbSession
from src.modules.portfolio import schemas, service
from src.modules.portfolio.models import Asset

router = APIRouter(prefix="/portfolio", tags=["portfolio"])


# ============================================================
# HELPER FUNCTIONS
# ============================================================


def _build_asset_response(
    asset: Asset,
    include_extension: bool = False,
) -> schemas.AssetResponse:
    """Convert Asset ORM model to AssetResponse schema."""
    asset_dict: dict = {
        "id": asset.id,
        "display_id": asset.display_id,
        "ownership_holding_entity": asset.ownership_holding_entity,
        "asset_group": asset.asset_group,
        "asset_group_strategy": asset.asset_group_strategy,
        "asset_type": asset.asset_type,
        "asset_subtype": asset.asset_subtype,
        "asset_subtype_2": asset.asset_subtype_2,
        "asset_name": asset.asset_name,
        "asset_identifier": asset.asset_identifier,
        "asset_status": asset.asset_status,
        "geographic_focus": asset.geographic_focus,
        "broker_asset_manager": asset.broker_asset_manager,
        "denomination_currency": asset.denomination_currency,
        "report_date": asset.report_date,
        "initial_investment_date": asset.initial_investment_date,
        "number_of_shares": asset.number_of_shares,
        "avg_purchase_price_base_currency": asset.avg_purchase_price_base_currency,
        "current_share_price": asset.current_share_price,
        "usd_eur_inception": asset.usd_eur_inception,
        "usd_eur_current": asset.usd_eur_current,
        "usd_cad_current": asset.usd_cad_current,
        "usd_chf_current": asset.usd_chf_current,
        "usd_hkd_current": asset.usd_hkd_current,
        "total_investment_commitment_base_currency": asset.total_investment_commitment_base_currency,
        "paid_in_capital_base_currency": asset.paid_in_capital_base_currency,
        "asset_level_financing_base_currency": asset.asset_level_financing_base_currency,
        "unfunded_commitment_base_currency": asset.unfunded_commitment_base_currency,
        "estimated_asset_value_base_currency": asset.estimated_asset_value_base_currency,
        "total_asset_return_base_currency": asset.total_asset_return_base_currency,
        "total_investment_commitment_usd": asset.total_investment_commitment_usd,
        "paid_in_capital_usd": asset.paid_in_capital_usd,
        "unfunded_commitment_usd": asset.unfunded_commitment_usd,
        "estimated_asset_value_usd": asset.estimated_asset_value_usd,
        "total_asset_return_usd": asset.total_asset_return_usd,
        "total_investment_commitment_eur": asset.total_investment_commitment_eur,
        "paid_in_capital_eur": asset.paid_in_capital_eur,
        "unfunded_commitment_eur": asset.unfunded_commitment_eur,
        "estimated_asset_value_eur": asset.estimated_asset_value_eur,
        "total_asset_return_eur": asset.total_asset_return_eur,
        "created_at": asset.created_at,
        "updated_at": asset.updated_at,
    }

    # Add extension data if requested and present
    if include_extension:
        if asset.structured_note:
            asset_dict["structured_note"] = schemas.StructuredNoteResponse(
                annual_coupon=asset.structured_note.annual_coupon,
                coupon_payment_frequency=asset.structured_note.coupon_payment_frequency,
                next_coupon_review_date=asset.structured_note.next_coupon_review_date,
                next_principal_review_date=asset.structured_note.next_principal_review_date,
                final_due_date=asset.structured_note.final_due_date,
                redemption_type=asset.structured_note.redemption_type,
                underlying_index_name=asset.structured_note.underlying_index_name,
                underlying_index_code=asset.structured_note.underlying_index_code,
                strike_level=asset.structured_note.strike_level,
                underlying_index_level=asset.structured_note.underlying_index_level,
                performance_vs_strike=asset.structured_note.performance_vs_strike,
                effective_strike_percentage=asset.structured_note.effective_strike_percentage,
                note_leverage=asset.structured_note.note_leverage,
                capital_protection=asset.structured_note.capital_protection,
                capital_protection_barrier=asset.structured_note.capital_protection_barrier,
                coupon_protection_barrier_pct=asset.structured_note.coupon_protection_barrier_pct,
                coupon_protection_barrier_value=asset.structured_note.coupon_protection_barrier_value,
            )
        if asset.real_estate:
            asset_dict["real_estate"] = schemas.RealEstateResponse(
                cost_original_asset=asset.real_estate.cost_original_asset,
                estimated_capex_budget=asset.real_estate.estimated_capex_budget,
                pivert_development_fees=asset.real_estate.pivert_development_fees,
                estimated_total_cost=asset.real_estate.estimated_total_cost,
                capex_invested=asset.real_estate.capex_invested,
                total_investment_to_date=asset.real_estate.total_investment_to_date,
                equity_investment_to_date=asset.real_estate.equity_investment_to_date,
                pending_equity_investment=asset.real_estate.pending_equity_investment,
                estimated_capital_gain=asset.real_estate.estimated_capital_gain,
            )

    return schemas.AssetResponse(**asset_dict)


# ============================================================
# FILTER OPTIONS
# ============================================================


@router.get("/filters", response_model=schemas.FilterOptionsResponse)
@log_endpoint
async def get_filters(
    request: Request,
    current_user: CurrentUser,
    db: DbSession,
) -> schemas.FilterOptionsResponse:
    """
    Get available filter options for dropdowns.

    Returns distinct values for:
    - entities: Ownership holding entities (for sidebar)
    - asset_types: Asset types (for navbar tabs)
    - report_dates: Available report dates (for date picker)
    """
    options = service.get_filter_options(db)
    return schemas.FilterOptionsResponse(**options)


# ============================================================
# ASSET LIST & DETAIL
# ============================================================


@router.get("/assets", response_model=schemas.AssetListResponse)
@log_endpoint
async def list_assets(
    request: Request,
    current_user: CurrentUser,
    db: DbSession,
    entity: str | None = Query(
        None,
        description="Filter by ownership_holding_entity (None = all)",
    ),
    asset_type: str | None = Query(
        None,
        description="Filter by asset_type (None = all)",
    ),
    asset_group: str | None = Query(
        None,
        description="Filter by asset_group (e.g., 'Liquid Assets')",
    ),
    asset_group_strategy: str | None = Query(
        None,
        description="Filter by asset_group_strategy (e.g., 'Direct investment')",
    ),
    report_date: date | None = Query(
        None,
        description="Filter by report_date (default: latest)",
    ),
    search: str | None = Query(
        None,
        description="Search in asset_name (case-insensitive)",
    ),
    page: int = Query(1, ge=1, description="Page number (1-based)"),
    page_size: int = Query(20, ge=1, le=100, description="Results per page"),
    sort_by: str = Query("asset_name", description="Column to sort by"),
    sort_order: str = Query(
        "asc",
        pattern="^(asc|desc)$",
        description="Sort direction: asc or desc",
    ),
    include_extension: bool = Query(
        False,
        description="Include structured_note/real_estate extension data",
    ),
) -> schemas.AssetListResponse:
    """
    Get filtered, paginated asset list with ALL columns.

    Supports filtering by entity, asset_type, report_date, and text search.
    Returns all 42+ asset columns plus optional extension data.
    """
    assets, total = service.get_assets(
        db=db,
        entity=entity,
        asset_type=asset_type,
        asset_group=asset_group,
        asset_group_strategy=asset_group_strategy,
        report_date=report_date,
        search=search,
        page=page,
        page_size=page_size,
        sort_by=sort_by,
        sort_order=sort_order,
        include_extension=include_extension,
    )

    total_pages = (total + page_size - 1) // page_size if total > 0 else 0

    # Convert assets to response schema using helper function
    asset_responses = [_build_asset_response(asset, include_extension) for asset in assets]

    return schemas.AssetListResponse(
        assets=asset_responses,
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages,
    )


@router.get("/assets/{asset_id}", response_model=schemas.AssetResponse)
@log_endpoint
async def get_asset(
    request: Request,
    asset_id: UUID,
    current_user: CurrentUser,
    db: DbSession,
) -> schemas.AssetResponse:
    """
    Get a single asset by ID with all columns and extension data.
    """
    asset = service.get_asset_by_id(db, asset_id, include_extension=True)
    return _build_asset_response(asset, include_extension=True)


# ============================================================
# AGGREGATIONS
# ============================================================


@router.get("/aggregations/summary", response_model=schemas.PortfolioSummaryResponse)
@log_endpoint
async def get_portfolio_summary(
    request: Request,
    current_user: CurrentUser,
    db: DbSession,
    entity: str | None = Query(
        None,
        description="Filter by entity (None = consolidated)",
    ),
    asset_type: str | None = Query(
        None,
        description="Filter by asset_type",
    ),
    asset_group: str | None = Query(
        None,
        description="Filter by asset_group (e.g., 'Liquid Assets')",
    ),
    asset_group_strategy: str | None = Query(
        None,
        description="Filter by asset_group_strategy (e.g., 'Direct investment')",
    ),
    report_date: date | None = Query(
        None,
        description="Report date (default: latest)",
    ),
) -> schemas.PortfolioSummaryResponse:
    """
    Get portfolio summary KPIs.

    Returns total assets, total value, paid-in capital,
    unfunded commitment, and weighted average return.
    """
    result = service.get_portfolio_summary(
        db=db,
        entity=entity,
        asset_type=asset_type,
        asset_group=asset_group,
        asset_group_strategy=asset_group_strategy,
        report_date=report_date,
    )
    return schemas.PortfolioSummaryResponse(**result)


@router.get(
    "/aggregations/by-entity",
    response_model=schemas.EntityAggregationResponse,
)
@log_endpoint
async def get_aggregation_by_entity(
    request: Request,
    current_user: CurrentUser,
    db: DbSession,
    entity: str | None = Query(
        None,
        description="Filter by entity (returns only this entity at 100%)",
    ),
    asset_type: str | None = Query(
        None,
        description="Pre-filter by asset_type",
    ),
    asset_group: str | None = Query(
        None,
        description="Filter by asset_group (e.g., 'Liquid Assets')",
    ),
    asset_group_strategy: str | None = Query(
        None,
        description="Filter by asset_group_strategy (e.g., 'Direct investment')",
    ),
    report_date: date | None = Query(
        None,
        description="Report date (default: latest)",
    ),
) -> schemas.EntityAggregationResponse:
    """
    Get portfolio distribution by ownership entity.

    Used for entity donut chart. Returns groups with:
    - name: Entity name
    - value_usd: Sum of estimated_asset_value_usd
    - percentage: Pre-calculated percentage
    - count: Number of assets
    """
    result = service.get_aggregation_by_entity(
        db=db,
        entity=entity,
        asset_type=asset_type,
        asset_group=asset_group,
        asset_group_strategy=asset_group_strategy,
        report_date=report_date,
    )
    return schemas.EntityAggregationResponse(**result)


@router.get(
    "/aggregations/by-asset-type",
    response_model=schemas.AssetTypeAggregationResponse,
)
@log_endpoint
async def get_aggregation_by_asset_type(
    request: Request,
    current_user: CurrentUser,
    db: DbSession,
    entity: str | None = Query(
        None,
        description="Pre-filter by entity",
    ),
    asset_type: str | None = Query(
        None,
        description="Filter by asset_type (returns only this type at 100%)",
    ),
    asset_group: str | None = Query(
        None,
        description="Filter by asset_group (e.g., 'Liquid Assets')",
    ),
    asset_group_strategy: str | None = Query(
        None,
        description="Filter by asset_group_strategy (e.g., 'Direct investment')",
    ),
    report_date: date | None = Query(
        None,
        description="Report date (default: latest)",
    ),
) -> schemas.AssetTypeAggregationResponse:
    """
    Get portfolio distribution by asset type.

    Used for asset type donut chart and summary table. Returns groups with:
    - asset_type: Asset type name
    - value_usd: Sum of estimated_asset_value_usd
    - percentage: Pre-calculated percentage
    - count: Number of assets
    - paid_in_capital_usd: Sum of paid_in_capital
    - unfunded_commitment_usd: Sum of unfunded_commitment
    """
    result = service.get_aggregation_by_asset_type(
        db=db,
        entity=entity,
        asset_type=asset_type,
        asset_group=asset_group,
        asset_group_strategy=asset_group_strategy,
        report_date=report_date,
    )
    return schemas.AssetTypeAggregationResponse(**result)


@router.get(
    "/aggregations/historical",
    response_model=schemas.HistoricalNavResponse,
)
@log_endpoint
async def get_historical_nav(
    request: Request,
    current_user: CurrentUser,
    db: DbSession,
    entity: str | None = Query(
        None,
        description="Filter by entity (ignored if group_by_entity=true)",
    ),
    asset_type: str | None = Query(
        None,
        description="Filter by asset_type",
    ),
    asset_group: str | None = Query(
        None,
        description="Filter by asset_group (e.g., 'Liquid Assets')",
    ),
    asset_group_strategy: str | None = Query(
        None,
        description="Filter by asset_group_strategy (e.g., 'Direct investment')",
    ),
    start_date: date | None = Query(
        None,
        description="Start of date range",
    ),
    end_date: date | None = Query(
        None,
        description="End of date range",
    ),
    group_by_entity: bool = Query(
        True,
        description="Return separate series per entity",
    ),
) -> schemas.HistoricalNavResponse:
    """
    Get historical NAV time series data.

    Used for historical NAV chart (stacked bars by entity).
    Returns series with name and data points (date, value).
    """
    result = service.get_historical_nav(
        db=db,
        entity=entity,
        asset_type=asset_type,
        asset_group=asset_group,
        asset_group_strategy=asset_group_strategy,
        start_date=start_date,
        end_date=end_date,
        group_by_entity=group_by_entity,
    )
    return schemas.HistoricalNavResponse(**result)


# ============================================================
# FLEXIBLE AGGREGATION
# ============================================================


@router.get(
    "/aggregations/flexible",
    response_model=schemas.FlexibleAggregationResponse,
    summary="Flexible aggregation by any dimension",
    description="""
    Aggregate portfolio data by any valid dimension.

    **Valid group_by values:**
    - `ownership_holding_entity` - By owner (ILV, Isis Invest, etc.)
    - `asset_type` - By type (Equities, Bonds, etc.)
    - `asset_group` - By group (Various, StructuredNotes, etc.)
    - `asset_group_strategy` - By strategy
    - `geographic_focus` - By geography (USA, Europe, etc.)
    - `denomination_currency` - By currency (USD, EUR, etc.)
    - `asset_status` - By status (Active, Sold, etc.)
    - `broker_asset_manager` - By manager (Goldman, UBS, etc.)

    **Supported chart types:**
    - Donut/Pie: use `label` + `percentage` or `value_usd`
    - Bar chart: use `label` + `value_usd`
    - Treemap: use `label` + `value_usd`
    - Radar: use `label` + `percentage`
    - Bubble: use `label` + `value_usd` + `count`
    """,
)
@log_endpoint
async def get_flexible_aggregation(
    request: Request,
    current_user: CurrentUser,
    db: DbSession,
    group_by: schemas.GroupByField = Query(
        ...,
        description="Field to group by",
    ),
    entity: str | None = Query(
        None,
        description="Pre-filter by entity",
    ),
    asset_type: str | None = Query(
        None,
        description="Pre-filter by asset_type",
    ),
    asset_group: str | None = Query(
        None,
        description="Filter by asset_group (e.g., 'Liquid Assets')",
    ),
    asset_group_strategy: str | None = Query(
        None,
        description="Filter by asset_group_strategy (e.g., 'Direct investment')",
    ),
    report_date: date | None = Query(
        None,
        description="Report date (default: latest)",
    ),
) -> schemas.FlexibleAggregationResponse:
    """
    Get flexible aggregation by any valid dimension.

    Supports all chart types: donut, pie, bar, treemap, radar, bubble.
    Returns multiple metrics per group for maximum visualization flexibility.
    """
    result = service.get_flexible_aggregation(
        db=db,
        group_by=group_by.value,
        entity=entity,
        asset_type=asset_type,
        asset_group=asset_group,
        asset_group_strategy=asset_group_strategy,
        report_date=report_date,
    )
    return schemas.FlexibleAggregationResponse(**result)
