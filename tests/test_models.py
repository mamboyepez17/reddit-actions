"""Tests for domain models."""

from __future__ import annotations

from reddit_actions.models import Comment, Post


def _sample_post() -> Post:
    return Post(
        id="abc",
        title="Hello",
        selftext="body",
        subreddit="python",
        author="alice",
        score=10,
        upvote_ratio=0.95,
        num_comments=2,
        permalink="/r/python/comments/abc/hello/",
        url="https://example.com",
        created_utc=1_700_000_000.0,
        nsfw=False,
    )


def test_post_full_permalink_relative():
    post = _sample_post()
    assert post.full_permalink == "https://www.reddit.com/r/python/comments/abc/hello/"


def test_post_full_permalink_absolute_passthrough():
    post = _sample_post()
    absolute = Post(
        id=post.id,
        title=post.title,
        selftext=post.selftext,
        subreddit=post.subreddit,
        author=post.author,
        score=post.score,
        upvote_ratio=post.upvote_ratio,
        num_comments=post.num_comments,
        permalink="https://www.reddit.com/r/python/comments/abc/hello/",
        url=post.url,
        created_utc=post.created_utc,
        nsfw=post.nsfw,
    )
    assert absolute.full_permalink == "https://www.reddit.com/r/python/comments/abc/hello/"


def test_comment_full_permalink():
    comment = Comment(
        id="c1",
        parent_id="t3_abc",
        body="hi",
        author="bob",
        score=1,
        created_utc=1_700_000_000.0,
        depth=0,
        controversiality=0,
        permalink="/r/python/comments/abc/hello/c1/",
    )
    assert comment.full_permalink.endswith("/c1/")
    assert comment.full_permalink.startswith("https://www.reddit.com/")
