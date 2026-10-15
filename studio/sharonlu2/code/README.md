# Research Update

## Requirements and setup

The Python program uses only the standard library, so there are no Python packages to install and no separate virtual environment is needed. Use the shared course Python installation (`python3`). The report summarizer also requires the Codex CLI to be installed and signed in; the script does not read or store API keys.

From the repository root, run:

```bash
python3 studio/sharonlu2/code/research_update.py --team sharonlu2
```

By default, the program checks Anthropic News, Anthropic Engineering, and OpenAI News. To check custom sites instead, repeat `--source`:

```bash
python3 studio/sharonlu2/code/research_update.py --team sharonlu2 \
  --source https://example.org/news \
  --source https://example.net/research
```

Each model invocation writes raw evidence outside the repository under `~/.local/state/research-update/raw-logs/` by default. Override that location with `--raw-log-dir`; the program rejects paths inside the repository. For example:

```bash
python3 studio/sharonlu2/code/research_update.py --team sharonlu2 \
  --raw-log-dir /private/tmp/research-update-raw-logs
```

Each invocation gets its own directory, named by the log identifier. It contains the exact prompt (`prompt.txt`), final response (`response.txt`), Codex JSONL stdout events (`events.jsonl`), stderr (`stderr.log`), and command settings and exit status (`invocation.json`). Article text is included in the prompt, so raw logs can contain full retrieved article content. The structured run record links to the invocation by `model.log_id`. When no articles qualify, it records `invoked: false` and `not_called_reason: no_eligible_articles`.

If a custom URL is malformed or DNS confirms its host does not exist, the program prints a notice and checks the three default sources. An HTTP 404/410 means the requested page is unavailable; it is recorded as a source failure and does not establish that the website itself is gone. Other retrieval errors are recorded as failed or partial checks. `--timeout` controls each web request, and `--model-timeout` bounds the model step.

The model defaults to `gpt-6-luna`, matching the existing run metadata. Override it with `--model <name>` or `RESEARCH_UPDATE_MODEL=<name>`. The Codex executable defaults to `codex`; use `--codex-binary` if it is installed under another command name or path.

## Retrieval and reporting

For each source, the program fetches the source page, follows a discovered RSS/Atom feed when one is available, and otherwise collects same-site article links from the page HTML. It then fetches candidate article pages and reads publication dates from page metadata, JSON-LD, `<time>` elements, or feed publication fields. Feed update timestamps are not used as publication dates. The current date window is the previous seven complete Eastern Time calendar dates, excluding the run date. Missing dates and dates outside that window are skipped.

The program sorts eligible stories newest first and keeps at most ten. It sends the retrieved article text to `codex exec --json` in one request and asks for concise JSON summaries grounded only in that text. The invocation is ephemeral, read-only, and uses a temporary working directory. If retrieval or summarization fails, the report says so and is marked incomplete; a failed source is never described as having no news. An HTTP 404 or 410 is recorded as an unavailable page, not evidence that the host does not exist. Only malformed custom URLs or a DNS response indicating a nonexistent host trigger fallback to default sources.

Each run writes a uniquely named `.md` report and `.json` run record under `studio/sharonlu2/outputs/`. The record contains the source outcomes, candidate and eligible counts, date window, model status and raw log identifier, article metadata, and report filename. Existing reports and run records are preserved.

## Limitations

Some sites render story listings only in JavaScript or use page layouts whose publication dates are not exposed in common metadata. Those stories may be missed; the program skips articles when it cannot verify a date. The program does not crawl arbitrary site paths, and the model can still produce an imperfect summary even when prompted to stay within retrieved text. A successful run requires network access to the configured sites and an available, authenticated Codex CLI. This implementation has not made live requests or model calls.
