"""Retry with exponential backoff for the live tool adapters.

Live adapters hit real third-party APIs (GitHub/Jira/Confluence/Slack/Jenkins), which fail transiently —
timeouts, dropped connections, and HTTP 429/5xx rate-limit/availability blips. ``retry_async`` re-runs an
async call a bounded number of times with exponential backoff before giving up. It is transient-only: a
4xx that isn't 429 (a real client error) is raised immediately, never retried.

Offline-safe: ``base_delay=0`` (the test default) skips the sleep entirely, so the retry path is
exercised deterministically without wall-clock waits.
"""

from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Callable
from typing import TypeVar

from app.core.logging import get_logger

_log = get_logger("apex.tools.retry")

T = TypeVar("T")


class TransientToolError(Exception):
    """A retryable adapter failure (timeout, connection reset, or an HTTP 429/5xx)."""


def _is_transient(exc: BaseException) -> bool:
    if isinstance(exc, TransientToolError):
        return True
    # httpx transport errors are transient; imported lazily so the core stays dependency-light.
    try:
        import httpx

        if isinstance(exc, (httpx.TimeoutException, httpx.TransportError)):
            return True
        if isinstance(exc, httpx.HTTPStatusError):
            code = exc.response.status_code
            return code == 429 or 500 <= code < 600
    except ImportError:  # pragma: no cover - httpx is always present in practice
        pass
    return False


async def retry_async(
    factory: Callable[[], Awaitable[T]],
    *,
    attempts: int = 3,
    base_delay: float = 0.0,
    tool: str = "",
) -> T:
    """Await ``factory()``, retrying on transient failures up to ``attempts`` total tries.

    ``factory`` must return a *fresh* awaitable each call (a lambda), since a coroutine can only be
    awaited once. Backoff is ``base_delay * 2**n``; a non-transient exception propagates immediately.
    """
    last: BaseException | None = None
    for attempt in range(max(1, attempts)):
        try:
            return await factory()
        except BaseException as exc:  # noqa: BLE001 - re-raised below if not transient/exhausted
            if not _is_transient(exc) or attempt == attempts - 1:
                raise
            last = exc
            delay = base_delay * (2**attempt)
            _log.warning(
                "tool.retry", tool=tool, attempt=attempt + 1, of=attempts, error=str(exc), delay=delay
            )
            if delay > 0:
                await asyncio.sleep(delay)
    raise last if last is not None else RuntimeError("retry_async exhausted with no error")
