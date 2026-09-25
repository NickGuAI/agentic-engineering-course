# Delegation Card

## Task
Produce a weekly AI research-update digest as a Markdown file (`outputs/research-update-<date>.md`): 3-6 items from the past 7 days, each with a 2-3 sentence plain-English summary and a "why it matters" line for CS students.

## Context
- Approved sources: https://www.anthropic.com/news and https://openai.com/news/ (and the individual article pages they link to).
- Window: posts dated within the 7 days before the run date.
- Audience: CS students who follow AI but don't read every announcement.
- Tooling: Claude Code with web fetch; `code/verify_digest.py` (stdlib Python) checks the output.

## Success criteria
`python3 code/verify_digest.py <digest> ...` exits 0, meaning:
- Every item has a `Date:` inside the window and a `Source:` URL on an approved domain.
- Every required source domain appears at least once (coverage).
- Total length is at most 600 words.
- Claims only restate what the source article says; unknowns are labeled, not guessed (checked by hand against the fetched pages).

## Restrictions
- Write only inside `studio/timoteahu/`; do not edit course-owned files.
- Fetch only the approved source domains; any new URL or domain needs human approval first.
- No package installs, no paid API calls, no credentials or personal info in outputs or commits.
- If a source can't be read, stop and report it as missing. Never fill the gap from memory.
