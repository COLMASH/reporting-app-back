"""
Rate limiting configuration and utilities.
"""

from slowapi import Limiter
from slowapi.util import get_remote_address

from src.core.config import settings


def get_rate_limit_string() -> str:
    """
    Get rate limit string based on configuration.

    Returns:
        Rate limit string (e.g., "100/60" for 100 requests per 60 seconds)
    """
    return f"{settings.rate_limit_requests}/{settings.rate_limit_period}"


# Create limiter instance
limiter = Limiter(
    key_func=get_remote_address,
    default_limits=[get_rate_limit_string()],
    storage_uri=settings.redis_url if settings.redis_url else None,
)
