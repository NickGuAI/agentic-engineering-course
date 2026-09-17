# Studio 02 Setup and Run Procedure for Autonomous Coding Agents

## Course and Studio Context
This procedure is for Studio 02, "Context Window Stress Test & Memory Architecture," in COMS W4995-009 Agentic Engineering at Columbia University. You will set up and run this studio in your copy of the course repository. This repository contains the directory `code/studio-02/` for the provided scripts and the directory `studio/studio-02/starter/` for template files. You must copy these template files into your evidence folder. Do not commit API keys or personal information. Do not delete any existing evidence files. The scripts are re-runnable and additive.

## Step-by-Step Procedure

1. Check Node.js version.
Command:
```bash
node --version
```
Expected: The command prints a version string of 22.19.0 or higher.
Verify: Compare the printed version against 22.19.0. Confirm that the installed version is equal to or greater than 22.19.0.
STOP CONDITION: If Node.js is missing or older than 22.19.0, stop immediately. Do not try to install or upgrade Node.js. Ask your human teammate to install or upgrade Node.js using nvm before you continue.

2. Install pi.
Command:
```bash
npm install -g --ignore-scripts @earendil-works/pi-coding-agent
```
Expected: npm finishes with no error.
Verify: Run the command `pi --version` and check that it prints a version number with no error.
STOP CONDITION: If the installation fails or `pi --version` returns an error, stop immediately. Do not attempt to use `sudo` or make system-level changes. Ask your human teammate to resolve the installation issue.

3. Confirm a model provider is connected.
Command:
Ask your human teammate which of these four paths they want to use:
- Path (a): Claude Pro/Max subscription
- Path (b): ChatGPT Plus/Pro (Codex) subscription
- Path (c): GitHub Copilot
- Path (d): An API key

For paths (a), (b), or (c):
Your human teammate must run `pi` interactively, type `/login`, and complete the provider picker. This is a browser-based login that you cannot complete on your own. On a remote or headless machine, `pi` will ask the human to paste back a redirect URL instead of opening a browser. This still requires the human to complete the action.

For path (d):
Ask your human teammate to set exactly one of these environment variables matching their provider:
- Anthropic: `ANTHROPIC_API_KEY`
- OpenAI: `OPENAI_API_KEY`
- Google Gemini: `GEMINI_API_KEY`
- DeepSeek: `DEEPSEEK_API_KEY`

Never print, log, or write the API key value anywhere. Only confirm that the variable is set and is not empty.

Verify the connection by running a small non-interactive check (replace `<provider/id>` with the provider and model identifier you connected in this step, for example `openai/gpt-4o` or `anthropic/claude-sonnet-4-5`):
```bash
pi -p "Say ready" --no-tools --model <provider/id>
```
Expected: The command returns ordinary text with no authentication error.
Verify: Confirm that the command outputs standard text such as "ready" and does not produce an authentication error.
STOP CONDITION: If there is a missing login or an authentication error of any kind, stop immediately. Do not guess a credential. Do not try a different provider without asking. Ask your human teammate to complete the `/login` command or set the correct environment variable.

4. Prepare the corpus.
Command:
```bash
cd code/studio-02/ && bash setup.sh
```
Expected: The script checks Node.js and pi, downloads the corpus PDF file (Mei et al. 2025, arXiv 2507.13334) if it is not present, converts it to `corpus/survey.txt` with `pdftotext`, writes `corpus/sections/section-01.txt` through `corpus/sections/section-NN.txt` (where NN represents the section number), and prints word and estimated token counts, plus which providers pi can use with no secret values printed.
Verify: Confirm that `corpus/survey.txt` exists and is not empty, and that the directory `corpus/sections/` contains more than one `section-NN.txt` file.
STOP CONDITION: If the corpus download fails because of no network access to the arXiv repository, or if `pdftotext` is missing, stop immediately. Ask your human teammate to either install `pdftotext` (part of the `poppler-utils` package) or manually place a long plain-text corpus at `corpus/survey.txt`.

5. Confirm the model choice for the graded runs.
Command:
Ask your human teammate which `--model <provider/id>` to use, or use the default documented in `code/studio-02/README.md` for the connected provider.
Run this command to check the model list:
```bash
pi --list-models
```
Expected: The command prints the available models.
Verify: Confirm that the requested model appears in the model list for the active provider.
STOP CONDITION: If the requested model is not found in the model catalog, stop immediately. Do not silently substitute a different model. Ask your human teammate to choose a different model, or run this command to refresh the catalog and check again:
```bash
pi update --models
```

6. Run Part A.
Command:
```bash
python3 part_a_stress.py --model <provider/id>
```
Expected: The script creates one result JSON file per corpus size under `evidence/part_a/`, plus `evidence/part_a/summary.md` with a table of size, input tokens, score out of five, and any wrong or missing question numbers, and a stated first size where the score dropped or the call errored.
Verify: Confirm that `evidence/part_a/summary.md` exists and names a first-failure size (or states that none was found).
STOP CONDITION: If every run in this step fails with the same authentication, quota, or rate-limit error, stop immediately. Do not keep retrying the same failing call. Ask your human teammate for help.

7. Run Part B.
Command:
```bash
python3 part_b_isolate_compress.py --model <provider/id>
```
Expected: The script creates one findings file per corpus section under `evidence/part_b/findings/`, a `evidence/part_b/summary-of-part-a.md` file, and `evidence/part_b/summary.md` comparing four scores (Part A best, isolate, summary-artifact, post-compaction) with token counts.
Verify: Confirm that `evidence/part_b/summary.md` exists and contains all four comparison numbers.
STOP CONDITION: If every run in this step fails with the same authentication, quota, or rate-limit error, stop immediately. Do not keep retrying the same failing call. Ask your human teammate for help.

8. Run Part C.
Command:
```bash
python3 part_c_memory.py --model <provider/id>
```
Expected: The script creates a `decisions.md` file with three dated entries after session 1 and at least one more after session 2, a session-three answer from the memory run and a separate session-three answer from a memoryless baseline run, and `evidence/part_c/summary.md` scoring each of the three decisions as recalled correctly, missing, or invented for both runs.
Verify: Confirm that `evidence/part_c/summary.md` states a recall result for all three decisions in both runs.
STOP CONDITION: If every run in this step fails with the same authentication, quota, or rate-limit error, stop immediately. Do not keep retrying the same failing call. Ask your human teammate for help.

9. Write the explanation.
Command (still from `code/studio-02/`; the starter files live two directories up, under `studio/studio-02/starter/`):
```bash
cp ../../studio/studio-02/starter/EXPLANATION_TEMPLATE.md evidence/EXPLANATION.md
```
Expected: The template file is copied to the evidence directory.
Verify: Confirm that `evidence/EXPLANATION.md` exists. Open `evidence/EXPLANATION.md` and fill in all six sections using only numbers and facts that appear in the `evidence/` files produced above. Do not estimate or recall numbers from earlier in the conversation; read them back from the files.
STOP CONDITION: None.

10. Fill in the evidence checklist.
Command (still from `code/studio-02/`):
```bash
cp ../../studio/studio-02/starter/evidence/README.md evidence/README.md
```
Expected: The template file is copied to the evidence directory.
Verify: Confirm that `evidence/README.md` exists. Fill in each field from the actual run outputs. Confirm that no field is left blank without a stated reason.
STOP CONDITION: None.

## General Stop Conditions
Apply these stop conditions at any step:
- Missing or incomplete login: stop immediately and ask your human teammate to log in.
- A quota-exhausted or rate-limit error from the provider: stop immediately and ask your human teammate before retrying. Do not loop.
- Corpus download failure: stop immediately and ask your human teammate, as described in Step 4.
- A model that pi cannot find in its catalog: stop immediately and ask your human teammate, as described in Step 5.
- Never commit API keys, `.env` files, or personal information to the repository.

## File Layout
The final repository layout must look like this:
```
code/studio-02/
  README.md
  setup.sh
  questions.json
  lib/pi_runner.py
  part_a_stress.py
  part_b_isolate_compress.py
  part_c_memory.py
  corpus/                   (created by setup.sh; not committed to the repository)
    survey.txt
    sections/section-01.txt ... section-NN.txt
  work/                      (created by the Part C script; temporary workspace; not committed to the repository)
    part_c/with-memory/
    part_c/no-memory/
  evidence/                  (created by the scripts; this is the folder to submit)
    part_a/summary.md, run-<size>.json
    part_b/findings/section-NN.md, summary-of-part-a.md, summary.md
    part_c/summary.md, decisions.md, session-3 answers
    sessions/                (raw pi session JSONL files, the run record)
    summary.md
    EXPLANATION.md
    README.md                (the completed evidence checklist)
```

## Evidence Schema Mapping
- Date of the runs, model name, harness name and version, corpus name and token size: `evidence/README.md`
- The five questions and gold answers: `code/studio-02/questions.json`
- Input and cached tokens per run, and where Part A went wrong: `evidence/part_a/summary.md`
- Sub-agent split and returned conclusions: `evidence/part_b/findings/*.md` and `evidence/part_b/summary.md`
- Summary artifact content and size: `evidence/part_b/summary-of-part-a.md`
- Memory file with dated entries, and session-three answers with and without memory: `evidence/part_c/`
- What remains unknown, and member contributions: `evidence/EXPLANATION.md`
