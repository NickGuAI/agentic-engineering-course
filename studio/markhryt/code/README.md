# AI News Digest — recurring ingest → summarize → output job

Bounded, recurring job that watches three pages, summarizes what is new, and writes a digest:

| Source | Requested page | What the job actually reads | Full text? |
|---|---|---|---|
| Anthropic News | https://www.anthropic.com/news | the listing HTML, then each new article page | yes |
| Anthropic Engineering | https://www.anthropic.com/engineering | the listing HTML, then each new article page | yes |
| OpenAI News | https://openai.com/news/ | https://openai.com/news/rss.xml | no — openai.com serves HTTP 403 to non-browser clients, so the feed's title + description is the input |

## Pipeline

```
ingest  (newsdigest/ingest.py)   listing → Article records → dedupe against outputs/state.json → cap N newest/source → fetch bodies
summary (newsdigest/summarize.py) ClaudeSummarizer (structured JSON output) or ExtractiveSummarizer (offline fallback)
output  (newsdigest/output.py)    outputs/digests/<ts>.md + .json, outputs/latest.md, outputs/runs.jsonl (one trace line per run)
```

`newsdigest/job.py` orchestrates one run and the in-process loop; `run_job.py` is the CLI.

## Run

```bash
cd studio/markhryt/code
python3 -m venv .venv && . .venv/bin/activate && pip install -r requirements.txt   # only needed for LLM summaries
export ANTHROPIC_API_KEY=...        # or `ant auth login`; never commit a key

python3 run_job.py --dry-run        # list what would be ingested; writes nothing
python3 run_job.py --no-llm         # offline run: extractive summaries, stdlib only
python3 run_job.py                  # real run: Claude summaries (claude-opus-5 by default)
python3 run_job.py --loop --interval 6h            # keep running in the foreground
python3 run_job.py --sources openai-news --max-per-source 5 --force
```

Flags: `--max-per-source N` (default 10), `--model`, `--force` (ignore seen-state), `--always-write`
(write a digest even when nothing is new), `--outputs-dir` (default `../outputs`), `-v`.

Exit code is 0 for `ok` / `ok-empty` / `dry-run`, 2 for `degraded` (a source failed, or no
credentials so summaries are extractive) or `error` (every source failed).

## Scheduling

- In-process: `python3 run_job.py --loop --interval 6h`.
- cron: see `schedule/crontab.example`.
- macOS launchd: see `schedule/com.markhryt.newsdigest.plist`.

Whichever you use, credentials must come from the environment of the scheduled process.

## What a run records

- `outputs/latest.md` — the most recent digest (overview, themes, per-source items with
  headline, summary, "why it matters", tags).
- `outputs/digests/` — every digest as Markdown and JSON.
- `outputs/runs.jsonl` — one line per run: status, listed/new counts per source, source errors,
  body-fetch failures, summarizer method and model, token usage, output paths, duration, notes.
- `outputs/logs/job.log` — full log.
- `outputs/state.json` — seen URLs. Everything listed in a run is marked seen (only the newest
  N per source are summarized), so old backlog does not trickle into later digests.

## Failure behavior (bounded by design)

- A single source failing → the run continues with the others and is marked `degraded`.
- An article body failing to fetch → its listing teaser is summarized and the digest says so.
- No credentials / SDK → `degraded`, extractive summaries, clear note in the output and run log.
- The model declining a request or returning malformed JSON → that batch falls back to extractive.
- All sources failing → `error`, nothing written except the run-log line, state untouched.

## Tests

```bash
cd studio/markhryt/code && python3 -m unittest -v test_newsdigest
```

Offline only: fixture HTML/RSS, a fake fetcher for end-to-end runs, no network or API key.

## Cost note

Summaries use `claude-opus-5` (adaptive thinking, effort `medium`, structured output). A full
run of 30 new articles is roughly 100–150k input tokens across 4–5 requests; the system prompt
is cache-marked. Lower `--max-per-source` or pass `--model claude-sonnet-5` to spend less.
