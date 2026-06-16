from __future__ import annotations

import uuid
from typing import Generic, TypeVar

from pydantic import BaseModel, ConfigDict

T = TypeVar("T")


class ProblemDetail(BaseModel):
    """RFC 7807 Problem Details response."""

    model_config = ConfigDict(extra="forbid")

    type: str = "about:blank"
    title: str
    status: int
    detail: str
    instance: str | None = None


class UUIDResponse(BaseModel):
    """Minimal response returning just an id."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID


class PaginatedResponse(BaseModel, Generic[T]):
    """Generic cursor-based paginated list response."""

    model_config = ConfigDict(arbitrary_types_allowed=True)

    items: list[T]
    total: int
    limit: int
    next_cursor: str | None = None
