# Delegation Card

## Task
Implement a repeatable AI news-update program that collects latest AI news and generates a Markdown report.

Each report contains at most 10 entries, ordered by publication date from newest to oldest. Each entry includes a title, publication date, source, original article link, and a concise summary.

Save reports and run records under `studio/sharonlu2/outputs/`, preserving previous runs.

## Context
The audience is CS graduate students and AI researchers.

The default sources are:
- Anthropic News: https://www.anthropic.com/news
- Anthropic Engineering: https://www.anthropic.com/engineering
- OpenAI News: https://openai.com/news/

Users may provide one or more custom website URLs instead  of the defaults.Include articles published within the seven days before the run, using Eastern Time. Skip articles without a verifiable publication date.

## Success criteria
- Every configured source is checked, with its outcome recorded.
- The Markdown report contains no more than 10 entries, with the required fields and correct date ordering.
- Included articles fall within the date window, and summaries are supported by the retrieved content.
- Missing information and source failures are disclosed. Partial reports are labeled incomplete.
- Preserve a baseline run, a run with one changed condition, and evidence of the resulting correction or responsible stop.

## Restrictions
- Keep implementation code under `studio/sharonlu2/code/` and outputs under `studio/sharonlu2/outputs/`. Do not modify shared course files.
- Do not invent news or use model memory to replace unavailable source content.
- If no eligible articles are found after successful source checks, report this honestly.
- If a custom URL is invalid or its website does not exist, notify the user and fall back to the default sources.
- For other retrieval failures, record the error. Allow an incomplete report from available sources; do not describe failed sources as having no news.
- Use limited retries and a timeout; stop rather than retry indefinitely.
- Do not expose credentials or commit raw session logs.
- Leave the evaluation criteria, evaluation harness, and personal explanation for the student to author.