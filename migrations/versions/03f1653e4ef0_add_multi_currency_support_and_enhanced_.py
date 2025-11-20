"""add_multi_currency_support_and_enhanced_categorization

Revision ID: 03f1653e4ef0
Revises: e47ac02c7b04
Create Date: 2025-11-20 15:40:41.571288

This migration adds:
1. Display ID column for user-friendly reference
2. Multi-currency support (USD/EUR) with FX rates
3. Enhanced asset categorization (asset_subtype, asset_subtype_2)
4. Renamed columns for clarity (_base_currency suffix)
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '03f1653e4ef0'
down_revision: Union[str, None] = 'e47ac02c7b04'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ========================================================================
    # STEP 1: ADD NEW COLUMNS
    # ========================================================================

    # 1. Display ID for user-friendly sequential numbering
    op.add_column('assets', sa.Column('display_id', sa.Integer(), nullable=True))
    op.create_index('idx_assets_display_id', 'assets', ['display_id'], unique=False)

    # 2. Enhanced categorization columns
    op.add_column('assets', sa.Column('asset_subtype', sa.String(length=100), nullable=True))
    op.add_column('assets', sa.Column('asset_subtype_2', sa.String(length=200), nullable=True))

    # 3. FX Rates (5 columns) - high precision for accurate conversion
    op.add_column('assets', sa.Column('usd_eur_inception', sa.Numeric(precision=12, scale=8), nullable=True))
    op.add_column('assets', sa.Column('usd_eur_current', sa.Numeric(precision=12, scale=8), nullable=True))
    op.add_column('assets', sa.Column('usd_cad_current', sa.Numeric(precision=12, scale=8), nullable=True))
    op.add_column('assets', sa.Column('usd_chf_current', sa.Numeric(precision=12, scale=8), nullable=True))
    op.add_column('assets', sa.Column('usd_hkd_current', sa.Numeric(precision=12, scale=8), nullable=True))

    # 4. Multi-currency financial amounts - USD (5 columns)
    op.add_column('assets', sa.Column('total_investment_commitment_usd', sa.Numeric(precision=20, scale=2), nullable=True))
    op.add_column('assets', sa.Column('paid_in_capital_usd', sa.Numeric(precision=20, scale=2), nullable=True))
    op.add_column('assets', sa.Column('unfunded_commitment_usd', sa.Numeric(precision=20, scale=2), nullable=True))
    op.add_column('assets', sa.Column('estimated_asset_value_usd', sa.Numeric(precision=20, scale=2), nullable=True))
    op.add_column('assets', sa.Column('total_asset_return_usd', sa.Numeric(precision=10, scale=6), nullable=True))

    # 5. Multi-currency financial amounts - EUR (5 columns)
    op.add_column('assets', sa.Column('total_investment_commitment_eur', sa.Numeric(precision=20, scale=2), nullable=True))
    op.add_column('assets', sa.Column('paid_in_capital_eur', sa.Numeric(precision=20, scale=2), nullable=True))
    op.add_column('assets', sa.Column('unfunded_commitment_eur', sa.Numeric(precision=20, scale=2), nullable=True))
    op.add_column('assets', sa.Column('estimated_asset_value_eur', sa.Numeric(precision=20, scale=2), nullable=True))
    op.add_column('assets', sa.Column('total_asset_return_eur', sa.Numeric(precision=10, scale=6), nullable=True))

    # ========================================================================
    # STEP 2: RENAME EXISTING COLUMNS
    # ========================================================================

    # Strategic grouping rename
    op.alter_column('assets', 'asset_sub_group', new_column_name='asset_group_strategy')

    # Geographic clarity rename
    op.alter_column('assets', 'location', new_column_name='geographic_focus')

    # Financial columns - add _base_currency suffix for multi-currency clarity
    op.alter_column('assets', 'avg_purchase_price', new_column_name='avg_purchase_price_base_currency')
    op.alter_column('assets', 'total_investment_commitment', new_column_name='total_investment_commitment_base_currency')
    op.alter_column('assets', 'paid_in_capital', new_column_name='paid_in_capital_base_currency')
    op.alter_column('assets', 'asset_level_financing', new_column_name='asset_level_financing_base_currency')
    op.alter_column('assets', 'pending_investment', new_column_name='unfunded_commitment_base_currency')
    op.alter_column('assets', 'estimated_asset_value', new_column_name='estimated_asset_value_base_currency')
    op.alter_column('assets', 'total_asset_return', new_column_name='total_asset_return_base_currency')

    # ========================================================================
    # STEP 3: UPDATE COLUMN TYPES FOR FLEXIBILITY
    # ========================================================================

    # Expand denomination_currency from String(3) to String(10) for flexibility
    op.alter_column('assets', 'denomination_currency',
                    existing_type=sa.String(length=3),
                    type_=sa.String(length=10),
                    existing_nullable=False)


def downgrade() -> None:
    # ========================================================================
    # REVERSE STEP 3: REVERT COLUMN TYPE CHANGES
    # ========================================================================

    # Revert denomination_currency back to String(3)
    op.alter_column('assets', 'denomination_currency',
                    existing_type=sa.String(length=10),
                    type_=sa.String(length=3),
                    existing_nullable=False)

    # ========================================================================
    # REVERSE STEP 2: RENAME COLUMNS BACK TO ORIGINAL NAMES
    # ========================================================================

    # Revert financial column renames
    op.alter_column('assets', 'total_asset_return_base_currency', new_column_name='total_asset_return')
    op.alter_column('assets', 'estimated_asset_value_base_currency', new_column_name='estimated_asset_value')
    op.alter_column('assets', 'unfunded_commitment_base_currency', new_column_name='pending_investment')
    op.alter_column('assets', 'asset_level_financing_base_currency', new_column_name='asset_level_financing')
    op.alter_column('assets', 'paid_in_capital_base_currency', new_column_name='paid_in_capital')
    op.alter_column('assets', 'total_investment_commitment_base_currency', new_column_name='total_investment_commitment')
    op.alter_column('assets', 'avg_purchase_price_base_currency', new_column_name='avg_purchase_price')

    # Revert geographic rename
    op.alter_column('assets', 'geographic_focus', new_column_name='location')

    # Revert strategic grouping rename
    op.alter_column('assets', 'asset_group_strategy', new_column_name='asset_sub_group')

    # ========================================================================
    # REVERSE STEP 1: DROP ALL NEW COLUMNS
    # ========================================================================

    # Drop multi-currency EUR columns
    op.drop_column('assets', 'total_asset_return_eur')
    op.drop_column('assets', 'estimated_asset_value_eur')
    op.drop_column('assets', 'unfunded_commitment_eur')
    op.drop_column('assets', 'paid_in_capital_eur')
    op.drop_column('assets', 'total_investment_commitment_eur')

    # Drop multi-currency USD columns
    op.drop_column('assets', 'total_asset_return_usd')
    op.drop_column('assets', 'estimated_asset_value_usd')
    op.drop_column('assets', 'unfunded_commitment_usd')
    op.drop_column('assets', 'paid_in_capital_usd')
    op.drop_column('assets', 'total_investment_commitment_usd')

    # Drop FX rate columns
    op.drop_column('assets', 'usd_hkd_current')
    op.drop_column('assets', 'usd_chf_current')
    op.drop_column('assets', 'usd_cad_current')
    op.drop_column('assets', 'usd_eur_current')
    op.drop_column('assets', 'usd_eur_inception')

    # Drop categorization columns
    op.drop_column('assets', 'asset_subtype_2')
    op.drop_column('assets', 'asset_subtype')

    # Drop display ID and its index
    op.drop_index('idx_assets_display_id', table_name='assets')
    op.drop_column('assets', 'display_id')
