"""Tests for get_comments scraper (mocked HTTP)."""

from __future__ import annotations

import httpx
import pytest
import respx
from reddit_actions import NotFoundError, get_comments
from reddit_actions.http_client import RedditHttpClient
from reddit_actions.scrapers.comments import get_comments as get_comments_direct

BASE = "https://www.reddit.com"


@pytest.fixture
def http(test_settings, no_sleep):
    return RedditHttpClient(test_settings, sleep=no_sleep, monotonic=lambda: 0.0)


def _comment_node(cid: str, body: str = "hi", author: str = "u", parent: str = "t3_post1", replies=None) -> dict:
    data = {
        "id": cid,
        "body": body,
        "author": author,
        "score": 1,
        "parent_id": parent,
        "created_utc": 1_700_000_000.0,
        "controversiality": 0,
        "permalink": f"/r/python/comments/post1/title/{cid}/",
    }
    if replies is not None:
        data["replies"] = replies
    return {"kind": "t1", "data": data}


def _payload(*children: dict) -> list:
    return [
        {
            "kind": "Listing",
            "data": {
                "children": [
                    {
                        "kind": "t3",
                        "data": {"id": "post1", "title": "T", "permalink": "/r/python/comments/post1/title/"},
                    }
                ]
            },
        },
        {"kind": "Listing", "data": {"children": list(children)}},
    ]


@respx.mock
def test_get_comments_success_and_params(http):
    route = respx.get(f"{BASE}/comments/post1.json").mock(
        return_value=httpx.Response(
            200,
            json=_payload(_comment_node("c1"), _comment_node("c2", body="second")),
        )
    )
    comments = get_comments("post1", limit=30, client=http)
    assert [c.id for c in comments] == ["c1", "c2"]
    assert comments[1].body == "second"
    request = route.calls.last.request
    url = str(request.url)
    assert "limit=30" in url
    assert "depth=2" in url
    assert "raw_json=1" in url


@respx.mock
def test_get_comments_strips_t3_prefix(http):
    route = respx.get(f"{BASE}/comments/abc999.json").mock(
        return_value=httpx.Response(200, json=_payload(_comment_node("c1")))
    )
    comments = get_comments("t3_abc999", client=http)
    assert len(comments) == 1
    assert route.called
    assert "/comments/abc999.json" in str(route.calls.last.request.url)


@respx.mock
def test_get_comments_nested_depth(http):
    payload = _payload(
        _comment_node(
            "root",
            replies={
                "kind": "Listing",
                "data": {
                    "children": [
                        _comment_node("child", parent="t1_root"),
                    ]
                },
            },
        )
    )
    respx.get(f"{BASE}/comments/post1.json").mock(return_value=httpx.Response(200, json=payload))
    comments = get_comments("post1", depth=2, client=http)
    by_id = {c.id: c for c in comments}
    assert by_id["root"].depth == 0
    assert by_id["child"].depth == 1


@respx.mock
def test_get_comments_depth_zero_only_toplevel(http):
    payload = _payload(
        _comment_node(
            "root",
            replies={"kind": "Listing", "data": {"children": [_comment_node("child", parent="t1_root")]}},
        )
    )
    respx.get(f"{BASE}/comments/post1.json").mock(return_value=httpx.Response(200, json=payload))
    comments = get_comments("post1", depth=0, client=http)
    assert [c.id for c in comments] == ["root"]


@respx.mock
def test_get_comments_empty_thread(http):
    respx.get(f"{BASE}/comments/post1.json").mock(
        return_value=httpx.Response(200, json=_payload())
    )
    assert get_comments("post1", client=http) == []


@respx.mock
def test_get_comments_missing_numeric_fields_safe(http):
    node = {"kind": "t1", "data": {"id": "bare", "body": "no score"}}
    respx.get(f"{BASE}/comments/post1.json").mock(
        return_value=httpx.Response(200, json=_payload(node))
    )
    comments = get_comments("post1", client=http)
    assert comments[0].score == 0
    assert comments[0].controversiality == 0
    assert comments[0].author == "[deleted]"


@respx.mock
def test_get_comments_404_raises_not_found(http):
    respx.get(f"{BASE}/comments/nope.json").mock(return_value=httpx.Response(404))
    with pytest.raises(NotFoundError):
        get_comments("nope", client=http)


@respx.mock
def test_get_comments_respects_limit(test_settings, no_sleep):
    children = tuple(_comment_node(f"c{i}") for i in range(20))
    respx.get(f"{BASE}/comments/post1.json").mock(
        return_value=httpx.Response(200, json=_payload(*children))
    )
    client = RedditHttpClient(test_settings, sleep=no_sleep, monotonic=lambda: 0.0)
    comments = get_comments("post1", limit=5, client=client)
    assert len(comments) == 5


def test_get_comments_validates_input(http):
    with pytest.raises(ValueError):
        get_comments("", client=http)
    with pytest.raises(ValueError):
        get_comments("t3_", client=http)
    with pytest.raises(ValueError):
        get_comments("abc", limit=0, client=http)
    with pytest.raises(ValueError):
        get_comments("abc", depth=-1, client=http)


@respx.mock
def test_get_comments_own_client_from_settings(test_settings):
    respx.get(f"{BASE}/comments/post1.json").mock(
        return_value=httpx.Response(200, json=_payload(_comment_node("c1")))
    )
    comments = get_comments_direct("post1", settings=test_settings)
    assert comments[0].id == "c1"


def test_get_comments_exported():
    from reddit_actions import get_comments as exported
    from reddit_actions.scrapers import get_comments as from_scrapers

    assert exported is get_comments_direct
    assert from_scrapers is get_comments_direct
