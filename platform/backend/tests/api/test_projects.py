from __future__ import annotations

import pytest
from httpx import AsyncClient


async def _create_org(client: AsyncClient, name: str, slug: str) -> str:
    """Helper to create an organisation and return its id."""
    resp = await client.post(
        "/api/v1/organisations/",
        json={"name": name, "slug": slug},
    )
    assert resp.status_code == 201, resp.text
    return str(resp.json()["id"])  # type: ignore[return-value]


@pytest.mark.asyncio
async def test_create_project(client: AsyncClient) -> None:
    """POST /api/v1/projects returns 201 with created entity."""
    org_id = await _create_org(client, "Proj Org", "proj-org")
    payload = {
        "organisation_id": org_id,
        "name": "My Service",
        "slug": "my-service",
        "project_type": "spring-boot",
    }
    response = await client.post("/api/v1/projects/", json=payload)
    assert response.status_code == 201
    body = response.json()
    assert body["name"] == "My Service"
    assert body["slug"] == "my-service"
    assert body["organisation_id"] == org_id
    assert body["project_type"] == "spring-boot"
    assert body["status"] == "active"
    assert body["current_phase"] == "requirements"
    assert "id" in body


@pytest.mark.asyncio
async def test_list_projects(client: AsyncClient) -> None:
    """GET /api/v1/projects returns paginated list."""
    org_id = await _create_org(client, "List Proj Org", "list-proj-org")
    await client.post(
        "/api/v1/projects/",
        json={"organisation_id": org_id, "name": "Proj A", "slug": "proj-a"},
    )
    response = await client.get("/api/v1/projects/")
    assert response.status_code == 200
    body = response.json()
    assert "items" in body
    assert "total" in body
    assert isinstance(body["items"], list)


@pytest.mark.asyncio
async def test_list_projects_filter_by_org(client: AsyncClient) -> None:
    """GET /api/v1/projects?organisation_id=X filters correctly."""
    org_id = await _create_org(client, "Filter Org", "filter-org")
    await client.post(
        "/api/v1/projects/",
        json={"organisation_id": org_id, "name": "Filtered Proj", "slug": "filtered-proj"},
    )
    response = await client.get(f"/api/v1/projects/?organisation_id={org_id}")
    assert response.status_code == 200
    items = response.json()["items"]
    assert all(p["organisation_id"] == org_id for p in items)


@pytest.mark.asyncio
async def test_get_project_by_id(client: AsyncClient) -> None:
    """GET /api/v1/projects/{id} returns the correct project."""
    org_id = await _create_org(client, "Get Proj Org", "get-proj-org")
    create_resp = await client.post(
        "/api/v1/projects/",
        json={"organisation_id": org_id, "name": "Get Me", "slug": "get-me"},
    )
    project_id = create_resp.json()["id"]

    response = await client.get(f"/api/v1/projects/{project_id}")
    assert response.status_code == 200
    assert response.json()["id"] == project_id


@pytest.mark.asyncio
async def test_get_project_not_found(client: AsyncClient) -> None:
    """GET /api/v1/projects/{nonexistent} returns 404."""
    response = await client.get("/api/v1/projects/00000000-0000-0000-0000-000000000000")
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_update_project(client: AsyncClient) -> None:
    """PATCH /api/v1/projects/{id} applies partial update."""
    org_id = await _create_org(client, "Update Proj Org", "update-proj-org")
    create_resp = await client.post(
        "/api/v1/projects/",
        json={"organisation_id": org_id, "name": "Update Target", "slug": "update-target-proj"},
    )
    project_id = create_resp.json()["id"]

    response = await client.patch(
        f"/api/v1/projects/{project_id}",
        json={"status": "paused", "current_phase": "architecture"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "paused"
    assert body["current_phase"] == "architecture"


@pytest.mark.asyncio
async def test_delete_project(client: AsyncClient) -> None:
    """DELETE /api/v1/projects/{id} removes the entity."""
    org_id = await _create_org(client, "Del Proj Org", "del-proj-org")
    create_resp = await client.post(
        "/api/v1/projects/",
        json={"organisation_id": org_id, "name": "Delete Me", "slug": "delete-me-proj"},
    )
    project_id = create_resp.json()["id"]

    delete_resp = await client.delete(f"/api/v1/projects/{project_id}")
    assert delete_resp.status_code == 204

    get_resp = await client.get(f"/api/v1/projects/{project_id}")
    assert get_resp.status_code == 404
