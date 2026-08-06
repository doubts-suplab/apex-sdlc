"""Global auth middleware — opt-in enforcement with an allowlist.

Builds a fresh app with ``AUTH_REQUIRED=true`` (the shared ``client`` fixture runs with it off, proving
the default stays open) and checks that non-allowlisted routes demand a token while health/login don't.
"""

from __future__ import annotations

import pytest
from httpx import ASGITransport, AsyncClient

from app.core.security import create_access_token
from app.main import create_app

pytestmark = pytest.mark.asyncio

_PROTECTED = "/api/v1/journey/reference/metrics"


async def _authed_app(monkeypatch) -> AsyncClient:
    monkeypatch.setenv("AUTH_REQUIRED", "true")
    transport = ASGITransport(app=create_app())  # type: ignore[arg-type]
    return AsyncClient(transport=transport, base_url="http://test")


async def test_default_off_leaves_routes_open(client: AsyncClient):
    # The shared fixture app has AUTH_REQUIRED unset → the protected route is reachable anonymously.
    assert (await client.get(_PROTECTED)).status_code == 200


async def test_enforced_requires_a_token(monkeypatch):
    async with await _authed_app(monkeypatch) as ac:
        anon = await ac.get(_PROTECTED)
        assert anon.status_code == 401 and anon.json()["status"] == 401

        token = create_access_token(subject="u", persona="lead")
        ok = await ac.get(_PROTECTED, headers={"Authorization": f"Bearer {token}"})
        assert ok.status_code == 200


async def test_enforced_rejects_a_bad_token(monkeypatch):
    async with await _authed_app(monkeypatch) as ac:
        bad = await ac.get(_PROTECTED, headers={"Authorization": "Bearer not-a-jwt"})
        assert bad.status_code == 401


async def test_allowlist_stays_open_when_enforced(monkeypatch):
    async with await _authed_app(monkeypatch) as ac:
        # Health + the login endpoint must work without a token even under enforcement.
        assert (await ac.get("/api/v1/health")).status_code == 200
        login = await ac.post("/api/v1/auth/token", json={"subject": "u", "persona": "lead"})
        assert login.status_code == 200
