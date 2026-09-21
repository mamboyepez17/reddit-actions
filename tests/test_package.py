"""Package smoke tests."""

from __future__ import annotations

import reddit_actions
from reddit_actions import (
    Comment,
    Post,
    RateLimitError,
    RedditError,
    RedditHttpClient,
    Settings,
    ThreadAnalysis,
    analyze_thread,
    get_comments,
    get_subreddit_posts,
    search_posts,
)


def test_version_string():
    assert reddit_actions.__version__


def test_public_exports_importable():
    assert issubclass(RateLimitError, RedditError)
    assert RedditHttpClient is not None
    assert Settings is not None
    assert Post is not None
    assert Comment is not None
    assert ThreadAnalysis is not None
    assert callable(search_posts)
    assert callable(get_comments)
    assert callable(get_subreddit_posts)
    assert callable(analyze_thread)


def test_cli_version_command():
    from click.testing import CliRunner
    from reddit_actions.cli import cli

    result = CliRunner().invoke(cli, ["version"])
    assert result.exit_code == 0
    assert reddit_actions.__version__ in result.output


def test_library_api_in_all():
    for name in (
        "search_posts",
        "get_comments",
        "get_subreddit_posts",
        "analyze_thread",
        "ThreadAnalysis",
        "RedditHttpClient",
        "Settings",
        "Post",
        "Comment",
    ):
        assert name in reddit_actions.__all__
