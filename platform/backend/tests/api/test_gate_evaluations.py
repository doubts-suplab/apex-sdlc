"""Persisted phase-gate evaluations (ROADMAP Phase 5 — DB persistence of gate evaluations)."""

from __future__ import annotations

import uuid

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import create_access_token
from app.models.organisation import Organisation
from app.models.project import Project

pytestmark = pytest.mark.asyncio


def _approver() -> dict[str, str]:
    return {"Authorization": f"Bearer {create_access_token(subject='lead-user', persona='lead')}"}


def _non_approver() -> dict[str, str]:
    return {"Authorization": f"Bearer {create_access_token(subject='dev-user', persona='developer')}"}


async def _make_project(db: AsyncSession) -> Project:
    org = Organisation(name=f"Org {uuid.uuid4().hex[:8]}", slug=f"org-{uuid.uuid4().hex[:8]}")
    db.add(org)
    await db.flush()
    project = Project(organisation_id=org.id, name="Refund Service", slug="refund-service")
    db.add(project)
    await db.flush()
    return project


async def test_persist_and_list_gate_evaluation(client: AsyncClient, db_session: AsyncSession):
    project = await _make_project(db_session)
    pid = str(project.id)

    # A requirements gate with its required artifacts present + spec approved → passed.
    resp = await client.post(
        f"/api/v1/projects/{pid}/phases/requirements/gate/evaluations",
        headers=_approver(),
        json={"produced_artifacts": ["user-stories", "acceptance-criteria"],
              "auto_enforced": False, "approved": True, "bypass_total": 0},
    )
    assert resp.status_code == 201, resp.text
    body = resp.json()
    assert body["phase"] == "requirements"
    assert body["status"] in ("passed", "pending", "failed")
    assert body["evaluated_by"] == "lead-user"
    assert isinstance(body["checks"], list) and body["checks"]

    listed = await client.get(f"/api/v1/projects/{pid}/gate/evaluations")
    assert listed.status_code == 200
    items = listed.json()["items"]
    assert len(items) == 1
    assert items[0]["id"] == body["id"]


async def test_evaluations_are_append_only(client: AsyncClient, db_session: AsyncSession):
    project = await _make_project(db_session)
    pid = str(project.id)
    payload = {"produced_artifacts": [], "auto_enforced": False, "approved": False}

    await client.post(f"/api/v1/projects/{pid}/phases/requirements/gate/evaluations",
                      headers=_approver(), json=payload)
    await client.post(f"/api/v1/projects/{pid}/phases/requirements/gate/evaluations",
                      headers=_approver(), json=payload)

    listed = await client.get(f"/api/v1/projects/{pid}/gate/evaluations?phase=requirements")
    assert listed.json()["total"] == 2  # each evaluation is a new row


async def test_persist_requires_approver_persona(client: AsyncClient, db_session: AsyncSession):
    project = await _make_project(db_session)
    pid = str(project.id)
    resp = await client.post(
        f"/api/v1/projects/{pid}/phases/requirements/gate/evaluations",
        headers=_non_approver(),
        json={"produced_artifacts": [], "auto_enforced": True},
    )
    assert resp.status_code == 403


async def test_unknown_phase_returns_problem_detail(client: AsyncClient, db_session: AsyncSession):
    project = await _make_project(db_session)
    pid = str(project.id)
    resp = await client.post(
        f"/api/v1/projects/{pid}/phases/not-a-phase/gate/evaluations",
        headers=_approver(),
        json={"produced_artifacts": []},
    )
    assert resp.status_code == 404
    assert resp.json()["status"] == 404  # RFC 7807
