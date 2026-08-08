"""API tests for the configurable-spine query param on the journey endpoints."""

from __future__ import annotations

import pytest
from httpx import AsyncClient

pytestmark = pytest.mark.asyncio


async def test_reference_journey_runs_a_phase_subset(client: AsyncClient):
    resp = await client.get("/api/v1/journey/reference?phases=requirements,development")
    assert resp.status_code == 200
    body = resp.json()
    assert [p["phase"] for p in body["phases"]] == ["requirements", "development"]
    assert body["stats"]["phase_count"] == 2


async def test_reference_journey_full_when_no_phases(client: AsyncClient):
    resp = await client.get("/api/v1/journey/reference")
    assert resp.status_code == 200
    assert resp.json()["stats"]["phase_count"] == 7


async def test_reference_journey_invalid_phase_is_400(client: AsyncClient):
    resp = await client.get("/api/v1/journey/reference?phases=requirements,bogus")
    assert resp.status_code == 400
    problem = resp.json()["detail"]  # RFC-7807 problem detail (under `detail`, like the auth 401/403)
    assert problem["status"] == 400
    assert "bogus" in problem["detail"]


async def test_reference_gates_respect_the_spine_subset(client: AsyncClient):
    resp = await client.get("/api/v1/journey/reference/gates?phases=requirements,architecture")
    assert resp.status_code == 200
    body = resp.json()
    assert body["phases"] == ["requirements", "architecture"]
    assert [g["phase"] for g in body["gates"]] == ["requirements", "architecture"]
    # Both are SUGGEST specs → the spine blocks at the first, unapproved.
    assert body["blocking_phase"] == "requirements"
