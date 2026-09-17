# Part A: Context Window Stress Test -- summary

Model: `google/gemini-3.1-flash-lite`
Corpus: 70802 words (~94167 estimated tokens)
Compaction: disabled for this run (`work/part_a/.pi/settings.json`)
Sizes 2x/3x are optional and not part of the default `--sizes`: the full corpus followed by 1 or 2 extra rounds of its own section files, reshuffled, appended as distractor padding (for models whose context window is too large for "full" alone to stress).

| size | est. tokens | input tokens | cached tokens | output tokens | score | wrong/missing Qs | error |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 8k | 7993 | 10842 | 0 | 295 | 2/5 | 2, 3, 4 |  |
| 16k | 16000 | 21140 | 0 | 195 | 3/5 | 3, 4 |  |
| 32k | 31997 | 21248 | 20462 | 1076 | 5/5 |  |  |
| 64k | 63994 | 59652 | 40945 | 1150 | 5/5 |  |  |
| full | 94167 | 159142 | 0 | 1043 | 5/5 |  |  |
| 2x | 188341 | 317611 | 0 | 799 | 5/5 |  |  |
| 3x | 282516 | 164807 | 311273 | 993 | 5/5 |  |  |

**No failure observed: score never dropped below an earlier best, and no call errored.**
