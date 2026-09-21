"""Tests for analyze_thread and ThreadAnalysis aggregates."""

from __future__ import annotations

import httpx
import pytest
import respx
from reddit_actions import NotFoundError, ThreadAnalysis, analyze_thread
from reddit_actions.analytics.thread import analyze_thread as analyze_direct
from reddit_actions.http_client import RedditHttpClient
from reddit_actions.models import Comment, Post

BASE = "https://www.reddit.com"


@pytest.fixture
def http(test_settings, no_sleep):
    return RedditHttpClient(test_settings, sleep=no_sleep, monotonic=lambda: 0.0)


def _post_node(pid: str = "post1", score: int = 10) -> dict:
    return {
        "kind": "t3",
        "data": {
            "id": pid,
            "title": "Thread title",
            "selftext": "body",
            "subreddit": "python",
            "author": "op",
            "score": score,
            "upvote_ratio": 0.95,
            "num_comments": 3,
            "permalink": f"/r/python/comments/{pid}/thread_title/",
            "url": "https://example.com",
            "created_utc": 1_700_000_000.0,
            "over_18": False,
        },
    }


def _comment_node(
    cid: str,
    *,
    score: int = 1,
    parent: str = "t3_post1",
    body: str = "hello",
    controversiality: int = 0,
    replies: dict | None = None,
) -> dict:
    data = {
        "id": cid,
        "body": body,
        "author": f"user_{cid}",
        "score": score,
        "parent_id": parent,
        "controversiality": controversiality,
        "created_utc": 1_700_000_000.0,
        "permalink": f"/r/python/comments/post1/thread_title/{cid}/",
    }
    if replies is not None:
        data["replies"] = replies
    return {"kind": "t1", "data": data}


def _replies(*children: dict) -> dict:
    return {"kind": "Listing", "data": {"children": list(children)}}


def _payload(post: dict | None, *comments: dict) -> list:
    post_listing = {
        "kind": "Listing",
        "data": {"children": [post] if post else []},
    }
    comments_listing = {"kind": "Listing", "data": {"children": list(comments)}}
    return [post_listing, comments_listing]


@respx.mock
def test_analyze_thread_aggregates(http):
    payload = _payload(
        _post_node(score=10),
        _comment_node("low", score=1),
        _comment_node("high", score=20),
        _comment_node(
            "root",
            score=5,
            replies=_replies(_comment_node("child", score=2, parent="t1_root")),
        ),
    )
    respx.get(f"{BASE}/comments/post1.json").mock(return_value=httpx.Response(200, json=payload))

    analysis = analyze_thread("post1", client=http)
    assert isinstance(analysis, ThreadAnalysis)
    assert analysis.post is not None
    assert analysis.post.id == "post1"
    assert analysis.post.title == "Thread title"
    assert analysis.post.score == 10
    assert analysis.comment_count == 4
    assert analysis.total_comment_score == 1 + 20 + 5 + 2
    assert analysis.comments_by_depth[0] == 3
    assert analysis.comments_by_depth[1] == 1


@respx.mock
def test_analyze_thread_top_comments_sorted_by_score(http):
    payload = _payload(
        _post_node(),
        _comment_node("a", score=3),
        _comment_node("b", score=30),
        _comment_node("c", score=12),
    )
    respx.get(f"{BASE}/comments/post1.json").mock(return_value=httpx.Response(200, json=payload))
    analysis = analyze_thread("post1", client=http)
    top = analysis.top_comments(2)
    assert [c.id for c in top] == ["b", "c"]
    assert top[0].score == 30


@respx.mock
def test_analyze_thread_without_comments(http):
    payload = _payload(_post_node())
    respx.get(f"{BASE}/comments/post1.json").mock(return_value=httpx.Response(200, json=payload))
    analysis = analyze_thread("post1", client=http)
    assert analysis.post is not None
    assert analysis.comment_count == 0
    assert analysis.total_comment_score == 0
    assert analysis.top_comments(5) == []
    assert analysis.comments_by_depth == {}


@respx.mock
def test_analyze_thread_post_none_when_listing_empty(http):
    payload = _payload(None, _comment_node("c1"))
    respx.get(f"{BASE}/comments/post1.json").mock(return_value=httpx.Response(200, json=payload))
    analysis = analyze_thread("post1", client=http)
    assert analysis.post is None
    assert analysis.comment_count == 1


@respx.mock
def test_analyze_thread_single_http_call(http):
    payload = _payload(_post_node(), _comment_node("c1"))
    route = respx.get(f"{BASE}/comments/post1.json").mock(
        return_value=httpx.Response(200, json=payload)
    )
    analyze_thread("t3_post1", client=http)
    assert route.call_count == 1


@respx.mock
def test_analyze_thread_404(http):
    respx.get(f"{BASE}/comments/gone.json").mock(return_value=httpx.Response(404))
    with pytest.raises(NotFoundError):
        analyze_thread("gone", client=http)


@respx.mock
def test_analyze_thread_controversial_count(http):
    payload = _payload(
        _post_node(),
        _comment_node("ok", controversiality=0),
        _comment_node("spicy", controversiality=1),
    )
    respx.get(f"{BASE}/comments/post1.json").mock(return_value=httpx.Response(200, json=payload))
    analysis = analyze_thread("post1", client=http)
    assert analysis.controversial_count == 1


def test_analyze_thread_validates_input(http):
    with pytest.raises(ValueError):
        analyze_thread("", client=http)
    with pytest.raises(ValueError):
        analyze_thread("abc", comment_limit=0, client=http)
    with pytest.raises(ValueError):
        analyze_thread("abc", comment_depth=-1, client=http)


def test_thread_analysis_model_helpers():
    post = Post(
        id="p",
        title="t",
        selftext="",
        subreddit="python",
        author="a",
        score=1,
        upvote_ratio=1.0,
        num_comments=0,
        permalink="/r/python/comments/p/t/",
        url="",
        created_utc=0.0,
        nsfw=False,
    )
    comments = (
        Comment(
            id="c1",
            parent_id="t3_p",
            body="x",
            author="u",
            score=5,
            created_utc=0.0,
            depth=0,
            controversiality=0,
            permalink="/p/c1/",
        ),
        Comment(
            id="c2",
            parent_id="t1_c1",
            body="y",
            author="v",
            score=9,
            created_utc=0.0,
            depth=1,
            controversiality=0,
            permalink="/p/c2/",
        ),
    )
    analysis = ThreadAnalysis(post=post, comments=comments)
    assert analysis.comment_count == 2
    assert analysis.total_comment_score == 14
    assert analysis.comments_by_depth == {0: 1, 1: 1}
    assert [c.id for c in analysis.top_comments(1)] == ["c2"]


@respx.mock
def test_analyze_own_client_settings(test_settings):
    respx.get(f"{BASE}/comments/post1.json").mock(
        return_value=httpx.Response(200, json=_payload(_post_node(), _comment_node("c1")))
    )
    analysis = analyze_direct("post1", settings=test_settings)
    assert analysis.post is not None
    assert analysis.comment_count == 1


def test_exports():
    import reddit_actions
    from reddit_actions.analytics import analyze_thread as from_analytics

    assert from_analytics is analyze_direct
    assert "analyze_thread" in reddit_actions.__all__
    assert "get_subreddit_posts" in reddit_actions.__all__
    assert "ThreadAnalysis" in reddit_actions.__all__
