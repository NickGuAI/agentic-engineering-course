# run-4 log

- Run date: 2026-09-13 (Sunday). Started on the student's explicit go-ahead.
- Agent: Claude Code (Opus 5), single agent, no subagents. Same session as runs 1–3.
- Card: ../../delegation-card.md, corrected after run-3.
- **Correction (evidence-led, decided by the student after run-3):**
  - window 14 → 7 days, to match the weekly schedule
  - minimum items 3 → 1, so a quiet week is not a failure
- **Other differences from run-3:**
  - Two card changes at once: this run can't show which one resolved run-3's failure. Either alone would have.
  - Run date moved from Sep 11 to Sep 13. Neither site posted anything new after Sep 11.
  - The student edited the card's audience line (removed the note about diagrams). Affects style, not counts.
  - Memory: an earlier, unapproved run-4 attempt today (deleted at the student's request) fetched the same pages, and the agent remembered them. As in runs 2–3, it went straight to the browser for OpenAI because it knew `WebFetch` gets a 403 there.
- Prediction before running: PASS with about 7 items.

## Fetches (budget 10, used 10)

| # | URL | Tool | Status | Purpose |
|---|-----|------|--------|---------|
| 1 | https://www.anthropic.com/news | WebFetch | 200 | index |
| 2 | https://www.anthropic.com/engineering | WebFetch | 200 | index |
| 3 | https://openai.com/news/ | Browser navigate + find | loaded | index + article links |
| 4 | https://www.anthropic.com/threat-intelligence-report-september-2026 | WebFetch | 200 | article |
| 5 | https://openai.com/index/scaling-storage-one-billion-users-part-one/ | Browser | loaded | article |
| 6 | https://openai.com/index/put-data-to-work/ | Browser | loaded | article |
| 7 | https://openai.com/index/introducing-chatgpt-financial-services/ | Browser | loaded | article |
| 8 | https://openai.com/index/introducing-gpt-live-1-in-the-api/ | Browser | loaded | article |
| 9 | https://openai.com/index/introducing-the-agents-api/ | Browser | loaded | article |
| 10 | https://openai.com/index/gpt-6-astra-next-generation-work/ | Browser | loaded | article |

"loaded" = the page title returned after navigate matched the headline; the browser tool reports no HTTP status. Browser use was read-only (navigate, find, get_page_text). No other sites visited.

## Items

- Considered: 13 Anthropic News, 4 newest Engineering, 10 OpenAI index entries.
- In window: 1 Anthropic News (Sep 10), 0 Engineering, 10 OpenAI (Sep 8–11).
- Included: 7 (1 Anthropic, 6 OpenAI).
- Selection rule for OpenAI: newest first, product launches before company news and case studies. Applied strictly, it picks "Now everyone can put data to work" over the Christiano board appointment. Run-2 picked the reverse, so run-2 did not follow its own stated rule.

## Checks

| # | Criterion | Result |
|---|-----------|--------|
| 1 | brief.md exists, ≤ ~60 lines | PASS (46 lines, `wc -l`) |
| 2 | 1–8 items, each with title / URL / date / 1–3 bullets | PASS (7 items, `grep -c '^### '`; 2–3 summary bullets each, `grep -n` listing) |
| 3 | all dates within 7 days | PASS (Sep 9–11); Astra caveat as in run-2 |
| 4 | every item URL fetched and logged | PASS (7/7 URLs found in this log, `grep -F`) |
| 5 | run-log complete | PASS |
| 6 | optional table only if it clarifies | none in the brief |
| 7 | report failures, don't overclaim | PASS |

## Result

PASS. Matched the prediction.

## Comparison across runs

| Run | Date | Window | Min items | Items | Result |
|-----|------|--------|-----------|-------|--------|
| run-1 | Sep 11 | 14 days | 3 | 4 (Anthropic only) | PASS, OpenAI articles missing |
| run-2 | Sep 11 | 3 days | 3 | 7 (1 Anthropic, 6 OpenAI) | PASS |
| run-3 | Sep 11 | today only | 3 | 1 | FAIL (check 2) |
| run-4 | Sep 13 | 7 days | 1 | 7 (1 Anthropic, 6 OpenAI) | PASS |

Run-3 → run-4: under the corrected card, run-3's single item would also have passed (minimum 1), and a 7-day window held 11 in-window stories this week.

## Observations

- **Summaries of the same page differ between runs.** `WebFetch` returns a small AI model's answer about a page, not the page itself. For the Anthropic threat report it surfaced different facts each time:
  - run-1: "20+ organizations", ">1 TB", "222 constituencies"
  - run-2: "20+ organizations", "~70 fake news sites"
  - run-4: "ShinyHunters", "roughly 200" organizations in "34 hours"

  None of these numbers were checked against the page.
- **A source changed after publication.** The Habitat article said "Two years ago…" on Sep 11 (see run-3's brief). On Sep 13 it says "first launched … at DevDay 2023". Reruns against live pages are not exactly repeatable.
