from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin


class Artifact(Base, TimestampMixin):
    """The logical artifact for a project phase (user stories, ADR, test plan, …).

    Holds the *latest* content; every content change is also snapshotted in ``ArtifactVersion`` for
    lineage. Unique per (project, phase, name) so persistence upserts rather than duplicates.
    """

    __tablename__ = "artifacts"
    __table_args__ = (
        UniqueConstraint("project_id", "phase", "name", name="uq_artifact_project_phase_name"),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    project_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, index=True
    )
    phase: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    title: Mapped[str] = mapped_column(String(500), nullable=False, default="")
    kind: Mapped[str] = mapped_column(String(50), nullable=False, default="md")
    content_sha256: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)

    project: Mapped[Project] = relationship(  # type: ignore[name-defined]  # noqa: F821
        "Project", lazy="noload"
    )
    versions: Mapped[list[ArtifactVersion]] = relationship(
        "ArtifactVersion",
        back_populates="artifact",
        cascade="all, delete-orphan",
        lazy="noload",
    )

    def __repr__(self) -> str:
        return f"<Artifact id={self.id} phase={self.phase!r} name={self.name!r} v{self.version}>"


class ArtifactVersion(Base):
    """An immutable snapshot of an artifact's content at a given version (lineage)."""

    __tablename__ = "artifact_versions"
    __table_args__ = (
        UniqueConstraint("artifact_id", "version", name="uq_artifact_version"),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    artifact_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("artifacts.id", ondelete="CASCADE"), nullable=False, index=True
    )
    version: Mapped[int] = mapped_column(Integer, nullable=False)
    content_sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    artifact: Mapped[Artifact] = relationship("Artifact", back_populates="versions", lazy="noload")

    def __repr__(self) -> str:
        return f"<ArtifactVersion artifact={self.artifact_id} v{self.version}>"
