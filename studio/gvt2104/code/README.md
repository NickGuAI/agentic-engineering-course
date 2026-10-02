# Agent News Digest

A single-page web app that aggregates the latest updates from **Anthropic** and
**OpenAI**, summarizes them, and ranks them for one audience in particular:
**people who build AI agents**. You rate each summary block (👍 / 👎 + an optional
note) and the ranking function learns from that feedback and re-orders the digest.

Built to satisfy [`../delegation-card.md`](../delegation-card.md).

## Sources

| Source | URL | How it's read |
|--------|-----|---------------|
| Anthropic News | https://www.anthropic.com/news | HTML card parsing |
| Anthropic Engineering | https://www.anthropic.com/engineering | HTML card parsing |
| OpenAI News | https://openai.com/news/ | RSS feed (`/news/rss.xml`) |

If a source can't be reached or its markup changes, that source falls back to the
on-disk cache and then to bundled seed data (`seed_data.py`), so the page always
renders. Well-known posts are enriched with a summary from the seed when the list
page doesn't include one.

## Run it

No dependencies — just Python 3.9+ (standard library only).

```bash
cd code
python3 server.py
# open http://localhost:8765
```

Defaults to port **8765**; if it's taken, the server automatically falls forward
to the next free port and prints the URL it bound to. Override host/port with env
vars: `PORT=9000 HOST=0.0.0.0 python3 server.py` (an explicit `PORT` is honored
exactly and won't fall forward).

## How the ranking works (the success criterion)

Each article is scored by a transparent, inspectable function:

```
score = 1.0 * agent_relevance   # curated keyword match (agents, MCP, tool use, harness, evals, …)
      + 1.5 * recency           # exponential decay, ~45-day half-life
      +       learned_boost      # sum of the tag weights you've trained
```

* Every article is tagged with agent-developer topics (`ranking.py:AGENT_KEYWORDS`).
* **Rating a block** stores your 👍 (+1) / 👎 (−1) and optional note.
* The learned tag weights are recomputed from your *entire* rating history on
  every change (so re-rating is idempotent, never drifts). A 👍 lifts every topic
  on that block; a 👎 buries them. Keywords found in your **note** nudge those
  topics too (at 0.6× weight) — e.g. a note "more MCP + tool-use" boosts `mcp` and
  `tool-use` even on blocks you didn't explicitly vote on.
* The "What the ranker has learned from you" panel shows the current weights live.

Your feedback persists in `data/ratings.json`, so the digest stays personalized
across restarts. "Reset all ratings" clears it.

## API

| Method | Path | Purpose |
|--------|------|---------|
| `GET`  | `/api/articles` | Ranked articles + learned weights (from cache) |
| `POST` | `/api/refresh`  | Re-fetch all sources, then return the ranked list |
| `POST` | `/api/rate`     | Body `{id, rating, note, tags, title}` → persist + re-rank |
| `GET`  | `/api/health`   | Liveness probe |

## Files

```
code/
├── server.py     # stdlib HTTP server: static files + JSON API
├── fetcher.py    # fetch + parse the 3 sources (concurrent, resilient, cached)
├── ranking.py    # tagging + the learning ranking function
├── storage.py    # JSON persistence (ratings + fetch cache)
├── seed_data.py  # bundled fallback articles (offline mode)
├── static/       # index.html, styles.css, app.js
└── data/         # runtime cache + ratings (git-ignored)
```
