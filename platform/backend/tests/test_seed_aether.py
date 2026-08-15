from __future__ import annotations

import pytest
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.organisation import Organisation
from app.models.project import Project
from app.seeds.aether import AETHER_REPOS, seed_aether_projects


@pytest.mark.asyncio
async def test_seed_registers_all_aether_repos(db_session: AsyncSession) -> None:
    projects = await seed_aether_projects(db_session)

    assert len(projects) == len(AETHER_REPOS) == 9
    # every project carries an owner/repo github_repo the planner can target
    assert all(p.github_repo == f"doubts-suplab/{p.slug}" for p in projects)
    slugs = {p.slug for p in projects}
    assert "aether-core" in slugs and "agent-harness" in slugs


@pytest.mark.asyncio
async def test_seed_is_idempotent(db_session: AsyncSession) -> None:
    await seed_aether_projects(db_session)
    second = await seed_aether_projects(db_session)

    assert second == []  # nothing new created on the second run
    # count only the Aether org's projects — other tests may have committed unrelated rows
    org_id = (
        await db_session.execute(select(Organisation.id).where(Organisation.slug == "aether"))
    ).scalar_one()
    aether_total = (
        await db_session.execute(
            select(func.count()).select_from(Project).where(Project.organisation_id == org_id)
        )
    ).scalar_one()
    assert aether_total == len(AETHER_REPOS)  # no duplicates
