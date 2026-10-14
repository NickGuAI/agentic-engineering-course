# official-Auralin — Research Update

A local Codex agent that checks Anthropic News, Anthropic Engineering, and OpenAI
News on weekdays at 9:00 AM **America/New_York** (Eastern, including daylight saving).
Its Python harness fetches first-party evidence, keeps state, validates summaries,
and writes a cited Markdown digest plus JSONL execution records. Codex performs
the language-model work through the student's existing ChatGPT sign-in. Execution
and stored state are local; model inference is a network service.

## Run

Requirements: macOS or Linux, Python 3.10+, curl, and a recent signed-in Codex CLI
supporting `exec --ignore-user-config --ignore-rules --ephemeral --output-schema`.
There are no Python packages to install. No separate API key is needed.

From this folder:

```sh
codex login status
python3 code/run.py
```

Read each day's report at `outputs/live/reports/YYYY-MM-DD.md`. Filenames use
America/New_York dates. Different days have separate files; same-day runs merge
summaries by article URL, and unchanged runs leave the report untouched. A day
with no published summaries gets a short empty-day report. There is no latest.md.

Coverage warnings, source status, retrieval errors, and truncation details go to
`outputs/live/runs/<run_id>/coverage.log`, not the reading report. Raw data and
execution traces remain in that run directory. The final JSON gives the dated
`digest` path, the `log` path, article count,
`failed_sources`, `limited_sources`, and whether there is something to report.
Exit codes: **0** completed, **2** completed with failed source coverage, **1** failed.
The first run can take several minutes. The CLI uses its built-in default model
and existing sign-in while ignoring user config and execpolicy rules; it requests
a structured response in a read-only sandbox. It is instructed not to use tools.

The desktop scheduled task follows `code/research-update.md` and runs this same
command in the local checkout. Keep the Mac awake, connected, and the desktop app
running. The host timezone was verified as America/New_York. Review the schedule
if you change the Mac's timezone; do not assume a powered-off machine will run it.
Network/CLI permission failures are reported; the agent does not disable sandboxing.

## Layout

```text
official-Auralin/
├── delegation-card.md         # The course template's exact four fields
├── AGENTS.md                  # Folder and scheduled-run instructions
├── README.md
├── code/
│   ├── run.py                 # Complete local agent invocation
│   ├── agent.py               # Collection, validation, publication, state
│   ├── sources.json           # Three approved discovery sources
│   ├── summarize.md           # Model prompt
│   ├── summary-schema.json    # Structured model response
│   ├── research-update.md     # Scheduled task workflow
│   └── tests/                 # Offline tests and synthetic HTML/RSS fixtures
└── outputs/
    ├── verification/          # Reviewed shareable evidence
    └── live/                  # Ignored local runtime artifacts
        ├── reports/          # YYYY-MM-DD.md daily reading files
        └── runs/             # Run snapshots, coverage.log, and execution traces
```

Each student must personally create `explanation-<username>.md` in this folder.
The course prohibits AI-generated text for that explanation; it is intentionally
not generated here. See the shared Studio README for the required topics.

## Evidence and failure handling

- Discovery starts only at the two Anthropic indexes and OpenAI News's official
  RSS feed. Links must stay on the approved publisher hosts. Featured articles
  and feed entries can legitimately live outside `/news/` or `/index/`.
- First publication establishes a baseline: up to five newest discoverable
  articles per source are summarized. Older initial index entries are recorded
  as baseline only, without being labeled as read or summarized. Failed selected
  articles remain eligible for retry.
- Later runs process up to ten unseen URLs per source and recheck the five newest
  indexed articles already summarized. Other unseen items are deferred. Old edits
  outside that recheck window and articles removed from an index before a run can
  be missed. The Anthropic collector reads the rendered index, not its full archive
  or client-side pagination. Coverage is recorded honestly, not claimed exhaustive.
- Hashes track normalized article text; model judgment distinguishes meaningful
  edits from cosmetic ones. Dates come from article metadata, its visible date,
  or the source index. Missing/future dates are reported and deferred.
- Each fetch has a 25-second timeout, one retry, and an 8 MB response limit. The
  collector does not follow redirects. The model has an eight-minute timeout.
  Model evidence is capped at the first 60,000 characters of each article, with
  truncation recorded in coverage.log. Full article text is kept only in ignored local artifacts.
- OpenAI article pages returned HTTP 403 during verification. Its official RSS
  descriptions remain available and are used as a fallback recorded in coverage.log.
  These entries receive short, limited summaries. If neither article nor useful
  feed description is available, that article fails and is retried next time.
- Publication requires exactly one entry per candidate URL and a short verbatim
  evidence excerpt. This checks traceability, not complete semantic truth; review
  the summaries and their sources. Facts are attributed to the companies; “why it
  matters” is labeled analysis. No fixture is presented as a real model result.
- The harness writes a digest before advancing state. File locks prevent parallel
  runs, and revisions reject stale or duplicate publication. A failed source does
  not discard successful ones. Unchanged runs do not invoke the model or notify.
  Repeated RSS coverage warnings alone do not trigger a notification.

## Inspect and test

See [verification evidence](outputs/verification/README.md) for measured live
results, the OpenAI fallback recovery, and the duplicate-free repeat run. The
weekday schedule is active in the desktop app as `auralin-research-update`.

```sh
python3 -m unittest discover -s code/tests -v
python3 code/agent.py collect
```

`collect` only produces a packet; it does not advance state. For manual review,
create a JSON array matching the `articles` field in `summary-schema.json`, then:

```sh
python3 code/agent.py publish RUN_ID outputs/live/runs/RUN_ID/draft.json
```

Each live run stores `packet.json`, source snapshots, `trace.jsonl`, and (when the
model runs) `model-input.txt`, `model-output.json`, `model-trace.jsonl`, and stderr.
Successful publication adds `summaries.json`, a per-run `digest.md` snapshot,
`coverage.log`, and `result.json`, plus the dated reading file under `reports/`.
Original verification snapshots may still contain the old report format; they
are historical evidence, not the current reading files. To rebuild dated reports
and coverage logs from completed runs without fetching or changing seen state:

```sh
python3 code/agent.py rebuild-reports
```

Do not commit authentication files, raw pages, or full model traces. Reviewed
digest excerpts and sanitized harness records belong in `outputs/verification/`.

## Course workflow

This work is on `official-auralin-research-update`, based on updated `main` at
`474fbf7`. Keep changes in this team folder. Once each student has written their
explanation, commit the folder and submit a PR targeting the course repository's
`main`. After a confirmed merge, remove only the merged working branches. Official
grading and deadlines remain in CourseWorks.

References: [course workspace instructions](../README.md),
[Codex non-interactive execution](https://learn.chatgpt.com/docs/non-interactive-mode),
[scheduled tasks](https://learn.chatgpt.com/docs/automations).
