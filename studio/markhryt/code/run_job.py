#!/usr/bin/env python3
"""AI news digest job: ingest -> summarize -> output.

Sources: Anthropic News, Anthropic Engineering, OpenAI News.

Examples
  python3 run_job.py                     # one run, summarize with Claude if credentials exist
  python3 run_job.py --no-llm            # one run, offline extractive summaries
  python3 run_job.py --dry-run           # list what would be ingested; write nothing
  python3 run_job.py --loop --interval 6h
  python3 run_job.py --sources openai-news --max-per-source 5 --force
"""

from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from newsdigest.config import DEFAULT_MODEL, DEFAULT_OUTPUT_DIR, SOURCES_BY_KEY  # noqa: E402
from newsdigest.job import RunOptions, parse_interval, run_loop, run_once, select_sources  # noqa: E402


def setup_logging(outputs_dir: Path, verbose: bool) -> None:
    fmt = "%(asctime)s %(levelname)-7s %(name)s: %(message)s"
    level = logging.DEBUG if verbose else logging.INFO
    handlers: list[logging.Handler] = [logging.StreamHandler(sys.stderr)]
    try:
        (outputs_dir / "logs").mkdir(parents=True, exist_ok=True)
        handlers.append(logging.FileHandler(outputs_dir / "logs" / "job.log", encoding="utf-8"))
    except OSError as e:
        print(f"warning: cannot open log file under {outputs_dir}: {e}", file=sys.stderr)
    logging.basicConfig(level=level, format=fmt, handlers=handlers)


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--loop", action="store_true", help="keep running every --interval (default: run once)")
    p.add_argument("--interval", default="6h", help="loop interval, e.g. 30m, 6h, 1d (default 6h)")
    p.add_argument("--max-runs", type=int, default=None, help="stop the loop after N runs")
    p.add_argument("--sources", default=None,
                   help="comma-separated subset of: " + ", ".join(SOURCES_BY_KEY))
    p.add_argument("--max-per-source", type=int, default=10, help="new articles per source per run (default 10)")
    p.add_argument("--model", default=None, help=f"Claude model id (default {DEFAULT_MODEL})")
    p.add_argument("--no-llm", action="store_true", help="offline extractive summaries; no API calls")
    p.add_argument("--force", action="store_true", help="ignore seen-state and re-summarize listed articles")
    p.add_argument("--dry-run", action="store_true", help="ingest listings only; no summaries, no files written")
    p.add_argument("--always-write", action="store_true", help="write a digest even when nothing is new")
    p.add_argument("--outputs-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    p.add_argument("-v", "--verbose", action="store_true")
    args = p.parse_args(argv)

    setup_logging(args.outputs_dir, args.verbose)
    opts = RunOptions(
        outputs_dir=args.outputs_dir, sources=select_sources(args.sources),
        max_per_source=args.max_per_source, no_llm=args.no_llm, force=args.force,
        dry_run=args.dry_run, always_write=args.always_write, model=args.model,
    )

    if args.loop:
        try:
            interval = parse_interval(args.interval)
        except ValueError as e:
            p.error(str(e))
        try:
            run_loop(opts, interval, max_runs=args.max_runs)
        except KeyboardInterrupt:
            logging.getLogger("run_job").info("stopped by user")
        return 0

    result = run_once(opts)
    print(f"status={result.status} new={sum(result.new.values())} summarized={result.summarized} "
          f"method={result.method or '-'} duration={result.duration_s}s")
    for n in result.notes:
        print(f"note: {n}")
    for k, v in result.source_errors.items():
        print(f"source error: {k}: {v}")
    if result.outputs:
        print(f"digest: {result.outputs['markdown']}")
    return 0 if result.status in ("ok", "ok-empty", "dry-run") else 2


if __name__ == "__main__":
    sys.exit(main())
