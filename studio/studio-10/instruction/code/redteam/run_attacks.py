"""Run repeated attacks on a single target model."""

import argparse

from .harness import add_arguments, build_pipeline, read_attacks, run_attacks, slack_suite, stock_specs, trace_root, write_json
from .models import resolve_model


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    add_arguments(parser)
    parser.add_argument("--stock", action="store_true", help="Use five upstream stock templates on the supplied goal/task grid")
    args = parser.parse_args()
    suite = slack_suite()
    specs = read_attacks(args.attacks, suite)
    pipeline, _ = build_pipeline(args.model, args.model_id)
    if args.stock:
        specs = stock_specs(specs, suite, pipeline)
    rows = run_attacks(suite, pipeline, specs, args.runs, trace_root(args))
    write_json(args.out, {
        "target": {"model_alias": args.model, "model": resolve_model(args.model, args.model_id), "suite": "slack@v1.2"},
        "runs_per_attack": args.runs, "attacks": rows,
    })


if __name__ == "__main__":
    main()
