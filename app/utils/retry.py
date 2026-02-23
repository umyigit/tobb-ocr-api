from __future__ import annotations

from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

import httpx


def with_retry(max_retries: int = 3, backoff_factor: float = 0.5):
    """Exponential backoff retry decorator for HTTP operations."""
    return retry(
        retry=retry_if_exception_type((httpx.TransportError, httpx.TimeoutException)),
        stop=stop_after_attempt(max_retries),
        wait=wait_exponential(multiplier=backoff_factor, min=0.5, max=30),
        reraise=True,
    )
