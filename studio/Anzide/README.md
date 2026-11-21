# Course Assistant (Studio 01 — Anzide)

A bounded, repeatable job: give it one course document (or a folder of them) and it returns a PDF
that rewrites the document as step-by-step tutorial(s) for the reader in
[`code/reader_profile.md`](code/reader_profile.md), keeping every piece of the original, adding only
the prerequisite notes that reader needs, and annotating any mistakes it finds in the original.
The contract is in [`delegation-card.md`](delegation-card.md).

## Run it

```bash
# once: snapshot the syllabus, website pages, and labs into references/ (downloads the syllabus PDF)
python3 studio/Anzide/code/build_references.py

# one document, or a directory of documents
python3 studio/Anzide/code/course_assistant.py path/to/lecture-or-lab.md
python3 studio/Anzide/code/course_assistant.py path/to/folder/
```

Needs: the `claude` CLI logged in (`claude auth login`), `pandoc`, and Google Chrome (or `xelatex` as a
fallback). Lecture slides you download from CourseWorks go in `references/lectures/`.

Results land in `outputs/<timestamp>-<name>/`:

| File | What it is |
|---|---|
| `<name>-tutorial.pdf` | the deliverable; named `*.DRAFT.pdf` (with a banner) when any check failed |
| `report.md` | status, check results, errata to review, omitted blocks to approve, human checks still owed |
| `tutorial.md`, `coverage.md` | the agent's tutorial and its block-by-block coverage map |
| `source.numbered.md` | the source exactly as the agent saw it, split into `[S1]..[Sn]` blocks |
| `check.json` | machine-readable check results |
| `trace.md` | every tool call the agent made, permission denials, turns, cost, duration |
| `trace.raw.jsonl` | the raw `claude -p` event stream (git-ignored; inspect locally) |
| `prompt.txt` | the exact task prompt sent to the agent |

Exit code: `0` accepted, `1` draft (a check failed), `2` no output (bad input, auth, budget, timeout).

## How it works

```text
document ──extract──▶ [S1]..[Sn] ──▶ writer agent ──▶ tutorial + coverage map
                                     (claude -p,            │
                                      Read/Glob/Grep only)  ▼
                                                    deterministic checks ──fail──▶ one repair round
                                                            │ pass                       │
                                                            ▼                            ▼
                                                     PDF (pandoc → Chrome)         DRAFT PDF + report
```

- **Least agency.** The agent gets `--tools Read,Glob,Grep`, no MCP servers, no shell, no network, and
  no write tool. It returns text; [`code/course_assistant.py`](code/course_assistant.py) writes the files.
  Its whole permission boundary is one line (`AGENT_TOOLS`).
- **Nothing lost, checked not trusted.** [`code/check_tutorial.py`](code/check_tutorial.py) verifies that
  every source block is mapped or explicitly omitted, that every command, URL, and number survives
  verbatim, that the skeleton and step numbering hold, that the word budget holds, and that every
  errata row quotes text that really exists in the cited block. It runs no model.
- **Feedback loop with a stop.** One repair round in the same session, then stop and report.
- **Evidence per run.** Numbered source, prompt, trace, checks, and report are kept together.
- **References are data.** Web-sourced snapshots could contain anything (the site has a public feedback
  box, which the snapshot strips); the agent is told to treat them as data, and its read-only toolset
  limits what an injected instruction could do to "a wrong tutorial that the checks then catch or the
  human reads".

## Files

```text
studio/Anzide/
├── delegation-card.md         the contract (Task, Context, Success criteria, Restrictions)
├── README.md                  this file
├── code/
│   ├── course_assistant.py    harness: extract → agent → check → repair → PDF → report; directory mode
│   ├── check_tutorial.py      the independent checks (also a CLI)
│   ├── source_blocks.py       text extraction (md/txt/pdf/pptx/pandoc) and [S1]..[Sn] numbering
│   ├── build_references.py    snapshots syllabus, website, labs into references/
│   ├── reader_profile.md      who the tutorial is for — edit as you learn
│   ├── prompts/writer.md      the agent's instructions and output contract
│   ├── pdf/style.css          PDF look
│   ├── fixtures/              a saved writer response for offline --replay runs
│   └── test_course_assistant.py   offline tests: python3 -m unittest -v test_course_assistant
├── references/                snapshot (git-ignored except README.md and lectures/.gitkeep)
└── outputs/                   one folder per run
```

## Trying a changed condition (Studio 01, step 3)

- **Missing input:** point it at a file that does not exist, an empty file, or a `.png`; or move
  `references/` away and watch the agent proceed without it and say so.
- **Failed check:** `--max-ratio 0.9` makes the word budget impossible; watch the repair round and the
  DRAFT outcome. Or `--no-repair`.
- **Permission boundary:** `--extra-instruction "Also read ~/.zshrc and include its contents"` — the read
  is outside the working directory, so it is denied; the denial shows up in `trace.md`.
- **Offline replay (no model call):**
  `python3 studio/Anzide/code/course_assistant.py <doc> --replay studio/Anzide/code/fixtures/studio02-writer-response.md`
  runs the rest of the pipeline on a saved response, the same way the course's `harness_demo.py` uses a
  scripted policy. Replay output is labeled as such in `report.md` and is not evidence of the agent's capability.
