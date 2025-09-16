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

from sqlalchemy import Column, Date, DateTime, ForeignKey, Index, Numeric, String
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

    # Excel columns - kept exact names
    report_date = Column(Date)
    ownership_holding_entity = Column(String(100), nullable=False)
    asset_group = Column(String(100), nullable=False)
    asset_sub_group = Column(String(100))
    asset_type = Column(String(100), nullable=False)
    asset_name = Column(String(500), nullable=False)
    location = Column(String(200))
    asset_identifier = Column(String(100))  # ISIN, CUSIP, etc.
    asset_status = Column(String(50), default="Active in portfolio")
    broker_asset_manager = Column(String(200))
    denomination_currency = Column(String(3), nullable=False)  # EUR, USD, etc.

    # Investment details from Excel
    initial_investment_date = Column(Date)
    number_of_shares = Column(Numeric(20, 6), default=0)
    avg_purchase_price = Column(Numeric(20, 6), default=0)
    total_investment_commitment = Column(Numeric(20, 2), default=0)
    paid_in_capital = Column(Numeric(20, 2), default=0)  # In Excel this is calculated, but we store it
    asset_level_financing = Column(Numeric(20, 2), default=0)
    pending_investment = Column(Numeric(20, 2), default=0)  # In Excel this is calculated
    current_share_price = Column(Numeric(20, 6))
    estimated_asset_value = Column(Numeric(20, 2))
    total_asset_return = Column(Numeric(20, 6))  # Store the calculated value

    # Minimal audit fields
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships to extension tables
    structured_note = relationship("StructuredNote", back_populates="asset", uselist=False, cascade="all, delete-orphan")
    real_estate = relationship("RealEstateAsset", back_populates="asset", uselist=False, cascade="all, delete-orphan")

    # Calculated fields matching Excel formulas (for validation/recalculation)
    @hybrid_property
    def calculated_paid_in_capital(self) -> Any:  # Returns Decimal on instance, ColumnElement on class
        """Excel formula: =M*N (number_of_shares * avg_purchase_price)"""
        if self.number_of_shares and self.avg_purchase_price:
            return self.number_of_shares * self.avg_purchase_price
        return Decimal(0)

    @hybrid_property
    def calculated_pending_investment(self) -> Any:  # Returns Decimal on instance, ColumnElement on class
        """Excel formula: =O-P (total_investment_commitment - paid_in_capital)"""
        if self.total_investment_commitment and self.paid_in_capital:
            return self.total_investment_commitment - self.paid_in_capital
        return Decimal(0)

    @hybrid_property
    def calculated_return(self) -> Any:  # Returns Decimal|None on instance, ColumnElement on class
        """Excel formula: =IFERROR((T/P-1),"-") (estimated_asset_value / paid_in_capital - 1)"""
        if self.estimated_asset_value and self.paid_in_capital and self.paid_in_capital > 0:
            return (self.estimated_asset_value / self.paid_in_capital) - 1
        return None

    __table_args__ = (
        Index("idx_assets_entity", "ownership_holding_entity"),
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

    # Columns from RealEstate Excel sheet
    cost_original_asset = Column(Numeric(20, 2), default=0)
    estimated_capex_budget = Column(Numeric(20, 2), default=0)
    pivert_development_fees = Column(Numeric(20, 2), default=0)
    estimated_total_cost = Column(Numeric(20, 2), default=0)  # Calculated in Excel
    capex_invested = Column(Numeric(20, 2), default=0)
    total_investment_to_date = Column(Numeric(20, 2), default=0)  # Calculated in Excel
    # asset_level_financing is in main assets table
    equity_investment_to_date = Column(Numeric(20, 2), default=0)  # Calculated in Excel
    pending_equity_investment = Column(Numeric(20, 2), default=0)  # Calculated in Excel
    # estimated_asset_value is in main assets table
    estimated_capital_gain = Column(Numeric(20, 2))  # Calculated in Excel

    # Relationship
    asset = relationship("Asset", back_populates="real_estate")

    # Calculated fields matching Excel formulas
    @hybrid_property
    def calculated_total_cost(self) -> Any:  # Returns Decimal on instance, ColumnElement on class
        """Excel formula: =M+N+O"""
        return (self.cost_original_asset or Decimal(0)) + (self.estimated_capex_budget or Decimal(0)) + (self.pivert_development_fees or Decimal(0))

    @hybrid_property
    def calculated_investment_to_date(self) -> Any:  # Returns Decimal on instance, ColumnElement on class
        """Excel formula: =M+Q+O"""
        return (self.cost_original_asset or Decimal(0)) + (self.capex_invested or Decimal(0)) + (self.pivert_development_fees or Decimal(0))

    __table_args__ = (Index("idx_real_estate_asset", "asset_id"),)
