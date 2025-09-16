"""
Pydantic schemas for portfolio management system.
Simple schemas for the 3-table database design matching Excel columns.
"""

from datetime import date, datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel


class BaseSchema(BaseModel):
    """Base schema with common configuration."""

    class Config:
        from_attributes = True  # Support SQLAlchemy ORM models
        json_encoders = {
            datetime: lambda v: v.isoformat() if v else None,
            date: lambda v: v.isoformat() if v else None,
            Decimal: lambda v: float(v) if v else None,
        }


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

    # Excel columns specific to real estate
    cost_original_asset: Decimal | None = None
    estimated_capex_budget: Decimal | None = None
    pivert_development_fees: Decimal | None = None
    estimated_total_cost: Decimal | None = None
    capex_invested: Decimal | None = None
    total_investment_to_date: Decimal | None = None
    equity_investment_to_date: Decimal | None = None
    pending_equity_investment: Decimal | None = None
    estimated_capital_gain: Decimal | None = None


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
