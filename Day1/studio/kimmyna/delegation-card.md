# Delegation Card

## Task
For ONE lecture deck per session, produce a text summary and teach-back prompts:
1. Extract keywords → write /summaries/{n}-keywords.json (core ≤ 8 / minor,
   with page numbers). STOP and wait for human approval.
2. Proceed only if /approved/{n}-keywords.json exists; otherwise stop and report.
   Using the approved list, write /summaries/{n}.md: clear explanations of all
   core concepts + a "Lecture Flow" section (written by the assistant) showing
   how concepts connect from start to finish.
3. Write /summaries/{n}-teachback.md: one prompt per approved core keyword.
4. Run scripts/check_summary.py; save its raw output to /summaries/{n}-report.md.

## Context
- Input: /course-materials/lecture-{n}.pdf ({n} = two digits, given by the user)
- Tool: local Claude Code, own account; API keys in local env vars only
- Learning style: text only, no diagrams. The assistant writes the flow;
  the user does not reconstruct it.
- Exam points / cheatsheet: only if explicitly requested
- Approved keywords: /approved/{n}-keywords.json (copied there by the human
  = approval record)
- Outputs: /summaries/{n}.md, {n}-teachback.md, {n}-keywords.json,
  {n}-report.md (always written, pass or fail)
- Run record: prompt, trace, model used, spot-check result → /runs/{n}-{date}/

## Success criteria
- Approval: /approved/{n}-keywords.json exists before step 2 starts
- Automated checks by scripts/check_summary.py (pre-written; not generated
  or edited during the run). All must pass:
  - Coverage: every approved core keyword (or alias) appears in {n}.md
  - Traceability: every paragraph/bullet in concept sections carries [p.N]
    or [보충]; in Lecture Flow, each core concept carries [p.N] on first mention
  - Flow: "Lecture Flow" section exists and mentions all core keywords
    in order of first appearance
  - Prints 5 random tagged items for the human spot-check
- Teach-back: one prompt per core keyword, each asking (a) meaning in own
  words and (b) relation to another core keyword
- No exam/cheatsheet section unless requested
- Human spot-check: reviewer confirms the 5 printed items ([p.N] matches
  the source; [보충] doesn't contradict it); result recorded in
  /runs/{n}-{date}/spot-check.md
- Learning outcome (logged separately, NOT a run gate): teach-back scored
  0/1/2 per item; failures traced to whether the summary covered that relation

## Restrictions
- Do not modify or delete /course-materials, /approved, or /scripts
  (Edit denied in settings.json; Bash limited to allowed commands)
- No WebSearch/WebFetch (denied in settings.json)
- No API keys or personal info in any file
- Content beyond the slides only if tagged [보충]; never contradict the source
- Stop after step 1; do not start step 2 until /approved/{n}-keywords.json exists
- Run is "done" only when check_summary.py passes all checks AND the human
  spot-check passes; no self-declared success
- One deck per session; model (Sonnet) is set by the human at launch and
  recorded in the run record
- Missing/unreadable input or pages → stop and report page numbers;
  do not substitute or invent
- Existing output → do not overwrite without confirmation
- Permission denied → stop and report; do not write elsewhere