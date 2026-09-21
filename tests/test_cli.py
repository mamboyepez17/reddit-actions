"""CLI tests with mocked HTTP."""

from __future__ import annotations

import json

import httpx
import pytest
import respx
from click.testing import CliRunner
from reddit_actions.cli import cli

BASE = "https://www.reddit.com"


@pytest.fixture
def runner():
    return CliRunner()


@pytest.fixture(autouse=True)
def _fast_settings(monkeypatch):
    monkeypatch.setenv("REDDIT_USER_AGENT", "reddit-actions-tests/0.1 (by u/test; research)")
    monkeypatch.setenv("REDDIT_MIN_DELAY", "0")
    monkeypatch.setenv("REDDIT_MAX_RETRIES", "1")
    from reddit_actions.config import reset_settings_cache

    reset_settings_cache()
    yield
    reset_settings_cache()


def _post_payload(*ids_titles: tuple[str, str]) -> dict:
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
                        "num_comments": 2,
                        "permalink": f"/r/python/comments/{pid}/{title}/",
                        "url": "https://example.com",
                        "created_utc": 1_700_000_000.0,
                        "selftext": "",
                        "over_18": False,
                    },
                }
                for pid, title in ids_titles
            ]
        },
    }


def _comments_payload(*comments: dict) -> list:
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
                            "selftext": "x",
                            "subreddit": "python",
                            "author": "op",
                            "score": 5,
                            "upvote_ratio": 1.0,
                            "num_comments": len(comments),
                            "permalink": "/r/python/comments/post1/thread/",
                            "url": "",
                            "created_utc": 1_700_000_000.0,
                            "over_18": False,
                        },
                    }
                ]
            },
        },
        {"kind": "Listing", "data": {"children": list(comments)}},
    ]


def _comment_node(cid: str, body: str = "hello", score: int = 3) -> dict:
    return {
        "kind": "t1",
        "data": {
            "id": cid,
            "body": body,
            "author": f"user_{cid}",
            "score": score,
            "parent_id": "t3_post1",
            "controversiality": 0,
            "created_utc": 1_700_000_000.0,
            "permalink": f"/r/python/comments/post1/thread/{cid}/",
        },
    }


def test_version(runner):
    result = runner.invoke(cli, ["version"])
    assert result.exit_code == 0
    assert result.output.strip()


def test_help(runner):
    result = runner.invoke(cli, ["--help"])
    assert result.exit_code == 0
    for cmd in ("search", "comments", "thread", "subreddit", "version"):
        assert cmd in result.output


@respx.mock
def test_search_text_output(runner):
    respx.get(f"{BASE}/search.json").mock(
        return_value=httpx.Response(200, json=_post_payload(("abc", "Python tips")))
    )
    result = runner.invoke(cli, ["search", "python", "--limit", "5"])
    assert result.exit_code == 0
    assert "Python tips" in result.output
    assert "r/python" in result.output


@respx.mock
def test_search_json_output(runner):
    respx.get(f"{BASE}/search.json").mock(
        return_value=httpx.Response(200, json=_post_payload(("abc", "JSON post"), ("def", "Other")))
    )
    result = runner.invoke(cli, ["search", "python", "--json", "--limit", "2"])
    assert result.exit_code == 0
    data = json.loads(result.output)
    assert isinstance(data, list)
    assert data[0]["id"] == "abc"
    assert data[0]["title"] == "JSON post"
    assert data[0]["permalink"].startswith("https://www.reddit.com/")


@respx.mock
def test_search_subreddit_flag(runner):
    route = respx.get(f"{BASE}/r/cryptocurrency/search.json").mock(
        return_value=httpx.Response(200, json=_post_payload(("eth", "ETH news")))
    )
    result = runner.invoke(cli, ["search", "eth", "--subreddit", "cryptocurrency", "--limit", "3"])
    assert result.exit_code == 0
    assert "ETH news" in result.output
    assert route.called


@respx.mock
def test_search_empty(runner):
    respx.get(f"{BASE}/search.json").mock(
        return_value=httpx.Response(200, json={"kind": "Listing", "data": {"children": []}})
    )
    result = runner.invoke(cli, ["search", "nothingxyz"])
    assert result.exit_code == 0
    assert "No posts found" in result.output


@respx.mock
def test_comments_text_and_t3_strip(runner):
    route = respx.get(f"{BASE}/comments/post1.json").mock(
        return_value=httpx.Response(200, json=_comments_payload(_comment_node("c1", "nice thread")))
    )
    result = runner.invoke(cli, ["comments", "t3_post1", "--limit", "10"])
    assert result.exit_code == 0
    assert "nice thread" in result.output
    assert "/comments/post1.json" in str(route.calls.last.request.url)


@respx.mock
def test_comments_json(runner):
    respx.get(f"{BASE}/comments/post1.json").mock(
        return_value=httpx.Response(200, json=_comments_payload(_comment_node("c1", "body one", 7)))
    )
    result = runner.invoke(cli, ["comments", "post1", "--json"])
    assert result.exit_code == 0
    data = json.loads(result.output)
    assert data[0]["id"] == "c1"
    assert data[0]["body"] == "body one"
    assert data[0]["score"] == 7


@respx.mock
def test_thread_json(runner):
    payload = _comments_payload(_comment_node("c1", "first", 10), _comment_node("c2", "second", 2))
    respx.get(f"{BASE}/comments/post1.json").mock(return_value=httpx.Response(200, json=payload))
    result = runner.invoke(cli, ["thread", "post1", "--json"])
    assert result.exit_code == 0
    data = json.loads(result.output)
    assert data["post"]["id"] == "post1"
    assert data["comment_count"] == 2
    assert data["total_comment_score"] == 12
    assert "top_comments" in data
    assert len(data["comments"]) == 2


@respx.mock
def test_thread_text(runner):
    payload = _comments_payload(_comment_node("c1", "hello world", 10))
    respx.get(f"{BASE}/comments/post1.json").mock(return_value=httpx.Response(200, json=payload))
    result = runner.invoke(cli, ["thread", "post1"])
    assert result.exit_code == 0
    assert "Thread" in result.output
    assert "Comments parsed: 1" in result.output


@respx.mock
def test_rate_limit_nonzero_exit(runner):
    respx.get(f"{BASE}/search.json").mock(return_value=httpx.Response(429, headers={"Retry-After": "0"}))
    result = runner.invoke(cli, ["search", "python"])
    assert result.exit_code != 0
    assert "Error" in result.output
    assert "Rate limited" in result.output or "429" in result.output


@respx.mock
def test_not_found_comments_exit_code(runner):
    respx.get(f"{BASE}/comments/nope.json").mock(return_value=httpx.Response(404))
    result = runner.invoke(cli, ["comments", "nope"])
    assert result.exit_code != 0
    assert "Not found" in result.output or "Error" in result.output


def test_invalid_sort_exit_code(runner):
    result = runner.invoke(cli, ["search", "q", "--sort", "nope"])
    assert result.exit_code != 0


@respx.mock
def test_subreddit_command(runner):
    route = respx.get(f"{BASE}/r/python/hot.json").mock(
        return_value=httpx.Response(200, json=_post_payload(("h1", "Hot post")))
    )
    result = runner.invoke(cli, ["subreddit", "--subreddit", "python", "--sort", "hot", "--limit", "5"])
    assert result.exit_code == 0
    assert "Hot post" in result.output
    assert route.called


@respx.mock
def test_subreddit_json(runner):
    respx.get(f"{BASE}/r/python/new.json").mock(
        return_value=httpx.Response(200, json=_post_payload(("n1", "New thing")))
    )
    result = runner.invoke(cli, ["subreddit", "--subreddit", "python", "--sort", "new", "--json"])
    assert result.exit_code == 0
    data = json.loads(result.output)
    assert data[0]["id"] == "n1"


def test_missing_user_agent_friendly_error(runner, monkeypatch):
    monkeypatch.delenv("REDDIT_USER_AGENT", raising=False)
    from reddit_actions.config import reset_settings_cache

    reset_settings_cache()
    result = runner.invoke(cli, ["search", "python"])
    assert result.exit_code != 0
    assert "REDDIT_USER_AGENT" in result.output or "user_agent" in result.output.lower() or "Error" in result.output
