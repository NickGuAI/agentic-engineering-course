# Run comparison (2026-09-24)

| Run | Condition | Verifier | Items |
|-----|-----------|----------|-------|
| 1 baseline | Anthropic News is the only required source | PASS | 3 |
| 2 changed | OpenAI News added as a required source; page returns HTTP 403 (missing input) | FAIL `coverage_openai.com` | 3 plus a missing-source note |
| 3 corrected | OpenAI's official RSS feed on the same domain used as a fallback | PASS | 5 |

- Run 2 stopped on the missing source instead of filling the gap from memory. The verifier caught the gap through its coverage check.
- Correction: the evidence was a 403 on the HTML page only. The site's own RSS feed served the same posts with dates and descriptions.
- Tradeoff: the OpenAI items in Run 3 come from one-line feed descriptions, not full articles, so they're thinner and marked as vendor claims.
- Process issue: the agent fetched the RSS URL before a human approved it, which the card's restriction didn't allow. The fetch is logged in trace.jsonl, step 7.
- Verifier limits: it checks structure (dates, domains, coverage, length) but not whether claims are faithful to the source. That part was checked by hand.

Reproduce:
    python3 code/verify_digest.py outputs/run1-baseline-research-update-2026-09-24.md --run-date 2026-09-24 --require anthropic.com
    python3 code/verify_digest.py outputs/run2-missing-input-research-update-2026-09-24.md --run-date 2026-09-24 --require anthropic.com openai.com
    python3 code/verify_digest.py outputs/run3-corrected-research-update-2026-09-24.md --run-date 2026-09-24 --require anthropic.com openai.com
