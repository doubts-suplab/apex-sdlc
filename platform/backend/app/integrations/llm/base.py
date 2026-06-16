from __future__ import annotations

from dataclasses import dataclass, field
from typing import AsyncIterator, Protocol, runtime_checkable


@dataclass
class Message:
    """A single chat message."""

    role: str  # "system" | "user" | "assistant"
    content: str


@dataclass
class ToolDefinition:
    """Describes a callable tool that can be offered to an LLM."""

    name: str
    description: str
    parameters: dict  # JSON Schema object


@dataclass
class ToolCall:
    """A tool invocation requested by the LLM."""

    name: str
    arguments: dict
    id: str = ""


@dataclass
class CompletionResult:
    """Unified response from any LLM provider."""

    content: str
    tool_calls: list[ToolCall] = field(default_factory=list)
    input_tokens: int = 0
    output_tokens: int = 0
    model: str = ""
    provider: str = ""


@runtime_checkable
class LLMProvider(Protocol):
    """Protocol that every LLM provider adapter must satisfy."""

    provider_name: str
    model: str

    async def complete(
        self,
        messages: list[Message],
        system: str | None = None,
        tools: list[ToolDefinition] | None = None,
        max_tokens: int = 4096,
        temperature: float = 0.7,
    ) -> CompletionResult:
        """Generate a single completion and return the full result."""
        ...

    async def stream(
        self,
        messages: list[Message],
        system: str | None = None,
        max_tokens: int = 4096,
        temperature: float = 0.7,
    ) -> AsyncIterator[str]:
        """Stream text tokens as they are generated."""
        ...
