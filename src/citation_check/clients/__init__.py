"""Shared utilities for API clients."""

from __future__ import annotations

import asyncio
import functools
from collections.abc import Callable
from typing import TypeVar

import httpx

T = TypeVar("T")

_MAX_RETRIES = 3
_BASE_DELAY = 1.0  # seconds


def retry_on_rate_limit(func: Callable[..., T]) -> Callable[..., T]:
    """Decorator that retries an async function on HTTP 429 with exponential backoff.

    Retries up to 3 times with delays of 1s, 2s, 4s.
    Only retries on httpx.HTTPStatusError with status_code == 429.
    """

    @functools.wraps(func)
    async def wrapper(*args, **kwargs):
        last_exc: Exception | None = None
        for attempt in range(_MAX_RETRIES + 1):
            try:
                return await func(*args, **kwargs)
            except httpx.HTTPStatusError as exc:
                if exc.response.status_code != 429 or attempt == _MAX_RETRIES:
                    raise
                last_exc = exc
                delay = _BASE_DELAY * (2**attempt)
                await asyncio.sleep(delay)
        raise last_exc  # type: ignore[misc]  # pragma: no cover

    return wrapper
