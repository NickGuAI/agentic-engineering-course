# Research Update job

This folder contains a bounded, repeatable Studio01 job that reads the official
Anthropic News, Anthropic Engineering, and OpenAI News landing pages, follows a
small number of article links, and creates a Markdown digest for a graduate
student studying agentic engineering.

The implementation uses deterministic HTML metadata/text extraction and a small
keyword relevance ranking. Summaries are source-derived excerpts or descriptions,
not generated claims. “Why it matters” is a deterministic relevance note based on
the observed title and description.

## Requirements and installation

- Python 3.10 or newer
- Internet access to the three public sources

No package installation, external LLM API, API key, or other credential is
required. The program uses only the Python standard library.

## Run

From the repository root:

```bash
python studio/tcyxox/code/research_update.py
```

Run the offline unit tests with:

```bash
python -m unittest discover -s studio/tcyxox/code -p "test_*.py" -v
```

The job deliberately limits itself to six article fetches per source and six
selected digest items by default. Use `--help` to see the bounded configuration
options. The `--source-url SOURCE_ID=URL` option exists for the later controlled
failure experiment; it is not used in the baseline run.

## Outputs and evidence

Every execution creates a new unique UTC-timestamped directory under
`studio/tcyxox/outputs/`; existing run directories are never reused. Each run
contains:

- `digest.md`: the human-readable research digest
- `evidence.json`: configured and attempted sources, per-source outcomes and
  counts, selected items, warnings/errors, verification checks, output path, and
  final status
- `events.jsonl`: timestamped event-level execution log

Statuses mean:

- `SUCCESS`: every configured source produced processable items, at least one
  item was selected, and all required internal verification checks passed.
- `DEGRADED`: at least one source failed, but verified output could still be
  produced from another successful source. The failed source remains explicit in
  the evidence. The process exits with code 2.
- `FAILED`: no reliable digest could be produced or a required verification
  check failed. The process exits with code 1.

An article-level failure is recorded as a warning. A source is successful only if
its landing page yields at least one article that can be fetched and processed.
The job never treats missing dates or inaccessible content as known information.
