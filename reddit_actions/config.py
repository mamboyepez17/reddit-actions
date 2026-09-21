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
    # Session cookie fallback when anonymous public JSON is blocked (403).
    # Never log these values. Prefer REDDIT_COOKIE_HEADER if you copied the
    # full Cookie request header from DevTools Network.
    reddit_session_cookie: str | None = Field(
        default=None,
        description="Value of the reddit_session cookie (not the whole Cookie header).",
    )
    reddit_session_tracker: str | None = Field(
        default=None,
        description="Optional value of the session_tracker cookie.",
    )
    reddit_token_v2: str | None = Field(
        default=None,
        description="Optional value of the token_v2 cookie.",
    )
    reddit_cookie_header: str | None = Field(
        default=None,
        description="Full Cookie request header string from the browser (overrides individual cookies).",
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

    @field_validator(
        "reddit_session_cookie",
        "reddit_session_tracker",
        "reddit_token_v2",
        "reddit_cookie_header",
        mode="before",
    )
    @classmethod
    def _empty_str_to_none(cls, value: object) -> object:
        if isinstance(value, str) and not value.strip():
            return None
        return value

    @field_validator("reddit_session_cookie", "reddit_session_tracker", "reddit_token_v2")
    @classmethod
    def _strip_cookie_name_prefix(cls, value: str | None) -> str | None:
        """Accept either raw value or 'name=value' from DevTools copy."""
        if value is None:
            return None
        cleaned = value.strip()
        for prefix in ("reddit_session=", "session_tracker=", "token_v2="):
            if cleaned.startswith(prefix):
                cleaned = cleaned[len(prefix) :].strip()
                break
        return cleaned or None

    @field_validator("reddit_cookie_header")
    @classmethod
    def _normalize_cookie_header(cls, value: str | None) -> str | None:
        if value is None:
            return None
        cleaned = value.strip()
        if cleaned.lower().startswith("cookie:"):
            cleaned = cleaned.split(":", 1)[1].strip()
        return cleaned or None

    def build_cookie_header(self) -> str | None:
        """Compose the Cookie header value for HTTP requests, if any."""
        if self.reddit_cookie_header:
            return self.reddit_cookie_header
        parts: list[str] = []
        if self.reddit_session_cookie:
            parts.append(f"reddit_session={self.reddit_session_cookie}")
        if self.reddit_session_tracker:
            parts.append(f"session_tracker={self.reddit_session_tracker}")
        if self.reddit_token_v2:
            parts.append(f"token_v2={self.reddit_token_v2}")
        return "; ".join(parts) if parts else None

    @property
    def has_session_auth(self) -> bool:
        return self.build_cookie_header() is not None


@lru_cache
def get_settings() -> Settings:
    """Return cached settings loaded from env/.env."""
    return Settings()


def reset_settings_cache() -> None:
    """Clear the settings cache (useful in tests after env changes)."""
    get_settings.cache_clear()
