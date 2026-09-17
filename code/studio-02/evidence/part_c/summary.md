# Part C: File-based Memory vs. Memoryless Baseline -- summary

Model: `google/gemini-3.1-flash-lite`
AGENTS.md source: studio/studio-02/starter/AGENTS.md

Session 1 wrote decisions.md with ~3 dated entries.
Session 2 (unrelated fib.py task) left decisions.md with ~4 dated entries.

Recall of the three session-1 decisions, asked fresh in session 3:

| decision | with memory (session 3) | no memory baseline (session 3) |
| --- | --- | --- |
| storage format for notes | correct | missing |
| command name for the tool | correct | missing |
| date format for entries | correct | missing |

'correct' = the answer's content for that decision overlaps with what decisions.md actually recorded. 'invented' = the answer addresses that decision but does not match what was recorded (or nothing was ever recorded for it). 'missing' = the answer does not address that decision at all. This is an automated keyword-overlap heuristic; the actual answer text is saved alongside this file for a human to check.

With-memory session 3 answer: see session3-with-memory-answer.md
No-memory baseline session 3 answer: see session3-no-memory-answer.md
