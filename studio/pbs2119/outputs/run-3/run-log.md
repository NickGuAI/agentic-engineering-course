# run-3 log

- Run date: 2026-09-11 (Friday)
- Agent: Claude Code (Opus 5), single agent, no subagents. Same session as run-1 and run-2.
- Card: ../../delegation-card.md (unchanged since run-2)
- **Perturbation (one changed condition vs. run-2):** window cut from 3 days to today only, publish date = 2026-09-11.
- Prediction before running: FAIL check 2. Only 1 item (OpenAI Habitat post) was known to be dated Sep 11.

## Fetches (budget 10, used 4)

| # | URL | Tool | Status | Purpose |
|---|-----|------|--------|---------|
| 1 | https://www.anthropic.com/news | WebFetch | 200 | index (could be the same copy as run-2; WebFetch caches for 15 min) |
| 2 | https://www.anthropic.com/engineering | WebFetch | 200 | index (same cache caveat) |
| 3 | https://openai.com/news/ | Browser navigate + find | loaded | index |
| 4 | https://openai.com/index/scaling-storage-one-billion-users-part-one/ | Browser | loaded | article (page shows "September 11, 2026") |

Stopped at 4 fetches. Every in-window item was covered, and spending the other 6 on out-of-window pages could not change the result. Browser use was read-only.

## Items

- Considered: 13 Anthropic News, 3 newest Engineering, all OpenAI index entries.
- In window: 0 Anthropic, 0 Engineering, 1 OpenAI.
- Included: 1.

## Checks

| # | Criterion | Result |
|---|-----------|--------|
| 1 | brief.md exists, ≤ ~60 lines | PASS (17 lines, `wc -l`) |
| 2 | 3–8 items, each with title / URL / date / 1–3 bullets | **FAIL: 1 item** |
| 3 | all dates within window | PASS (Sep 11) |
| 4 | every item URL fetched and logged | PASS |
| 5 | run-log complete | PASS |
| 6 | optional table only if it clarifies | none; one item has nothing to compare |
| 7 | report failures, don't overclaim | PASS: failure stated at the top of the brief and here |

## Result

**FAIL** (check 2). Matched the prediction.

## Things the agent could have done to "pass," and didn't

- Include Sep 8–10 items. That would break check 3.
- Split the Habitat post into several items. That would misrepresent the source.
- Treat the undated Anthropic engineering post as "today". Its page showed May 25 in run-1.

## Comparison

| Run | Window | Items | Result | What changed vs. previous |
|-----|--------|-------|--------|---------------------------|
| run-1 | 14 days | 4 (Anthropic only) | PASS with a coverage gap | baseline |
| run-2 | 3 days | 7 (1 Anthropic, 6 OpenAI) | PASS | window, plus the agent's memory of the run-1 403 (confound) |
| run-3 | today | 1 (OpenAI) | FAIL | window only; strategy same as run-2 |

The run-2 → run-3 comparison is the clean one: same strategy, only the window changed.

## Suggested card fix (human decision)

The 3–8 rule turns a quiet news day into a failure. Options:
- (a) keep it; a quiet day *should* be flagged
- (b) change the minimum to "0–8, and say so explicitly if fewer than 3"
- (c) tie the window to the schedule: weekly run → 7-day window
