"""Register the Aether ecosystem repos as APEX projects (offline, idempotent).

Gives the planning agent real targets to plan against without any live GitHub call: one ``aether``
organisation owning a project per ecosystem repo, each with its ``github_repo`` set. Idempotent —
re-running never duplicates the org or its projects — so it is safe to call at startup or from a test.
"""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger
from app.models.organisation import Organisation
from app.models.project import Project

logger = get_logger(__name__)

_ORG_NAME = "Aether"
_ORG_SLUG = "aether"
_OWNER = "doubts-suplab"

# (slug, display name, apex project_type) for each ecosystem repo. project_type is constrained to
# apex's PROJECT_TYPES — the Java platform layers map to spring-boot, the Python engines to python,
# and the doc/hub repos to generic.
AETHER_REPOS: tuple[tuple[str, str, str], ...] = (
    ("aether", "Aether (hub)", "generic"),
    ("aether-core", "Aether Core", "spring-boot"),
    ("aether-grid", "Aether Grid", "spring-boot"),
    ("aether-memory", "Aether Memory", "spring-boot"),
    ("aether-vault", "Aether Vault", "spring-boot"),
    ("aether-flow", "Aether Flow", "spring-boot"),
    ("aether-iel", "Aether IEL", "generic"),
    ("eeik-bootstrap", "EEIK Bootstrap", "python"),
    ("agent-harness", "HALO Agent Harness", "python"),
)


async def seed_aether_projects(db: AsyncSession) -> list[Project]:
    """Ensure the Aether org and one project per ecosystem repo exist. Returns the projects."""
    org = (
        await db.execute(select(Organisation).where(Organisation.slug == _ORG_SLUG))
    ).scalar_one_or_none()
    if org is None:
        org = Organisation(name=_ORG_NAME, slug=_ORG_SLUG, description="The Aether ecosystem.")
        db.add(org)
        await db.flush()
        logger.info("seed.aether.org_created", id=str(org.id))

    existing = {
        p.slug
        for p in (
            await db.execute(select(Project).where(Project.organisation_id == org.id))
        ).scalars()
    }

    projects: list[Project] = []
    created = 0
    for slug, name, project_type in AETHER_REPOS:
        if slug in existing:
            continue
        project = Project(
            organisation_id=org.id,
            name=name,
            slug=slug,
            description=f"{name} — Aether ecosystem repository.",
            project_type=project_type,
            github_repo=f"{_OWNER}/{slug}",
        )
        db.add(project)
        projects.append(project)
        created += 1
    await db.flush()
    logger.info("seed.aether.projects", created=created, total=len(AETHER_REPOS))
    return projects
