"""MemberService — teams + members CRUD and the token→Member resolution the RBAC layer relies on.

The persona↔identity mapping that Increments 8/16/17 referenced: a token's ``sub`` is reconciled against a
project's ``members`` so authority can be tied to a real person, not just a claimed persona. Mirrors the
``ProjectService`` async-service pattern.
"""

from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger
from app.models.team import Member, Team
from app.schemas.team import MemberCreate, TeamCreate

logger = get_logger(__name__)

_DEFAULT_TEAM_SLUG = "core"


class MemberService:
    """Async CRUD for teams + members, plus token→member resolution."""

    def __init__(self, db: AsyncSession) -> None:
        self._db = db

    # -- teams ------------------------------------------------------------------------------------
    async def create_team(self, organisation_id: uuid.UUID, payload: TeamCreate) -> Team:
        team = Team(
            organisation_id=organisation_id,
            name=payload.name,
            slug=payload.slug,
            description=payload.description,
        )
        self._db.add(team)
        await self._db.flush()
        await self._db.refresh(team)
        logger.info("team.created", id=str(team.id), org_id=str(organisation_id), slug=team.slug)
        return team

    async def list_teams(self, organisation_id: uuid.UUID) -> list[Team]:
        result = await self._db.execute(
            select(Team).where(Team.organisation_id == organisation_id).order_by(Team.created_at)
        )
        return list(result.scalars().all())

    async def ensure_default_team(self, organisation_id: uuid.UUID, name: str = "Core Team") -> Team:
        """Return the org's default ``core`` team, creating it if absent (idempotent)."""
        result = await self._db.execute(
            select(Team).where(
                Team.organisation_id == organisation_id, Team.slug == _DEFAULT_TEAM_SLUG
            )
        )
        existing = result.scalar_one_or_none()
        if existing is not None:
            return existing
        team = Team(
            organisation_id=organisation_id,
            name=name,
            slug=_DEFAULT_TEAM_SLUG,
            description="Default team seeded at onboarding.",
        )
        self._db.add(team)
        await self._db.flush()
        await self._db.refresh(team)
        logger.info("team.default_seeded", id=str(team.id), org_id=str(organisation_id))
        return team

    # -- members ----------------------------------------------------------------------------------
    async def add_member(self, project_id: uuid.UUID, payload: MemberCreate) -> Member:
        member = Member(
            project_id=project_id,
            team_id=payload.team_id,
            subject=payload.subject,
            persona=payload.persona,
            display_name=payload.display_name or payload.subject,
            email=payload.email,
        )
        self._db.add(member)
        await self._db.flush()
        await self._db.refresh(member)
        logger.info(
            "member.added",
            id=str(member.id),
            project_id=str(project_id),
            subject=member.subject,
            persona=member.persona,
        )
        return member

    async def list_members(self, project_id: uuid.UUID) -> list[Member]:
        result = await self._db.execute(
            select(Member).where(Member.project_id == project_id).order_by(Member.created_at)
        )
        return list(result.scalars().all())

    async def get_member(self, project_id: uuid.UUID, subject: str) -> Member | None:
        """Resolve a token subject to its project Member, or None if the subject is not a member."""
        result = await self._db.execute(
            select(Member).where(
                Member.project_id == project_id, Member.subject == subject
            )
        )
        return result.scalar_one_or_none()
