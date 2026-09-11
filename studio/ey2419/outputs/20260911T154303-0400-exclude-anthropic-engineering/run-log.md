# Studio01 Step 3 — Run Log

## Inputs and effective policy

- Run ID: `20260911T154303-0400-exclude-anthropic-engineering`.
- Started: 2026-09-11T15:43:03-04:00, America/New_York.
- Publication window: September 5–11, 2026, inclusive.
- Baseline: `20260911T153119-0400-baseline`, preserved in its original folder.
- Input card: [delegation-card.md](../../delegation-card.md).
- Changed condition: Anthropic Engineering excluded.
- Effective sources: Anthropic News and OpenAI News; [saved policy](source-policy.json).
- Execution: the existing local Codex session. One parallel agent handled OpenAI News while the main agent handled Anthropic News.

## Actions and outcomes

1. Captured hashes for all 13 baseline files, the card, and the student explanation.
2. Compared the baseline source plan with the changed allowlist. The old plan failed because it included the excluded source.
3. Removed the excluded source and validated the corrected two-source plan before web access.
4. Retrieved the two allowed listings and six distinct article pages. Five targeted text searches inspected already retrieved pages for publication dates.
5. Verified six eligible candidates and applied the unchanged selection rule to include five. The same-day data-product announcement remained omitted under the cap.
6. Saved the new digest, source evidence, trace, and comparison separately from the baseline.
7. Inspected the saved artifacts and baseline preservation using `inspect_run.py`; results are in `validation.json`.

## Source outcomes

| Source | Requests and evidence | Outcome |
| --- | --- | --- |
| Anthropic News | One listing, one article, two searches inside that article; [source report](evidence/anthropic-news-report.json). | One eligible item. Publication day verified from the official listing; both article date-text searches returned no match. |
| OpenAI News | One listing, five articles, three searches inside those articles; [source report](evidence/openai-source-report.json). | Five eligible candidates; four selected. Dates directly verified on article pages. |
| Anthropic Engineering | No request. | Excluded by policy; not assessed in this run. |

The six web-tool calls contained 13 URL-target operations: two listing accesses and 11 article operations, including five text searches. Six distinct articles were visited. No URL failed, and no failed-URL retry occurred. The date-text searches that found no match were recorded as a display limitation rather than an access failure.

## Inspection and attribution

Each digest item includes its publication date, an official article link, and a summary of 54–70 words. The new evidence references support the retained dates and summary wording. Official claims are attributed, and relevance judgments are labeled as interpretation.

The machine-readable [execution trace](execution-trace.jsonl) contains timestamped tool requests, actual target URLs, and outcomes. Metadata and compact support notes are retained instead of full article copies or private reasoning.

The automated inspection verifies recorded-request compliance and artifact consistency. It does not independently establish every source claim or prove the absence of an action omitted from a log.

The first local inspection attempt stopped because the installed Python datetime parser rejected a trailing `Z` timezone marker. The helper was corrected to use the equivalent explicit `+00:00` offset and rerun. This affected only validation tooling, not the experiment inputs or research outputs; the event is retained in the trace.

## Comparison and remaining student work

The [comparison](comparison.md) reports the changed condition, failed preflight check, correction, measured differences, and limits. All 13 original baseline artifacts are verified against [pre-run hashes](evidence/preservation-before.json). A new `.DS_Store` file was observed in that folder, and the explanation file changed during the run. These changes caused the initial whole-folder/explanation equality checks to fail; that result is retained in `evidence/validation-attempt-02.json`. The final check reports these observations separately from preservation of original baseline artifacts. The pre-run hashes were not changed.

The experiment and comparison are agent outputs. The agents did not edit `explanation-ey2419.md`. Its current text is preserved, and its authorship is not inferred from the file change; the studio instructions require the student to write it personally.

Final inspection: **25/25 checks passed with notes** about concurrent metadata and explanation changes. Independent artifact-consistency review also passed.
