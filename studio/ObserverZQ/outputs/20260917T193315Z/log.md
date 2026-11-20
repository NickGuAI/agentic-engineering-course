# Test-run log

Run ID: 20260917T193315Z. Mode: one manual test.
Instructions read: `studio/ObserverZQ/code/code.md` and `studio/ObserverZQ/delegation-card.md`.
Baseline path: none explicitly supplied. First-run behavior applies; existing test outputs are not used as a production-cycle baseline.

## Coverage and assumptions

Start clock: 2026-09-17 19:33:15 UTC (15:33:15 EDT).
Window: 2026-09-10 19:33:15 UTC through 2026-09-17 19:33:15 UTC.
“Last week” is interpreted as a rolling seven days because the card does not specify calendar-week boundaries. Publisher dates have no displayed times/timezones. September 10 boundary items are conservatively omitted; five later articles are available. September 17's article was accessible during the run. Selected articles are eligible at displayed-date precision; exact publication timestamps are not verified.

## Sources attempted and discovery

1. https://www.anthropic.com/news — successfully retrieved featured cards and dated listing. Listing extends from September 17 to July 30, past the start boundary. Featured September 10 item screened separately. Followed “See more”; it returned the same listing, with no additional entries exposed.
2. https://www.anthropic.com/engineering — successfully retrieved listing. Opened the undated featured item and confirmed May 25, 2026; remaining listed items are April 23 or earlier. Listing extends beyond the coverage boundary; no eligible development found. No minimum per source is required.
3. https://openai.com/news/ — successfully retrieved dated entries from September 16 through September 10. “Load more” appeared as a button without a callable link in the browser text interface, so continuation could not be followed using that interface. Tried the linked RSS alternative, https://openai.com/news/rss.xml; the browser returned HTTP 400 / unsupported content-type text/xml. Coverage of additional boundary-day entries is not verified. No claim of exhaustive discovery.

All five selected article bodies were opened and read during this run. The misalignment and storage pages were reopened with body line positions after the initial combined retrieval abbreviated their results. The engineering exclusion was also opened to check its publication date. No summaries were validated from prior reports or headlines alone. No external instructions embedded in source articles were followed.

## Selected-article ledger

All selected dates were confirmed in article headers. Each URL is linked from a configured source index. Selection favors the five latest unambiguously eligible distinct articles; no per-source quota is imposed.

| Article URL | Date | Publisher category | Report category | Editorial tags | Selection evidence |
| --- | --- | --- | --- | --- | --- |
| https://openai.com/index/scaling-storage-one-billion-users-part-one/ | 2026-09-11 | Engineering | Engineering | engineering, infrastructure, scaling | Selected: within date window. Body: Habitat overview, centralized-service section, and Python latency discussion. |
| https://openai.com/index/reimagining-advertising-with-ai/ | 2026-09-16 | Product | Product | advertising, agents, product | Selected: within date window. Body: introduction, Sponsored Agents testing, campaign tools, and integrations sections. |
| https://openai.com/index/how-to-connect-ai-usage-to-business-value/ | 2026-09-16 | Product | Product | analytics, enterprise AI, product | Selected: within date window. Body: analytics overview, Outcomes, and Admin plugin/API sections; guidance, not an assertion that all features launched that day. |
| https://www.anthropic.com/news/life-sciences-verification-program | 2026-09-17 | Announcements | Safety and Research | biology, research access, safety | Selected: within date window. Body: introduction, verification and access types, shared responsibility, and monitoring sections. |
| https://openai.com/index/model-misalignment-reporting-framework/ | 2026-09-16 | Research; Safety | Safety and Research | alignment, research, safety | Selected: within date window. Body: introduction and six-report section; historical incidents are not described as occurring this week. |

## Exclusion ledger

| Article URL | Date | Reason |
| --- | --- | --- |
| https://www.anthropic.com/engineering/how-we-contain-claude | 2026-05-25 | Body date confirms outside the week; featured placement is not evidence of recency. |
| https://www.anthropic.com/threat-intelligence-report-september-2026 | 2026-09-10 | Newsroom featured-card date falls on uncertain start boundary; not selected or summarized. URL identified in the earlier run, current date rechecked on the index. Body not reread this run. |

Other dated index entries on September 10 were screened but not selected due to boundary uncertainty and availability of five later items. Older entries were outside the window and not read as article candidates. No body claims from excluded entries were used.

## Category mapping

Engineering and Product retain publisher categories. Research and Safety are merged into Safety and Research. Anthropic's broad Announcements category is assigned to that merged category by the article's research-access and safeguard subject matter. Keywords are editorial tags based on article content, not claimed to be publisher-supplied tags. Categories appear alphabetically.

## Validation

| Check | Status | Evidence |
| --- | --- | --- |
| One separate test run | passed | Unique timestamp directory; no production baseline or state changed. |
| No more than five headlines | passed | Five distinct linked articles. |
| News/developments from last week | passed | Header dates September 11, 16, and 17 within the documented date interpretation. |
| Exact timestamp eligibility | not verified | No publication times/timezones displayed; boundary candidates omitted. |
| All three configured sources inspected | passed | Three successful index retrievals documented above. |
| Mainly use configured sources; no minimum per source | passed | All selected URLs originate from configured indexes: one Anthropic News, four OpenAI News. Zero Anthropic Engineering items is permitted. |
| Read selected article bodies during this run | passed | Five bodies inspected; source sections recorded in ledger. |
| Ground summaries in actual content | passed | Each summary checked against the corresponding body sections, including testing/availability qualifications. |
| Title, summary, tags, specific article citation | passed | Every entry includes linked article title, date, summary, and Tags line. Title link cites the entry; summaries are paraphrases. |
| Normalize categories and sort alphabetically | passed | Engineering, Product, Safety and Research; mapping recorded above. |
| Combined summaries at most 300 words | passed | 124 whitespace-delimited words, excluding titles, tags, links, dates, and introductory notes. |
| Explicit baseline comparison | not applicable | None supplied; code.md explicitly requires first-run behavior. |
| Five recurring topics covered more than once in past month | not applicable | Fallback not triggered in first-run mode; no monthly recurrence claims made. |
| Discovery through coverage window | not verified | Anthropic listings extend past boundary; OpenAI continuation inaccessible in text interface and RSS alternative unsupported. Limitation disclosed, not hidden. |
| Unique output and preservation of prior runs | passed | Directory created with exist_ok=False; only new report.md and log.md written. |
| Recurring schedule not activated | passed | No scheduling tools or actions used. |
| Monday 07:00 EST scheduling behavior | not applicable | Scheduling intentionally excluded from this test; not a report failure. |

Overall: report content and format checks passed. Discovery completeness and exact timestamp precision remain not verified. Comparison, monthly-topic fallback, and scheduling are not applicable to this test. No failed checks.
