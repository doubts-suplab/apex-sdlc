from __future__ import annotations

import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

DeliveryStatus = Literal["proposed", "planned", "in_progress", "done", "dropped"]
DeliveryPriority = Literal["low", "medium", "high", "critical"]
DeliverySource = Literal["human", "agent"]


class DeliveryCreate(BaseModel):
    """Payload for creating a delivery under a project (project comes from the path)."""

    model_config = ConfigDict(extra="forbid")

    title: str = Field(..., min_length=1, max_length=255)
    description: str | None = Field(default=None)
    status: DeliveryStatus = Field(default="proposed")
    priority: DeliveryPriority = Field(default="medium")
    estimate_points: int | None = Field(default=None, ge=0, le=1000)
    target_ref: str | None = Field(default=None, max_length=255)
    source: DeliverySource = Field(default="human")


class DeliveryUpdate(BaseModel):
    """Payload for partial-update of a delivery (all fields optional)."""

    model_config = ConfigDict(extra="forbid")

    title: str | None = Field(default=None, min_length=1, max_length=255)
    description: str | None = Field(default=None)
    status: DeliveryStatus | None = Field(default=None)
    priority: DeliveryPriority | None = Field(default=None)
    estimate_points: int | None = Field(default=None, ge=0, le=1000)
    target_ref: str | None = Field(default=None, max_length=255)


class DeliveryResponse(BaseModel):
    """Read-side representation of a delivery."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    project_id: uuid.UUID
    title: str
    description: str | None
    status: str
    priority: str
    estimate_points: int | None
    target_ref: str | None
    source: str
    created_at: datetime
    updated_at: datetime


class PlanRequest(BaseModel):
    """Payload for asking the planning agent to propose a delivery backlog."""

    model_config = ConfigDict(extra="forbid")

    brief: str = Field(default="", description="Free-text project brief the plan is derived from")
    actor_id: str = Field(default="system", max_length=255)


class PlanDecision(BaseModel):
    """The governed decision the planning agent produced (a suggestion, never auto-enforced)."""

    action: str
    confidence: float
    auto_enforced: bool
    rationale: str


class PlanResponse(BaseModel):
    """The proposed deliveries plus the governed decision that produced them."""

    decision: PlanDecision
    deliveries: list[DeliveryResponse]
