"""Measure one defense against the same attacks and clean Slack tasks."""

import argparse

from .harness import add_arguments, build_pipeline, read_attacks, run_attacks, slack_suite, task_completion, trace_root, write_json
from .models import resolve_model


def summarize(rows, completed):
    return {
        "attack_success": sum(sum(row["runs"]) for row in rows),
        "attack_trials": sum(len(row["runs"]) for row in rows),
        "task_completion": completed,
        "attacks": rows,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    add_arguments(parser)
    parser.add_argument("--defense", required=True, help="Built-in name or defense/defense.py")
    parser.add_argument("--completion-tasks", nargs="+", help="Smoke test only: restrict clean completion tasks; omit for all 21")
    args = parser.parse_args()
    if args.model != "luna":
        parser.error("Defense checkpoint uses --model luna (a dated --model-id override is allowed)")
    suite = slack_suite()
    specs = read_attacks(args.attacks, suite)
    tasks = args.completion_tasks if args.completion_tasks is not None else list(suite.user_tasks)
    if len(tasks) != len(set(tasks)):
        parser.error("--completion-tasks contains duplicates")
    for task in tasks:
        suite.get_user_task_by_id(task)
    baseline_pipe, _ = build_pipeline(args.model, args.model_id)
    defended_pipe, name = build_pipeline(args.model, args.model_id, args.defense)
    logdir = trace_root(args)
    baseline_rows = run_attacks(suite, baseline_pipe, specs, args.runs, logdir / "baseline")
    defended_rows = run_attacks(suite, defended_pipe, specs, args.runs, logdir / "defended")
    baseline = summarize(baseline_rows, task_completion(suite, baseline_pipe, tasks, logdir / "baseline-clean"))
    defended = summarize(defended_rows, task_completion(suite, defended_pipe, tasks, logdir / "defended-clean"))
    if baseline["task_completion"] == 0:
        raise RuntimeError("Baseline completed zero clean tasks; completion_ratio is undefined. Inspect traces before rerunning.")
    write_json(args.out, {
        "target": {"model_alias": args.model, "model": resolve_model(args.model, args.model_id)},
        "defense": {"source": args.defense, "name": name},
        "completion_tasks": len(tasks), "baseline": baseline, "defended": defended,
        "completion_ratio": defended["task_completion"] / baseline["task_completion"],
    })


if __name__ == "__main__":
    main()
