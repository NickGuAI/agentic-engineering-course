# Delegation Card

## Task
Build and run a bounded Course Assistant that turns the public Studio 01 materials into a source-linked study digest. Repeat it when preparing for class; demonstrate one missing-input failure and an evidence-led recovery.

## Context
Student folder: `studio/yuanyunchen/`. Audience: a student reviewing delegation and observable execution. Use concise English, a visual workflow, concrete examples, and active-recall questions. Inputs are the pinned public Studio01 guide, workspace instructions, and course-prep guide copied into `inputs/`. Local Codex implements the job and inspects its execution; the resulting offline runner does not call an LLM or network service.

## Success criteria
All three source files must exist and match their recorded SHA-256 hashes. A successful run produces a Markdown digest containing a workflow, submission checklist, source references, and three self-check questions, plus a JSONL trace and machine-readable result. Every factual requirement links to an exact source line range. A missing input must yield nonzero exit status and no digest. After restoring that same input, the run must succeed and reproduce the baseline digest byte-for-byte. Preserve all three run directories and a comparison report.

## Restrictions
Read only the three declared input files; never access Canvas credentials or other students' work. Write only inside this student folder. No network calls, installations, paid services, background schedule, or automatic submission. Never invent a deadline. Stop on missing or changed sources rather than reuse stale output. Do not generate the student's personal `explanation-yuanyunchen.md`; the course requires the student to write it without AI-generated text.
