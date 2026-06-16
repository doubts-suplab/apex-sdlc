"""LLM abstraction layer — always import through this package, never from SDKs directly."""

from app.integrations.llm.base import (
    CompletionResult,
    LLMProvider,
    Message,
    ToolCall,
    ToolDefinition,
)
from app.integrations.llm.factory import get_llm_provider

__all__ = [
    "LLMProvider",
    "Message",
    "CompletionResult",
    "ToolDefinition",
    "ToolCall",
    "get_llm_provider",
]
