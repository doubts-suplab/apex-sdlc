from __future__ import annotations

import uuid

from sqlalchemy import ForeignKey, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin

PROJECT_TYPES = ("spring-boot", "angular", "shared-lib", "mainframe", "python", "generic")
PHASE_TYPES = (
    "requirements",
    "architecture",
    "development",
    "testing",
    "cicd",
    "docs",
    "governance",
)
PROJECT_STATUSES = ("active", "paused", "archived")


class Project(Base, TimestampMixin):
    """A software project belonging to an organisation."""

    __tablename__ = "projects"
    __table_args__ = (UniqueConstraint("organisation_id", "slug", name="uq_project_org_slug"),)

    id: Mapped[uuid.UUID] = mapped_column(
        primary_key=True,
        default=uuid.uuid4,
    )
    organisation_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("organisations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    slug: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    project_type: Mapped[str] = mapped_column(String(50), nullable=False, default="generic")
    github_repo: Mapped[str | None] = mapped_column(String(255), nullable=True)
    jira_board_id: Mapped[str | None] = mapped_column(String(100), nullable=True)
    confluence_space_key: Mapped[str | None] = mapped_column(String(100), nullable=True)
    current_phase: Mapped[str] = mapped_column(
        String(50), nullable=False, default="requirements"
    )
    status: Mapped[str] = mapped_column(String(50), nullable=False, default="active")
    # Issue tracker in use for this project: jira | rally | none
    issue_tracker: Mapped[str] = mapped_column(String(20), nullable=False, default="none")

    # Relationships
    organisation: Mapped["Organisation"] = relationship(  # type: ignore[name-defined]  # noqa: F821
        "Organisation",
        back_populates="projects",
        lazy="noload",
    )
    phases: Mapped[list["Phase"]] = relationship(  # type: ignore[name-defined]  # noqa: F821
        "Phase",
        back_populates="project",
        cascade="all, delete-orphan",
        lazy="noload",
    )
    integrations: Mapped[list["ProjectIntegration"]] = relationship(  # type: ignore[name-defined]  # noqa: F821
        "ProjectIntegration",
        back_populates="project",
        cascade="all, delete-orphan",
        lazy="noload",
    )

    def __repr__(self) -> str:
        return f"<Project id={self.id} slug={self.slug!r}>"
