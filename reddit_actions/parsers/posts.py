"""Parse Reddit listing/search JSON into Post models."""

from __future__ import annotations

import logging
from typing import Any

from reddit_actions.models import Post

logger = logging.getLogger(__name__)

__all__ = ["parse_reddit_post", "parse_posts_payload"]


def _as_str(value: Any, default: str = "") -> str:
    if value is None:
        return default
    return str(value)


def _as_int(value: Any, default: int = 0) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _as_float(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _as_bool(value: Any, default: bool = False) -> bool:
    if isinstance(value, bool):
        return value
    if value is None:
        return default
    return bool(value)


def parse_reddit_post(raw: dict[str, Any]) -> Post | None:
    """Map one Reddit post-like object to Post. Returns None if unusable."""
    if not isinstance(raw, dict):
        return None

    # Listing items wrap the real post under "data"
    data = raw.get("data") if isinstance(raw.get("data"), dict) else raw
    if not isinstance(data, dict):
        return None

    post_id = _as_str(data.get("id") or data.get("name") or "").removeprefix("t3_")
    title = _as_str(data.get("title"))
    if not post_id or not title:
        logger.debug("Skipping post without id/title: keys=%s", list(data)[:12])
        return None

    permalink = _as_str(data.get("permalink"))
    if not permalink:
        permalink = f"/comments/{post_id}/"

    return Post(
        id=post_id,
        title=title,
        selftext=_as_str(data.get("selftext")),
        subreddit=_as_str(data.get("subreddit")),
        author=_as_str(data.get("author"), default="[deleted]"),
        score=_as_int(data.get("score")),
        upvote_ratio=_as_float(data.get("upvote_ratio"), default=0.0),
        num_comments=_as_int(data.get("num_comments")),
        permalink=permalink,
        url=_as_str(data.get("url") or data.get("url_overridden_by_dest")),
        created_utc=_as_float(data.get("created_utc")),
        nsfw=_as_bool(data.get("over_18") or data.get("nsfw")),
    )


def parse_posts_payload(payload: Any) -> list[Post]:
    """Extract posts from a Reddit search/listing JSON payload.

    Tolerates missing/partial fields and bad items: skips them, never raises
    for individual malformed children.
    """
    if not isinstance(payload, dict):
        return []

    data = payload.get("data")
    if not isinstance(data, dict):
        return []

    children = data.get("children")
    if not isinstance(children, list):
        return []

    posts: list[Post] = []
    for child in children:
        try:
            post = parse_reddit_post(child)
        except Exception:  # noqa: BLE001 — never crash the batch
            logger.warning("Failed to parse a post child", exc_info=True)
            continue
        if post is not None:
            posts.append(post)
    return posts
