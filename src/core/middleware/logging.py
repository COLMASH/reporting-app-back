"""
Request/Response logging middleware.
"""

import time
import uuid
from collections.abc import Awaitable, Callable

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

from src.core.logging import get_logger

logger = get_logger(__name__)


class LoggingMiddleware(BaseHTTPMiddleware):
    """
    Middleware to log HTTP requests and responses.
    Similar to NestJS's built-in request logging.
    """

    async def dispatch(
        self, request: Request, call_next: Callable[[Request], Awaitable[Response]]
    ) -> Response:
        # Generate unique request ID
        request_id = str(uuid.uuid4())

        # Add request ID to request state for access in routes
        request.state.request_id = request_id

        # Extract request details
        method = request.method
        path = request.url.path
        client_host = request.client.host if request.client else "unknown"

        # Log incoming request
        logger.info(
            "Incoming request",
            request_id=request_id,
            method=method,
            path=path,
            client=client_host,
            query_params=dict(request.query_params),
        )

        # Track request timing
        start_time = time.time()

        try:
            # Process request
            response = await call_next(request)

            # Calculate request duration
            duration_ms = round((time.time() - start_time) * 1000, 2)

            # Log response
            logger.info(
                "Request completed",
                request_id=request_id,
                method=method,
                path=path,
                status_code=response.status_code,
                duration_ms=duration_ms,
            )

            # Add request ID to response headers
            response.headers["X-Request-ID"] = request_id

            return response

        except Exception as e:
            # Calculate request duration
            duration_ms = round((time.time() - start_time) * 1000, 2)

            # Log error without exposing local variables
            logger.error(
                "Request failed",
                request_id=request_id,
                method=method,
                path=path,
                duration_ms=duration_ms,
                error=str(e),
                # Don't use exc_info=True to avoid exposing sensitive data in stack traces
            )

            # Re-raise to let exception handlers deal with it
            raise
