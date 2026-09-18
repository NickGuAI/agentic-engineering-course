# Course: COMS W4995-009 Agentic Engineering, Columbia University, Fall 2026
# Title: Studio 02: Context Window Stress Test & Memory Architecture
# Duration: 75 minutes
# Teams: up to 3 students per team

## Objective
This studio evaluates a coding agent past its useful context length to observe performance degradation. We then mitigate this using context isolation and targeted summarization to cap peak single-call context tokens. Finally, we implement persistent file-based memory across separate sessions and compare it to a memoryless baseline.

## Prerequisites
Ensure your machine meets the following environment prerequisites:
- **Node.js**: `>= 22.19` (required because the `pi` coding agent needs it)
- **Install `pi`**: `npm install -g @earendil-works/pi-coding-agent`
- **Python**: `>= 3.9`
- **GitHub CLI `gh`**: logged in via `gh auth login`

## Get your private repo
One team member runs `bash bootstrap.sh` from any directory. This script automatically clones the public course repository, creates a private copy named `agentic-engineering-private` under your own GitHub account (your public fork from Studio 01 is untouched), pushes it, and grants access to the instructor and TAs. Once done, that team member must add the other teammates as collaborators on GitHub under the repository's **Settings > Collaborators**.

## Connect a model
Configure your model access using one of these two supported paths:
1. **Primary**: Set `export OPENAI_API_KEY=...` and use model `openai/gpt-5.6-luna`.
2. **Alternative**: Run `pi`, execute `/login` inside it using a ChatGPT Plus/Pro account, and use model `openai-codex/gpt-5.6-luna`.

Do not use any other provider or path.

## Setup
Run the following commands from `studio/studio-02/instruction/code`:
```bash
cd studio/studio-02/instruction/code
pip install -r requirements.txt
bash setup.sh
```
This script downloads BABILong qa1 data (256k/512k/1M buckets, ~700 MB total), builds the 768K bucket, samples 5 items per bucket into a subset benchmark, overrides the agent configuration to raise the model's context window limit, and reports available model providers. Use `bash setup.sh --dry-run` to preview the plan without downloading or modifying settings.

## Part A, Part B, Part C

### Part A — Context Window Stress Test
Tests the model with one call per item at three context sizes (256K, 512K, 768K real input tokens) to observe where performance degrades. This illustrates how single-call attention dilutes as context size increases.
```bash
python3 part_a_stress.py --model openai/gpt-5.6-luna --team <team>
python3 plot_qa1_curve.py --team <team>
```
Writes: `summary.md`, `results.json`, `results.csv` (from `part_a_stress.py`) and `qa1_curve.png` (from `plot_qa1_curve.py`).

### Part B — Context Isolation and Targeted Summarization
Splits each long item into roughly 96K-token chunks and compares two mitigation strategies: Isolate (one sub-call per chunk, then a lead call over the short reports) and Targeted summary (one ~200-token summary per chunk, then one answer call over the summaries). This demonstrates how reducing peak single-call context tokens bypasses long-context degradation.
```bash
python3 part_b_isolate_compress.py --model openai/gpt-5.6-luna --team <team>
```
Writes: `summary.md`, `results.json`, `results.csv`, and `comparison.png`.

### Part C — File-Based Memory Architecture
Runs three separate `pi` sessions where the agent must keep a `decisions.md` memory file (per instructions in `part_c/AGENTS.md`); the third session must recall decisions from the first two. This demonstrates how file-based memory maintains architectural context across independent stateless runs, compared against a memoryless baseline.
```bash
python3 part_c_memory.py --model openai/gpt-5.6-luna --team <team>
```
Writes: `summary.md` and `results.json`.

*Note:* All part outputs land under `studio/studio-02/submission/<team>/evidence/part_a/`, `part_b/`, and `part_c/` respectively.

## Deliverable
Copy the `submission/_template/EXPLANATION.md` template into your team's submission folder and fill it in. Your document must contain exactly these six sections:
- What we ran
- What degraded in Part A
- What fixed it in Part B
- What memory got right/wrong in Part C
- What remains unknown
- Who did what

## Submit
One submission per team. Commit and push all changes to your team's private repository before Session 3, Friday, September 25, 2026. Paste your repository URL once on CourseWorks (https://courseworks2.columbia.edu/courses/251648) — later studios are collected from the same repository, so you only paste the URL once. Never commit API keys.

## Grading
Refer to `GRADING_RUBRIC.md` in the same folder; the 10 points are split 6 (completion, 2 per part) + 4 (explanation).
