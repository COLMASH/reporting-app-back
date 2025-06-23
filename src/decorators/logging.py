"""
Logging decorator for automatic endpoint logging.
Similar to NestJS's @Logger() decorator.
"""

import functools
import inspect
from collections.abc import Callable
from typing import Any

from fastapi import Request

from src.logging import get_logger


def log_endpoint(func: Callable) -> Callable:
    """
    Decorator that automatically logs endpoint calls.

    Usage:
        @router.get("/users")
        @log_endpoint
        async def get_users(...):
            ...

    Logs:
        - Function entry with all parameters (except Request, db sessions)
        - Function exit with success
        - Any exceptions that occur
    """
    logger = get_logger(func.__module__)

    @functools.wraps(func)
    async def wrapper(*args: Any, **kwargs: Any) -> Any:
        # Get function signature
        sig = inspect.signature(func)
        bound_args = sig.bind(*args, **kwargs)
        bound_args.apply_defaults()

        # Extract request ID from any request-like object
        request = None
        request_id = "unknown"

        for _arg_name, arg_value in bound_args.arguments.items():
            # Check if it's a FastAPI Request or has a state attribute with request_id
            if isinstance(arg_value, Request) or (
                hasattr(arg_value, "state") and hasattr(arg_value.state, "request_id")
            ):
                request = arg_value
                request_id = getattr(request.state, "request_id", "unknown")
                break

        # Filter out technical parameters we don't want to log
        log_params = {}
        skip_params = {"request", "req", "db", "current_user"}  # Parameter names to skip
        skip_types = ("Request", "Session", "DbSession", "CurrentUser", "OptionalUser", "AdminUser")

        for name, value in bound_args.arguments.items():
            # Skip by parameter name
            if name in skip_params:
                continue

            param = sig.parameters[name]

            # Skip technical parameters by type annotation
            annotation_str = str(param.annotation)
            if any(skip_type in annotation_str for skip_type in skip_types):
                continue

            # Skip if value is None
            if value is None:
                continue

            # For Pydantic models, extract key fields
            if hasattr(value, "model_dump"):
                model_data = value.model_dump()
                # Only log safe fields (no passwords)
                safe_fields = ["email", "name", "role", "company_name"]
                filtered_data = {k: v for k, v in model_data.items() if k in safe_fields}
                if filtered_data:  # Only add if we have data to log
                    log_params[name] = filtered_data
            else:
                log_params[name] = value

        # Log function entry
        if log_params:
            # Flatten nested dicts for better logging
            flat_params = {}
            for key, value in log_params.items():
                if isinstance(value, dict):
                    for k, v in value.items():
                        flat_params[f"{key}_{k}"] = v
                else:
                    flat_params[key] = value
            logger.info(f"{func.__name__} called", request_id=request_id, **flat_params)
        else:
            logger.info(f"{func.__name__} called", request_id=request_id)

        try:
            # Call the actual function
            result = await func(*args, **kwargs)

            # Log successful completion
            logger.info(
                f"{func.__name__} completed",
                request_id=request_id,
            )

            return result

        except Exception as e:
            # Log any exceptions without exposing local variables
            logger.error(
                f"{func.__name__} failed",
                request_id=request_id,
                error=str(e),
                # Don't use exc_info=True as it exposes local variables including passwords
            )
            raise

    return wrapper
