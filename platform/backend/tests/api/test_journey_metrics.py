"""API test for the reference cost/latency dashboard endpoint."""

from __future__ import annotations

import pytest
from httpx import AsyncClient

pytestmark = pytest.mark.asyncio


async def test_reference_metrics_endpoint(client: AsyncClient):
    resp = await client.get("/api/v1/journey/reference/metrics")
    assert resp.status_code == 200
    body = resp.json()
    assert body["totals"]["runs"] == 7
    assert body["pricing_model"]  # a reference model is applied by default
    personas = {p["persona"] for p in body["personas"]}
    assert {"ba", "architect", "developer", "qa", "lead", "ciso"} <= personas
    developer = next(p for p in body["personas"] if p["persona"] == "developer")
    assert developer["runs"] == 2 and developer["cost_usd"] > 0


async def test_reference_metrics_respects_model_override(client: AsyncClient):
    resp = await client.get("/api/v1/journey/reference/metrics?model=claude-haiku-4-5-20251001")
    assert resp.status_code == 200
    assert resp.json()["pricing_model"] == "claude-haiku-4-5-20251001"
