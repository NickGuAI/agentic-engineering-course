#!/usr/bin/env python3
"""Contract addendum v10, step 1: extend Part A to n=20 at 512K and 768K.

Runs the 20 new items benchmarks/extend_qa1_topend.py appended to
subset_qa1_topend.json (ids 21-30 = 512K, 31-40 = 768K) through pi, using
the EXACT same method as the existing 80 rows in evidence/part_a/:
single user message (the item's own baked-in prompt: INSTRUCTION + story +
question), compaction disabled via a per-item work-dir .pi/settings.json,
--no-tools --no-context-files --thinking low, model openai/gpt-5.6-luna.

Appends the 20 new rows to evidence/part_a/results.json + results.csv
without touching any of the 80 existing rows, then regenerates summary.md
and qa1_curve.png (plot_qa1_curve.py, data-driven) from the complete,
updated set. Budget is shared with part_b_grid.py via
evidence/grid_budget.json (lib/grid_budget.py) against the v10 $20.1
target / $24.00 hard stop.

Usage:
  python3 run_part_a_extend.py                # run all 20 new items
  python3 run_part_a_extend.py --dry-run       # plan + cost estimate only
  python3 run_part_a_extend.py --concurrency 6
"""
import argparse
import csv
import json
import re
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from lib.pi_runner import run_pi, write_json, write_text  # noqa: E402
from lib.grid_budget import GridBudget, BudgetExceeded, estimate_call_cost_usd  # noqa: E402

BASE = Path(__file__).resolve().parent
MODEL = "openai/gpt-5.6-luna"
THINKING = "low"
NEW_IDS = list(range(21, 31)) + list(range(31, 41))  # 512k: 21-30, 768k: 31-40
LEDGER_PATH = str(BASE / "evidence" / "grid_budget.json")

_ARTICLE_RE = re.compile(r"^(the|a|an)\s+", re.IGNORECASE)


def normalize_room(s: str) -> str:
    s = (s or "").strip()
    s = _ARTICLE_RE.sub("", s)
    s = re.sub(r"[^\w\s]", "", s)
    return s.strip().lower()


def extract_final_answer(answer_text: str) -> str:
    lines = [l.strip() for l in (answer_text or "").splitlines() if l.strip()]
    return lines[-1] if lines else ""


def prompt_tokens_from_usage(usage: dict) -> int:
    return (usage.get("input") or 0) + (usage.get("cacheRead") or 0) + (usage.get("cacheWrite") or 0)


_LENGTH_ERROR_RE = re.compile(r"context.?length|maximum context|too long|token limit", re.IGNORECASE)


class _ReplayResult:
    """Minimal stand-in for lib.pi_runner.RunResult, reconstructed from an
    already-saved raw_events_path jsonl file instead of re-invoking pi --
    used only to recover a completed call's answer/usage/cost without paying
    for it a second time (see parse_raw_jsonl / --recover)."""
    def __init__(self):
        self.ok = False
        self.answer_text = ""
        self.usage = {}
        self.total_cost_usd = 0.0
        self.error = None
        self.wall_time_s = 0.0


def parse_raw_jsonl(raw_path: Path) -> "_ReplayResult":
    """Re-parse a saved pi --mode json stdout capture exactly like
    lib.pi_runner.run_pi does, to recover a call's result without
    re-running it. Used by --recover after a bug in this script's own
    post-processing (NOT pi/the budget) dropped a completed batch's
    results before they were persisted -- see run_part_a_extend.py history."""
    result = _ReplayResult()
    stdout = raw_path.read_text(encoding="utf-8", errors="replace")
    events = []
    for line in stdout.splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            events.append(json.loads(line))
        except json.JSONDecodeError:
            continue
    assistant_ends = [e for e in events if e.get("type") == "message_end" and e.get("message", {}).get("role") == "assistant"]
    total_cost = 0.0
    last_usage = {}
    error_message = None
    for e in assistant_ends:
        msg = e.get("message", {})
        usage = msg.get("usage") or {}
        cost = usage.get("cost") or {}
        total_cost += cost.get("total", 0) or 0
        if usage:
            last_usage = usage
        if msg.get("stopReason") == "error":
            error_message = msg.get("errorMessage") or "pi reported an error stopReason"
    result.total_cost_usd = total_cost
    result.usage = last_usage
    if assistant_ends:
        last_msg = assistant_ends[-1].get("message", {})
        text_parts = [c.get("text", "") for c in last_msg.get("content", []) if c.get("type") == "text"]
        result.answer_text = "\n".join(t for t in text_parts if t)
    if error_message:
        result.error = error_message
        result.ok = False
    else:
        result.ok = bool(assistant_ends)
    return result


def build_record(item: dict, result) -> dict:
    idn = item["id"]
    raw_answer = extract_final_answer(result.answer_text) if result.ok else None
    correct = bool(raw_answer) and normalize_room(raw_answer) == normalize_room(item["target"])
    length_refusal = bool(result.error) and bool(_LENGTH_ERROR_RE.search(result.error))
    format_ok = result.ok and bool(raw_answer) and len(raw_answer) < 60
    real_input_tokens = prompt_tokens_from_usage(result.usage)
    return {
        "id": idn, "benchmark": "babilong", "task": "qa1", "bucket": item["bucket"],
        "real_input_tokens": real_input_tokens or item["real_tokens_estimate"],
        "output_tokens": result.usage.get("output"),
        "cost_usd": round(result.total_cost_usd, 6),
        "wall_time_s": round(result.wall_time_s, 2),
        "raw_answer": raw_answer,
        "error": result.error,
        "ok": result.ok,
        "length_refusal": length_refusal,
        "format_ok": format_ok,
        "correct": correct,
        "score": 1.0 if correct else 0.0,
        "target": item["target"],
        "needle_depth_tokens": item.get("needle_depth_tokens"),
    }


def run_one_item(budget: GridBudget, item: dict, work_root: Path, session_dir: Path, raw_dir: Path,
                  timeout: int):
    idn = item["id"]
    work_dir = work_root / f"item-{idn}"
    pi_settings_dir = work_dir / ".pi"
    pi_settings_dir.mkdir(parents=True, exist_ok=True)
    (pi_settings_dir / "settings.json").write_text(
        json.dumps({"compaction": {"enabled": False}}, indent=2), encoding="utf-8"
    )

    label = f"part_a_extend/item-{idn}-{item['bucket']}"
    input_tok_estimate = item["real_tokens_estimate"]
    rid = budget.check_before(label, input_tok_estimate, output_tokens_guess=150)
    try:
        result = run_pi(
            prompt=item["prompt"], cwd=str(work_dir), model=MODEL, no_tools=True,
            session_dir=str(session_dir), raw_events_path=str(raw_dir / f"item-{idn}.raw.jsonl"),
            timeout=timeout, approve=True, no_context_files=True, thinking=THINKING,
        )
    except Exception:
        budget.release(rid)
        raise
    budget.record(rid, label, result.total_cost_usd)
    return build_record(item, result)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--concurrency", type=int, default=6)
    ap.add_argument("--timeout", type=int, default=1800)
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--recover", action="store_true",
                     help="reconstruct records from already-saved raw jsonl files instead of calling pi again")
    args = ap.parse_args()

    subset_path = BASE / "benchmarks" / "subset_qa1_topend.json"
    all_items = json.loads(subset_path.read_text(encoding="utf-8"))
    by_id = {it["id"]: it for it in all_items}
    items = [by_id[idn] for idn in NEW_IDS]
    assert len(items) == 20, f"expected 20 new items, found {len(items)}"
    print(f"Loaded {len(items)} new items: 512k ids {NEW_IDS[:10]}, 768k ids {NEW_IDS[10:]}")

    if args.dry_run:
        total_est = 0.0
        for it in items:
            est = estimate_call_cost_usd(it["real_tokens_estimate"], 150)
            total_est += est
            print(f"  id={it['id']} bucket={it['bucket']} ~{it['real_tokens_estimate']:,} tok -> est ${est:.4f}")
        print(f"\nEstimated total: ${total_est:.4f}")
        return

    part_a_dir = BASE / "evidence" / "part_a"
    raw_dir = part_a_dir / "raw_topend_extend"
    raw_dir.mkdir(parents=True, exist_ok=True)
    work_root = BASE / "work" / "part_a_extend"
    session_dir = (BASE / "evidence" / "sessions").resolve()

    new_records = []
    errors = []

    if args.recover:
        # Reconstruct completed calls' answers/usage/cost from the raw
        # jsonl each already wrote, instead of re-invoking pi (a bug in
        # this script's own post-processing -- NOT the pi calls or the
        # budget guard -- dropped a completed batch before it was
        # persisted; see parse_raw_jsonl's docstring). No budget is spent.
        print("--recover: reconstructing records from evidence/part_a/raw_topend_extend/*.raw.jsonl, no pi calls.")
        for it in items:
            raw_path = raw_dir / f"item-{it['id']}.raw.jsonl"
            if not raw_path.exists():
                errors.append((it["id"], f"no raw file at {raw_path}"))
                print(f"  *** MISSING raw file for id={it['id']}: {raw_path} ***", file=sys.stderr)
                continue
            result = parse_raw_jsonl(raw_path)
            rec = build_record(it, result)
            new_records.append(rec)
            verdict = "correct" if rec["correct"] else ("ERROR" if not rec["ok"] else "WRONG")
            print(f"  id={rec['id']} bucket={rec['bucket']} verdict={verdict} "
                  f"answer={rec['raw_answer']!r} target={rec['target']!r} "
                  f"real_input_tokens={rec['real_input_tokens']} cost=${rec['cost_usd']:.4f}", flush=True)
    else:
        budget = GridBudget(LEDGER_PATH)
        print(f"Budget ledger: {LEDGER_PATH} (starting spend ${budget.spent:.4f} / target ${budget.target:.2f} / "
              f"hard stop ${budget.hard_stop:.2f})")

        with ThreadPoolExecutor(max_workers=args.concurrency) as ex:
            futures = {ex.submit(run_one_item, budget, it, work_root, session_dir, raw_dir, args.timeout): it
                       for it in items}
            for fut in as_completed(futures):
                it = futures[fut]
                try:
                    rec = fut.result()
                    new_records.append(rec)
                    verdict = "correct" if rec["correct"] else ("ERROR" if not rec["ok"] else "WRONG")
                    print(f"  id={rec['id']} bucket={rec['bucket']} verdict={verdict} "
                          f"answer={rec['raw_answer']!r} target={rec['target']!r} "
                          f"real_input_tokens={rec['real_input_tokens']} cost=${rec['cost_usd']:.4f}", flush=True)
                except BudgetExceeded as e:
                    errors.append((it["id"], str(e)))
                    print(f"  *** BUDGET GUARD TRIPPED for id={it['id']}: {e} ***", file=sys.stderr, flush=True)
                except Exception as e:
                    errors.append((it["id"], str(e)))
                    print(f"  *** ERROR for id={it['id']}: {e} ***", file=sys.stderr, flush=True)

    if errors:
        print(f"\n{len(errors)} item(s) failed to complete: {errors}", file=sys.stderr)

    # --- Append to results.json (never touch existing rows). "id" is scoped
    # to (bucket, id), not globally unique -- e.g. bucket 512k id 1 and
    # bucket 128k id 1 are different rows, matching the existing 80-row
    # convention (32k/128k/256k use one global 1-60 id counter; 512k/768k
    # use their own separate 1-20 counter from select_qa1_topend.py). ---
    results_path = part_a_dir / "results.json"
    existing = json.loads(results_path.read_text(encoding="utf-8"))
    existing_keys = {(r["bucket"], r["id"]) for r in existing}
    appended = [r for r in new_records if (r["bucket"], r["id"]) not in existing_keys]
    combined = existing + sorted(appended, key=lambda r: (r["bucket"], r["id"]))
    write_json(str(results_path), combined)
    print(f"\nAppended {len(appended)} rows to {results_path} (total now {len(combined)})")

    # --- Append to results.csv (same columns, same order, never touch existing rows) ---
    csv_path = part_a_dir / "results.csv"
    fieldnames = ["benchmark", "task", "bucket", "id", "real_input_tokens", "output_tokens", "cost_usd",
                  "wall_time_s", "raw_answer", "target", "score", "needle_depth_tokens", "error"]
    with csv_path.open("a", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        for r in sorted(appended, key=lambda r: (r["bucket"], r["id"])):
            writer.writerow({k: r.get(k, "") if r.get(k) is not None else "" for k in fieldnames})
    print(f"Appended {len(appended)} rows to {csv_path}")

    if not args.recover:
        snap = budget.snapshot()
        print(f"\nBudget after step 1: completed=${snap['completed_spend_usd']:.4f} "
              f"(target ${snap['target_usd']:.2f}, hard stop ${snap['hard_stop_usd']:.2f})")
    else:
        ledger = json.loads(Path(LEDGER_PATH).read_text(encoding="utf-8")) if Path(LEDGER_PATH).exists() else {}
        print(f"\n(--recover: no new spend. Ledger from the original run: "
              f"${ledger.get('total_spent_usd', 0):.4f})")

    if errors:
        sys.exit(1)


if __name__ == "__main__":
    main()
