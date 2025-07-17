"""
Dependencies for reporting analysis module.
"""

from typing import Annotated

from fastapi import Depends

from src.modules.auth.dependencies import DbSession

# TODO: Add analysis-specific dependencies as needed


# Functional service dependencies
def get_db_session(db: DbSession) -> DbSession:
    """Pass through database session for functional services."""
    return db


DbSessionDep = Annotated[DbSession, Depends(get_db_session)]
