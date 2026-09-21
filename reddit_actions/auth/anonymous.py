"""Anonymous access to Reddit public JSON endpoints — no API key.

Endpoints (v1):
- Search: https://www.reddit.com/search.json?q=...
- Sub search: https://www.reddit.com/r/{sub}/search.json?q=...
- Comments: https://www.reddit.com/comments/{post_id}.json
- Sorts: https://www.reddit.com/r/{sub}/{sort}.json
"""

from __future__ import annotations

from typing import Any

VALID_SORTS = frozenset({"hot", "new", "top", "rising", "controversial"})


def build_search_path() -> str:
    """Global search path (public JSON)."""
    return "/search.json"


def build_subreddit_search_path(subreddit: str) -> str:
    """Subreddit-scoped search path."""
    name = subreddit.removeprefix("r/").strip("/")
    return f"/r/{name}/search.json"


def build_comments_path(post_id: str) -> str:
    """Comments path for a post id (with or without t3_ prefix)."""
    pid = post_id.removeprefix("t3_")
    return f"/comments/{pid}.json"


def build_subreddit_sort_path(subreddit: str, sort: str = "hot") -> str:
    """Subreddit listing path for a given sort."""
    name = subreddit.removeprefix("r/").strip("/")
    if sort not in VALID_SORTS:
        raise ValueError(f"Invalid sort {sort!r}. Expected one of {sorted(VALID_SORTS)}")
    return f"/r/{name}/{sort}.json"


def build_search_params(
    query: str,
    *,
    subreddit: str | None = None,
    sort: str = "relevance",
    limit: int = 25,
    **extra: Any,
) -> dict[str, Any]:
    """Build query params for public search/listing endpoints."""
    if limit < 1:
        raise ValueError("limit must be >= 1")
    params: dict[str, Any] = {
        "q": query,
        "limit": min(limit, 100),
        "sort": sort,
        "raw_json": 1,
    }
    if subreddit:
        name = subreddit.removeprefix("r/").strip("/")
        params["restrict_sr"] = 1
        params["sr_name"] = name
    params.update(extra)
    return params
