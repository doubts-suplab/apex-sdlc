from __future__ import annotations

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_create_organisation(client: AsyncClient) -> None:
    """POST /api/v1/organisations returns 201 with created entity."""
    payload = {
        "name": "Acme Corporation",
        "slug": "acme-corporation",
        "description": "Global leader in dynamite.",
    }
    response = await client.post("/api/v1/organisations/", json=payload)
    assert response.status_code == 201
    body = response.json()
    assert body["name"] == "Acme Corporation"
    assert body["slug"] == "acme-corporation"
    assert "id" in body
    assert "created_at" in body
    assert "updated_at" in body


@pytest.mark.asyncio
async def test_create_organisation_duplicate_slug(client: AsyncClient) -> None:
    """Creating two orgs with the same slug must result in a DB error (409 or 500)."""
    payload = {"name": "Dupe One", "slug": "dupe-slug"}
    await client.post("/api/v1/organisations/", json=payload)
    response2 = await client.post(
        "/api/v1/organisations/", json={"name": "Dupe Two", "slug": "dupe-slug"}
    )
    assert response2.status_code in (409, 422, 500)


@pytest.mark.asyncio
async def test_list_organisations(client: AsyncClient) -> None:
    """GET /api/v1/organisations returns paginated list."""
    await client.post(
        "/api/v1/organisations/",
        json={"name": "List Org A", "slug": "list-org-a"},
    )
    response = await client.get("/api/v1/organisations/")
    assert response.status_code == 200
    body = response.json()
    assert "items" in body
    assert "total" in body
    assert "limit" in body
    assert isinstance(body["items"], list)


@pytest.mark.asyncio
async def test_get_organisation_by_id(client: AsyncClient) -> None:
    """GET /api/v1/organisations/{id} returns the correct org."""
    create_resp = await client.post(
        "/api/v1/organisations/",
        json={"name": "Fetch Me Org", "slug": "fetch-me-org"},
    )
    assert create_resp.status_code == 201
    org_id = create_resp.json()["id"]

    response = await client.get(f"/api/v1/organisations/{org_id}")
    assert response.status_code == 200
    assert response.json()["id"] == org_id


@pytest.mark.asyncio
async def test_get_organisation_not_found(client: AsyncClient) -> None:
    """GET /api/v1/organisations/{nonexistent} returns 404."""
    response = await client.get(
        "/api/v1/organisations/00000000-0000-0000-0000-000000000000"
    )
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_update_organisation(client: AsyncClient) -> None:
    """PATCH /api/v1/organisations/{id} applies partial update."""
    create_resp = await client.post(
        "/api/v1/organisations/",
        json={"name": "Update Target", "slug": "update-target"},
    )
    org_id = create_resp.json()["id"]

    response = await client.patch(
        f"/api/v1/organisations/{org_id}",
        json={"description": "New description"},
    )
    assert response.status_code == 200
    assert response.json()["description"] == "New description"


@pytest.mark.asyncio
async def test_delete_organisation(client: AsyncClient) -> None:
    """DELETE /api/v1/organisations/{id} removes the entity."""
    create_resp = await client.post(
        "/api/v1/organisations/",
        json={"name": "Delete Me", "slug": "delete-me"},
    )
    org_id = create_resp.json()["id"]

    delete_resp = await client.delete(f"/api/v1/organisations/{org_id}")
    assert delete_resp.status_code == 204

    get_resp = await client.get(f"/api/v1/organisations/{org_id}")
    assert get_resp.status_code == 404
