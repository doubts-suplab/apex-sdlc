"""Team / Member model tests — persistence, the persona↔member mapping, and unique constraints."""

from __future__ import annotations

import uuid

import pytest
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.organisation import Organisation
from app.models.project import Project
from app.models.team import Member, Team

pytestmark = pytest.mark.asyncio


async def _org_project(db: AsyncSession) -> tuple[Organisation, Project]:
    org = Organisation(name=f"Org {uuid.uuid4().hex[:6]}", slug=f"org-{uuid.uuid4().hex[:6]}")
    db.add(org)
    await db.flush()
    project = Project(organisation_id=org.id, name="Refunds", slug="refunds")
    db.add(project)
    await db.flush()
    return org, project


async def test_team_and_members_persist_with_persona(db_session: AsyncSession):
    org, project = await _org_project(db_session)
    team = Team(organisation_id=org.id, name="Payments Squad", slug="payments")
    db_session.add(team)
    await db_session.flush()

    db_session.add_all(
        [
            Member(project_id=project.id, team_id=team.id, subject="lead@apex", persona="lead"),
            Member(project_id=project.id, team_id=team.id, subject="ba@apex", persona="ba"),
        ]
    )
    await db_session.flush()

    members = (
        await db_session.execute(select(Member).where(Member.project_id == project.id))
    ).scalars().all()
    assert {m.persona for m in members} == {"lead", "ba"}
    assert all(m.team_id == team.id for m in members)


async def test_member_is_unique_per_project_subject(db_session: AsyncSession):
    _, project = await _org_project(db_session)
    db_session.add(Member(project_id=project.id, subject="dev@apex", persona="developer"))
    await db_session.flush()
    # Same (project, subject) again → unique-constraint violation.
    db_session.add(Member(project_id=project.id, subject="dev@apex", persona="qa"))
    with pytest.raises(IntegrityError):
        await db_session.flush()
