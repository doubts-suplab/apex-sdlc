"""ARB approval-workflow tests — submit / decide / append-only audit (closes 14/4 tail)."""

from __future__ import annotations

import uuid

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import create_access_token
from app.models.organisation import Organisation
from app.models.project import Project
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


async def _submit(client: AsyncClient, pid: str, persona: str = "architect") -> str:
    resp = await client.post(
        f"/api/v1/projects/{pid}/arb",
        headers=_auth(persona),
        json={"title": "Refund service target architecture", "summary": "C4 + risk assessment"},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "pending"
    return body["id"]


async def test_submit_creates_pending(client: AsyncClient, db_session: AsyncSession) -> None:
    project = await _make_project(db_session)
    arb_id = await _submit(client, str(project.id))
    listed = await client.get(f"/api/v1/projects/{project.id}/arb")
    assert listed.json()["total"] == 1
    assert listed.json()["items"][0]["id"] == arb_id


async def test_submit_requires_submit_persona(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    project = await _make_project(db_session)
    resp = await client.post(
        f"/api/v1/projects/{project.id}/arb",
        headers=_auth("developer"),  # not architect/lead
        json={"title": "x"},
    )
    assert resp.status_code == 403


async def test_approve_sets_status_and_writes_audit(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    project = await _make_project(db_session)
    arb_id = await _submit(client, str(project.id))

    resp = await client.post(
        f"/api/v1/projects/{project.id}/arb/{arb_id}/decision",
        headers=_auth("ciso"),
        json={"decision": "approve", "rationale": "meets standards"},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "approved"
    assert body["reviewed_by"] == "ciso-user"
    assert body["decision_rationale"] == "meets standards"

    # The decision is recorded append-only in the audit log.
    audit = await PersistenceService(db_session).list_audit_log(project.id)
    arb_rows = [a for a in audit if a.agent_name == "arb"]
    assert len(arb_rows) == 1
    assert arb_rows[0].action == "arb-approved"
    assert arb_rows[0].actor == "ciso-user"


async def test_reject_and_request_changes(client: AsyncClient, db_session: AsyncSession) -> None:
    project = await _make_project(db_session)
    a1 = await _submit(client, str(project.id))
    r1 = await client.post(
        f"/api/v1/projects/{project.id}/arb/{a1}/decision",
        headers=_auth("lead"),
        json={"decision": "reject", "rationale": "no rollback plan"},
    )
    assert r1.json()["status"] == "rejected"

    a2 = await _submit(client, str(project.id))
    r2 = await client.post(
        f"/api/v1/projects/{project.id}/arb/{a2}/decision",
        headers=_auth("lead"),
        json={"decision": "request_changes", "rationale": "tighten the data model"},
    )
    assert r2.json()["status"] == "changes_requested"


async def test_decision_requires_board_persona(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    project = await _make_project(db_session)
    arb_id = await _submit(client, str(project.id))
    resp = await client.post(
        f"/api/v1/projects/{project.id}/arb/{arb_id}/decision",
        headers=_auth("ba"),  # BA is not on the board
        json={"decision": "approve"},
    )
    assert resp.status_code == 403


async def test_decision_unknown_arb_404(client: AsyncClient, db_session: AsyncSession) -> None:
    project = await _make_project(db_session)
    missing = uuid.uuid4()
    resp = await client.post(
        f"/api/v1/projects/{project.id}/arb/{missing}/decision",
        headers=_auth("ciso"),
        json={"decision": "approve"},
    )
    assert resp.status_code == 404
