"""Shared test fixtures: safe defaults, no real network."""

from __future__ import annotations

import os

import pytest

# Ensure a valid UA exists for any code that constructs Settings() without overrides.
os.environ.setdefault(
    "REDDIT_USER_AGENT",
    "reddit-actions-tests/0.1 (by u/test; research)",
)


@pytest.fixture
def test_settings():
    from reddit_actions.config import Settings

    return Settings(
        _env_file=None,
        reddit_user_agent="reddit-actions-tests/0.1 (by u/test; research)",
        reddit_min_delay=0.0,
        reddit_max_retries=2,
        reddit_timeout=5.0,
        reddit_base_url="https://www.reddit.com",
    )


@pytest.fixture
def no_sleep():
    """Record sleep calls without waiting."""
    calls: list[float] = []

    def _sleep(seconds: float) -> None:
        calls.append(float(seconds))

    _sleep.calls = calls  # type: ignore[attr-defined]
    return _sleep
