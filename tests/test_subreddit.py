"""Tests for get_subreddit_posts scraper (mocked HTTP)."""

from __future__ import annotations

import httpx
import pytest
import respx
from reddit_actions import NotFoundError, get_subreddit_posts
from reddit_actions.http_client import RedditHttpClient
from reddit_actions.scrapers.subreddit import (
    get_subreddit_posts as get_subreddit_posts_direct,
)

BASE = "https://www.reddit.com"


@pytest.fixture
def http(test_settings, no_sleep):
    return RedditHttpClient(test_settings, sleep=no_sleep, monotonic=lambda: 0.0)


def _listing(*items: dict) -> dict:
    return {"kind": "Listing", "data": {"children": list(items)}}


def _post(pid: str, title: str, score: int = 1) -> dict:
    return {
        "kind": "t3",
        "data": {
            "id": pid,
            "title": title,
            "subreddit": "python",
            "author": "alice",
            "score": score,
            "upvote_ratio": 0.9,
            "num_comments": 2,
            "permalink": f"/r/python/comments/{pid}/{title.lower()}/",
            "url": "https://example.com",
            "created_utc": 1_700_000_000.0,
            "over_18": False,
        },
    }


@respx.mock
def test_hot_listing_path_and_params(http):
    route = respx.get(f"{BASE}/r/python/hot.json").mock(
        return_value=httpx.Response(200, json=_listing(_post("a", "Hot A"), _post("b", "Hot B")))
    )
    posts = get_subreddit_posts("python", sort="hot", limit=10, client=http)
    assert [p.id for p in posts] == ["a", "b"]
    url = str(route.calls.last.request.url)
    assert "limit=10" in url
    assert "raw_json=1" in url


@respx.mock
def test_new_and_top_sorts_build_expected_paths(http):
    respx.get(f"{BASE}/r/python/new.json").mock(
        return_value=httpx.Response(200, json=_listing(_post("n1", "New")))
    )
    respx.get(f"{BASE}/r/python/top.json").mock(
        return_value=httpx.Response(200, json=_listing(_post("t1", "Top")))
    )
    new_posts = get_subreddit_posts("python", sort="new", client=http)
    top_posts = get_subreddit_posts("python", sort="top", client=http)
    assert new_posts[0].id == "n1"
    assert top_posts[0].id == "t1"
    paths = [str(c.request.url) for c in respx.calls]
    assert any("/r/python/new.json" in p for p in paths)
    assert any("/r/python/top.json" in p for p in paths)


@respx.mock
def test_strips_r_prefix(http):
    route = respx.get(f"{BASE}/r/learnpython/hot.json").mock(
        return_value=httpx.Response(200, json=_listing())
    )
    get_subreddit_posts("r/learnpython", client=http)
    assert route.called


@respx.mock
def test_empty_listing(http):
    respx.get(f"{BASE}/r/python/hot.json").mock(return_value=httpx.Response(200, json=_listing()))
    assert get_subreddit_posts("python", client=http) == []


@respx.mock
def test_extra_params_forwarded(http):
    route = respx.get(f"{BASE}/r/python/top.json").mock(
        return_value=httpx.Response(200, json=_listing())
    )
    get_subreddit_posts("python", sort="top", extra_params={"t": "week"}, client=http)
    assert "t=week" in str(route.calls.last.request.url)


@respx.mock
def test_404_subreddit(http):
    respx.get(f"{BASE}/r/doesnotexistxyz/hot.json").mock(return_value=httpx.Response(404))
    with pytest.raises(NotFoundError):
        get_subreddit_posts("doesnotexistxyz", client=http)


def test_invalid_sort_and_input(http):
    with pytest.raises(ValueError):
        get_subreddit_posts("python", sort="nope", client=http)
    with pytest.raises(ValueError):
        get_subreddit_posts("", client=http)
    with pytest.raises(ValueError):
        get_subreddit_posts("r/", client=http)
    with pytest.raises(ValueError):
        get_subreddit_posts("python", limit=0, client=http)


@respx.mock
def test_own_client_from_settings(test_settings):
    respx.get(f"{BASE}/r/python/hot.json").mock(
        return_value=httpx.Response(200, json=_listing(_post("z", "Zed")))
    )
    posts = get_subreddit_posts_direct("python", settings=test_settings)
    assert posts[0].id == "z"


def test_exported_from_package():
    from reddit_actions import get_subreddit_posts as exported
    from reddit_actions.scrapers import get_subreddit_posts as from_scrapers

    assert exported is get_subreddit_posts_direct
    assert from_scrapers is get_subreddit_posts_direct
