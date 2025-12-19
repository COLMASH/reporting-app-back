"""Remove estimated_net_asset_value columns from real_estate_assets

These columns were added due to a typo in the Excel file.
The correct columns are estimated_asset_value_eur/usd which exist in the parent assets table.

Revision ID: b5c8a2d1e3f4
Revises: afb17921c4ce
Create Date: 2024-12-11

"""

from typing import Sequence, Union

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "b5c8a2d1e3f4"
down_revision: Union[str, None] = "afb17921c4ce"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Drop the incorrectly named columns."""
    op.drop_column("real_estate_assets", "estimated_net_asset_value_eur")
    op.drop_column("real_estate_assets", "estimated_net_asset_value_usd")


def downgrade() -> None:
    """Re-add the columns if needed."""
    import sqlalchemy as sa

    op.add_column(
        "real_estate_assets",
        sa.Column("estimated_net_asset_value_eur", sa.Numeric(20, 2), nullable=True),
    )
    op.add_column(
        "real_estate_assets",
        sa.Column("estimated_net_asset_value_usd", sa.Numeric(20, 2), nullable=True),
    )
