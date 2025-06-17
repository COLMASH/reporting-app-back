"""
API route registration.
"""

from fastapi import FastAPI

from src.analysis.controller import router as analysis_router
from src.auth.controller import router as auth_router
from src.files.controller import router as files_router
from src.results.controller import router as results_router


def register_routes(app: FastAPI) -> None:
    """
    Register all API routes with the FastAPI application.

    Args:
        app: FastAPI application instance
    """
    # API v1 routes
    api_v1_prefix = "/api/v1"

    # Register routers
    app.include_router(auth_router, prefix=api_v1_prefix)
    app.include_router(files_router, prefix=api_v1_prefix)
    app.include_router(analysis_router, prefix=api_v1_prefix)
    app.include_router(results_router, prefix=api_v1_prefix)

    # Health check route
    @app.get("/health")
    async def health_check() -> dict[str, str]:
        """Basic health check endpoint."""
        return {"status": "healthy", "service": "reporting-backend"}

    @app.get("/")
    async def root() -> dict[str, str]:
        """Root endpoint."""
        return {
            "service": "Reporting Backend API",
            "version": "0.1.0",
            "docs": "/docs",
            "redoc": "/redoc",
        }
