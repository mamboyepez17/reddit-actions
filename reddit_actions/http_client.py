"""HTTP client for Reddit public JSON: User-Agent, polite delay, retries."""

from __future__ import annotations

import logging
import time
from types import TracebackType
from typing import Any

import httpx

from .config import Settings, get_settings

logger = logging.getLogger(__name__)

__all__ = [
    "RedditError",
    "RateLimitError",
    "AuthError",
    "NotFoundError",
    "RedditHttpClient",
]


class RedditError(Exception):
    """Base error for Reddit Actions HTTP operations."""


class RateLimitError(RedditError):
    """Raised when Reddit rate-limits the client (HTTP 429) after retries."""


class AuthError(RedditError):
    """Raised on 401/403 (blocked or unauthorized) after retries."""


class NotFoundError(RedditError):
    """Raised when the requested Reddit resource does not exist (HTTP 404)."""


class RedditHttpClient:
    """Thin sync client over Reddit public JSON endpoints.

    Responsibilities:
    - Always send a descriptive User-Agent
    - Enforce a minimum delay between requests
    - Retry with backoff on 429/403 and network errors
    - Map HTTP failures to structured exceptions (never crash callers silently)
    """

    def __init__(
        self,
        settings: Settings | None = None,
        *,
        transport: httpx.BaseTransport | None = None,
        sleep: Any = time.sleep,
        monotonic: Any = time.monotonic,
    ) -> None:
        self.settings = settings or get_settings()
        self._sleep = sleep
        self._monotonic = monotonic
        self._last_request_at: float | None = None
        self._client = httpx.Client(
            base_url=self.settings.reddit_base_url,
            headers={
                "User-Agent": self.settings.reddit_user_agent,
                "Accept": "application/json",
            },
            timeout=self.settings.reddit_timeout,
            follow_redirects=True,
            transport=transport,
        )

    @property
    def user_agent(self) -> str:
        return self.settings.reddit_user_agent

    def get_json(self, path: str, params: dict[str, Any] | None = None) -> Any:
        """GET a Reddit `.json` path and return parsed JSON.

        Never raises bare httpx errors: failures become RedditError subclasses
        after polite retries.
        """
        max_attempts = self.settings.reddit_max_retries + 1
        last_error: Exception | None = None

        for attempt in range(max_attempts):
            self._throttle()
            try:
                response = self._client.get(path, params=params)
            except httpx.HTTPError as exc:
                last_error = exc
                logger.warning("Network error on %s (attempt %s): %s", path, attempt + 1, exc)
                if attempt >= self.settings.reddit_max_retries:
                    break
                self._backoff(attempt)
                continue

            status = response.status_code
            if status == 200:
                self._last_request_at = self._monotonic()
                return response.json()

            if status == 404:
                raise NotFoundError(f"Not found: {path}")

            if status == 429:
                if attempt >= self.settings.reddit_max_retries:
                    raise RateLimitError(
                        f"Rate limited by Reddit after {max_attempts} attempts: {path}"
                    )
                delay = self._retry_after_seconds(response)
                logger.warning("429 on %s; sleeping %.2fs (attempt %s)", path, delay, attempt + 1)
                self._sleep(delay)
                continue

            if status in (401, 403):
                if attempt >= self.settings.reddit_max_retries:
                    raise AuthError(
                        f"Blocked or unauthorized ({status}) after {max_attempts} attempts: {path}"
                    )
                logger.warning("%s on %s (attempt %s)", status, path, attempt + 1)
                self._backoff(attempt)
                continue

            if status >= 500:
                if attempt >= self.settings.reddit_max_retries:
                    raise RedditError(f"Server error {status} for {path}")
                self._backoff(attempt)
                continue

            raise RedditError(f"Unexpected HTTP {status} for {path}")

        raise RedditError(f"Request failed for {path}") from last_error

    def close(self) -> None:
        self._client.close()

    def __enter__(self) -> RedditHttpClient:
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: TracebackType | None,
    ) -> None:
        self.close()

    def _throttle(self) -> None:
        """Sleep so consecutive requests are at least `reddit_min_delay` apart."""
        if self._last_request_at is None:
            return
        elapsed = self._monotonic() - self._last_request_at
        wait = self.settings.reddit_min_delay - elapsed
        if wait > 0:
            self._sleep(wait)

    def _backoff(self, attempt: int) -> None:
        base = max(self.settings.reddit_min_delay, 0.5)
        delay = base * (2**attempt)
        self._sleep(min(delay, 30.0))

    @staticmethod
    def _retry_after_seconds(response: httpx.Response) -> float:
        raw = response.headers.get("Retry-After")
        if raw is None:
            return 2.0
        try:
            return max(float(raw), 0.0)
        except ValueError:
            return 2.0
