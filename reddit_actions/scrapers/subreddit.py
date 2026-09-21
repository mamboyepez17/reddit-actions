"""List public posts from a subreddit via Reddit JSON endpoints."""

from __future__ import annotations

from typing import Any

from reddit_actions.auth.anonymous import (
    VALID_SORTS,
    build_subreddit_sort_path,
)
from reddit_actions.config import Settings
from reddit_actions.http_client import RedditHttpClient
from reddit_actions.models import Post
from reddit_actions.parsers.posts import parse_posts_payload

__all__ = ["get_subreddit_posts"]


def get_subreddit_posts(
    subreddit: str,
    sort: str = "hot",
    limit: int = 25,
    *,
    client: RedditHttpClient | None = None,
    settings: Settings | None = None,
    extra_params: dict[str, Any] | None = None,
) -> list[Post]:
    """List public posts from a subreddit.

    Args:
        subreddit: Subreddit name with or without r/.
        sort: One of hot, new, top, rising, controversial.
        limit: Max posts to return.
        client: Optional pre-built HTTP client.
        settings: Optional settings when constructing an internal client.
        extra_params: Extra query params (e.g. t=top for weekly top).

    Returns:
        List of Post models. Empty list when the listing is empty.

    Raises:
        ValueError: Invalid subreddit, sort or limit.
        NotFoundError: Subreddit does not exist (HTTP 404).
        RateLimitError / AuthError / RedditError: Other HTTP failures.
    """
    name = (subreddit or "").strip().removeprefix("r/").strip("/")
    if not name:
        raise ValueError("subreddit must be a non-empty string")
    if sort not in VALID_SORTS:
        raise ValueError(f"Invalid sort {sort!r}. Expected one of {sorted(VALID_SORTS)}")
    if limit < 1:
        raise ValueError("limit must be >= 1")

    path = build_subreddit_sort_path(name, sort)
    params: dict[str, Any] = {
        "limit": min(limit, 100),
        "raw_json": 1,
    }
    if extra_params:
        params.update(extra_params)

    owns_client = client is None
    http = client or RedditHttpClient(settings)
    try:
        payload = http.get_json(path, params=params)
    finally:
        if owns_client:
            http.close()

    return parse_posts_payload(payload)
