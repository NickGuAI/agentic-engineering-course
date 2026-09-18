#!/usr/bin/env python3
"""Part A: Context Window Stress Test.

BABILong qa1 ("Where is PERSON?", the answer is a single room name buried in
a long, otherwise irrelevant story) at 256K, 512K, and 768K real input
tokens. One pi call per item, single-message delivery (the whole story plus
the question, no tools, compaction disabled), exact-match scoring against
the gold room name.

Reads benchmarks/subset_qa1_topend.json (written by
benchmarks/select_qa1_topend.py; see setup.sh), takes the lowest --n item
ids in each requested bucket, and asks pi one at a time.

Usage:
  python3 part_a_stress.py --model openai/gpt-5.6-luna --buckets 256k,512k,768k --n 5 --team <name>

Run from studio/studio-02/instruction/code/. Re-runnable: overwrites its own
part_a/results.json / results.csv / summary.md; never deletes anything else
under the evidence output directory.
"""
import argparse
import csv
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from lib.pi_runner import DEFAULT_MODEL, md_table, real_token_count, run_pi, write_json, write_text  # noqa: E402

BASE = Path(__file__).resolve().parent
BENCHMARKS = BASE / "benchmarks"
BUCKET_ORDER = ["256k", "512k", "768k"]

SUBMISSION_ROOT = Path(__file__).resolve().parent.parent.parent / "submission"
TEAM_NAME_RE = re.compile(r"^[A-Za-z0-9._-]{1,40}$")

_ARTICLE_RE = re.compile(r"^(the|a|an)\s+", re.IGNORECASE)


def resolve_team_and_out(team, out):
    """Shared --team/--out resolution (see part_a_stress.py, part_b_isolate_compress.py,
    part_c_memory.py, plot_qa1_curve.py -- kept identical in each script).

    Returns (out_dir, sessions_dir). Exits 2 with a one-line stderr message if
    neither --team nor --out is given, or if --team fails validation."""
    if team is not None and (team == "_template" or not TEAM_NAME_RE.match(team)):
        print(f"error: --team must match {TEAM_NAME_RE.pattern!r} and must not be '_template'", file=sys.stderr)
        sys.exit(2)
    if out:
        out_dir = Path(out)
    elif team:
        out_dir = SUBMISSION_ROOT / team / "evidence"
    else:
        print("error: pass --team <name> (writes to studio/studio-02/submission/<name>/evidence/) "
              "or --out <dir>", file=sys.stderr)
        sys.exit(2)
    sessions_dir = (BASE / "work" / "sessions" / (team or "default")).resolve()
    return out_dir, sessions_dir


def normalize_room(s: str) -> str:
    s = (s or "").strip()
    s = _ARTICLE_RE.sub("", s)
    s = re.sub(r"[^\w\s]", "", s)
    return s.strip().lower()


def extract_final_answer(answer_text: str) -> str:
    """Last non-empty line of the reply -- robust to a stray leading line of
    reasoning despite --thinking low."""
    lines = [l.strip() for l in (answer_text or "").splitlines() if l.strip()]
    return lines[-1] if lines else ""


def score_babilong(answer_text: str, target: str) -> dict:
    raw = extract_final_answer(answer_text)
    correct = bool(raw) and normalize_room(raw) == normalize_room(target)
    return {"raw_answer": raw, "correct": correct}


def load_items(buckets, n):
    """Load benchmarks/subset_qa1_topend.json, keep only the requested
    buckets, and take the lowest n ids in each (deterministic; never chosen
    by correctness)."""
    subset_path = BENCHMARKS / "subset_qa1_topend.json"
    if not subset_path.exists():
        print(f"ERROR: {subset_path} not found. Run: bash setup.sh", file=sys.stderr)
        sys.exit(1)
    all_items = json.loads(subset_path.read_text(encoding="utf-8"))
    by_bucket = {}
    for bucket in buckets:
        rows = sorted((it for it in all_items if it["bucket"] == bucket), key=lambda it: it["id"])
        by_bucket[bucket] = rows[:n]
    return by_bucket


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--model", default=DEFAULT_MODEL, help=f"provider/model-id (default: {DEFAULT_MODEL})")
    ap.add_argument("--buckets", default="256k,512k,768k", help="comma-separated buckets to test")
    ap.add_argument("--n", type=int, default=5, help="items per bucket (default: 5)")
    ap.add_argument("--team", default=None, help="team name; writes to studio/studio-02/submission/<name>/evidence/")
    ap.add_argument("--out", default=None,
                     help="output directory (overrides --team; default: derived from --team)")
    ap.add_argument("--work-dir", default="work/part_a", help="scratch cwd for the pi process (holds .pi/settings.json)")
    ap.add_argument("--timeout", type=int, default=1800)
    ap.add_argument("--thinking", default="low")
    args = ap.parse_args()

    out_dir, sessions_dir = resolve_team_and_out(args.team, args.out)

    buckets = [b.strip() for b in args.buckets.split(",") if b.strip()]
    items_by_bucket = load_items(buckets, args.n)

    # Scratch work dir with compaction disabled, so a real overflow (if a
    # haystack ever exceeds the model's real context window) surfaces as a
    # real API error instead of being silently summarized away.
    work_dir = Path(args.work_dir)
    pi_settings_dir = work_dir / ".pi"
    pi_settings_dir.mkdir(parents=True, exist_ok=True)
    (pi_settings_dir / "settings.json").write_text(
        json.dumps({"compaction": {"enabled": False}}, indent=2), encoding="utf-8"
    )

    part_a_dir = out_dir / "part_a"
    part_a_dir.mkdir(parents=True, exist_ok=True)
    raw_dir = part_a_dir / "raw"
    raw_dir.mkdir(parents=True, exist_ok=True)

    results = []
    for bucket in buckets:
        items = items_by_bucket.get(bucket, [])
        print(f"=== Part A: bucket={bucket}, {len(items)} item(s) ===", flush=True)
        for item in items:
            raw_path = str(raw_dir / f"{bucket}-item-{item['id']}.raw.jsonl")
            result = run_pi(
                prompt=item["prompt"],
                cwd=str(work_dir),
                model=args.model,
                no_tools=True,
                session_dir=str(sessions_dir),
                raw_events_path=raw_path,
                timeout=args.timeout,
                approve=True,
                no_context_files=True,
                thinking=args.thinking,
            )
            scoring = score_babilong(result.answer_text, item["target"]) if result.ok else {
                "raw_answer": None, "correct": False}
            record = {
                "bucket": bucket, "id": item["id"], "person": item.get("person"), "target": item["target"],
                "question": item["question"], "model": args.model,
                "ok": result.ok, "error": result.error, **scoring,
                "real_input_tokens": real_token_count(item["haystack"]),
                "usage": result.usage, "cost_usd": round(result.total_cost_usd, 6),
                "wall_time_s": round(result.wall_time_s, 2),
                "answer_text": result.answer_text,
            }
            results.append(record)
            verdict = "correct" if scoring.get("correct") else ("ERROR" if not result.ok else "WRONG")
            print(f"  id={item['id']}: {verdict} answer={scoring.get('raw_answer')!r} target={item['target']!r} "
                  f"real_input_tokens={record['real_input_tokens']:,} cost=${record['cost_usd']:.4f}", flush=True)

    if not results:
        print("No items were run.", file=sys.stderr)
        sys.exit(1)

    write_json(str(part_a_dir / "results.json"), results)

    csv_path = part_a_dir / "results.csv"
    fieldnames = ["bucket", "id", "person", "target", "raw_answer", "correct", "real_input_tokens", "cost_usd",
                  "wall_time_s", "ok", "error"]
    with csv_path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for r in results:
            writer.writerow({k: (r.get(k) if r.get(k) is not None else "") for k in fieldnames})

    # Per-bucket accuracy table.
    rows = []
    for bucket in buckets:
        rows_b = [r for r in results if r["bucket"] == bucket]
        if not rows_b:
            continue
        n_correct = sum(1 for r in rows_b if r["correct"])
        mean_tokens = round(sum(r["real_input_tokens"] for r in rows_b) / len(rows_b))
        total_cost = sum(r["cost_usd"] for r in rows_b)
        rows.append([bucket, f"{n_correct}/{len(rows_b)}", f"{n_correct / len(rows_b) * 100:.0f}%",
                     f"{mean_tokens:,}", f"${total_cost:.4f}"])
    table_md = md_table(["bucket", "correct/n", "accuracy", "mean real input tokens", "total cost"], rows)

    lines = [
        "# Part A: Context Window Stress Test -- summary", "",
        f"Model: `{args.model}`, thinking `{args.thinking}`, single-message delivery, compaction disabled, "
        "exact-match scoring against the gold room name.", "",
        table_md, "",
        "Per-item answers, targets, and costs are in results.csv.", "",
    ]
    write_text(str(part_a_dir / "summary.md"), "\n".join(lines))

    print("\n" + table_md)
    print(f"\nWrote {part_a_dir / 'results.json'}, results.csv, and summary.md")


if __name__ == "__main__":
    main()
