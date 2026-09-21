"""B7 release quality checks (README, CI, gitignore, public API)."""

from __future__ import annotations

from pathlib import Path

import reddit_actions
from reddit_actions import (
    analyze_thread,
    get_comments,
    get_subreddit_posts,
    search_posts,
)

ROOT = Path(__file__).resolve().parents[1]


def test_readme_exists_and_english_public_surface():
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    assert "Reddit Actions" in readme
    assert "search_posts" in readme
    assert "get_comments" in readme
    assert "get_subreddit_posts" in readme
    assert "analyze_thread" in readme
    assert "reddit-actions" in readme
    assert "MIT" in readme
    # Free toolkit messaging — paid API is context, not a requirement
    lower = readme.lower()
    assert (
        "paid api" in lower
        or "paid reddit api" in lower
        or "without a paid" in lower
        or "no paid" in lower
    )
    assert "REDDIT_USER_AGENT" in readme
    assert "Rate limit" in readme or "rate limit" in readme.lower()


def test_env_example_has_required_key():
    text = (ROOT / ".env.example").read_text(encoding="utf-8")
    assert "REDDIT_USER_AGENT=" in text
    assert "REDDIT_MIN_DELAY=" in text


def test_license_mit():
    text = (ROOT / "LICENSE").read_text(encoding="utf-8")
    assert "MIT License" in text
    assert "Permission is hereby granted" in text


def test_ci_workflow_present_and_valid_shape():
    text = (ROOT / ".github" / "workflows" / "ci.yml").read_text(encoding="utf-8")
    assert "pytest" in text
    assert "ruff" in text
    assert "ubuntu-latest" in text
    assert "windows-latest" in text
    assert "3.11" in text
    assert "3.12" in text
    assert "3.13" in text
    assert 'REDDIT_USER_AGENT' in text


def test_gitignore_excludes_internal_planning():
    text = (ROOT / ".gitignore").read_text(encoding="utf-8")
    assert "PROMPT_ARRANQUE.md" in text
    assert "IMPLEMENTATION_PLAN.md" in text
    assert ".env" in text
    assert "Implementation_Plan/" in text


def test_trendscope_quality_bar_imports():
    # Ready for: from reddit_actions import search_posts, get_comments
    assert callable(search_posts)
    assert callable(get_comments)
    assert callable(get_subreddit_posts)
    assert callable(analyze_thread)
    for name in (
        "search_posts",
        "get_comments",
        "get_subreddit_posts",
        "analyze_thread",
        "ThreadAnalysis",
        "RedditHttpClient",
        "Settings",
    ):
        assert name in reddit_actions.__all__


def test_version_exported():
    assert reddit_actions.__version__
