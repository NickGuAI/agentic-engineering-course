# Studio 01 — research briefing

This folder preserves Hiba and Natalie's original email-briefing attempt and adds
new local Codex runs with captured execution evidence. The September 11 prompts
and screenshots are historical artifacts; no execution trace was recovered for
those runs. The new logs are not reconstructions of that history.

## Run locally

Requirements: Python 3.9+ and Codex CLI, already signed in with your own account.
No packages or API keys are stored in this folder. From the repository root:

```bash
python3 studio/ha2616-nsg2137-studio1/code/run.py run-01-baseline
python3 studio/ha2616-nsg2137-studio1/code/run.py run-02-missing-input --sources inputs/missing-sources.txt
python3 studio/ha2616-nsg2137-studio1/code/run.py run-03-restored-input
```

Use new run names when repeating these commands; existing evidence is never
overwritten. The second command changes only the input path to a nonexistent file.
The third restores the original path. The prompt and runner remain the same.
Live news and model outputs may vary between runs.

The daily job can be invoked again at 8 AM America/New_York. This submission does
not install a scheduler or send email. Its observable artifact is a local briefing;
the original email delivery goal is preserved in `outputs/delegation-card-original.md`.

## Evidence files

`outputs/comparison.json` records the three runs side by side using their saved
logs and checks: word counts, web calls, source hashes, and shell exit codes.
It is an agent-generated evidence index, not a student's personal explanation.

Each new run saves:

- `prompt.txt`: exact rendered prompt and UTC as-of time.
- `sources.txt`: input snapshot, omitted when the input was absent.
- `trace.jsonl`: actual Codex event stream, including commands and web actions.
- `stderr.log`: CLI diagnostics, including any warnings or errors.
- `briefing.md`: the final response, including a stop response when appropriate.
- `run.json`: command, CLI version, timestamps, source hash, and process exit code.
- `checks.json`: structural checks, separate from manual factual review.

The runner uses the student's saved login and a read-only agent sandbox. It ignores
user configuration to avoid loading unrelated MCP integrations. The prompt caps
web calls at 12; the wrapper imposes a ten-minute timeout. The web-call budget is a
prompt instruction, not a hard transport-level limit. No email integration exists.

Codex's JSONL stream records observable events; it is not a complete copy of every
retrieved web page. Inspect the linked articles to verify facts. A completed CLI
process alone does not prove the briefing is accurate or that no newer news exists.
Log options follow the [official non-interactive Codex documentation](https://learn.chatgpt.com/docs/non-interactive-mode).

## Personal work and submission

`explanation-ha2616.md` is intentionally untouched. Each student must personally
write their own `explanation-<username>.md`, inspect the evidence, and describe
their decisions and uncertainties. The agent does not supply that prose.

No PR is opened until Hiba explicitly requests it. Before requesting submission,
ensure both personal explanations are present and reviewed.
Submit through CourseWorks as instructed. Delete the working branch only after
the upstream PR is confirmed merged; preserve unmerged work.
