# Delegation Card

## Task
Produce a weekly research-update article summarizing the latest AI news, as a Markdown file in an engaging, article-style format (with a diagram only where it clarifies an important architectural distinction). Audience: me and other CS students who want to understand these new topics.

## Context
- Sources: https://openai.com/news/ and https://www.anthropic.com/news — synthesize across both rather than listing them source-by-source.
- Cover the most recent posts as of the run date (no fixed lookback window).
- Depth: written for someone relatively new to the industry, explaining how the covered techniques could be used in a business or personal product for growth/development. Simplify difficult concepts in a human, readable tone rather than a dry recap.
- Mostly text; add a diagram only for an important architectural distinction.
- Tooling: run with Claude Code, with web access enabled.

## Success criteria
- Every item mentioned is among the most recent posts on its source page as of the run date.
- Total output is under 1500 words.
- Every claim traces to something explicitly stated in a source article — no invented updates, features, or details.

## Restrictions
- Write only inside `studio/rb3736/`; no temp files outside this folder either.
- No credentials, API keys, or personal info in any output or commit.
- Do not edit course-owned files (`instruction/`, `docs/`, `.github/`, `bootstrap.sh`, `README.md`, `AGENTS.md`).
- No downloads, no installing packages.
- No fetching sites outside the approved source list (see "change one condition" note below).
- No spending money; should not require any paid API calls.

---
**Planned condition change (Studio 01, step 3):** for the second run, relax the source-list restriction above to let the agent browse and cite any relevant source it finds, instead of only the two listed URLs. Compare the two runs' outputs and note the tradeoffs (e.g., broader coverage vs. harder-to-verify claims) in the explanation.
