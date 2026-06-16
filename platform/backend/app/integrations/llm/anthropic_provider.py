from __future__ import annotations

from typing import TYPE_CHECKING, AsyncIterator

from app.integrations.llm.base import CompletionResult, LLMProvider, Message, ToolCall, ToolDefinition
from app.core.logging import get_logger

if TYPE_CHECKING:
    pass

logger = get_logger(__name__)


class AnthropicProvider:
    """LLM provider backed by the Anthropic API (Claude models)."""

    provider_name: str = "anthropic"

    def __init__(self, model: str, api_key: str) -> None:
        # Lazy import — only required when this provider is active
        import anthropic  # type: ignore[import]

        self.model = model
        self._client = anthropic.AsyncAnthropic(api_key=api_key)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _to_anthropic_messages(messages: list[Message]) -> list[dict]:
        """Convert Message list to Anthropic message format (excludes system)."""
        return [
            {"role": m.role, "content": m.content}
            for m in messages
            if m.role != "system"
        ]

    @staticmethod
    def _extract_system(messages: list[Message], override: str | None) -> str | None:
        """Return explicit system override, or first system message content, or None."""
        if override is not None:
            return override
        for m in messages:
            if m.role == "system":
                return m.content
        return None

    @staticmethod
    def _to_anthropic_tools(tools: list[ToolDefinition]) -> list[dict]:
        return [
            {
                "name": t.name,
                "description": t.description,
                "input_schema": t.parameters,
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
        """Generate a non-streaming completion."""
        kwargs: dict = {
            "model": self.model,
            "max_tokens": max_tokens,
            "temperature": temperature,
            "messages": self._to_anthropic_messages(messages),
        }

        sys_prompt = self._extract_system(messages, system)
        if sys_prompt:
            kwargs["system"] = sys_prompt

        if tools:
            kwargs["tools"] = self._to_anthropic_tools(tools)

        response = await self._client.messages.create(**kwargs)

        # Extract text content and tool calls
        text_parts: list[str] = []
        tool_calls: list[ToolCall] = []

        for block in response.content:
            if block.type == "text":
                text_parts.append(block.text)
            elif block.type == "tool_use":
                tool_calls.append(
                    ToolCall(
                        name=block.name,
                        arguments=block.input,
                        id=block.id,
                    )
                )

        logger.debug(
            "anthropic.complete",
            model=self.model,
            input_tokens=response.usage.input_tokens,
            output_tokens=response.usage.output_tokens,
        )

        return CompletionResult(
            content="".join(text_parts),
            tool_calls=tool_calls,
            input_tokens=response.usage.input_tokens,
            output_tokens=response.usage.output_tokens,
            model=response.model,
            provider=self.provider_name,
        )

    async def stream(
        self,
        messages: list[Message],
        system: str | None = None,
        max_tokens: int = 4096,
        temperature: float = 0.7,
    ) -> AsyncIterator[str]:
        """Stream text tokens from the Anthropic API."""
        kwargs: dict = {
            "model": self.model,
            "max_tokens": max_tokens,
            "temperature": temperature,
            "messages": self._to_anthropic_messages(messages),
        }

        sys_prompt = self._extract_system(messages, system)
        if sys_prompt:
            kwargs["system"] = sys_prompt

        async with self._client.messages.stream(**kwargs) as stream:
            async for text in stream.text_stream:
                yield text


# Satisfy the Protocol at import time (structural subtyping check)
_: LLMProvider = AnthropicProvider.__new__(AnthropicProvider)  # type: ignore[assignment]
