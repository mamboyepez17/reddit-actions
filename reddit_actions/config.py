"""Settings for Reddit Actions via environment variables and optional .env file."""

from __future__ import annotations

from functools import lru_cache

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Runtime configuration. `REDDIT_USER_AGENT` is required."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    reddit_user_agent: str = Field(
        ...,
        description="Descriptive User-Agent required by Reddit for non-official clients.",
    )
    reddit_min_delay: float = Field(
        default=1.5,
        ge=0.0,
        description="Minimum seconds between HTTP requests.",
    )
    reddit_max_retries: int = Field(
        default=3,
        ge=0,
        description="Max retries on 429/403/network errors.",
    )
    reddit_timeout: float = Field(
        default=30.0,
        gt=0.0,
        description="HTTP timeout in seconds.",
    )
    reddit_base_url: str = Field(
        default="https://www.reddit.com",
        description="Base URL for public JSON endpoints.",
    )

    @field_validator("reddit_user_agent")
    @classmethod
    def _user_agent_not_blank(cls, value: str) -> str:
        cleaned = value.strip()
        if not cleaned:
            raise ValueError(
                "REDDIT_USER_AGENT is required and cannot be blank. "
                "Use a descriptive agent, e.g. reddit-actions/0.1 (by u/name; research)."
            )
        return cleaned

    @field_validator("reddit_base_url")
    @classmethod
    def _strip_trailing_slash(cls, value: str) -> str:
        return value.rstrip("/")


@lru_cache
def get_settings() -> Settings:
    """Return cached settings loaded from env/.env."""
    return Settings()


def reset_settings_cache() -> None:
    """Clear the settings cache (useful in tests after env changes)."""
    get_settings.cache_clear()
