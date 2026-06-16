from __future__ import annotations

import json
from typing import AsyncIterator

from app.integrations.llm.base import CompletionResult, LLMProvider, Message, ToolCall, ToolDefinition
from app.core.logging import get_logger

logger = get_logger(__name__)

_GROQ_BASE_URL = "https://api.groq.com/openai/v1"


class GroqProvider:
    """LLM provider backed by the Groq Cloud API (OpenAI-compatible)."""

    provider_name: str = "groq"

    def __init__(self, model: str, api_key: str) -> None:
        # Lazy import — openai SDK only required when this provider is active
        from openai import AsyncOpenAI  # type: ignore[import]

        self.model = model
        self._client = AsyncOpenAI(api_key=api_key, base_url=_GROQ_BASE_URL)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _to_openai_messages(
        messages: list[Message], system: str | None
    ) -> list[dict]:
        """Build OpenAI-format message list, prepending system prompt if needed."""
        result: list[dict] = []
        has_system = any(m.role == "system" for m in messages)

        # Prefer explicit override, fall back to embedded system message
        if system and not has_system:
            result.append({"role": "system", "content": system})

        for m in messages:
            if m.role == "system" and system:
                # Replace embedded system with override
                result.append({"role": "system", "content": system})
            else:
                result.append({"role": m.role, "content": m.content})

        return result

    @staticmethod
    def _to_openai_tools(tools: list[ToolDefinition]) -> list[dict]:
        return [
            {
                "type": "function",
                "function": {
                    "name": t.name,
                    "description": t.description,
                    "parameters": t.parameters,
                },
            }
            for t in tools
        ]

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
        """Generate a non-streaming completion via Groq."""
        kwargs: dict = {
            "model": self.model,
            "messages": self._to_openai_messages(messages, system),
            "max_tokens": max_tokens,
            "temperature": temperature,
        }
        if tools:
            kwargs["tools"] = self._to_openai_tools(tools)
            kwargs["tool_choice"] = "auto"

        response = await self._client.chat.completions.create(**kwargs)

        choice = response.choices[0]
        content = choice.message.content or ""
        tool_calls: list[ToolCall] = []

        if choice.message.tool_calls:
            for tc in choice.message.tool_calls:
                try:
                    args = json.loads(tc.function.arguments)
                except json.JSONDecodeError:
                    args = {"raw": tc.function.arguments}
                tool_calls.append(
                    ToolCall(
                        name=tc.function.name,
                        arguments=args,
                        id=tc.id,
                    )
                )

        input_tokens = response.usage.prompt_tokens if response.usage else 0
        output_tokens = response.usage.completion_tokens if response.usage else 0

        logger.debug(
            "groq.complete",
            model=self.model,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
        )

        return CompletionResult(
            content=content,
            tool_calls=tool_calls,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
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
        """Stream text tokens from Groq."""
        kwargs: dict = {
            "model": self.model,
            "messages": self._to_openai_messages(messages, system),
            "max_tokens": max_tokens,
            "temperature": temperature,
            "stream": True,
        }

        response = await self._client.chat.completions.create(**kwargs)
        async for chunk in response:
            delta = chunk.choices[0].delta if chunk.choices else None
            if delta and delta.content:
                yield delta.content


# Structural check
_: LLMProvider = GroqProvider.__new__(GroqProvider)  # type: ignore[assignment]
