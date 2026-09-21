"""Domain models for Reddit public data."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True, slots=True)
class Post:
    """A Reddit post (submission) from public JSON."""

    id: str
    title: str
    selftext: str
    subreddit: str
    author: str
    score: int
    upvote_ratio: float
    num_comments: int
    permalink: str
    url: str
    created_utc: float
    nsfw: bool

    @property
    def full_permalink(self) -> str:
        """Absolute permalink on reddit.com."""
        if self.permalink.startswith("http"):
            return self.permalink
        return f"https://www.reddit.com{self.permalink}"


@dataclass(frozen=True, slots=True)
class Comment:
    """A Reddit comment node from public JSON."""

    id: str
    parent_id: str
    body: str
    author: str
    score: int
    created_utc: float
    depth: int
    controversiality: int
    permalink: str

    @property
    def full_permalink(self) -> str:
        if self.permalink.startswith("http"):
            return self.permalink
        return f"https://www.reddit.com{self.permalink}"


@dataclass(frozen=True, slots=True)
class ThreadAnalysis:
    """Aggregated view of a post + its public comment tree."""

    post: Post | None
    comments: tuple[Comment, ...] = field(default_factory=tuple)

    @property
    def comment_count(self) -> int:
        return len(self.comments)

    @property
    def total_comment_score(self) -> int:
        return sum(c.score for c in self.comments)

    @property
    def comments_by_depth(self) -> dict[int, int]:
        counts: dict[int, int] = {}
        for c in self.comments:
            counts[c.depth] = counts.get(c.depth, 0) + 1
        return counts

    def top_comments(self, n: int = 5) -> list[Comment]:
        return sorted(self.comments, key=lambda c: c.score, reverse=True)[: max(n, 0)]

    @property
    def controversial_count(self) -> int:
        return sum(1 for c in self.comments if c.controversiality > 0)
