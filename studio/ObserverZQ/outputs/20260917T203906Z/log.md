# Test-run log

Run ID: 20260917T203906Z. One manual test, separate from production.
Instructions read: `studio/ObserverZQ/code/code.md` and `studio/ObserverZQ/delegation-card.md`.
Baseline path: none explicitly supplied. Per code.md, use first-run mode; do not infer a baseline from earlier tests.

## Coverage

Clock at start: 2026-09-17 20:39:06 UTC (16:39:06 EDT).
Window: 2026-09-10 20:39:06 UTC through 2026-09-17 20:39:06 UTC.
Assumption: “last week” means rolling seven days. Publisher headers supply calendar dates, not exact times/timezones. Selected dates are September 16 and 17, with same-day articles already accessible during retrieval. September 10 boundary candidates are omitted conservatively. Exact timestamp precision is not verified.

## Source attempts and stopping points

- https://www.anthropic.com/news — success. Dated listing extends from September 17 through July 30, beyond the coverage boundary; featured cards inspected separately. No further pagination needed for the visible chronological window.
- https://www.anthropic.com/engineering — success. Dated listing extends from April 23 backward; opened undated featured article, confirmed May 25, 2026. No eligible item found; no per-source minimum applies.
- https://openai.com/news/ — success. Listing includes September 17, September 16, September 11, and September 10. “Load more” is a button without an actionable link in the browser text interface. Continuation could not be followed with that interface.
- https://openai.com/news/rss.xml — attempted through the index RSS link as an alternative; browser returned Internal Error. Additional boundary-day entries are not verified. Discovery is not claimed exhaustive.

Opened and read all five selected article bodies during this run. Reopened analytics, misalignment, and life-sciences pages at body line positions after abbreviated combined tool output. Opened the engineering featured article to establish its date. No previous report was used to validate summaries.

## Selection and labels

Select at most five distinct articles, prioritizing recent publication dates. Five September 16–17 articles were selected; the eligible September 11 storage article was excluded because it ranks below those five by recency.

Normalize this article's OpenAI Company label and Anthropic Announcements into Announcements: both selected items announce new offerings. Preserve Product. Merge Research and Safety into Research and Safety. These mappings are editorial decisions, not claims that all Company articles are announcements. Attached keyword labels are assigned from article content. Categories are alphabetical: Announcements, Product, Research and Safety.

| Selected URL | Header date | Source category | Normalized category | Editorial labels | Body evidence |
| --- | --- | --- | --- | --- | --- |
| https://openai.com/index/astra-for-law/ | 2026-09-17 | Company | Announcements | legal AI, enterprise, model configuration | Introduction and legal research sections; availability paragraph explicitly distinguishes initial access from forthcoming API. |
| https://www.anthropic.com/news/life-sciences-verification-program | 2026-09-17 | Announcements | Announcements | life sciences, verified access, safeguards | Introduction, verification/access types, and shared-responsibility monitoring sections. |
| https://openai.com/index/reimagining-advertising-with-ai/ | 2026-09-16 | Product | Product | advertising, agents, integrations | Introduction, Sponsored Agents testing, campaign tooling, and integrations sections. |
| https://openai.com/index/how-to-connect-ai-usage-to-business-value/ | 2026-09-16 | Product | Product | analytics, enterprise AI, business outcomes | Analytics overview, Outcomes, and Admin plugin/API sections; guidance publication, not a claim every feature launched that day. |
| https://openai.com/index/model-misalignment-reporting-framework/ | 2026-09-16 | Research; Safety | Research and Safety | alignment, disclosure, research | Introduction and six-report section; incident occurrence is distinguished from publication date. |

## Exclusions

| URL | Date and evidence | Reason |
| --- | --- | --- |
| https://openai.com/index/scaling-storage-one-billion-users-part-one/ | 2026-09-11, current news index; URL known from previous retrieval | Eligible but omitted under five-item limit in favor of newer articles. Body not reread or summarized this run. |
| https://www.anthropic.com/engineering/how-we-contain-claude | 2026-05-25, article header read this run | Outside coverage despite featured placement. |

Other September 10 entries were screened by index dates and omitted for start-boundary uncertainty and lower recency. Older entries were outside coverage. No body claims from unselected items used.

## Checks

| Requirement | Status | Evidence |
| --- | --- | --- |
| One separate test; unique timestamp | passed | New directory created with exist_ok=False; prior runs untouched. |
| No more than five headlines | passed | Five distinct linked titles, no split articles used to increase count. |
| Last-week publication dates | passed | Headers confirm September 16–17 within documented window; same-day pages already available. |
| Exact publication timestamps | not verified | Pages expose dates only. |
| Inspect all three configured sources | passed | Three index retrievals, dated listings and featured engineering item checked. |
| Discovery through entire window | not verified | OpenAI continuation unavailable in text interface; RSS alternative returned Internal Error. Limitation disclosed. |
| Mainly specified sources; no minimum per source | passed | Four OpenAI News and one Anthropic News article; zero Engineering articles is allowed. |
| Read selected bodies during this run | passed | Five article bodies inspected; supporting sections in ledger. |
| No fabricated news; summaries grounded in articles | passed | Claims checked against bodies, including availability qualifications and distinction between historical incidents and new disclosure. |
| Title, summary, keyword/label, specific link | passed | Each entry has linked article title citing its summary, publication date, summary, and Labels line. Paraphrases, not verbatim quotations. |
| Normalize editorial labels; alphabetical categories | passed | Mapping above and ordered report headings verified. |
| Combined summaries at most 300 words | passed | 129 whitespace-delimited words, excluding titles, labels, links, dates, and introductory note. |
| Previous-cycle comparison | not applicable | No explicitly supplied baseline; first-run rule applies. |
| Five ongoing topics covered more than once in past month | not applicable | First-run rule; no fallback triggered or monthly recurrence claimed. |
| Required report.md and log.md | passed | Both written and read back in the new run directory. |
| No recurring schedule activated | passed | Only browsing and local file operations performed. |
| Monday 07:00 EST recurrence | not applicable | Intentionally not tested or activated under code.md. |

Overall: report content and format checks passed, with no failed checks. Discovery completeness and exact timestamp precision remain not verified. Baseline comparison, fallback, and scheduling are not applicable.
