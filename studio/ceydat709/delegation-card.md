# Delegation Card

## Task
What specific artifact or result are you delegating to the AI?

Produce a Markdown digest of the 3 most recent posts from each of: Anthropic News, Anthropic Engineering, and OpenAI News. Structure the file with one heading per source (e.g. `## Anthropic News`), and under each heading, one entry per post with its title, publish date, link, and 2-4 bullet points covering its most important parts. Save the output to `outputs/dd-mm-yyyy.md`, using the run date. Log any run failures.

## Context
What relevant inputs, files, tools, target audience, or learning preferences should the AI consider?
- **Sources:** Pull only from https://www.anthropic.com/news, https://www.anthropic.com/engineering, and https://openai.com/news/. Verify each article is genuinely from its listed source before including it.
- **Tooling:** Browse each source page directly (don't rely on training memory). The posts will be newer than any knowledge cutoff, so content must come from a live fetch of the actual pages.
- **Audience:** Students in an Agentic Engineering course (undergrad and grad) studying how agents perceive, reason, act, and self-correct.
- **Style:** Bullet points should be concise and understandable at a high level, not dense. Each day's doc should be no more than 150 lines total.
- **Date:** Use the runtime date (America/New_York) and include it in the digest.

## Success criteria
What is the observable check or metric that defines a successful run?
A run passes if:
1. `studio/ceydat709/outputs/dd-mm-yyyy.md` exists for that run's date.
2. Each of the 3 sources (Anthropic News, Anthropic Engineering, OpenAI) has exactly 3 distinct posts.
3. Each post has 2-4 bullet points.
4. All included posts were published within the same week as the run date. **Fallback:** if a source has not published 3 posts within that week, include its most recent 3 posts regardless of date instead.
5. The log confirms the run executed.
6. Every link resolves to a real, live post (no broken/404 links).
7. No post appears more than once, within a source or across sources.

## Restrictions
Are there any prohibited actions, resource limits, or human approval boundaries to enforce?
- Do not include bullet points or summary content that isn't drawn directly from that specific post.
- Do not substitute related/similar articles that aren't the source's own listed posts.
