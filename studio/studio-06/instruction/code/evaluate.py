#!/usr/bin/env python3
"""Package six reports and invoke the pinned, unmodified RACE evaluator."""

import argparse
import csv
import hashlib
import json
import math
import os
from pathlib import Path
import subprocess
import sys

REVISION = "f2735b5c3636759c22f9e936c0232de8bf545b67"
TASK_FILE = Path(__file__).resolve().parents[1] / "selected-tasks.jsonl"
MODES = ("single", "multi")
SCORE_FIELDS = ("comprehensiveness", "insight", "instruction_following", "readability", "overall_score")
SOURCE_FILES = (
    "deepresearch_bench_race.py",
    "utils/api.py",
    "utils/clean_article.py",
    "utils/score_calculator.py",
    "prompt/score_prompt_en.py",
    "data/criteria_data/criteria.jsonl",
    "data/test_data/cleaned_data/reference.jsonl",
)


def read_jsonl(path):
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def tasks():
    selected = read_jsonl(TASK_FILE)
    if [row["id"] for row in selected] != [99, 93, 100]:
        raise ValueError("The selected task IDs must be 99, 93, and 100, in that order.")
    return selected


def verify_benchmark(benchmark, selected):
    revision = subprocess.check_output(
        ["git", "-C", str(benchmark), "rev-parse", "HEAD"], text=True
    ).strip()
    if revision != REVISION:
        raise ValueError(f"Use DeepResearchBench revision {REVISION}.")
    changed = subprocess.run(
        ["git", "-C", str(benchmark), "diff", "--quiet", "HEAD", "--"], check=False
    )
    if changed.returncode:
        raise ValueError("The benchmark checkout has tracked changes. Use a clean checkout.")
    original = {row["id"]: row for row in read_jsonl(benchmark / "data/prompt_data/query.jsonl")}
    criteria = {row["prompt"] for row in read_jsonl(benchmark / "data/criteria_data/criteria.jsonl")}
    references = {row["prompt"] for row in read_jsonl(benchmark / "data/test_data/cleaned_data/reference.jsonl")}
    for row in selected:
        if row != original.get(row["id"]):
            raise ValueError(f"Task {row['id']} differs from the pinned upstream task.")
        if row["prompt"] not in criteria or row["prompt"] not in references:
            raise ValueError(f"Task {row['id']} has no matching criteria or reference.")
    return {name: digest(benchmark / name) for name in SOURCE_FILES}


def prepare(submission, output, selected):
    reports = {}
    for mode in MODES:
        reports[mode] = []
        for task in selected:
            path = submission / "reports" / mode / f"{task['id']}.md"
            article = path.read_text(encoding="utf-8")
            if not article.strip():
                raise ValueError(f"Report is empty: {path}")
            reports[mode].append({
                "id": task["id"], "prompt": task["prompt"],
                "language": "en", "article": article,
            })
    output.mkdir(parents=True, exist_ok=False)
    raw = output / "input"
    raw.mkdir()
    for mode, rows in reports.items():
        (raw / f"{mode}.jsonl").write_text(
            "".join(json.dumps(row, ensure_ascii=False) + "\n" for row in rows), encoding="utf-8"
        )
    (output / "queries.jsonl").write_bytes(TASK_FILE.read_bytes())


def evaluator_env():
    env = os.environ.copy()
    # Use the pinned evaluator's own defaults, without inherited local overrides.
    for name in ("MAX_OUTPUT_TOKENS", "LLM_HTTP_TIMEOUT", "LLM_CONCURRENCY", "OPENAI_BASE_URL"):
        env.pop(name, None)
    env.update({"LLM_BACKEND": "openai", "RACE_MODEL": "gpt-5.5", "CLEAN_MODEL": "gpt-5.6-luna"})
    return env


def run_mode(benchmark, output, mode):
    destination = output / mode
    destination.mkdir()
    command = [
        sys.executable, str(benchmark / "deepresearch_bench_race.py"), mode,
        "--only_en", "--query_file", str(output / "queries.jsonl"),
        "--raw_data_dir", str(output / "input"),
        "--cleaned_data_dir", str(output / "cleaned"),
        "--output_dir", str(destination),
    ]
    with (destination / "evaluator.log").open("w", encoding="utf-8") as log:
        result = subprocess.run(command, cwd=benchmark, env=evaluator_env(), stdout=log, stderr=subprocess.STDOUT)
    if result.returncode:
        raise RuntimeError(f"RACE failed for {mode}. Read {destination / 'evaluator.log'}.")
    return command


def summarize(output, selected):
    expected = {row["id"]: row for row in selected}
    scores = {}
    for mode in MODES:
        rows = read_jsonl(output / mode / "raw_results.jsonl")
        if len(rows) != len(expected) or {row.get("id") for row in rows} != set(expected):
            raise ValueError(f"RACE must return all three task IDs for {mode}. Read its evaluator.log.")
        scores[mode] = {}
        for row in rows:
            task_id = row["id"]
            if "error" in row or row.get("prompt") != expected[task_id]["prompt"]:
                raise ValueError(f"RACE returned an error or a different prompt for {mode}, task {task_id}.")
            for field in SCORE_FIELDS:
                score = row.get(field)
                if isinstance(score, bool) or not isinstance(score, (int, float)) or not math.isfinite(score) or not 0 <= score <= 1:
                    raise ValueError(f"RACE returned no valid {field} for {mode}, task {task_id}.")
            scores[mode][task_id] = row["overall_score"]
    with (output / "comparison.csv").open("w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(["task_id", "topic", "single", "multi", "multi_minus_single"])
        for row in selected:
            a, b = (scores[mode][row["id"]] for mode in MODES)
            writer.writerow([row["id"], row["topic"], f"{a:.6f}", f"{b:.6f}", f"{b-a:.6f}"])
        means = [sum(scores[mode].values()) / len(expected) for mode in MODES]
        writer.writerow(["mean", "All three tasks", f"{means[0]:.6f}", f"{means[1]:.6f}", f"{means[1]-means[0]:.6f}"])
    return scores


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--submission", type=Path, required=True)
    parser.add_argument("--benchmark", type=Path)
    parser.add_argument("--output", type=Path, help="Fresh result directory. Default: <submission>/eval/race-01.")
    action = parser.add_mutually_exclusive_group()
    action.add_argument("--prepare-only", action="store_true", help="Package reports without model calls.")
    action.add_argument("--summarize-only", action="store_true", help="Read existing native scores without model calls.")
    args = parser.parse_args()
    submission = args.submission.resolve()
    output = (args.output or submission / "eval/race-01").resolve()
    selected = tasks()
    if args.summarize_only:
        summarize(output, selected)
        print(f"Wrote {output / 'comparison.csv'}")
        return
    if args.prepare_only:
        prepare(submission, output, selected)
        print(f"Packaged six reports in {output / 'input'}. No model calls made.")
        return
    if not args.benchmark:
        parser.error("--benchmark is required for evaluation.")
    if not os.environ.get("OPENAI_API_KEY"):
        parser.error("Set OPENAI_API_KEY to your class key before evaluation.")
    benchmark = args.benchmark.resolve()
    source_hashes = verify_benchmark(benchmark, selected)
    prepare(submission, output, selected)
    receipt = {
        "benchmark_revision": REVISION, "source_sha256": source_hashes,
        "tasks": [row["id"] for row in selected], "judge_model": "gpt-5.5",
        "cleaner_model": "gpt-5.6-luna", "input_sha256": {
            mode: digest(output / "input" / f"{mode}.jsonl") for mode in MODES
        }, "commands": [], "status": "running",
    }
    receipt_file = output / "evaluation.json"
    try:
        for mode in MODES:
            receipt["commands"].append(run_mode(benchmark, output, mode))
        summarize(output, selected)
        receipt["status"] = "complete"
    except Exception:
        receipt["status"] = "incomplete"
        raise
    finally:
        receipt_file.write_text(json.dumps(receipt, indent=2) + "\n", encoding="utf-8")
    print(f"Six RACE scores verified. Read {output / 'comparison.csv'}.")


if __name__ == "__main__":
    main()
