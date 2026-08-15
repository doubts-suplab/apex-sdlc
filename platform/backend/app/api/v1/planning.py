from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from halo_agent_harness import ToolRegistry

from app.agents.context import AgentContext
from app.agents.planning import PlanningAgent
from app.agents.runtime import build_apex_harness, run_agent
from app.core.logging import get_logger
from app.db.session import DbSession
from app.integrations.llm.factory import get_llm_provider
from app.schemas.common import ProblemDetail
from app.schemas.delivery import (
    DeliveryCreate,
    DeliveryResponse,
    PlanDecision,
    PlanRequest,
    PlanResponse,
)
from app.services.delivery_service import DeliveryService
from app.services.project_service import ProjectService

router = APIRouter(prefix="/projects/{project_id}", tags=["planning"])
logger = get_logger(__name__)


def _get_delivery_service(db: DbSession) -> DeliveryService:
    return DeliveryService(db)


def _get_project_service(db: DbSession) -> ProjectService:
    return ProjectService(db)


DelService = Annotated[DeliveryService, Depends(_get_delivery_service)]
ProjService = Annotated[ProjectService, Depends(_get_project_service)]

_PROJECT_NOT_FOUND = ProblemDetail(
    type="https://apex.example.com/problems/not-found",
    title="Project Not Found",
    status=404,
    detail="The requested project does not exist.",
)


@router.post(
    "/plan",
    response_model=PlanResponse,
    status_code=status.HTTP_201_CREATED,
    responses={404: {"model": ProblemDetail}},
    summary="Propose a delivery plan for a project",
)
async def plan_project(
    project_id: uuid.UUID,
    payload: PlanRequest,
    service: DelService,
    projects: ProjService,
) -> PlanResponse:
    """Run the planning agent (on the harness) to propose a prioritized delivery backlog.

    The agent proposes at ``SUGGEST`` authority — the harness never auto-enforces it — so the proposed
    deliveries are persisted as ``status='proposed', source='agent'`` for a human to accept.
    """
    if await projects.get_by_id(project_id) is None:
        raise HTTPException(status_code=404, detail=_PROJECT_NOT_FOUND.model_dump())

    agent = PlanningAgent(get_llm_provider())
    harness = build_apex_harness(registry=ToolRegistry())
    ctx = AgentContext(
        project_id=str(project_id),
        phase="planning",
        actor_id=payload.actor_id,
        inputs={"brief": payload.brief},
        run_id=f"plan:{project_id}",
    )
    result = run_agent(harness, agent, ctx)

    created: list[DeliveryResponse] = []
    for draft in agent.proposed():
        delivery = await service.create(
            project_id,
            DeliveryCreate(
                title=draft["title"],
                description=draft["description"],
                status="proposed",
                priority=draft["priority"],
                estimate_points=draft["estimate_points"],
                source="agent",
            ),
        )
        created.append(DeliveryResponse.model_validate(delivery))

    logger.info(
        "plan.proposed",
        project_id=str(project_id),
        count=len(created),
        action=result.decision.action.value,
        auto_enforced=result.decision.auto_enforced,
    )
    return PlanResponse(
        decision=PlanDecision(
            action=result.decision.action.value,
            confidence=result.decision.confidence,
            auto_enforced=result.decision.auto_enforced,
            rationale=result.decision.rationale,
        ),
        deliveries=created,
    )
