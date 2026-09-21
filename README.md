# Reddit Actions

### Read-only Reddit toolkit for Python, CLI and AI agents

Explore **public** Reddit posts and comments with a free, open-source toolkit that runs locally. Access depends on Reddit availability and terms.

The toolkit is free and open source. Reddit access depends on approval, authentication, applicable terms and rate limits; availability and zero-cost access are not guaranteed.

Library · CLI · Optional MCP server · Python 3.11+

[![Python](https://img.shields.io/badge/Python-3.11%2B-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://www.python.org/)
[![License](https://img.shields.io/badge/License-MIT-2ea44f?style=for-the-badge)](LICENSE)
[![Tests](https://img.shields.io/badge/Tests-138%20passing-brightgreen?style=for-the-badge)](#development)
[![CI](https://img.shields.io/badge/CI-GitHub%20Actions-blue?style=for-the-badge&logo=githubactions)](.github/workflows/ci.yml)

---

## Table of contents

- [Why this project?](#why-this-project)
- [What you get](#what-you-get)
- [Quick start](#quick-start)
- [Session cookies (optional authentication)](#session-cookies-optional-authentication)
- [Verify your setup](#verify-your-setup)
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

**Reddit Actions** provides a Python library, CLI and optional MCP server for reading public Reddit posts and comments.

Reddit offers free access for eligible applications as well as paid access. Its current documentation lists **100 queries per minute per OAuth client ID** for eligible free access, averaged over a 10-minute window. API access requires approval; this is not an entitlement provided by installing this toolkit.

- [Reddit Data API Wiki](https://support.reddithelp.com/hc/en-us/articles/16160319875092-Reddit-Data-API-Wiki)
- [Responsible Builder Policy](https://support.reddithelp.com/hc/en-us/articles/42728983564564-Responsible-Builder-Policy)

**Current implementation (experimental access):** public JSON endpoints with a descriptive User-Agent and optional session cookies. OAuth is an optional future integration and is **not implemented** in this release. The current implementation does not require OAuth credentials to run, but that does not remove Reddit’s access requirements. The OAuth quota above does not describe or guarantee the quota of the current cookie-based client. Cookies do not guarantee access or replace required approval.

**Product promise:** a free local tool for exploring public Reddit posts and comments through a consistent, read-only interface. Access depends on Reddit availability and terms. No guarantee of unrestricted access, complete historical coverage, or zero Reddit fees for every use case.

**Not in v1:** posting, voting, spam bots, mass scraping, Reddit Enterprise.

### Planned improvements

The next development priorities are secret protection, reliable request pacing and errors, pagination with explicit partial results, temporary local caching, and guided setup diagnostics. Saved searches and incremental tracking follow. These features aim to make setup easier and reduce unnecessary requests; they do not increase Reddit’s authorized quota. OAuth remains an optional integration rather than a prerequisite for these improvements. These are roadmap items, not features shipped in this release.

The intended deployment is local: no shared service account or hosted credential pool. Persistent access denials should stop requests and produce a clear diagnostic; this stop behavior is planned, while the current client still performs bounded retries on 401/403.

---

## What you get

| Capability | Library | CLI | MCP |
|---|:---:|:---:|:---:|
| Search posts | `search_posts` | `reddit-actions search` | `reddit_search` |
| Comments tree | `get_comments` | `reddit-actions comments` | `reddit_comments` |
| Subreddit listing | `get_subreddit_posts` | `reddit-actions subreddit` | `reddit_subreddit` |
| Thread analysis | `analyze_thread` | `reddit-actions thread` | `reddit_thread` |

Design principles:

- **Explicit error handling** — typed HTTP exceptions in the library and structured errors in MCP
- **Type-hinted** public API
- **Mocked tests** — no live Reddit required for CI
- **Secrets stay local** — `.env` is gitignored
- **Optional session cookies** — availability depends on Reddit; a **403** may still occur

---

## Quick start

```bash
git clone https://github.com/mamboyepez17/reddit-actions.git
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

Minimum `.env` (always required):

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

## Session cookies (optional authentication)

Some networks (datacenter IPs, aggressive bot detection) get **HTTP 403** on Reddit’s public JSON even with a valid User-Agent. That is platform protection, not a bug in this library.

For permitted session-based access, configure your own browser session cookies in a **local** `.env` file. This does not bypass access restrictions or guarantee service availability.

`.env` is gitignored — never commit cookies, never paste them in issues/chats.

### Step 1 — Log in

Open [reddit.com](https://www.reddit.com) in your browser and **sign in**.

### Step 2 — Open DevTools cookies

1. Press `F12` → **Application** tab  
2. Left sidebar: **Storage → Cookies → `https://www.reddit.com`**  
3. Select that origin so it is highlighted  

If the table on the right shows `google.com` / `accounts.google.com` domains, you are looking at the wrong cookie store. Re-click `https://www.reddit.com`.

### Step 3 — Filter and copy the session cookies

1. In the **Filter** box type: `session`  
2. You should see rows like:

| Name | Domain | Needed? |
|------|--------|---------|
| `reddit_session` | `.reddit.com` | **Yes (required)** — long JWT, often starts with `eyJ...` |
| `session_tracker` | `.reddit.com` | Recommended |
| `token_v2` | `.reddit.com` | Optional, if present |

3. Click the **`reddit_session`** row  
4. In the preview panel below, copy the **full Value** (the table column is truncated)

### Step 4 — Paste into `.env`

```env
REDDIT_USER_AGENT=reddit-actions/0.1 (by u/yourname; research)
REDDIT_SESSION_COOKIE=paste_full_reddit_session_value_here
REDDIT_SESSION_TRACKER=paste_session_tracker_value_here
```

You may paste either:

- raw values only (`eyJhbGciOi...`), or  
- full `name=value` strings (`reddit_session=eyJ...`) — prefixes are stripped automatically

**Alternative (often easier):** `F12` → **Network** → reload Reddit → click any `www.reddit.com` request → **Headers → Request Headers → Cookie** → copy the entire `Cookie:` string:

```env
REDDIT_COOKIE_HEADER=reddit_session=...; session_tracker=...; other=...
```

`REDDIT_COOKIE_HEADER` overrides the individual cookie variables.

### Step 5 — Cookie expired or blocked again?

Session cookies expire. If requests return **403** again:

1. Verify that your session is valid and your intended access is permitted.
2. If the session expired, sign in and update your local cookie values.
3. If access remains denied, stop and resolve access with Reddit; repeated attempts or account switching are not a solution.

No code changes needed.

### Security checklist

- [ ] `.env` stays on your machine only  
- [ ] `.env` is listed in `.gitignore` (default in this repo)  
- [ ] Do not paste cookies into GitHub issues, README, or chats  
- [ ] Treat session cookies as credentials; never share them with other users or a hosted credential pool

---

## Verify your setup

```powershell
# from project root, with .venv activated
.venv\Scripts\python.exe -c "from reddit_actions import search_posts; posts=search_posts('python', limit=5); print(f'{len(posts)} posts'); [print(p.score, p.title[:60]) for p in posts]"
```

When access is available: a list of real post titles from Reddit. A successful request only verifies access at that moment.

CLI smoke test:

```powershell
reddit-actions search "python" --limit 5
reddit-actions subreddit --subreddit python --sort hot --limit 5
reddit-actions comments <post_id> --limit 10
```

If you see `Error: Blocked or unauthorized (403)`, check session validity and access eligibility (section above). Refreshing cookies may not resolve the denial.

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

Example MCP config (stdio) — copy the **absolute path** of your venv scripts:

```json
{
  "mcpServers": {
    "reddit-actions": {
      "command": "C:/path/to/reddit-actions/.venv/Scripts/reddit-actions-mcp.exe",
      "env": {
        "REDDIT_USER_AGENT": "reddit-actions/0.1 (by u/yourname; research)",
        "REDDIT_SESSION_COOKIE": "paste_your_session_cookie_here"
      }
    }
  }
}
```

Prefer putting secrets in the process environment or a local env file — not in committed JSON.

---

## Models

**`Post`** — id, title, selftext, subreddit, author, score, upvote_ratio, num_comments, permalink, url, created_utc, nsfw  

**`Comment`** — id, parent_id, body, author, score, created_utc, depth, controversiality, permalink  

**`ThreadAnalysis`** — post, comments + helpers: `comment_count`, `total_comment_score`, `comments_by_depth`, `top_comments(n)`, `controversial_count`

```python
post.full_permalink  # always absolute reddit.com URL
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
- Use only within your approved purpose and applicable Reddit terms; research and commercial use have additional requirements.
- Do **not** mass-rehost content or hammer endpoints
- Always identify your app in the User-Agent
- Session cookies do not grant additional permission or guaranteed access.
- The configured delay is local client behavior, not a Reddit quota. The current limiter is per client instance; separate calls that construct fresh clients do not share it.

---

## Project layout

```
reddit-actions/
├── reddit_actions/
│   ├── config.py           # pydantic-settings + .env + session cookies
│   ├── http_client.py      # UA, delay, retries, typed errors, Cookie header
│   ├── models.py           # Post, Comment, ThreadAnalysis
│   ├── auth/anonymous.py   # public JSON path builders
│   ├── scrapers/           # search · comments · subreddit
│   ├── parsers/            # Reddit JSON → models
│   ├── analytics/          # analyze_thread
│   ├── cli.py              # click CLI
│   └── mcp_server.py       # optional MCP tools
├── tests/                  # pytest + respx (mocked HTTP)
├── .github/workflows/ci.yml
├── .env.example            # template — copy to .env
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

**Reddit Actions** — a consistent interface for public Reddit posts and comments.
