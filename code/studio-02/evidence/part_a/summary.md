# Part A: BABILong qa1, accuracy vs context length

Model `openai/gpt-5.6-luna`, thinking low, single-message delivery, compaction disabled, exact-match scoring.

| bucket | n | mean | 95% CI | mean input tokens |
| --- | --- | --- | --- | --- |
| 32k | 20 | 85.0% | [69.4%, 100.0%] | 30,549 |
| 128k | 20 | 75.0% | [56.0%, 94.0%] | 122,552 |
| 256k | 20 | 65.0% | [44.1%, 85.9%] | 241,380 |
| 512k | 10 | 70.0% | [41.6%, 98.4%] | 481,833 |
| 768k | 10 | 40.0% | [9.6%, 70.4%] | 766,944 |

32k/128k/256k are n=20; 512k/768k are n=10.

The 768K bucket has no native BABILong equivalent: it was built by truncating 1M-bucket items to 768,000 tokens and
keeping only those whose qa1 supporting fact survived (68 of 100). Surviving needles never sit past about 80 percent
of the original document, so that bucket is structurally easier than an unbiased sample and the decline it shows is
if anything an understatement.

At 768K, four of the six wrong answers name the wrong room; the other two ("London", "Fairy Knowe") are places from
the PG-19 novels used as filler, not BABILong locations at all -- the model answering the haystack instead of the task.
