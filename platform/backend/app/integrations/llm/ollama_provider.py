from __future__ import annotations

import json
from typing import AsyncIterator

import httpx

from app.integrations.llm.base import CompletionResult, LLMProvider, Message, ToolCall, ToolDefinition
from app.core.logging import get_logger

logger = get_logger(__name__)

_TOOL_USE_NOT_SUPPORTED = (
    "Tool use not supported by Ollama provider — "
    "switch to anthropic or groq provider for agent tool use"
)


class OllamaProvider:
    """LLM provider backed by a local Ollama instance via its HTTP API."""

    provider_name: str = "ollama"

    def __init__(self, model: str, base_url: str = "http://localhost:11434") -> None:
        self.model = model
        self._base_url = base_url.rstrip("/")

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _to_ollama_messages(messages: list[Message]) -> list[dict]:
        return [{"role": m.role, "content": m.content} for m in messages]

    # ------------------------------------------------------------------
    # Protocol implementation
    # ------------------------------------------------------------------

    async def complete(
        self,
        messages: list[Message],
        system: str | None = None,
        tools: list[ToolDefinition] | None = None,
        max_tokens: int = 4096,
        temperature: float = 0.7,
    ) -> CompletionResult:
        """Generate a non-streaming completion via the Ollama /api/chat endpoint."""
        if tools:
            raise NotImplementedError(_TOOL_USE_NOT_SUPPORTED)

        ollama_messages = self._to_ollama_messages(messages)
        # Inject system prompt as a leading system message if provided
        if system:
            ollama_messages = [{"role": "system", "content": system}] + ollama_messages

        payload = {
            "model": self.model,
            "messages": ollama_messages,
            "stream": False,
            "options": {
                "temperature": temperature,
                "num_predict": max_tokens,
            },
        }

        async with httpx.AsyncClient(timeout=120.0) as client:
            response = await client.post(f"{self._base_url}/api/chat", json=payload)
            response.raise_for_status()
            data = response.json()

        content = data.get("message", {}).get("content", "")
        prompt_tokens = data.get("prompt_eval_count", 0)
        eval_tokens = data.get("eval_count", 0)

        logger.debug(
            "ollama.complete",
            model=self.model,
            prompt_tokens=prompt_tokens,
            eval_tokens=eval_tokens,
        )

        return CompletionResult(
            content=content,
            tool_calls=[],
            input_tokens=prompt_tokens,
            output_tokens=eval_tokens,
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
        """Stream tokens from the Ollama /api/chat endpoint (NDJSON)."""
        ollama_messages = self._to_ollama_messages(messages)
        if system:
            ollama_messages = [{"role": "system", "content": system}] + ollama_messages

        payload = {
            "model": self.model,
            "messages": ollama_messages,
            "stream": True,
            "options": {
                "temperature": temperature,
                "num_predict": max_tokens,
            },
        }

        async with httpx.AsyncClient(timeout=300.0) as client:
            async with client.stream("POST", f"{self._base_url}/api/chat", json=payload) as resp:
                resp.raise_for_status()
                async for raw_line in resp.aiter_lines():
                    if not raw_line.strip():
                        continue
                    try:
                        line = json.loads(raw_line)
                    except json.JSONDecodeError:
                        continue
                    token = line.get("message", {}).get("content", "")
                    if token:
                        yield token
                    if line.get("done"):
                        break


# Structural check
_: LLMProvider = OllamaProvider.__new__(OllamaProvider)  # type: ignore[assignment]
