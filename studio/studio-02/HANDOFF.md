# Run-of-Show: Context Window Stress Test & Memory Architecture
## Instructor & TA Guide for Session 2

This document provides the timeline, run-of-show, pre-session announcements, likely failure scenarios, deliverables, and grading guidelines for running the Studio 02 session live in class.

---

### Course and Session Information
* **Course:** COMS W4995-009 Agentic Engineering, Columbia University, Fall 2026.
* **Instructor:** Nick Gu.
* **Studio 02 Title:** "Context Window Stress Test & Memory Architecture"
* **Session 2 (This Studio):** Friday, September 18, 2026. Duration: 75 minutes.
* **Session 3 (Deadline):** Friday, September 25, 2026.
* **Submission Link:** Submit the team repository link on CourseWorks (https://courseworks2.columbia.edu/courses/251648) before the deadline.

---

### Pre-Session Announcements
Instruct students to complete these setup steps *before* the studio session to ensure a smooth start.

1. **System Prerequisites**:
   * Ensure Node.js >= 22.19.0 is installed on your machine.
   * Install the coding agent globally:
     ```bash
     npm install -g --ignore-scripts @earendil-works/pi-coding-agent
     ```
   * Verify the installation and check the agent version:
     ```bash
     pi --version
     ```
   * Ensure Python >= 3.9 is installed, then install Python requirements from the `code/studio-02/` directory:
     ```bash
     pip install -r requirements.txt
     ```

2. **Model Provider Setup** (Only these two paths are supported):
   * **Primary Path (OpenAI API Key)**: Set up the OpenAI API key environment variable in the active terminal:
     ```bash
     export OPENAI_API_KEY=your_actual_api_key_here
     ```
     The default model used is `openai/gpt-5.6-luna`.
   * **Alternative Path (ChatGPT Plus/Pro Login)**: Run the coding agent and log in:
     ```bash
     pi
     ```
     Inside the agent shell, run the `/login` command, choose `ChatGPT/Codex` as the provider, and run all Python scripts with the model flag set to:
     ```bash
     --model openai-codex/gpt-5.6-luna
     ```
   * **Security Warning**: Warn students to never print, log, or commit their API keys or authentication keys to any public or team repository. They must never manually edit the global configuration file at `~/.pi/agent/auth.json`.

3. **Run the Setup Script**:
   * Run the setup script from the `code/studio-02/` directory:
     ```bash
     bash setup.sh
     ```
     This script downloads the BABILong qa1 data from Hugging Face (`RMT-team/babilong`) for the requested buckets. Note that these files are large:
     * 256k bucket: ~103 MB
     * 512k bucket: ~205 MB
     * 1M bucket: ~401 MB
     *Running this before class is highly recommended to avoid network bottlenecks.*
   * **What `setup.sh` does**:
     * Verifies that Node.js, the agent, and Python >= 3.9 with required packages are installed.
     * Downloads the required raw dataset files (skipping any already present).
     * Builds the 768K bucket from the 1M data without model calls (truncating 1M items to 768,000 real tokens and keeping items where the supporting fact survives).
     * Samples `--n` items (default: 5) per bucket (256k, 512k, 768k) into `benchmarks/subset_qa1_topend.json`.
     * Applies a one-time global model-catalog override to `~/.pi/agent/models.json` raising the context window limit of `gpt-5.6-luna` to 1,050,000 tokens for both `openai` and `openai-codex` providers (needed for the 512K and 768K runs, since the agent's default catalog caps it at 272,000 input tokens).
     * Reports which model providers are ready to use.
     * *Note:* Students can run with the `--dry-run` flag to preview checks and downloads without modifying any configuration.

---

### Run of Show (75 Minutes)

#### **00 to 10 Minutes: Prerequisites & Setup**
* **Goal:** Verify that Node.js, Python, and the agent are correctly installed, and ensure `setup.sh` has run and the model provider is connected.
* **TA Actions:**
  * Walk around the room to troubleshoot environment variables, Node/Python paths, or global login failures.
  * Ensure students have run `bash setup.sh` and are ready to execute Part A.
* **Live Cue (Nick Gu):** *"Welcome to Studio 02. Today we are stress-testing context windows and evaluating file-based memory architectures. Please verify your environment, export your OpenAI API key or log in via the pi agent, and execute setup.sh in code/studio-02/ right now if you haven't already."*

#### **10 to 30 Minutes: Part A - Stress-Testing the Context Window**
* **Goal:** Run the BABILong qa1 stress test across 256K, 512K, and 768K token buckets to identify where performance degrades.
* **TA Actions:**
  * Help students experiencing rate limits, API key errors, or timeouts.
  * Ensure students are running the correct stress command:
    ```bash
    python3 part_a_stress.py --model <provider/id> [--buckets 256k,512k,768k] [--n 5]
    ```
  * Confirm that `plot_qa1_curve.py` is run to visualize the results, writing `qa1_curve.png` and updating the summary.
  * Ensure files are written to `evidence/part_a/results.json`, `results.csv`, and `summary.md`.
* **Live Cue (Nick Gu):** *"It is now minute 10. Let's begin Part A. Run your stress-testing script and observe where accuracy begins to drop as the context window grows. Once the runs finish, use plot_qa1_curve.py to generate your accuracy curve."*

#### **30 to 50 Minutes: Part B - Context Isolation & Targeted Summarization**
* **Goal:** Implement and compare the two architectural solutions (Isolate and Targeted summary) on the same items to reduce peak single-call context tokens and restore accuracy.
* **TA Actions:**
  * Explain the two mitigation designs:
    1. **Isolate:** Splits the story into ~96,000-token chunks, calls sub-agents, and uses a lead agent to resolve the final answer (taking the last chunk that reported a location).
    2. **Targeted Summary:** Summarizes chunks into ~200 tokens each while preserving locations, then answers from concatenated summaries.
  * Assist students in managing parallel agent calls using `--concurrency` (default: 4) and limiting spending using `--max-usd`.
  * Confirm files are written to `evidence/part_b/results.json`, `results.csv`, `summary.md`, and `comparison.png`.
* **Live Cue (Nick Gu):** *"We are at minute 30. Please transition to Part B. We will run context isolation and targeted summarization to see how capping the peak single-call context tokens helps maintain accuracy on the same items."*

#### **50 to 70 Minutes: Part C - Evaluating File-Based Persistent Memory**
* **Goal:** Run the persistent memory evaluation across three separate sequential agent sessions and compare it to a memoryless baseline.
* **TA Actions:**
  * Guide students to understand the directory structures in `work/part_c/with-memory/` (uses `AGENTS.md` instructing the agent to log decisions in `decisions.md`) and `work/part_c/no-memory/` (the memoryless baseline).
  * Ensure students execute:
    ```bash
    python3 part_c_memory.py --model <provider/id>
    ```
  * Troubleshooting: If a run fails or has corrupt state, direct students to pass the `--fresh` flag to wipe `work/part_c/` and restart the three sessions.
  * Ensure files are written to `evidence/part_c/decisions.md`, `fib.py`, `session3-with-memory-answer.md`, `session3-no-memory-answer.md`, `part_c.json`, and `summary.md`.
* **Live Cue (Nick Gu):** *"Minute 50. Let's move to Part C. Run the persistent memory experiment to explore how storing decisions in a persistent file enables agents to coordinate context across separate sessions, and compare it with the baseline."*

#### **70 to 75 Minutes: Review & Repository Submission**
* **Goal:** Verify all generated files, draft the student group's explanation in `EXPLANATION.md`, and submit the repository link on CourseWorks.
* **TA Actions:**
  * Remind students to double-check their `evidence/` directories for all required outputs.
  * Warn students against committing API keys or global agent configuration files.
  * Direct students to the root `EXPLANATION.md` template and verify they are filling in all six sections.
* **Live Cue (Nick Gu):** *"We are in the final 5 minutes of the session. Double-check your evidence folder, complete your EXPLANATION.md draft, commit your changes, and submit your repository link on CourseWorks before Session 3 next week."*

---

### Likely Failures and Fixes

| Failure Scenario | Root Cause | Resolution / Fix |
|:---|:---|:---|
| **`setup.sh` halts or errors on missing Node.js or `pi`** | Node.js is missing or version is < 22.19.0, or global agent is not installed. | Ensure Node.js >= 22.19.0 is installed. Install the global agent via `npm install -g --ignore-scripts @earendil-works/pi-coding-agent` and check version with `pi --version`. |
| **`setup.sh` indicates Python packages are missing** | Python environment is missing `tiktoken`, `huggingface_hub`, or `matplotlib`. | Run `pip install -r requirements.txt` inside the `code/studio-02/` directory. Ensure Python >= 3.9 is active. |
| **Model context window errors on large buckets (512K, 768K)** | Default agent model-catalog caps `gpt-5.6-luna` at 272,000 input tokens. | Run `bash setup.sh` completely. It applies a safe, idempotent one-time override to `~/.pi/agent/models.json` raising the limit to 1,050,000 tokens for both `openai` and `openai-codex` providers. |
| **Slow or failing dataset downloads from Hugging Face** | Large size of datasets (256k ~103 MB, 512k ~205 MB, 1M ~401 MB) over classroom Wi-Fi. | Advise students to run `setup.sh` before class, or narrow downloads using `bash setup.sh --buckets 256k` to save time. Note that setup.sh skips files already present. |
| **Rate limit or API key authentication errors** | Missing `OPENAI_API_KEY` in environment, or invalid subscription login. | Set the API key using `export OPENAI_API_KEY=your_actual_key`. For subscription users, run `pi`, run `/login`, select `ChatGPT/Codex`, and use `--model openai-codex/gpt-5.6-luna`. |
| **Out of budget or runaway API spending** | Running large context items concurrently or repeatedly can accumulate costs. | Students can use the `--max-usd N` flag to cap spending, or use `--dry-run` to verify costs first. They can also adjust concurrency using `--concurrency` (default: 4). |
| **Incomplete memory sessions in Part C** | Previous failed sessions left corrupt or partial state in `work/part_c/`. | Run `python3 part_c_memory.py --model <provider/id> --fresh` to completely wipe the working directory and safely restart the three sequential sessions. |

---

### Deliverables and Collection

* **Submission Format:** Cloned repository link submitted on CourseWorks (https://courseworks2.columbia.edu/courses/251648).
* **Deadline:** Before Session 3 on Friday, September 25, 2026.
* **Group Constraints:** Teams of up to three students. One submission per student group.
* **Required Files in the Submitted Repository:**
  * **Part A:**
    * `evidence/part_a/results.json`
    * `evidence/part_a/results.csv`
    * `evidence/part_a/summary.md`
    * `qa1_curve.png`
  * **Part B:**
    * `evidence/part_b/results.json`
    * `evidence/part_b/results.csv`
    * `evidence/part_b/summary.md`
    * `comparison.png`
  * **Part C:**
    * `evidence/part_c/decisions.md`
    * `evidence/part_c/fib.py`
    * `evidence/part_c/session3-with-memory-answer.md`
    * `evidence/part_c/session3-no-memory-answer.md`
    * `evidence/part_c/part_c.json`
    * `evidence/part_c/summary.md`
  * **Explanation Document:**
    * `EXPLANATION.md` at the root of the repository, completed using the provided six-section template:
      1. What we ran (exact commands, flags, and model provider ID)
      2. What degraded in Part A (the bucket where accuracy dropped, real numbers from evidence)
      3. What fixed it in Part B (Isolate, Targeted summary, or both; before/after scores and token counts)
      4. What memory got right/wrong in Part C (comparison of memory run vs. memoryless baseline)
      5. What remains unknown
      6. Who did what (Exactly one paragraph for each group member detailing individual contributions)

---

### Post-Class Grading Workflow

TAs must grade submissions out of 10 points total based on completion and explanation criteria:

1. **Completion (6 Points Total — 2 points each for Parts A, B, and C)**:
   * **Presence:** All expected output files are present in the submitted repository.
   * **Internal Consistency:** The results and token sizes recorded in the `evidence/` directory match the explanations and data presented in `EXPLANATION.md`.
   * **Reproducibility:** The exact same commands and model settings reproduce the results in the `evidence/` directory.

2. **Explanation (4 Points Total — 1 point per section)**:
   * **Part A Degradation (1 point):** Correct causal account of context window degradation at longer context lengths.
   * **Part B Explanation (1 point):** Correct attribution of the fix to the right operation (chunk-level isolation vs. targeted summarization).
   * **Part C Analysis (1 point):** Clear discussion of honest unknowns paired with a real comparison to the memoryless baseline.
   * **Individual Contributions (1 point):** A specific, individual contribution paragraph from every team member.

3. **TA Spot-Check Protocol**:
   * Select one team member from each student group at random.
   * The selected team member must be able to explain the details, commands, and results of a specific run from their submission.
   * This verifies authentic understanding and collaborative effort.

4. **Policy Escapes**:
   * TAs must flag any late submissions, missing files, or policy exceptions directly to Nick Gu for resolution rather than guessing or inventing a policy.
