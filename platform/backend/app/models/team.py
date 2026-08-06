"""Team + Member ORM models.

- ``Team`` — a group within an organisation, assignable to projects.
- ``Member`` — a user holding a **persona role** (developer/ba/qa/pm/lead/architect/ciso) on a project.
  This is the persona↔identity mapping the RBAC layer (Increment 8) referenced: a token's persona can be
  reconciled against a project's members.
"""

from __future__ import annotations

import uuid

from sqlalchemy import ForeignKey, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin


class Team(Base, TimestampMixin):
    """A team within an organisation."""

    __tablename__ = "teams"
    __table_args__ = (UniqueConstraint("organisation_id", "slug", name="uq_team_org_slug"),)

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    organisation_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("organisations.id", ondelete="CASCADE"), nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    slug: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)

    organisation: Mapped["Organisation"] = relationship(  # type: ignore[name-defined]  # noqa: F821
        "Organisation", lazy="noload"
    )

    def __repr__(self) -> str:
        return f"<Team id={self.id} slug={self.slug!r}>"


class Member(Base, TimestampMixin):
    """A user with a persona role on a project (optionally via a team)."""

    __tablename__ = "members"
    __table_args__ = (UniqueConstraint("project_id", "subject", name="uq_member_project_subject"),)

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    project_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, index=True
    )
    team_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("teams.id", ondelete="SET NULL"), nullable=True, index=True
    )
    subject: Mapped[str] = mapped_column(String(255), nullable=False)  # user/subject id (matches JWT sub)
    display_name: Mapped[str] = mapped_column(String(255), nullable=False, default="")
    email: Mapped[str | None] = mapped_column(String(320), nullable=True)
    persona: Mapped[str] = mapped_column(String(20), nullable=False)  # one of app.agents.catalog.PERSONAS

    project: Mapped["Project"] = relationship(  # type: ignore[name-defined]  # noqa: F821
        "Project", lazy="noload"
    )
    team: Mapped["Team | None"] = relationship("Team", lazy="noload")

    def __repr__(self) -> str:
        return f"<Member id={self.id} subject={self.subject!r} persona={self.persona!r}>"
