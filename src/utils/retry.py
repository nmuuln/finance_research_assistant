"""Retry utilities with exponential backoff for API calls."""

import time
import logging
from typing import TypeVar, Callable, Any
from functools import wraps

logger = logging.getLogger(__name__)

T = TypeVar('T')


def retry_with_backoff(
    max_retries: int = 3,
    initial_delay: float = 1.0,
    backoff_factor: float = 2.0,
    exceptions: tuple = (Exception,)
):
    """
    Decorator to retry a function with exponential backoff.

    Args:
        max_retries: Maximum number of retry attempts
        initial_delay: Initial delay in seconds
        backoff_factor: Multiplier for delay after each retry
        exceptions: Tuple of exceptions to catch and retry

    Example:
        @retry_with_backoff(max_retries=3, initial_delay=1.0)
        def call_api():
            return client.models.generate_content(...)
    """
    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @wraps(func)
        def wrapper(*args, **kwargs) -> T:
            delay = initial_delay
            last_exception = None

            for attempt in range(max_retries + 1):
                try:
                    return func(*args, **kwargs)
                except exceptions as e:
                    last_exception = e
                    error_msg = str(e)

                    # Check if it's a retryable error
                    is_retryable = (
                        "503" in error_msg or
                        "overloaded" in error_msg.lower() or
                        "UNAVAILABLE" in error_msg or
                        "429" in error_msg or  # Rate limit
                        "RESOURCE_EXHAUSTED" in error_msg
                    )

                    if not is_retryable or attempt == max_retries:
                        logger.error(f"Non-retryable error or max retries reached: {error_msg}")
                        raise

                    logger.warning(
                        f"Attempt {attempt + 1}/{max_retries + 1} failed with error: {error_msg}. "
                        f"Retrying in {delay:.1f}s..."
                    )
                    time.sleep(delay)
                    delay *= backoff_factor

            # Should not reach here, but just in case
            if last_exception is not None:
                raise last_exception
            raise RuntimeError("Unexpected retry loop exit")

        return wrapper
    return decorator


def retry_gemini_call(func: Callable[..., T]) -> Callable[..., T]:
    """
    Convenience decorator specifically for Gemini API calls.
    Pre-configured with sensible defaults for Gemini errors.

    Usage:
        @retry_gemini_call
        def my_gemini_function():
            return client.models.generate_content(...)
    """
    return retry_with_backoff(
        max_retries=5,
        initial_delay=3.0,
        backoff_factor=2.5,
        exceptions=(Exception,)
    )(func)
