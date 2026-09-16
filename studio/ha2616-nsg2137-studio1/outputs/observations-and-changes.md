# Run observations and changes

Agent-generated record of observable events; personal explanations are separate.
These are new local Codex runs from September 16, 2026. Logs were not recovered
for the original September 11 email attempts, which remain in Git history.

| Run | Condition | Observed result |
| --- | --- | --- |
| [1](run-1-output.md) | Valid source-list input | 509-word briefing; six web calls. |
| [2](run-2-output.md) | Changed only the input path to a nonexistent source-list file | File read exited with code 1; explicit STOP response; zero web calls. |
| [3](run-3-output.md) | Restored the original valid input path | 553-word briefing; six web calls. |

From run 1 to run 2, the prompt's source path changed from `inputs/sources.txt`
to `inputs/missing-sources.txt`. The as-of timestamp also advanced naturally.
Run 2's log records `No such file or directory`; the agent stopped instead of
inventing input. The correction for run 3 was to point back to the original
source file. Its contents matched run 1. The task instructions were unchanged.

All three CLI processes completed successfully; run 2 was a responsible task
stop, not a successful briefing. The two briefings stayed under 800 words and
labeled older items as carried forward. Neither established that no newer news
existed. Basic structural checks do not prove factual accuracy or completeness.

Each run log contains its exact prompt, available source input, timestamps,
raw Codex events, and CLI diagnostics. Final outputs match the final messages
in those events. The source file and wrapper used during capture were removed
from the submission to keep only the evidence; their contents or history remain
available. No email was sent and no schedule was installed by these local runs.
