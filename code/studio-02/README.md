# Studio 02: Context Window Stress Test & Memory Architecture

Welcome to Studio 02 of COMS W4995-009 Agentic Engineering at Columbia University (Fall 2026), taught by Instructor Nick Gu. This studio, titled "Context Window Stress Test & Memory Architecture," is designed to explore the performance limits of large context windows and investigate agentic memory structures using the `pi` coding agent as the main harness. Active work takes place on Friday, September 18, 2026, with submissions due before the Session 3 deadline on Friday, September 25, 2026.

## Install pi

To install the `pi` coding agent, ensure you meet the following requirements:
*   **Node.js**: Version `>= 22.19.0` (required by `pi`).

Run the following command to install `pi` globally:
```bash
npm install -g --ignore-scripts @earendil-works/pi-coding-agent
```

Verify the installation by checking the version:
```bash
pi --version
```

Next, configure your Python environment. Ensure you have Python `>= 3.9` installed, and then install the required Python packages from the `code/studio-02/` directory:
```bash
pip install -r requirements.txt
```

## Provider Setup

There are only two supported paths for configuring model providers. Choose one of the following:

1.  **Primary (OpenAI API Key)**: Set your OpenAI API key in your environment:
    ```bash
    export OPENAI_API_KEY=your_actual_key_here
    ```
    The default model used by the scripts is `openai/gpt-5.6-luna` (which is each script's internal default).

2.  **Alternative (ChatGPT Plus/Pro Subscription Login)**:
    Run `pi` and execute `/login`. Select ChatGPT/Codex, and then supply `--model openai-codex/gpt-5.6-luna` when running the scripts.

**Important Security Practices**:
*   Never print, log, or commit your API key or any secrets.
*   Never manually edit the global authentication configuration file `~/.pi/agent/auth.json`.

## Setup

To prepare your environment and benchmark datasets, run the setup script from the `code/studio-02/` directory:

```bash
bash setup.sh [flags]
```

### Flags for `setup.sh`
*   `--buckets`: Comma-separated list of buckets to download and prepare (default: `256k,512k,1M`).
*   `--n`: Number of items per bucket to sample for the benchmark subset (default: `5`).
*   `--dry-run`: Runs all checks and prints proposed downloads/overrides without downloading data or writing files.

### The Six Steps of `setup.sh` (In Order)
1.  **Node.js and pi Installation Check**: Verifies that both Node.js and the `pi` CLI are installed. If either is missing, it displays installation instructions and exits.
2.  **Python Environment Check**: Confirms Python >= 3.9 is installed and checks for the required packages (`tiktoken`, `huggingface_hub`, and `matplotlib`). If they are not importable, it directs you to run `pip install -r requirements.txt`.
3.  **Hugging Face Dataset Download**: Downloads the BABILong qa1 dataset files for the specified buckets from `RMT-team/babilong`. It prints each file's size before downloading and skips files already present locally:
    *   `256k` bucket: ~103 MB
    *   `512k` bucket: ~205 MB
    *   `1M` bucket: ~401 MB
4.  **768K Bucket Generation and Sampling**: Builds the custom `768k` bucket from the downloaded `1M` data using no model calls. It truncates each 1M item to exactly 768,000 real tokens and retains only items where the supporting fact survives truncation. It then samples `--n` items per bucket (`256k`, `512k`, `768k`) and writes them into `benchmarks/subset_qa1_topend.json`. (This step requires the `512k` and `1M` downloads to be complete).
5.  **Model Catalog Context Window Override**: Applies a one-time, idempotent override to your global `~/.pi/agent/models.json` file. Since `pi`'s default catalog caps the input context window of `gpt-5.6-luna` at 272,000 tokens, this script raises the limit to 1,050,000 tokens under both the `openai` and `openai-codex` providers (allowing the 512K and 768K runs to fit). It backs up your current configuration, safely merges with existing custom settings (without deleting other models or providers), and prints the applied changes. Running the script again is safe and will report that no changes are needed.
6.  **Provider Verification**: Identifies and prints which model providers are configured and available to `pi` based on the presence of keys or active sessions (never prints actual keys or credential values).

---

## Script Reference

### `setup.sh`

Verifies prerequisites, downloads the core datasets, builds the 768K bucket, samples items, and overrides the global model catalog settings.

*   **Command**:
    ```bash
    bash setup.sh
    ```
*   **Optional Flags**:
    *   `--buckets`: Comma-separated list of buckets to download (default: `256k,512k,1M`).
    *   `--n`: Number of items per bucket to sample (default: `5`).
    *   `--dry-run`: Performs verification and simulation without writing or downloading.
*   **Writes**:
    *   `benchmarks/subset_qa1_topend.json`
    *   `~/.pi/agent/models.json` (modifies with backup of old file)

### `part_a_stress.py`

Performs a context window stress test by challenging the model to extract a single location needle from a large irrelevant text haystack using the BABILong qa1 dataset.

*   **Command**:
    ```bash
    python3 part_a_stress.py --model <provider/id> [--buckets BUCKETS] [--n N]
    ```
*   **Optional Flags**:
    *   `--model`: Provider and model ID (default: `openai/gpt-5.6-luna`).
    *   `--buckets`: Comma-separated buckets to stress test (default: `256k,512k,768k`).
    *   `--n`: Number of items per bucket to test (default: `5`).
    *   `--out`: Output directory (default: `evidence`).
    *   `--work-dir`: Scratch cwd for the `pi` process which holds `.pi/settings.json`.
    *   `--timeout`: Execution timeout.
    *   `--thinking`: Thinking configuration options.
*   **How it Works**:
    *   Reads `benchmarks/subset_qa1_topend.json` and evaluates the lowest `--n` items.
    *   Fires a single `pi` call per item containing the complete story text and the question.
    *   Runs with tools disabled and automatic history truncation or context management turned off.
    *   Scores answers via exact match against the gold room name (case, article, and punctuation insensitive).
*   **Writes**:
    *   `evidence/part_a/results.json`: Full structured output and evaluation state.
    *   `evidence/part_a/results.csv`: Flat tabular dataset of evaluation metrics.
    *   `evidence/part_a/summary.md`: A markdown summary table showing accuracy per bucket.

### `part_b_isolate_compress.py`

Addresses context degradation from Part A by demonstrating two context reduction techniques (Isolate and Targeted Summary) that cap peak context sizes.

*   **Command**:
    ```bash
    python3 part_b_isolate_compress.py --model <provider/id> [--buckets BUCKETS] [--n N] [--concurrency 4] [--max-usd N]
    ```
*   **Optional Flags**:
    *   `--model`: Provider and model ID (default: `openai/gpt-5.6-luna`).
    *   `--buckets`: Comma-separated buckets to run.
    *   `--n`: Number of items to run per bucket (default: `5`, matches items tested in Part A).
    *   `--out`: Output directory (default: `evidence`).
    *   `--concurrency`: Maximum concurrent `pi` calls allowed (default: `4`).
    *   `--max-usd`: Stops submitting new calls if the running total cost would exceed this limit (default: no limit).
    *   `--dry-run`: Prints the planned steps and cost estimates without making any model calls.
*   **How it Works**:
    *   Requires Part A to have run first (utilizes `evidence/part_a/results.json` for performance comparison).
    *   Operates on the exact same dataset items as Part A.
    *   **Isolate Method**: Splits the story into fixed ~96,000-token chunks. One `pi` sub-agent call evaluates each chunk and reports either the location sentence found or `NOT FOUND`. A lead `pi` call reviews only this sequence of short reports and answers by tracking the *last* known location (accounting for cases where a person relocates).
    *   **Targeted Summary Method**: Concatenates ~200-token summaries written for each ~96,000-token chunk (which are explicitly instructed to preserve location statements). The final answer is derived exclusively from this concatenated summary.
    *   **Key Metric**: Measures *Peak Single-Call Context* (the maximum input tokens any single call must handle), showcasing that splitting context is highly effective at preserving extraction quality.
    *   Concurrently executes up to `--concurrency` calls using a two-stage thread pool to avoid deadlocks.
*   **Writes**:
    *   `evidence/part_b/results.json`: Full evaluation results.
    *   `evidence/part_b/results.csv`: CSV table containing token metrics and exact matches.
    *   `evidence/part_b/summary.md`: A markdown table comparing conditions (Part A baseline vs. Isolate vs. Summary) with 95% confidence intervals.
    *   `evidence/part_b/comparison.png`: Accuracy comparison plot.

### `part_c_memory.py`

Tests file-based agentic memory across three separate sequential `pi` sessions compared against a memoryless baseline.

*   **Command**:
    ```bash
    python3 part_c_memory.py --model <provider/id> [--fresh]
    ```
*   **Optional Flags**:
    *   `--model`: Provider and model ID (default: `openai/gpt-5.6-luna`).
    *   `--out`: Output directory (default: `evidence`).
    *   `--timeout`: Execution timeout.
    *   `--fresh`: Wipes `work/part_c/` and restarts the three sessions from scratch (does not delete existing results in `evidence/`).
*   **How it Works**:
    *   **With-Memory Environment (`work/part_c/with-memory/`)**: Gets an `AGENTS.md` file instructing `pi` to read `decisions.md` before executing any task and append a dated entry whenever a decision is made.
    *   **Session 1**: `pi` plans a command-line note-taking tool. It must record three decisions (storage format, command name, and date format) with justifications in `decisions.md`.
    *   **Session 2**: Runs an unrelated task (writing `fib.py` to print the first 20 Fibonacci numbers) and appends at least one more decision.
    *   **Session 3**: Asks `pi`: "What did we decide in session 1 about the note-taking tool, and why?"
    *   **No-Memory Baseline (`work/part_c/no-memory/`)**: Runs the same Session 3 query inside a fresh directory without `AGENTS.md` or `decisions.md`.
    *   **Execution Isolation**: Uses the `--no-context-files` flag to avoid reading outside configuration files, and feeds the system-prompt instructions through `--append-system-prompt` with the current real date injected.
*   **Writes**:
    *   `evidence/part_c/decisions.md`
    *   `fib.py`
    *   `session3-with-memory-answer.md`
    *   `session3-no-memory-answer.md`
    *   `part_c.json` (An automatic accuracy assessment classifying decisions as correct, missing, or invented)
    *   `summary.md` (or `evidence/part_c/summary.md`)

### `plot_qa1_curve.py`

Regenerates performance visualization and summary tables based on the stress-test results from Part A.

*   **Command**:
    ```bash
    python3 plot_qa1_curve.py
    ```
*   **How it Works**:
    *   Reads `evidence/part_a/results.json`.
    *   Generates an accuracy vs. real-input-tokens chart. The chart features 95% Wald binomial confidence interval error bars and annotates the sample count `n` at each data point.
*   **Writes**:
    *   `evidence/part_a/summary.md`
    *   `qa1_curve.png`

### `benchmarks/prepare_qa1_topend.py`

Measures native BABILong dataset token lengths and builds the custom `768k` context bucket.

*   **Command**:
    ```bash
    python3 benchmarks/prepare_qa1_topend.py
    ```
*   **How it Works**:
    *   Calculates real-token sizes for items in the native `512k` and `1M` buckets.
    *   Truncates each item in the `1M` dataset to exactly 768,000 real tokens.
    *   Filters out items where the crucial location fact (the needle) is cut off, retaining only items where the supporting fact survives.
    *   Operates entirely locally with no external model API calls.
*   **Requires**:
    *   `benchmarks/babilong/data/qa1/512k.json`
    *   `benchmarks/babilong/data/qa1/1M.json`

### `benchmarks/select_qa1_topend.py`

Samples a standardized, seeded subset of items from the available buckets and prepares the final benchmark suite.

*   **Command**:
    ```bash
    python3 benchmarks/select_qa1_topend.py --n 5 --buckets 256k,512k,768k
    ```
*   **Flags**:
    *   `--n`: Number of items to sample per bucket (default: `5`).
    *   `--buckets`: Comma-separated buckets to sample (default: `256k,512k,768k`).
*   **How it Works**:
    *   Uses a fixed seed (`seed=7`) to ensure identical, reproducible sampling on repeated runs.
    *   Packages each sampled item with a sequential ID, raw story haystack, question, gold room target, person's name, needle depth in real tokens, source provenance, and a fully formed, ready-to-send prompt.
*   **Requires**:
    *   `benchmarks/babilong/data/qa1/256k.json`
    *   `benchmarks/babilong/data/qa1/512k.json`
    *   `benchmarks/qa1_768k_survivors.json` (generated by `prepare_qa1_topend.py`)

---

## Files in this Folder

*   `setup.sh`: Environment preparation and dataset setup shell script.
*   `part_a_stress.py`: Main stress test script for long-context retrieval evaluation.
*   `part_b_isolate_compress.py`: Implements and compares Isolate and Targeted Summary context methods.
*   `part_c_memory.py`: Evaluates file-based agentic memory across multiple sessions.
*   `plot_qa1_curve.py`: Generates the performance curve visualization for Part A results.
*   `requirements.txt`: Python package dependency configuration.
*   `benchmarks/prepare_qa1_topend.py`: Script to truncate and build the custom `768k` token dataset bucket.
*   `benchmarks/select_qa1_topend.py`: Seeded sampler script to create the standardized benchmark evaluation subset.
