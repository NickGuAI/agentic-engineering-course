# COMS W4995-009 Agentic Engineering
## Columbia University, Fall 2026
### Studio 02: Context Window Stress Test & Memory Architecture

**Instructor:** Nick Gu  
**Session 2 (This Studio):** Friday, September 18, 2026 (Duration: 75 minutes)  
**Session 3 (Deadline):** Friday, September 25, 2026  

---

### Objective
In this studio, you will explore the physical limits of LLM context windows and investigate how agent architectures can overcome these constraints. You will stress-test a state-of-the-art model using extremely long contexts, evaluate two mitigation strategies (context isolation and targeted summarization) that cap peak single-call context, and analyze the performance of a file-based, persistent memory architecture across separate agent sessions.

---

### Prerequisites
Before running the studio scripts, ensure your local environment meets the following specifications:
- **Node.js:** version >= 22.19.0 (the minimum required version).
- **Python:** version >= 3.9.

#### Installation Commands
1. Install the coding agent globally:
   ```bash
   npm install -g --ignore-scripts @earendil-works/pi-coding-agent
   ```
2. Verify the installation and check the agent version:
   ```bash
   pi --version
   ```
3. Install the required Python packages (run this from `code/studio-02/`):
   ```bash
   pip install -r requirements.txt
   ```

---

### Connect a Model Provider
You can configure a model provider using one of the following two paths. Do not attempt to use any other paths.

1. **Primary Path (OpenAI API Key):**
   Set your OpenAI API key as an environment variable in your terminal session:
   ```bash
   export OPENAI_API_KEY=your_actual_api_key_here
   ```
   The scripts use the default model `openai/gpt-5.6-luna`.

2. **Alternative Path (ChatGPT Plus/Pro Login):**
   If you have a ChatGPT Plus or Pro subscription, run the following command to log in:
   ```bash
   pi
   ```
   Then execute the `/login` command inside the agent shell, select `ChatGPT/Codex` as the provider, and run your scripts with the model flag set to:
   ```bash
   --model openai-codex/gpt-5.6-luna
   ```

*Security Warning:* Never print, log, or commit an API key to any repository. Never manually edit the global authentication file located at `~/.pi/agent/auth.json`.

---

### The Setup Step: `setup.sh`
Before beginning the tasks, run the setup script from the `code/studio-02/` directory:
```bash
bash setup.sh [--buckets BUCKETS] [--n N] [--dry-run]
```

#### Flags
- `--buckets`: A comma-separated list of context window buckets to download (default: `256k,512k,1M`).
- `--n`: The number of items sampled per bucket for the subset benchmark file (default: 5).
- `--dry-run`: Performs all environment checks, prints the planned file downloads with their approximate sizes, and shows the model catalog overrides that would be applied, without modifying any system configuration or downloading files.

#### Order of Operations in `setup.sh`
1. **Tool Verification:** Checks that Node.js and the agent are installed, printing their active versions. If either is missing, it halts with installation instructions.
2. **Python Environment Verification:** Confirms Python >= 3.9 is present and verifies if the required libraries (`tiktoken`, `huggingface_hub`, and `matplotlib`) are importable. If they are not found, it prints the command `pip install -r requirements.txt` as the next steps.
3. **Data Download:** Downloads the BABILong qa1 data from the Hugging Face dataset `RMT-team/babilong` for the requested buckets. It prints each file's approximate size BEFORE downloading it and skips any file already present. Approximate download sizes:
   - 256k: ~103 MB
   - 512k: ~205 MB
   - 1M: ~401 MB
4. **Benchmark Construction:** Builds the 768K bucket from the 1M data without making any model calls (it truncates each 1M item to 768,000 real tokens and retains only items where the supporting fact survives truncation). It then samples `--n` items per bucket (256k, 512k, 768k) and writes them to `benchmarks/subset_qa1_topend.json`. (This step requires the 512K and 1M downloads to have completed).
5. **Model-Catalog Override:** Applies a one-time override to your global model-catalog file at `~/.pi/agent/models.json` (there is no per-project override file). The default model-catalog in the agent caps `gpt-5.6-luna` at 272,000 input tokens. Since our 512K and 768K runs exceed this, `setup.sh` raises the context window limit to 1,050,000 tokens for `gpt-5.6-luna` under BOTH the `openai` and `openai-codex` providers. It safely merges this override with any existing settings in `~/.pi/agent/models.json` without removing other models or providers, backing up the existing file first. This step is fully idempotent (subsequent runs will report that no change is needed).
6. **Model Provider Status:** Prints which model providers the agent can currently use, by presence only (it never prints the value of any key).

---

### Studio Timeboxes
Organize your 75-minute studio session using the following schedule:
- **00 to 10 minutes:** Prerequisites & Setup
- **10 to 30 minutes:** Part A - Stress-Testing the Context Window
- **30 to 50 minutes:** Part B - Context Isolation and Targeted Summarization
- **50 to 70 minutes:** Part C - Evaluating File-Based Persistent Memory
- **70 to 75 minutes:** Review and Repository Submission

---

### Part A: Context Window Stress Test
Evaluate the performance of the model under extremely large context lengths using the BABILong qa1 benchmark. In this benchmark, each item consists of a very long, otherwise irrelevant story containing one sentence stating where a specific person is, followed by the question "Where is PERSON?".

#### Execution Command
Run this command from `code/studio-02/` after completing `setup.sh`:
```bash
python3 part_a_stress.py --model <provider/id> [--buckets 256k,512k,768k] [--n 5]
```

#### Details
- Uses one agent call per item (the whole story and the question are delivered in a single message, with tools disabled and the agent's built-in message-management and reduction features turned off for this run).
- Performance is scored by exact match against the gold room name (insensitive to articles and punctuation).
- Tests context window buckets of 256K, 512K, and 768K real input tokens (the 768K bucket is constructed by `setup.sh` from the 1M data).

#### Outputs Written
- `evidence/part_a/results.json`
- `evidence/part_a/results.csv`
- `evidence/part_a/summary.md` (a per-bucket accuracy summary table)

#### Plotting Results
After completing Part A, you can run the following script to generate a visualization:
```bash
python3 plot_qa1_curve.py
```
This regenerates `evidence/part_a/summary.md` and outputs `qa1_curve.png` (a chart showing accuracy vs. real input tokens with 95% Wald binomial confidence interval error bars and the sample size annotated per point) using the data in `evidence/part_a/results.json`.

---

### Part B: Context Isolation and Targeted Summarization
Evaluate architectural strategies to mitigate long-context degradation on the same items evaluated in Part A.

#### Execution Command
Run this command from `code/studio-02/` after completing Part A:
```bash
python3 part_b_isolate_compress.py --model <provider/id> [--buckets BUCKETS] [--n 5] [--concurrency 4] [--max-usd N]
```

#### Details
- This script uses `evidence/part_a/results.json` for performance comparison and operates on the same items scored in Part A.
- To handle stories where characters are mentioned multiple times, the implementations are instructed to resolve the question using the last reported location.
- The script evaluates two architectural mitigations run for every item:
  1. **Isolate:** The story is split into fixed chunks of approximately 96,000 tokens. A sub-agent is called for each chunk to report whether it found the person's location (returning either the direct quoted sentence or `NOT FOUND`). Finally, a lead agent call reviews only these brief reports in order and answers, taking the last chunk that reported a location.
  2. **Targeted Summary:** The same chunks are processed, but each sub-agent call is directed to write a summary of its chunk (around 200 tokens) that is explicitly instructed to preserve any location statements. The lead agent then answers the question using only the concatenated summaries.
- **Key Metric:** Focuses on **PEAK single-call context** (the maximum tokens held in a single model call) rather than total tokens. Chunking reduces the peak context size by splitting the story up, though total tokens processed remain similar.
- **Concurrency:** Up to `--concurrency` parallel agent calls run at once (default is 4) using a safe two-stage thread pool to prevent deadlocks.
- **Budget Limit:** The optional `--max-usd N` (default: no limit) stops submitting new calls if the running cost would exceed the specified value in USD.
- **Dry Run:** Running with `--dry-run` prints the execution plan and cost estimates without making actual model calls.

#### Outputs Written
- `evidence/part_b/results.json`
- `evidence/part_b/results.csv`
- `evidence/part_b/summary.md` (a table comparing bucket and condition combinations with 95% confidence intervals)
- `evidence/part_b/comparison.png`

---

### Part C: File-Based Memory Architecture
Evaluate how persistent, file-based memory allows an agent to maintain architectural context across separate, independent tasks.

#### Execution Command
Run this command from `code/studio-02/`:
```bash
python3 part_c_memory.py --model <provider/id> [--fresh]
```

#### Details
- Tests file-based memory across three distinct sequential agent sessions inside the directory `work/part_c/with-memory/`.
- In the `with-memory` directory, an `AGENTS.md` file instructs the agent to read `decisions.md` before starting any task and to append a dated log entry whenever it makes an architectural decision.
- The three sessions are executed as follows:
  - **Session 1:** Plan a small command-line note-taking tool. The agent must record three specific decisions (the storage format, the command name, and the date format) along with the reasoning for each.
  - **Session 2:** Perform an unrelated coding task (writing `fib.py` to output the first 20 Fibonacci numbers) and record at least one more decision.
  - **Session 3:** Ask the agent: "What did we decide in session 1 about the note-taking tool, and why?"
- **Baseline:** The exact same Session 3 question is asked in a fresh, separate directory `work/part_c/no-memory/` that lacks `AGENTS.md` and `decisions.md` to serve as a memoryless baseline.
- **Technical reproduction details:** Every call in both conditions passes `--no-context-files` to ensure the agent never searches parent directories for unrelated agent rules, maintaining a clean comparison. The `with-memory` condition injects the same instructions via system prompt arguments, along with today's date for accurate logs.
- **Wipe & restart:** Passing the `--fresh` flag wipes `work/part_c/` and re-runs the entire three-session process. (The output folder `evidence/` is never deleted).

#### Outputs Written
- `evidence/part_c/decisions.md`
- `evidence/part_c/fib.py`
- `evidence/part_c/session3-with-memory-answer.md`
- `evidence/part_c/session3-no-memory-answer.md`
- `evidence/part_c/part_c.json` (auto-scored accuracy checks mapping correct, missing, or invented decisions)
- `evidence/part_c/summary.md`

---

### Data Collection
You must observe and record the following information during your runs:
- Today's date, the specific model ID used, and your harness version (obtained by running `pi --version`).
- The BABILong item IDs and buckets used (found in `benchmarks/subset_qa1_topend.json` and the results files).
- Total input tokens and, for Part B, the peak single-call context tokens for each run.
- The context window bucket where Part A's accuracy first drops.
- The exact reports returned by the Isolate sub-agents for each chunk, and the lead agent's final decision.
- The targeted-summary text generated for each chunk.
- The dated `decisions.md` entries generated in Part C.
- The Session 3 answers with and without the persistent memory architecture.
- Any unresolved unknowns and each team member's individual contribution.

---

### Deliverables
Your primary deliverable is `EXPLANATION.md`. A pre-existing template is included in your cloned repository; do not alter its structural layout. It must contain the following six sections:
1. **What we ran:** Specify the exact commands, flags, and model provider ID used.
2. **What degraded in Part A:** Describe your performance observations at longer context lengths.
3. **What fixed it in Part B:** Document how context isolation and targeted summarization addressed the failures.
4. **What memory got right/wrong in Part C:** Document the performance of the persistent memory architecture compared to the baseline.
5. **What remains unknown:** List any unresolved questions or unexplained behaviors.
6. **Who did what:** Provide exactly one paragraph for each team member detailing their specific individual contribution.

---

### Grading Criteria
Each student team receives up to 10 points. The grade is divided into completion and explanation:

#### Completion (6 points total - 2 points per part for Parts A, B, and C)
- **Presence:** All expected output files are generated and present in the submitted repository.
- **Internal Consistency:** The results recorded in `evidence/` match the explanations and data presented in `EXPLANATION.md`.
- **Reproducibility:** The exact same commands and model settings can reproduce the results.

#### Explanation (4 points total - 1 point per section)
- **Part A Degradation (1 point):** A correct causal explanation of what caused the performance degradation at longer context windows.
- **Part B Operations (1 point):** A correct attribution of the fix to the specific underlying operation (chunk-level isolation vs targeted summarization).
- **Part C Analysis (1 point):** A clear discussion of honest unknowns paired with a real baseline comparison.
- **Individual Contributions (1 point):** A specific, individual contribution paragraph from every team member.

#### Verification Spot-Checks
TAs will spot-check repositories. One team member chosen at random must be able to explain the details and results of any specific run.

---

### Submission Instructions
- Teams can consist of up to three students.
- One submission is required from each team.
- Submit the link to your team's cloned repository on CourseWorks before Session 3 on Friday, September 25, 2026.
- CourseWorks Link: [https://courseworks2.columbia.edu/courses/251648](https://courseworks2.columbia.edu/courses/251648)
- **Security Check:** Ensure no API keys or local authentication configurations are committed to your repository.
