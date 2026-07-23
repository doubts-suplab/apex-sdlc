"""apex phase agents, running on the generic agent-harness runtime (doubts-suplab/agent-harness).

The harness owns agent execution governance (typed envelope, confidence gate, tool registry, audit,
human review, safe-failure defaults); apex supplies the agents and the infrastructure adapters.
"""

from __future__ import annotations

from .architecture import ArchitectureAgent
from .base import PhaseAgent
from .catalog import PERSONAS, PHASE_CATALOG, PHASE_ORDER, PhaseSpec, phases_for_persona, spec_for
from .cicd import ReleaseEngineerAgent
from .compliance import ComplianceOfficerAgent
from .context import (
    AgentContext,
    AgentResult,
    TokenUsage,
    context_from_input,
    to_agent_input,
    to_agent_result,
)
from .development import PRReviewerAgent
from .docs import TechWriterAgent
from .orchestrator import (
    REFERENCE_PROJECT,
    JourneyPhase,
    JourneyResult,
    run_journey,
    run_reference_journey,
)
from .requirements import RequirementsAgent
from .runtime import build_apex_harness, run_agent
from .testing import QAAnalystAgent

__all__ = [
    "PhaseAgent",
    # phase agents
    "RequirementsAgent",
    "ArchitectureAgent",
    "PRReviewerAgent",
    "QAAnalystAgent",
    "ReleaseEngineerAgent",
    "TechWriterAgent",
    "ComplianceOfficerAgent",
    # catalog (single source of truth)
    "PHASE_CATALOG",
    "PHASE_ORDER",
    "PERSONAS",
    "PhaseSpec",
    "spec_for",
    "phases_for_persona",
    # orchestration
    "REFERENCE_PROJECT",
    "JourneyPhase",
    "JourneyResult",
    "run_journey",
    "run_reference_journey",
    # context + runtime
    "AgentContext",
    "AgentResult",
    "TokenUsage",
    "context_from_input",
    "to_agent_input",
    "to_agent_result",
    "build_apex_harness",
    "run_agent",
]
