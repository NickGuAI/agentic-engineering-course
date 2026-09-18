# Course Assistant run report

- **Status:** ACCEPTED
- **Source:** `studio/Anzide/references/labs/studio/studio-02/instruction/Studio_Instruction.md` (sha256 f1ebbf92a116a381...)
- **Writer:** REPLAY FIXTURE /Users/cyrus/Workspace/agentic-engineering-course/studio/Anzide/code/fixtures/studio02-writer-response.md (no model call)
- **PDF:** `studio/Anzide/outputs/20260918-studio02-replay/Studio_Instruction-tutorial.pdf` via chrome (/Applications/Google Chrome.app/Contents/MacOS/Google Chrome)
- **Cost / turns / wall time:** $0.0000 / 0 / 0.8s
- **Run folder:** `studio/Anzide/outputs/20260918-studio02-replay` (see `trace.md` for every tool call)

## Checks

Attempt: initial

```text
Overall: PASS
[ok] STRUCT-1 Skeleton sections present
[ok] STRUCT-2 Steps numbered in sequence
[ok] STRUCT-3 Every step has Do and Check
[ok] COVER-1 Every source block mapped or explicitly omitted (49 blocks, 0 omitted)
[ok] COVER-2 Code lines and inline code kept verbatim
[ok] COVER-3 URLs kept verbatim
[ok] COVER-4 Numbers kept
[ok] LENGTH-1 Tutorial within word budget (1121 words vs 665 in source (budget 1163))
[ok] LENGTH-2 Each prerequisite note <= 50 words (6 notes)
[ok] ERRATA-1 Each correction quotes real source text and rates confidence (1 corrections)
[ok] PDF-1 PDF exists, has pages, text extractable (210 KB)
```

| Source words | Tutorial words | Budget | Blocks | Tutorials | Steps | Notes | Errata | Omitted |
|---|---|---|---|---|---|---|---|---|
| 665 | 1121 | 1163 | 49 | 3 | 9 | 6 | 1 | 0 |

## Errata proposed by the agent (review before trusting)

| Block | Source says | Should be | Evidence | Confidence |
|---|---|---|---|---|
| S11 | `>= 3.9` | Python 3.11+ | `docs/course-prep.md` says "Python 3.11+", as does the syllabus Resources section; the lab's `setup.sh` checks for 3.9. Using 3.11+ satisfies both. | likely |

## Omitted source blocks (approve or reject)

None.

## Human checks still owed

- [ ] Level match: I can follow every step without looking anything up; no note explains what I already know.
- [ ] Every Errata row is right (or rejected).
- [ ] Every Omitted block may be dropped (or must be restored).
- [ ] Accept the PDF.
