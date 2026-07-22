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
from typing import Any, Awaitable, TypeVar

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

    # -- harness Agent protocol -----------------------------------------
    def run(self, request: AgentInput, tools: ToolInvoker) -> Decision:
        return self.decide(context_from_input(request), tools)

    @abstractmethod
    def decide(self, ctx: AgentContext, tools: ToolInvoker) -> Decision:
        """Produce a Decision for this phase. MUST NOT set ``auto_enforced`` (the harness owns it)."""

    # -- helpers --------------------------------------------------------
    def complete(self, messages: list[Message], system: str | None = None) -> str:
        """Synchronously obtain a completion via the injected LLM port."""
        result: Any = _run_sync(self._llm.complete(messages, system=system))
        return result.content
