# Research Update implementation record

**Date:** 2026-10-14  
**Scope:** Implementation and offline verification only. Existing baseline and changed-condition artifacts were inspected read-only and preserved. No live website requests, model calls, or formal news experiments were run.

## Decisions

- Use the shared `python3` installation and Python standard library; no separate environment or Python package dependencies are required.
- Use Codex CLI for summaries, defaulting to `gpt-6-luna` based on existing run metadata. The model can be overridden with `--model` or `RESEARCH_UPDATE_MODEL`.
- Discover RSS/Atom feeds when linked, then fall back to same-site HTML article links. Feed `updated` timestamps are not accepted as publication dates.
- Use the previous seven complete Eastern Time calendar dates, excluding the run date, as clarified by the user.
- Keep raw model logs outside the repository. The default directory is `~/.local/state/research-update/raw-logs/`; `--raw-log-dir` can select another external path.
- Accept only publication evidence tied to the main article. Preserve date-only values as calendar dates; convert real zoned timestamps to Eastern Time. Treat exact UTC-midnight timestamps as ambiguous unless the article's visible date clarifies whether the value represents the UTC calendar date or an instant that converts to the preceding Eastern date. Skip unresolved or conflicting dates.

## Implemented

- Fetch configured source pages and candidate articles with a per-request timeout, one retry, and a response-size limit.
- Extract publication dates from explicit publication metadata, matching Article JSON-LD `datePublished`, semantically marked `<time>` values inside the main article, and matching feed publication fields. Exclude related-content/navigation dates and modification fields. Skip undated, ambiguous, conflicting, and out-of-window articles.
- Sort newest first and cap the report at ten entries.
- Record source outcomes and distinguish invalid URLs, unavailable pages (including HTTP 404/410), and DNS responses indicating a nonexistent host. Only invalid URLs and confirmed nonexistent hosts trigger default-source fallback.
- Preserve failed candidate article URLs with their retrieval exception details in source results and reports.
- Include the selected publication-date evidence, corroborating signals, and interpretation for each included article in both the report and structured run record.
- Run `codex exec --json` with the prompt on standard input and preserve per-invocation `prompt.txt`, `response.txt`, `events.jsonl`, `stderr.log`, and `invocation.json` in a uniquely named raw-log directory. The structured run record stores the log identifier and raw-log root.
- Record `invoked: false`, a null log identifier, and `no_eligible_articles` when no model call occurs because no articles qualify.
- Save dated Markdown reports and structured JSON run records under `studio/sharonlu2/outputs/`, preserving earlier runs.

## Offline verification

- Python AST syntax parsing and CLI `--help` passed, including the new `--raw-log-dir` option.
- Mock page fixtures confirmed related-content date exclusion, visible-date resolution for UTC-midnight values, Eastern conversion for non-midnight zoned timestamps, and rejection of modification-only evidence.
- Mock timestamp fixtures confirmed both supported UTC-midnight interpretations: preserve the represented calendar day when visible text matches UTC, or convert to the prior Eastern date when visible text matches that instant's Eastern date. Unsupported midnight values remain unresolved.
- Mock feed fixtures confirmed Atom `updated` alone does not produce a publication date.
- A mocked article fetch failure confirmed the candidate URL and actual error are retained in source evidence. A temporary report/run-record fixture confirmed publication evidence and failed URL/error details are serialized into Markdown and JSON.
- Mock HTTP errors confirmed 404/410 produce `unavailable_page`; a mocked DNS `EAI_NONAME` produces `nonexistent_host`.
- A mock local Codex executable confirmed `--json` is passed and the exact prompt, response, JSONL stdout, stderr, command settings, and exit status are persisted outside the repository.
- A mocked no-article run confirmed the structured record explicitly marks the model as not called and uses the previous seven complete dates, excluding the run date.

## Not verified

- No live source page layouts, feeds, network errors, or default-source date extraction were checked; the two reported date examples have not been re-fetched in this session.
- No real Codex CLI invocation was made; authentication, model availability, actual JSONL event format, response quality, and summary fidelity remain unverified.
- Dynamic JavaScript listings and sites that do not expose publication dates may omit eligible stories.
