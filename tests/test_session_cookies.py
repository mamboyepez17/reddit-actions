"""Tests for session-cookie auth settings and HTTP client headers."""

from __future__ import annotations

import httpx
import pytest
import respx
from reddit_actions.config import Settings, reset_settings_cache
from reddit_actions.http_client import RedditHttpClient

BASE = "https://www.reddit.com"

UA = "reddit-actions-tests/0.1 (by u/test; research)"


@pytest.fixture
def no_sleep():
    calls: list[float] = []

    def _sleep(seconds: float) -> None:
        calls.append(float(seconds))

    _sleep.calls = calls  # type: ignore[attr-defined]
    return _sleep


def test_settings_build_cookie_header_from_parts():
    s = Settings(
        _env_file=None,
        reddit_user_agent=UA,
        reddit_session_cookie="abc123secret",
        reddit_session_tracker="track999",
        reddit_token_v2="tok456",
    )
    header = s.build_cookie_header()
    assert header == "reddit_session=abc123secret; session_tracker=track999; token_v2=tok456"
    assert s.has_session_auth is True


def test_settings_strips_name_prefix_from_values():
    s = Settings(
        _env_file=None,
        reddit_user_agent=UA,
        reddit_session_cookie="reddit_session=abc123secret",
        reddit_token_v2="token_v2=tok456",
    )
    assert s.reddit_session_cookie == "abc123secret"
    assert s.reddit_token_v2 == "tok456"
    assert s.build_cookie_header() == "reddit_session=abc123secret; token_v2=tok456"


def test_settings_cookie_header_overrides_and_strips_label():
    s = Settings(
        _env_file=None,
        reddit_user_agent=UA,
        reddit_session_cookie="ignored",
        reddit_cookie_header="Cookie: reddit_session=fullheader; token_v2=t2",
    )
    assert s.reddit_cookie_header == "reddit_session=fullheader; token_v2=t2"
    assert s.build_cookie_header() == "reddit_session=fullheader; token_v2=t2"


def test_settings_empty_cookie_strings_are_none():
    s = Settings(
        _env_file=None,
        reddit_user_agent=UA,
        reddit_session_cookie="   ",
        reddit_cookie_header="",
    )
    assert s.reddit_session_cookie is None
    assert s.reddit_cookie_header is None
    assert s.build_cookie_header() is None
    assert s.has_session_auth is False


def test_settings_anonymous_has_no_cookie_header():
    s = Settings(_env_file=None, reddit_user_agent=UA)
    assert s.build_cookie_header() is None
    assert s.has_session_auth is False


@respx.mock
def test_http_client_sends_cookie_header(no_sleep):
    settings = Settings(
        _env_file=None,
        reddit_user_agent=UA,
        reddit_min_delay=0.0,
        reddit_session_cookie="sessionvalue123",
        reddit_token_v2="tokenvalue456",
    )
    route = respx.get(f"{BASE}/search.json").mock(
        return_value=httpx.Response(200, json={"kind": "Listing", "data": {"children": []}})
    )
    client = RedditHttpClient(settings, sleep=no_sleep, monotonic=lambda: 0.0)
    client.get_json("/search.json", params={"q": "test"})
    request = route.calls.last.request
    cookie = request.headers.get("Cookie", "")
    assert "reddit_session=sessionvalue123" in cookie
    assert "token_v2=tokenvalue456" in cookie
    assert request.headers["User-Agent"] == UA


@respx.mock
def test_http_client_no_cookie_when_anonymous(no_sleep):
    settings = Settings(_env_file=None, reddit_user_agent=UA, reddit_min_delay=0.0)
    route = respx.get(f"{BASE}/search.json").mock(
        return_value=httpx.Response(200, json={"kind": "Listing", "data": {"children": []}})
    )
    client = RedditHttpClient(settings, sleep=no_sleep, monotonic=lambda: 0.0)
    client.get_json("/search.json")
    assert "Cookie" not in route.calls.last.request.headers


@respx.mock
def test_http_client_full_cookie_header_from_network_tab(no_sleep):
    settings = Settings(
        _env_file=None,
        reddit_user_agent=UA,
        reddit_min_delay=0.0,
        reddit_cookie_header="reddit_session=aaa; token_v2=bbb; loid=ccc",
    )
    route = respx.get(f"{BASE}/r/python/hot.json").mock(
        return_value=httpx.Response(200, json={"kind": "Listing", "data": {"children": []}})
    )
    client = RedditHttpClient(settings, sleep=no_sleep, monotonic=lambda: 0.0)
    client.get_json("/r/python/hot.json")
    assert route.calls.last.request.headers["Cookie"] == "reddit_session=aaa; token_v2=bbb; loid=ccc"


def test_env_loads_cookie_settings(monkeypatch):
    monkeypatch.setenv("REDDIT_USER_AGENT", UA)
    monkeypatch.setenv("REDDIT_SESSION_COOKIE", "from-env-session")
    monkeypatch.setenv("REDDIT_TOKEN_V2", "from-env-token")
    s = Settings(_env_file=None)
    assert s.build_cookie_header() == "reddit_session=from-env-session; token_v2=from-env-token"
    reset_settings_cache()
