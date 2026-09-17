# Newsletter reproduction

Python 3.9+; standard library only. From the repository root:

```bash
python3 studio/yirangong88/code/newsletter.py --input studio/yirangong88/outputs/evidence-run-03.json --name replay-03
python3 -B studio/yirangong88/code/test_newsletter.py
```

The renderer computes the previous calendar date in America/New_York, filters publisher date labels, validates original-source domains and editorial fields, and writes the issue plus a selection trace. Existing outputs are protected against overwrite.

This code reproduces a manually researched issue; it does not fetch live news, validate factual claims automatically, or schedule delivery. For a new issue, retrieve both official indexes and matching original posts, record a fresh execution time, update the evidence JSON and two questions, and choose a new output name. Do not reuse this snapshot as fresh news.
