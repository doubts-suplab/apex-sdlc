from __future__ import annotations

import uuid

from sqlalchemy import JSON, ForeignKey, Integer, String
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin

# JSONB on PostgreSQL (production); generic JSON elsewhere (SQLite in tests) so the schema compiles.
_JSON = JSON().with_variant(JSONB, "postgresql")


class ProjectManifestRecord(Base, TimestampMixin):
    """The persisted eeik project-manifest posture for a project — how APEX *manages* a governed project.

    One row per project (1:1). APEX ingests a repo's ``project-manifest.yaml`` through the eeik engine
    (validate + resolve packs) and records the result here: a few first-class posture columns for
    querying and the portfolio rollup, plus the full ``raw`` manifest for fidelity (the canonical eeik
    schema carries fields APEX's internal Pydantic model drops, e.g. ``governance.coverage_threshold``).
    Provenance (``engine``, ``source_ref``) records which engine authored the decision — ``sdk``/``mcp``
    when the real eeik engine validated, ``vendored`` on the offline fallback — and where the manifest
    came from. Generic by design: nothing here names any particular organisation or project.
    """

    __tablename__ = "project_manifests"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    project_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("projects.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
        index=True,
    )

    # First-class posture (mirrors the eeik manifest; nullable so a thin manifest still persists).
    domain: Mapped[str | None] = mapped_column(String(50), nullable=True)
    governance_profile: Mapped[str | None] = mapped_column(String(50), nullable=True)
    coverage_threshold: Mapped[int | None] = mapped_column(Integer, nullable=True)
    compliance_frameworks: Mapped[list[str]] = mapped_column(_JSON, nullable=False, default=list)
    resolved_packs: Mapped[list[str]] = mapped_column(_JSON, nullable=False, default=list)

    # Provenance.
    engine: Mapped[str | None] = mapped_column(String(20), nullable=True)
    source_ref: Mapped[str | None] = mapped_column(String(500), nullable=True)

    # Full manifest as ingested — no fidelity loss.
    raw: Mapped[dict] = mapped_column(_JSON, nullable=False, default=dict)

    project: Mapped["Project"] = relationship(  # type: ignore[name-defined]  # noqa: F821
        "Project",
        back_populates="manifest",
        lazy="noload",
    )

    def __repr__(self) -> str:
        return (
            f"<ProjectManifestRecord project={self.project_id} "
            f"profile={self.governance_profile!r} domain={self.domain!r}>"
        )
