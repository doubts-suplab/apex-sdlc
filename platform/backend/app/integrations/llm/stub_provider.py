"""StubLLMProvider — a deterministic, offline LLM provider.

Satisfies the apex ``LLMProvider`` protocol (and, by identical shape, the harness ``LlmPort``) so the
reference journey and the demo run with **no** API key. It returns a short, phase-aware one-liner by
matching the persona hint in the prompt, so the generated rationales read sensibly without a network
call. Real deployments select anthropic/ollama/groq/huggingface instead (see ``factory.py``).
"""

from __future__ import annotations

from collections.abc import AsyncIterator

from app.integrations.llm.base import CompletionResult, Message, ToolDefinition

# Persona hint (as it appears in an agent's prompt) → canned one-line rationale.
_REPLIES: dict[str, str] = {
    "business analyst": "Scope is clear enough to draft stories; four gaps remain for the BA to resolve.",
    "solution architect": "A standalone hexagonal service with idempotent refunds and an outbox to the ledger is the sound choice.",
    "senior reviewer": "The change works but has a SQL-injection risk and PII in logs — an advisory review is warranted.",
    "qa lead": "The plan covers the happy path and all rejection branches; add the missing idempotency test.",
    "release engineer": "Checks are green and the rollback is safe; the release can proceed.",
    "technical writer": "The API reference and onboarding guide are ready for a human to publish.",
    "compliance": "Two golden-rule breaches at moderate risk — material but not certain; a human should decide.",
}
_DEFAULT_REPLY = "Assessment complete; see the generated artifacts and the harness decision."


class StubLLMProvider:
    """Returns a deterministic, phase-aware completion; no network, no key."""

    def __init__(self, model: str = "stub-1") -> None:
        self.provider_name = "stub"
        self.model = model

    def _reply_for(self, messages: list[Message], system: str | None) -> str:
        haystack = " ".join([system or ""] + [m.content for m in messages]).lower()
        for hint, reply in _REPLIES.items():
            if hint in haystack:
                return reply
        return _DEFAULT_REPLY

    async def complete(
        self,
        messages: list[Message],
        system: str | None = None,
        tools: list[ToolDefinition] | None = None,
        max_tokens: int = 4096,
        temperature: float = 0.7,
    ) -> CompletionResult:
        reply = self._reply_for(messages, system)
        return CompletionResult(
            content=reply,
            input_tokens=sum(len(m.content.split()) for m in messages),
            output_tokens=len(reply.split()),
            model=self.model,
            provider=self.provider_name,
        )

    async def stream(
        self,
        messages: list[Message],
        system: str | None = None,
        max_tokens: int = 4096,
        temperature: float = 0.7,
    ) -> AsyncIterator[str]:
        for token in self._reply_for(messages, system).split():
            yield token + " "
