# Studio 02: Context Window Stress Test & Memory Architecture - Agent Setup Guide

This guide is a structured, step-by-step procedure written for an autonomous coding agent to set up, execute, and analyze Studio 02 inside a student group's copy of the course repository.

---

### Step 1: Check Node.js Version
**Command**
```bash
node --version
```
**Expected**
Prints the installed version of Node.js, which must be Node.js >= 22.19.0.
**Verify**
Ensure the output begins with `v22`, `v23`, `v24`, or higher, and matches or exceeds version `22.19.0`.
**STOP CONDITION**
If Node.js is not installed, or if the reported version is below `22.19.0`, stop immediately and ask your human teammate to upgrade Node.js on the system.

### Step 2: Install pi and Verify Version
**Command**
```bash
npm install -g --ignore-scripts @earendil-works/pi-coding-agent
pi --version
```
**Expected**
Installs the `pi` coding agent globally and prints its active version.
**Verify**
Ensure that the `pi` installation completes successfully and the version command executes without errors, returning the active harness version.
**STOP CONDITION**
If the installation fails with permission or network errors, or if `pi --version` is not recognized, stop and ask your human teammate to troubleshoot the global node environment.

### Step 3: Connect a Model Provider
**Command**
*Option A: Export OpenAI API Key (Primary Path)*
```bash
export OPENAI_API_KEY="your_api_key_here"
```
*Option B: Login via ChatGPT Plus/Pro Subscription (Alternative Path)*
```bash
pi
# Once inside the interactive shell:
# /login
# Select ChatGPT/Codex as your provider
```
**Expected**
For Option A, sets the primary environment variable. For Option B, logs into your ChatGPT subscription via the interactive prompt.
**Verify**
Ensure that the active provider is configured properly. Never print, log, or commit any keys or passwords, and never manually edit the file `~/.pi/agent/auth.json`.
**STOP CONDITION**
If both Option A (no API key provided) and Option B (login process fails or rejects access details) are unavailable, or if you are prompted to edit `~/.pi/agent/auth.json` manually, stop and ask your human teammate to supply valid access details.

### Step 4: Run the Setup Script
**Command**
```bash
cd code/studio-02/
bash setup.sh
```
*Optional Flags:*
- `--buckets <buckets>`: Comma-separated buckets to download (default: `256k,512k,1M`).
- `--n <n>`: Number of sampled items per bucket (default: `5`).
- `--dry-run`: Prints checks and downloads without modifying files.
**Expected**
Runs the setup sequence in order:
1. Checks that Node.js >= 22.19.0 and `pi` are installed.
2. Checks that Python >= 3.9 is present and required packages (tiktoken, huggingface_hub, matplotlib) are importable (prints instructions to run `pip install -r requirements.txt` if any are missing).
3. Downloads the BABILong qa1 data for requested buckets from Hugging Face dataset `RMT-team/babilong`, printing sizes before downloading, skipping existing (256k ~103 MB, 512k ~205 MB, 1M ~401 MB).
4. Constructs the 768K bucket from the 1M data (truncating to 768,000 real tokens and retaining items where the supporting fact survives truncation) and samples `n` items per bucket into `benchmarks/subset_qa1_topend.json`.
5. Updates `~/.pi/agent/models.json` to raise the context window limit of `gpt-5.6-luna` to 1,050,000 tokens for both `openai` and `openai-codex` providers (backing up the file first).
6. Prints which model providers are ready to use by presence only.
**Verify**
Ensure that the script runs all 6 steps without error and generates `benchmarks/subset_qa1_topend.json`.
**STOP CONDITION**
If Python >= 3.9 is missing, or if required packages fail to import, run `pip install -r requirements.txt` and retry. If setup fails during the data download, or if writing the catalog override to `~/.pi/agent/models.json` fails, stop and ask your human teammate for assistance.

### Step 5: Run Part A (Context Window Stress Test)
**Command**
```bash
cd code/studio-02/
python3 part_a_stress.py --model openai/gpt-5.6-luna
# If using Option B (ChatGPT Plus/Pro subscription):
# python3 part_a_stress.py --model openai-codex/gpt-5.6-luna

# After part_a_stress.py completes, run:
python3 plot_qa1_curve.py
```
*Optional Flags for part_a_stress.py:*
- `--buckets <buckets>`: Comma-separated buckets to test (e.g., `256k,512k,768k`).
- `--n <n>`: Number of items per bucket to test (default: `5`).
**Expected**
Executes a single-message `pi` call per item in the sampled buckets (with tools off), checking if the model can extract the buried location from the long story. Then, `plot_qa1_curve.py` generates the performance curve and updates the summary.
**Verify**
Ensure that the stress test completes and creates:
- `evidence/part_a/results.json`
- `evidence/part_a/results.csv`
- `evidence/part_a/summary.md`
- `evidence/part_a/qa1_curve.png` (rebuilt by the plot script)
Check that exact-match accuracy scores and token sizes are recorded.
**STOP CONDITION**
If the script encounters model provider connection failures, rate limits, or persistent API errors, stop and ask your human teammate to check API status or available credits.

### Step 6: Run Part B (Isolate and Targeted Summary Fixes)
**Command**
```bash
cd code/studio-02/
python3 part_b_isolate_compress.py --model openai/gpt-5.6-luna
# If using Option B (ChatGPT Plus/Pro subscription):
# python3 part_b_isolate_compress.py --model openai-codex/gpt-5.6-luna
```
*Optional Flags:*
- `--buckets <buckets>`: Comma-separated buckets to run.
- `--n <n>`: Number of items per bucket (default: `5`, must match Part A).
- `--concurrency <concurrency>`: Max concurrent calls (default: `4`).
- `--max-usd <max_usd>`: Stop submitting new calls if running cost exceeds this.
- `--dry-run`: Prints the run plan and estimated cost without executing calls.
**Expected**
Runs two separate fixes for each story item in Part A:
1. Isolate: Splits the story into ~96,000-token chunks, calls a sub-agent per chunk to report locations, and uses a lead agent to make the final determination (taking the last mentioned location).
2. Targeted summary: Summarizes chunks in ~200 tokens (instructed to keep location details) and answers the question from concatenated summaries.
**Verify**
Ensure that the following files are successfully created under `evidence/part_b/`:
- `results.json`
- `results.csv`
- `summary.md`
- `comparison.png`
Confirm that peak single-call context tokens and total tokens are explicitly tracked and written.
**STOP CONDITION**
If the script fails due to concurrency issues, thread deadlocks, or if cost estimates exceed your group's spending limit, stop and ask your human teammate.

### Step 7: Run Part C (Memory Architecture Test)
**Command**
```bash
cd code/studio-02/
python3 part_c_memory.py --model openai/gpt-5.6-luna
# If using Option B (ChatGPT Plus/Pro subscription):
# python3 part_c_memory.py --model openai-codex/gpt-5.6-luna
```
*Optional Flags:*
- `--fresh`: Wipes `work/part_c/` and restarts all three sessions.
**Expected**
Runs three sequential `pi` sessions under `work/part_c/with-memory/` (guided by `AGENTS.md` instructions to consult `decisions.md` and log decisions) and compares the final recall to a baseline run in `work/part_c/no-memory/`.
- Session 1: Plans a note-taking tool and writes three decisions to `decisions.md`.
- Session 2: Writes Fibonacci script (`fib.py`) and writes at least one decision.
- Session 3: Queries the decisions made in Session 1.
**Verify**
Ensure that the following files are written:
- `evidence/part_c/decisions.md`
- `evidence/part_c/fib.py`
- `evidence/part_c/session3-with-memory-answer.md`
- `evidence/part_c/session3-no-memory-answer.md`
- `evidence/part_c/part_c.json`
- `evidence/part_c/summary.md`
**STOP CONDITION**
If the memory sessions crash, if files are written outside the `work/part_c/` directory, or if the final JSON comparison file is not generated, stop and ask your human teammate.

### Step 8: Initialize EXPLANATION.md
**Command**
```bash
cd code/studio-02/
cp ../../studio/studio-02/starter/EXPLANATION_TEMPLATE.md evidence/EXPLANATION.md
```
**Expected**
Copies the explanation template from the starter pack into the active evidence directory.
**Verify**
Ensure that `evidence/EXPLANATION.md` exists and contains the six required markdown sections with their original instructions. Do not change the template structure.
**STOP CONDITION**
If the template file is not found in the path, stop and ask your human teammate to locate the template.

### Step 9: Initialize the Evidence Checklist
**Command**
```bash
cd code/studio-02/
cp ../../studio/studio-02/starter/evidence/README.md evidence/README.md
```
**Expected**
Copies the checklist readme from the starter pack into the active evidence directory.
**Verify**
Ensure that `evidence/README.md` is present and contains the exact blank lines for recording runs, tokens, and contributions.
**STOP CONDITION**
If the copy fails because the source checklist is missing, stop and ask your human teammate.

---

## General Stop Conditions

As an autonomous agent, you must stop immediately and hand over control to your human teammate in the following scenarios:
1. **API Key and Access Token Exposure Risk:** If any command, output, or error reveals or risks committing API keys, tokens, or configuration secrets.
2. **Persistent API Blockers:** If the model provider returns persistent authentication errors, rate limits, or credit exhaustion warnings.
3. **Execution Anomalies:** If a script throws an unhandled traceback or encounters a file access error that cannot be resolved via standard dependencies.
4. **Discrepancies in Data:** If any step produces corrupt files or fails to generate the outputs listed in the File Layout.

---

## File Layout

After running all procedures successfully, the `evidence/` directory must match this structure exactly:

```
evidence/
├── EXPLANATION.md
├── README.md
├── part_a/
│   ├── results.json
│   ├── results.csv
│   ├── summary.md
│   └── qa1_curve.png
├── part_b/
│   ├── results.json
│   ├── results.csv
│   ├── summary.md
│   └── comparison.png
└── part_c/
    ├── decisions.md
    ├── fib.py
    ├── session3-with-memory-answer.md
    ├── session3-no-memory-answer.md
    ├── part_c.json
    └── summary.md
```
