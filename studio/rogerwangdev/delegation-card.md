# Delegation Card

## Task
Create a weekly AI news and development digest.

The assistant should check selected AI company news sources once per week and produce a concise summary of the latest or most worth-looking-at AI news and engineering updates. The weekly digest should help me keep up with important developments without having to manually scan every article.

The intended recurring schedule is every Monday at 7:00 AM Eastern Time.

The artifact should include:

- A short executive summary of the most important updates.
- A ranked list of notable articles or announcements.
- A brief explanation of why each item matters.
- A section connecting the news to my interests as an Agentic Engineering student, especially agents, tooling, evaluation, coding assistants, model behavior, and AI engineering workflows.
- Links back to the original sources.
- A short "worth reading fully" recommendation list.

## Context
Primary sources:

- https://www.anthropic.com/news
- https://www.anthropic.com/engineering
- https://openai.com/news/

Target audience: me, a student in COMS W4995 Agentic Engineering who wants to stay current on AI news and development, especially items related to agentic systems, developer tools, model releases, AI safety, evaluation, and practical engineering lessons.

The agent should behave like a careful news scout, not a hype generator. It should prioritize recent, source-backed updates and explain why each item is relevant.

Learning preference: concise, structured, and practical. Use a table when comparing items. Avoid long summaries unless an item is unusually important.

## Success criteria
The run is successful if the assistant:

- Checks all three specified sources or clearly reports which source could not be accessed.
- Includes article titles, source names, dates when available, and direct links.
- Distinguishes confirmed source information from the assistant's own interpretation of why the item matters.
- Ranks the most relevant updates for me as an Agentic Engineering student.
- Flags any items that are worth reading in full.
- Avoids repeating old news unless it is still directly relevant to the current week.
- Produces a digest short enough to review in under 10 minutes.
- Can be configured to run every Monday at 7:00 AM Eastern Time, while asking for approval before enabling any real automation.

## Restrictions
Do not use or expose private credentials, API keys, account tokens, personal information, or anything that should not be committed to GitHub.

Do not bypass website terms, paywalls, robots restrictions, login walls, or rate limits.

Do not schedule or enable a real weekly automation without my explicit approval.

Do not send emails, notifications, GitHub commits, or CourseWorks submissions without approval.

If a source cannot be accessed, the assistant should record the failure, continue with the accessible sources, and clearly mark the digest as partial.

If an article's relevance is uncertain, the assistant should say so instead of overstating importance.
