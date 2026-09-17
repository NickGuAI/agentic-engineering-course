# Benchmark sweep (v6): Graphwalks / BABILong / MRCR 8-needle, n=20 per cell

Properly-powered rerun of the v5 pilot (n=2/cell, which could only ever read 0/50/100% and was sampling noise, not measurement). n=20 per cell this time, seed 7, all cells at or below 272K real input tokens (the cheap pricing tier). Each benchmark graded with its own published grader, unchanged. 95% CI = mean +/- 1.96 * sample SD / sqrt(n) (normal/Wald approximation), clipped to [0%, 100%] where the symmetric interval would otherwise extend past the valid range -- a known limitation of this method near a 0%/100% mean at small n, not a computation error.

**Total: 242/260 calls run, $8.3328 spend, 20.6 minutes of summed per-item wall time (6-way concurrent), 0 length refusals, 0 other errors.**

**Budget note (read before the tables): the hard stop tripped at $8.0248, $0.0248 over the $8.00 cap** -- 5 calls already in flight when that item completed landed afterward (the harness stops SUBMITTING new work immediately but drains already-dispatched concurrent calls rather than abandoning them mid-request), taking the final total to $8.3328. No further calls were made once this was seen. This left **18 of 260 items unrun, all in `babilong/qa2/256k`**, which therefore has only n=2 in the table below -- the exact underpowered condition this whole redo exists to avoid. Its row is marked accordingly; do not read it as a measured result.

## Graphwalks (F1 on node sets; published grader unchanged)
| bucket | task | n | mean F1 | 95% CI | format-ok rate | F1 among format-ok | mean tokens | mean wall (s) |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| ~128K | bfs | 20 | 60.0% | [38.0%, 82.0%] | 18/20 (90%) | 66.7% | 128,450 | 6.9 |
| ~128K | parents | 20 | 76.3% | [65.0%, 87.6%] | 20/20 (100%) | 76.3% | 128,443 | 5.6 |
| ~256K | bfs | 20 | 80.0% | [62.0%, 97.9%] | 20/20 (100%) | 80.0% | 256,025 | 6.6 |
| ~256K | parents | 20 | 60.3% | [45.3%, 75.4%] | 20/20 (100%) | 60.3% | 255,944 | 6.4 |

## BABILong (exact match, lowercase+strip; published grader unchanged)
| bucket | task | n | accuracy | 95% CI | mean tokens | mean wall (s) |
| --- | --- | --- | --- | --- | --- | --- |
| 32k | qa1 | 20 | 85.0% | [68.9%, 100.0%] | 30,549 | 1.9 |
| 32k | qa2 | 20 | 40.0% | [18.0%, 62.0%] | 30,523 | 2.7 |
| 128k | qa1 | 20 | 75.0% | [55.5%, 94.5%] | 122,552 | 2.4 |
| 128k | qa2 | 20 | 30.0% | [9.4%, 50.6%] | 121,868 | 3.0 |
| 256k | qa1 | 20 | 65.0% | [43.6%, 86.4%] | 241,380 | 3.5 |
| 256k | qa2 | 2 **[UNDERPOWERED -- budget ran out, see note above]** | 0.0% | [0.0%, 0.0%] | 246,286 | 3.8 |

## MRCR 8-needle (hash-prefix check + SequenceMatcher ratio; published grader unchanged)
| bucket (tokens) | n | mean ratio | 95% CI | prefix-ok rate | mean tokens | mean wall (s) |
| --- | --- | --- | --- | --- | --- | --- |
| (16384,32768] | 20 | 59.8% | [39.6%, 80.0%] | 19/20 (95%) | 26,663 | 5.5 |
| (65536,131072] | 20 | 56.8% | [35.8%, 77.9%] | 20/20 (100%) | 90,089 | 7.8 |
| (131072,262144] | 20 | 37.9% | [17.4%, 58.4%] | 20/20 (100%) | 190,418 | 9.0 |

## What n=20 can and cannot detect
At n=20 per cell, the worst-case (p=0.5) standard error is `sqrt(0.5*0.5/20) ~= 11.2` percentage points, so a 95% CI half-width is roughly +/-22 points in the worst case (narrower wherever the true rate sits far from 50%, as several cells above do). Two cells' CIs overlapping is not evidence of no difference, but as a practical guide: reliably distinguishing two means at this n needs a true gap on the order of 25-30 points or more; a 10-point difference between two buckets of the same task is within noise and should not be reported as a trend. Where a benchmark's CIs across buckets overlap substantially in the table above, that is read here as 'no detected degradation across this token range,' not as 'no degradation exists' -- a flat line at n=20 is a real, reportable result, unlike the same-looking flat line at n=2 in the v5 pilot.

For reference, our own two prior results on this course's own materials: the 20-question needle sweep (`evidence/context_sweep/`) scored 100% at every size from 16K to 580K real tokens; the 20-item comprehension check (`evidence/comprehension/`) scored 100% with only the 20 relevant excerpts (~5K tokens) and 80% with the full 551K-token corpus.

See `curves.png` for the plotted comparison, with 95% CI error bars, across all three benchmarks plus our own two prior results.
