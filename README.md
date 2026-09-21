# Reddit Actions

### Free Reddit intelligence toolkit

Read **public** posts and comments — no paid Reddit API required.

Library · CLI · Optional MCP server · Python 3.11+

[![Python](https://img.shields.io/badge/Python-3.11%2B-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://www.python.org/)
[![License](https://img.shields.io/badge/License-MIT-2ea44f?style=for-the-badge)](LICENSE)
[![Tests](https://img.shields.io/badge/Tests-129%20passing-brightgreen?style=for-the-badge)](#development)
[![CI](https://img.shields.io/badge/CI-GitHub%20Actions-blue?style=for-the-badge&logo=githubactions)](.github/workflows/ci.yml)
[![API cost](https://img.shields.io/badge/Reddit%20API-Free-ff4500?style=for-the-badge&logo=reddit&logoColor=white)](#why-this-project)

---

## Table of contents

- [Why this project?](#why-this-project)
- [What you get](#what-you-get)
- [Quick start](#quick-start)
- [Library](#library)
- [CLI](#cli)
- [MCP server](#mcp-server)
- [Models](#models)
- [Rate limits & ethics](#rate-limits--ethics)
- [Project layout](#project-layout)
- [Development](#development)
- [License](#license)

---

## Why this project?

Product-grade Reddit access usually means the **paid** official API.  
**Reddit Actions** is a free, read-only toolkit that talks to Reddit’s **public JSON** endpoints with a polite rate limit.

| | Paid Reddit API | Reddit Actions |
|---|---|---|
| Cost | $$$ | **Free** |
| Auth | OAuth app required | **User-Agent only** (v1) |
| Scope | Full write/read surface | **Public read-only** |
| Shape | Official SDK | **Python lib + CLI + MCP** |
| Target users | Commercial integrations | Research, agents, tools like TrendScope |

**Not in v1:** posting, voting, spam bots, mass scraping, Reddit Enterprise.

---

## What you get

| Capability | Library | CLI | MCP |
|---|:---:|:---:|:---:|
| Search posts | `search_posts` | `reddit-actions search` | `reddit_search` |
| Comments tree | `get_comments` | `reddit-actions comments` | `reddit_comments` |
| Subreddit listing | `get_subreddit_posts` | `reddit-actions subreddit` | `reddit_subreddit` |
| Thread analysis | `analyze_thread` | `reddit-actions thread` | `reddit_thread` |

Design principles:

- **Never crash the pipeline** — empty lists + structured errors
- **Type-hinted** public API
- **Mocked tests** — no live Reddit required for CI
- **Secrets stay local** — `.env` is gitignored

---

## Quick start

```bash
git clone https://github.com/<you>/reddit-actions.git
cd reddit-actions
python -m venv .venv
```

**Windows (PowerShell)**

```powershell
.venv\Scripts\Activate.ps1
pip install -e ".[dev]"
copy .env.example .env
```

**Linux / macOS**

```bash
source .venv/bin/activate
pip install -e ".[dev]"
cp .env.example .env
```

Set a descriptive User-Agent in `.env` (required):

```env
REDDIT_USER_AGENT=reddit-actions/0.1 (by u/yourname; research)
REDDIT_MIN_DELAY=1.5
REDDIT_MAX_RETRIES=3
REDDIT_TIMEOUT=30.0
REDDIT_BASE_URL=https://www.reddit.com
```

Optional MCP extras:

```bash
pip install -e ".[mcp,dev]"
```

---

## Library

```python
from reddit_actions import (
    search_posts,
    get_comments,
    get_subreddit_posts,
    analyze_thread,
)

# Search public posts
posts = search_posts("crypto", subreddit="cryptocurrency", limit=10)
for p in posts:
    print(f"[{p.score:>5}] {p.title}")
    print(f"        {p.full_permalink}")

# Comment tree (accepts id with or without t3_)
comments = get_comments("abc123", limit=30, depth=2)
for c in comments:
    print("  " * c.depth + f"[{c.score}] {c.author}: {c.body[:80]}")

# Subreddit listings
hot = get_subreddit_posts("python", sort="hot", limit=10)

# Thread intelligence
analysis = analyze_thread(posts[0].id)
print(analysis.post.title)
print("comments:", analysis.comment_count)
print("by depth:", analysis.comments_by_depth)
for c in analysis.top_comments(3):
    print(f"  top [{c.score}] {c.author}")
```

TrendScope-style import:

```python
from reddit_actions import search_posts, get_comments
```

Errors you may catch:

```python
from reddit_actions import (
    RateLimitError,  # HTTP 429 after retries
    AuthError,       # HTTP 401/403 blocked/unauthorized
    NotFoundError,   # HTTP 404
    RedditError,     # other HTTP/network failures
)
```

---

## CLI

```bash
reddit-actions search "crypto" --subreddit cryptocurrency --limit 10
reddit-actions search "python" --sort top --json
reddit-actions comments <post_id> --limit 30 --depth 2
reddit-actions comments <post_id> --json
reddit-actions thread <post_id>
reddit-actions thread <post_id> --json
reddit-actions subreddit --subreddit python --sort hot --limit 10
reddit-actions version
```

| Flag | Commands | Purpose |
|------|----------|---------|
| `--json` | all data commands | machine-readable output |
| `--limit` | search, comments, thread, subreddit | max items |
| `--depth` | comments, thread | reply tree depth |
| `--sort` | search, subreddit | relevance/hot/new/top/... |
| `--subreddit` | search, subreddit | scope the query |

Failures print to **stderr** and exit **non-zero** (rate limit, 404, missing `REDDIT_USER_AGENT`, invalid args).

---

## MCP server

Expose the same intelligence to AI agents (Claude, MiMo, etc.):

```bash
pip install -e ".[mcp]"
reddit-actions-mcp
# or
python -m reddit_actions.mcp_server
```

| Tool | Returns |
|------|---------|
| `reddit_search` | `{ok, count, posts[]}` |
| `reddit_comments` | `{ok, count, comments[]}` |
| `reddit_thread` | `{ok, thread:{post, aggregates, top_comments}}` |
| `reddit_subreddit` | `{ok, subreddit, sort, posts[]}` |

On failure tools return structured errors (never crash the server):

```json
{
  "ok": false,
  "tool": "reddit_search",
  "error": {
    "kind": "rate_limit",
    "type": "RateLimitError",
    "message": "Rate limited by Reddit after 4 attempts: /search.json"
  }
}
```

Example MCP config (stdio):

```json
{
  "mcpServers": {
    "reddit-actions": {
      "command": "C:/path/to/reddit-actions/.venv/Scripts/reddit-actions-mcp.exe",
      "env": {
        "REDDIT_USER_AGENT": "reddit-actions/0.1 (by u/yourname; research)"
      }
    }
  }
}
```

---

## Models

**`Post`** — id, title, selftext, subreddit, author, score, upvote_ratio, num_comments, permalink, url, created_utc, nsfw  

**`Comment`** — id, parent_id, body, author, score, created_utc, depth, controversiality, permalink  

**`ThreadAnalysis`** — post, comments + helpers: `comment_count`, `total_comment_score`, `comments_by_depth`, `top_comments(n)`, `controversial_count`

```python
analysis.full_permalink  # via Post/Comment: always absolute reddit.com URL
```

---

## Rate limits & ethics

| Setting | Default | Meaning |
|---------|---------|---------|
| `REDDIT_MIN_DELAY` | `1.5` | seconds between requests |
| `REDDIT_MAX_RETRIES` | `3` | retries on 429/403/network |
| `REDDIT_TIMEOUT` | `30.0` | HTTP timeout (s) |

- Honors **`Retry-After`** on 429
- Exponential backoff on 403 / 5xx / network errors
- Intended use: **research, personal agents, product read-only integrations**
- Do **not** mass-rehost content or hammer endpoints
- Always identify your app in the User-Agent

> **Access note:** some networks (especially datacenter IPs) receive HTTP 403 from Reddit on public JSON even with a valid User-Agent. That is platform bot protection, not a parser bug. OAuth / cookie fallback is on the roadmap when anonymous access is blocked.

---

## Project layout

```
reddit-actions/
├── reddit_actions/
│   ├── config.py           # pydantic-settings + .env
│   ├── http_client.py      # UA, delay, retries, typed errors
│   ├── models.py           # Post, Comment, ThreadAnalysis
│   ├── auth/anonymous.py   # public JSON path builders
│   ├── scrapers/           # search · comments · subreddit
│   ├── parsers/            # Reddit JSON → models
│   ├── analytics/          # analyze_thread
│   ├── cli.py              # click CLI
│   └── mcp_server.py       # optional MCP tools
├── tests/                  # pytest + respx (mocked HTTP)
├── .github/workflows/ci.yml
├── .env.example
├── LICENSE
└── README.md
```

---

## Development

```powershell
# tests
.venv\Scripts\python.exe -m pytest tests -v

# lint
.venv\Scripts\python.exe -m ruff check reddit_actions tests
```

CI (GitHub Actions) runs the same on **Ubuntu + Windows** × Python **3.11 / 3.12 / 3.13**.

Quality bar:

- Full test suite green
- Ruff critical rules clean
- No secrets in the repo
- Stable import surface for TrendScope

---

## License

[MIT](LICENSE) — free to use, modify, and distribute.

---

**Reddit Actions** — public Reddit intelligence, free by design.
