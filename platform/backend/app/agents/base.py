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

from app.middleware.pii_guard import PiiGuard

from .context import AgentContext, context_from_input

T = TypeVar("T")

# Golden rule (backend CLAUDE.md #9): all LLM I/O passes through the PII guard. One shared, stateless
# regex guard is enough — it holds no per-request state.
_PII_GUARD = PiiGuard()

# A generated artifact body must clear this length to be used; below it the agent falls back to its
# deterministic template. Set well above the offline stub provider's one-line replies (≤ ~110 chars) and
# well below a real multi-section artifact (300+ chars), so the offline demo stays byte-reproducible while
# a real provider's output is used.
_MIN_GENERATED_LEN = 200


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
        self._input_tokens = 0
        self._output_tokens = 0
        self._model = ""
        self._provider = ""

    # -- harness Agent protocol -----------------------------------------
    def run(self, request: AgentInput, tools: ToolInvoker) -> Decision:
        # A harness invocation is one run: start from an empty artifact buffer and zeroed token tally so
        # a reused instance never leaks a previous run's artifacts or usage. The harness owns the
        # Decision; artifacts + token usage ride alongside on the agent (the ``AgentOutput`` carries only
        # the Decision).
        self._artifacts = []
        self._input_tokens = self._output_tokens = 0
        return self.decide(context_from_input(request), tools)

    def token_usage(self) -> tuple[int, int]:
        """(input_tokens, output_tokens) accumulated across this run's LLM calls."""
        return self._input_tokens, self._output_tokens

    @property
    def model(self) -> str:
        return self._model

    @property
    def provider(self) -> str:
        return self._provider

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
        """Synchronously obtain a completion via the injected LLM port, PII-guarded on both sides.

        **Outgoing:** every message body (and the system prompt) is scrubbed — PII never reaches the
        model. **Incoming:** the completion is scanned and any findings are logged for the audit trail,
        but the text is returned intact (redacting the model's output would corrupt a legitimately
        generated artifact; the primary data-protection boundary is the outbound one).
        """
        safe_messages = [
            Message(role=m.role, content=_PII_GUARD.scrub(m.content)) for m in messages
        ]
        safe_system = _PII_GUARD.scrub(system) if system else system
        result: Any = _run_sync(self._llm.complete(safe_messages, system=safe_system))
        # Accumulate token usage + capture the model/provider for cost accounting (spec: every run is
        # metered). The harness owns the decision; usage rides alongside on the agent.
        self._input_tokens += int(getattr(result, "input_tokens", 0) or 0)
        self._output_tokens += int(getattr(result, "output_tokens", 0) or 0)
        self._model = getattr(result, "model", "") or self._model
        self._provider = getattr(result, "provider", "") or self._provider
        content: str = result.content
        findings = _PII_GUARD.scan(content)
        if findings:
            _PII_GUARD.log_findings(findings, source=f"agent:{getattr(self, 'name', 'unknown')}")
        return content

    def generate(self, *, prompt: str, fallback: str, system: str | None = None) -> str:
        """Generate an artifact body via the LLM port, falling back to a deterministic template.

        A substantive completion (from a real provider) is used verbatim; a short reply — the offline
        ``stub`` provider returns a one-liner — or any LLM failure resolves to ``fallback``. This is what
        keeps the offline reference journey deterministic while a configured provider yields real output.
        """
        try:
            out = self.complete([Message(role="user", content=prompt)], system=system).strip()
        except Exception:  # LLM failure is never fatal — the harness applies safe defaults around us
            return fallback
        return out if len(out) >= _MIN_GENERATED_LEN else fallback
