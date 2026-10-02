# Runs: baseline, changed condition, correction

All runs were executed on 2026-09-11 from `studio/markhryt/code` with no `ANTHROPIC_API_KEY`
set, so every run took the extractive (no-model) summarization path and was marked `degraded`
for that reason. Each run directory holds the full pipeline output: `digests/`, `latest.md`,
`runs.jsonl` (one trace line per iteration), `state.json`, `logs/job.log`, and `console.log`.

## run1 — baseline

Command:

```bash
python3 run_job.py --loop --interval 60 --max-runs 2 --outputs-dir ../runs/run1
```

| iteration | status | listed (news / eng / openai) | new | summarized |
|---|---|---|---|---|
| 1 | degraded (no credentials) | 12 / 25 / 1190 | 10 / 10 / 10 | 30 |
| 2 (+60 s) | ok-empty | 12 / 25 / 1190 | 0 / 0 / 0 | 0 |

Both sources on anthropic.com were read from their listing pages plus each article page.
OpenAI was read from `https://openai.com/news/rss.xml`. The second iteration shows the
seen-state dedupe: nothing new, no digest written, one trace line appended.

## The change (condition: failed check on one input)

One line in `code/newsdigest/config.py`, the OpenAI source:

```diff
-        fetch_url="https://openai.com/news/rss.xml",
+        fetch_url="https://openai.com/news/",  # CHANGE (run2): fetch the HTML page instead of the RSS feed
```

This points the RSS parser at the HTML page the job was originally asked to watch. The
expectation was the graceful path already tested for a failing source: `status=degraded`,
an entry in `source_errors`, and the two Anthropic sources still summarized.

## run2 — observed with the change

Command (same as run1, output to `runs/run2`).

| iteration | status | notes |
|---|---|---|
| 1 | error | `unhandled exception; see logs/job.log` |
| 2 (+60 s) | error | same |

Observed, not expected: the whole run died, including the two healthy Anthropic sources,
and no digest was written. `logs/job.log` has the traceback:

```
File ".../newsdigest/ingest.py", line 180, in parse_rss
    root = ET.fromstring(xml_text)
xml.etree.ElementTree.ParseError: not well-formed (invalid token) ...
```

Two things were learned from the evidence:

1. `openai.com/news/` answered **200 with HTML** to the job's fetch (an earlier manual probe
   had received 403), so the failure did not happen at fetch time, where it was handled, but at
   parse time.
2. `xml.etree.ElementTree.ParseError` subclasses `SyntaxError`, not `ValueError`. The per-source
   handler in `job.py` caught only `FetchError` and `ValueError`, so the exception escaped and
   the loop's outer catch-all logged it as an unhandled run failure.

## Correction

In `code/newsdigest/ingest.py`, `parse_rss` now catches `ET.ParseError` and re-raises a
`ValueError` naming the problem and the first bytes of the response, and also rejects a
well-formed XML document that is not an RSS feed. A malformed or wrong-format feed is thereby a
source-level failure like a fetch error. Two tests were added in `code/test_newsdigest.py`:
`test_rss_rejects_html` and `test_html_feed_is_source_failure_not_crash`.

## run3 — same changed condition, with the correction

```bash
python3 run_job.py --outputs-dir ../runs/run3
```

| status | source error | new | summarized |
|---|---|---|---|
| degraded | `openai-news: not a valid RSS/XML feed (...); response starts with '<!DOCTYPE html>...'` | 10 / 10 / 0 | 20 |

The digest in `runs/run3/latest.md` has Anthropic News and Anthropic Engineering sections and
no OpenAI section; `runs.jsonl` records the OpenAI failure text; the process exit code is 2.
This is the behavior run2 was expected to show.

## Comparison

| | run1 | run2 | run3 |
|---|---|---|---|
| OpenAI input | RSS feed | HTML page | HTML page |
| parse-error handling | (not exercised) | escapes, run dies | caught, source-level failure |
| digest written | yes (30 items) | no | yes (20 items) |
| trace line | full counts | "unhandled exception" | counts + source error |

After run3 the config change was reverted, so the committed code reads the RSS feed again
and keeps the parse-error fix.
