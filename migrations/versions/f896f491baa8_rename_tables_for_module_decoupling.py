"""Rename tables for module decoupling

Revision ID: f896f491baa8
Revises: 9d0621f8a4b9
Create Date: 2025-07-12 21:35:45.446739

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'f896f491baa8'
down_revision: Union[str, None] = '9d0621f8a4b9'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Rename tables to their new names
    # Note: reporting_analyses stays as is per user request
    op.rename_table('reporting_file_uploads', 'files')
    op.rename_table('reporting_results', 'results')
    
    # Update foreign key constraints
    # For reporting_analyses table - update FK to files table
    op.drop_constraint('reporting_analyses_file_id_fkey', 'reporting_analyses', type_='foreignkey')
    op.create_foreign_key('reporting_analyses_file_id_fkey', 'reporting_analyses', 'files', ['file_id'], ['id'], ondelete='CASCADE')
    
    # For results table - update FK to reporting_analyses table  
    op.drop_constraint('reporting_results_analysis_id_fkey', 'results', type_='foreignkey')
    op.create_foreign_key('results_analysis_id_fkey', 'results', 'reporting_analyses', ['analysis_id'], ['id'], ondelete='CASCADE')


def downgrade() -> None:
    # Update foreign key constraints back
    op.drop_constraint('results_analysis_id_fkey', 'results', type_='foreignkey')
    op.create_foreign_key('reporting_results_analysis_id_fkey', 'results', 'reporting_analyses', ['analysis_id'], ['id'], ondelete='CASCADE')
    
    op.drop_constraint('reporting_analyses_file_id_fkey', 'reporting_analyses', type_='foreignkey')
    op.create_foreign_key('reporting_analyses_file_id_fkey', 'reporting_analyses', 'reporting_file_uploads', ['file_id'], ['id'], ondelete='CASCADE')
    
    # Rename tables back
    op.rename_table('results', 'reporting_results')
    op.rename_table('files', 'reporting_file_uploads')