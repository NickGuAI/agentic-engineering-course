# Studio 01 evidence audit

AI-generated technical audit, September 11, 2026. This is not the student's personal explanation and must not be submitted as that explanation.

Requirements checked against the current [Studio01.md](https://github.com/NickGuAI/agentic-engineering-course/blob/main/studio/Studio01.md) and [workspace README](https://github.com/NickGuAI/agentic-engineering-course/blob/main/studio/README.md).

| Requirement | Evidence and status |
|---|---|
| Course preparation | Local Codex, Git, Tavily, and connected Gmail were used. Full Course Prep completion and CourseWorks requirements have not been audited. |
| Choose and frame a job | Complete: Research Update; the delegation card has exactly the four requested fields. |
| Individual folder | Corrected during audit: all task artifacts now live under `studio/Elad_Hirsh/`, using the name supplied for the working branch. |
| Teammate exercise | User feedback and revisions are recorded in the conversation. A human teammate swap/paraphrase/debrief is not evidenced; do not claim it occurred. |
| Run local agent on a bounded recurring job | A local Tavily research attempt is saved. The recurring automation is active, but no scheduled end-to-end news-card delivery is evidenced yet. |
| Inspect output and execution trace | Complete for the attempted run: saved JSON errors/results, article-date inspection, and explicit stop output. |
| Change, observe, correct, compare | Planning changes are documented. Runtime evidence also compares a raw-content validation error against a successful empty search after removing the incompatible flag. Extraction recovery is documented, although it changed both batch size and depth. |
| Responsible stop | Documented: retrieved candidates did not satisfy the original reporting window. This is permitted by the assignment, but does not establish that the card-generation success criteria passed. |
| Preserve artifacts | Delegation card, run prompt, raw retrieval results, output, execution record, and planning history are saved in this folder. There is no standalone application code: execution uses Codex, Tavily, and an app-managed automation. |
| Personal explanation | MISSING. The student must personally create `explanation-Elad_Hirsh.md`, without AI-generated text. Existing AI-generated records are supporting evidence only. |
| Dedicated branch from updated course main | Local branch `Elad_Hirsh_Studio01` exists. This repository began with an independent root commit; it is not yet based on an updated checkout of the course repository. |
| PR to course main | NOT DONE, intentionally: user prohibited pushing and PR creation. Future submission requires reconciling the local work with the course repository workflow. |
| Delete branch after merge | Not applicable yet. Preserve this unmerged branch. |
| Official submission | Not checked or submitted. CourseWorks controls official instructions and deadlines. |

## Product verification limits

No five-minute visual news edition has been generated or visually inspected. No WSJ author's eligibility has been demonstrated. Gmail sending was tested and the user confirmed receipt, but that was a setup message, not a visual briefing or a scheduled run. Monthly date gating, hourly detection, deduplication, and unattended Gmail availability remain configured behavior rather than tested outcomes.

The first run used September 4–11. The later switch to calendar-month coverage does not retroactively change that run's evidence. References in relocated Markdown files were updated for navigation; the raw JSON responses remain unchanged.

## Remaining student actions

1. Write the personal explanation yourself, covering what the agent did, your decisions and reasons, verification, and uncertainties. Use the records as evidence, not as text to copy.
2. Check the teammate activity, Course Prep, and CourseWorks requirements against what you actually completed.
3. When ready to submit, authorize the course-repository integration and PR workflow. No push or PR is authorized now.

A successful visual-card run would additionally demonstrate the product's own success criteria. The current evidence supports an inspected attempt with a responsible stop, not a finished news product. This audit does not determine a grade or guarantee instructor acceptance.

## Submission preparation update

The earlier audit above is a historical snapshot. The student has now supplied the personal explanation, saved verbatim. A seven-card August report was generated and Gmail accepted delivery; browser visual inspection was blocked, so rendering remains unverified. See `runs/2026-08-monthly/run-record.md`. The user has now authorized a PR. Submission is being prepared in a clean checkout of current course main, using the student folder and the branch `Elad_Hirsh_Studio01` in the user fork. Scheduled end-to-end behavior and CourseWorks submission remain unverified.
