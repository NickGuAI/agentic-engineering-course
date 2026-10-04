# Delegation Card

## Task
Have the agent help me keep up with the latest news and developments of AI: a weekly (Friday) brief of what Anthropic and OpenAI published in the last 7 days (matches the weekly schedule; changed from 14 days after run-3), saved to `studio/pbs2119/outputs/run-N/brief.md`.

## Context
What relevant inputs, files, tools, target audience, or learning preferences should the AI consider?

The AI should consider the following:
1. inputs
    a. the relevant source sites to read for information (list below)
    b. my preferences on how to synthesize and present the information
    c. the frequency: weekly, Fridays. For the studio: run-1 (baseline), run-2 and run-3 (changed conditions), run-4 (after correcting this card).
2. sources (the only pre-authorized web pages)
    a. https://www.anthropic.com/news
    b. https://www.anthropic.com/engineering
    c. https://openai.com/news/
    d. individual article pages linked directly from a, b, or c
3. tools (Claude Code tool names)
    a. `WebFetch`: primary way to read the pre-authorized pages
    b. in-app Browser, read-only: `navigate` + `get_page_text` / `read_page` / `find` only. Fallback when `WebFetch` is blocked. No clicking, typing, forms, or `javascript_tool`.
    c. `Write` / `Edit`: only under `studio/pbs2119/outputs/`
    d. `Read` / `Bash` (`wc`, `grep`): only on files in `studio/pbs2119/`, to run the checks
    e. not allowed: `WebSearch`, Claude in Chrome (my logged-in browser), network via `Bash` (`curl`, etc.), `Agent` (subagents)
4. target audience
    myself. I prefer dense, nontechnical summaries of information. My preference is for bullet points over paragraphs.

## Success criteria
What is the observable check or metric that defines a successful run?

A run passes only if all of the following hold:
1. `studio/pbs2119/outputs/run-N/brief.md` exists and is at most one page (~60 lines).
2. It contains 1–8 items (changed from 3–8 after run-3, so a quiet week is not a failure). Each item has: title, source URL, publish date, and a 1–3 bullet summary.
3. Every publish date is within 7 days of the run date.
4. Every URL appears in `studio/pbs2119/outputs/run-N/run-log.md` as a page that was actually fetched. Nothing invented.
5. `run-log.md` records: run date, pages fetched (with HTTP status), items considered vs. included, and the result of checks 1–4.
6. Optional: one short table or diagram, only if it clarifies a comparison.
7. If any check fails, the agent reports the failure and does not claim success.

## Restrictions
Are there any prohibited actions, resource limits, or human approval boundaries to enforce?
1. Prohibited actions
    a. navigating to websites that are not among the pre-authorized sources in Context 2
    b. taking any action other than reading and summarizing text from a website, and writing the outputs above
    c. reading or writing any files on my local machine that are not in this repo's `studio/` folder
2. resource limits
    a. at most 1 agent (no subagents); at most 10 web fetches per run
    b. writes inside `studio/pbs2119/outputs/` are pre-approved; seek human approval to read or write any other local file
    c. seek human approval to navigate to any web page not on the pre-authorized list
