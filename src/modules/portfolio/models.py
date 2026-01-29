"""
Portfolio Management System Models - Final Simplified Version

Only 3 essential tables matching Excel structure:
1. assets - Main table with all common fields
2. structured_notes - Extension for structured products
3. real_estate_assets - Extension for real estate
"""

import uuid
from datetime import datetime
from decimal import Decimal
from typing import Any

from sqlalchemy import Column, Date, DateTime, ForeignKey, Index, Integer, Numeric, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.ext.hybrid import hybrid_property
from sqlalchemy.orm import relationship

from src.core.database.core import Base


# Main Assets Table (Common fields from Excel)
class Asset(Base):
    """
    Base table for all assets. Column names match Excel exactly.
    Contains all common fields from Various, StructuredNotes, and RealEstate sheets.
    """

    __tablename__ = "assets"

    # Essential DB fields
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    display_id = Column(Integer)  # User-friendly sequential ID for display/reference

    # Excel columns - kept exact names
    report_date = Column(Date)
    holding_company = Column(String(100))  # NEW - parent holding company
    ownership_holding_entity = Column(String(100), nullable=False)
    managing_entity = Column(String(100), nullable=False)  # Renamed from asset_group
    asset_group = Column(String(100))  # Renamed from asset_group_strategy
    asset_type = Column(String(100), nullable=False)
    asset_subtype = Column(String(100))  # NEW - first level subtype
    asset_subtype_2 = Column(String(200))  # NEW - second level subtype
    asset_name = Column(String(500), nullable=False)
    geographic_focus = Column(String(200))  # Renamed from location (kept original size)
    asset_identifier = Column(String(100))  # ISIN, CUSIP, etc.
    asset_status = Column(String(50), default="Active in portfolio")
    broker_asset_manager = Column(String(200))
    denomination_currency = Column(String(10), nullable=False)  # Expanded from String(3) for flexibility

    # Investment details from Excel - Base Currency
    initial_investment_date = Column(Date)
    number_of_shares = Column(Numeric(20, 6), default=0)
    avg_purchase_price_base_currency = Column(Numeric(20, 6), default=0)  # Renamed from avg_purchase_price
    total_investment_commitment_base_currency = Column(Numeric(20, 2), default=0)  # Renamed from total_investment_commitment
    paid_in_capital_base_currency = Column(Numeric(20, 2), default=0)  # Renamed from paid_in_capital
    asset_level_financing_base_currency = Column(Numeric(20, 2), default=0)  # Renamed from asset_level_financing
    unfunded_commitment_base_currency = Column(Numeric(20, 2), default=0)  # Renamed from pending_investment
    current_share_price = Column(Numeric(20, 6))
    estimated_asset_value_base_currency = Column(Numeric(20, 2))  # Renamed from estimated_asset_value
    total_asset_return_base_currency = Column(Numeric(20, 6))  # Renamed from total_asset_return (kept original precision)

    # FX Rates for multi-currency conversion
    usd_eur_inception = Column(Numeric(12, 8))  # USD/EUR rate at investment inception
    usd_eur_current = Column(Numeric(12, 8))  # Current USD/EUR rate
    usd_cad_current = Column(Numeric(12, 8))  # Current USD/CAD rate
    usd_chf_current = Column(Numeric(12, 8))  # Current USD/CHF rate
    usd_hkd_current = Column(Numeric(12, 8))  # Current USD/HKD rate

    # Multi-currency values - USD
    total_investment_commitment_usd = Column(Numeric(20, 2))
    paid_in_capital_usd = Column(Numeric(20, 2))
    unfunded_commitment_usd = Column(Numeric(20, 2))
    estimated_asset_value_usd = Column(Numeric(20, 2))
    total_asset_return_usd = Column(Numeric(10, 6))

    # Multi-currency values - EUR
    total_investment_commitment_eur = Column(Numeric(20, 2))
    paid_in_capital_eur = Column(Numeric(20, 2))
    unfunded_commitment_eur = Column(Numeric(20, 2))
    estimated_asset_value_eur = Column(Numeric(20, 2))
    total_asset_return_eur = Column(Numeric(10, 6))

    # Unrealized gain columns (NEW)
    unrealized_gain_usd = Column(Numeric(20, 2))
    unrealized_gain_eur = Column(Numeric(20, 2))

    # Realized gain columns (NEW - for Structured Notes)
    realized_gain_usd = Column(Numeric(20, 2))
    realized_gain_eur = Column(Numeric(20, 2))

    # Minimal audit fields
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships to extension tables
    structured_note = relationship("StructuredNote", back_populates="asset", uselist=False, cascade="all, delete-orphan")
    real_estate = relationship("RealEstateAsset", back_populates="asset", uselist=False, cascade="all, delete-orphan")

    # Calculated fields matching Excel formulas (for validation/recalculation)
    @hybrid_property
    def calculated_paid_in_capital(self) -> Any:  # Returns Decimal on instance, ColumnElement on class
        """Excel formula: =M*N (number_of_shares * avg_purchase_price_base_currency)"""
        if self.number_of_shares and self.avg_purchase_price_base_currency:
            return self.number_of_shares * self.avg_purchase_price_base_currency
        return Decimal(0)

    @hybrid_property
    def calculated_unfunded_commitment(self) -> Any:  # Returns Decimal on instance, ColumnElement on class
        """Excel formula: =O-P (total_investment_commitment_base_currency - paid_in_capital_base_currency)"""
        if self.total_investment_commitment_base_currency and self.paid_in_capital_base_currency:
            return self.total_investment_commitment_base_currency - self.paid_in_capital_base_currency
        return Decimal(0)

    @hybrid_property
    def calculated_return(self) -> Any:  # Returns Decimal|None on instance, ColumnElement on class
        """Excel formula: =IFERROR((T/P-1),"-") (estimated_asset_value_base_currency / paid_in_capital_base_currency - 1)"""
        if self.estimated_asset_value_base_currency and self.paid_in_capital_base_currency and self.paid_in_capital_base_currency > 0:
            return (self.estimated_asset_value_base_currency / self.paid_in_capital_base_currency) - 1
        return None

    __table_args__ = (
        Index("idx_assets_display_id", "display_id"),
        Index("idx_assets_entity", "ownership_holding_entity"),
        Index("idx_assets_managing_entity", "managing_entity"),
        Index("idx_assets_group", "asset_group"),
        Index("idx_assets_status", "asset_status"),
        Index("idx_assets_name", "asset_name"),
    )


class StructuredNote(Base):
    """
    Extension for structured notes. All column names from Excel preserved.
    Only for assets that are structured products.
    """

    __tablename__ = "structured_notes"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    asset_id = Column(UUID(as_uuid=True), ForeignKey("assets.id", ondelete="CASCADE"), nullable=False, unique=True)

    # All columns from StructuredNotes Excel sheet
    annual_coupon = Column(Numeric(10, 4))
    coupon_payment_frequency = Column(String(50))  # Quarterly, etc.
    next_coupon_review_date = Column(String(50))  # Keeping as string like Excel
    next_principal_review_date = Column(Date)
    final_due_date = Column(Date)
    redemption_type = Column(String(50))  # Fixed date, AUTOCALL

    underlying_index_name = Column(String(200))
    underlying_index_code = Column(String(50))
    strike_level = Column(Numeric(20, 6))
    underlying_index_level = Column(Numeric(20, 6))
    performance_vs_strike = Column(Numeric(20, 6))  # Calculated in Excel, stored here
    effective_strike_percentage = Column(Numeric(10, 4))
    note_leverage = Column(String(50))  # Keeping as string like Excel
    capital_protection = Column(Numeric(10, 4))
    capital_protection_barrier = Column(Numeric(20, 6))
    coupon_protection_barrier_pct = Column(Numeric(10, 4))
    coupon_protection_barrier_value = Column(Numeric(20, 6))

    # Relationship
    asset = relationship("Asset", back_populates="structured_note")

    # Calculated field matching Excel
    @hybrid_property
    def calculated_performance_vs_strike(self) -> Any:  # Returns Decimal|None on instance, ColumnElement on class
        """Excel formula: =IFERROR(AE/AD-1,"-")"""
        if self.underlying_index_level and self.strike_level and self.strike_level > 0:
            return (self.underlying_index_level / self.strike_level) - 1
        return None

    __table_args__ = (Index("idx_structured_notes_asset", "asset_id"),)


class RealEstateAsset(Base):
    """
    Extension for real estate assets. All column names from Excel preserved.
    Only for assets that are real estate developments.
    """

    __tablename__ = "real_estate_assets"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    asset_id = Column(UUID(as_uuid=True), ForeignKey("assets.id", ondelete="CASCADE"), nullable=False, unique=True)

    # NEW column - real estate status
    real_estate_status = Column(String(100))  # e.g., "Under development", "Completed"

    # Columns from RealEstate Excel sheet - EUR values (renamed with _eur suffix)
    cost_original_asset_eur = Column(Numeric(20, 2), default=0)
    estimated_capex_budget_eur = Column(Numeric(20, 2), default=0)
    pivert_development_fees_eur = Column(Numeric(20, 2), default=0)
    estimated_total_cost_eur = Column(Numeric(20, 2), default=0)  # Calculated in Excel
    capex_invested_eur = Column(Numeric(20, 2), default=0)
    total_investment_to_date_eur = Column(Numeric(20, 2), default=0)  # Calculated in Excel
    # asset_level_financing is in main assets table
    equity_investment_to_date_eur = Column(Numeric(20, 2), default=0)  # Calculated in Excel
    pending_equity_investment_eur = Column(Numeric(20, 2), default=0)  # Calculated in Excel
    # estimated_asset_value is in main assets table
    estimated_capital_gain_eur = Column(Numeric(20, 2))  # Calculated in Excel

    # NEW USD columns for multi-currency support
    estimated_total_cost_usd = Column(Numeric(20, 2))
    total_investment_to_date_usd = Column(Numeric(20, 2))
    equity_investment_to_date_usd = Column(Numeric(20, 2))
    pending_equity_investment_usd = Column(Numeric(20, 2))
    estimated_capital_gain_usd = Column(Numeric(20, 2))

    # Relationship
    asset = relationship("Asset", back_populates="real_estate")

    # Calculated fields matching Excel formulas
    @hybrid_property
    def calculated_total_cost(self) -> Any:  # Returns Decimal on instance, ColumnElement on class
        """Excel formula: =M+N+O"""
        return (self.cost_original_asset_eur or Decimal(0)) + (self.estimated_capex_budget_eur or Decimal(0)) + (self.pivert_development_fees_eur or Decimal(0))

    @hybrid_property
    def calculated_investment_to_date(self) -> Any:  # Returns Decimal on instance, ColumnElement on class
        """Excel formula: =M+Q+O"""
        return (self.cost_original_asset_eur or Decimal(0)) + (self.capex_invested_eur or Decimal(0)) + (self.pivert_development_fees_eur or Decimal(0))

    __table_args__ = (Index("idx_real_estate_asset", "asset_id"),)
