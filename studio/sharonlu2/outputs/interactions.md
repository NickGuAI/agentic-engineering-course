# AI Interaction Record

This file is a curated record of the independent Codex CLI work used to implement and run the Research Update program. Raw terminal recordings, Codex session JSONL, model event JSONL, and retrieved article bodies remain outside the repository because the repository rules prohibit committing raw session logs and downloaded data.

## Development session

- Date: 2026-10-14 ET / 2026-10-15 UTC
- Harness: Codex CLI TUI `0.162.1`
- Model: `gpt-6-luna`
- Reasoning effort recorded in the session: `high`
- Session ID: `01a13ce4-3ac5-7b03-a61f-8f096dabfd78`
- Working directory: `agentic-engineering-studio01`
- Session archive SHA-256: `8b45c759a3798756613e0ff8fe959c70cc4de297a452a89193299fd3ebc2a508`
- Terminal recording SHA-256: `7a946414bf4755fc701027b79673a93e7d3cc0cde6b03aa91c20dce0a2bfb27e`
- Repository metadata: [implementation-20261014-200911-metadata.txt](implementation-20261014-200911-metadata.txt)
- Development record: [implementation-notes-20261014.md](implementation-notes-20261014.md)

### Interaction 1: initial implementation

User prompt, recorded at `2026-10-15T00:10:48.971Z`:

> Read `studio/sharonlu2/delegation-card.md` and implement the Research Update program it describes.
>
> First, read the repository `AGENTS.md` and the Studio 01 instructions. Briefly explain your implementation plan. Ask me about any ambiguity that affects the implementation before making assumptions.
>
> Use the shared course Python environment rather than creating a separate environment for this studio.
>
> Keep implementation files under `studio/sharonlu2/code/` and development records under `studio/sharonlu2/outputs/`. Do not modify the delegation card, shared course files, my evaluation harness, or `explanation-sharonlu2.md`.
>
> Do not generate my evaluation criteria, evaluation harness, or personal explanation.
>
> When finished, explain how to install dependencies and run the program; how the program retrieves sources, invokes the model, and saves reports and run records; and what behavior was verified or remained unverified.
>
> Complete the implementation only. Do not make live model calls, run formal news experiments, commit changes, or push changes until I have reviewed the implementation. Use English for all questions, explanations, and development documentation.

Agent plan and clarification:

- Proposed a Python CLI with bounded requests, article/date extraction, a seven-day Eastern Time filter, model-backed summaries, and preserved Markdown and JSON outputs.
- Asked which summary provider to support and whether custom sources should use generic HTML parsing with feed discovery or require RSS/Atom.
- After finding existing run metadata naming Codex CLI and `gpt-6-luna`, used Codex CLI as the configurable model adapter and selected feed discovery with HTML fallback.
- Used the shared `python3` installation and Python standard library without creating another environment.

Agent result:

- Created `studio/sharonlu2/code/research_update.py`, `studio/sharonlu2/code/README.md`, and the implementation notes.
- Reported that AST/syntax, CLI help, and mocked offline fixtures passed.
- Stated that it made no live website requests or model calls during implementation and left live layouts, authentication, model availability, and summary quality unverified.

### Interaction 2: evidence capture and retrieval rules

User prompt, recorded at `2026-10-15T00:18:56.583Z`:

> Before the formal experiments, improve the implementation's evidence capture and correct these retrieval issues.
>
> 1. Add a `--raw-log-dir` option. For each model invocation, preserve the exact prompt, final response, Codex JSONL event output, stderr, command settings, and exit status in that directory. Use `codex exec --json`. Do not discard these records when the temporary directory is removed. Raw logs will be stored outside the repository.
> 2. Link each invocation's log identifier from the structured run record. If no articles qualify and no model invocation occurs, explicitly record that the model was not called.
> 3. Do not treat feed update dates as publication dates.
> 4. Do not describe an HTTP 404 or 410 response as proof that the website itself does not exist. Distinguish an unavailable page from an invalid URL or confirmed nonexistent host.
>
> Do not modify my delegation card or evaluation harness. Ask me to clarify the date-window definition before changing that behavior. Use offline verification only. Do not run the formal experiments or make live model calls yet.

The agent asked for the date-window definition. The user answered at `2026-10-15T00:20:18.366Z`:

> Previous 7 complete ET calendar dates, excluding run date.

Agent result:

- Added persistent per-invocation evidence and linked it from `model.log_id` in each run record.
- Recorded `invoked: false` and `not_called_reason: no_eligible_articles` when no model call occurs.
- Stopped treating feed `updated` timestamps as publication dates.
- Distinguished malformed URLs, confirmed nonexistent hosts, and unavailable pages; only the first two trigger fallback.
- Changed the window to the previous seven complete Eastern Time dates, excluding the run date.
- Verified the changes with offline mocks and did not run a formal experiment in this interaction.

### Interaction 3: evidence-led date correction

User prompt, recorded at `2026-10-15T00:42:53.628Z`:

> The baseline run exposed publication-date extraction errors. Preserve all existing baseline and changed-condition evidence. Do not overwrite or regenerate those artifacts.
>
> Observed examples:
> 1. “Helping small businesses put AI to work” was reported as published on 2026-10-13, but the article page displays September 30, 2026. The parser appears to have selected a date from related content.
> 2. “Redesigning source control at Anthropic” was reported as published on 2026-10-12, but the article displays October 13, 2026. Converting a midnight UTC date representation to Eastern Time shifted the displayed publication date backward.
>
> Inspect the retrieval and date-extraction code and propose a focused correction before editing. Associate date evidence with the main article, exclude dates from related content and navigation, distinguish publication from modification dates, distinguish calendar dates from timestamps, skip uncertain dates, preserve the existing window, record selected date evidence, and retain failed article URLs and errors.
>
> Keep changes within `studio/sharonlu2/code/` and development records within `studio/sharonlu2/outputs/`. Do not modify the delegation card, evaluation harness, personal explanation, or previous run artifacts. Do not author a new evaluation harness. Use offline verification and do not make live model calls, run formal experiments, commit, or push.

Agent diagnosis and proposed correction:

- Found that the original parser collected dates across the whole page, selected the first parseable value, converted every timestamp to Eastern Time, and discarded article-level retrieval errors.
- Proposed retaining each date's raw value, source, and page context; accepting only publication evidence connected to the main article; preserving date-only values; converting genuine zoned instants; treating midnight UTC values as ambiguous unless corroborated; and recording failed URLs and errors.

Agent result:

- Restricted date evidence to explicit publication metadata, matching Article JSON-LD, and semantically marked dates tied to the main article.
- Excluded related-content, navigation, and modification dates.
- Preserved calendar dates as written and converted genuine timestamps to Eastern Time, while skipping unresolved or conflicting values.
- Added publication evidence and failed article details to reports and structured run records.
- Reported passing offline fixtures for related-date exclusion, timestamps, modification-only evidence, feed handling, failed fetches, serialization, and no-article behavior.
- Did not execute the corrected live run; the user ran it separately afterward.

## Formal runs

All three formal runs used the same summarization instruction:

> Summarize these retrieved news articles for CS graduate students and AI researchers. Use only facts supported by each article's supplied content. Do not add background from memory. Return only a JSON array of objects with fields id and summary. Each summary must be concise (1-3 sentences). If content does not support a useful summary, use an empty string.

The remainder of each model prompt was a JSON payload containing retrieved article titles, URLs, and article text. Those article bodies are omitted from this repository record. The exact external prompt files are identified by SHA-256 below.

### Baseline

- Run: `research-update-20261014-202318-40f0bd`
- Report: [baseline/research-update-20261014-202318-40f0bd.md](baseline/research-update-20261014-202318-40f0bd.md)
- Run record: [baseline/research-update-20261014-202318-40f0bd.json](baseline/research-update-20261014-202318-40f0bd.json)
- Model invocation: `codex-20261015T002336Z-c4a3ac86`
- Provider/model: Codex CLI / `gpt-6-luna`
- Invocation flags: JSON events, ephemeral session, read-only sandbox
- Invocation start: `2026-10-15T00:23:36.767335Z`
- Invocation exit status: `0`; model status: `succeeded`
- Program exit code: `2`; run status: `incomplete`
- Usage: 35,009 input, 12,032 cached input, 1,051 output, 153 reasoning-output tokens
- Prompt SHA-256: `eb849f39a11aa02d087f9c3f180e6e98bdd9965ada70bf09d3d4409d99c10f7a`
- Response SHA-256: `991fc857d2bf40436e58c819d63203a8a1aa9a24df7f4b4fe3d91a8488b9ae56`
- Events SHA-256: `dadf9bfbb669da360d35584744c836914d9a3091c10cac821fbdbbc1e1e3607f`
- Model response: ten non-empty summaries; their text is preserved in the linked Markdown report.

The run produced ten entries but exposed incorrect date extraction in sampled articles. Its partial source failures and overall incomplete status were preserved rather than hidden.

### Changed condition

The changed condition was the custom source argument `--source not-a-url`. An initial shell attempt inside the CLI session failed before the program started because previously defined shell variables were not present in that shell; redirection consequently targeted `/changed-condition-console.log` on the read-only root filesystem. The later successful run used a newly defined output/log location and is the run documented below.

- Run: `research-update-20261014-203907-29a006`
- Report: [changed-condition/research-update-20261014-203907-29a006.md](changed-condition/research-update-20261014-203907-29a006.md)
- Run record: [changed-condition/research-update-20261014-203907-29a006.json](changed-condition/research-update-20261014-203907-29a006.json)
- Model invocation: `codex-20261015T003928Z-ee8857c0`
- Provider/model: Codex CLI / `gpt-6-luna`
- Invocation flags: JSON events, ephemeral session, read-only sandbox
- Invocation start: `2026-10-15T00:39:28.752047Z`
- Invocation exit status: `0`; model status: `succeeded`
- Program exit code: `2`; run status: `incomplete`
- Usage: 36,904 input, 12,032 cached input, 979 output, 58 reasoning-output tokens
- Prompt SHA-256: `eb849f39a11aa02d087f9c3f180e6e98bdd9965ada70bf09d3d4409d99c10f7a`
- Response SHA-256: `e123917fb4e2ab32754e73fdc227875056773579042f4dcb428d51dc1b529061`
- Events SHA-256: `a39f192e9283f8b43fae94e833c0ef44293b7b40f4730bd1644bb5a9091f8612`
- Model response: ten non-empty summaries; their text is preserved in the linked Markdown report.

The program recorded `not-a-url` as `invalid_url`, notified the user, and checked all three defaults. The date errors observed in the baseline remained.

### Corrected

- Run: `research-update-20261014-205025-f70277`
- Report: [corrected/research-update-20261014-205025-f70277.md](corrected/research-update-20261014-205025-f70277.md)
- Run record: [corrected/research-update-20261014-205025-f70277.json](corrected/research-update-20261014-205025-f70277.json)
- Model invocation: `codex-20261015T005044Z-f0bf7679`
- Provider/model: Codex CLI / `gpt-6-luna`
- Invocation flags: JSON events, ephemeral session, read-only sandbox
- Invocation start: `2026-10-15T00:50:44.385677Z`
- Invocation exit status: `0`; model status: `succeeded`
- Program exit code: `2`; run status: `incomplete`
- Usage: 25,987 input, 12,032 cached input, 804 output, 144 reasoning-output tokens
- Corrected code SHA-256: `7a224208d4008db1fa84651c10bbfa6672ee904a2047b225df759ebd188c114f`
- Prompt SHA-256: `598426ad82c5a37a65463ba24eac474ada6e05a783e856c204706384aae5d406`
- Response SHA-256: `219857a39a16f12e42c79de46411906c30eaeb43765e72ebf4cdb94173f25822`
- Events SHA-256: `cdf65ebd8aed128132d10fe7ff49e70c6a750de96bb238be208c48651f83593a`
- Model response: seven non-empty summaries and empty strings for IDs 5, 7, and 8. The report represents these empty responses as `Summary unavailable` rather than inventing content.

The corrected run recorded publication-date evidence and improved sampled dates, but remained incomplete. It also exposed unresolved article-body extraction, candidate-link filtering, skipped-article, and missing-summary issues.

## Evidence retention and omissions

- Exact independent CLI session messages, tool records, and terminal output remain in the external session archive and terminal recording identified by the hashes above.
- Each formal model invocation retains `prompt.txt`, `response.txt`, `events.jsonl`, `stderr.log`, and `invocation.json` in its external raw-log directory. Each run record contains its invocation ID and original raw-log reference.
- Full article bodies are excluded because they are retrieved source material and make the prompt files unsuitable for committing.
- Raw terminal control sequences, internal reasoning records, repeated UI redraws, and tool protocol messages are excluded because this is a curated interaction record rather than a raw session dump.
- No credentials, API keys, authentication files, or environment secrets are included.
