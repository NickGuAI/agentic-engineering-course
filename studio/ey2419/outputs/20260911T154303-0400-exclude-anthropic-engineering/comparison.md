# Studio01 Step 3 — Changed-Condition Comparison

## Result

The corrected run used two allowed sources and made no request to the excluded Anthropic Engineering source. It selected the same five articles, in the same order, with the same dates and freshly revalidated summary wording. The digest now explicitly discloses reduced source coverage.

Baseline: [Step 2 digest](../20260911T153119-0400-baseline/research-update.md)  
Changed run: [Step 3 digest](research-update.md)  
Publication window for both: **September 5–11, 2026**, America/New_York.

## Changed condition, observation, and correction

**Changed condition:** Anthropic Engineering was removed from the allowed source set. Anthropic News and OpenAI News remained allowed. The date window, five-item cap, 100-word summary limit, 15-page limit, retry limit, remaining-source page allocations, and selection policy were retained.

**Observation:** Applying the changed allowlist to the baseline retrieval plan failed the local policy check: the old plan still contained the excluded engineering listing. This was a preflight policy mismatch, not a failed network request. The [recorded check](evidence/policy-preflight.json) identifies the rejected target.

**Evidence-led correction:** Remove that source before dispatching web requests, execute the two-source plan, and label the missing coverage explicitly. The corrected plan passed the same allowlist check. No excluded article, replacement source, or wider date range was used to compensate.

The remaining sources were retrieved again. Each retained summary was rechecked against the newly returned article content before its wording was kept.

## Observed differences

| Measure | Baseline | Changed run | Difference |
| --- | ---: | ---: | ---: |
| Allowed sources / listings inspected | 3 | 2 | -1 |
| Verified eligible candidates | 6 | 6 | 0 |
| Selected digest items | 5 | 5 | 0 |
| Distinct article pages inspected | 7 | 6 | -1 |
| Article-target operations, including text searches | 12 | 11 | -1 |
| Listing-target operations | 3 | 2 | -1 |
| Web-tool calls | 8 | 6 | -2 |
| Failed URLs / retries | 0 / 0 | 0 / 0 | 0 |
| Anthropic Engineering requests | 2 | 0 | -2 |

No article URL was added or removed. The item order, dates, and summary text remained the same. Run metadata, source-status wording, and coverage disclosure changed. The document as a whole is therefore not byte-identical to the baseline.

The unchanged selection is consistent with the saved [baseline engineering report](../20260911T153119-0400-baseline/evidence/anthropic-engineering-source-report.json): that source contributed no verified in-window candidate. Excluding it reduced inspected coverage and work without removing a selected article. This finding applies to these two runs; it does not establish that the source is unnecessary for future updates.

## Verification and limits

The [inspection script](inspect_run.py) checks the changed allowlist, all recorded requested URLs, item limits and provenance, and unchanged controls. It compares the 13 original baseline artifacts with the hashes captured before the rerun and checks the card. It separately reports new folder metadata and changes to the personal explanation. Results are saved in [validation.json](validation.json) and [comparison-data.json](comparison-data.json).

Both runs are bounded inspections of the returned initial listings and candidate articles, not exhaustive archives. The calls occurred at different times on the same day, and the web tool may serve cached content. No substantive change affecting the selected claims was observed; this is not a controlled freshness, latency, or factual-accuracy benchmark.

The first preservation inspection found two concurrent workspace changes: a new `.DS_Store` metadata file in the baseline folder and changed contents in the personal explanation. All 13 original baseline artifacts and the card still match their pre-run hashes. The initial failed result is retained in `evidence/validation-attempt-02.json`; the final inspection distinguishes original-artifact preservation from these additional observations. The explanation was not edited by the agents, and its current text was preserved. Hashes alone do not identify who changed it.

This document records agent execution and measurable comparison results. The student's personal reflection remains a separate artifact.

Final inspection: **25/25 checks passed with notes** about concurrent metadata and explanation changes. Independent artifact-consistency review also passed.
