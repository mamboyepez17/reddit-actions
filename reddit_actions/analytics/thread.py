"""Thread-level analysis: post + comments aggregates."""

from __future__ import annotations

from reddit_actions.auth.anonymous import build_comments_path
from reddit_actions.config import Settings
from reddit_actions.http_client import RedditHttpClient
from reddit_actions.models import Post, ThreadAnalysis
from reddit_actions.parsers.comments import parse_comments_payload
from reddit_actions.parsers.posts import parse_reddit_post

__all__ = ["analyze_thread"]


def _parse_post_from_comments_payload(payload: object) -> Post | None:
    """Recover the post from Reddit comments JSON (listing[0])."""
    if not isinstance(payload, list) or not payload:
        return None
    listing = payload[0]
    if not isinstance(listing, dict):
        return None
    data = listing.get("data")
    if not isinstance(data, dict):
        return None
    children = data.get("children")
    if not isinstance(children, list) or not children:
        return None
    try:
        return parse_reddit_post(children[0])
    except Exception:  # noqa: BLE001
        return None


def analyze_thread(
    post_id: str,
    *,
    comment_limit: int = 50,
    comment_depth: int = 2,
    client: RedditHttpClient | None = None,
    settings: Settings | None = None,
) -> ThreadAnalysis:
    """Analyze a public Reddit thread (post + comment tree aggregates).

    One HTTP call to /comments/{id}.json; post and comments are both parsed
    from that payload (public JSON shape: [post_listing, comments_listing]).

    Args:
        post_id: Post id with or without t3_ prefix.
        comment_limit: Max comments to include.
        comment_depth: Max reply depth to parse.
        client: Optional shared HTTP client.
        settings: Optional settings when constructing an internal client.

    Returns:
        ThreadAnalysis with optional post, comments, and aggregate helpers.

    Raises:
        ValueError: Empty post_id / negative limits.
        NotFoundError: Post does not exist (HTTP 404).
        RateLimitError / AuthError / RedditError: Other HTTP failures.
    """
    cleaned = (post_id or "").strip().removeprefix("t3_")
    if not cleaned:
        raise ValueError("post_id must be a non-empty string")
    if comment_limit < 1:
        raise ValueError("comment_limit must be >= 1")
    if comment_depth < 0:
        raise ValueError("comment_depth must be >= 0")

    path = build_comments_path(cleaned)
    params = {
        "limit": min(comment_limit, 100),
        "depth": comment_depth,
        "raw_json": 1,
        "sort": "confidence",
    }

    owns_client = client is None
    http = client or RedditHttpClient(settings)
    try:
        payload = http.get_json(path, params=params)
    finally:
        if owns_client:
            http.close()

    post = _parse_post_from_comments_payload(payload)
    comments = parse_comments_payload(
        payload,
        max_depth=comment_depth,
        limit=comment_limit,
    )
    return ThreadAnalysis(post=post, comments=tuple(comments))
