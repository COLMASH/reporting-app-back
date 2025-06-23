"""
Middleware modules for cross-cutting concerns.
"""

from src.core.middleware.logging import LoggingMiddleware

__all__ = ["LoggingMiddleware"]
