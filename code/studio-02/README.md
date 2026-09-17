# What this is

This folder implements Studio 02, "Context Window Stress Test & Memory Architecture," for COMS
W4995-009 Agentic Engineering at Columbia University. It uses pi, the open-source terminal coding
agent (package `@earendil-works/pi-coding-agent`), as the harness, instead of "choose your own
harness."

There are five scripts: `setup.sh`, `part_a_stress.py`, `part_b_isolate_compress.py`,
`part_c_memory.py`, and `context_sweep.py`. Run all of them from inside `code/studio-02/`. The Python
scripts need Python 3.9 or newer. Most of the code is standard library only; real-token counting and
the two charts need two extra packages: `pip install --user tiktoken matplotlib` (both are already
installed on the validation machine). Everything degrades to a word-count estimate if `tiktoken` is
missing, but the two context-sweep charts need `matplotlib`.

# Install pi

pi needs Node.js. The installed package's own `package.json` states the real minimum: Node.js 22.19.0
or newer (stricter than some general guidance suggesting Node 20, so trust the package.json). Install
pi with:

```bash
npm install -g --ignore-scripts @earendil-works/pi-coding-agent
```

Check it worked:

```bash
pi --version
```

This should print a version number (validated on this machine: `0.85.1`).

**This studio's validated path is the ChatGPT/Codex subscription**, through pi's `openai-codex`
provider. On the validation machine it is already logged in (an OAuth -- Open Authorization -- token in
`~/.pi/agent/auth.json`, a pooled team account); none of the scripts in this folder call `/login` or
touch that file, and no API key is used, needed, or read from the environment for the default model. On
your own machine, log in once yourself, interactively: `pi` then `/login`, and select ChatGPT/Codex. On
a headless machine with no browser, the OAuth callback cannot complete; paste the final redirect URL
into the prompt instead.

Without Codex access, you can still use an API-key provider (Anthropic, OpenAI, Google Gemini,
DeepSeek) by passing `--model` explicitly. The exact environment variable names pi reads are
`ANTHROPIC_API_KEY` (Anthropic), `OPENAI_API_KEY` (OpenAI), `GEMINI_API_KEY` (Google Gemini -- note this
is `GEMINI_API_KEY`, not a "GOOGLE_..." name), and `DEEPSEEK_API_KEY` (DeepSeek). Export whichever one
you have before running any script here. Never print, log, or commit an API key, and never edit
`~/.pi/agent/auth.json` by hand.

# Setup

Run this first, from `code/studio-02/`:

```bash
bash setup.sh
```

Add `--install` if pi is not yet installed, and you want the script to install it for you:

```bash
bash setup.sh --install
```

`setup.sh` does six things, in order: (1) checks Node.js and pi are installed and prints their versions;
(2) downloads the survey PDF (arXiv 2507.13334, "A Survey of Context Engineering for Large Language
Models," Mei et al. 2025) if not already present and converts it to `corpus/survey.txt` with
`pdftotext`; (3) prints the word count and an estimated token count (words times 1.33) for
`corpus/survey.txt` -- validated at 70,802 words, about 94,167 estimated tokens; (4) prints which model
providers are currently usable, based on which environment variables are set, without ever printing a
secret value; (5) downloads the 12 additional arXiv papers used by `context_sweep.py` (see that section
below) if not already present, converts each to text, and builds `corpus/combined.txt` and
`corpus/manifest.json` from all 13 documents, in order, using the real tiktoken token count (`o200k_base`)
-- validated at 579,456 real tokens total; (6) splits `corpus/combined.txt` into
`corpus/sections/section-01.txt` through `section-NN.txt` of about 30,000 real tokens each, for Part B
(this corpus produces 20 section files, the last one shorter).

It is safe to run more than once: it will not re-download or re-convert any PDF already present, and it
never touches `evidence/`.

# Part A: stress test

```bash
python3 part_a_stress.py --model openai-codex/gpt-5.6-luna --sizes 64k,128k,256k,full --out evidence
```

Both flags shown are also the defaults (as of contract addendum v2 section 7), so `python3
part_a_stress.py` alone does the same thing. Expect progress lines as each size is tested and scored.

Part A now shares its corpus, its real-token slicing, and its section-5 scoring (overall / in-slice /
abstention accuracy) with `context_sweep.py` -- see that section below for what those three accuracies
mean. Its default corpus is `corpus/combined.txt` (the same 579,456-real-token, 13-document corpus the
sweep uses), not the single-document `corpus/survey.txt`; pass `--corpus corpus/survey.txt` to run the
smaller, original version instead. Sizes `8k`,`16k`,`32k`,`200k` are still accepted too (not just the
four defaults), and slices are always real tiktoken tokens now, not the word-based estimate.

For each size, the script takes the first that-many real tokens of the corpus, builds one prompt with
that slice of text plus every question in `questions.json`, and asks pi to answer them all, numbered to
match, saying NOT FOUND for anything not in the text. It disables pi's automatic compaction for this run
(a project settings file, `work/part_a/.pi/settings.json`, sets `"compaction": {"enabled": false}`), so
if a slice were ever too large for the model's real context window, that would show up as a genuine API
error instead of being silently summarized away -- though see the context sweep section below: on
`openai-codex/gpt-5.6-luna`, even a slice past its documented context window did not actually error.
Tools are disabled entirely (`--no-tools`), since the whole slice is pasted directly into the prompt
(sent over stdin, not as a command-line argument).

Two optional sizes, `2x` and `3x`, are also accepted: the full corpus followed by 1 or 2 extra rounds of
its own section files, reshuffled into a different order each round, appended as distractor padding, for
a model whose context window is too large for "full" alone to threaten. Run them with `python3
part_a_stress.py --sizes 2x,3x`.

It writes, for each size: `evidence/part_a/run-<size>.json` (accuracy, the parsed answers, token usage,
cost, and any error) and `evidence/part_a/run-<size>.raw.jsonl` (the complete raw stream of events pi
produced, exactly as pi wrote it; this raw file stays local and is not committed -- see "Evidence size
note" below). Once all sizes have run, it writes `evidence/part_a/summary.md`: a table across all sizes,
plus one line stating the first size where overall accuracy dropped below an earlier best, or where the
call errored -- whichever came first. If neither ever happened, it says so.

Re-running is safe: each run only overwrites its own files, and nothing under `evidence/` is ever
deleted. **Note:** the `evidence/part_a/` (and `part_b/`, `part_c/`) files currently in this repository
were produced by an earlier round of this studio, before the Codex subscription and the combined corpus
existed, using `--model google/gemini-3.1-flash-lite` and the single-document survey corpus -- they have
not been regenerated at the new defaults (doing so was optional and was not run, to conserve the shared
Codex quota after the context sweep). `evidence/context_sweep/` is the one deliverable validated against
the new defaults end to end.

# Part B: isolate and compress

```bash
python3 part_b_isolate_compress.py --model <provider/id> --out evidence
```

This needs `evidence/part_a/` to already exist -- run Part A first, since Part B uses Part A's
best-scoring run as input for one of its three demonstrations. Expect progress logging for each
demonstration, then a comparison table.

Part B's corpus sections are `corpus/sections/section-NN.txt`, built by `setup.sh` from
`corpus/combined.txt` at about 30,000 real tokens each (20 section files for the current 13-document
corpus; see "Setup" above) -- since section 7 of contract addendum v2, no longer the original
12,000-word, single-document survey sections.

The three demonstrations, run in one pass:

1. **Isolate.** One pi process runs per corpus section file, each told to return only a short numbered
   list of findings relevant to the questions in `questions.json` (at most 150 words, never a full
   transcript). One more "lead" pi process then answers using only the combined findings plus the
   questions -- no raw corpus text. With 20 sections, this means 20 sub-agent calls plus 1 lead call.
2. **Compress, summary artifact.** pi writes a short markdown briefing summarizing Part A's best run's
   answers (what was found, what was not), then the questions are re-asked using only that briefing as
   context.
3. **Compress, pi's own compaction.** pi runs in a work directory whose `.pi/settings.json` turns
   compaction back on, with a `reserveTokens` value computed from the model's real context window so
   that compaction should trigger around 50,000 tokens of context. The agent reads the corpus section
   files one by one through its own `read` tool calls, so context actually grows turn by turn (the way
   compaction is meant to be triggered), then the questions are asked. With 20 sections instead of the
   original 6, this demonstration now reads much more text before answering, so compaction firing is
   more likely, not less.

It writes: `evidence/part_b/findings/section-NN.md` (each section's findings), `evidence/part_b/
isolate.json`, `evidence/part_b/summary-of-part-a.md` and `evidence/part_b/summary-artifact.json`,
`evidence/part_b/compaction.json` (including any `compaction_start` / `compaction_end` events pi
reported, with the `tokensBefore` value pi recorded), and `evidence/part_b/summary.md` (one table
comparing Part A's best score against all three Part B methods, with tokens and cost for each). It also
writes `evidence/part_b/raw/*.raw.jsonl` (the raw event stream for every call), but these stay local and
are not committed to the repository -- see "Evidence size note" below.

Re-running is safe in the same way as Part A.

# Part C: memory across sessions

```bash
python3 part_c_memory.py --model <provider/id> --out evidence
```

Add `--fresh` to wipe `work/part_c/` and start the three sessions over from nothing (`evidence/` is
still never deleted):

```bash
python3 part_c_memory.py --model <provider/id> --out evidence --fresh
```

Expect step-by-step progress lines for each session, then a recall comparison table.

In `work/part_c/with-memory/` (which gets an `AGENTS.md` file telling pi to check `decisions.md` before
any task, and to append -- never delete or rewrite -- a dated entry whenever it makes a decision), the
script runs three separate new pi sessions:

- **Session 1** plans a small command-line note-taking tool and is told to make and record three
  specific decisions, each with a reason: the storage format for notes, the command name, and the date
  format.
- **Session 2** does an unrelated task (write `fib.py`, printing the first 20 Fibonacci numbers) and
  records at least one decision of its own.
- **Session 3** asks: "What did we decide in session 1 about the note-taking tool, and why?"

The identical session-3 question is then asked again in a completely separate, fresh
`work/part_c/no-memory/` directory with no `AGENTS.md` and no `decisions.md`, as the memoryless
baseline.

Every one of these calls passes `--no-context-files`, so pi never walks parent directories looking for
`AGENTS.md`/`CLAUDE.md` (this machine has unrelated personal ones above the repo root that once leaked
into an answer -- see the evidence size note and `EXPLANATION.md` section 4). The with-memory sessions
still get their `AGENTS.md` instructions: the same text is also passed straight to the model with
`--append-system-prompt`, along with today's real date (from the system clock), so `decisions.md` gets
correctly dated entries instead of a guess. The recall-checking step (session 3, both conditions) also
gets a `--append-system-prompt` instruction to only use its own current directory: giving it just a
`read` tool, with no directory-listing tool, was not enough on its own -- a no-memory baseline still
found the sibling with-memory directory's `decisions.md` by guessing relative paths and reading its way
up to this very README, which documents the with-memory/no-memory layout. See `EXPLANATION.md` section 4
for the full account.

It writes: `evidence/part_c/decisions.md` and `evidence/part_c/fib.py` (copied from the working
directory), `evidence/part_c/session3-with-memory-answer.md` and `evidence/part_c/session3-no-memory-
answer.md`, `evidence/part_c/part_c.json` (full detail, including an automatic recall check -- correct,
missing, or invented -- for each of the three decisions, in both conditions), and
`evidence/part_c/summary.md`. It also writes `evidence/part_c/raw/*.raw.jsonl`, which stays local and is
not committed -- see "Evidence size note" below.

Re-running is safe; use `--fresh` if you want the three sessions to start over rather than continuing
in an already-used `work/part_c/` directory.

# Context sweep: accuracy vs. context length

`context_sweep.py` measures accuracy against context length over a bigger, 13-document combined corpus:
the original survey plus 12 more arXiv papers on context engineering, memory, and retrieval, used as
bulk length and distractor text. `setup.sh` builds it into `corpus/combined.txt` and
`corpus/manifest.json`, 579,456 real tokens total (tiktoken `o200k_base`). `questions.json` has 20
questions: 17 answerable, each with a measured `needle_depth_tokens` position in the combined corpus,
and 3 marked `expect_not_found` (verified by grep that the topic is not in the corpus at all -- the
correct answer is always NOT FOUND).

Command actually run:

```bash
python3 context_sweep.py --model openai-codex/gpt-5.6-luna \
    --sizes 16k,32k,64k,128k,200k,256k,full --out evidence/context_sweep --thinking low
```

For each size, the script takes the first N real tokens of `combined.txt` (a line-safe cut) and asks all
20 questions in one turn: auto-compaction disabled (a project `.pi/settings.json`), tools disabled
(`--no-tools`), pi's own parent-directory context-file discovery disabled (`--no-context-files`), and
the bulk text sent over stdin rather than as a command-line argument (to stay under the operating
system's per-argument size limit).

Three accuracies are computed per size, and `results.json` / `results.csv` record a correct / wrong /
hallucinated verdict for every question at every size: **overall accuracy** (correct out of all 20
questions), **in-slice accuracy** (correct out of only the questions whose needle sits inside that
size's slice), and **abstention accuracy** (correct out of only the questions whose needle is beyond the
slice, or marked `expect_not_found` -- does the model correctly say NOT FOUND instead of guessing).
`summary.md` also lists, per size, which question ids were in-slice, and separately flags any
"verbose-but-correct" case: an answer that matched every required gold keyword but also mentioned a
`must_not_contain` distractor term, which the scoring rule marks wrong but which is worth a human
double-checking by hand. None were flagged in this run.

**Real result: the `full` size did not fail.** At 579,456 real tokens (580,786 by pi's own usage
report) -- more than double `gpt-5.6-luna`'s documented 272,000-token context window -- there was no
context-length error, no error of any kind. The model returned a complete, coherent answer to all 20
questions. This contradicts what was expected going in (a context-length failure was predicted). It is
a real, verified finding, not a mistake: compaction was disabled and confirmed absent from the event
log, the full corpus was genuinely sent (token counts match), and the answer was complete and on-topic,
not truncated.

**Correction (see `evidence/context_sweep/summary.md` for the full note).** The first scoring pass had
two bugs, both in the scorer, not in the model calls: the answer parser matched only single-digit
question numbers, so answers 10-20 were silently read as leftover text of answer 9 and scored wrong or
hallucinated regardless of their real content; and some keyword groups required only terms already
present in the question text, so a terse correct answer could not match, and number-format variants
like "2,048K" vs "2048K" were not normalized. All 7 model calls are the original ones -- nothing was
re-run. `python3 context_sweep.py --rescore --out evidence/context_sweep` re-parses and re-scores the
same saved `answer_text` with the fixed parser and the revised `questions.json`, at no cost (no pi
calls), and rewrites `results.json` / `results.csv` / `summary.md` and both charts; the original
`run-<size>.json` files (usage, timing, raw text) are left untouched, and every changed verdict is
listed in `rescore_diff.json`. 91 of 140 (size x question) verdicts changed, every one of them from
wrong or hallucinated to correct; none moved the other way. The numbers below are the corrected ones.

| size | real input tokens | overall accuracy | in-slice accuracy | abstention accuracy | wall time |
| --- | --- | --- | --- | --- | --- |
| 16k | 16,875 | 100% (20/20) | 100% (n=4) | 100% (n=16) | 10.67s |
| 32k | 32,729 | 100% (20/20) | 100% (n=4) | 100% (n=16) | 11.97s |
| 64k | 64,333 | 100% (20/20) | 100% (n=5) | 100% (n=15) | 16.33s |
| 128k | 127,610 | 100% (20/20) | 100% (n=5) | 100% (n=15) | 13.75s |
| 200k | 198,865 | 100% (20/20) | 100% (n=11) | 100% (n=9) | 13.0s |
| 256k | 253,860 | 100% (20/20) | 100% (n=15) | 100% (n=5) | 15.85s |
| full | 580,786 | 100% (20/20) | 100% (n=17) | 100% (n=3) | 18.16s |

With the scorer fixed, `openai-codex/gpt-5.6-luna` answered every question correctly at every size
tested, both the ones whose needle was in the slice and the ones it correctly declined (NOT FOUND) --
including the 3 `expect_not_found` questions (ids 18, 19, 20), which were never actually hallucinated;
that claim in an earlier draft of this README was itself an artifact of the parser bug above.

Total real cost for this sweep: $0.3745 across the 7 calls above (the `--rescore` pass itself made no
pi calls and cost nothing).

Two charts are written to `evidence/context_sweep/`: `accuracy_vs_length.png` (the three accuracies
above, as lines, against real input tokens) and `heatmap.png` (a correct / wrong / hallucinated grid,
questions ordered by needle depth, with a step-line boundary marking which cells were inside that size's
window). Both use this project's `dataviz`-skill palette: categorical blue/orange/aqua for the three
accuracy lines, and a fixed status-color grid (green/amber/red) for the heatmap.

# How we chose a model

**This studio's validated path is the ChatGPT/Codex subscription**, through pi's `openai-codex`
provider (see "Install pi" above). The model used for every run of real evidence in this folder --
`context_sweep.py` and Part A alike -- is `openai-codex/gpt-5.6-luna`, with pi's `--thinking low` flag.
Its context window is 272,000 tokens per pi's catalog. This model is now validated end to end,
including a real run past its documented context window with no error at all (see "Context sweep"
above). List available models non-interactively with `pi --list-models` (add a search term to narrow
it down, e.g. `pi --list-models codex`); this needs at least one provider's credentials configured
first (a login, or an API key), or it prints nothing for that provider.

**Historical note.** An earlier round of this studio, before the Codex subscription was available, used
an API-key provider instead. The cheapest tool-capable OpenAI model, `gpt-5-nano`, failed because the
OpenAI API key on the validation machine had no credits ("You have no credits remaining"); DeepSeek's
`deepseek-flash` also failed ("402 Insufficient Balance"); Google Gemini's `gemini-2.5-flash-lite` is
deprecated ("no longer available to new users"). `google/gemini-3.1-flash-lite` worked and was used for
that round's evidence, still recorded under `evidence/part_a`, `evidence/part_b`, and `evidence/part_c`.
To use that fallback model now, pass `--model google/gemini-3.1-flash-lite` and export `GEMINI_API_KEY`.

# Cost and time observed

Two rounds of real spending are recorded here. The context sweep (current round, Codex subscription,
`openai-codex/gpt-5.6-luna`): $0.3745 across the 7 calls in `evidence/context_sweep/`. The earlier round
(`google/gemini-3.1-flash-lite`, API key): $0.3151 across 69 calls in `evidence/part_a`, `part_b`, and
`part_c`, over about 95 seconds of wall time for the three scripts run back to back. Both totals are far
under a $10 budget for one validation pass.

# Evidence size note

Every pi call in these scripts saves its own session file under `evidence/sessions/` (via pi's
`--session-dir` flag; `context_sweep.py` uses its own `--out`-relative `sessions/` directory), and the
scripts separately save the complete raw `--mode json` event stream for each call next to that part's
other output files (`evidence/part_*/raw/*.raw.jsonl`, `evidence/context_sweep/raw/<size>.raw.jsonl`, or,
for Part A, `evidence/part_a/run-<size>.raw.jsonl`). The scripts always write both, locally, on every run.

Only the session files and each part's extracted `.json`/`.md`/`.png` outputs are committed to the
repository. The raw event streams are excluded through `.gitignore` (`evidence/**/*.raw.jsonl`) and stay
local only -- they carry the same information already captured in more compact form by the session
files (each one comfortably under 2 MB) plus the scripts' own summary files. A committed course
repository should not carry that much duplicate log data. If you need the full verbatim event-by-event
record for a specific call -- for example to see every streamed delta of a long run -- it is sitting
locally in the matching `raw/*.raw.jsonl` file; it is just not pushed to GitHub.

# Files in this folder

`setup.sh`, `questions.json`, `lib/pi_runner.py` and `lib/charts.py` (shared code used by every script),
`part_a_stress.py`, `part_b_isolate_compress.py`, `part_c_memory.py`, `context_sweep.py`, `.gitignore`,
`README.md` (this file), and `evidence/` (the recorded real runs, including `EXPLANATION.md`, the graded
write-up, and `context_sweep/accuracy_vs_length.png` / `context_sweep/heatmap.png`, the two charts).

`corpus/` and `work/` are created by the scripts and are not committed (see `.gitignore`): running
`bash setup.sh` recreates `corpus/` (including `combined.txt` and `manifest.json`), and running the
scripts recreates whatever they need under `work/`.
