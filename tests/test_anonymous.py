"""Tests for anonymous public JSON path/param builders."""

from __future__ import annotations

import pytest
from reddit_actions.auth.anonymous import (
    build_comments_path,
    build_search_params,
    build_search_path,
    build_subreddit_search_path,
    build_subreddit_sort_path,
)


def test_build_search_path():
    assert build_search_path() == "/search.json"


def test_build_subreddit_search_path_strips_r_prefix():
    assert build_subreddit_search_path("r/python") == "/r/python/search.json"
    assert build_subreddit_search_path("python") == "/r/python/search.json"


def test_build_comments_path_strips_t3():
    assert build_comments_path("t3_abc123") == "/comments/abc123.json"
    assert build_comments_path("abc123") == "/comments/abc123.json"


def test_build_subreddit_sort_path():
    assert build_subreddit_sort_path("python", "hot") == "/r/python/hot.json"
    with pytest.raises(ValueError):
        build_subreddit_sort_path("python", "nope")


def test_build_search_params_defaults():
    params = build_search_params("crypto")
    assert params["q"] == "crypto"
    assert params["limit"] == 25
    assert params["sort"] == "relevance"
    assert params["raw_json"] == 1
    assert "restrict_sr" not in params


def test_build_search_params_subreddit_and_limit_cap():
    params = build_search_params("eth", subreddit="r/cryptocurrency", limit=1000)
    assert params["restrict_sr"] == 1
    assert params["sr_name"] == "cryptocurrency"
    assert params["limit"] == 100


def test_build_search_params_limit_must_be_positive():
    with pytest.raises(ValueError):
        build_search_params("x", limit=0)
