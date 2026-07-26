"""Wire the DevOps tools into a harness ``ToolRegistry`` with per-agent allowlists (default-deny).

The registry is the harness's runtime-enforced tool boundary (spec §5): a tool an agent was not explicitly
granted raises ``ToolNotAuthorizedError`` *before* any side effect. There are **no wildcards**, and a
supervisor agent holds **no** tools. This module registers the catalog against a chosen adapter set and
grants the DevOps orchestrator exactly the five write tools it needs.
"""

from __future__ import annotations

from typing import Any

from agent_harness import ToolRegistry

from app.agents.tools.adapters import OFFLINE_ADAPTERS
from app.agents.tools.catalog import TOOL_CATALOG

# The agent that drives the DevOps flow. Keep in sync with ``app.devops.flow.DevOpsAgent.name``.
DEVOPS_AGENT_NAME = "devops-orchestrator"


def build_tool_registry(adapters: dict[str, Any] | None = None) -> ToolRegistry:
    """Register the tool catalog and grant the DevOps agent its allowlist.

    ``adapters`` maps tool name → ``dict -> dict`` impl; defaults to the offline deterministic set. Pass a
    credentialed set (same names) to go live without touching the agent or the flow.
    """
    impls = adapters or OFFLINE_ADAPTERS
    registry = ToolRegistry()
    for spec in TOOL_CATALOG:
        impl = impls.get(spec.name)
        if impl is None:
            continue  # a live set may expose a subset; only register what has an implementation
        registry.register_tool(
            spec.name,
            impl,
            description=spec.description,
            side_effect=spec.side_effect,
        )
    granted = frozenset(name for name in (s.name for s in TOOL_CATALOG) if name in impls)
    registry.grant(DEVOPS_AGENT_NAME, granted)
    return registry
