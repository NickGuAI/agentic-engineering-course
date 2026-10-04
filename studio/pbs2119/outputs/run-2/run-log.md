# run-2 log

- Run date: 2026-09-11 (Friday)
- Agent: Claude Code, single agent, no subagents (model switched from Fable 5.1 to Opus 5 mid-run by the user)
- Card: ../../delegation-card.md (tools section made precise before this run; it describes what run-1 actually did, so no behavior change intended)
- **Perturbation (the one changed condition):** window cut from 14 days to 3 days, publish date ≥ 2026-09-08. Card otherwise unchanged.
- Prediction before running: fail check 2 (fewer than 3 items), because only one Anthropic item is ≤ 3 days old. That prediction ignored the OpenAI headlines, which are all Sep 8–11.

## Fetches (budget 10)

| # | URL | Tool | Status | Purpose |
|---|-----|------|--------|---------|
| 1 | https://www.anthropic.com/news | WebFetch | 200 | index |
| 2 | https://www.anthropic.com/engineering | WebFetch | 200 | index |
| 3 | https://openai.com/news/ | Browser navigate + find | loaded | index + article links |
| 4 | https://www.anthropic.com/threat-intelligence-report-september-2026 | WebFetch | 200 | article |
| 5 | https://openai.com/index/gpt-6-astra-next-generation-work/ | Browser | loaded | article |
| 6 | https://openai.com/index/introducing-the-agents-api/ | Browser | loaded | article |
| 7 | https://openai.com/index/introducing-chatgpt-financial-services/ | Browser | loaded | article |
| 8 | https://openai.com/index/introducing-gpt-live-1-in-the-api/ | Browser | loaded | article |
| 9 | https://openai.com/index/paul-christiano-joins-openai-foundation-board/ | Browser | loaded | article |
| 10 | https://openai.com/index/scaling-storage-one-billion-users-part-one/ | Browser | loaded | article |

The Browser reports only the origin (`https://openai.com`), not the full path. Evidence that each article loaded is the page title returned after each navigate, which matched the headline every time. Browser use was read-only (navigate, find, get_page_text). No other sites visited.

## Items

- Considered: 13 Anthropic News, 5 newest Engineering, 10 OpenAI index entries.
- In window: 1 Anthropic News (Sep 10), 0 Engineering, 10 OpenAI (Sep 8–11).
- Included: 7 (1 Anthropic, 6 OpenAI). Chose OpenAI articles by newest date, then product launches over case studies.
- Seen but not summarized: 3 OpenAI (budget).

## Checks

| # | Criterion | Result |
|---|-----------|--------|
| 1 | brief.md exists, ≤ ~60 lines | PASS (54 lines, `wc -l`) |
| 2 | 3–8 items, each with title / URL / date / 1–3 bullets | PASS (7 items) |
| 3 | all dates within window | PASS (Sep 9–11); caveat: Astra post is Sep 9 but says the model launched "last week" |
| 4 | every item URL fetched and logged | PASS (7/7 URLs found in this log via `grep`) |
| 5 | run-log complete | PASS |
| 6 | optional table only if it clarifies | theme table included |
| 7 | report failures, don't overclaim | PASS: prediction miss and caveats stated |

## Result

PASS. The predicted failure did not happen.

## Why run-2 differs from run-1 (more than one thing changed)

- Intended change: the 3-day window ruled out three Anthropic articles, which freed fetch budget.
- Unintended change: in run-1, the agent learned that `WebFetch` gets a 403 from openai.com. In run-2 it went straight to the Browser, and it already knew the `/news/` path mistake. Same session, same memory. The run was not independent.
- Result: run-1 = 4 Anthropic items, 0 OpenAI. run-2 = 1 Anthropic, 6 OpenAI. The window changed *which* sources filled the brief, not whether it passed.
- To isolate the window effect, rerun it in a fresh session (no memory of run-1).
