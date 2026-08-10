"""PII-guard tests — the regex guard detects/redacts PII, and every LLM call is guarded on both sides.

Self-contained (no DB / FastAPI): ``pytest --noconftest tests/middleware/test_pii_guard.py``.
"""

from __future__ import annotations

from collections.abc import AsyncIterator

from halo_agent_harness.ports.llm import CompletionResult, Message, ToolDefinition

from app.agents.base import PhaseAgent
from app.middleware.pii_guard import PiiGuard

# -- guard unit ---------------------------------------------------------------------------------


def test_scrub_redacts_high_confidence_pii():
    guard = PiiGuard()
    text = "Contact jane.doe@example.com or SSN 123-45-6789; card 4111 1111 1111 1111."
    scrubbed = guard.scrub(text)
    assert "jane.doe@example.com" not in scrubbed
    assert "123-45-6789" not in scrubbed
    assert "4111 1111 1111 1111" not in scrubbed
    assert "[REDACTED]" in scrubbed


def test_scan_reports_findings_without_mutating():
    guard = PiiGuard()
    text = "reach me at jane.doe@example.com"
    findings = guard.scan(text)
    labels = {f.label for f in findings}
    assert "EMAIL" in labels
    # scan does not alter the input
    assert "jane.doe@example.com" in text


def test_clean_text_passes_through_untouched():
    guard = PiiGuard()
    text = "The refund service issues refunds within five business days."
    assert guard.scrub(text) == text
    assert guard.scan(text) == []


def test_disabled_guard_is_a_passthrough():
    guard = PiiGuard(enabled=False)
    text = "jane.doe@example.com"
    assert guard.scrub(text) == text
    assert guard.scan(text) == []


def test_scan_and_scrub_returns_full_result():
    result = PiiGuard().scan_and_scrub("SSN 123-45-6789")
    assert result.has_pii and result.finding_count == 1
    assert result.original == "SSN 123-45-6789"
    assert "[REDACTED]" in result.scrubbed


# -- I/O wiring in PhaseAgent.complete ----------------------------------------------------------


class _CapturingLlm:
    """Records the messages/system it was called with, so a test can assert what left the boundary."""

    provider_name = "capture"
    model = "capture-1"

    def __init__(self, reply: str = "ok") -> None:
        self._reply = reply
        self.seen_messages: list[Message] = []
        self.seen_system: str | None = None

    async def complete(
        self,
        messages: list[Message],
        system: str | None = None,
        tools: list[ToolDefinition] | None = None,
        max_tokens: int = 4096,
        temperature: float = 0.7,
    ) -> CompletionResult:
        self.seen_messages = messages
        self.seen_system = system
        return CompletionResult(
            content=self._reply, input_tokens=0, output_tokens=0, model=self.model,
            provider=self.provider_name,
        )

    async def stream(  # pragma: no cover - unused by these tests
        self, messages: list[Message], system: str | None = None,
        max_tokens: int = 4096, temperature: float = 0.7,
    ) -> AsyncIterator[str]:
        yield self._reply


class _BareAgent(PhaseAgent):
    """Minimal concrete PhaseAgent — only ``complete`` is exercised here."""

    name = "bare"

    def decide(self, ctx, tools):  # pragma: no cover - not used by these tests
        raise NotImplementedError


def test_complete_scrubs_outgoing_pii_before_the_model_sees_it():
    llm = _CapturingLlm(reply="ok")
    agent = _BareAgent(llm)
    agent.complete(
        [Message(role="user", content="Summarise for jane.doe@example.com please")],
        system="You may email admin@corp.com for escalation.",
    )
    # The model receives redacted content — raw PII never crosses the boundary.
    assert "jane.doe@example.com" not in llm.seen_messages[0].content
    assert "[REDACTED]" in llm.seen_messages[0].content
    assert llm.seen_system is not None and "admin@corp.com" not in llm.seen_system


def test_complete_returns_incoming_content_intact():
    # Incoming completions are scanned/logged but NOT redacted — the artifact body is preserved.
    body = "The API key sk-live-ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789 was rotated."
    agent = _BareAgent(_CapturingLlm(reply=body))
    assert agent.complete([Message(role="user", content="clean prompt")]) == body
