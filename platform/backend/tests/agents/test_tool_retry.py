"""Retry/backoff + per-tool-call audit tests (completion Batch D, closes Increment 10)."""

from __future__ import annotations

import pytest

from app.agents.tools.retry import TransientToolError, retry_async


@pytest.mark.asyncio
async def test_retry_succeeds_after_transient_failures():
    calls = {"n": 0}

    async def flaky():
        calls["n"] += 1
        if calls["n"] < 3:
            raise TransientToolError("429 rate limited")
        return "ok"

    result = await retry_async(lambda: flaky(), attempts=3, base_delay=0.0, tool="jira")
    assert result == "ok"
    assert calls["n"] == 3  # failed twice, succeeded on the third


@pytest.mark.asyncio
async def test_retry_raises_after_exhausting_attempts():
    async def always_fails():
        raise TransientToolError("still down")

    with pytest.raises(TransientToolError):
        await retry_async(lambda: always_fails(), attempts=2, base_delay=0.0)


@pytest.mark.asyncio
async def test_retry_does_not_retry_non_transient():
    calls = {"n": 0}

    async def bad_request():
        calls["n"] += 1
        raise ValueError("400 bad request")  # a real client error — not retryable

    with pytest.raises(ValueError):
        await retry_async(lambda: bad_request(), attempts=3, base_delay=0.0)
    assert calls["n"] == 1  # tried once, gave up immediately
