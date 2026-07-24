from __future__ import annotations

import uuid

from sqlalchemy import ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin


class Artifact(Base, TimestampMixin):
    """A generated artifact stored for a project phase (user stories, ADR, test plan, …)."""

    __tablename__ = "artifacts"

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

    project: Mapped["Project"] = relationship(  # type: ignore[name-defined]  # noqa: F821
        "Project", lazy="noload"
    )

    def __repr__(self) -> str:
        return f"<Artifact id={self.id} phase={self.phase!r} name={self.name!r} v{self.version}>"
