# Test-run log

Run: 20260917T192307Z. One manual test. No recurring schedule activated.
Read instructions: `studio/ObserverZQ/code/code.md`, `studio/ObserverZQ/delegation-card.md`.
Current card: five headlines from the last week; future schedule Monday at 07:00 EST. This supersedes the earlier ten-headline/72-hour criteria.

## Window and comparison

Clock: 2026-09-17 19:23:07 UTC (15:23:07 EDT).
Coverage: 2026-09-10 19:23:07 UTC through 2026-09-17 19:23:07 UTC, interpreted as a rolling seven days. Dates on articles have no precise publication time or timezone. September 10 boundary items are excluded conservatively; five more recent candidates suffice.

Read the previous test report at `../20260917T192008Z/report.md`. Four selected URLs overlap. The September 11 storage article is newly included because coverage widened, not because it was newly published since that test. No new publication since the preceding test was found in the retrieved indexes. Tests remain separate from recurring cycles: no prior weekly production-cycle report exists. This is the first baseline test of the revised weekly criteria, so the ordinary weekly report is produced; production-cycle novelty and fallback behavior are not claimed validated. If the preceding manual test is treated as the previous cycle, the no-update fallback would be relevant, but week-long trending evidence is insufficient. No popularity or sustained-trend claims are made.

## Source attempts and retrieval evidence

- https://www.anthropic.com/news — successful index retrieval; September 17 life-sciences article selected. Older featured cards are not assumed recent.
- https://www.anthropic.com/engineering — successful index retrieval; featured article opened, dated May 25. Remaining listed articles April 23 or earlier. No eligible article found.
- https://openai.com/news/ — successful index retrieval; September 16 and September 11 articles selected. September 10 entries are boundary-date candidates, omitted conservatively.

Reopened all five selected article URLs plus the engineering exclusion. The initial direct open of the life-sciences article returned a browser “not safe to open (non-retryable error)”; following its actual Newsroom link succeeded. Browsing was available overall. OpenAI articles returned text; source bodies already inspected in this conversation were retained as supporting evidence, and the storage body was explicitly reopened in this run. No claim of an independent full re-read of every unchanged body. Index pagination and exhaustive archive search were not performed.

## Article decisions

| URL | Published date | Decision and supporting evidence |
| --- | --- | --- |
| https://www.anthropic.com/news/life-sciences-verification-program | 2026-09-17 | Selected. Header date; introduction and access sections support beta applications, tiered grants, and monitoring. Same article as previous test. |
| https://openai.com/index/reimagining-advertising-with-ai/ | 2026-09-16 | Selected. Header date; introduction and advertising sections support US Sponsored Agents testing, campaign tooling, and HubSpot/Shopify integrations. Same article as previous test. |
| https://openai.com/index/how-to-connect-ai-usage-to-business-value/ | 2026-09-16 | Selected. Header date; analytics, Outcomes, and Admin plugin/API sections support the summary. Guidance publication, not a claim all features launched that date. Same article as previous test. |
| https://openai.com/index/model-misalignment-reporting-framework/ | 2026-09-16 | Selected. Header date; introduction and disclosure process support six training/evaluation reports and publication before complete explanation or mitigation. Same article as previous test. |
| https://openai.com/index/scaling-storage-one-billion-users-part-one/ | 2026-09-11 | Selected. Header date; Habitat overview and centralized-service sections support architecture, latency, and reliability summary. Newly eligible under seven-day scope. |
| https://www.anthropic.com/engineering/how-we-contain-claude | 2026-05-25 | Excluded. Body explicitly says Published May 25, 2026; outside the week despite featured placement. |

Other index items were screened by displayed dates, not opened as candidates in this run. September 10 items have uncertain eligibility at the exact start boundary; older items are outside the week. No unsupported article-body claims taken from those entries.

## Tag normalization

Publisher Engineering maps to Engineering; Product maps to Product. Research and Safety are combined into Safety and Research. Anthropic Announcements is broad, so its biology-access article is assigned to Safety and Research by subject. Keyword tags are editorial content labels, not asserted publisher metadata. Categories are alphabetical: Engineering, Product, Safety and Research.

## Checks

| Requirement | Status | Evidence |
| --- | --- | --- |
| Read current instructions | passed | Current five-headline weekly card loaded before selection. |
| Browsing available | passed | Three indexes and all selected article URLs ultimately returned text; initial article error and successful recovery recorded above. |
| Five distinct headlines | passed | Five unique linked article titles in report. |
| Published in the last week | passed | Selected dates September 11, 16, and 17; September 17 article already accessible at retrieval. |
| Exact publication times/timezones | not verified | Source text provides dates only. |
| Attempt all three configured sources | passed | All three indexes retrieved. |
| Include developments from all three source sections | failed | One Anthropic News and four OpenAI News articles; no eligible Anthropic Engineering article found. |
| Mainly use specified sources | passed | All five articles are linked from configured indexes. |
| Actual article content, no fabricated news | passed | Summaries checked against article sections recorded in ledger and browser text retained in this conversation. |
| Title, summary, attached tags, specific citation per item | passed | Five entries, each with linked title sourcing the entry, summary, date, and Tags line. Summaries are paraphrases. |
| Normalize tags and alphabetize categories | passed | Mapping documented above; ordered category headings verified programmatically. |
| Summaries at most 300 words | passed | 129 whitespace-delimited summary words; entire rendered report 270 words. |
| Previous weekly-cycle comparison | not verified | Prior artifact is a separate 72-hour test; no weekly production baseline. Four URLs overlap, fifth reflects changed scope. |
| Five trending topics fallback | not verified | Not invoked for first revised weekly baseline; no evidence of sustained week-long trends. |
| Exhaustive source coverage | not verified | Retrieved index listings only, no pagination/archive crawl. |
| Unique timestamp, no prior overwrite | passed | New directory created with exist_ok=False; earlier outputs only read. |
| No recurring schedule activated | passed | Only browsing, local reads, and output writes performed. |
| Monday 07:00 EST recurrence | not verified | Explicitly not activated/tested per code.md; EST versus daylight-saving local time would need resolution before scheduling. |

Overall: test completed and five-headline weekly report produced. Not a full validation pass: all-three-section representation failed; cycle comparison, fallback, and exhaustive coverage remain not verified.
