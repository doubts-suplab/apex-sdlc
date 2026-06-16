from __future__ import annotations

from typing import Annotated

from fastapi import Depends

from app.core.config import get_settings
from app.integrations.llm.base import LLMProvider


def get_llm_provider() -> LLMProvider:
    """
    Instantiate and return the configured LLM provider.

    Reads LLM_PROVIDER from settings and performs a lazy import of the
    corresponding SDK so that uninstalled providers do not cause import errors.
    """
    settings = get_settings()
    provider = settings.LLM_PROVIDER.lower()

    if provider == "anthropic":
        from app.integrations.llm.anthropic_provider import AnthropicProvider

        return AnthropicProvider(
            model=settings.LLM_MODEL or "claude-opus-4-5",
            api_key=settings.ANTHROPIC_API_KEY,
        )
    elif provider == "ollama":
        from app.integrations.llm.ollama_provider import OllamaProvider

        return OllamaProvider(
            model=settings.LLM_MODEL or "llama3.2",
            base_url=settings.OLLAMA_BASE_URL,
        )
    elif provider == "groq":
        from app.integrations.llm.groq_provider import GroqProvider

        return GroqProvider(
            model=settings.LLM_MODEL or "llama-3.3-70b-versatile",
            api_key=settings.GROQ_API_KEY,
        )
    elif provider == "huggingface":
        from app.integrations.llm.huggingface_provider import HuggingFaceProvider

        return HuggingFaceProvider(
            model=settings.LLM_MODEL or "meta-llama/Meta-Llama-3-8B-Instruct",
            token=settings.HUGGINGFACE_TOKEN,
        )
    else:
        raise ValueError(
            f"Unknown LLM provider: {provider!r}. "
            "Choose: anthropic | ollama | groq | huggingface"
        )


# FastAPI Depends alias — use as a type annotation in route handlers
LLMProviderDep = Annotated[LLMProvider, Depends(get_llm_provider)]
