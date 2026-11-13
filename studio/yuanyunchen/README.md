# Course Assistant — Studio 01

**Status: implementation and experiment complete; an AI-assisted reflection draft is included, but the required personally written explanation is still pending.**

A source-linked study digest for reviewing the Studio 01 delegation exercise. Local Codex built the implementation and ran the experiment using the student's authenticated session. The reusable Python program is an **offline deterministic renderer**, not an autonomous LLM and not evidence of model reasoning quality. It packages an AI-authored, source-reviewed learning scaffold with explicit freshness checks.

## Inspect the evidence

- [Delegation card](delegation-card.md): exactly four fields.
- [Study digest](outputs/baseline/digest.md): visual workflow, requirements, citations, and self-checks.
- [Baseline trace](outputs/baseline/trace.jsonl): successful source verification and output hash.
- [Missing-input trace](outputs/missing-input/trace.jsonl): explicit stop identifying `workspace.md`.
- [Recovered trace](outputs/recovered/trace.jsonl): restored source and successful rerun.
- [Machine comparison](outputs/comparison.json): failure has no digest; recovery matches baseline byte-for-byte.
- [Validation report](outputs/validation.json): independently executed checks.

The three inputs are verbatim public course files pinned in `sources.json` to an upstream commit and SHA-256. Citations use that commit, so later edits to `main` do not silently change the evidence. No Canvas data, credentials, personal student IDs, or private course files are included.

## Repeat the bounded job

Requires Python 3.11+ and no external packages. From this folder, choose an unused run directory:

```bash
python3 code/course_assistant.py --out outputs/my-review
```

Review this digest before class. It is a manually repeated job; no scheduler has been installed. To update materials, review source content and citations before updating the snapshot and pins. A changed source fails closed until that review is complete. The runner refuses to reuse an existing output directory, so old success artifacts cannot masquerade as a fresh run.

To reproduce the committed experiment without altering the preserved evidence, copy **this student folder only** to a scratch location, remove its copied `outputs/` directory there, and run:

```bash
python3 code/course_assistant.py --out outputs/baseline
python3 code/run_experiment.py
python3 code/validate.py
```

The experiment changes exactly one input condition: a separate input copy lacks `workspace.md`. The resulting `missing_input` report drives restoration of that exact source from the pinned original. It does not disable checks or modify the expected hash. The failed input snapshot remains under `outputs/missing-inputs/`.

## Authorship and submission boundary

Code, card, digest, and machine evidence are AI-assisted. This README and the comparison are not substitutes for the required personal explanation. `explanation-yuanyunchen.md` is explicitly labeled as an AI-assisted draft. It does not satisfy the no-AI personal explanation requirement. The student must replace it with a personally written explanation before this is a complete submission. The seven-minute peer exercise has not been claimed as completed.

CourseWorks owns official submission instructions and deadlines. On September 16 its assignments API returned an empty list for this course; no deadline is inferred. A draft PR is a review location, not confirmation of official submission. Do not delete this branch until its PR has actually merged.
