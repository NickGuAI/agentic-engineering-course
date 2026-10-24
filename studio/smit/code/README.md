# Research update implementation

This standard-library Python script turns source-checked article notes into a Markdown report. It enforces the approved source list, date window, required fields, HTTPS links, duplicate-title removal, and a maximum of five updates. It reports when fewer than three qualify rather than padding the result.

The article notes are collected and verified separately; this implementation does not crawl the web or make AI-generated claims. That boundary keeps the output auditable and avoids implying that a deterministic formatter is an autonomous research agent.

From the repository root, run the original seven-day condition:

```bash
python3 studio/smit/code/research_update.py \
  --as-of 2026-09-29 --days 7 \
  --output studio/smit/outputs/code-run-7-days.md
```

Run the comparison with only the lookback changed:

```bash
python3 studio/smit/code/research_update.py \
  --as-of 2026-09-29 --days 30 \
  --output studio/smit/outputs/code-run-30-days.md
```

Input records live in `articles.json`. Add only notes checked against the approved sources, with their publication date, short summary, significance, and direct article URL.
