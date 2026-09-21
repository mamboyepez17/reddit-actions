"""CLI search is implemented in B5 — replace old placeholder expectations."""

from __future__ import annotations

import httpx
import respx
from click.testing import CliRunner
from reddit_actions.cli import cli


@respx.mock
def test_search_command_is_implemented():
    respx.get("https://www.reddit.com/search.json").mock(
        return_value=httpx.Response(
            200,
            json={
                "kind": "Listing",
                "data": {
                    "children": [
                        {
                            "kind": "t3",
                            "data": {
                                "id": "x1",
                                "title": "Implemented",
                                "subreddit": "python",
                                "author": "a",
                                "score": 1,
                                "num_comments": 0,
                                "permalink": "/r/python/comments/x1/implemented/",
                                "url": "",
                                "created_utc": 0.0,
                                "selftext": "",
                                "upvote_ratio": 1.0,
                                "over_18": False,
                            },
                        }
                    ]
                },
            },
        )
    )
    result = CliRunner().invoke(cli, ["search", "implemented"])
    assert result.exit_code == 0
    assert "Implemented" in result.output
    assert "not implemented" not in result.output.lower()
