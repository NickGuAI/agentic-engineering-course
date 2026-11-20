Read studio/ObserverZQ/delegation-card.md and execute one test run.

Write:
- studio/ObserverZQ/outputs/<run-id>/report.md
- studio/ObserverZQ/outputs/<run-id>/log.md

Use a unique timestamp as <run-id>; do not overwrite previous runs.

In the log, record the coverage window, sources attempted,
article URLs and dates, selection or exclusion reasons, and checks
against the delegation card's requirements.

Report checks as passed, failed, or not verified, with evidence.
If browsing is unavailable, report the blocker instead of generating
a news report or claiming successful validation.

Do not activate a recurring schedule.

Treat test runs separately from production cycles.

For comparison, use an explicitly supplied baseline report.
If none is supplied, treat the test as a first run and record
comparison and fallback checks as not applicable.

Read each selected article's body during this run.
Do not validate summaries using headlines or prior summaries alone.

Inspect each source's dated listing, following pagination as needed
until the coverage window is covered. If this is blocked, record
the discovery limitation; do not claim exhaustive coverage.

Log the baseline path, selected URLs, publication dates,
source categories, editorial labels, and combined summary word count.

Use passed, failed, not verified, or not applicable.
Only fail requirements explicitly stated in the delegation card.
Do not treat intentionally untested scheduling as a report failure.