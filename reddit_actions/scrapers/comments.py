"""Fetch public Reddit comments for a post via JSON endpoints."""

from __future__ import annotations

from reddit_actions.auth.anonymous import build_comments_path
from reddit_actions.config import Settings
from reddit_actions.http_client import RedditHttpClient
from reddit_actions.models import Comment
from reddit_actions.parsers.comments import parse_comments_payload

__all__ = ["get_comments"]


def get_comments(
    post_id: str,
    limit: int = 50,
    depth: int = 2,
    *,
    client: RedditHttpClient | None = None,
    settings: Settings | None = None,
) -> list[Comment]:
    """Get the comment tree of a public Reddit post.

    Args:
        post_id: Post id with or without the t3_ prefix.
        limit: Max comments to return (client-side cap after parse).
        depth: Max reply depth to parse (0 = top-level only).
        client: Optional pre-built HTTP client.
        settings: Optional settings when constructing an internal client.

    Returns:
        List of Comment models ordered as Reddit returns them (depth-first).

    Raises:
        ValueError: Invalid post_id / limit / depth.
        NotFoundError: Post does not exist (HTTP 404).
        RateLimitError / AuthError / RedditError: Other HTTP failures.
    """
    cleaned = (post_id or "").strip().removeprefix("t3_")
    if not cleaned:
        raise ValueError("post_id must be a non-empty string")
    if limit < 1:
        raise ValueError("limit must be >= 1")
    if depth < 0:
        raise ValueError("depth must be >= 0")

    path = build_comments_path(cleaned)
    params = {
        "limit": min(limit, 100),
        "depth": depth,
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

    return parse_comments_payload(payload, max_depth=depth, limit=limit)
