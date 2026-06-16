from __future__ import annotations

from typing import AsyncIterator

from app.integrations.llm.base import CompletionResult, LLMProvider, Message, ToolCall, ToolDefinition
from app.core.logging import get_logger

logger = get_logger(__name__)

_TOOL_USE_NOT_SUPPORTED = (
    "Tool use not supported by HuggingFace provider — "
    "switch to anthropic or groq provider for agent tool use"
)


class HuggingFaceProvider:
    """LLM provider backed by HuggingFace Inference API."""

    provider_name: str = "huggingface"

    def __init__(self, model: str, token: str) -> None:
        # Lazy import — huggingface_hub only required when this provider is active
        from huggingface_hub import AsyncInferenceClient  # type: ignore[import]

        self.model = model
        self._client = AsyncInferenceClient(model=model, token=token)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _to_hf_messages(messages: list[Message], system: str | None) -> list[dict]:
        result: list[dict] = []
        has_system = any(m.role == "system" for m in messages)
        if system and not has_system:
            result.append({"role": "system", "content": system})
        for m in messages:
            result.append({"role": m.role, "content": m.content})
        return result

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
        """Generate a completion via HuggingFace Inference API."""
        if tools:
            raise NotImplementedError(_TOOL_USE_NOT_SUPPORTED)

        hf_messages = self._to_hf_messages(messages, system)

        response = await self._client.chat_completion(
            messages=hf_messages,
            model=self.model,
            max_tokens=max_tokens,
            temperature=temperature,
            stream=False,
        )

        content = response.choices[0].message.content or ""
        input_tokens = getattr(response.usage, "prompt_tokens", 0) if response.usage else 0
        output_tokens = (
            getattr(response.usage, "completion_tokens", 0) if response.usage else 0
        )

        logger.debug(
            "huggingface.complete",
            model=self.model,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
        )

        return CompletionResult(
            content=content,
            tool_calls=[],
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
        """Stream text tokens from HuggingFace Inference API."""
        hf_messages = self._to_hf_messages(messages, system)

        response = await self._client.chat_completion(
            messages=hf_messages,
            model=self.model,
            max_tokens=max_tokens,
            temperature=temperature,
            stream=True,
        )

        async for chunk in response:
            delta = chunk.choices[0].delta if chunk.choices else None
            if delta and delta.content:
                yield delta.content


# Structural check
_: LLMProvider = HuggingFaceProvider.__new__(HuggingFaceProvider)  # type: ignore[assignment]
