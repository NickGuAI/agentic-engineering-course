# Studio 02 evidence -- run overview

Date: 2026-09-17
Harness: pi (`@earendil-works/pi-coding-agent`), version 0.85.1 (`pi --version`)
Model: `google/gemini-3.1-flash-lite` for every run of real evidence in this folder. The scripts'
  `--model` default is now the Codex spark model, `openai-codex/gpt-5.3-codex-spark` (see README.md
  "How we chose a model"), but that default is untested here: it needs a ChatGPT/Codex login this
  machine does not have.
Corpus: Mei et al. 2025, A Survey of Context Engineering for Large Language Models, arXiv 2507.13334
  (70,802 words; ~94,167 estimated tokens by the words x 1.33 rule; the real, pi-reported token
  count for the full corpus was 159,142 -- see EXPLANATION.md section 2 for why)
Total real spend across Part A, B, and C's kept evidence: $0.3151 (69 model calls). This does not include
several earlier runs spent finding and fixing real bugs (an argument-size crash, an answer-parsing bug,
and two test-isolation leaks described in EXPLANATION.md section 4) before this evidence was produced;
the true total across all runs today was under $0.70.

## Part A: Context Window Stress Test

| size | est. tokens | input tokens | cached tokens | output tokens | score | wrong/missing Qs |
| --- | --- | --- | --- | --- | --- | --- |
| 8k | 7,993 | 10,842 | 0 | 295 | 2/5 | 2, 3, 4 |
| 16k | 16,000 | 21,140 | 0 | 195 | 3/5 | 3, 4 |
| 32k | 31,997 | 21,248 | 20,462 | 1,076 | 5/5 | -- |
| 64k | 63,994 | 59,652 | 40,945 | 1,150 | 5/5 | -- |
| full | 94,167 | 159,142 | 0 | 1,043 | 5/5 | -- |
| 2x (optional) | 188,341 | 317,611 | 0 | 799 | 5/5 | -- |
| 3x (optional) | 282,516 | 164,807 | 311,273 | 993 | 5/5 | -- |

No size scored below an earlier best, so no "first failure" fired under the contract's strict rule.
2x and 3x are optional sizes past "full": the whole corpus plus 1 or 2 extra, reshuffled rounds of its
own section files appended as distractor padding, for models like this one whose 1,048,576-token context
window is too large for "full" alone (159,142 real tokens) to threaten. Even at 3x (476,080 total real
tokens, almost half the context window), the score held at 5/5 -- no degradation or overflow observed on
this model at this scale. See EXPLANATION.md for the size at which each fact first appears and why the
score still climbs from 8k to 32k even though nothing ever regressed within this run.

## Part B: Isolate and Compress

| method | score | tokens (final scored call) | cost |
| --- | --- | --- | --- |
| Part A best (32k) | 5/5 | 21,248 | $0.0074 |
| Isolate (lead, from sub-agent findings) | 5/5 | 1,231 | $0.0342 |
| Compress: summary artifact | 5/5 | 910 (summary ~161 tokens) | $0.0013 |
| Compress: pi's own auto-compaction | 4/5 | 17,275 (1 compaction fired, tokensBefore 83,909) | $0.0300 |

Not re-run for this delta: Part A's best run is still 32k (still the smallest run that already scored
5/5, even counting 2x/3x), so Part B's numbers are unchanged. Isolate and the summary artifact both
recovered full marks at a fraction of the tokens of Part A's best run. Auto-compaction lost exactly one
fact (question 2, LongRoPE's context window) -- the one fact in the corpus that is stated only once; the
other four facts are each restated in at least two places in the survey and survived compaction.

## Part C: File-based Memory vs. Memoryless Baseline

| decision | with memory (session 3) | no-memory baseline (session 3) |
| --- | --- | --- |
| storage format for notes | correct | missing |
| command name for the tool | correct | missing |
| date format for entries | correct | missing |

The with-memory run correctly recalled all 3 of 3 decisions from `decisions.md`, each dated with today's
real date (2026-09-17, injected from the system clock -- an earlier run, before that fix, dated entries
2025-05-14, since the model has no clock of its own). The no-memory baseline recalled 0 of 3 and said,
correctly, that it could not find any record, after trying many plausible filenames within its own
directory. Getting a clean baseline took two fixes, not one: giving the recall step only a `read` tool
(no directory listing) stopped it from listing the sibling directory, but a baseline still found the
other run's `decisions.md` by guessing relative paths and reading its way up to this project's own
README.md, which documents the with-memory/no-memory layout. The fix that actually closed this was a
`--append-system-prompt` instruction telling the recall step to only use its current directory. See
EXPLANATION.md section 4 for the full account.

## Where everything is

- `part_a/run-<size>.json`, `part_a/summary.md` (raw event logs are captured locally too, but are not
  committed -- see README.md "Evidence size note")
- `part_b/findings/section-NN.md`, `part_b/isolate.json`, `part_b/summary-of-part-a.md`,
  `part_b/summary-artifact.json`, `part_b/compaction.json`, `part_b/summary.md`
- `part_c/decisions.md`, `part_c/fib.py`, `part_c/session3-with-memory-answer.md`,
  `part_c/session3-no-memory-answer.md`, `part_c/part_c.json`, `part_c/summary.md`
- `sessions/*.jsonl` -- pi's own session files for every run above (via `--session-dir`)
- `EXPLANATION.md` -- the graded write-up
