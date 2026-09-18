# Verification evidence — September 11, 2026

These are generated run artifacts and measured checks, not a student's personal
explanation. Each student still needs to write their own explanation file.

| Run | Published entries | Result | Model invoked |
| --- | ---: | --- | --- |
| [Initial live run](20260911T193243Z-10a1811b.md) | 10 | Anthropic succeeded; OpenAI article requests returned HTTP 403 | Yes |
| [RSS fallback recovery](20260911T193508Z-c8e47339.md) | 5 | All three indexes checked; OpenAI explicitly uses official RSS descriptions | Yes |
| [Unchanged repeat](20260911T193803Z-287a3b5c.md) | 0 | No duplicates, no notification; RSS limitation recorded | No |

Each digest has a same-named `.json` result and `.jsonl` harness execution record.
The exported model metadata shows only `agent_message` completed items, with no
tool actions during summarization. Full local source and model traces remain in
ignored `outputs/live/`.

[Offline checks](tests.txt): 21 tests passed, including source failures, blocked
pages, RSS fallback, stale publication, failed disk writes, future dates, baseline
handling, content updates, URL restrictions, invalid or missing evidence, daily
file separation, Eastern dates/DST, unchanged-run preservation, and report rebuilding.
The original snapshots above retain their historical format. Current daily reading
files live in `../live/reports/YYYY-MM-DD.md`; coverage details live in per-run logs.
[Machine-readable check summary](checks.json).

The app automation `auralin-research-update` was created and read back as ACTIVE
with Monday–Friday 9:00 AM recurrence. The Mac timezone was checked and is
America/New_York. Scheduled wall-clock execution has not yet occurred; the same
local command has been exercised manually. The Mac and desktop app must be running.

To rerun the tests and export another reviewed completed run, from the team folder:

```sh
python3 code/verify.py RUN_ID
```
