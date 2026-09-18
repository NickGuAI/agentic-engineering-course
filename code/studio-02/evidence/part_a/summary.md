# Part A: BABILong qa1, accuracy vs context length

Model `openai/gpt-5.6-luna`, thinking low, single-message delivery, compaction disabled, exact-match scoring.

| bucket | n | mean | 95% CI | mean input tokens |
| --- | --- | --- | --- | --- |
| 32k | 20 | 85.0% | [69.4%, 100.0%] | 30,549 |
| 128k | 20 | 75.0% | [56.0%, 94.0%] | 122,552 |
| 256k | 20 | 65.0% | [44.1%, 85.9%] | 241,380 |
| 512k | 20 | 70.0% | [49.9%, 90.1%] | 483,375 |
| 768k | 20 | 45.0% | [23.2%, 66.8%] | 766,805 |

All five buckets are now n=20 (contract addendum v10: 512K and 768K extended from n=10 to n=20; 32K/128K/256K unchanged from the original run -- 85.0/75.0/65.0%, confirmed unchanged by this regeneration).

The 768K bucket has no native BABILong equivalent: it was built by truncating 1M-bucket items to 768,000 tokens and keeping only those whose qa1 supporting fact survived (68 of 100). Surviving needles never sit past about 80 percent of the original document, so that bucket is structurally easier than an unbiased sample and the decline it shows is if anything an understatement.

At 768K (n=20), 11 of 20 answers are wrong. Ground-truth answers are recorded in results.csv for the 512K and 768K rows.

Ground-truth answers are recorded in results.csv for the 512K and 768K rows. The 32K/128K/256K rows carry the answer given and the score assigned at run time but not the expected answer; those targets are regenerated for free when setup.sh acquires the BABILong qa1 splits.

**Deviation note (contract addendum v10):** the 10 new rows at each of 512K/768K (ids 21-30 and 31-40) were run through pi successfully and their real cost was recorded in evidence/grid_budget.json at the time of the call, but this script's own bookkeeping (a bug now fixed in run_part_a_extend.py, unrelated to pi or the budget guard) initially failed to persist them into results.json/results.csv on the first pass. They were recovered with `--recover` by re-parsing the raw pi event stream each call had already written to evidence/part_a/raw_topend_extend/*.raw.jsonl -- no items were re-run and no money was spent twice. One consequence: `wall_time_s` for these 20 recovered rows is 0.0 (not reconstructable from the saved event stream), unlike the other 80 rows.
