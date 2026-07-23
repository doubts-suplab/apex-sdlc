"""PhaseAgent — the base class apex phase agents extend.

A PhaseAgent satisfies the agent-harness ``Agent`` protocol: a stable name, a static authority ceiling,
and the DecisionActions it may emit. The harness enforces the confidence gate, tool registry, and
authority around ``run`` — the agent only proposes a Decision (it never sets ``auto_enforced``).

The harness ``Agent.run`` is synchronous; apex LLM providers are async, so ``complete`` bridges the two
(safe under Celery's sync workers and in tests).
"""

from __future__ import annotations

import asyncio
import concurrent.futures
from abc import ABC, abstractmethod
from collections.abc import Awaitable
from typing import Any, TypeVar

from agent_harness import AgentInput, AuthorityLevel, Decision, DecisionAction
from agent_harness.core.agent import ToolInvoker
from agent_harness.ports.llm import LlmPort, Message

from .context import AgentContext, context_from_input

T = TypeVar("T")


def _run_sync(coro: Awaitable[T]) -> T:
    """Run an async coroutine to completion from sync code, inside or outside a running loop."""
    try:
        asyncio.get_running_loop()
    except RuntimeError:
        return asyncio.run(coro)  # type: ignore[arg-type]
    with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
        return pool.submit(lambda: asyncio.run(coro)).result()  # type: ignore[arg-type]


class PhaseAgent(ABC):
    """Base for apex phase agents. Subclasses set the class attributes and implement ``decide``."""

    name: str
    authority_level: AuthorityLevel
    capabilities: frozenset[DecisionAction]

    def __init__(self, llm: LlmPort) -> None:
        self._llm = llm
        self._artifacts: list[dict[str, Any]] = []

    # -- harness Agent protocol -----------------------------------------
    def run(self, request: AgentInput, tools: ToolInvoker) -> Decision:
        # A harness invocation is one run: start from an empty artifact buffer so a reused instance
        # never leaks a previous run's artifacts. The harness owns the Decision; artifacts ride
        # alongside on the agent (the harness ``AgentOutput`` carries only the Decision).
        self._artifacts = []
        return self.decide(context_from_input(request), tools)

    @abstractmethod
    def decide(self, ctx: AgentContext, tools: ToolInvoker) -> Decision:
        """Produce a Decision for this phase. MUST NOT set ``auto_enforced`` (the harness owns it)."""

    # -- artifacts ------------------------------------------------------
    def emit_artifact(
        self,
        *,
        name: str,
        title: str,
        kind: str,
        content: str,
        fmt: str = "md",
    ) -> None:
        """Record an artifact this phase produced. Drained by the orchestrator after the run."""
        self._artifacts.append(
            {"name": name, "title": title, "kind": kind, "format": fmt, "content": content}
        )

    def drain_artifacts(self) -> list[dict[str, Any]]:
        """Return the artifacts produced by the most recent run and clear the buffer."""
        drained, self._artifacts = self._artifacts, []
        return drained

    # -- helpers --------------------------------------------------------
    def complete(self, messages: list[Message], system: str | None = None) -> str:
        """Synchronously obtain a completion via the injected LLM port."""
        result: Any = _run_sync(self._llm.complete(messages, system=system))
        return result.content
