# Studio 02: Context Window Stress Test & Memory Architecture

## Course Information
* **Course:** COMS W4995-009 Agentic Engineering, Columbia University, Fall 2026.
* **Instructor:** Nick Gu.
* **Session 2 (This Studio):** Friday, September 18, 2026.
* **Session 3 (Deadline):** Friday, September 25, 2026.
* **Studio Weight:** Studios represent 30% of the overall course grade.
* **Duration:** 75 minutes.
* **Format:** Teams of up to three students. One submission per team.

Our syllabus outlines a foundational principle:
> "your judgement is what matters. You can and will be encouraged to delegate your work to AI, but you must be able to explain what you built and delivered."

---

## Objective
The objective of this studio is to push a terminal-based AI coding agent past its useful context length to observe how performance degrades. You will mitigate this failure using **isolation** (delegating tasks to specialized sub-agents) and **compression** (using summary artifacts and the agent's built-in compaction). You will then build a persistent, plain-text memory mechanism that logs decisions across three distinct sessions, and compare its performance to a memoryless baseline.

By analyzing your empirical evidence, you will explain how memory and compaction counteract "context rot"—the phenomenon documented by Chroma Research in 2025 where model performance degrades as input length increases, even on simple, low-complexity tasks. Ultimately, you will demonstrate the key system design principle: "Store everything ≠ show everything."

The harness for this studio is `pi`, the open-source terminal coding agent. All other aspects of the studio, including the five timeboxes, the four lecture operations, and the corpus, remain identical to the original handout.

---

## Prerequisites
Please complete these configuration steps before the studio begins.

### 1. Verify Node.js
Ensure you have Node.js version 22.19.0 or newer. Check your installed version:
```bash
node --version
```
*Expected Result:* The terminal displays a version of `v22.19.0` or higher. Older versions will fail to install the agent.

### 2. Install the Coding Agent
Install the `pi` terminal coding agent globally using the npm:
```bash
npm install -g --ignore-scripts @earendil-works/pi-coding-agent
```
Verify the installation by printing the version number:
```bash
pi --version
```
*Expected Result:* The terminal displays the installed version number with no errors.

### 3. Connect a Model Provider
Connect `pi` to your chosen model provider. Choose **exactly one** of the following four paths:

*   **Claude Pro/Max Subscription:** Run `pi`, type `/login`, and select "Claude Pro/Max." Third-party tool usage draws from Anthropic's separate "extra usage" allowance billed per token.
*   **ChatGPT Plus/Pro (Codex):** Run `pi`, type `/login`, and choose "ChatGPT Plus/Pro (Codex)." OpenAI officially endorses this as "Codex for OSS". Eligible US students have four free months of ChatGPT Plus through the offer in the course prep guide (claim by October 31, 2026), and that subscription covers this login.
*   **GitHub Copilot:** Run `pi`, type `/login`, and select "GitHub Copilot." Verified students can get this free through the "GitHub Copilot Student" benefit in the GitHub Student Developer Pack. If a model is not available, enable it first in VS Code's Copilot Chat model picker.
*   **An API Key:** Set one provider environment variable, then launch `pi`:
    *   Anthropic: `export ANTHROPIC_API_KEY=your_key_here`
    *   OpenAI: `export OPENAI_API_KEY=your_key_here`
    *   Google Gemini: `export GEMINI_API_KEY=your_key_here`
    *   DeepSeek: `export DEEPSEEK_API_KEY=your_key_here`

*Note for headless machines:* Paste the terminal-provided URL back into the prompt if the browser cannot open.

### 4. Prepare the Corpus
Our evaluation text is Mei et al. 2025, "A Survey of Context Engineering for Large Language Models" (arXiv 2507.13334), which contains about 70,800 words (roughly 95,000 tokens). Download and split it under `code/studio-02/`:
```bash
cd code/studio-02/
bash setup.sh
```
*Expected Result:* The setup script downloads the paper, converts it to plain text, segments it into per-section files, and prints total counts. Do not commit these text files to your repository.

---

## The Five Timeboxes
*   **0 to 10 min:** Complete setup checklist.
*   **10 to 30 min:** Part A: Stress Test.
*   **30 to 50 min:** Part B: Isolate and Compress.
*   **50 to 70 min:** Part C: Remember.
*   **70 to 75 min:** Submit.

---

## Part A: Stress Test (10–30 Minutes)
From the `code/studio-02/` directory, run:
```bash
python3 part_a_stress.py --model <provider/id> [--sizes 8k,16k,32k,64k,full]
```
Replace `<provider/id>` with your chosen model identifier (e.g., `anthropic/claude-...` or `openai/gpt-...`). The default model is specified in `code/studio-02/README.md`.

This script feeds the coding agent increasingly larger segments of the corpus alongside five fixed questions, all within a single turn, with compaction disabled. You will observe the point where accuracy degrades or the API call fails.

*Expected Result:* The script saves results per size and writes a summary table to `part_a/summary.md` displaying input tokens, scores out of five, incorrect or missing questions, and the context length where degradation first occurred.

---

## Part B: Isolate and Compress (30–50 Minutes)
Run the mitigation script from the `code/studio-02/` directory:
```bash
python3 part_b_isolate_compress.py --model <provider/id>
```
This script demonstrates two solutions to the Part A failure, keeping the exact same five questions:
*   **Isolate:** A specialized sub-agent process of `pi` inspects a single section of the corpus and extracts key findings, returning no transcript. A lead process then answers the questions using only those findings.
*   **Compress:** Done in two distinct ways:
    *   (a) Re-asks the questions using only a short generated summary of what Part A found.
    *   (b) Re-runs the full corpus with `pi`'s automatic compaction enabled, which summarizes older content mid-run as the window fills up.

*Expected Result:* The script writes comparison scores and token counts to `part_b/summary.md`.

---

## Part C: Remember (50–70 Minutes)
Run the memory script from the `code/studio-02/` directory:
```bash
python3 part_c_memory.py --model <provider/id>
```
This script tests persistent memory by running three separate, sequential `pi` sessions in a directory with an `AGENTS.md` file that directs the agent to read and append to `decisions.md`:
*   **Session 1:** Agent makes and records three design decisions for a small note-taking utility.
*   **Session 2:** Agent completes unrelated work and appends at least one more decision.
*   **Session 3:** A new session with no active memory of the previous two is asked what Session 1 decided and why.

This is also run in a fresh directory with no memory file to serve as a baseline. The script scores each decision (recalled, missing, or invented) and writes `part_c/summary.md`. All run files are saved under `<out>/sessions/` (defaulting to `evidence/sessions/`).

*Expected Result:* The script writes a recall comparison in JSON format and a summary table to `part_c/summary.md`, then saves the session logs under `evidence/sessions/`.

---

## Data Collection
Track the following empirical data as you progress:
*   Date, model ID, and harness version (`pi --version`).
*   Corpus name and total token size.
*   The five evaluation questions and gold answers.
*   Input tokens and cached tokens used per run.
*   Input length where Part A performance degraded.
*   Sub-agent partitions and returned conclusions.
*   Summary artifact text and word count.
*   Dated memory file entries.
*   Session 3 answers with and without the memory file.
*   Unresolved unknowns and individual team member contributions.

---

## Deliverables
At the root of your `evidence/` folder, write `EXPLANATION.md` (start from the template at `studio/studio-02/starter/EXPLANATION_TEMPLATE.md` in the course repository) containing:
1.  **What we ran:** Harness, model, corpus, and exact commands.
2.  **Part A analysis:** Detailed degradation points, exact input lengths, and scores.
3.  **Part B mitigation:** Score and token comparisons of Isolate and Compress.
4.  **Part C comparison:** Decision recall with the memory file versus the memoryless baseline.
5.  **Open questions:** Unresolved behaviors or next tests.
6.  **Team contributions:** A personal statement (one paragraph) by each team member describing their specific role.

---

## Grading Criteria
The studio is worth 10 points per team:
*   **6 Points (Completion):** 2 points each for Part A, B, and C evidence, judged on whether it is present, consistent with your explanation, and reproducible from the commands you recorded.
*   **4 Points (Explanation), 1 point each:** a correct causal account of the Part A degradation; correct attribution of the Part B fix to the right operation; honest unknowns and a real baseline comparison in Part C; and a specific contribution paragraph from every member.

*Oral spot-checks:* Teaching Assistants (TAs) will randomly select one team member to explain a specific run, adhering to the syllabus principle that you must be able to explain what you built.

---

## Submission
1.  Push your complete `evidence/` folder (including `EXPLANATION.md`) to your GitHub repository.
2.  Submit the repository link on CourseWorks (https://courseworks2.columbia.edu/courses/251648) before Session 3 on September 25, 2026.
3.  Submit only one repository link per team. 
4.  **Security:** Never commit API keys, credentials, or personal information to any public repository.
