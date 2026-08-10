"""Members + Teams API and token→Member enforcement tests.

Closes the identity tails of Increments 8/16/17: teams/members CRUD, and opt-in project-membership
enforcement (MEMBERSHIP_REQUIRED) that binds a token subject to a real Member at request time.
"""

from __future__ import annotations

import uuid
from pathlib import Path

import pytest
import yaml
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import create_access_token
from app.models.organisation import Organisation
from app.models.project import Project

pytestmark = pytest.mark.asyncio

_MANIFEST_EXAMPLE = (
    Path(__file__).resolve().parents[1].parent
    / "app"
    / "onboarding"
    / "eeik_assets"
    / "examples"
    / "greenfield-java-aws.yaml"
)


def _auth(persona: str, subject: str | None = None) -> dict[str, str]:
    sub = subject or f"{persona}-user"
    return {"Authorization": f"Bearer {create_access_token(subject=sub, persona=persona)}"}


async def _make_org_project(db: AsyncSession) -> tuple[Organisation, Project]:
    org = Organisation(name=f"Org {uuid.uuid4().hex[:8]}", slug=f"org-{uuid.uuid4().hex[:8]}")
    db.add(org)
    await db.flush()
    project = Project(organisation_id=org.id, name="Refund Service", slug="refund-service")
    db.add(project)
    await db.flush()
    return org, project


async def test_create_and_list_team(client: AsyncClient, db_session: AsyncSession):
    org, _ = await _make_org_project(db_session)
    resp = await client.post(
        f"/api/v1/organisations/{org.id}/teams",
        headers=_auth("lead"),
        json={"name": "Payments", "slug": "payments"},
    )
    assert resp.status_code == 200
    assert resp.json()["slug"] == "payments"

    listed = await client.get(f"/api/v1/organisations/{org.id}/teams")
    assert listed.json()["total"] == 1


async def test_add_and_list_member(client: AsyncClient, db_session: AsyncSession):
    _, project = await _make_org_project(db_session)
    resp = await client.post(
        f"/api/v1/projects/{project.id}/members",
        headers=_auth("lead"),
        json={"subject": "alice", "persona": "ba", "display_name": "Alice"},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["subject"] == "alice"
    assert body["persona"] == "ba"

    listed = await client.get(f"/api/v1/projects/{project.id}/members")
    assert listed.json()["total"] == 1


async def test_member_writes_require_admin_persona(client: AsyncClient, db_session: AsyncSession):
    _, project = await _make_org_project(db_session)
    resp = await client.post(
        f"/api/v1/projects/{project.id}/members",
        headers=_auth("developer"),  # not lead/ciso
        json={"subject": "bob", "persona": "developer"},
    )
    assert resp.status_code == 403


async def test_membership_not_enforced_by_default(client: AsyncClient, db_session: AsyncSession):
    """With MEMBERSHIP_REQUIRED off (default), a non-member approver may still approve."""
    _, project = await _make_org_project(db_session)
    resp = await client.post(
        f"/api/v1/projects/{project.id}/phases/requirements/approve", headers=_auth("lead")
    )
    assert resp.status_code == 200


async def test_membership_enforced_when_flag_on(
    client: AsyncClient, db_session: AsyncSession, monkeypatch: pytest.MonkeyPatch
):
    monkeypatch.setenv("MEMBERSHIP_REQUIRED", "true")
    _, project = await _make_org_project(db_session)

    # A lead who is NOT a project member is rejected.
    denied = await client.post(
        f"/api/v1/projects/{project.id}/phases/requirements/approve",
        headers=_auth("lead", subject="outsider"),
    )
    assert denied.status_code == 403
    assert denied.json()["detail"]["title"] == "Not a Project Member"

    # Add that subject as a member, then the same call succeeds.
    await client.post(
        f"/api/v1/projects/{project.id}/members",
        headers=_auth("lead", subject="admin"),
        json={"subject": "outsider", "persona": "lead"},
    )
    allowed = await client.post(
        f"/api/v1/projects/{project.id}/phases/requirements/approve",
        headers=_auth("lead", subject="outsider"),
    )
    assert allowed.status_code == 200


async def test_onboarding_seeds_default_team(client: AsyncClient, db_session: AsyncSession):
    org, _ = await _make_org_project(db_session)
    manifest = yaml.safe_load(_MANIFEST_EXAMPLE.read_text())
    resp = await client.post(
        f"/api/v1/onboarding/?organisation_id={org.id}", json=manifest
    )
    assert resp.status_code == 200
    body = resp.json()
    assert "default_team_id" in body

    teams = await client.get(f"/api/v1/organisations/{org.id}/teams")
    assert any(t["slug"] == "core" for t in teams.json()["items"])
