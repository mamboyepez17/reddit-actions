"""Search public Reddit posts via official public JSON endpoints."""

from __future__ import annotations

from typing import Any

from reddit_actions.auth.anonymous import (
    build_search_params,
    build_search_path,
    build_subreddit_search_path,
)
from reddit_actions.config import Settings
from reddit_actions.http_client import RedditHttpClient
from reddit_actions.models import Post
from reddit_actions.parsers.posts import parse_posts_payload

__all__ = ["search_posts"]

_VALID_SORTS = frozenset({"relevance", "hot", "top", "new", "comments"})


def search_posts(
    query: str,
    subreddit: str | None = None,
    sort: str = "relevance",
    limit: int = 25,
    *,
    client: RedditHttpClient | None = None,
    settings: Settings | None = None,
    extra_params: dict[str, Any] | None = None,
) -> list[Post]:
    """Search public Reddit posts.

    Args:
        query: Search query text.
        subreddit: Optional subreddit name (with or without r/).
        sort: Reddit search sort (relevance, hot, top, new, comments).
        limit: Max posts to request (capped by public API to 100).
        client: Optional pre-built HTTP client (tests / reuse).
        settings: Optional settings when constructing an internal client.
        extra_params: Extra query params passed to Reddit.

    Returns:
        List of Post models. Empty list when there are no results.

    Raises:
        ValueError: Invalid sort or limit.
        RateLimitError / AuthError / NotFoundError / RedditError: HTTP failures.
    """
    cleaned_query = (query or "").strip()
    if not cleaned_query:
        raise ValueError("query must be a non-empty string")
    if sort not in _VALID_SORTS:
        raise ValueError(f"Invalid sort {sort!r}. Expected one of {sorted(_VALID_SORTS)}")
    if limit < 1:
        raise ValueError("limit must be >= 1")

    if subreddit:
        path = build_subreddit_search_path(subreddit)
        # Subreddit search still accepts q + limit; restrict via path.
        params = build_search_params(
            cleaned_query,
            subreddit=None,
            sort=sort,
            limit=limit,
            **(extra_params or {}),
        )
    else:
        path = build_search_path()
        params = build_search_params(
            cleaned_query,
            sort=sort,
            limit=limit,
            **(extra_params or {}),
        )

    owns_client = client is None
    http = client or RedditHttpClient(settings)
    try:
        payload = http.get_json(path, params=params)
    finally:
        if owns_client:
            http.close()

    return parse_posts_payload(payload)
