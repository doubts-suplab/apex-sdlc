"""DevOps flow API — turn an NL intent into a governed, multi-tool DevOps action.

``POST /devops/flow`` plans tool calls from an intent and runs them through the harness (default-deny
tool registry + confidence gate). Today it uses the **offline** tool adapters, so it is safe to call
without credentials; a live build swaps in credentialed adapters of the same names. The endpoint requires
an **approver persona** — driving external write tools is a privileged action.
"""

from __future__ import annotations

from typing import Annotated, Any

from fastapi import APIRouter, Depends
from pydantic import BaseModel, ConfigDict, Field

from app.agents.tools.live_adapters import resolve_adapters
from app.core.security import Principal, require_persona
from app.db.session import DbSession
from app.devops import run_devops_flow
from app.integrations.llm.factory import get_llm_provider
from app.models.tool_call import ToolCallAudit

router = APIRouter(prefix="/devops", tags=["devops"])

_APPROVER_PERSONAS = ("lead", "developer", "architect", "ciso")


class DevOpsFlowRequest(BaseModel):
    """An NL intent plus the concrete targets the phrasing does not carry."""

    model_config = ConfigDict(extra="forbid")

    intent: str = Field(..., min_length=1, description="Free-text DevOps request")
    context: dict[str, Any] = Field(
        default_factory=dict,
        description="Targets: repo, jira_project_key, confluence_space, slack_channel, jenkins_job, feature…",
    )


@router.post("/flow", summary="Plan + run a governed multi-tool DevOps flow from an NL intent")
async def run_flow(
    body: DevOpsFlowRequest,
    db: DbSession,
    principal: Annotated[Principal, Depends(require_persona(*_APPROVER_PERSONAS))],
) -> dict[str, Any]:
    # Live per tool where credentials are configured, offline otherwise (see resolve_adapters).
    result = run_devops_flow(
        llm=get_llm_provider(),
        intent=body.intent,
        context=body.context,
        actor_id=principal.subject,
        adapters=resolve_adapters(),
    )
    decision = result.decision
    # Persist an append-only audit row per executed governed tool call (Increment 10 close).
    for call in result.tool_calls:
        outcome = call.get("result") or {}
        db.add(
            ToolCallAudit(
                actor=principal.subject,
                tool=str(call.get("tool", "")),
                system=str(outcome.get("system", "")),
                executed=True,
                detail=str(outcome.get("action", ""))[:2000],
            )
        )
    await db.flush()
    return {
        "action": decision.action.name,
        "confidence": decision.confidence,
        "auto_enforced": decision.auto_enforced,
        "rationale": decision.rationale,
        "executed": decision.action.name == "ALLOW",
        "tool_calls": len(result.tool_calls),
        "artifacts": [{"name": a["name"], "kind": a["kind"]} for a in result.artifacts],
    }


@router.get("/tool-calls", summary="Append-only audit of executed governed tool calls")
async def list_tool_calls(db: DbSession, limit: int = 50) -> dict[str, Any]:
    from sqlalchemy import select

    result = await db.execute(
        select(ToolCallAudit).order_by(ToolCallAudit.created_at.desc()).limit(limit)
    )
    items = list(result.scalars().all())
    return {
        "total": len(items),
        "items": [
            {
                "id": str(t.id),
                "actor": t.actor,
                "tool": t.tool,
                "system": t.system,
                "executed": t.executed,
                "detail": t.detail,
                "created_at": t.created_at.isoformat() if t.created_at else None,
            }
            for t in items
        ],
    }
