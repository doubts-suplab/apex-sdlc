from __future__ import annotations

import pytest
from httpx import AsyncClient


async def _create_org(client: AsyncClient, slug: str) -> str:
    org = await client.post(
        "/api/v1/organisations/", json={"name": f"Org {slug}", "slug": slug}
    )
    assert org.status_code == 201, org.text
    return str(org.json()["id"])


async def _create_project(client: AsyncClient, org_id: str, slug: str) -> str:
    proj = await client.post(
        "/api/v1/projects/",
        json={"organisation_id": org_id, "name": f"Proj {slug}", "slug": slug},
    )
    assert proj.status_code == 201, proj.text
    return str(proj.json()["id"])


async def _add_delivery(client: AsyncClient, project_id: str, **body: object) -> None:
    resp = await client.post(f"/api/v1/projects/{project_id}/deliveries/", json=body)
    assert resp.status_code == 201, resp.text


@pytest.mark.asyncio
async def test_portfolio_empty_org_is_zeroed(client: AsyncClient) -> None:
    org_id = await _create_org(client, "empty-org")
    resp = await client.get(f"/api/v1/organisations/{org_id}/portfolio")
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["project_count"] == 0
    assert body["delivery_count"] == 0
    assert body["open_count"] == 0
    assert body["total_estimate_points"] == 0
    # status/priority maps are zero-filled, not absent
    assert body["by_status"]["proposed"] == 0
    assert body["by_priority"]["high"] == 0
    assert body["projects"] == []


@pytest.mark.asyncio
async def test_portfolio_aggregates_across_projects(client: AsyncClient) -> None:
    org_id = await _create_org(client, "roll-org")
    p1 = await _create_project(client, org_id, "alpha")
    p2 = await _create_project(client, org_id, "beta")

    await _add_delivery(client, p1, title="A1", status="proposed", priority="high", estimate_points=3)
    await _add_delivery(client, p1, title="A2", status="planned", priority="medium", estimate_points=5)
    await _add_delivery(client, p2, title="B1", status="done", priority="low", estimate_points=8)
    await _add_delivery(client, p2, title="B2", status="proposed", priority="high")  # unsized

    resp = await client.get(f"/api/v1/organisations/{org_id}/portfolio")
    assert resp.status_code == 200, resp.text
    body = resp.json()

    assert body["project_count"] == 2
    assert body["delivery_count"] == 4
    # open = proposed + planned + in_progress (3 open, B1 is done)
    assert body["open_count"] == 3
    assert body["total_estimate_points"] == 16  # 3 + 5 + 8 + 0
    assert body["by_status"]["proposed"] == 2
    assert body["by_status"]["planned"] == 1
    assert body["by_status"]["done"] == 1
    assert body["by_priority"]["high"] == 2
    assert body["by_priority"]["medium"] == 1
    assert body["by_priority"]["low"] == 1

    rows = {row["slug"]: row for row in body["projects"]}
    assert rows["alpha"]["delivery_count"] == 2
    assert rows["alpha"]["estimate_points"] == 8
    assert rows["alpha"]["open_count"] == 2
    assert rows["beta"]["delivery_count"] == 2
    assert rows["beta"]["estimate_points"] == 8
    assert rows["beta"]["open_count"] == 1  # only B2 is open


@pytest.mark.asyncio
async def test_portfolio_is_scoped_to_org(client: AsyncClient) -> None:
    org_a = await _create_org(client, "scope-a")
    org_b = await _create_org(client, "scope-b")
    pa = await _create_project(client, org_a, "a-proj")
    pb = await _create_project(client, org_b, "b-proj")
    await _add_delivery(client, pa, title="A", estimate_points=2)
    await _add_delivery(client, pb, title="B", estimate_points=99)

    resp = await client.get(f"/api/v1/organisations/{org_a}/portfolio")
    body = resp.json()
    assert body["delivery_count"] == 1
    assert body["total_estimate_points"] == 2  # org B's delivery never leaks in
    assert [row["slug"] for row in body["projects"]] == ["a-proj"]


@pytest.mark.asyncio
async def test_portfolio_includes_projects_without_deliveries(client: AsyncClient) -> None:
    org_id = await _create_org(client, "sparse-org")
    await _create_project(client, org_id, "no-deliveries")
    resp = await client.get(f"/api/v1/organisations/{org_id}/portfolio")
    body = resp.json()
    assert body["project_count"] == 1
    assert body["projects"][0]["slug"] == "no-deliveries"
    assert body["projects"][0]["delivery_count"] == 0


@pytest.mark.asyncio
async def test_portfolio_unknown_org_is_problem_detail(client: AsyncClient) -> None:
    resp = await client.get(
        "/api/v1/organisations/00000000-0000-0000-0000-000000000000/portfolio"
    )
    assert resp.status_code == 404
    body = resp.json()
    assert body["status"] == 404
    assert "type" in body  # RFC 7807
