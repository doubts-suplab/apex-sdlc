"""Append-only enforcement for the governance tables (golden rule #10).

The ``AppendOnly`` mixin + ``before_flush`` guard veto any UPDATE or DELETE of an audit_log,
pii_events, or gate_evaluations row before it reaches the database — inserts and reads are
unaffected, and other (mutable) models are never touched.
"""

from __future__ import annotations

import uuid

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.base import AppendOnlyViolationError
from app.models.audit import AuditLog, PolicyViolation
from app.models.organisation import Organisation
from app.models.project import Project


async def _make_project(db: AsyncSession) -> Project:
    org = Organisation(name=f"Org {uuid.uuid4().hex[:8]}", slug=f"org-{uuid.uuid4().hex[:8]}")
    db.add(org)
    await db.flush()
    project = Project(organisation_id=org.id, name="Refund Service", slug="refund-service")
    db.add(project)
    await db.flush()
    return project


async def _make_audit(db: AsyncSession) -> AuditLog:
    project = await _make_project(db)
    entry = AuditLog(
        project_id=project.id,
        actor="ciso",
        phase="governance",
        agent_name="ComplianceOfficerAgent",
        action="ALLOW",
        summary="initial",
    )
    db.add(entry)
    await db.flush()
    return entry


@pytest.mark.asyncio
async def test_audit_log_insert_is_allowed(db_session: AsyncSession) -> None:
    entry = await _make_audit(db_session)
    assert entry.id is not None


@pytest.mark.asyncio
async def test_audit_log_update_is_rejected(db_session: AsyncSession) -> None:
    entry = await _make_audit(db_session)

    entry.summary = "tampered"
    with pytest.raises(AppendOnlyViolationError, match="append-only and cannot be updated"):
        await db_session.flush()


@pytest.mark.asyncio
async def test_audit_log_delete_is_rejected(db_session: AsyncSession) -> None:
    entry = await _make_audit(db_session)

    await db_session.delete(entry)
    with pytest.raises(AppendOnlyViolationError, match="append-only and cannot be deleted"):
        await db_session.flush()


@pytest.mark.asyncio
async def test_mutable_model_is_unaffected(db_session: AsyncSession) -> None:
    # PolicyViolation carries a remediation-status workflow, so it must stay updatable.
    project = await _make_project(db_session)
    violation = PolicyViolation(
        project_id=project.id, phase="governance", policy="pii-egress", severity="high"
    )
    db_session.add(violation)
    await db_session.flush()

    violation.status = "resolved"
    await db_session.flush()  # no AppendOnlyViolationError

    assert violation.status == "resolved"
