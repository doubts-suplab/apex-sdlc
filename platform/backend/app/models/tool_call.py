"""ToolCallAudit ORM model — an append-only record of each governed tool call.

Every tool the harness executes (open a PR, create a Jira issue, publish a Confluence page, …) is a
real-world side effect that must be attributable and reviewable. This records one row per executed call:
who ran it, which tool, the target system, and a compact detail. Append-only, like the AI-action audit
log — it is the tool-call analogue of ``AuditLog``.
"""

from __future__ import annotations

import uuid

from sqlalchemy import Boolean, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin


class ToolCallAudit(Base, TimestampMixin):
    """One executed governed tool call — append-only audit."""

    __tablename__ = "tool_call_audits"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    actor: Mapped[str] = mapped_column(String(255), nullable=False)  # token subject that ran the flow
    tool: Mapped[str] = mapped_column(String(100), nullable=False)  # catalog tool name
    system: Mapped[str] = mapped_column(String(50), nullable=False, default="")  # github | jira | …
    executed: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    detail: Mapped[str] = mapped_column(Text, nullable=False, default="")

    def __repr__(self) -> str:
        return f"<ToolCallAudit tool={self.tool!r} system={self.system!r} by={self.actor!r}>"
