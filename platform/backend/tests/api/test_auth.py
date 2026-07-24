"""Auth + RBAC tests — token issue/verify, persona guarding, and the protected journey-persist write."""

from __future__ import annotations

import time
import uuid

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import (
    InvalidTokenError,
    create_access_token,
    decode_access_token,
)
from app.models.organisation import Organisation
from app.models.project import Project

pytestmark = pytest.mark.asyncio


# -- token unit (no HTTP) -----------------------------------------------------------------------
def test_token_round_trips_claims():
    token = create_access_token(subject="u1", persona="lead", organisation_id="org-9")
    claims = decode_access_token(token)
    assert claims["sub"] == "u1"
    assert claims["persona"] == "lead"
    assert claims["org_id"] == "org-9"
    assert claims["exp"] > claims["iat"]


def test_tampered_signature_is_rejected():
    token = create_access_token(subject="u1", persona="lead")
    header, payload, _sig = token.split(".")
    forged = f"{header}.{payload}.{'A' * 43}"
    with pytest.raises(InvalidTokenError):
        decode_access_token(forged)


def test_expired_token_is_rejected():
    token = create_access_token(subject="u1", persona="lead", expires_in=-1)
    with pytest.raises(InvalidTokenError):
        decode_access_token(token)


def test_malformed_token_is_rejected():
    with pytest.raises(InvalidTokenError):
        decode_access_token("not-a-jwt")


def test_unknown_persona_cannot_be_minted():
    with pytest.raises(ValueError):
        create_access_token(subject="u1", persona="wizard")


# -- token endpoint -----------------------------------------------------------------------------
async def test_issue_token_and_read_me(client: AsyncClient):
    resp = await client.post("/api/v1/auth/token", json={"subject": "ba-user", "persona": "ba"})
    assert resp.status_code == 200
    body = resp.json()
    assert body["token_type"] == "bearer" and body["persona"] == "ba"

    me = await client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {body['access_token']}"})
    assert me.status_code == 200
    assert me.json()["persona"] == "ba"


async def test_issue_token_rejects_unknown_persona(client: AsyncClient):
    resp = await client.post("/api/v1/auth/token", json={"subject": "x", "persona": "wizard"})
    assert resp.status_code == 422


async def test_me_requires_a_token(client: AsyncClient):
    resp = await client.get("/api/v1/auth/me")
    assert resp.status_code == 401
    assert resp.json()["detail"]["status"] == 401  # RFC 7807 problem detail (under `detail`)


# -- RBAC on the protected write ----------------------------------------------------------------
async def _make_project(db: AsyncSession) -> Project:
    org = Organisation(name=f"Org {uuid.uuid4().hex[:8]}", slug=f"org-{uuid.uuid4().hex[:8]}")
    db.add(org)
    await db.flush()
    project = Project(organisation_id=org.id, name="Refund Service", slug="refund-service")
    db.add(project)
    await db.flush()
    return project


async def test_persist_rejects_anonymous(client: AsyncClient, db_session: AsyncSession):
    project = await _make_project(db_session)
    resp = await client.post(f"/api/v1/projects/{project.id}/journey/persist")
    assert resp.status_code == 401


async def test_persist_forbids_non_approver_persona(client: AsyncClient, db_session: AsyncSession):
    project = await _make_project(db_session)
    token = create_access_token(subject="dev-user", persona="developer")  # not an approver
    resp = await client.post(
        f"/api/v1/projects/{project.id}/journey/persist",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 403
    assert resp.json()["detail"]["status"] == 403


async def test_persist_allows_approver_persona(client: AsyncClient, db_session: AsyncSession):
    project = await _make_project(db_session)
    token = create_access_token(subject="lead-user", persona="lead")
    resp = await client.post(
        f"/api/v1/projects/{project.id}/journey/persist",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
    assert resp.json()["artifacts"] == 17
