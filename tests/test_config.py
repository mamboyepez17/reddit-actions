"""Tests for Settings and cache helpers."""

from __future__ import annotations

import pytest
from pydantic import ValidationError
from reddit_actions.config import Settings, get_settings, reset_settings_cache


def test_user_agent_is_required(monkeypatch):
    monkeypatch.delenv("REDDIT_USER_AGENT", raising=False)
    with pytest.raises(ValidationError) as exc:
        Settings(_env_file=None)
    assert "reddit_user_agent" in str(exc.value)


def test_blank_user_agent_rejected():
    with pytest.raises(ValidationError):
        Settings(_env_file=None, reddit_user_agent="   ")


def test_defaults(monkeypatch):
    monkeypatch.setenv("REDDIT_USER_AGENT", "reddit-actions/0.1 (by u/x; research)")
    settings = Settings(_env_file=None)
    assert settings.reddit_min_delay == 1.5
    assert settings.reddit_max_retries == 3
    assert settings.reddit_timeout == 30.0
    assert settings.reddit_base_url == "https://www.reddit.com"


def test_loads_from_env(monkeypatch):
    monkeypatch.setenv("REDDIT_USER_AGENT", "reddit-actions/0.1 (test)")
    monkeypatch.setenv("REDDIT_MIN_DELAY", "0.25")
    monkeypatch.setenv("REDDIT_MAX_RETRIES", "1")
    monkeypatch.setenv("REDDIT_BASE_URL", "https://www.reddit.com/")
    settings = Settings(_env_file=None)
    assert settings.reddit_user_agent == "reddit-actions/0.1 (test)"
    assert settings.reddit_min_delay == 0.25
    assert settings.reddit_max_retries == 1
    assert settings.reddit_base_url == "https://www.reddit.com"


def test_get_settings_cached_then_reset(monkeypatch):
    monkeypatch.setenv("REDDIT_USER_AGENT", "reddit-actions/0.1 (cache-a)")
    reset_settings_cache()
    first = get_settings()
    monkeypatch.setenv("REDDIT_USER_AGENT", "reddit-actions/0.1 (cache-b)")
    second = get_settings()
    assert first.reddit_user_agent == second.reddit_user_agent == "reddit-actions/0.1 (cache-a)"
    reset_settings_cache()
    third = get_settings()
    assert third.reddit_user_agent == "reddit-actions/0.1 (cache-b)"
