# Part B: Isolate and Compress -- summary

Model: `google/gemini-3.1-flash-lite`

| method | score | tokens (final scored call) | cost |
| --- | --- | --- | --- |
| Part A best (32k) | 5/5 | 21248 | $0.0074 |
| Isolate (lead, from findings) | 5/5 | 1231 | $0.0342 |
| Compress: summary artifact | 5/5 | 910 (summary ~161 tok) | $0.0013 |
| Compress: pi auto-compaction | 4/5 | 17275 (1 compaction(s) fired) | $0.0300 |

Isolate: one pi sub-agent per corpus section returns short findings only; a lead pi process answers the five questions from the concatenated findings alone (no raw corpus text).

Compress (summary artifact): a 161-token briefing was written from Part A's best run (32k, 5/5), then the five questions were re-asked with only that briefing as context.

Compress (pi's own compaction): reserveTokens was set to 998576 (context window 1048576) so auto-compaction should fire around 50000 tokens; 1 compaction(s) fired while the agent read the corpus section files one by one via the read tool (actual tokensBefore: 83909; pi only checks the threshold between tool batches, so the observed value can run higher than the configured threshold if the agent reads several files back to back before pi's next check).
