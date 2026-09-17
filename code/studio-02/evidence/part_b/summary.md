# Part B: Isolate and Compress -- summary

Model: `openai/gpt-5.6-luna`, thinking `low`, 8 chunks per item.

## Data check: how many times is the target person mentioned?

37/68 items have the target person moving MORE THAN ONCE (regex hits for 'PERSON moved/went/travelled/... (back) to the ROOM'); the remaining 31 have exactly one mention, 0 had no literal regex hit. Across all 68 items with at least one hit, the LAST mention's room matches the gold target in EVERY case (68/68, 0 disagreements) -- when a person moves more than once, only their most recent move is ever the right answer. Every demonstration below is therefore told explicitly to take the LAST reported location, never the first.

Mention-count distribution across the 68 items checked: {'1': 31, '2': 16, '3': 12, '4': 6, '5': 2, '6': 1} (key = number of movement-sentence matches for that item's person). 37 items have more than one; 0 of those disagree with taking the LAST one.

## Per-item results (same ids Part A scored, chosen by lowest id, not by correctness)

| id (bucket) | condition | verdict | total tokens | PEAK single-call context | cost |
| --- | --- | --- | --- | --- | --- |
| 11 (768k) | Part A (single call) | correct | 766814 | 766814 | $0.3834 |
| 12 (768k) | Part A (single call) | correct | 766266 | 766266 | $0.3833 |
| 13 (768k) | Part A (single call) | WRONG | 766569 | 766569 | $0.3838 |
| 11 (768k) | Isolate | correct | 771044 | 98165 | $0.1929 |
| 12 (768k) | Isolate | correct | 770659 | 98492 | $0.1929 |
| 13 (768k) | Isolate | correct | 771084 | 98257 | $0.1931 |
| 11 (768k) | Compress: targeted summary | correct | 774572 | 98179 | $0.1956 |
| 12 (768k) | Compress: targeted summary | WRONG | 773905 | 98506 | $0.1955 |
| 13 (768k) | Compress: targeted summary | WRONG | 774364 | 98271 | $0.1956 |
| 41 (256k) | Part A (single call) | correct | 246894 | 246894 | $0.0618 |
| 42 (256k) | Part A (single call) | WRONG | 245047 | 245047 | $0.0617 |
| 41 (256k) | Compress: pi auto-compaction | WRONG | 577081 | 113217 | $0.0401 (1 compaction(s)) |
| 42 (256k) | Compress: pi auto-compaction | WRONG | 461640 | 102146 | $0.0335 (1 compaction(s)) |

## Condition summary

Part A on these same 3 (768K) ids: 2/3 correct.
Isolate on the same 3 ids: 3/3 correct.
Compress (targeted summary) on the same 3 ids: 1/3 correct.

Part A on these same 2 (256K) ids: 1/2 correct.
Compress (pi auto-compaction) on the same 2 ids: 0/2 correct.

**Isolate** RECOVERED accuracy Part A lost on these ids (2/3 -> 3/3).
**Compress (targeted summary)** did WORSE than Part A on these ids (2/3 -> 1/3).
**Compress (pi auto-compaction)** did WORSE than Part A on these ids (1/2 -> 0/2).

## The actual lesson: peak context, not total tokens

Part A's single call for a 768K item had to hold the ENTIRE haystack in context at once: peak context = total input tokens = ~767,000. Isolate's peak single-call context across these 3 items maxes out at 98,492 tokens (one ~1/8-sized chunk) -- roughly a 7.8x reduction in what any ONE call had to attend to. Compress (targeted summary)'s peak is 98,506 for the same reason: its per-chunk calls still each read one full chunk to summarize it. Compress (auto-compaction)'s peak across the 256K items is 113,217 tokens, bounded near its configured threshold regardless of the 256K item size.

Meanwhile TOTAL tokens barely move: isolate's 3 items sum to 2,312,787 tokens across all 3x8+3 calls, against 2,299,649 for Part A's 3 single calls on the same ids -- the same haystack still gets read in full, just split across calls instead of handed to one. Isolation and targeted summarization do not save tokens; they cap what any single call has to hold in context at once.

## Budget

Target $1.70, hard stop $2.00. Actual total spend: $1.2391 across 56 pi calls.
