"""update_portfolio_schema_renames_and_new_columns

This migration updates the portfolio schema to match the new Excel structure:

ASSETS table:
- Renames: asset_group -> managing_entity, asset_group_strategy -> asset_group
- New columns: holding_company, unrealized_gain_usd, unrealized_gain_eur

REAL_ESTATE_ASSETS table:
- Renames: 9 columns get _eur suffix
- New columns: real_estate_status, estimated_net_asset_value_eur, and 6 USD columns

Revision ID: afb17921c4ce
Revises: 03f1653e4ef0
Create Date: 2025-12-11 18:08:18.877519

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'afb17921c4ce'
down_revision: Union[str, None] = '03f1653e4ef0'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ========================================
    # ASSETS TABLE CHANGES
    # ========================================

    # 1. Renames (order matters - rename asset_group first, then asset_group_strategy)
    op.alter_column('assets', 'asset_group', new_column_name='managing_entity')
    op.alter_column('assets', 'asset_group_strategy', new_column_name='asset_group')

    # 2. New columns
    op.add_column('assets', sa.Column('holding_company', sa.String(length=100), nullable=True))
    op.add_column('assets', sa.Column('unrealized_gain_usd', sa.Numeric(precision=20, scale=2), nullable=True))
    op.add_column('assets', sa.Column('unrealized_gain_eur', sa.Numeric(precision=20, scale=2), nullable=True))

    # ========================================
    # REAL_ESTATE_ASSETS TABLE CHANGES
    # ========================================

    # 1. Renames - add _eur suffix to existing columns
    op.alter_column('real_estate_assets', 'cost_original_asset', new_column_name='cost_original_asset_eur')
    op.alter_column('real_estate_assets', 'estimated_capex_budget', new_column_name='estimated_capex_budget_eur')
    op.alter_column('real_estate_assets', 'pivert_development_fees', new_column_name='pivert_development_fees_eur')
    op.alter_column('real_estate_assets', 'estimated_total_cost', new_column_name='estimated_total_cost_eur')
    op.alter_column('real_estate_assets', 'capex_invested', new_column_name='capex_invested_eur')
    op.alter_column('real_estate_assets', 'total_investment_to_date', new_column_name='total_investment_to_date_eur')
    op.alter_column('real_estate_assets', 'equity_investment_to_date', new_column_name='equity_investment_to_date_eur')
    op.alter_column('real_estate_assets', 'pending_equity_investment', new_column_name='pending_equity_investment_eur')
    op.alter_column('real_estate_assets', 'estimated_capital_gain', new_column_name='estimated_capital_gain_eur')

    # 2. New columns
    op.add_column('real_estate_assets', sa.Column('real_estate_status', sa.String(length=100), nullable=True))
    op.add_column('real_estate_assets', sa.Column('estimated_net_asset_value_eur', sa.Numeric(precision=20, scale=2), nullable=True))
    op.add_column('real_estate_assets', sa.Column('estimated_total_cost_usd', sa.Numeric(precision=20, scale=2), nullable=True))
    op.add_column('real_estate_assets', sa.Column('total_investment_to_date_usd', sa.Numeric(precision=20, scale=2), nullable=True))
    op.add_column('real_estate_assets', sa.Column('equity_investment_to_date_usd', sa.Numeric(precision=20, scale=2), nullable=True))
    op.add_column('real_estate_assets', sa.Column('pending_equity_investment_usd', sa.Numeric(precision=20, scale=2), nullable=True))
    op.add_column('real_estate_assets', sa.Column('estimated_net_asset_value_usd', sa.Numeric(precision=20, scale=2), nullable=True))
    op.add_column('real_estate_assets', sa.Column('estimated_capital_gain_usd', sa.Numeric(precision=20, scale=2), nullable=True))


def downgrade() -> None:
    # ========================================
    # REAL_ESTATE_ASSETS TABLE - REVERT
    # ========================================

    # 1. Drop new columns
    op.drop_column('real_estate_assets', 'estimated_capital_gain_usd')
    op.drop_column('real_estate_assets', 'estimated_net_asset_value_usd')
    op.drop_column('real_estate_assets', 'pending_equity_investment_usd')
    op.drop_column('real_estate_assets', 'equity_investment_to_date_usd')
    op.drop_column('real_estate_assets', 'total_investment_to_date_usd')
    op.drop_column('real_estate_assets', 'estimated_total_cost_usd')
    op.drop_column('real_estate_assets', 'estimated_net_asset_value_eur')
    op.drop_column('real_estate_assets', 'real_estate_status')

    # 2. Revert renames - remove _eur suffix
    op.alter_column('real_estate_assets', 'estimated_capital_gain_eur', new_column_name='estimated_capital_gain')
    op.alter_column('real_estate_assets', 'pending_equity_investment_eur', new_column_name='pending_equity_investment')
    op.alter_column('real_estate_assets', 'equity_investment_to_date_eur', new_column_name='equity_investment_to_date')
    op.alter_column('real_estate_assets', 'total_investment_to_date_eur', new_column_name='total_investment_to_date')
    op.alter_column('real_estate_assets', 'capex_invested_eur', new_column_name='capex_invested')
    op.alter_column('real_estate_assets', 'estimated_total_cost_eur', new_column_name='estimated_total_cost')
    op.alter_column('real_estate_assets', 'pivert_development_fees_eur', new_column_name='pivert_development_fees')
    op.alter_column('real_estate_assets', 'estimated_capex_budget_eur', new_column_name='estimated_capex_budget')
    op.alter_column('real_estate_assets', 'cost_original_asset_eur', new_column_name='cost_original_asset')

    # ========================================
    # ASSETS TABLE - REVERT
    # ========================================

    # 1. Drop new columns
    op.drop_column('assets', 'unrealized_gain_eur')
    op.drop_column('assets', 'unrealized_gain_usd')
    op.drop_column('assets', 'holding_company')

    # 2. Revert renames (reverse order - rename asset_group back to asset_group_strategy first)
    op.alter_column('assets', 'asset_group', new_column_name='asset_group_strategy')
    op.alter_column('assets', 'managing_entity', new_column_name='asset_group')
