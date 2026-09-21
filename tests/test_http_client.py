"""Tests for RedditHttpClient (mocked HTTP, no real Reddit)."""

from __future__ import annotations

import httpx
import pytest
import respx
from reddit_actions.http_client import (
    AuthError,
    NotFoundError,
    RateLimitError,
    RedditError,
    RedditHttpClient,
)

BASE = "https://www.reddit.com"


@pytest.fixture
def client(test_settings, no_sleep):
    return RedditHttpClient(test_settings, sleep=no_sleep, monotonic=lambda: 0.0)


@respx.mock
def test_get_json_success_sends_user_agent(client):
    route = respx.get(f"{BASE}/search.json").mock(
        return_value=httpx.Response(200, json={"data": {"children": []}})
    )
    data = client.get_json("/search.json", params={"q": "python", "limit": 10})
    assert data == {"data": {"children": []}}
    assert route.called
    request = route.calls.last.request
    assert request.headers["User-Agent"] == client.user_agent
    assert "q=python" in str(request.url)


@respx.mock
def test_context_manager_closes(test_settings, no_sleep):
    respx.get(f"{BASE}/r/python/hot.json").mock(
        return_value=httpx.Response(200, json={"data": {"children": []}})
    )
    with RedditHttpClient(test_settings, sleep=no_sleep, monotonic=lambda: 0.0) as client:
        assert client.get_json("/r/python/hot.json") == {"data": {"children": []}}


@respx.mock
def test_404_raises_not_found(client):
    respx.get(f"{BASE}/comments/abc.json").mock(return_value=httpx.Response(404))
    with pytest.raises(NotFoundError):
        client.get_json("/comments/abc.json")


@respx.mock
def test_429_retries_then_rate_limit_error(test_settings, no_sleep):
    respx.get(f"{BASE}/search.json").mock(
        return_value=httpx.Response(429, headers={"Retry-After": "0.1"})
    )
    client = RedditHttpClient(test_settings, sleep=no_sleep, monotonic=lambda: 0.0)
    with pytest.raises(RateLimitError):
        client.get_json("/search.json")
    # initial + reddit_max_retries (2)
    assert respx.calls.call_count == 3
    assert any(c >= 0.1 for c in no_sleep.calls)


@respx.mock
def test_429_then_success_uses_retry_after(test_settings, no_sleep):
    route = respx.get(f"{BASE}/search.json")
    route.side_effect = [
        httpx.Response(429, headers={"Retry-After": "0.2"}),
        httpx.Response(200, json={"ok": True}),
    ]
    client = RedditHttpClient(test_settings, sleep=no_sleep, monotonic=lambda: 0.0)
    assert client.get_json("/search.json") == {"ok": True}
    assert 0.2 in no_sleep.calls


@respx.mock
def test_403_raises_auth_error_after_retries(test_settings, no_sleep):
    respx.get(f"{BASE}/search.json").mock(return_value=httpx.Response(403))
    client = RedditHttpClient(test_settings, sleep=no_sleep, monotonic=lambda: 0.0)
    with pytest.raises(AuthError):
        client.get_json("/search.json")
    assert respx.calls.call_count == 3


@respx.mock
def test_network_error_raises_reddit_error_after_retries(test_settings, no_sleep):
    respx.get(f"{BASE}/search.json").mock(side_effect=httpx.ConnectError("boom"))
    client = RedditHttpClient(test_settings, sleep=no_sleep, monotonic=lambda: 0.0)
    with pytest.raises(RedditError):
        client.get_json("/search.json")


@respx.mock
def test_unexpected_4xx_raises_reddit_error(client):
    respx.get(f"{BASE}/search.json").mock(
        return_value=httpx.Response(418, text="teapot")
    )
    with pytest.raises(RedditError):
        client.get_json("/search.json")


@respx.mock
def test_polite_min_delay_between_requests(test_settings):
    """Second successful call must sleep ~min_delay when no time has passed."""
    sleeps: list[float] = []
    clock = {"t": 0.0}

    def fake_sleep(seconds: float) -> None:
        sleeps.append(seconds)
        clock["t"] += seconds

    respx.get(f"{BASE}/a.json").mock(return_value=httpx.Response(200, json={"n": 1}))
    respx.get(f"{BASE}/b.json").mock(return_value=httpx.Response(200, json={"n": 2}))

    settings = test_settings.model_copy(update={"reddit_min_delay": 1.5})
    client = RedditHttpClient(
        settings,
        sleep=fake_sleep,
        monotonic=lambda: clock["t"],
    )
    client.get_json("/a.json")
    client.get_json("/b.json")
    assert sleeps and sleeps[0] == pytest.approx(1.5)


@respx.mock
def test_retry_after_defaults_when_header_invalid(client, no_sleep):
    respx.get(f"{BASE}/search.json").mock(
        return_value=httpx.Response(429, headers={"Retry-After": "not-a-number"})
    )
    with pytest.raises(RateLimitError):
        client.get_json("/search.json")
    assert 2.0 in no_sleep.calls
