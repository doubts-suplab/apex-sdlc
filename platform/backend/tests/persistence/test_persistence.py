"""Persistence tests — a governed journey's runs, artifacts, and gates become stored state.

Uses the shared aiosqlite fixtures from ``tests/conftest.py`` (DB-backed; not ``--noconftest``).
"""

from __future__ import annotations

import uuid

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.orchestrator import run_reference_journey
from app.integrations.llm.stub_provider import StubLLMProvider
from app.models.organisation import Organisation
from app.models.project import Project
from app.services.persistence_service import PersistenceService

pytestmark = pytest.mark.asyncio


async def _make_project(db: AsyncSession) -> Project:
    org = Organisation(name=f"Org {uuid.uuid4().hex[:8]}", slug=f"org-{uuid.uuid4().hex[:8]}")
    db.add(org)
    await db.flush()
    project = Project(organisation_id=org.id, name="Refund Service", slug="refund-service")
    db.add(project)
    await db.flush()
    return project


# -- service layer ------------------------------------------------------------------------------
async def test_persist_journey_stores_runs_artifacts_and_gates(db_session: AsyncSession):
    project = await _make_project(db_session)
    journey = run_reference_journey(StubLLMProvider())
    svc = PersistenceService(db_session)

    summary = await svc.persist_journey(project.id, journey, approvals=set())
    assert summary["agent_runs"] == 7
    assert summary["artifacts"] == 17
    assert summary["blocking_phase"] == "requirements"  # no approvals → spine blocks

    artifacts = await svc.list_artifacts(project.id)
    runs = await svc.list_agent_runs(project.id)
    gates = await svc.gate_matrix(project.id)
    assert len(artifacts) == 17
    assert len(runs) == 7
    assert len(gates) == 7
    # every artifact has a content hash; development/cicd gates passed, requirements pending.
    assert all(len(a.content_sha256) == 64 for a in artifacts)
    by_phase = {g["phase"]: g["status"] for g in gates}
    assert by_phase["development"] == "passed"
    assert by_phase["requirements"] == "pending"


async def test_content_hash_is_stable(db_session: AsyncSession):
    project = await _make_project(db_session)
    journey = run_reference_journey(StubLLMProvider())
    svc = PersistenceService(db_session)
    await svc.persist_journey(project.id, journey)
    stories = next(a for a in await svc.list_artifacts(project.id) if a.name == "user-stories.md")
    import hashlib

    assert stories.content_sha256 == hashlib.sha256(stories.content.encode()).hexdigest()


# -- API layer ----------------------------------------------------------------------------------
async def test_persist_and_read_via_api(client: AsyncClient, db_session: AsyncSession):
    project = await _make_project(db_session)
    pid = str(project.id)

    persisted = await client.post(f"/api/v1/projects/{pid}/journey/persist")
    assert persisted.status_code == 200
    assert persisted.json()["artifacts"] == 17

    arts = await client.get(f"/api/v1/projects/{pid}/artifacts")
    assert arts.status_code == 200 and arts.json()["total"] == 17

    runs = await client.get(f"/api/v1/projects/{pid}/agent-runs")
    assert runs.json()["total"] == 7

    gates = await client.get(f"/api/v1/projects/{pid}/gate-status")
    assert len(gates.json()["gates"]) == 7


async def test_persist_unknown_project_404(client: AsyncClient):
    missing = "00000000-0000-0000-0000-000000000000"
    r = await client.post(f"/api/v1/projects/{missing}/journey/persist")
    assert r.status_code == 404


# -- onboarding persistence ---------------------------------------------------------------------
async def test_onboarding_persists_project_when_org_supplied(client: AsyncClient, db_session: AsyncSession):
    org = Organisation(name="Payments", slug="payments")
    db_session.add(org)
    await db_session.flush()

    manifest = {
        "schema_version": "1.0",
        "project": {"name": "refund-service", "description": "", "owner": "pay",
                    "domain": "generic", "project_type": "greenfield"},
        "technology": {"backend": {"language": "java", "framework": "spring-boot"},
                       "frontend": {"framework": "none"}, "database": {"migration_tool": "flyway"}},
        "architecture": {"style": "microservices", "api_style": "rest"},
        "cloud": {"provider": "aws", "infra_as_code": "cdk"},
        "ai": {"enabled": False, "pattern": "none"},
        "governance": {"profile": "standard"},
    }
    resp = await client.post(f"/api/v1/onboarding/?organisation_id={org.id}", json=manifest)
    assert resp.status_code == 200
    assert "project_id" in resp.json()  # the onboarded project was persisted
