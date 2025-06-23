"""Rename tables to use reporting_ prefix

Revision ID: 1178c10e0997
Revises: 801adf5bfe88
Create Date: 2025-06-23 15:24:23.157276

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '1178c10e0997'
down_revision: Union[str, None] = '801adf5bfe88'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Rename tables
    op.rename_table('file_uploads', 'reporting_file_uploads')
    op.rename_table('analyses', 'reporting_analyses')
    op.rename_table('results', 'reporting_results')
    
    # Drop old foreign key constraints
    op.drop_constraint('analyses_file_id_fkey', 'reporting_analyses', type_='foreignkey')
    op.drop_constraint('results_analysis_id_fkey', 'reporting_results', type_='foreignkey')
    
    # Create new foreign key constraints with updated table references
    op.create_foreign_key(
        'reporting_analyses_file_id_fkey',
        'reporting_analyses',
        'reporting_file_uploads',
        ['file_id'],
        ['id'],
        ondelete='CASCADE'
    )
    op.create_foreign_key(
        'reporting_results_analysis_id_fkey',
        'reporting_results',
        'reporting_analyses',
        ['analysis_id'],
        ['id'],
        ondelete='CASCADE'
    )


def downgrade() -> None:
    # Drop new foreign key constraints
    op.drop_constraint('reporting_analyses_file_id_fkey', 'reporting_analyses', type_='foreignkey')
    op.drop_constraint('reporting_results_analysis_id_fkey', 'reporting_results', type_='foreignkey')
    
    # Create old foreign key constraints
    op.create_foreign_key(
        'analyses_file_id_fkey',
        'reporting_analyses',
        'reporting_file_uploads',
        ['file_id'],
        ['id'],
        ondelete='CASCADE'
    )
    op.create_foreign_key(
        'results_analysis_id_fkey',
        'reporting_results',
        'reporting_analyses',
        ['analysis_id'],
        ['id'],
        ondelete='CASCADE'
    )
    
    # Rename tables back
    op.rename_table('reporting_file_uploads', 'file_uploads')
    op.rename_table('reporting_analyses', 'analyses')
    op.rename_table('reporting_results', 'results')