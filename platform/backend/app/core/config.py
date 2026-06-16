from __future__ import annotations

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application configuration loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )

    # Required
    DATABASE_URL: str = Field(..., description="Async PostgreSQL connection URL")
    REDIS_URL: str = Field(..., description="Redis connection URL")
    SECRET_KEY: str = Field(..., description="Secret key for signing tokens")

    # Application
    ENVIRONMENT: str = Field(default="development", description="Runtime environment")
    LOG_LEVEL: str = Field(default="INFO", description="Logging level")
    APP_VERSION: str = Field(default="1.0.0", description="Application version")

    # ------------------------------------------------------------------
    # LLM Provider (flexible — anthropic | ollama | groq | huggingface)
    # ------------------------------------------------------------------
    LLM_PROVIDER: str = Field(default="anthropic", description="Active LLM provider")
    LLM_MODEL: str = Field(default="", description="Model name override (empty = provider default)")

    # Anthropic
    ANTHROPIC_API_KEY: str = Field(default="", description="Anthropic API key")

    # Ollama (local LLMs)
    OLLAMA_BASE_URL: str = Field(default="http://localhost:11434", description="Ollama base URL")

    # Groq
    GROQ_API_KEY: str = Field(default="", description="Groq Cloud API key")

    # HuggingFace
    HUGGINGFACE_TOKEN: str = Field(default="", description="HuggingFace Hub token")

    # ------------------------------------------------------------------
    # GitHub
    # ------------------------------------------------------------------
    GITHUB_TOKEN: str = Field(default="", description="GitHub personal access token")

    # ------------------------------------------------------------------
    # Jira
    # ------------------------------------------------------------------
    JIRA_BASE_URL: str = Field(default="", description="Jira instance base URL")
    JIRA_EMAIL: str = Field(default="", description="Jira service account email")
    JIRA_API_TOKEN: str = Field(default="", description="Jira API token")

    # ------------------------------------------------------------------
    # Rally (CA Agile Central)
    # ------------------------------------------------------------------
    RALLY_BASE_URL: str = Field(
        default="https://rally1.rallydev.com", description="Rally base URL"
    )
    RALLY_API_KEY: str = Field(default="", description="Rally API key")
    RALLY_WORKSPACE_OID: str = Field(default="", description="Rally numeric workspace OID")

    # ------------------------------------------------------------------
    # Confluence
    # ------------------------------------------------------------------
    CONFLUENCE_BASE_URL: str = Field(default="", description="Confluence base URL")
    CONFLUENCE_TOKEN: str = Field(default="", description="Confluence API token")
    CONFLUENCE_EMAIL: str = Field(default="", description="Confluence account email (basic auth)")

    # ------------------------------------------------------------------
    # S3 / Storage
    # ------------------------------------------------------------------
    S3_ARTIFACT_BUCKET: str = Field(default="apex-artifacts-dev", description="S3 bucket for artifacts")
    AWS_REGION: str = Field(default="eu-west-1", description="AWS region")


def get_settings() -> Settings:
    """Return application settings singleton."""
    return Settings()  # type: ignore[call-arg]
