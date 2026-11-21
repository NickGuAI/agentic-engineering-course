# Trace — lecture 01 (2026-09-11)

Step 1 only. Stopped at the approval gate, as instructed.

| # | Action | Result |
|---|--------|--------|
| 1 | Read `code/PROMPT.md` | Job spec loaded; `{{n}}` not supplied by user, inferred `01` (only deck present: `course-materials/lecture-01.pdf`) |
| 2 | Read `delegation-card.md`, `code/.claude/settings.json`, `code/scripts/check_summary.py` | Confirmed gates, restrictions, and relative-path layout (run root = `outputs/`) |
| 3 | `pdfinfo course-materials/lecture-01.pdf` | 41 pages, 612x792pt, "Introduction CS4731 Fall 26", Shree K. Nayar, created 2026-09-07 |
| 4 | `pdftotext -layout` -> scratchpad | 38,190 chars extracted; all 41 pages readable, no unreadable/empty-text failures that hid slide titles |
| 5 | Read all 41 pages of extracted text | Deck is 2 slides per PDF page (slides 1-82) |
| 6 | Wrote `summaries/01-keywords.json` | 8 core + 55 minor keywords with page numbers; JSON validated |
| 7 | Wrote this run record | Pending: steps 2-4, which require `approved/01-keywords.json` |

## Decisions worth reviewing
- **Page numbering = PDF page number** (1-41), not the printed slide number (1-82).
  E.g. "Vision Deals with Images" is slide 5 but PDF page 3 -> tagged `[p.3]`.
- **Lecture number inferred**, not given: `01`.
- No web access used. No files under `course-materials/`, `approved/`, or `scripts/`
  were modified. No keys or personal data written.

## Not yet done
- Step 2 (`summaries/01.md`) — blocked on approval gate: `approved/01-keywords.json` does not exist.
- Step 3 (`summaries/01-teachback.md`) — follows step 2.
- Step 4 (`python3 scripts/check_summary.py 01`) — follows step 3; output to be appended here and to `spot-check.md`.

---

# Trace — lecture 01, session 2 (2026-09-11)

Step 1 re-run. **The source PDF was replaced between session 1 and session 2.**
Stopped again at the approval gate.

| # | Action | Result |
|---|--------|--------|
| 1 | Read `code/PROMPT.md` | Job spec loaded; `{{n}}` again not supplied, inferred `01` (confirmed by user) |
| 2 | Read `delegation-card.md`, `code/.claude/settings.json`, `code/scripts/check_summary.py`, session-1 run record | Gates and prior state understood |
| 3 | `ls approved/` | Directory exists but is **empty** → approval gate still closed; steps 2-4 blocked |
| 4 | `pdfinfo course-materials/lecture-01.pdf` | **Different deck than session 1**: "COMS W4701: Artificial Intelligence — Lecture 3: Uninformed Search", Tony Dear, 22 pages, 960x540pt, created 2025-01-29. md5 `8d5a8f9d9d445ff2ea4e203e0197dfc4`. File mtime 22:55, after session 1's keyword extraction at 17:47. |
| 5 | `pdftotext -layout` -> scratchpad | 12,105 chars; all 22 pages readable, no empty or unreadable pages |
| 6 | Per-page first-line extraction | One slide per PDF page, pages 1-22; slide number == PDF page number for this deck |
| 7 | Asked user: overwrite stale `summaries/01-keywords.json`? confirm `{{n}}`? | User approved overwrite (no backup) and confirmed `{{n}}` = `01` |
| 8 | Wrote `summaries/01-keywords.json` | 8 core + 31 minor keywords with page numbers; JSON validated |
| 9 | Appended this run record | Pending: steps 2-4, which require `approved/01-keywords.json` |

## Decisions worth reviewing
- **Stale output overwritten with user consent.** The session-1 keyword list described
  the Computer Vision deck (CS4731, 41 pages) that no longer exists at
  `course-materials/lecture-01.pdf`. None of its 63 keywords appear in the current deck.
  The old list was replaced, not backed up, per the user's choice.
- **Lecture number mismatch, not resolved in the filename.** The deck's own title is
  "Lecture 3", but the input path is filename-driven (`lecture-01.pdf`) and no
  `lecture-03.pdf` exists. User confirmed running as `01`.
- **Page numbering = PDF page number** (1-22), which equals the slide number here.
- **`Frontier` attributed to p.9**, where the term is introduced ("Leaf nodes lie in a
  frontier data structure"), not p.12, where it gets a dedicated slide.
- **Iterative Deepening Search classed as minor, not core**, because the deck's own
  "Today" agenda (p.2) lists the algorithms as "DFS, BFS, UCS" and omits IDS. This keeps
  core at the 8-keyword cap.
- No web access used. No files under `course-materials/`, `approved/`, or `scripts/`
  were modified. No keys or personal data written.

## Not yet done
- Step 2 (`summaries/01.md`) — blocked on approval gate: `approved/01-keywords.json` does not exist.
- Step 3 (`summaries/01-teachback.md`) — follows step 2.
- Step 4 (`python3 scripts/check_summary.py 01`) — follows step 3.

---

# Trace — lecture 01, session 3 (2026-09-11)

Steps 2-4, run after the human opened the approval gate.

| # | Action | Result |
|---|--------|--------|
| 1 | `ls approved/` (1st attempt, prior turn) | Empty — gate closed. Stopped and reported; did not write `summaries/01.md`. The user's `cp` had failed on a wrong relative path (`outputs/summaries/...` from a cwd already inside `outputs/`). |
| 2 | `ls approved/` (2nd attempt) | `approved/01-keywords.json` present → **GATE_OPEN** |
| 3 | `diff approved/01-keywords.json summaries/01-keywords.json` | Identical to the step-1 draft; human made no edits. 8 core / 31 minor. |
| 4 | Wrote `summaries/01.md` | Core Concepts (8 core subsections + 1 supporting-algorithms subsection covering depth-limited / iterative deepening) plus Lecture Flow. Every non-flow line carries `[p.N]` or `[보충]`; 7 `[보충]` items total. |
| 5 | Wrote `summaries/01-teachback.md` | 8 prompts, one per approved core keyword, each with an (a) own-words part and a (b) relate-to-another-core-keyword part. No answers included. |
| 6 | `python3 ../code/scripts/check_summary.py 01` | **PASSED**, exit 0. Coverage missing: none. Untagged lines: 0. Flow: exists, no missing core, order OK, no missing page tags. |
| 7 | Saved checker output + report to `runs/01-2026-09-11/` | `check_summary_output.md`, `check_summary_report.md` |
| 8 | Wrote `runs/01-2026-09-11/spot-check.md` | 5 sampled items tabulated with blank verdict column for the human |

## Decisions worth reviewing
- **Checker invoked by a different path than PROMPT.md specifies.** PROMPT.md says
  `python3 scripts/check_summary.py 01`, but `scripts/` lives under `code/` while
  `approved/` and `summaries/` live under `outputs/`, and the checker resolves its inputs
  relative to cwd. Run as `python3 ../code/scripts/check_summary.py 01` with cwd =
  `outputs/`. The file itself was not created, edited, moved, or symlinked, and no
  substitute `scripts/` directory was made inside the run root. See
  `check_summary_output.md` for the full note.
- **`spot_check_sample` is randomized per invocation.** An intermediate re-run produced a
  different sample than the first, so the record was re-synced: the sample in
  `check_summary_output.md`, `check_summary_report.md`, `summaries/01-report.md` and
  `spot-check.md` all come from the same final invocation.
- **Iterative deepening given its own non-core subsection.** Depth-limited search and
  iterative deepening search are approved *minor* keywords, so they are explained under a
  "supporting algorithms" heading rather than promoted into the core set.
- **Two flow-section items landed in the spot-check sample** (items 3 and 4). Those test
  the page tag on a core concept's first mention in Lecture Flow, not a per-slide
  paraphrase.
- No exam-points or cheatsheet section was written — not requested.
- No web access used. No files under `course-materials/`, `approved/`, or `scripts/` were
  modified. No keys or personal data written.

## Status
- Steps 1-4 complete. Automated check: **PASS**.
- Run is **not** "done": the human spot-check in `spot-check.md` is still pending, and per
  the delegation card both gates must pass. Success is not self-declared.
