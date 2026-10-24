# Run 02 — missing-input experiment

- **Type:** simulated condition change for Studio01; no new live source fetch.
- **Unchanged inputs:** Run 01's reporting interval, card, and Anthropic observations.
- **Changed condition:** remove all OpenAI retrieval evidence, simulating an unavailable source.
- **Observed consequence:** OpenAI coverage becomes unavailable; Anthropic still has two date-only candidates and zero timestamp-verified candidates.
- **Correction:** report partial coverage and hold the issue. Do not replace the missing source with memory, older news, or fabricated timestamps.
- **Comparison:** Run 01 reached both publishers but could not establish freshness. Run 02 has both a missing-source condition and unresolved freshness. Both responsibly admit zero stories, for different recorded reasons.
- **Limitation:** this experiment documents the decision using retained evidence; it is not an automated fetcher test or evidence of a real OpenAI outage.
