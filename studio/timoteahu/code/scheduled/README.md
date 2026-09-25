# Scheduled research digest (v2)

Rebuild of the first Codex version, which ran as a long-lived loop that slept until the next
run, with source links hardcoded in the prompt.

| v1 (Codex loop) | v2 (this folder) | Why |
|---|---|---|
| Process loops and sleeps | One-shot `run_digest.py`, scheduled by launchd | A sleeping loop dies on reboot/crash and skips runs while the laptop sleeps; launchd runs a missed job on wake |
| Links hardcoded in prompt | `config.json` (sources, fallbacks, window, limits) + `prompt.md` template | Change sources without editing the prompt |
| Web search + any tools | Claude: only `WebFetch`, only on configured domains, `dontAsk` denies the rest | Run 3 fetched an unapproved URL; the harness now enforces the allowlist instead of the prompt |
| Schema-valid = done | Schema, then semantic checks (window, domain, article URL, duplicates, coverage), then **grounding** (each item's verbatim quotes re-fetched and matched on the live page), then `code/verify_digest.py` on the rendered file | Schema only proves shape; grounding catches invented claims, the gap noted in `run-comparison.md` |
| Single attempt | Failed checks are fed back for a repair attempt (`agent.max_attempts`) | Most failures (wrong date, index URL) are fixable |
| Missing source → ? | Agent reports `failed` per source; runner publishes with a "Missing sources" note and exits 2 | Honest stop instead of filling from memory |
| No record | `outputs/scheduled/<date>/{digest.json, research-update-<date>.md, checks.json}`, one line per run in `runs.jsonl` (status, attempts, cost); raw agent output in gitignored `work/` | Auditable without committing session logs |
| — | Lock file, skip-if-already-passed, `--force`, budget cap, timeout, atomic writes | Safe to trigger twice |

Failed digests are written as `research-update-<date>.REJECTED.md` so nobody reads them by mistake.

## Use

```bash
cd studio/timoteahu/code/scheduled
python3 -m unittest -v test_run_digest            # offline, no API calls
python3 run_digest.py --dry-run                   # print prompt + claude command, call nothing
python3 run_digest.py --agent fixture --fixture fixtures/sample_digest.json \
    --run-date 2026-09-24 --skip-grounding --out-dir /tmp/digest-demo   # offline end-to-end
python3 run_digest.py --agent claude              # live run (real API usage)
bash schedule/install_launchd.sh install claude   # weekly, Mondays 09:00
bash schedule/install_launchd.sh uninstall
```

Exit codes: 0 pass, 1 fail, 2 incomplete (required source unreadable), 3 already running.

## Limits

- Grounding proves quoted text is on the page, not that the summary is faithful to it. Summaries still get a human read.
- Pages that block scripted fetches (openai.com returned 403) are marked unverifiable (warning), not failed; set `grounding.fail_on_unverifiable` to make them fail.
- The Codex adapter (`--agent codex`) is untested here (Codex not installed) and cannot restrict fetch domains, so only the post-hoc domain and grounding checks apply on that path.
