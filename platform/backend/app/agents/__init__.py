"""apex phase agents, running on the generic agent-harness runtime (doubts-suplab/agent-harness).

The harness owns agent execution governance (typed envelope, confidence gate, tool registry, audit,
human review, safe-failure defaults); apex supplies the agents and the infrastructure adapters.
"""

from __future__ import annotations

from .base import PhaseAgent
from .compliance import ComplianceOfficerAgent
from .context import (
    AgentContext,
    AgentResult,
    TokenUsage,
    context_from_input,
    to_agent_input,
    to_agent_result,
)
from .runtime import build_apex_harness, run_agent

__all__ = [
    "PhaseAgent",
    "ComplianceOfficerAgent",
    "AgentContext",
    "AgentResult",
    "TokenUsage",
    "context_from_input",
    "to_agent_input",
    "to_agent_result",
    "build_apex_harness",
    "run_agent",
]
