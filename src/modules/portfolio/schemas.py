"""
Pydantic schemas for portfolio management system.
Simple schemas for the 3-table database design matching Excel columns.
"""

from datetime import date, datetime
from decimal import Decimal
from enum import Enum
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, field_serializer

# ============================================================
# ENUMS
# ============================================================


class GroupByField(str, Enum):
    """Valid fields for flexible aggregation grouping."""

    OWNERSHIP_HOLDING_ENTITY = "ownership_holding_entity"
    HOLDING_COMPANY = "holding_company"  # NEW
    MANAGING_ENTITY = "managing_entity"  # Renamed from ASSET_GROUP
    ASSET_TYPE = "asset_type"
    ASSET_SUBTYPE = "asset_subtype"  # For subtype summary table
    ASSET_GROUP = "asset_group"  # Renamed from ASSET_GROUP_STRATEGY
    GEOGRAPHIC_FOCUS = "geographic_focus"
    DENOMINATION_CURRENCY = "denomination_currency"
    ASSET_STATUS = "asset_status"
    BROKER_ASSET_MANAGER = "broker_asset_manager"


class BaseSchema(BaseModel):
    """Base schema with common configuration."""

    model_config = ConfigDict(from_attributes=True)

    @field_serializer("*", mode="wrap")
    @classmethod
    def serialize_special_types(cls, value: Any, handler: Any) -> Any:
        """Serialize datetime, date, and Decimal types."""
        if isinstance(value, datetime):
            return value.isoformat() if value else None
        if isinstance(value, date):
            return value.isoformat() if value else None
        if isinstance(value, Decimal):
            return float(value) if value else None
        return handler(value)


# ============================================================
# ASSET SCHEMAS (Main table matching Excel columns A-U)
# ============================================================


class AssetBase(BaseSchema):
    """Base asset fields matching Excel columns exactly."""

    # Excel columns A-U
    report_date: date | None = None
    ownership_holding_entity: str
    asset_group: str
    asset_sub_group: str | None = None
    asset_type: str
    asset_name: str
    location: str | None = None
    asset_identifier: str | None = None
    asset_status: str | None = "Active in portfolio"
    broker_asset_manager: str | None = None
    denomination_currency: str = "USD"
    initial_investment_date: date | None = None
    number_of_shares: Decimal | None = None
    avg_purchase_price: Decimal | None = None
    total_investment_commitment: Decimal | None = None
    paid_in_capital: Decimal | None = None
    asset_level_financing: Decimal | None = None
    pending_investment: Decimal | None = None
    current_share_price: Decimal | None = None
    estimated_asset_value: Decimal | None = None
    total_asset_return: Decimal | None = None


class AssetCreate(AssetBase):
    """Schema for creating new assets."""

    pass


class AssetUpdate(BaseSchema):
    """Schema for updating assets. All fields optional."""

    # All fields optional for partial updates
    report_date: date | None = None
    ownership_holding_entity: str | None = None
    asset_group: str | None = None
    asset_sub_group: str | None = None
    asset_type: str | None = None
    asset_name: str | None = None
    location: str | None = None
    asset_identifier: str | None = None
    asset_status: str | None = None
    broker_asset_manager: str | None = None
    denomination_currency: str | None = None
    initial_investment_date: date | None = None
    number_of_shares: Decimal | None = None
    avg_purchase_price: Decimal | None = None
    total_investment_commitment: Decimal | None = None
    paid_in_capital: Decimal | None = None
    asset_level_financing: Decimal | None = None
    pending_investment: Decimal | None = None
    current_share_price: Decimal | None = None
    estimated_asset_value: Decimal | None = None
    total_asset_return: Decimal | None = None


class Asset(AssetBase):
    """Schema for reading assets from database."""

    id: UUID
    created_at: datetime
    updated_at: datetime | None = None

    # Optional relationships
    structured_note: "StructuredNote | None" = None
    real_estate: "RealEstateAsset | None" = None


# ============================================================
# STRUCTURED NOTE SCHEMAS (Extension table for Excel columns V-AL)
# ============================================================


class StructuredNoteBase(BaseSchema):
    """Structured note fields matching Excel columns V-AL."""

    # Excel columns V-AL
    annual_coupon: Decimal | None = None
    coupon_payment_frequency: str | None = None
    next_coupon_review_date: str | None = None  # String as in Excel
    next_principal_review_date: date | None = None
    final_due_date: date | None = None
    redemption_type: str | None = None
    underlying_index_name: str | None = None
    underlying_index_code: str | None = None
    strike_level: Decimal | None = None
    underlying_index_level: Decimal | None = None
    performance_vs_strike: Decimal | None = None
    effective_strike_percentage: Decimal | None = None
    note_leverage: str | None = None  # String as in Excel
    capital_protection: Decimal | None = None
    capital_protection_barrier: Decimal | None = None
    coupon_protection_barrier_pct: Decimal | None = None
    coupon_protection_barrier_value: Decimal | None = None


class StructuredNoteCreate(StructuredNoteBase):
    """Schema for creating structured notes."""

    asset_id: UUID


class StructuredNoteUpdate(StructuredNoteBase):
    """Schema for updating structured notes. All fields optional."""

    pass


class StructuredNote(StructuredNoteBase):
    """Schema for reading structured notes from database."""

    id: UUID
    asset_id: UUID

    # Relationship back to asset
    asset: "Asset | None" = None


# ============================================================
# REAL ESTATE ASSET SCHEMAS (Extension table for Excel real estate columns)
# ============================================================


class RealEstateAssetBase(BaseSchema):
    """Real estate fields matching Excel columns."""

    # NEW column
    real_estate_status: str | None = None

    # EUR columns (renamed with _eur suffix)
    cost_original_asset_eur: Decimal | None = None
    estimated_capex_budget_eur: Decimal | None = None
    pivert_development_fees_eur: Decimal | None = None
    estimated_total_cost_eur: Decimal | None = None
    capex_invested_eur: Decimal | None = None
    total_investment_to_date_eur: Decimal | None = None
    equity_investment_to_date_eur: Decimal | None = None
    pending_equity_investment_eur: Decimal | None = None
    estimated_capital_gain_eur: Decimal | None = None

    # NEW USD columns
    estimated_total_cost_usd: Decimal | None = None
    total_investment_to_date_usd: Decimal | None = None
    equity_investment_to_date_usd: Decimal | None = None
    pending_equity_investment_usd: Decimal | None = None
    estimated_capital_gain_usd: Decimal | None = None


class RealEstateAssetCreate(RealEstateAssetBase):
    """Schema for creating real estate assets."""

    asset_id: UUID


class RealEstateAssetUpdate(RealEstateAssetBase):
    """Schema for updating real estate assets. All fields optional."""

    pass


class RealEstateAsset(RealEstateAssetBase):
    """Schema for reading real estate assets from database."""

    id: UUID
    asset_id: UUID

    # Relationship back to asset
    asset: "Asset | None" = None


# Update forward references for relationships
Asset.model_rebuild()
StructuredNote.model_rebuild()
RealEstateAsset.model_rebuild()


# ============================================================
# API RESPONSE SCHEMAS (For Dashboard Endpoints)
# ============================================================


class FilterOptionsResponse(BaseSchema):
    """Response for GET /portfolio/filters endpoint."""

    entities: list[str]
    holding_companies: list[str]  # NEW - for sidebar navigation
    asset_types: list[str]
    report_dates: list[date]


class StructuredNoteResponse(BaseSchema):
    """Structured note extension data for API responses."""

    annual_coupon: Decimal | None = None
    coupon_payment_frequency: str | None = None
    next_coupon_review_date: str | None = None
    next_principal_review_date: date | None = None
    final_due_date: date | None = None
    redemption_type: str | None = None
    underlying_index_name: str | None = None
    underlying_index_code: str | None = None
    strike_level: Decimal | None = None
    underlying_index_level: Decimal | None = None
    performance_vs_strike: Decimal | None = None
    effective_strike_percentage: Decimal | None = None
    note_leverage: str | None = None
    capital_protection: Decimal | None = None
    capital_protection_barrier: Decimal | None = None
    coupon_protection_barrier_pct: Decimal | None = None
    coupon_protection_barrier_value: Decimal | None = None


class RealEstateResponse(BaseSchema):
    """Real estate extension data for API responses."""

    # NEW column
    real_estate_status: str | None = None

    # EUR columns (renamed with _eur suffix)
    cost_original_asset_eur: Decimal | None = None
    estimated_capex_budget_eur: Decimal | None = None
    pivert_development_fees_eur: Decimal | None = None
    estimated_total_cost_eur: Decimal | None = None
    capex_invested_eur: Decimal | None = None
    total_investment_to_date_eur: Decimal | None = None
    equity_investment_to_date_eur: Decimal | None = None
    pending_equity_investment_eur: Decimal | None = None
    estimated_capital_gain_eur: Decimal | None = None

    # NEW USD columns
    estimated_total_cost_usd: Decimal | None = None
    total_investment_to_date_usd: Decimal | None = None
    equity_investment_to_date_usd: Decimal | None = None
    pending_equity_investment_usd: Decimal | None = None
    estimated_capital_gain_usd: Decimal | None = None


class AssetResponse(BaseSchema):
    """Full asset response with ALL columns for dashboard tables."""

    # Identifiers
    id: UUID
    display_id: int | None = None

    # Classification
    holding_company: str | None = None  # NEW
    ownership_holding_entity: str
    managing_entity: str  # Renamed from asset_group
    asset_group: str | None = None  # Renamed from asset_group_strategy
    asset_type: str
    asset_subtype: str | None = None
    asset_subtype_2: str | None = None
    asset_name: str
    asset_identifier: str | None = None
    asset_status: str | None = None

    # Location & Manager
    geographic_focus: str | None = None
    broker_asset_manager: str | None = None
    denomination_currency: str

    # Dates
    report_date: date | None = None
    initial_investment_date: date | None = None

    # Share data
    number_of_shares: Decimal | None = None
    avg_purchase_price_base_currency: Decimal | None = None
    current_share_price: Decimal | None = None

    # FX Rates
    usd_eur_inception: Decimal | None = None
    usd_eur_current: Decimal | None = None
    usd_cad_current: Decimal | None = None
    usd_chf_current: Decimal | None = None
    usd_hkd_current: Decimal | None = None

    # Financial - Base Currency
    total_investment_commitment_base_currency: Decimal | None = None
    paid_in_capital_base_currency: Decimal | None = None
    asset_level_financing_base_currency: Decimal | None = None
    unfunded_commitment_base_currency: Decimal | None = None
    estimated_asset_value_base_currency: Decimal | None = None
    total_asset_return_base_currency: Decimal | None = None

    # Financial - USD
    total_investment_commitment_usd: Decimal | None = None
    paid_in_capital_usd: Decimal | None = None
    unfunded_commitment_usd: Decimal | None = None
    estimated_asset_value_usd: Decimal | None = None
    total_asset_return_usd: Decimal | None = None
    unrealized_gain_usd: Decimal | None = None  # NEW

    # Financial - EUR
    total_investment_commitment_eur: Decimal | None = None
    paid_in_capital_eur: Decimal | None = None
    unfunded_commitment_eur: Decimal | None = None
    estimated_asset_value_eur: Decimal | None = None
    total_asset_return_eur: Decimal | None = None
    unrealized_gain_eur: Decimal | None = None  # NEW

    # Timestamps
    created_at: datetime
    updated_at: datetime | None = None

    # Extension data (only populated when include_extension=true)
    structured_note: StructuredNoteResponse | None = None
    real_estate: RealEstateResponse | None = None


class AssetListResponse(BaseSchema):
    """Paginated asset list response."""

    assets: list[AssetResponse]
    total: int
    page: int
    page_size: int
    total_pages: int


class PortfolioSummaryResponse(BaseSchema):
    """Portfolio summary KPIs response."""

    report_date: date | None = None
    total_assets: int
    total_estimated_value_usd: Decimal
    total_paid_in_capital_usd: Decimal
    total_unfunded_commitment_usd: Decimal
    total_unrealized_gain_usd: Decimal
    total_estimated_value_eur: Decimal
    total_paid_in_capital_eur: Decimal
    total_unfunded_commitment_eur: Decimal
    total_unrealized_gain_eur: Decimal
    weighted_avg_return: Decimal | None = None


class AggregationGroup(BaseSchema):
    """Single group in aggregation response (for donut charts)."""

    name: str
    value_usd: Decimal
    value_eur: Decimal
    percentage: Decimal
    count: int


class EntityAggregationResponse(BaseSchema):
    """Aggregation by ownership entity response."""

    report_date: date | None = None
    total_value_usd: Decimal
    total_value_eur: Decimal
    groups: list[AggregationGroup]


class AssetTypeGroup(BaseSchema):
    """Asset type group with additional financial metrics."""

    asset_type: str
    value_usd: Decimal
    value_eur: Decimal
    percentage: Decimal
    count: int
    paid_in_capital_usd: Decimal
    paid_in_capital_eur: Decimal
    unrealized_gain_usd: Decimal
    unrealized_gain_eur: Decimal
    unfunded_commitment_usd: Decimal
    unfunded_commitment_eur: Decimal


class AssetTypeAggregationResponse(BaseSchema):
    """Aggregation by asset type response."""

    report_date: date | None = None
    total_value_usd: Decimal
    total_value_eur: Decimal
    groups: list[AssetTypeGroup]


class NavDataPoint(BaseSchema):
    """Single NAV data point for time series."""

    date: date
    value_usd: Decimal
    value_eur: Decimal


class NavSeries(BaseSchema):
    """NAV series for one entity."""

    name: str
    data: list[NavDataPoint]


class HistoricalNavResponse(BaseSchema):
    """Historical NAV time series response."""

    series: list[NavSeries]


# ============================================================
# FLEXIBLE AGGREGATION SCHEMAS
# ============================================================


class FlexibleAggregationGroup(BaseSchema):
    """Single group in flexible aggregation response."""

    label: str  # The grouped value (e.g., "USA", "EUR", "Active")
    value_usd: Decimal
    value_eur: Decimal
    percentage: Decimal
    count: int
    paid_in_capital_usd: Decimal
    unfunded_commitment_usd: Decimal
    avg_return: Decimal | None = None


class FlexibleAggregationResponse(BaseSchema):
    """
    Flexible aggregation response - supports any chart type.

    Use cases:
    - Donut/Pie: label + percentage or value_usd
    - Bar chart: label + value_usd
    - Treemap: label + value_usd
    - Radar: label + percentage
    - Bubble: label + value_usd + count
    """

    report_date: date | None = None
    group_by: str  # The field used for grouping
    total_value_usd: Decimal
    total_value_eur: Decimal
    total_count: int
    groups: list[FlexibleAggregationGroup]
