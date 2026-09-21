"""Tests for Reddit post payload parsers."""

from __future__ import annotations

from reddit_actions.parsers.posts import parse_posts_payload, parse_reddit_post


def _listing(*children: dict) -> dict:
    return {"kind": "Listing", "data": {"children": list(children)}}


def _child(**data) -> dict:
    return {"kind": "t3", "data": data}


def test_parse_reddit_post_happy_path():
    raw = _child(
        id="abc123",
        title="Python tips",
        selftext="body",
        subreddit="python",
        author="alice",
        score=42,
        upvote_ratio=0.91,
        num_comments=7,
        permalink="/r/python/comments/abc123/python_tips/",
        url="https://example.com",
        created_utc=1_700_000_000.0,
        over_18=False,
    )
    post = parse_reddit_post(raw)
    assert post is not None
    assert post.id == "abc123"
    assert post.title == "Python tips"
    assert post.selftext == "body"
    assert post.subreddit == "python"
    assert post.author == "alice"
    assert post.score == 42
    assert post.upvote_ratio == 0.91
    assert post.num_comments == 7
    assert post.permalink == "/r/python/comments/abc123/python_tips/"
    assert post.url == "https://example.com"
    assert post.created_utc == 1_700_000_000.0
    assert post.nsfw is False


def test_parse_reddit_post_strips_t3_prefix():
    raw = _child(id="t3_xyz", title="Hello")
    post = parse_reddit_post(raw)
    assert post is not None
    assert post.id == "xyz"


def test_parse_reddit_post_missing_optional_fields():
    raw = _child(id="id1", title="Only title")
    post = parse_reddit_post(raw)
    assert post is not None
    assert post.selftext == ""
    assert post.author == "[deleted]"
    assert post.score == 0
    assert post.upvote_ratio == 0.0
    assert post.num_comments == 0
    assert post.permalink == "/comments/id1/"
    assert post.nsfw is False


def test_parse_reddit_post_skips_without_id_or_title():
    assert parse_reddit_post(_child(title="no id")) is None
    assert parse_reddit_post(_child(id="x", title="")) is None
    assert parse_reddit_post({"data": {}}) is None
    assert parse_reddit_post("not-a-dict") is None  # type: ignore[arg-type]


def test_parse_posts_payload_children():
    payload = _listing(
        _child(id="a", title="Post A", subreddit="python", score=1),
        _child(id="b", title="Post B", subreddit="learnpython", score=2),
    )
    posts = parse_posts_payload(payload)
    assert [p.id for p in posts] == ["a", "b"]
    assert posts[0].title == "Post A"


def test_parse_posts_payload_empty_and_malformed():
    assert parse_posts_payload({}) == []
    assert parse_posts_payload({"data": {}}) == []
    assert parse_posts_payload({"data": {"children": []}}) == []
    assert parse_posts_payload(None) == []
    assert parse_posts_payload("nope") == []


def test_parse_posts_payload_skips_bad_children_keeps_good_ones():
    payload = _listing(
        {"kind": "t3", "data": {}},
        _child(id="good", title="Good post"),
        {"kind": "t3", "data": None},
        _child(id="also", title="Also good"),
    )
    posts = parse_posts_payload(payload)
    assert [p.id for p in posts] == ["good", "also"]


def test_parse_posts_payload_raw_data_without_listing_wrapper():
    """Some fixtures may pass children data dicts directly in a listing shape."""
    payload = {"data": {"children": [{"data": {"id": "z", "title": "Z"}}]}}
    posts = parse_posts_payload(payload)
    assert len(posts) == 1
    assert posts[0].id == "z"
