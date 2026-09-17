# Context sweep: accuracy vs. context length -- summary

## Correction

The first scoring pass had two bugs, both in the scorer, not in the model calls: (1) the answer parser matched only single-digit question numbers, so answers 10-20 were silently read as continuation text of answer 9 and scored wrong or hallucinated regardless of their real content; (2) several keyword groups required only terms already present in the question text (so a terse correct answer could not match) and number-format variants like "2,048K" vs "2048K" were not normalized. All 7 model calls below are the original ones from the first run (same answer_text, same usage, same timing, same cost) -- nothing was re-run. These figures are the fixed parser and scorer re-applied to that same saved answer_text, with the revised questions.json (keyword groups now answer-bearing terms only; gold answers and needle depths unchanged). 91 of 140 (size x question) verdicts changed, all from wrong or hallucinated to correct; none moved the other way. See rescore_diff.json for the full list.

Model: `openai-codex/gpt-5.6-luna` (Codex subscription, `--thinking low`)
Corpus: corpus/combined.txt, 307944 words, 579456 real tokens (tiktoken o200k_base)
Model context window: 272000 tokens

| size | slice real tokens | pi input tokens | overall accuracy | in-slice accuracy | abstention accuracy | wall time | error |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 16k | 15800 | 16875 | 100% (20/20) | 100% (n=4) | 100% (n=16) | 10.67s |  |
| 32k | 31654 | 32729 | 100% (20/20) | 100% (n=4) | 100% (n=16) | 11.97s |  |
| 64k | 63258 | 64333 | 100% (20/20) | 100% (n=5) | 100% (n=15) | 16.33s |  |
| 128k | 126535 | 127610 | 100% (20/20) | 100% (n=5) | 100% (n=15) | 13.75s |  |
| 200k | 197790 | 198865 | 100% (20/20) | 100% (n=11) | 100% (n=9) | 13.0s |  |
| 256k | 252785 | 253860 | 100% (20/20) | 100% (n=15) | 100% (n=5) | 15.85s |  |
| full | 579456 | 580786 | 100% (20/20) | 100% (n=17) | 100% (n=3) | 18.16s |  |

'overall accuracy' is correct / all questions in questions.json. 'in-slice accuracy' is correct / (questions whose needle sits inside this slice and are not expect_not_found) -- can a call that has the fact in view actually answer it. 'abstention accuracy' is correct / (questions whose needle is beyond this slice, plus expect_not_found questions) -- does the model correctly say NOT FOUND rather than guessing. A question with no needle_depth_tokens is always counted as in-slice/answerable.

## Question ids in-slice per size

- **16k**: 1, 2, 3, 5
- **32k**: 1, 2, 3, 5
- **64k**: 1, 2, 3, 4, 5
- **128k**: 1, 2, 3, 4, 5
- **200k**: 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11
- **256k**: 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15
- **full**: 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17

## Flagged: verbose-but-correct (matched every gold keyword group, but also contains a must_not_contain distractor term -- scored wrong per the section-5 rule; listed here for a human to re-score by hand)

None at any size.

See results.json and results.csv for the per-question, per-size verdicts (correct / wrong / hallucinated) and the verbose_but_correct flag, and accuracy_vs_length.png / heatmap.png for the charts.
