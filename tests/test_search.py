"""Tests for search_posts scraper (mocked HTTP)."""

from __future__ import annotations

import httpx
import pytest
import respx
from reddit_actions import RateLimitError, search_posts
from reddit_actions.http_client import RedditHttpClient
from reddit_actions.scrapers.search import search_posts as search_posts_direct

BASE = "https://www.reddit.com"


@pytest.fixture
def http(test_settings, no_sleep):
    return RedditHttpClient(test_settings, sleep=no_sleep, monotonic=lambda: 0.0)


def _listing_payload(*titles_and_ids: tuple[str, str]) -> dict:
    children = [
        {"kind": "t3", "data": {"id": pid, "title": title, "subreddit": "python", "score": i}}
        for i, (title, pid) in enumerate(titles_and_ids, start=1)
    ]
    return {"kind": "Listing", "data": {"children": children}}


@respx.mock
def test_search_posts_global_path_and_params(http):
    route = respx.get(f"{BASE}/search.json").mock(
        return_value=httpx.Response(
            200,
            json=_listing_payload(("Hello", "abc"), ("World", "def")),
        )
    )
    posts = search_posts("hello world", limit=10, client=http)
    assert [p.id for p in posts] == ["abc", "def"]
    assert posts[0].title == "Hello"
    assert route.called
    request = route.calls.last.request
    url = str(request.url)
    assert "q=hello" in url
    assert "limit=10" in url
    assert "sort=relevance" in url


@respx.mock
def test_search_posts_subreddit_uses_sub_search_path(http):
    route = respx.get(f"{BASE}/r/cryptocurrency/search.json").mock(
        return_value=httpx.Response(
            200,
            json=_listing_payload(("ETH", "eth1")),
        )
    )
    posts = search_posts("eth", subreddit="r/cryptocurrency", limit=5, client=http)
    assert len(posts) == 1
    assert posts[0].id == "eth1"
    request = route.calls.last.request
    assert "q=eth" in str(request.url)
    assert "limit=5" in str(request.url)


@respx.mock
def test_search_posts_empty_results_return_empty_list(http):
    respx.get(f"{BASE}/search.json").mock(
        return_value=httpx.Response(200, json={"kind": "Listing", "data": {"children": []}})
    )
    assert search_posts("nothing-here", client=http) == []


@respx.mock
def test_search_posts_skips_malformed_items(http):
    payload = {
        "kind": "Listing",
        "data": {
            "children": [
                {"kind": "t3", "data": {}},
                {"kind": "t3", "data": {"id": "ok", "title": "Valid"}},
            ]
        },
    }
    respx.get(f"{BASE}/search.json").mock(return_value=httpx.Response(200, json=payload))
    posts = search_posts("x", client=http)
    assert [p.id for p in posts] == ["ok"]


@respx.mock
def test_search_posts_rate_limit_propagates(test_settings, no_sleep):
    respx.get(f"{BASE}/search.json").mock(return_value=httpx.Response(429, headers={"Retry-After": "0"}))
    client = RedditHttpClient(test_settings, sleep=no_sleep, monotonic=lambda: 0.0)
    with pytest.raises(RateLimitError):
        search_posts("crypto", client=client)


@respx.mock
def test_search_posts_own_client_closes(test_settings, no_sleep, monkeypatch):
    """When no client is injected, search still works via settings."""
    respx.get(f"{BASE}/search.json").mock(
        return_value=httpx.Response(200, json=_listing_payload(("T", "id1")))
    )
    posts = search_posts_direct(
        "t",
        settings=test_settings,
    )
    assert posts[0].id == "id1"


def test_search_posts_validates_input(http):
    with pytest.raises(ValueError):
        search_posts("", client=http)
    with pytest.raises(ValueError):
        search_posts("q", sort="nope", client=http)
    with pytest.raises(ValueError):
        search_posts("q", limit=0, client=http)


@respx.mock
def test_search_posts_sort_forwarded(http):
    route = respx.get(f"{BASE}/search.json").mock(
        return_value=httpx.Response(200, json=_listing_payload(("A", "a1")))
    )
    search_posts("q", sort="top", limit=3, client=http)
    assert "sort=top" in str(route.calls.last.request.url)


@respx.mock
def test_search_posts_exported_from_package():
    from reddit_actions import search_posts as exported

    assert exported is search_posts_direct
