# Delegation Card

## Task
Produce a weekly AI briefing from only these sources:
- https://openai.com/news/

Cover posts published in the last 7 days relative to the run date. Select the **top 5 most important** items across all three sources (hard cap: fewer than 10; prefer exactly 5 unless fewer exist). Rank by practical impact on AI/agent builders and students (new models/APIs, tooling, methods, evals, safety-relevant product changes) over marketing or hiring posts.

For each item include:
- title
- source name (`OpenAI News`)
- publication date (as shown on the page)
- canonical URL
- one short paragraph summarizing main outcomes in **method + result** form (what they did / shipped, and what changed or was demonstrated)

Include both news and engineering posts when they fall in-range. Do not create separate source dumps of everything—curate the ranked shortlist only. If a source contributes zero selected items, note that under a brief Sources checked note.

Write one new dated markdown file under `studio/pz/outputs/` named:
`ai-news-brief_YYYY-MM-DD_to_YYYY-MM-DD_ver2.md`
(start/end dates of the covered week). Never overwrite prior weekly files.

## Context
Audience: a student who wants to stay current on AI/agent developments without reading every release post. Prefer concrete product, model, method, and tooling changes over fluff. Keep the whole brief skimmable in a few minutes.

## Success criteria
- A new dated file exists at the path/name pattern above (prior weeks preserved).
- Item count is 5 when possible, never 10+, and never padded with weak items.
- Every listed item has a real URL from the allowed sources and a date in the 7-day window.
- Each item has a short method+result paragraph (not a bullet dump or long essay).
- If a source has zero in-range posts, say so explicitly in the Sources checked note.

## Restrictions
- Do not use sources outside the three URLs above (no Reddit, Twitter/X, blogs, secondary aggregators).
- Do not invent titles, dates, URLs, or claims; if a date/URL cannot be verified, omit the item and note the gap.
- Do not pad to hit 5 with unimportant posts.
- Do not modify files outside `studio/pz/outputs/` (and do not edit this card unless asked).
- Do not overwrite earlier `ai-news-brief_*.md` files.
- Do not include API keys, account details, or private personal information.
- Do not fetch or summarize paywalled/full article bodies beyond what the listing/post page makes public.
- Stop and ask before expanding scope (extra sources, longer history, code generation, etc.).