"""Tests for the LLM provider factory.

Verifies that get_llm_provider() returns the correct provider class for each
LLM_PROVIDER setting, and that an unknown provider raises ValueError.
Provider constructors are mocked so no real SDKs or network calls are needed.
"""
from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_settings(**overrides):
    """Return a minimal Settings-like object for the factory."""
    defaults = {
        "LLM_PROVIDER": "anthropic",
        "LLM_MODEL": "",
        "ANTHROPIC_API_KEY": "sk-ant-test",
        "OLLAMA_BASE_URL": "http://localhost:11434",
        "GROQ_API_KEY": "gsk_test",
        "HUGGINGFACE_TOKEN": "hf_test",
    }
    defaults.update(overrides)
    obj = MagicMock()
    for k, v in defaults.items():
        setattr(obj, k, v)
    return obj


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


def test_factory_returns_anthropic_provider():
    """LLM_PROVIDER=anthropic → AnthropicProvider instance."""
    settings = _make_settings(LLM_PROVIDER="anthropic", ANTHROPIC_API_KEY="sk-ant-test")

    with (
        patch("app.integrations.llm.factory.get_settings", return_value=settings),
        patch(
            "app.integrations.llm.anthropic_provider.AnthropicProvider.__init__",
            return_value=None,
        ) as mock_init,
    ):
        from app.integrations.llm.anthropic_provider import AnthropicProvider
        from app.integrations.llm.factory import get_llm_provider

        provider = get_llm_provider()
        assert isinstance(provider, AnthropicProvider)
        mock_init.assert_called_once_with(
            model="claude-opus-4-5",  # default when LLM_MODEL is empty
            api_key="sk-ant-test",
        )


def test_factory_uses_explicit_model_override():
    """LLM_MODEL override is passed to the provider constructor."""
    settings = _make_settings(
        LLM_PROVIDER="anthropic",
        LLM_MODEL="claude-haiku-4-5",
        ANTHROPIC_API_KEY="sk-ant-test",
    )

    with (
        patch("app.integrations.llm.factory.get_settings", return_value=settings),
        patch(
            "app.integrations.llm.anthropic_provider.AnthropicProvider.__init__",
            return_value=None,
        ) as mock_init,
    ):
        from app.integrations.llm.factory import get_llm_provider

        get_llm_provider()
        mock_init.assert_called_once_with(model="claude-haiku-4-5", api_key="sk-ant-test")


def test_factory_returns_ollama_provider():
    """LLM_PROVIDER=ollama → OllamaProvider instance."""
    settings = _make_settings(
        LLM_PROVIDER="ollama",
        OLLAMA_BASE_URL="http://localhost:11434",
    )

    with (
        patch("app.integrations.llm.factory.get_settings", return_value=settings),
        patch(
            "app.integrations.llm.ollama_provider.OllamaProvider.__init__",
            return_value=None,
        ) as mock_init,
    ):
        from app.integrations.llm.factory import get_llm_provider
        from app.integrations.llm.ollama_provider import OllamaProvider

        provider = get_llm_provider()
        assert isinstance(provider, OllamaProvider)
        mock_init.assert_called_once_with(
            model="llama3.2",
            base_url="http://localhost:11434",
        )


def test_factory_returns_groq_provider():
    """LLM_PROVIDER=groq → GroqProvider instance."""
    settings = _make_settings(LLM_PROVIDER="groq", GROQ_API_KEY="gsk_test")

    with (
        patch("app.integrations.llm.factory.get_settings", return_value=settings),
        patch(
            "app.integrations.llm.groq_provider.GroqProvider.__init__",
            return_value=None,
        ) as mock_init,
    ):
        from app.integrations.llm.factory import get_llm_provider
        from app.integrations.llm.groq_provider import GroqProvider

        provider = get_llm_provider()
        assert isinstance(provider, GroqProvider)
        mock_init.assert_called_once_with(
            model="llama-3.3-70b-versatile",
            api_key="gsk_test",
        )


def test_factory_returns_huggingface_provider():
    """LLM_PROVIDER=huggingface → HuggingFaceProvider instance."""
    settings = _make_settings(LLM_PROVIDER="huggingface", HUGGINGFACE_TOKEN="hf_test")

    with (
        patch("app.integrations.llm.factory.get_settings", return_value=settings),
        patch(
            "app.integrations.llm.huggingface_provider.HuggingFaceProvider.__init__",
            return_value=None,
        ) as mock_init,
    ):
        from app.integrations.llm.factory import get_llm_provider
        from app.integrations.llm.huggingface_provider import HuggingFaceProvider

        provider = get_llm_provider()
        assert isinstance(provider, HuggingFaceProvider)
        mock_init.assert_called_once_with(
            model="meta-llama/Meta-Llama-3-8B-Instruct",
            token="hf_test",
        )


def test_factory_raises_for_unknown_provider():
    """Unknown LLM_PROVIDER value raises ValueError with a helpful message."""
    settings = _make_settings(LLM_PROVIDER="openai")

    with patch("app.integrations.llm.factory.get_settings", return_value=settings):
        from app.integrations.llm.factory import get_llm_provider

        with pytest.raises(ValueError, match="Unknown LLM provider"):
            get_llm_provider()


def test_factory_provider_name_is_case_insensitive():
    """Provider matching is case-insensitive (ANTHROPIC → anthropic)."""
    settings = _make_settings(LLM_PROVIDER="ANTHROPIC", ANTHROPIC_API_KEY="sk-ant-test")

    with (
        patch("app.integrations.llm.factory.get_settings", return_value=settings),
        patch(
            "app.integrations.llm.anthropic_provider.AnthropicProvider.__init__",
            return_value=None,
        ),
    ):
        from app.integrations.llm.anthropic_provider import AnthropicProvider
        from app.integrations.llm.factory import get_llm_provider

        provider = get_llm_provider()
        assert isinstance(provider, AnthropicProvider)
