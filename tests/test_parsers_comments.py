"""Tests for Reddit comment payload parsers."""

from __future__ import annotations

from reddit_actions.parsers.comments import (
    parse_comments_payload,
    parse_reddit_comment,
)


def _comment(
    cid: str,
    *,
    body: str | None = "hello",
    author: str = "alice",
    score: int = 1,
    parent_id: str = "t3_post1",
    permalink: str | None = None,
    kind: str = "t1",
    replies: dict | list | None = None,
    controversiality: int = 0,
    created_utc: float = 1_700_000_000.0,
) -> dict:
    data: dict = {
        "id": cid,
        "author": author,
        "score": score,
        "parent_id": parent_id,
        "controversiality": controversiality,
        "created_utc": created_utc,
    }
    if body is not None:
        data["body"] = body
    if permalink is not None:
        data["permalink"] = permalink
    if replies is not None:
        data["replies"] = replies
    return {"kind": kind, "data": data}


def _replies_listing(*children: dict) -> dict:
    return {"kind": "Listing", "data": {"children": list(children)}}


def _comments_payload(*top_level: dict, post_permalink: str = "/r/python/comments/post1/title/") -> list:
    return [
        {
            "kind": "Listing",
            "data": {
                "children": [
                    {
                        "kind": "t3",
                        "data": {"id": "post1", "title": "Title", "permalink": post_permalink},
                    }
                ]
            },
        },
        {"kind": "Listing", "data": {"children": list(top_level)}},
    ]


def test_parse_reddit_comment_happy_path():
    raw = _comment(
        "c1",
        permalink="/r/python/comments/post1/title/c1/",
        controversiality=1,
    )
    comment = parse_reddit_comment(raw)
    assert comment is not None
    assert comment.id == "c1"
    assert comment.body == "hello"
    assert comment.author == "alice"
    assert comment.score == 1
    assert comment.parent_id == "t3_post1"
    assert comment.depth == 0
    assert comment.controversiality == 1
    assert comment.permalink.endswith("/c1/")


def test_parse_reddit_comment_strips_t1_prefix():
    comment = parse_reddit_comment(_comment("t1_abc"))
    assert comment is not None
    assert comment.id == "abc"


def test_parse_reddit_comment_missing_fields_defaults():
    raw = {"kind": "t1", "data": {"id": "x", "body": "only body"}}
    comment = parse_reddit_comment(raw)
    assert comment is not None
    assert comment.author == "[deleted]"
    assert comment.score == 0
    assert comment.controversiality == 0
    assert comment.parent_id == "t3_x"


def test_parse_reddit_comment_removed_body_kept():
    comment = parse_reddit_comment(_comment("r1", body="[removed]"))
    assert comment is not None
    assert comment.body == "[removed]"


def test_parse_reddit_comment_deleted_body_kept():
    comment = parse_reddit_comment(_comment("d1", body="[deleted]"))
    assert comment is not None
    assert comment.body == "[deleted]"


def test_parse_reddit_comment_skips_more_stubs():
    assert parse_reddit_comment({"kind": "more", "data": {"id": "m1", "count": 3}}) is None
    assert parse_reddit_comment({"kind": "t3", "data": {"id": "p", "body": "x"}}) is None


def test_parse_reddit_comment_skips_without_id_or_body():
    assert parse_reddit_comment({"kind": "t1", "data": {"body": "no id"}}) is None
    assert parse_reddit_comment({"kind": "t1", "data": {"id": "z"}}) is None
    assert parse_reddit_comment("nope") is None  # type: ignore[arg-type]


def test_parse_comments_payload_flat_thread():
    payload = _comments_payload(
        _comment("a", parent_id="t3_post1"),
        _comment("b", parent_id="t3_post1", score=5),
    )
    comments = parse_comments_payload(payload, max_depth=2, limit=50)
    assert [c.id for c in comments] == ["a", "b"]
    assert all(c.depth == 0 for c in comments)
    assert comments[1].score == 5


def test_parse_comments_payload_nested_depths():
    payload = _comments_payload(
        _comment(
            "root",
            parent_id="t3_post1",
            replies=_replies_listing(
                _comment(
                    "child",
                    parent_id="t1_root",
                    replies=_replies_listing(_comment("grand", parent_id="t1_child")),
                )
            ),
        )
    )
    comments = parse_comments_payload(payload, max_depth=2, limit=50)
    by_id = {c.id: c for c in comments}
    assert set(by_id) == {"root", "child", "grand"}
    assert by_id["root"].depth == 0
    assert by_id["child"].depth == 1
    assert by_id["grand"].depth == 2


def test_parse_comments_payload_respects_max_depth():
    payload = _comments_payload(
        _comment(
            "root",
            replies=_replies_listing(
                _comment("child", parent_id="t1_root", replies=_replies_listing(_comment("grand", parent_id="t1_child")))
            ),
        )
    )
    comments = parse_comments_payload(payload, max_depth=0, limit=50)
    assert [c.id for c in comments] == ["root"]


def test_parse_comments_payload_skips_more_in_tree():
    payload = _comments_payload(
        _comment(
            "root",
            replies=_replies_listing(
                {"kind": "more", "data": {"id": "m", "children": ["xyz"]}},
                _comment("ok", parent_id="t1_root"),
            ),
        )
    )
    comments = parse_comments_payload(payload, max_depth=2, limit=50)
    assert [c.id for c in comments] == ["root", "ok"]


def test_parse_comments_payload_empty_and_malformed():
    assert parse_comments_payload({}) == []
    assert parse_comments_payload([]) == []
    assert parse_comments_payload([{}]) == []
    assert parse_comments_payload([{}, {}]) == []
    assert parse_comments_payload({"data": {"children": []}}) == []
    assert parse_comments_payload([{}, {"data": {"children": None}}]) == []


def test_parse_comments_payload_limit():
    payload = _comments_payload(*[ _comment(f"c{i}") for i in range(10) ])
    comments = parse_comments_payload(payload, max_depth=2, limit=3)
    assert len(comments) == 3


def test_parse_comments_payload_fallback_permalink_from_post():
    payload = _comments_payload(_comment("c1", permalink=None), post_permalink="/r/py/comments/post1/x/")
    comments = parse_comments_payload(payload)
    assert comments[0].permalink == "/r/py/comments/post1/x/c1/"
