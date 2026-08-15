from __future__ import annotations

import pytest
from httpx import AsyncClient


async def _create_project(client: AsyncClient) -> str:
    """Create an org + project and return the project id."""
    org = await client.post(
        "/api/v1/organisations/", json={"name": "Del Org", "slug": "del-org"}
    )
    assert org.status_code == 201, org.text
    org_id = org.json()["id"]
    proj = await client.post(
        "/api/v1/projects/",
        json={"organisation_id": org_id, "name": "Del Svc", "slug": "del-svc"},
    )
    assert proj.status_code == 201, proj.text
    return str(proj.json()["id"])


@pytest.mark.asyncio
async def test_create_delivery(client: AsyncClient) -> None:
    project_id = await _create_project(client)
    resp = await client.post(
        f"/api/v1/projects/{project_id}/deliveries/",
        json={"title": "Ship export API", "priority": "high", "estimate_points": 5},
    )
    assert resp.status_code == 201, resp.text
    body = resp.json()
    assert body["title"] == "Ship export API"
    assert body["priority"] == "high"
    assert body["estimate_points"] == 5
    assert body["status"] == "proposed"   # default
    assert body["source"] == "human"      # default
    assert body["project_id"] == project_id
    assert "id" in body


@pytest.mark.asyncio
async def test_list_deliveries_scoped_to_project(client: AsyncClient) -> None:
    project_id = await _create_project(client)
    for title in ("A", "B"):
        await client.post(
            f"/api/v1/projects/{project_id}/deliveries/", json={"title": title}
        )
    resp = await client.get(f"/api/v1/projects/{project_id}/deliveries/")
    assert resp.status_code == 200
    body = resp.json()
    assert body["total"] == 2
    assert {d["title"] for d in body["items"]} == {"A", "B"}


@pytest.mark.asyncio
async def test_list_deliveries_filter_by_status(client: AsyncClient) -> None:
    project_id = await _create_project(client)
    await client.post(
        f"/api/v1/projects/{project_id}/deliveries/",
        json={"title": "planned one", "status": "planned"},
    )
    await client.post(
        f"/api/v1/projects/{project_id}/deliveries/", json={"title": "proposed one"}
    )
    resp = await client.get(
        f"/api/v1/projects/{project_id}/deliveries/", params={"status": "planned"}
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["total"] == 1
    assert body["items"][0]["title"] == "planned one"


@pytest.mark.asyncio
async def test_get_update_delete_delivery(client: AsyncClient) -> None:
    project_id = await _create_project(client)
    created = await client.post(
        f"/api/v1/projects/{project_id}/deliveries/", json={"title": "iterate"}
    )
    delivery_id = created.json()["id"]

    got = await client.get(f"/api/v1/projects/{project_id}/deliveries/{delivery_id}")
    assert got.status_code == 200

    patched = await client.patch(
        f"/api/v1/projects/{project_id}/deliveries/{delivery_id}",
        json={"status": "in_progress", "estimate_points": 8},
    )
    assert patched.status_code == 200
    assert patched.json()["status"] == "in_progress"
    assert patched.json()["estimate_points"] == 8

    deleted = await client.delete(
        f"/api/v1/projects/{project_id}/deliveries/{delivery_id}"
    )
    assert deleted.status_code == 204
    gone = await client.get(f"/api/v1/projects/{project_id}/deliveries/{delivery_id}")
    assert gone.status_code == 404


@pytest.mark.asyncio
async def test_create_delivery_unknown_project_is_problem_detail(client: AsyncClient) -> None:
    resp = await client.post(
        "/api/v1/projects/00000000-0000-0000-0000-000000000000/deliveries/",
        json={"title": "orphan"},
    )
    assert resp.status_code == 404
    body = resp.json()
    assert body["status"] == 404
    assert "type" in body  # RFC 7807


@pytest.mark.asyncio
async def test_get_unknown_delivery_is_404(client: AsyncClient) -> None:
    project_id = await _create_project(client)
    resp = await client.get(
        f"/api/v1/projects/{project_id}/deliveries/00000000-0000-0000-0000-000000000000"
    )
    assert resp.status_code == 404
