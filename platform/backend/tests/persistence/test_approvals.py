"""Durable, identity-bound gate approval tests.

A phase approval is now stored (who/when/decision), bound to the project Member when the JWT subject
maps to one, and drives the gate on the next journey persist — replacing the ephemeral ?approved= param.
DB-backed via the shared aiosqlite fixtures.
"""

from __future__ import annotations

import uuid

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import create_access_token
from app.models.organisation import Organisation
from app.models.project import Project
from app.models.team import Member
from app.services.persistence_service import PersistenceService

pytestmark = pytest.mark.asyncio


def _auth(persona: str, subject: str | None = None) -> dict[str, str]:
    sub = subject or f"{persona}-user"
    return {"Authorization": f"Bearer {create_access_token(subject=sub, persona=persona)}"}


async def _make_project(db: AsyncSession) -> Project:
    org = Organisation(name=f"Org {uuid.uuid4().hex[:8]}", slug=f"org-{uuid.uuid4().hex[:8]}")
    db.add(org)
    await db.flush()
    project = Project(organisation_id=org.id, name="Refund Service", slug="refund-service")
    db.add(project)
    await db.flush()
    return project


# -- service layer ------------------------------------------------------------------------------
async def test_record_approval_binds_to_member_when_present(db_session: AsyncSession):
    project = await _make_project(db_session)
    db_session.add(
        Member(project_id=project.id, subject="lead-user", persona="lead", display_name="Lead")
    )
    await db_session.flush()
    svc = PersistenceService(db_session)

    approval = await svc.record_approval(
        project.id, "requirements", approver_subject="lead-user", approver_persona="lead"
    )
    assert approval.member_id is not None
    assert approval.decision == "approved"
    assert await svc.approved_phases(project.id) == {"requirements"}


async def test_record_approval_without_member_leaves_binding_null(db_session: AsyncSession):
    project = await _make_project(db_session)
    svc = PersistenceService(db_session)
    approval = await svc.record_approval(
        project.id, "architecture", approver_subject="nobody", approver_persona="architect"
    )
    assert approval.member_id is None
    assert await svc.approved_phases(project.id) == {"architecture"}


async def test_latest_decision_wins_reject_withdraws(db_session: AsyncSession):
    project = await _make_project(db_session)
    svc = PersistenceService(db_session)
    await svc.record_approval(project.id, "requirements", "lead-user", "lead")
    assert await svc.approved_phases(project.id) == {"requirements"}
    await svc.record_approval(project.id, "requirements", "lead-user", "lead", decision="rejected")
    assert await svc.approved_phases(project.id) == set()


# -- API ------------------------------------------------------------------------------------------
async def test_approve_endpoint_persists_and_is_attributable(
    client: AsyncClient, db_session: AsyncSession
):
    project = await _make_project(db_session)
    db_session.add(
        Member(project_id=project.id, subject="lead-user", persona="lead", display_name="Lead")
    )
    await db_session.flush()
    pid = str(project.id)

    resp = await client.post(
        f"/api/v1/projects/{pid}/phases/requirements/approve",
        headers=_auth("lead"),
        json={"note": "signed off"},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["phase"] == "requirements"
    assert body["decision"] == "approved"
    assert body["approver_persona"] == "lead"
    assert body["member_bound"] is True

    listed = await client.get(f"/api/v1/projects/{pid}/approvals")
    assert listed.status_code == 200
    data = listed.json()
    assert data["approved_phases"] == ["requirements"]
    assert data["total"] == 1


async def test_approve_requires_approver_persona(client: AsyncClient, db_session: AsyncSession):
    project = await _make_project(db_session)
    resp = await client.post(
        f"/api/v1/projects/{project.id}/phases/requirements/approve",
        headers=_auth("developer"),  # not an approver persona
    )
    assert resp.status_code == 403


async def test_approve_unknown_phase_404(client: AsyncClient, db_session: AsyncSession):
    project = await _make_project(db_session)
    resp = await client.post(
        f"/api/v1/projects/{project.id}/phases/nope/approve", headers=_auth("lead")
    )
    assert resp.status_code == 404
    assert "nope" in resp.json()["detail"]


async def test_stored_approval_unblocks_the_spine_on_persist(
    client: AsyncClient, db_session: AsyncSession
):
    project = await _make_project(db_session)
    pid = str(project.id)

    # With no approvals, the spine blocks at the first SUGGEST phase (requirements).
    first = await client.post(f"/api/v1/projects/{pid}/journey/persist", headers=_auth("lead"))
    assert first.status_code == 200
    assert first.json()["blocking_phase"] == "requirements"

    # Durably approve requirements, then re-persist WITHOUT the ?approved= param — the stored
    # approval is authoritative, so the spine advances past requirements.
    approve = await client.post(
        f"/api/v1/projects/{pid}/phases/requirements/approve", headers=_auth("lead")
    )
    assert approve.status_code == 200
    second = await client.post(f"/api/v1/projects/{pid}/journey/persist", headers=_auth("lead"))
    assert second.status_code == 200
    assert second.json()["blocking_phase"] != "requirements"
