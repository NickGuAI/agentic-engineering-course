# Benchmark pilot: Graphwalks / BABILong / MRCR 8-needle -- results

Three public long-context benchmarks piloted on `openai/gpt-5.6-luna` (`--thinking low`), against a fixed, reproducible 40-item stratified subset (seed 7, see `benchmarks/subset.json` and `benchmarks/prepare_subsets.py`). Each benchmark graded with its own published grader -- F1 on node sets (Graphwalks), exact match after lowercase+strip (BABILong), hash-prefix check + `difflib.SequenceMatcher` ratio (MRCR). Scores are NOT comparable across benchmarks in level, only in shape (see `curves.png` caption).

**Total: 40/40 items run, $2.5282 spend (hard stop was $4.00), 4.5 minutes of summed per-item wall time (6-way concurrent, so real wall clock was much less), 5 length refusals.**

## Graphwalks (F1 on node sets; task = bfs or parents)
| bucket | task | n | n scored | mean F1 | mean real tokens | mean wall (s) | errors |
| --- | --- | --- | --- | --- | --- | --- | --- |
| ~128K | bfs | 2 | 2 | 100.0% | 128,432 | 7.5 | 0 |
| ~128K | parents | 2 | 2 | 60.0% | 128,364 | 5.6 | 0 |
| ~256K | bfs | 2 | 2 | 96.5% | 255,838 | 7.1 | 0 |
| ~256K | parents | 2 | 2 | 70.0% | 255,805 | 5.2 | 0 |
| ~1M | bfs | 2 | 0 | n/a | n/a | n/a | 2 refusal(s) |
| ~1M | parents | 2 | 0 | n/a | n/a | n/a | 2 refusal(s) |

Note on the BFS cells: since BFS answer-set sizes are strongly right-skewed (up to ~6,900 nodes in this data), the 2 replicates per BFS cell were chosen near that cell's MEDIAN answer-node count -- filtering on answer SIZE only, never on difficulty or correctness.

## BABILong (exact match, lowercase+strip; task = qa1 or qa2)
| bucket | task | n | n scored | accuracy | mean real tokens | mean wall (s) |
| --- | --- | --- | --- | --- | --- | --- |
| 32k | qa1 | 2 | 2 | 50.0% | 31,262 | 1.4 |
| 32k | qa2 | 2 | 2 | 0.0% | 30,946 | 1.9 |
| 128k | qa1 | 2 | 2 | 100.0% | 123,428 | 2.3 |
| 128k | qa2 | 2 | 2 | 0.0% | 120,648 | 2.5 |
| 512k | qa1 | 2 | 2 | 50.0% | 484,361 | 5.7 |
| 512k | qa2 | 2 | 2 | 0.0% | 493,367 | 13.0 |

## MRCR 8-needle (hash-prefix check + SequenceMatcher ratio)
| bucket (tokens) | n | n scored | mean ratio | mean real tokens | mean wall (s) | errors |
| --- | --- | --- | --- | --- | --- | --- |
| (4096,8192] | 2 | 2 | 99.9% | 6,796 | 4.3 | 0 |
| (8192,16384] | 2 | 2 | 50.0% | 15,428 | 23.0 | 0 |
| (16384,32768] | 2 | 2 | 100.0% | 25,513 | 8.0 | 0 |
| (32768,65536] | 2 | 2 | 55.2% | 47,884 | 6.2 | 0 |
| (65536,131072] | 2 | 2 | 51.1% | 99,696 | 5.7 | 0 |
| (131072,262144] | 2 | 2 | 9.9% | 189,406 | 8.3 | 0 |
| (262144,524288] | 2 | 2 | 52.6% | 460,102 | 10.9 | 0 |
| (524288,1048576] | 2 | 1 | 100.0% | 683,068 | 11.7 | 1 refusal(s) |

## Headline comparison: shortest vs. longest bucket per benchmark
| benchmark | shortest bucket | score | longest bucket | score | delta |
| --- | --- | --- | --- | --- | --- |
| Graphwalks (bfs+parents) | ~128K | 80.0% | ~1M | n/a | n/a |
| BABILong (qa1+qa2) | 32k | 25.0% | 512k | 25.0% | 0.0% |
| MRCR 8-needle | (4096,8192] | 99.9% | (524288,1048576] | 100.0% | 0.1% |

For reference, our own two prior results on this course's own materials: the 20-question needle sweep (`evidence/context_sweep/`) scored 100% at every size from 16K to 580K real tokens; the 20-item comprehension check (`evidence/comprehension/`) scored 100% with only the 20 relevant excerpts (~5K tokens) and 80% with the full 551K-token corpus.

## Length refusals
5 items (4 Graphwalks `~1M`, 1 MRCR `(524288,1048576]`) were refused outright with the exact error text `"Your input exceeds the context window of this model. Please adjust your input and try again."`, at $0 cost each (rejected before any tokens were billed). Per the contract, the `~/.pi/agent/models.json` `contextWindow` override for `openai/gpt-5.6-luna` was raised from 1,050,000 first to 1,400,000, then as a confirmatory test to 5,000,000 -- the refusal was byte-for-byte identical every time, including at 5,000,000, which rules out the override as the mechanism (it was load-bearing for the earlier ~552K-token comprehension-check run, but has no effect here). The real ceiling sits somewhere between the largest item that succeeded (MRCR, 673,520 real input tokens) and the smallest that was refused (MRCR, 998,200 real input tokens) -- independent of any client-side override we can set. The override was left at 1,050,000, its last proven-useful value. These 5 items are recorded with `score: null` (refusal, not a zero) and excluded from the means above.

| id | benchmark | task | bucket | real input tokens (estimate) |
| --- | --- | --- | --- | --- |
| 9 | graphwalks | bfs | ~1M | 1,022,645 |
| 10 | graphwalks | bfs | ~1M | 1,022,225 |
| 11 | graphwalks | parents | ~1M | 1,022,759 |
| 12 | graphwalks | parents | ~1M | 1,022,640 |
| 39 | mrcr | 8needle | (524288,1048576] | 998,200 |

See `curves.png` for the plotted comparison across all three benchmarks plus our own two prior results.
