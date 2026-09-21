"""MCP tool handlers and registry tests (no live MCP runtime required)."""

from __future__ import annotations

import httpx
import pytest
import respx
from reddit_actions.mcp_server import (
    SERVER_NAME,
    TOOL_SPECS,
    create_server,
    registered_tool_names,
    tool_reddit_comments,
    tool_reddit_search,
    tool_reddit_subreddit,
    tool_reddit_thread,
)

BASE = "https://www.reddit.com"


@pytest.fixture(autouse=True)
def _fast_settings(monkeypatch):
    monkeypatch.setenv("REDDIT_USER_AGENT", "reddit-actions-tests/0.1 (by u/test; research)")
    monkeypatch.setenv("REDDIT_MIN_DELAY", "0")
    monkeypatch.setenv("REDDIT_MAX_RETRIES", "1")
    from reddit_actions.config import reset_settings_cache

    reset_settings_cache()
    yield
    reset_settings_cache()


def _posts_payload(*pairs: tuple[str, str]) -> dict:
    return {
        "kind": "Listing",
        "data": {
            "children": [
                {
                    "kind": "t3",
                    "data": {
                        "id": pid,
                        "title": title,
                        "subreddit": "python",
                        "author": "alice",
                        "score": 10,
                        "upvote_ratio": 0.9,
                        "num_comments": 1,
                        "permalink": f"/r/python/comments/{pid}/{title}/",
                        "url": "https://example.com",
                        "created_utc": 1_700_000_000.0,
                        "selftext": "",
                        "over_18": False,
                    },
                }
                for pid, title in pairs
            ]
        },
    }


def _comments_payload(*nodes: dict) -> list:
    return [
        {
            "kind": "Listing",
            "data": {
                "children": [
                    {
                        "kind": "t3",
                        "data": {
                            "id": "post1",
                            "title": "Thread",
                            "selftext": "",
                            "subreddit": "python",
                            "author": "op",
                            "score": 3,
                            "upvote_ratio": 1.0,
                            "num_comments": len(nodes),
                            "permalink": "/r/python/comments/post1/thread/",
                            "url": "",
                            "created_utc": 1_700_000_000.0,
                            "over_18": False,
                        },
                    }
                ]
            },
        },
        {"kind": "Listing", "data": {"children": list(nodes)}},
    ]


def _comment_node(cid: str, body: str = "hello", score: int = 2) -> dict:
    return {
        "kind": "t1",
        "data": {
            "id": cid,
            "body": body,
            "author": f"u_{cid}",
            "score": score,
            "parent_id": "t3_post1",
            "controversiality": 0,
            "created_utc": 1_700_000_000.0,
            "permalink": f"/r/python/comments/post1/thread/{cid}/",
        },
    }


def test_server_name_and_tool_specs():
    assert SERVER_NAME == "reddit-actions"
    names = registered_tool_names()
    assert names == [
        "reddit_search",
        "reddit_comments",
        "reddit_thread",
        "reddit_subreddit",
    ]
    for spec in TOOL_SPECS:
        assert spec["name"]
        assert spec["description"]


def test_import_mcp_server_without_mcp_package():
    """Handlers must work even if the optional mcp package is missing."""
    import reddit_actions.mcp_server as mod

    assert callable(mod.tool_reddit_search)
    assert callable(mod.create_server)


@respx.mock
def test_tool_search_success():
    respx.get(f"{BASE}/search.json").mock(
        return_value=httpx.Response(200, json=_posts_payload(("abc", "MCP post")))
    )
    result = tool_reddit_search("python", limit=5)
    assert result["ok"] is True
    assert result["tool"] == "reddit_search"
    assert result["count"] == 1
    assert result["posts"][0]["id"] == "abc"
    assert result["posts"][0]["title"] == "MCP post"
    assert result["posts"][0]["permalink"].startswith("https://www.reddit.com/")


@respx.mock
def test_tool_search_empty():
    respx.get(f"{BASE}/search.json").mock(
        return_value=httpx.Response(200, json={"kind": "Listing", "data": {"children": []}})
    )
    result = tool_reddit_search("zzzz")
    assert result["ok"] is True
    assert result["count"] == 0
    assert result["posts"] == []


@respx.mock
def test_tool_search_rate_limit_structured_error():
    respx.get(f"{BASE}/search.json").mock(
        return_value=httpx.Response(429, headers={"Retry-After": "0"})
    )
    result = tool_reddit_search("python")
    assert result["ok"] is False
    assert result["tool"] == "reddit_search"
    assert result["error"]["kind"] == "rate_limit"
    assert result["error"]["type"] == "RateLimitError"
    assert result["error"]["message"]


@respx.mock
def test_tool_search_validation_error():
    result = tool_reddit_search("", limit=5)
    assert result["ok"] is False
    assert result["error"]["kind"] == "validation"
    assert "query" in result["error"]["message"].lower() or result["error"]["message"]


@respx.mock
def test_tool_comments_success():
    respx.get(f"{BASE}/comments/post1.json").mock(
        return_value=httpx.Response(200, json=_comments_payload(_comment_node("c1", "from mcp")))
    )
    result = tool_reddit_comments("t3_post1", limit=10, depth=1)
    assert result["ok"] is True
    assert result["count"] == 1
    assert result["comments"][0]["id"] == "c1"
    assert result["comments"][0]["body"] == "from mcp"


@respx.mock
def test_tool_comments_not_found():
    respx.get(f"{BASE}/comments/gone.json").mock(return_value=httpx.Response(404))
    result = tool_reddit_comments("gone")
    assert result["ok"] is False
    assert result["error"]["kind"] == "not_found"


@respx.mock
def test_tool_thread_success():
    payload = _comments_payload(_comment_node("c1", "a", 5), _comment_node("c2", "b", 1))
    respx.get(f"{BASE}/comments/post1.json").mock(return_value=httpx.Response(200, json=payload))
    result = tool_reddit_thread("post1")
    assert result["ok"] is True
    thread = result["thread"]
    assert thread["post"]["id"] == "post1"
    assert thread["comment_count"] == 2
    assert thread["total_comment_score"] == 6
    assert len(thread["top_comments"]) == 2


@respx.mock
def test_tool_thread_unexpected_error_does_not_raise(monkeypatch):
    def boom(*_a, **_k):
        raise RuntimeError("kaboom")

    monkeypatch.setattr("reddit_actions.mcp_server.analyze_thread", boom)
    result = tool_reddit_thread("post1")
    assert result["ok"] is False
    assert result["error"]["kind"] == "unexpected"
    assert "kaboom" in result["error"]["message"]


@respx.mock
def test_tool_subreddit_success():
    respx.get(f"{BASE}/r/python/hot.json").mock(
        return_value=httpx.Response(200, json=_posts_payload(("h1", "Hot one")))
    )
    result = tool_reddit_subreddit("r/python", sort="hot", limit=5)
    assert result["ok"] is True
    assert result["subreddit"] == "python"
    assert result["posts"][0]["id"] == "h1"


@respx.mock
def test_tool_subreddit_invalid_sort():
    result = tool_reddit_subreddit("python", sort="nope")
    assert result["ok"] is False
    assert result["error"]["kind"] == "validation"


def test_create_server_optional_mcp():
    try:
        import mcp  # noqa: F401
    except ImportError:
        with pytest.raises(RuntimeError, match="MCP extra"):
            create_server()
    else:
        server = create_server()
        assert server is not None
        assert hasattr(server, "tool") or hasattr(server, "run")


def test_handlers_exported():
    import reddit_actions.mcp_server as mod

    assert "tool_reddit_search" in mod.__all__
    assert "create_server" in mod.__all__
    assert "TOOL_SPECS" in mod.__all__
