# Studio 1 research agent

A local AI-news digest for **jamieYe0317**, using the existing Codex/ChatGPT login. Python collects publisher evidence and checks the output. Codex summarizes the evidence in one batch; the harness controls requests, retries, files, and completion checks.

The sources are OpenAI News, Anthropic News, and Anthropic Engineering. The normal window is seven calendar dates including the run date in America/New_York. Up to five distinct updates are included. Failed source access is reported explicitly.

## Open the local browser interface

From the repository root:

```bash
cd "studio/studio-01/submission/jamieYe0317"
python3 code/server.py --team jamieYe0317 --port 8765
```

Open **http://127.0.0.1:8765**. The page shows saved digests, source coverage, verification, token measurements, and run history. **Run research** starts a live run using your existing Codex login. **Offline demo** exercises the fixed synthetic fixture with no LLM usage; its fixture window and item count are independent of the live controls.

The server listens only on this computer and allows one browser-initiated job at a time. Closing the browser leaves the server and any active job running. Press **Ctrl+C** in its terminal to stop; an active bounded research job finishes before shutdown. Use another `--port` if 8765 is occupied. No Python packages or frontend build step are needed.

Only the interface and selected saved-run data are served. Local snapshots, credentials, configuration files, raw logs, and arbitrary filesystem paths are not exposed. The UI checks artifacts again when loading them; human source review remains pending.

## Run from the terminal

Python 3.9 or later and an authenticated Codex CLI are required. The project uses the Python standard library; there is no package installation or separate API key requirement. The model adapter currently verifies the installed CLI version `0.154.0-alpha.6.2`; a different version must have its event format and tool restrictions checked before use.

```bash
cd "studio/studio-01/submission/jamieYe0317"
codex login status
python3 code/run.py run --team jamieYe0317
```

If Codex is not signed in, run `codex login` and use your ChatGPT account. Normal live execution needs network access to the publishers and Codex. If an editor's execution sandbox blocks network access, approve the specific live-run command or run it in your terminal; the agent does not disable its own controls.

The CLI prints the run status and output directory. Read `digest.md` for the result, `status.json` for warnings, and `usage.json` for token measurements. A blocked run saves diagnostics without a digest.

The selected model comes from your existing Codex configuration. This project explicitly uses **low reasoning** for short summaries, as recorded in `policy.json`; global Codex settings are not edited. For an intentional per-run choice, use `--model` and `--reasoning`. Do not assume a model or reasoning level is available merely because a string can be supplied.

Other options:

```bash
python3 code/run.py run --team jamieYe0317 --max-items 3
python3 code/run.py run --team jamieYe0317 --run-id my-digest --no-cache
python3 code/run.py verify --team jamieYe0317 --run-id my-digest
```

`--days` accepts 1–7; `--max-items` accepts 1–5. `--as-of` accepts an ISO timestamp with a timezone for a deliberate historical window. It changes the eligibility window; it does not retrieve historical versions of websites.

## Test without model usage

```bash
python3 -m unittest discover -s tests -v
python3 code/run.py demo --team jamieYe0317
```

`demo` creates explicitly labeled synthetic articles and scripted responses. It exercises the same harness, verification, caching, and output path as a live run. Its usage numbers are simulated estimates, not real LLM usage. It records full-input, compact-input, warm-cache, source-failure, and corrected runs with comparisons under `evidence/`.

## Replay a real run

Every research run preserves a local snapshot under ignored `work/snapshots/`. Use the original run ID as the snapshot ID:

```bash
python3 code/run.py replay --team jamieYe0317 --snapshot my-digest --run-id my-replay
python3 code/run.py replay --team jamieYe0317 --snapshot my-digest --run-id failure --fail-source anthropic_news --source-failure-policy stop
python3 code/run.py replay --team jamieYe0317 --snapshot my-digest --run-id corrected --fail-source anthropic_news --source-failure-policy partial
python3 code/run.py compare --team jamieYe0317 --runs my-digest failure corrected
```

Replay preserves the snapshot clock and uses saved publisher content. It is labeled `snapshot_replay`, not live collection. It may use a valid summary cache; a miss can still invoke Codex. `--no-cache` disables summary reads for an explicit cold comparison, but validated results are still saved for a later warm run.

The stop policy represents a conservative initial behavior. Changing it to partial output is the documented policy correction: valid remaining items must pass fresh checks. If no trustworthy items remain, even the corrected policy must stop. A preexisting source outage can already prevent a stop-policy baseline, so inspect source coverage when choosing the changed condition.

For token comparisons, compare a full-text replay using `--evidence full --no-cache` against a compact replay using `--evidence compact --no-cache`, with identical snapshot, clock, model, settings, and final-item set. Both must fit the same application budget. An oversized full-text baseline is recorded as blocked; do not silently increase the live limits. Compare quality against a facts-and-caveats checklist before interpreting the token reduction.

## What the harness enforces

- Source URLs, redirect targets and network addresses are checked before access.
- HTTP attempts, response sizes, actions, model calls and elapsed time are bounded.
- One batch summarization and at most one repair are allowed. Unknown usage prevents another model call.
- Model tools are removed for the summarizer invocation. The adapter also rejects unexpected tool events.
- The model returns known article and evidence IDs. Python supplies publisher titles, dates and URLs.
- Final verification checks the exact digest and manifest. Editing either makes saved verification stale.
- A partial digest must pass the same checks as a complete one. Invalid items cannot bypass verification.
- Source text cannot choose a new policy, credential, tool or output location.

The harness controls this application. It is not a claim that Python itself is an adversarial OS sandbox. Read-only Codex execution is retained as an additional restriction.

| Status | Meaning | Exit code |
|---|---|---:|
| `complete` | Bounded source checks succeeded; valid digest produced | 0 |
| `empty` | Sources were successfully checked but no eligible updates were found | 0 |
| `partial` | Valid items produced, with explicitly limited coverage | 2 |
| `blocked` | No trustworthy result could be finalized | 3 |

An HTTP 403 is an access failure, not proof that the publisher has no news. Automated checks validate provenance and structure; a person still needs to compare summaries with the cited source material.

## Token controls

Initial application input is limited to 8,000 estimated tokens and 48 KiB; repair input to 4,000 estimated tokens and 24 KiB. The cumulative application allowance is 12,000 estimated tokens. Numeric estimates use UTF-8 bytes divided by three, rounded up, and are labeled as estimates everywhere. They are not an exact model tokenizer.

The evidence pool is 6,000 estimated tokens. Five articles normally get 1,200 each. A sparse set can share unused slots so important qualifications do not have to be removed just to fit a per-article target. The final prompt and schema still must pass the shared request limit.

The collector filters dates and duplicates without an LLM. Evidence selection removes irrelevant background while retaining detected qualification paragraphs. Summaries are cached by source-content hash, evidence, prompt/schema versions and model settings. Live runs refetch content before reuse; snapshot replays reuse the saved text. No model call is used to format Markdown.

Codex adds its own context and may generate non-visible reasoning. **These limits are not a hard ceiling on total provider tokens.** `usage.json` records actual reported usage separately. Cached-input and reasoning breakdowns are not counted twice. Missing usage remains unknown, and a timeout may already have consumed tokens. The 40,000 observed-token threshold blocks later calls after an overrun; it cannot retroactively cap the initial call.

## Files and submission

- `ENGINEERING_PLAN.md`: original design, with implementation status notes.
- `delegation-card.md`: the four-field assignment contract.
- `policy.json`: explicit limits and summarization reasoning setting.
- `code/`, `prompts/`, `tests/`: implementation and tests.
- `outputs/`: digests, manifests, sanitized traces, checks and usage.
- `evidence/`: machine-generated comparisons and verification evidence.
- `work/`: ignored source snapshots, summary cache and transient scratch files.

No downloaded article bodies, raw model logs, authentication files or API keys belong in commits. The source manifests keep IDs and hashes rather than downloaded paragraphs. A hash alone cannot reconstruct a disappeared webpage; replay requires the locally retained snapshots.

Jamie must personally write `explanation-jamieYe0317.md`. This project does not generate that explanation, submit to CourseWorks, create an automated schedule, or publish to the public course repository.
