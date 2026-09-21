"""CLI entry point for Reddit Actions."""

from __future__ import annotations

import json
import sys
from typing import Any

import click
from pydantic import ValidationError

from reddit_actions import __version__
from reddit_actions.analytics import analyze_thread
from reddit_actions.http_client import RedditError
from reddit_actions.models import Comment, Post, ThreadAnalysis
from reddit_actions.scrapers import get_comments, get_subreddit_posts, search_posts


def _fail(message: str, code: int = 1) -> None:
    click.echo(f"Error: {message}", err=True)
    sys.exit(code)


def _guarded(fn, *args, **kwargs):
    try:
        return fn(*args, **kwargs)
    except RedditError as exc:
        _fail(str(exc))
    except ValidationError as exc:
        _fail(f"Configuration error (check REDDIT_USER_AGENT / .env): {exc}")
    except ValueError as exc:
        _fail(str(exc), code=2)


def _post_to_dict(post: Post) -> dict[str, Any]:
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


def _comment_to_dict(comment: Comment) -> dict[str, Any]:
    return {
        "id": comment.id,
        "parent_id": comment.parent_id,
        "author": comment.author,
        "score": comment.score,
        "depth": comment.depth,
        "controversiality": comment.controversiality,
        "permalink": comment.full_permalink,
        "created_utc": comment.created_utc,
        "body": comment.body,
    }


def _thread_to_dict(analysis: ThreadAnalysis) -> dict[str, Any]:
    return {
        "post": _post_to_dict(analysis.post) if analysis.post else None,
        "comment_count": analysis.comment_count,
        "total_comment_score": analysis.total_comment_score,
        "comments_by_depth": {str(k): v for k, v in sorted(analysis.comments_by_depth.items())},
        "controversial_count": analysis.controversial_count,
        "top_comments": [_comment_to_dict(c) for c in analysis.top_comments(5)],
        "comments": [_comment_to_dict(c) for c in analysis.comments],
    }


def _print_posts(posts: list[Post]) -> None:
    if not posts:
        click.echo("No posts found.")
        return
    for post in posts:
        click.echo(f"[{post.score:>5}] {post.title}")
        click.echo(f"        r/{post.subreddit} · u/{post.author} · {post.num_comments} comments")
        click.echo(f"        {post.full_permalink}")


def _print_comments(comments: list[Comment]) -> None:
    if not comments:
        click.echo("No comments found.")
        return
    for comment in comments:
        indent = "  " * comment.depth
        body = comment.body.replace("\n", " ")
        if len(body) > 100:
            body = body[:97] + "..."
        click.echo(f"{indent}[{comment.score:>4}] u/{comment.author}: {body}")


def _print_thread(analysis: ThreadAnalysis) -> None:
    if analysis.post is not None:
        click.echo(f"Post [{analysis.post.score}] {analysis.post.title}")
        click.echo(f"  r/{analysis.post.subreddit} · u/{analysis.post.author}")
        click.echo(f"  {analysis.post.full_permalink}")
    else:
        click.echo("Post: (metadata unavailable)")
    click.echo(f"Comments parsed: {analysis.comment_count}")
    click.echo(f"Total comment score: {analysis.total_comment_score}")
    click.echo(f"Controversial: {analysis.controversial_count}")
    depth = ", ".join(f"{k}:{v}" for k, v in sorted(analysis.comments_by_depth.items()))
    click.echo(f"By depth: {depth or '—'}")
    top = analysis.top_comments(3)
    if top:
        click.echo("Top comments:")
        _print_comments(top)


@click.group()
@click.version_option(__version__, prog_name="reddit-actions")
def cli() -> None:
    """Reddit Actions — free public Reddit intelligence toolkit."""


@cli.command()
def version() -> None:
    """Print package version."""
    click.echo(__version__)


@cli.command()
@click.argument("query")
@click.option("--subreddit", default=None, help="Optional subreddit (with or without r/).")
@click.option("--limit", default=25, show_default=True, type=int, help="Max posts.")
@click.option(
    "--sort",
    default="relevance",
    show_default=True,
    type=click.Choice(["relevance", "hot", "top", "new", "comments"], case_sensitive=False),
)
@click.option("--json", "as_json", is_flag=True, help="Emit JSON instead of text.")
def search(query: str, subreddit: str | None, limit: int, sort: str, as_json: bool) -> None:
    """Search public Reddit posts."""
    posts = _guarded(search_posts, query, subreddit=subreddit, sort=sort, limit=limit)
    if as_json:
        click.echo(json.dumps([_post_to_dict(p) for p in posts], ensure_ascii=False, indent=2))
    else:
        _print_posts(posts)


@cli.command()
@click.argument("post_id")
@click.option("--limit", default=30, show_default=True, type=int)
@click.option("--depth", default=2, show_default=True, type=int)
@click.option("--json", "as_json", is_flag=True, help="Emit JSON instead of text.")
def comments(post_id: str, limit: int, depth: int, as_json: bool) -> None:
    """Fetch comments for a post id (with or without t3_)."""
    items = _guarded(get_comments, post_id, limit=limit, depth=depth)
    if as_json:
        click.echo(json.dumps([_comment_to_dict(c) for c in items], ensure_ascii=False, indent=2))
    else:
        _print_comments(items)


@cli.command()
@click.argument("post_id")
@click.option("--limit", default=50, show_default=True, type=int, help="Max comments to parse.")
@click.option("--depth", default=2, show_default=True, type=int)
@click.option("--json", "as_json", is_flag=True, help="Emit JSON instead of text.")
def thread(post_id: str, limit: int, depth: int, as_json: bool) -> None:
    """Analyze a post thread (post + comment aggregates)."""
    analysis = _guarded(analyze_thread, post_id, comment_limit=limit, comment_depth=depth)
    if as_json:
        click.echo(json.dumps(_thread_to_dict(analysis), ensure_ascii=False, indent=2))
    else:
        _print_thread(analysis)


@cli.command()
@click.option("--subreddit", default="python", show_default=True)
@click.option("--limit", default=10, show_default=True, type=int)
@click.option(
    "--sort",
    default="hot",
    show_default=True,
    type=click.Choice(["hot", "new", "top", "rising", "controversial"], case_sensitive=False),
)
@click.option("--json", "as_json", is_flag=True)
def subreddit(subreddit: str, limit: int, sort: str, as_json: bool) -> None:
    """List public posts from a subreddit."""
    posts = _guarded(get_subreddit_posts, subreddit, sort=sort, limit=limit)
    if as_json:
        click.echo(json.dumps([_post_to_dict(p) for p in posts], ensure_ascii=False, indent=2))
    else:
        _print_posts(posts)


if __name__ == "__main__":
    cli()
