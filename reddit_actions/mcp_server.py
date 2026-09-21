"""Optional MCP server exposing Reddit Actions tools.

Handlers are plain functions returning structured dicts so they can be tested
without a live MCP runtime. Server construction requires the optional `mcp`
extra: pip install "reddit-actions[mcp]".
"""

from __future__ import annotations

from typing import Any

from pydantic import ValidationError

from reddit_actions.analytics import analyze_thread
from reddit_actions.http_client import (
    AuthError,
    NotFoundError,
    RateLimitError,
    RedditError,
)
from reddit_actions.models import Comment, Post, ThreadAnalysis
from reddit_actions.scrapers import get_comments, get_subreddit_posts, search_posts

__all__ = [
    "TOOL_SPECS",
    "tool_reddit_search",
    "tool_reddit_comments",
    "tool_reddit_thread",
    "tool_reddit_subreddit",
    "create_server",
    "run_server",
    "SERVER_NAME",
]

SERVER_NAME = "reddit-actions"

TOOL_SPECS: tuple[dict[str, str], ...] = (
    {
        "name": "reddit_search",
        "description": "Search public Reddit posts, subject to Reddit access availability.",
    },
    {
        "name": "reddit_comments",
        "description": "Fetch public comments for a Reddit post id.",
    },
    {
        "name": "reddit_thread",
        "description": "Analyze a Reddit thread: post + comment aggregates.",
    },
    {
        "name": "reddit_subreddit",
        "description": "List public posts from a subreddit (hot/new/top/...).",
    },
)


def _error_payload(exc: Exception, *, tool: str) -> dict[str, Any]:
    if isinstance(exc, RateLimitError):
        kind = "rate_limit"
    elif isinstance(exc, NotFoundError):
        kind = "not_found"
    elif isinstance(exc, AuthError):
        kind = "auth"
    elif isinstance(exc, RedditError):
        kind = "reddit_error"
    elif isinstance(exc, ValidationError):
        kind = "config"
    elif isinstance(exc, ValueError):
        kind = "validation"
    else:
        kind = "unexpected"
    return {
        "ok": False,
        "tool": tool,
        "error": {
            "kind": kind,
            "type": type(exc).__name__,
            "message": str(exc) or type(exc).__name__,
        },
    }


def _post_payload(post: Post) -> dict[str, Any]:
    return {
        "id": post.id,
        "title": post.title,
        "subreddit": post.subreddit,
        "author": post.author,
        "score": post.score,
        "upvote_ratio": post.upvote_ratio,
        "num_comments": post.num_comments,
        "permalink": post.full_permalink,
        "url": post.url,
        "created_utc": post.created_utc,
        "nsfw": post.nsfw,
        "selftext": post.selftext,
    }


def _comment_payload(comment: Comment) -> dict[str, Any]:
    return {
        "id": comment.id,
        "parent_id": comment.parent_id,
        "body": comment.body,
        "author": comment.author,
        "score": comment.score,
        "depth": comment.depth,
        "controversiality": comment.controversiality,
        "permalink": comment.full_permalink,
        "created_utc": comment.created_utc,
    }


def _thread_payload(analysis: ThreadAnalysis) -> dict[str, Any]:
    return {
        "post": _post_payload(analysis.post) if analysis.post else None,
        "comment_count": analysis.comment_count,
        "total_comment_score": analysis.total_comment_score,
        "comments_by_depth": {str(k): v for k, v in sorted(analysis.comments_by_depth.items())},
        "controversial_count": analysis.controversial_count,
        "top_comments": [_comment_payload(c) for c in analysis.top_comments(5)],
        "comments": [_comment_payload(c) for c in analysis.comments],
    }


def tool_reddit_search(
    query: str,
    subreddit: str | None = None,
    sort: str = "relevance",
    limit: int = 25,
) -> dict[str, Any]:
    """Search public posts. Returns {ok, posts|error}."""
    try:
        posts = search_posts(query, subreddit=subreddit, sort=sort, limit=limit)
        return {
            "ok": True,
            "tool": "reddit_search",
            "count": len(posts),
            "posts": [_post_payload(p) for p in posts],
        }
    except Exception as exc:  # noqa: BLE001 — MCP tools never crash the server
        return _error_payload(exc, tool="reddit_search")


def tool_reddit_comments(
    post_id: str,
    limit: int = 50,
    depth: int = 2,
) -> dict[str, Any]:
    """Fetch public comments. Returns {ok, comments|error}."""
    try:
        comments = get_comments(post_id, limit=limit, depth=depth)
        return {
            "ok": True,
            "tool": "reddit_comments",
            "count": len(comments),
            "comments": [_comment_payload(c) for c in comments],
        }
    except Exception as exc:  # noqa: BLE001
        return _error_payload(exc, tool="reddit_comments")


def tool_reddit_thread(
    post_id: str,
    comment_limit: int = 50,
    comment_depth: int = 2,
) -> dict[str, Any]:
    """Analyze a thread. Returns {ok, thread aggregates|error}."""
    try:
        analysis = analyze_thread(
            post_id,
            comment_limit=comment_limit,
            comment_depth=comment_depth,
        )
        return {
            "ok": True,
            "tool": "reddit_thread",
            "thread": _thread_payload(analysis),
        }
    except Exception as exc:  # noqa: BLE001
        return _error_payload(exc, tool="reddit_thread")


def tool_reddit_subreddit(
    subreddit: str = "python",
    sort: str = "hot",
    limit: int = 25,
) -> dict[str, Any]:
    """List subreddit posts. Returns {ok, posts|error}."""
    try:
        posts = get_subreddit_posts(subreddit, sort=sort, limit=limit)
        return {
            "ok": True,
            "tool": "reddit_subreddit",
            "subreddit": subreddit.removeprefix("r/"),
            "sort": sort,
            "count": len(posts),
            "posts": [_post_payload(p) for p in posts],
        }
    except Exception as exc:  # noqa: BLE001
        return _error_payload(exc, tool="reddit_subreddit")


def registered_tool_names() -> list[str]:
    return [spec["name"] for spec in TOOL_SPECS]


def create_server():
    """Build an MCP server instance. Requires the optional mcp package."""
    try:
        try:
            from mcp.server.mcpserver import MCPServer
        except ImportError:
            from mcp.server.fastmcp import FastMCP as MCPServer
    except ImportError as exc:  # pragma: no cover
        raise RuntimeError(
            "MCP extra not installed. Run: pip install \"reddit-actions[mcp]\""
        ) from exc

    server = MCPServer(
        SERVER_NAME,
        instructions=(
            "Free, open-source Reddit toolkit (public JSON; access subject to Reddit terms). "
            "Read-only: search posts, comments, threads, subreddit listings."
        ),
    )

    @server.tool()
    def reddit_search(
        query: str,
        subreddit: str | None = None,
        sort: str = "relevance",
        limit: int = 25,
    ) -> dict[str, Any]:
        """Search public Reddit posts."""
        return tool_reddit_search(query, subreddit=subreddit, sort=sort, limit=limit)

    @server.tool()
    def reddit_comments(post_id: str, limit: int = 50, depth: int = 2) -> dict[str, Any]:
        """Fetch public comments for a post id (with or without t3_)."""
        return tool_reddit_comments(post_id, limit=limit, depth=depth)

    @server.tool()
    def reddit_thread(post_id: str, comment_limit: int = 50, comment_depth: int = 2) -> dict[str, Any]:
        """Analyze a public Reddit thread (post + comment aggregates)."""
        return tool_reddit_thread(post_id, comment_limit=comment_limit, comment_depth=comment_depth)

    @server.tool()
    def reddit_subreddit(subreddit: str = "python", sort: str = "hot", limit: int = 25) -> dict[str, Any]:
        """List public posts from a subreddit."""
        return tool_reddit_subreddit(subreddit, sort=sort, limit=limit)

    return server


def run_server() -> None:
    """CLI entrypoint for the MCP server (stdio)."""
    server = create_server()
    if hasattr(server, "run"):
        server.run()
    else:  # pragma: no cover
        raise RuntimeError("MCP server object has no run() method")


if __name__ == "__main__":
    run_server()

