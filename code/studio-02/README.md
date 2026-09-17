# What this is

This folder implements Studio 02, "Context Window Stress Test & Memory Architecture," for COMS
W4995-009 Agentic Engineering at Columbia University. It uses pi, the open-source terminal coding
agent (package `@earendil-works/pi-coding-agent`), as the harness, instead of "choose your own
harness."

There are four scripts: `setup.sh`, `part_a_stress.py`, `part_b_isolate_compress.py`, and
`part_c_memory.py`. Run all of them from inside `code/studio-02/`. The Python scripts need Python 3.9
or newer and use only the standard library -- there is nothing extra to install.

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

pi can use a provider two ways. The first is a subscription -- Anthropic Claude Pro/Max, OpenAI
ChatGPT Plus/Pro (for Codex), GitHub Copilot, and others -- through `pi` and then `/login` in
interactive mode. On a headless machine with no browser, the Codex login's OAuth (Open Authorization)
callback cannot complete; you paste the final redirect URL into the prompt instead, but this whole flow
is interactive only, and it was not used for this validation.

The second way is an API key through an environment variable. The exact names pi reads are
`ANTHROPIC_API_KEY` (Anthropic), `OPENAI_API_KEY` (OpenAI), `GEMINI_API_KEY` (Google Gemini -- note
this is `GEMINI_API_KEY`, not a "GOOGLE_..." name), and `DEEPSEEK_API_KEY` (DeepSeek). Export whichever
one you have before running any script here. Never print, log, or commit an API key.

# Setup

Run this first, from `code/studio-02/`:

```bash
bash setup.sh
```

Add `--install` if pi is not yet installed, and you want the script to install it for you:

```bash
bash setup.sh --install
```

`setup.sh` does four things, in order: (1) checks Node.js and pi are installed and prints their
versions; (2) downloads the corpus PDF (arXiv 2507.13334, "A Survey of Context Engineering for Large
Language Models," Mei et al. 2025) if it is not already present, converts it to `corpus/survey.txt`
with `pdftotext`, and splits it into `corpus/sections/section-01.txt` through `section-NN.txt` of about
12,000 words each (this corpus produces 6 section files, the last one shorter); (3) prints the word
count and an estimated token count (words times 1.33) for the whole corpus and each section --
validated at 70,802 words, about 94,167 estimated tokens; (4) prints which model providers are
currently usable, based on which environment variables are set, without ever printing a secret value.

It is safe to run more than once: it will not re-download or re-split anything if `corpus/survey.txt`
already exists, and it never touches `evidence/`.

# Part A: stress test

```bash
python3 part_a_stress.py --model <provider/id> --sizes 8k,16k,32k,64k,full --out evidence
```

The `--sizes` value shown is also the default. `--model` defaults to the Codex spark model,
`openai-codex/gpt-5.3-codex-spark` (see "How we chose a model" below), which needs a ChatGPT/Codex login
(`pi` then `/login`) and was not validated on this machine. To use the model every recorded run in this
folder actually used, pass it explicitly:

```bash
python3 part_a_stress.py --model google/gemini-3.1-flash-lite
```

Expect progress lines as each size is tested and scored.

For each size, the script takes the first that-many estimated tokens of the corpus, builds one prompt
with that slice of text plus the five questions from `questions.json`, and asks pi to answer all five,
numbered 1 to 5, saying NOT FOUND for anything not in the text. It disables pi's automatic compaction
for this run (a project settings file, `work/part_a/.pi/settings.json`, sets `"compaction": {"enabled":
false}`), so if a slice were ever too large for the model's real context window, that would show up as
a genuine API error instead of being silently summarized away. Tools are disabled entirely
(`--no-tools`), since the whole slice is pasted directly into the prompt.

Two optional sizes, `2x` and `3x`, are also accepted (but are not part of the default `--sizes` and
were not added to it): the full corpus followed by 1 or 2 extra rounds of its own section files,
reshuffled into a different order each round, appended as distractor padding. These exist for models
whose context window is too large for "full" alone to threaten -- for example
`google/gemini-3.1-flash-lite`'s 1,048,576-token window is nearly 7 times the corpus's real token count,
so `2x`/`3x` push the total context to roughly a third and a half of that window instead. Run them with
`python3 part_a_stress.py --model <provider/id> --sizes 2x,3x`.

It writes, for each size: `evidence/part_a/run-<size>.json` (score, the five parsed answers, token
usage, cost, and any error) and `evidence/part_a/run-<size>.raw.jsonl` (the complete raw stream of
events pi produced, exactly as pi wrote it; this raw file stays local and is not committed -- see
"Evidence size note" below). Once all sizes have run, it writes `evidence/part_a/summary.md`: a table
across all sizes, plus one line stating the first size where the score dropped below an earlier best, or
where the call errored -- whichever came first. If neither ever happened, it says so.

Re-running is safe: each run only overwrites its own files, and nothing under `evidence/` is ever
deleted.

# Part B: isolate and compress

```bash
python3 part_b_isolate_compress.py --model <provider/id> --out evidence
```

This needs `evidence/part_a/` to already exist -- run Part A first, since Part B uses Part A's
best-scoring run as input for one of its three demonstrations. Expect progress logging for each
demonstration, then a comparison table.

The three demonstrations, run in one pass:

1. **Isolate.** One pi process runs per corpus section file, each told to return only a short numbered
   list of findings relevant to the five questions (at most 150 words, never a full transcript). One
   more "lead" pi process then answers using only the combined findings plus the five questions -- no
   raw corpus text.
2. **Compress, summary artifact.** pi writes a short markdown briefing summarizing Part A's best run's
   answers (what was found, what was not), then the five questions are re-asked using only that
   briefing as context.
3. **Compress, pi's own compaction.** pi runs in a work directory whose `.pi/settings.json` turns
   compaction back on, with a `reserveTokens` value computed from the model's real context window so
   that compaction should trigger around 50,000 tokens of context. The agent reads the corpus section
   files one by one through its own `read` tool calls, so context actually grows turn by turn (the way
   compaction is meant to be triggered), then the five questions are asked.

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

# How we chose a model

The instructions were: use the cheapest tool-capable model in pi's `openai` catalog whose context
window fits the roughly 95,000-token corpus, falling back to Gemini or DeepSeek if OpenAI fails. List
models non-interactively with:

```bash
pi --list-models
```

Add a search term to narrow it down, for example:

```bash
pi --list-models codex
```

This needs at least one provider's credentials configured first, or it prints nothing for that
provider.

The cheapest qualifying OpenAI model was `gpt-5-nano` (400,000-token context window, $0.05 per million
input tokens, $0.40 per million output tokens) -- but this machine's OpenAI API key had no credits left
(pi's own error: "You have no credits remaining"). Falling back to DeepSeek's `deepseek-flash` also
failed ("402 Insufficient Balance"). Falling back to Gemini worked, but the obvious first choice,
`gemini-2.5-flash-lite`, is deprecated (the API's error said it is "no longer available to new users"
and suggested `gemini-3.5-flash-lite` instead).

The model actually used for every validated run in this folder is `google/gemini-3.1-flash-lite`:
cheaper than the suggested replacement ($0.25 per million input tokens and $1.50 per million output
tokens, versus $0.30 / $2.50), with a 1,048,576-token context window (comfortably larger than the whole
corpus), and confirmed working with real tool calls before committing to the full run. Use a different
model by passing `--model provider/model-id` to any of the three part scripts.

**On the "spark" model, and the scripts' default.** Nick asked for the Codex model
`gpt-5.3-codex-spark`, and whether it exists. It does: `gpt-5.3-codex-spark` is a real model ID, listed
both under the `openai-codex` provider (the ChatGPT/Codex subscription provider, 128,000-token context
window) and under the plain `openai` API-key provider (also a real, listable model, 128,000-token
context window, $1.75 per million input tokens, $14 per million output tokens -- not cheap). Since the
contract asks for the spark model as the default whenever it exists, `--model` defaults to
`openai-codex/gpt-5.3-codex-spark` in all three part scripts.

**This default is untested on the validation machine and every piece of recorded evidence in this
folder actually used `google/gemini-3.1-flash-lite` instead**, passed explicitly with `--model
google/gemini-3.1-flash-lite`. The `openai-codex` provider needs the interactive ChatGPT/Codex browser
login, which cannot complete headlessly, and this machine's Codex quota was reported as exhausted
regardless, so the default could not be exercised end to end here. If a script fails on you with an
authentication or model-not-found error, it now prints one hint line: log in (`pi` then `/login`) or
fall back to the validated model (`--model google/gemini-3.1-flash-lite`). Students with a working
ChatGPT Plus/Pro subscription can reach the default with:

```bash
pi
```

then, inside the interactive session:

```text
/login
```

and select ChatGPT/Codex. After that, launch pi with:

```bash
pi --model openai-codex/gpt-5.3-codex-spark
```

# Cost and time observed

Total real API spend for the evidence kept in this folder: $0.3151, across 69 model calls (Part A,
including the optional 2x/3x sizes, plus Part B plus Part C). Wall time for the three scripts run back
to back: about 95 seconds total. All of this is far under a $10 budget for one validation pass with
this model.

# Evidence size note

Every pi call in these scripts saves its own session file under `evidence/sessions/` (via pi's
`--session-dir` flag), and the scripts separately save the complete raw `--mode json` event stream for
each call next to that part's other output files (`evidence/part_*/raw/*.raw.jsonl` or, for Part A,
`evidence/part_a/run-<size>.raw.jsonl`). The scripts always write both, locally, on every run.

Only the session files and each part's extracted `.json`/`.md` summaries are committed to the
repository. The raw event streams are excluded through `.gitignore` (`evidence/**/*.raw.jsonl`) and stay
local only: in this run they added up to about 9.5 MB, all of it the same information already captured
in more compact form by the ~6.9 MB of session files (each one comfortably under 2 MB) plus the scripts'
own summary files. A committed course repository should not carry that much duplicate log data. If you
need the full verbatim event-by-event record for a specific call -- for example to see every streamed
delta of a long compaction run -- it is sitting locally in the matching `raw/*.raw.jsonl` file; it is
just not pushed to GitHub.

# Files in this folder

`setup.sh`, `questions.json`, `lib/pi_runner.py` (shared code used by every script), `part_a_stress.py`,
`part_b_isolate_compress.py`, `part_c_memory.py`, `.gitignore`, `README.md` (this file), and `evidence/`
(the recorded real run, including `EXPLANATION.md`, the graded write-up).

`corpus/` and `work/` are created by the scripts and are not committed (see `.gitignore`): running
`bash setup.sh` recreates `corpus/`, and running the three part scripts recreates whatever they need
under `work/`.
