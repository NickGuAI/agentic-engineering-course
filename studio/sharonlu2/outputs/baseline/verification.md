# Verification — baseline

## Run
- Run ID: `research-update-20261014-202318-40f0bd`
- Started: `2026-10-14T20:23:18.712383-04:00`
- Model: `gpt-6-luna`; harness: Codex CLI. Per-invocation CLI version and effective reasoning effort were not recorded.
- Development metadata records Codex CLI `0.162.1`; this does not independently establish the version of every runtime invocation.
- Report: [research-update-20261014-202318-40f0bd.md](research-update-20261014-202318-40f0bd.md)
- Run record: [research-update-20261014-202318-40f0bd.json](research-update-20261014-202318-40f0bd.json)
- Window: 2026-10-07 through 2026-10-13 inclusive, excluding the run date.
- Raw invocation ID: `codex-20261015T002336Z-c4a3ac86`. Raw logs remain outside Git.
- Verification date: 2026-10-14.

## Checks

| Criterion | Method and evidence | Assistant finding |
|---|---|---|
| At most 10 entries, required fields, descending dates | Inspect report and JSON `articles`: 10 entries, required fields present, recorded dates descending | Pass for structure; does not establish date accuracy |
| Real model invocation and preserved response | `invocation.json`: exit status 0; `events.jsonl`: thread/turn events and agent response; `response.txt` preserved | Pass for execution and local evidence |
| Accurate publication dates | “Helping small businesses put AI to work” is recorded as 2026-10-13; the linked reference page displayed September 30, 2026 during review. “Redesigning source control at Anthropic” is recorded as 2026-10-12, while the reference page displayed October 13 | Fail in the sampled cases |
| Correct date-window selection | The small-business article was included despite the reference publication date falling outside the window | Fail in the sampled case |
| Source failures disclosed | Engineering source is `partial`; report and run record are `incomplete` | Pass for disclosure; failure details are insufficient |
| Summary fidelity | A limited assistant spot-check found support for selected numeric claims in the saved model input; all ten summaries were not fully checked against primary pages | Not fully verified |

## Execution metrics
- Model exit status: `0`.
- Program status: `incomplete`; saved console exit code: `2`.
- Model usage reported in the event log: input 35009, output 1051, cached input 12032.

## Decision
Date accuracy and eligibility failed in sampled cases. Need fixing.

## Limitations
- Website content and access conditions can change between runs and later review.
- Dates appearing within the recorded interval are not proof that the extracted dates are correct.
- Primary-page observations made during review were not saved as page snapshots by the original run.

## Reference pages used in assistant review
- [Small-business article](https://openai.com/index/helping-small-businesses-put-ai-to-work/)
- [Source-control article](https://www.anthropic.com/engineering/redesigning-source-control)
- [Asana article](https://openai.com/index/asana-browser-agent/)
- [Higgsfield article](https://openai.com/index/higgsfield-longer-videos-voice/)

## Code identity
Commit `4b20547` preserves the first implementation and baseline artifacts. The original baseline record does not contain a code hash. Do not present the commit as conclusive proof of the exact bytes executed by both old runs.
