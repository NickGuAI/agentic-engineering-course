# Part B grid: Isolate and Targeted summary, n=20 x 3 buckets x 2 conditions -- summary

Model `openai/gpt-5.6-luna`, thinking `low`, chunk counts per bucket: {'256k': 3, '512k': 6, '768k': 8}. Compaction is NOT part of this run (contract addendum v10). 768K ids [11, 12, 13] are reused from the pre-v10 run, not re-run and not re-charged (see evidence/part_b/results_v9_pre_grid.json for that run's own record).

## 3 x 3 table (bucket x condition)

| bucket | condition | correct/n | mean | 95% CI | mean total tokens | mean peak single-call context | total cost |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 256k | Part A (single call) | 13/20 | 65.0% | [44.1%, 85.9%] | 241,380 | 241,380 | $1.2088 |
| 256k | Isolate | 12/20 | 60.0% | [38.5%, 81.5%] | 243,066 | 81,264 | $1.2179 |
| 256k | Targeted summary | 6/20 | 30.0% | [9.9%, 50.1%] | 244,370 | 81,278 | $1.2389 |
| 512k | Part A (single call) | 14/20 | 70.0% | [49.9%, 90.1%] | 483,375 | 483,375 | $4.8376 |
| 512k | Isolate | 15/20 | 75.0% | [56.0%, 94.0%] | 486,719 | 81,964 | $2.4377 |
| 512k | Targeted summary | 5/20 | 25.0% | [6.0%, 44.0%] | 489,202 | 81,978 | $2.4762 |
| 768k | Part A (single call) | 9/20 | 45.0% | [23.2%, 66.8%] | 766,805 | 766,805 | $7.6718 |
| 768k | Isolate | 17/20 | 85.0% | [69.4%, 100.0%] | 771,355 | 98,026 | $3.8637 |
| 768k | Targeted summary | 7/20 | 35.0% | [14.1%, 55.9%] | 774,651 | 98,040 | $3.9142 |

## Per-item results (same ids Part A scored in every bucket)

| id (bucket) | Part A | Isolate | Isolate peak context | Targeted summary | Targeted summary peak context |
| --- | --- | --- | --- | --- | --- |
| 41 (256k) | correct | WRONG | 83,342 | WRONG | 83,356 |
| 42 (256k) | WRONG | WRONG | 82,466 | WRONG | 82,480 |
| 43 (256k) | WRONG | correct | 81,669 | WRONG | 81,683 |
| 44 (256k) | correct | WRONG | 78,431 | WRONG | 78,445 |
| 45 (256k) | WRONG | correct | 83,621 | WRONG | 83,635 |
| 46 (256k) | correct | correct | 82,045 | WRONG | 82,059 |
| 47 (256k) | correct | correct | 78,232 | WRONG | 78,246 |
| 48 (256k) | WRONG | WRONG | 83,012 | WRONG | 83,026 |
| 49 (256k) | WRONG | correct | 81,850 | correct | 81,864 |
| 50 (256k) | correct | WRONG | 83,251 | WRONG | 83,265 |
| 51 (256k) | correct | correct | 77,988 | correct | 78,002 |
| 52 (256k) | correct | correct | 79,862 | WRONG | 79,876 |
| 53 (256k) | correct | WRONG | 81,209 | WRONG | 81,223 |
| 54 (256k) | WRONG | correct | 77,988 | correct | 78,002 |
| 55 (256k) | WRONG | WRONG | 80,916 | WRONG | 80,930 |
| 56 (256k) | correct | correct | 79,412 | WRONG | 79,426 |
| 57 (256k) | correct | correct | 82,648 | correct | 82,662 |
| 58 (256k) | correct | correct | 82,595 | correct | 82,609 |
| 59 (256k) | correct | WRONG | 82,081 | WRONG | 82,095 |
| 60 (256k) | correct | correct | 82,663 | correct | 82,677 |
| 1 (512k) | WRONG | correct | 82,102 | WRONG | 82,116 |
| 2 (512k) | correct | correct | 79,979 | correct | 79,993 |
| 3 (512k) | WRONG | correct | 80,047 | WRONG | 80,061 |
| 4 (512k) | correct | WRONG | 83,686 | WRONG | 83,700 |
| 5 (512k) | correct | correct | 80,544 | correct | 80,558 |
| 6 (512k) | correct | correct | 79,212 | correct | 79,226 |
| 7 (512k) | correct | WRONG | 82,791 | WRONG | 82,805 |
| 8 (512k) | correct | WRONG | 82,288 | WRONG | 82,302 |
| 9 (512k) | WRONG | correct | 83,924 | WRONG | 83,938 |
| 10 (512k) | correct | correct | 81,522 | WRONG | 81,536 |
| 21 (512k) | correct | correct | 83,993 | WRONG | 84,007 |
| 22 (512k) | correct | correct | 80,069 | WRONG | 80,083 |
| 23 (512k) | correct | WRONG | 84,160 | WRONG | 84,174 |
| 24 (512k) | correct | correct | 78,363 | correct | 78,377 |
| 25 (512k) | correct | correct | 81,268 | WRONG | 81,282 |
| 26 (512k) | correct | correct | 82,044 | WRONG | 82,058 |
| 27 (512k) | WRONG | correct | 82,065 | correct | 82,079 |
| 28 (512k) | correct | correct | 83,689 | WRONG | 83,703 |
| 29 (512k) | WRONG | WRONG | 84,178 | WRONG | 84,192 |
| 30 (512k) | WRONG | correct | 83,346 | WRONG | 83,360 |
| 11 (768k) | correct | correct | 98,165 | correct | 98,179 |
| 12 (768k) | correct | correct | 98,492 | WRONG | 98,506 |
| 13 (768k) | WRONG | correct | 98,257 | WRONG | 98,271 |
| 14 (768k) | correct | correct | 97,542 | correct | 97,556 |
| 15 (768k) | WRONG | WRONG | 98,789 | WRONG | 98,803 |
| 16 (768k) | WRONG | correct | 98,132 | WRONG | 98,146 |
| 17 (768k) | correct | correct | 98,178 | WRONG | 98,192 |
| 18 (768k) | WRONG | correct | 97,365 | WRONG | 97,379 |
| 19 (768k) | WRONG | WRONG | 97,396 | WRONG | 97,410 |
| 20 (768k) | WRONG | correct | 97,405 | WRONG | 97,419 |
| 31 (768k) | WRONG | correct | 98,928 | WRONG | 98,942 |
| 32 (768k) | correct | correct | 97,569 | correct | 97,583 |
| 33 (768k) | correct | correct | 98,185 | WRONG | 98,199 |
| 34 (768k) | WRONG | correct | 99,028 | WRONG | 99,042 |
| 35 (768k) | WRONG | correct | 97,783 | WRONG | 97,797 |
| 36 (768k) | correct | correct | 97,771 | WRONG | 97,785 |
| 37 (768k) | WRONG | correct | 97,261 | correct | 97,275 |
| 38 (768k) | WRONG | correct | 97,540 | correct | 97,554 |
| 39 (768k) | correct | correct | 98,279 | correct | 98,293 |
| 40 (768k) | correct | WRONG | 98,464 | correct | 98,478 |

## What this grid does and does not show

Every cell above is n=20, so its 95% CI spans roughly +/-20-25 percentage points -- wide enough that this grid resolves large, consistent gaps (for example Part A's baseline falling from 65% at 256K to 45% at 768K) but cannot distinguish two conditions that differ by 10-15 points; at this n, a fair reading only trusts differences that are large AND consistent across buckets, or confirms with a CI-aware test rather than eyeballing point estimates. The chunked conditions (Isolate, Targeted summary) cut the PEAK context any single call has to hold -- to roughly one chunk's worth (a 256K haystack: ~3x smaller; 512K: ~6x; 768K: ~8x) -- while total tokens moved barely change, since the same haystack is still read in full, just split across more, smaller calls. Whether that peak-context reduction also recovers accuracy lost at long context is the empirical question this table answers per bucket: compare each bucket's Isolate/Targeted-summary row against its own Part A row, not against a different bucket's Part A row.

## Deviations from the contract

A session restart interrupted the first attempt to run this grid partway through Stage A (chunk calls). 131 chunk calls (all of 256K's isolate and targeted-summary chunks, plus 11 of 512K's) had already been made and paid for -- real pi calls, real cost, recorded in evidence/grid_budget.json -- before the interruption, but this script's own checkpoint file (evidence/part_b/grid_checkpoint.json) had fallen behind and only reflected 11 of them. Rather than re-running (and re-paying for) those 120 calls, they were recovered by re-parsing the raw pi event stream each one had already written to evidence/part_b/raw/*.raw.jsonl -- ledger cost and recovered-record cost matched to the penny for all 131 (see backfill_part_b_checkpoint.py) -- and the run resumed from there. No item was ever charged twice and no completed call was re-run.

## Budget

Target $20.10, hard stop $24.00. Cumulative completed spend across Part A's extension and this grid (shared ledger, evidence/grid_budget.json): $20.2457.
