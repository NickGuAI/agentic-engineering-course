# Session 2 Run-of-Show: Handoff Document

This document is for the instructor, Nick Gu, and the teaching assistants (TAs). It provides the schedule, instructions, and troubleshooting steps for Session 2.

## Course and Session Facts

* **Course:** COMS W4995-009 Agentic Engineering, Columbia University, Fall 2026.
* **Instructor:** Nick Gu.
* **Schedule:** Fridays, 1:10 to 3:40 p.m.
* **Location:** 303 Uris Hall.
* **Session 2 Date:** Friday, September 18, 2026 (this studio).
* **Session 3 Date:** Friday, September 25, 2026.
* **Studio 02 Title:** "Context Window Stress Test & Memory Architecture."
* **Duration:** 75 minutes.
* **Team Format:** Teams of up to three students.
* **Submissions:** One submission per team.
* **Harness:** The harness for this studio is pi, the open-source terminal coding agent (`@earendil-works/pi-coding-agent`). This replaces the "choose your harness" line in the student handout. All other details in the handout, such as the timeboxes, the corpus, and the recorded data, still apply.

---

## Pre-Session Announcements

Send these instructions to students before class. They must complete these steps before Session 2 starts:

1. **Install the pi tool:**
   Students must run the following command to install the agent. It requires Node.js version 22.19.0 or newer.
   ```bash
   npm install -g --ignore-scripts @earendil-works/pi-coding-agent
   ```
   **Expected result:** npm downloads and installs the pi package globally without any error messages.
   
   Students can verify the installation by running:
   ```bash
   pi --version
   ```
   **Expected result:** pi prints the installed version number of the pi agent.

2. **Complete the login step:**
   Students must log in before class. They can run `/login` inside the pi interface for one of Claude Pro or Claude Max, ChatGPT Plus or ChatGPT Pro (Codex), or GitHub Copilot. Alternatively, they can set one API key environment variable:
   * Anthropic: `ANTHROPIC_API_KEY`
   * OpenAI: `OPENAI_API_KEY`
   * Google Gemini: `GEMINI_API_KEY`
   * DeepSeek: `DEEPSEEK_API_KEY`
   
   Subscription logins require a web browser verification step. This step should not be left for the first minutes of class. The ChatGPT Plus student offer in the course prep guide (four free months, claim by October 31, 2026) covers the Codex login. The Google AI Pro student offer does not include Gemini API usage, so it does not help with the API-key path.

3. **Download and prepare the corpus:**
   Students must download the corpus in advance. They run the setup script from the `code/studio-02/` directory in their team repository. This prevents class time from being spent waiting on files to download and convert.
   ```bash
   bash setup.sh
   ```
   **Expected result:** The shell script downloads the default corpus paper, which is Mei et al. 2025, "A Survey of Context Engineering for Large Language Models," arXiv 2507.13334. The script then converts the PDF file into plain text, generates per-section files in the `corpus/` directory, and prints word and token counts.

---

## Run of Show (75 Minutes)

Teaching assistants should actively circulate throughout each of the five timeboxes to assist students.

### 1. Before You Start (0 to 10 minutes)
* **Goal:** Students confirm that the pi agent is installed, their login or API key works, and the corpus is present.
* **TA Actions:** Circulate to help any team that missed the pre-session announcement. Help them install the pi agent or complete their login on the spot.
* **Live Cue:** Nick Gu or a teaching assistant can run the following verification commands on a shared screen:
  ```bash
  pi --version
  ```
  **Expected result:** The screen displays the version of the pi agent.
  ```bash
  bash setup.sh
  ```
  **Expected result:** The screen displays the file counts, words, and tokens, or shows that the files are already prepared.

### 2. Part A: Stress Test (10 to 30 minutes)
* **Goal:** Teams test the agent against a growing context window to observe where answers degrade.
* **Student Command:** Teams run the stress test script from the `code/studio-02/` directory:
  ```bash
  python3 part_a_stress.py --model <provider/id>
  ```
  **Expected result:** The Python script runs the context stress test with the chosen model identifier. It saves individual run output files for each context size under the `part_a/` folder and generates a table in `part_a/summary.md` showing input tokens, scores, and failure details.
* **TA Actions:** Watch for authentication, quota, or model-not-found errors. Help teams identify what "first failure at <size>" means in their `part_a/summary.md` table.
* **Live Cue:** Show a real run of `part_a_stress.py` on the shared screen and point to the printed summary table. If the live run is slow, or the Codex quota is exhausted, show the recorded run instead: `code/studio-02/evidence/part_a/summary.md`, and later `part_b/summary.md` and `part_c/summary.md` in the same folder.

### 3. Part B: Isolate and Compress (30 to 50 minutes)
* **Goal:** Teams apply isolation (using sub-agents) and compression (summaries and automatic compaction) to resolve the Part A failures.
* **Student Command:** Teams run the isolation and compression script:
  ```bash
  python3 part_b_isolate_compress.py --model <provider/id>
  ```
  **Expected result:** The Python script executes the isolation and compression strategies. It creates findings files from sub-agent runs, runs automatic context compaction, and generates `part_b/summary.md` comparing the token usage and test scores of the isolate, summary-artifact, and post-compaction approaches against Part A.
* **TA Actions:** Confirm that teams understand the difference between the isolate score, the summary-artifact score, and the post-compaction score in `part_b/summary.md`.
* **Live Cue:** Show one sub-agent findings file and the lead process combined answer on the shared screen. Explain that the isolation contract expects one section of text as input and a short list of findings as output, never a full transcript.

### 4. Part C: Remember (50 to 70 minutes)
* **Goal:** Teams run a multi-session simulation to test persistent memory versus a memoryless baseline.
* **Student Command:** Teams run the memory script:
  ```bash
  python3 part_c_memory.py --model <provider/id>
  ```
  **Expected result:** The Python script executes three consecutive simulated agent sessions in order. It records dated entries of decisions in `decisions.md` and generates two final answers for session three (one incorporating the memory file and one as a memoryless baseline) in the `part_c/` folder.
* **TA Actions:** Verify that the three sessions ran in chronological order and that the file `decisions.md` has dated entries. A common student mistake is running session three before sessions one and two have finished writing to the file.
* **Live Cue:** Show the `decisions.md` file after session two, and display the two session-three answers (with memory versus the memoryless baseline) side by side on the shared screen.

### 5. Submit (70 to 75 minutes)
* **Goal:** Teams submit their completed work.
* **TA Actions:** Remind teams to push their entire evidence folder, including the `EXPLANATION.md` file, to GitHub. Remind them to submit their repository link on CourseWorks before Session 3 on September 25, 2026. Confirm that each team has exactly one submission link.

---

## Likely Failures and Fixes

| Failure | Fix |
|---|---|
| **Headless or remote login:** The browser callback page cannot load on the remote machine. | Paste the final redirect URL into the pi login prompt when requested. If that fails, switch the team to an API key for the class session. |
| **Quota exhausted:** The subscription or API key hits its limit during the studio session. | Do not wait. Switch immediately to another provider path, such as a teammate's login or a different API key. Instruct the team to note this switch in their evidence files. |
| **Model not found:** The model identifier passed to the `--model` parameter does not match any entry in the catalog. | Run the update command to refresh the local catalog: <br><br> `pi update --models` <br><br> **Expected result:** The local model catalog cache is updated. <br><br> For GitHub Copilot, students must also ensure the model is enabled first in the VS Code Copilot Chat model picker. |
| **`pdftotext` missing:** The corpus conversion step fails during `setup.sh`. | Install the poppler-utils package using the operating system package manager. Alternatively, manually place a plain-text version of the corpus at `corpus/survey.txt`. |
| **Windows compatibility issues:** The shell script fails to run. | The `setup.sh` script is a bash script. Windows students must use a bash-capable terminal like Git Bash or the WSL. The Python scripts do not depend on bash and run natively on Windows once the pi agent is installed and logged in. |

---

## Deliverables and Collection

TAs must collect exactly one GitHub repository link per team on CourseWorks before Session 3 on September 25, 2026. Keep an informal note of any team that did not finish all three parts during the live session so that grading can account for it.

---

## Post-Class Grading Workflow

TAs grade each team's evidence folder and `EXPLANATION.md` against `GRADING_RUBRIC.md` after the CourseWorks submissions are received. 

### Spot-Check Verification
To uphold the syllabus principle that student judgment is what matters and that students must be able to explain what they built and delivered, TAs must perform spot-checks. TAs choose one member from each team at random and ask them to explain one run from their evidence. For example, ask them why Part A failed where it did, or what the isolate sub-agents returned. A vague or unprepared answer should result in a lower completion or explanation score for that section at the discretion of the TA.
