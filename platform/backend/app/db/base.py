from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import DateTime, event, func
from sqlalchemy.orm import DeclarativeBase, Mapped, Session, mapped_column


class Base(DeclarativeBase):
    """Shared declarative base for all ORM models."""

    pass


class AppendOnlyViolationError(Exception):
    """Raised when a flush would UPDATE or DELETE a row of an append-only table.

    Append-only enforcement is a governance invariant: the audit trail and gate-evaluation
    history must be tamper-evident, so once written they may only ever be read (golden rule #10).
    """


class AppendOnly:
    """Marker mixin: rows of this model may be inserted and read, but never updated or deleted.

    Any model that mixes this in is guarded by the ``before_flush`` listener below — an attempt to
    modify or delete a persisted instance raises :class:`AppendOnlyViolationError` before the flush
    reaches the database. This enforces the invariant in application code, independent of (and in
    addition to) any database-level protection, and works identically on PostgreSQL and SQLite.
    """


@event.listens_for(Session, "before_flush")
def _forbid_append_only_mutations(session: Session, flush_context: object, instances: object) -> None:
    """Veto UPDATE/DELETE of any append-only row before it is flushed.

    Fires for every session (the listener is registered on the base ``Session`` class), but only
    ever raises for :class:`AppendOnly` instances — inserts (``session.new``) and every other model
    pass through untouched.
    """
    for obj in session.deleted:
        if isinstance(obj, AppendOnly):
            raise AppendOnlyViolationError(
                f"{type(obj).__name__} is append-only and cannot be deleted"
            )
    for obj in session.dirty:
        if isinstance(obj, AppendOnly) and session.is_modified(obj, include_collections=False):
            raise AppendOnlyViolationError(
                f"{type(obj).__name__} is append-only and cannot be updated"
            )


class TimestampMixin:
    """Mixin that adds created_at and updated_at columns to any model."""

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
