#!/usr/bin/env python3
"""Summarize a completed Harbor 0.25.0 job with five trials per question.

pass@1 is the fraction of individual trials that passed. pass^5 is the
fraction of questions for which all five trials passed. Harbor's pass@5
means at least one success; it is a separate cross-check, not pass^5.
"""

import argparse
import hashlib
import json
import math
import re
import sys
from pathlib import Path
from uuid import UUID

RUNS = 5
CRITERIA = (
    "factual_accuracy",
    "citation_accuracy",
    "completeness",
    "source_quality",
    "tool_efficiency",
)


class InvalidJob(ValueError):
    """The job cannot support a complete five-run estimate."""


def require(condition, message):
    if not condition:
        raise InvalidJob(message)


def object_value(value, label):
    require(isinstance(value, dict), f"{label}: expected a JSON object")
    return value


def read_json(path):
    try:
        return object_value(json.loads(path.read_text(encoding="utf-8")), str(path))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise InvalidJob(f"Cannot read JSON from {path}: {type(exc).__name__}") from exc


def nonempty(value):
    return isinstance(value, str) and bool(value.strip())


def number(value):
    return type(value) in (int, float) and math.isfinite(value)


def uuid_string(value, label):
    try:
        require(isinstance(value, str), f"{label}: missing UUID")
        UUID(value)
    except ValueError as exc:
        raise InvalidJob(f"{label}: invalid UUID") from exc
    return value


def read_questions(path):
    """Use the full expected ID list so an absent question cannot disappear."""
    ids = []
    try:
        content = path.read_bytes()
        for line_number, line in enumerate(content.decode("utf-8").splitlines(), 1):
            if not line.strip():
                continue
            row = object_value(json.loads(line), f"questions line {line_number}")
            question_id = row.get("id")
            require(
                isinstance(question_id, str)
                and re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_-]*", question_id),
                f"questions line {line_number}: invalid id",
            )
            require(question_id not in ids, f"Duplicate question id: {question_id}")
            ids.append(question_id)
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise InvalidJob(f"Cannot read questions: {type(exc).__name__}") from exc
    require(ids, "Questions file is empty")
    return ids, hashlib.sha256(content).hexdigest()


def read_judge(trial_dir, question_id, reward):
    judge = read_json(trial_dir / "verifier" / "judge.json")
    label = trial_dir.name
    require(judge.get("status") == "ok", f"{label}: judge did not finish successfully")
    require(judge.get("question_id") == question_id, f"{label}: judge question_id mismatch")
    require(type(judge.get("pass")) is bool, f"{label}: judge pass must be boolean")
    require(int(judge["pass"]) == reward, f"{label}: judge and reward disagree")
    scores = object_value(judge.get("scores"), f"{label}: judge scores")
    require(set(scores) == set(CRITERIA), f"{label}: expected all five rubric scores")
    for criterion in CRITERIA:
        require(
            number(scores[criterion]) and 0 <= scores[criterion] <= 1,
            f"{label}: {criterion} must be a number in [0, 1]",
        )
    unscored = judge.get("unscored")
    require(
        isinstance(unscored, list)
        and all(isinstance(item, str) and item in CRITERIA for item in unscored)
        and len(set(unscored)) == len(unscored),
        f"{label}: unscored must list criterion names without duplicates",
    )
    if "tool_efficiency" in unscored:
        require(scores["tool_efficiency"] == 0.5, f"{label}: unscored tool efficiency must be 0.5")
    require(nonempty(judge.get("reason")), f"{label}: judge reason is missing")
    require(nonempty(judge.get("model")), f"{label}: judge model is missing")
    require(
        isinstance(judge.get("prompt_hash"), str)
        and re.fullmatch(r"[0-9a-f]{64}", judge["prompt_hash"]),
        f"{label}: judge prompt_hash must be a SHA-256 hex digest",
    )
    require(
        isinstance(judge.get("rubric_sha256"), str)
        and re.fullmatch(r"[0-9a-f]{64}", judge["rubric_sha256"]),
        f"{label}: judge rubric_sha256 must be a SHA-256 hex digest",
    )
    return judge


def pass_at_k(successes, k):
    """Harbor's unbiased at-least-one-success estimator, with n=5."""
    return sum(
        1 - math.comb(RUNS - count, k) / math.comb(RUNS, k)
        if RUNS - count >= k else 1.0
        for count in successes
    ) / len(successes)


def summarize(job_dir, questions_path, team):
    question_ids, questions_hash = read_questions(questions_path)
    expected_trials = RUNS * len(question_ids)
    job = read_json(job_dir / "result.json")
    job_id = uuid_string(job.get("id"), "Job id")
    require(nonempty(job.get("finished_at")), "Job is unfinished; wait for Harbor to complete")
    require(job.get("n_total_trials") == expected_trials, "Job trial total does not match five per question")
    stats = object_value(job.get("stats"), "Job stats")
    require(stats.get("n_completed_trials") == expected_trials, "Job has incomplete trials")
    for field in ("n_errored_trials", "n_running_trials", "n_pending_trials", "n_cancelled_trials", "n_retries"):
        require(type(stats.get(field)) is int and stats[field] == 0, f"Job {field} must be zero")
    result_paths = sorted(job_dir.glob("*/result.json"))
    require(len(result_paths) == expected_trials, "Expected exactly five trial result files per question")

    groups = {question_id: [] for question_id in question_ids}
    identities = set()
    names = set()
    task_identities = {}
    setup = None
    setup_fingerprint = None
    for result_path in result_paths:
        trial_dir = result_path.parent
        trial = read_json(result_path)
        label = trial_dir.name
        question_id = trial.get("task_name")
        require(question_id in groups, f"{label}: task is absent from questions file")
        trial_id = uuid_string(trial.get("id"), f"{label}: trial id")
        require(trial_id not in identities, f"{label}: duplicate trial id")
        identities.add(trial_id)
        require(trial.get("trial_name") == label, f"{label}: trial_name must match its directory")
        require(label not in names, f"{label}: duplicate trial name")
        names.add(label)
        require(nonempty(trial.get("finished_at")), f"{label}: trial is unfinished")
        require(trial.get("exception_info") is None, f"{label}: trial has an infrastructure error")
        require(not trial.get("step_results"), f"{label}: expected a single-step Studio task")
        require(not (trial_dir / "exception.txt").exists(), f"{label}: trial has exception.txt; inspect it")
        config = object_value(trial.get("config"), f"{label}: config")
        require(config.get("job_id") == job_id, f"{label}: trial belongs to another job")
        require(not config.get("install_only"), f"{label}: install-only run cannot be scored")
        require(config.get("source_trial") is None, f"{label}: use a fresh run, not regrading")
        agent_config = object_value(config.get("agent"), f"{label}: agent config")
        verifier_config = object_value(config.get("verifier"), f"{label}: verifier config")
        require(not verifier_config.get("disable"), f"{label}: verification was disabled")
        agent = object_value(trial.get("agent_info"), f"{label}: agent info")
        require(nonempty(agent.get("name")), f"{label}: agent name is missing")
        model_info = agent.get("model_info") or {}
        object_value(model_info, f"{label}: model info")
        # Compare all execution settings; exclude only the per-trial identity,
        # output location, and the task (which is compared within each question).
        stable_config = {
            key: value for key, value in config.items()
            if key not in {"trial_name", "trials_dir", "task", "job_id"}
        }
        fingerprint = json.dumps(
            {"config": stable_config, "agent": agent, "source": trial.get("source")},
            sort_keys=True, allow_nan=False,
        )
        require(setup_fingerprint in (None, fingerprint), f"{label}: mixed agent/model/execution setups")
        setup_fingerprint = fingerprint
        require(nonempty(trial.get("task_checksum")), f"{label}: task checksum is missing")
        task_identity = (trial["task_checksum"], json.dumps(config.get("task"), sort_keys=True))
        require(
            task_identities.get(question_id, task_identity) == task_identity,
            f"{label}: task changed between attempts",
        )
        task_identities[question_id] = task_identity
        verifier = object_value(trial.get("verifier_result"), f"{label}: verifier result")
        rewards = object_value(verifier.get("rewards"), f"{label}: rewards")
        require(len(rewards) == 1, f"{label}: expected one scalar reward")
        reward = next(iter(rewards.values()))
        require(number(reward) and reward in (0, 1), f"{label}: reward must be 0 or 1")
        require(not (trial_dir / "verifier" / "reward.json").exists(), f"{label}: use reward.txt only")
        try:
            reward_text = (trial_dir / "verifier" / "reward.txt").read_text(encoding="utf-8").strip()
        except (OSError, UnicodeError) as exc:
            raise InvalidJob(f"{label}: cannot read reward.txt") from exc
        require(reward_text == str(int(reward)), f"{label}: reward.txt disagrees with trial result")
        judge = read_judge(trial_dir, question_id, reward)
        if setup is None:
            setup = {
                "team": team,
                "agent": agent["name"],
                "agent_version": agent.get("version"),
                "model": model_info.get("name") or agent_config.get("model_name"),
                "model_provider": model_info.get("provider"),
                "judge_model": judge["model"],
                "rubric_sha256": judge["rubric_sha256"],
                "job_id": job_id,
                "job_name": job_dir.name,
                "configuration_sha256": hashlib.sha256(fingerprint.encode()).hexdigest(),
                "questions_sha256": questions_hash,
            }
        require(judge["model"] == setup["judge_model"], f"{label}: mixed judge models")
        require(judge["rubric_sha256"] == setup["rubric_sha256"], f"{label}: mixed judge rubrics")
        groups[question_id].append({
            "trial_id": label,
            "pass": judge["pass"],
            "scores": judge["scores"],
            "reason": judge["reason"],
            "unscored": judge["unscored"],
        })

    for question_id, runs in groups.items():
        require(len(runs) == RUNS, f"{question_id}: expected five trials, found {len(runs)}")
    successes = [sum(run["pass"] for run in runs) for runs in groups.values()]
    evals = object_value(stats.get("evals"), "Job evals")
    require(len(evals) == 1, "Expected one Harbor evaluation setup")
    evaluation = object_value(next(iter(evals.values())), "Harbor evaluation")
    require(evaluation.get("n_trials") == expected_trials, "Harbor eval trial count disagrees")
    require(evaluation.get("n_errors") == 0, "Harbor eval reports errors")
    harbor_metrics = object_value(evaluation.get("pass_at_k"), "Harbor pass_at_k")
    require(set(harbor_metrics) == {"2", "4", "5"}, "Expected Harbor pass@2, pass@4 and pass@5")
    for k, reported in harbor_metrics.items():
        require(
            number(reported) and math.isclose(reported, pass_at_k(successes, int(k)), abs_tol=1e-12),
            f"Harbor pass@{k} disagrees with the trial results",
        )
    return {
        "setup": setup,
        "runs_per_question": RUNS,
        "questions": [{"id": question_id, "runs": runs} for question_id, runs in groups.items()],
        "pass_1": sum(successes) / expected_trials,
        "pass_5": sum(count == RUNS for count in successes) / len(question_ids),
        "harbor_pass_at_k": harbor_metrics,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("job_dir", type=Path, help="Completed Harbor job directory")
    parser.add_argument("--questions", type=Path, required=True, help="Full questions.jsonl used for this job")
    parser.add_argument("--team", required=True, help="Your team directory name (recorded in setup)")
    parser.add_argument("--output", type=Path, default=Path("eval/results.json"))
    args = parser.parse_args()
    try:
        require(re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_-]*", args.team), "Invalid team directory name")
        result = summarize(args.job_dir, args.questions, args.team)
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(result, indent=2, allow_nan=False) + "\n", encoding="utf-8")
    except (InvalidJob, OSError, ValueError, TypeError) as exc:
        print(f"metrics: {exc}", file=sys.stderr)
        return 1
    print(f"pass@1 = {result['pass_1']:.3f}; pass^5 = {result['pass_5']:.3f}")
    print(f"Wrote {args.output}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
