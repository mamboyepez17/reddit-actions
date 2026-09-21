"""reddit_actions — Read-only Reddit toolkit (posts, comments, CLI, MCP)."""

from importlib.metadata import PackageNotFoundError, version

try:
    __version__ = version("reddit-actions")
except PackageNotFoundError:
    __version__ = "0.1.0"

from .analytics import analyze_thread
from .config import Settings, get_settings, reset_settings_cache
from .http_client import (
    AuthError,
    NotFoundError,
    RateLimitError,
    RedditError,
    RedditHttpClient,
)
from .models import Comment, Post, ThreadAnalysis
from .scrapers import get_comments, get_subreddit_posts, search_posts

__all__ = [
    "__version__",
    "Settings",
    "get_settings",
    "reset_settings_cache",
    "RedditHttpClient",
    "RedditError",
    "RateLimitError",
    "AuthError",
    "NotFoundError",
    "Post",
    "Comment",
    "ThreadAnalysis",
    "search_posts",
    "get_comments",
    "get_subreddit_posts",
    "analyze_thread",
]
