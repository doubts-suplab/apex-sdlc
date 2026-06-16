from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin

INTEGRATION_TYPES = ("github", "jira", "rally", "confluence")


class ProjectIntegration(Base, TimestampMixin):
    """Stores per-project external integration configuration.

    One row per (project, integration_type) pair — enforced by unique constraint.
    Credentials are referenced by name from AWS Secrets Manager (production) or
    read directly from environment variables (development, ``credentials_ref="env"``).
    """

    __tablename__ = "project_integrations"
    __table_args__ = (
        UniqueConstraint(
            "project_id",
            "integration_type",
            name="uq_project_integration_type",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        primary_key=True,
        default=uuid.uuid4,
    )
    project_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("projects.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    integration_type: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
    )
    # Integration-specific config — e.g. {"repo": "org/repo"} or {"board_id": "42"}
    config: Mapped[dict] = mapped_column(
        JSONB,
        nullable=False,
        default=dict,
    )
    # AWS Secrets Manager secret name, or "env" for local dev
    credentials_ref: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
    )
    enabled: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
    )
    last_synced_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    # Relationships
    project: Mapped["Project"] = relationship(  # type: ignore[name-defined]  # noqa: F821
        "Project",
        back_populates="integrations",
        lazy="noload",
    )

    def __repr__(self) -> str:
        return (
            f"<ProjectIntegration project_id={self.project_id} "
            f"type={self.integration_type!r} enabled={self.enabled}>"
        )
