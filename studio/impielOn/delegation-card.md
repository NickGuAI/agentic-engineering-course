# Delegation Card

## Task
Create a recurring, bounded research-update job for `impielOn`.

Each run should collect the latest relevant articles from these official sources:

- Anthropic News: `https://www.anthropic.com/news`
- Anthropic Engineering: `https://www.anthropic.com/engineering`
- OpenAI News: `https://openai.com/news/`

The job should summarize the discovered articles for developers and technology or AI enthusiasts. It should be runnable as a single invocation so an external scheduler or Codex can invoke it repeatedly.

## Context
The target audience is developers and technology or AI enthusiasts. The team name or username is `impielOn`.

Use the existing implementation in `code/news_update.py` as the job entry point. Use only the three official sources listed above; do not substitute search results, social posts, or third-party reporting.

## Success criteria
A successful run must:

1. Attempt to read all three official source pages.
2. Return at least one current article from an allowed source when one is available.
3. Include the article title, source name, canonical URL, and a concise summary grounded in the article page's overall contents. The summary should synthesize multiple substantive parts of the article when available, rather than copying only its opening paragraph.
4. Include exactly one concise, objective `Why it matters` line for every identified article. State the practical implications or affected decisions without promotional, flattering, or unsupported language.
5. Write a timestamped Markdown report to `outputs/`.
6. Persist deduplication state and an execution log in `outputs/`.
7. If no articles are reported, state whether the cause was source failure, deduplication, or the lookback filter.
8. Report source or article fetch failures without fabricating news.

The implementation must be stored in `code/`. The job must remain bounded: use finite source and article limits, request timeouts, response-size limits, and a configurable lookback window.

## Restrictions
The agent may read or write only within the directory it is run from: `studio/<team-name-or-username>/`. It may write job outputs and logs under `outputs/` and implementation files under `code/`.

Do not write to or overwrite `explanation-<username>.md`; the student owns that file. Do not overwrite shared materials or other students' files. Do not send messages, publish content, or modify external systems.

If a source is unavailable, continue with the other allowed sources, record the failure, and exit within the configured bounds. Never invent article content or present third-party material as official-source news.

## Run contract
The default invocation should be equivalent to:

```bash
python3 code/news_update.py
```

The job should exit after one bounded run and print the path of the generated report. Repeated runs should avoid re-reporting the same article using persisted state.
