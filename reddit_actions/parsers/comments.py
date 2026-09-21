"""Parse Reddit comments JSON into Comment models."""

from __future__ import annotations

import logging
from typing import Any

from reddit_actions.models import Comment

logger = logging.getLogger(__name__)

__all__ = ["parse_reddit_comment", "parse_comments_payload"]


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


def parse_reddit_comment(
    raw: dict[str, Any],
    *,
    depth: int = 0,
    fallback_permalink: str = "",
) -> Comment | None:
    """Map one Reddit comment-like object to Comment. Returns None if unusable."""
    if not isinstance(raw, dict):
        return None

    data = raw.get("data") if isinstance(raw.get("data"), dict) else raw
    if not isinstance(data, dict):
        return None

    # "more" stubs and non-comment kinds have no body/id worth keeping
    kind = raw.get("kind")
    if kind is not None and kind not in ("t1", "Comment"):
        return None

    comment_id = _as_str(data.get("id")).removeprefix("t1_")
    if not comment_id:
        return None

    body = data.get("body")
    # Distinguish missing body from explicit empty/removed text
    if body is None and "body_html" not in data:
        logger.debug("Skipping comment without body: id=%s", comment_id)
        return None

    permalink = _as_str(data.get("permalink"))
    if not permalink and fallback_permalink:
        permalink = f"{fallback_permalink.rstrip('/')}/{comment_id}/"

    parent_id = _as_str(data.get("parent_id"))
    if not parent_id:
        link_id = _as_str(data.get("link_id"))
        parent_id = link_id or f"t3_{comment_id}"

    return Comment(
        id=comment_id,
        parent_id=parent_id,
        body=_as_str(body, default="[deleted]"),
        author=_as_str(data.get("author"), default="[deleted]"),
        score=_as_int(data.get("score")),
        created_utc=_as_float(data.get("created_utc")),
        depth=_as_int(depth),
        controversiality=_as_int(data.get("controversiality")),
        permalink=permalink,
    )


def _walk_comment_children(
    children: Any,
    *,
    depth: int,
    max_depth: int,
    fallback_permalink: str,
    out: list[Comment],
    limit: int,
) -> None:
    if not isinstance(children, list):
        return
    if depth > max_depth:
        return

    for child in children:
        if len(out) >= limit:
            return
        if not isinstance(child, dict):
            continue
        try:
            comment = parse_reddit_comment(
                child,
                depth=depth,
                fallback_permalink=fallback_permalink,
            )
        except Exception:  # noqa: BLE001 — never crash the batch
            logger.warning("Failed to parse a comment node", exc_info=True)
            continue
        if comment is not None:
            out.append(comment)

        data = child.get("data") if isinstance(child.get("data"), dict) else None
        replies = data.get("replies") if data else None
        if replies and isinstance(replies, dict):
            nested = replies.get("data", {}).get("children") if isinstance(replies.get("data"), dict) else None
            _walk_comment_children(
                nested,
                depth=depth + 1,
                max_depth=max_depth,
                fallback_permalink=fallback_permalink,
                out=out,
                limit=limit,
            )
        elif isinstance(replies, list):
            _walk_comment_children(
                replies,
                depth=depth + 1,
                max_depth=max_depth,
                fallback_permalink=fallback_permalink,
                out=out,
                limit=limit,
            )


def parse_comments_payload(
    payload: Any,
    *,
    max_depth: int = 2,
    limit: int = 50,
) -> list[Comment]:
    """Extract comments from a Reddit post-comments JSON payload.

    Reddit returns a list: [post_listing, comments_listing]. Comment trees are
    nested under each child's data.replies. "more" stubs are skipped.
    """
    if not isinstance(payload, list) or len(payload) < 2:
        # Some errors/edge cases return a dict instead
        return []

    comments_listing = payload[1]
    if not isinstance(comments_listing, dict):
        return []

    data = comments_listing.get("data")
    if not isinstance(data, dict):
        return []

    children = data.get("children")
    if not isinstance(children, list):
        return []

    # Best-effort permalink prefix from the post listing (payload[0])
    fallback_permalink = ""
    if isinstance(payload[0], dict):
        post_data = payload[0].get("data")
        if isinstance(post_data, dict):
            post_children = post_data.get("children")
            if isinstance(post_children, list) and post_children:
                first = post_children[0]
                if isinstance(first, dict) and isinstance(first.get("data"), dict):
                    fallback_permalink = _as_str(first["data"].get("permalink"))

    out: list[Comment] = []
    _walk_comment_children(
        children,
        depth=0,
        max_depth=max_depth,
        fallback_permalink=fallback_permalink,
        out=out,
        limit=limit,
    )
    return out
