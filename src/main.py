"""
FastAPI application entry point.
"""

from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address

from src.api import register_routes
from src.config import settings
from src.database.core import Base, engine

# Import all entities to ensure they're registered with SQLAlchemy
from src.exceptions import BaseError
from src.logging import get_logger
from src.middleware.logging import LoggingMiddleware

logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """
    Application lifespan manager.
    Handles startup and shutdown events.
    """
    # Startup
    logger.info("Starting up application", environment=settings.environment)

    # Create database tables if they don't exist
    # In production, use Alembic migrations instead
    if settings.is_development:
        logger.info("Creating database tables")
        Base.metadata.create_all(bind=engine)

    yield

    # Shutdown
    logger.info("Shutting down application")


# Create FastAPI app
app = FastAPI(
    title=settings.app_name,
    description="Backend API for Excel file analysis and reporting",
    version="0.1.0",
    docs_url="/docs" if not settings.is_production else None,
    redoc_url="/redoc" if not settings.is_production else None,
    lifespan=lifespan,
)

# Configure logging middleware (must be added after CORS)
app.add_middleware(LoggingMiddleware)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.backend_cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Configure rate limiting
limiter = Limiter(key_func=get_remote_address)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)  # type: ignore[arg-type]


# Global exception handler
@app.exception_handler(BaseError)
async def custom_exception_handler(request: Request, exc: BaseError) -> JSONResponse:
    """Handle custom application exceptions."""
    logger.error(
        "Application error",
        error_type=type(exc).__name__,
        detail=exc.detail,
        status_code=exc.status_code,
        path=request.url.path,
    )
    return JSONResponse(status_code=exc.status_code, content={"detail": exc.detail})


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """Handle unexpected exceptions."""
    logger.exception("Unexpected error", exc_info=exc, path=request.url.path, method=request.method)

    # Don't expose internal errors in production
    if settings.is_production:
        return JSONResponse(status_code=500, content={"detail": "Internal server error"})
    else:
        return JSONResponse(status_code=500, content={"detail": f"Internal error: {str(exc)}"})


# Register routes
register_routes(app)

# Log application startup
logger.info(
    "Application configured",
    environment=settings.environment,
    cors_origins=settings.backend_cors_origins,
    debug=settings.debug,
)
