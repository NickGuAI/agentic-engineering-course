# Curated execution record

Recorded on 2026-09-18. This is an AI-authored summary of observed tool activity and delegated-agent completion reports, not a raw session transcript or student explanation. It omits credentials and internal reasoning. The original interactive run occurred in the current Codex desktop conversation.

## Execution environment and limits

- The human supplied the article URL, requested assignment assistance, and identified their GitHub username as `yangcan1`.
- The coordinator read the Studio 1 instructions, prepared the delegation card, shared prompt, and two input files before starting the baseline generation.
- Each condition was executed by a separate delegated Codex agent invocation. The exact backend model version was not captured, and no separately configured API script was executed.
- All three agents received the same shared prompt and card. The card names the study as context, but the shared prompt makes the per-run JSON URL the prerequisite for browsing. Thus the changed run tests enforcement of that input boundary; it does not test forgetting the article's identity.
- Successful-run agents retrieved the live source independently. Outputs and tool-use reports were returned to the coordinator. The changed-run tool report contains no browsing call.
- No claim is made that an unaudited narrative proves every internal model action. The committed record contains useful summarized evidence, not a cryptographically complete execution transcript.

## 1. Baseline — `baseline_run`

Input: `runs/baseline-input.json`.

Observed/reported sequence:

1. `exec_command` read course instructions, the delegation card, shared prompt, and baseline input.
2. `web.run.open` retrieved the exact supplied URL successfully, including its publication date and article body.
3. `apply_patch` wrote `outputs/baseline.md`.
4. `exec_command` reread the output and counted its prose.
5. The coordinator reread the output, compared attribution and timing against the retrieved source, and executed `verify.py --team yangcan1 --phase baseline`.

Result: COMPLETE; 160 prose words. All 11 checks in the baseline report passed. Factual interpretation was reviewed separately from those checks. Human acceptance remains pending.

## 2. Changed condition — `missing_input_run`

Input: `runs/changed-input.json`. The only changed key was `source_url`, from the selected URL to null; the checked-on date and shared instructions remained fixed.

Observed/reported sequence:

1. `exec_command` read course instructions, the delegation card, shared prompt, and only the changed run input.
2. On seeing the missing URL, the agent made no browsing call and used `apply_patch` to write `outputs/changed.md`.
3. `exec_command` reread that output.
4. The coordinator reread the output and executed `verify.py --team yangcan1 --phase changed`.

Result: BLOCKED_MISSING_INPUT, with a request to provide the URL. All 8 changed-phase checks passed. This is a successful safe stop under the task contract, not successful article generation.

## 3. Evidence-led correction and recovery — `recovery_run`

The changed output identified the missing prerequisite. The coordinator restored that prerequisite by supplying the original `runs/baseline-input.json` to a new agent. No prompt, date, or acceptance criterion changed, and the prior output files were preserved.

Observed/reported sequence:

1. `exec_command` read course instructions, the delegation card, unchanged shared prompt, and restored baseline input. No prior output was read.
2. `web.run.open` retrieved the exact supplied URL successfully.
3. Python through `exec_command` counted the prose and wrote `outputs/recovery.md`.
4. The coordinator reread recovery output and executed `verify.py --team yangcan1 --phase all`, covering all three saved results and their inputs.

Result: COMPLETE; 145 prose words. All 22 combined checks passed. The recovered text differs from the baseline, as expected for a new generation; the task contract is preserved.

## 4. Review boundary

A separate agent reviewed the article and the completed artifacts, identifying no substantive attribution error in either completed output and confirming that the missing-input output stopped without article details. This is agent editorial review. It does not constitute the classroom human teammate exchange, independent external verification of company claims, student acceptance, or official submission.
