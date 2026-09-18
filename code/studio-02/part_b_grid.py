#!/usr/bin/env python3
"""Contract addendum v10, step 2/3: Isolate and Targeted summary on all 60
grid items (256K/512K/768K x n=20, the SAME ids Part A scored).

Chunking is by fixed COUNT per bucket -- 256K->3, 512K->6, 768K->8 -- which,
given each bucket's real token size, works out to fixed chunk SIZE ~= 96,000
tokens (this is exactly what the three 768K items already done under the old
part_b_isolate_compress.py used: 8 chunks x ~96K each -- see their reused
chunk records below, and evidence/part_b/summary.md). Compaction is NOT part
of this run (contract v10).

Reuses (does not re-run, does not re-charge) ids 11/12/13 at 768K: their full
isolate + targeted-summary records already exist in the pre-v10
evidence/part_b/results.json (backed up unchanged to
evidence/part_b/results_v9_pre_grid.json before this script overwrote
results.json). Every other item (57 of 60) is run fresh here.

Two-stage concurrent execution (contract: max 6 concurrent pi calls):
  Stage A: every per-chunk call for every (item, condition) not reused, all
           submitted to one ThreadPoolExecutor(max_workers<=6).
  Stage B: once an item's chunks are all in, its lead (isolate) / reask
           (summary) call -- also through a max_workers<=6 pool.
Two stages (rather than nesting item-level tasks inside the same pool) avoids
a pool deadlock: no worker ever blocks waiting on a sibling task competing
for the same fixed 6 slots.

Budget: shared with run_part_a_extend.py via evidence/grid_budget.json
(lib/grid_budget.py), same $20.1 target / $24.00 hard stop -- checked before
every call, thread-safe, accounting for calls already admitted but not yet
recorded (see grid_budget.py's docstring).

Usage:
  python3 part_b_grid.py --dry-run
  python3 part_b_grid.py --concurrency 6
"""
import argparse
import csv
import json
import re
import sys
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from lib.pi_runner import run_pi, write_json, write_text  # noqa: E402
from lib.grid_budget import GridBudget, BudgetExceeded, estimate_call_cost_usd  # noqa: E402
from part_b_isolate_compress import (  # noqa: E402
    ISOLATE_CHUNK_INSTRUCTIONS, ISOLATE_LEAD_TEMPLATE,
    SUMMARY_CHUNK_INSTRUCTIONS, SUMMARY_REASK_TEMPLATE,
    score_babilong, split_into_n_chunks, prompt_tokens_from_usage,
    lowest_256k_items, run_data_check,
)

BASE = Path(__file__).resolve().parent
BENCHMARKS = BASE / "benchmarks"
MODEL = "openai/gpt-5.6-luna"
THINKING = "low"
LEDGER_PATH = str(BASE / "evidence" / "grid_budget.json")

N_CHUNKS = {"256k": 3, "512k": 6, "768k": 8}
REUSED_768K_IDS = [11, 12, 13]  # already done under the old part_b run; not re-run, not re-charged
CHECKPOINT_PATH = BASE / "evidence" / "part_b" / "grid_checkpoint.json"


class CheckpointStore:
    """Thread-safe, disk-persisted cache of completed call results, keyed by
    a unique label. This run makes ~860 pi calls over several minutes; if the
    process is interrupted (timeout, crash) partway through, every already-
    PAID-FOR call's result would otherwise be lost and have to be re-run
    (real money spent twice). Loaded at startup; get() lets a task skip
    calling pi entirely for a label already recorded; set() persists
    immediately (small JSON, full rewrite -- one call's record is a few
    hundred bytes, so this stays cheap even at ~1000 entries)."""

    def __init__(self, path: Path):
        self.path = path
        self._lock = threading.Lock()
        if path.exists():
            self.data = json.loads(path.read_text(encoding="utf-8"))
        else:
            self.data = {}
            self._persist()

    def get(self, label: str):
        with self._lock:
            return self.data.get(label)

    def set(self, label: str, record: dict):
        with self._lock:
            self.data[label] = record
            self._persist()

    def _persist(self):
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(json.dumps(self.data), encoding="utf-8")


# ---------------------------------------------------------------------------
# Item loading -- same ids Part A scored in every bucket, chosen deterministically
# ---------------------------------------------------------------------------

def _load_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def load_512k_items(ids):
    """512K items reconstructed from babilong/data/qa1/512k.json via each
    subset_qa1_topend.json item's source.row_index (same cross-reference
    pattern part_b_isolate_compress.py's load_768k_items uses for 768K)."""
    topend = _load_json(BENCHMARKS / "subset_qa1_topend.json")
    by_id = {it["id"]: it for it in topend if it["bucket"] == "512k"}
    data = _load_json(BENCHMARKS / "babilong" / "data" / "qa1" / "512k.json")
    items = []
    for idn in ids:
        it = by_id[idn]
        row = data[it["source"]["row_index"]]
        m = re.search(r"Where is (\w+)", row["question"])
        person = m.group(1) if m else None
        items.append({
            "id": idn, "bucket": "512k", "person": person, "target": row["target"],
            "question": row["question"].strip(), "haystack": row["input"],
            "needle_depth_tokens": it.get("needle_depth_tokens"),
        })
    return items


def load_768k_items_grid(ids):
    topend = _load_json(BENCHMARKS / "subset_qa1_topend.json")
    by_id = {it["id"]: it for it in topend if it["bucket"] == "768k"}
    survivors = _load_json(BENCHMARKS / "qa1_768k_survivors.json")
    surv_by_rowidx = {s["row_index"]: s for s in survivors}
    items = []
    for idn in ids:
        it = by_id[idn]
        s = surv_by_rowidx[it["source"]["row_index"]]
        items.append({
            "id": idn, "bucket": "768k", "person": s["person"], "target": s["target"],
            "question": s["question"].strip(), "haystack": s["input_truncated"],
            "needle_depth_tokens": s["needle_depth_tokens"],
        })
    return items


def ids_for_bucket(bucket):
    if bucket == "256k":
        return list(range(41, 61))
    if bucket == "512k":
        return list(range(1, 11)) + list(range(21, 31))
    if bucket == "768k":
        return list(range(11, 21)) + list(range(31, 41))
    raise ValueError(bucket)


def load_all_items():
    items = {}
    for idn, it in zip(ids_for_bucket("256k"), lowest_256k_items(20)):
        items[("256k", idn)] = it
    for it in load_512k_items(ids_for_bucket("512k")):
        items[("512k", it["id"])] = it
    for it in load_768k_items_grid(ids_for_bucket("768k")):
        items[("768k", it["id"])] = it
    return items


def load_part_a_by_bucket_id():
    results = _load_json(BASE / "evidence" / "part_a" / "results.json")
    return {(r["bucket"], r["id"]): r for r in results}


# ---------------------------------------------------------------------------
# pi call wrapper: check_before -> run_pi -> record, against the shared ledger
# ---------------------------------------------------------------------------

def call_pi(budget: GridBudget, label: str, prompt: str, output_tokens_guess: int, **kwargs):
    from lib.pi_runner import real_token_count
    input_tok_estimate = real_token_count(prompt)
    rid = budget.check_before(label, input_tok_estimate, output_tokens_guess)
    try:
        result = run_pi(prompt=prompt, model=MODEL, thinking=THINKING, **kwargs)
    except Exception:
        budget.release(rid)
        raise
    budget.record(rid, label, result.total_cost_usd)
    return result


# ---------------------------------------------------------------------------
# Stage A: chunk-level calls (isolate reports / summary chunk-summaries)
# ---------------------------------------------------------------------------

def make_chunk_task(budget, checkpoint, condition, item, chunk_idx, chunk_text, work_root, session_dir, raw_dir,
                     timeout):
    person = item["person"]
    if condition == "isolate":
        prompt = f"{chunk_text}\n\n{ISOLATE_CHUNK_INSTRUCTIONS.format(person=person)}\n"
        out_guess = 60
    else:
        prompt = f"{chunk_text}\n\n{SUMMARY_CHUNK_INSTRUCTIONS}\n"
        out_guess = 250
    label = f"{condition}/{item['bucket']}-item-{item['id']}/chunk-{chunk_idx:02d}"
    cwd = work_root / f"{item['bucket']}-item-{item['id']}" / f"chunk-{chunk_idx:02d}"
    raw_path = raw_dir / f"{condition}-{item['bucket']}-item-{item['id']}-chunk-{chunk_idx:02d}.raw.jsonl"

    def task():
        cached = checkpoint.get(label)
        if cached is not None:
            return cached
        result = call_pi(
            budget, label, prompt, out_guess,
            cwd=str(cwd), no_tools=True, session_dir=str(session_dir),
            raw_events_path=str(raw_path), timeout=timeout, approve=True, no_context_files=True,
        )
        text = result.answer_text.strip() if result.ok else f"[ERROR: {result.error}]"
        record = {
            "chunk": chunk_idx, "ok": result.ok, "error": result.error,
            "report" if condition == "isolate" else "summary": text,
            "input_tokens": prompt_tokens_from_usage(result.usage), "output_tokens": result.usage.get("output"),
            "cost_usd": round(result.total_cost_usd, 6),
        }
        checkpoint.set(label, record)
        return record
    return task


# ---------------------------------------------------------------------------
# Stage B: lead (isolate) / reask (summary) call
# ---------------------------------------------------------------------------

def make_lead_task(budget, checkpoint, condition, item, chunk_records, work_root, session_dir, raw_dir, timeout):
    person = item["person"]
    n = len(chunk_records)
    if condition == "isolate":
        reports = "\n\n".join(f"Chunk {c['chunk']}: {c['report']}" for c in chunk_records)
        prompt = ISOLATE_LEAD_TEMPLATE.format(n=n, reports=reports, person=person)
        out_guess = 30
        suffix = "lead"
    else:
        summaries = "\n\n".join(f"Chunk {c['chunk']} summary: {c['summary']}" for c in chunk_records)
        prompt = SUMMARY_REASK_TEMPLATE.format(n=n, summaries=summaries, person=person)
        out_guess = 30
        suffix = "reask"
    label = f"{condition}/{item['bucket']}-item-{item['id']}/{suffix}"
    cwd = work_root / f"{item['bucket']}-item-{item['id']}" / suffix
    raw_path = raw_dir / f"{condition}-{item['bucket']}-item-{item['id']}-{suffix}.raw.jsonl"

    def task():
        cached = checkpoint.get(label)
        if cached is not None:
            return cached
        result = call_pi(
            budget, label, prompt, out_guess,
            cwd=str(cwd), no_tools=True, session_dir=str(session_dir),
            raw_events_path=str(raw_path), timeout=timeout, approve=True, no_context_files=True,
        )
        scoring = score_babilong(result.answer_text, item["target"]) if result.ok else {
            "raw_answer": None, "correct": False, "score": 0.0}
        record = {
            "ok": result.ok, "error": result.error, "answer_text": result.answer_text, **scoring,
            "input_tokens": prompt_tokens_from_usage(result.usage), "output_tokens": result.usage.get("output"),
            "cost_usd": round(result.total_cost_usd, 6),
        }
        checkpoint.set(label, record)
        return record
    return task


def finalize_item(item, condition, chunk_records, lead_rec):
    chunk_in = [c["input_tokens"] or 0 for c in chunk_records]
    chunk_out = [c["output_tokens"] or 0 for c in chunk_records]
    lead_in = lead_rec["input_tokens"] or 0
    lead_out = lead_rec["output_tokens"] or 0
    total_tokens = sum(chunk_in) + sum(chunk_out) + lead_in + lead_out
    peak_context = max(chunk_in + [lead_in]) if chunk_in else lead_in
    cost = sum(c["cost_usd"] for c in chunk_records) + lead_rec["cost_usd"]
    key = "lead" if condition == "isolate" else "reask"
    return {
        "bucket": item["bucket"], "id": item["id"], "condition": condition, "person": item["person"],
        "target": item["target"], "n_chunks": len(chunk_records), "chunks": chunk_records,
        key: lead_rec, "correct": lead_rec["correct"], "raw_answer": lead_rec.get("raw_answer"),
        "total_tokens": total_tokens, "peak_context_tokens": peak_context, "cost_usd": round(cost, 6),
    }


def reused_record_from_old(old_results, condition, idn):
    """Reshape one already-done id-11/12/13 record from the pre-v10
    evidence/part_b/results.json (isolate/summary_compress schema) into this
    script's flat per-item record schema, unchanged data, no re-run."""
    section = "isolate" if condition == "isolate" else "summary_compress"
    rec = next(r for r in old_results[section]["items"] if r["id"] == idn)
    key = "lead" if condition == "isolate" else "reask"
    return {
        "bucket": "768k", "id": idn, "condition": condition, "person": rec["person"], "target": rec["target"],
        "n_chunks": rec["n_chunks"], "chunks": rec["chunks"], key: rec[key],
        "correct": rec[key]["correct"], "raw_answer": rec[key].get("raw_answer"),
        "total_tokens": rec["total_tokens"], "peak_context_tokens": rec["peak_context_tokens"],
        "cost_usd": rec["cost_usd"], "reused_from_pre_v10_run": True,
    }


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--concurrency", type=int, default=6)
    ap.add_argument("--timeout", type=int, default=900)
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()
    assert args.concurrency <= 6, "contract: max 6 concurrent"

    part_b_dir = BASE / "evidence" / "part_b"
    raw_dir = part_b_dir / "raw"
    raw_dir.mkdir(parents=True, exist_ok=True)
    work_root = BASE / "work" / "part_b_grid"
    session_dir = (BASE / "evidence" / "sessions").resolve()

    print("=== data check (mention counts) ===")
    data_check = run_data_check()
    print(data_check["finding"])

    all_items = load_all_items()
    print(f"\nLoaded {len(all_items)} items across 3 buckets (20 each).")

    if args.dry_run:
        from lib.pi_runner import real_token_count
        total_est = 0.0
        for (bucket, idn), item in sorted(all_items.items()):
            reused = bucket == "768k" and idn in REUSED_768K_IDS
            n_chunks = N_CHUNKS[bucket]
            per_chunk_tok = real_token_count(item["haystack"]) // n_chunks
            if reused:
                continue
            for condition, out_g in (("isolate", 60), ("summary", 250)):
                est = n_chunks * estimate_call_cost_usd(per_chunk_tok, out_g) + estimate_call_cost_usd(1500, 30)
                total_est += est
        print(f"Estimated total (excluding {len(REUSED_768K_IDS)} reused 768K items x2 conditions): "
              f"${total_est:.4f}")
        return

    budget = GridBudget(LEDGER_PATH)
    print(f"Budget ledger: {LEDGER_PATH} (starting spend ${budget.spent:.4f} / target ${budget.target:.2f} / "
          f"hard stop ${budget.hard_stop:.2f})")
    checkpoint = CheckpointStore(CHECKPOINT_PATH)
    print(f"Checkpoint: {CHECKPOINT_PATH} ({len(checkpoint.data)} calls already recorded from a prior partial run)")

    old_results = _load_json(part_b_dir / "results_v9_pre_grid.json")

    # Work list: every (bucket, id, condition) EXCEPT the 3 reused 768K ids.
    work = []
    for (bucket, idn), item in all_items.items():
        for condition in ("isolate", "summary"):
            if bucket == "768k" and idn in REUSED_768K_IDS:
                continue
            work.append((bucket, idn, condition, item))
    print(f"{len(work)} (item, condition) pairs to run fresh; "
          f"{len(REUSED_768K_IDS) * 2} reused from the pre-v10 run.")

    errors = []

    # --- Stage A: all chunk calls ---
    chunk_tasks = {}  # (bucket, id, condition) -> list of (chunk_idx, callable)
    for bucket, idn, condition, item in work:
        n_chunks = N_CHUNKS[bucket]
        chunks = split_into_n_chunks(item["haystack"], n_chunks)
        tasks = []
        for i, chunk_text in enumerate(chunks, start=1):
            t = make_chunk_task(budget, checkpoint, condition, item, i, chunk_text, work_root, session_dir, raw_dir,
                                 args.timeout)
            tasks.append(t)
        chunk_tasks[(bucket, idn, condition)] = tasks

    print(f"\n=== Stage A: {sum(len(v) for v in chunk_tasks.values())} chunk calls, "
          f"max {args.concurrency} concurrent ===")
    chunk_results = {k: [None] * len(v) for k, v in chunk_tasks.items()}
    with ThreadPoolExecutor(max_workers=args.concurrency) as ex:
        futures = {}
        for key, tasks in chunk_tasks.items():
            for i, t in enumerate(tasks):
                futures[ex.submit(t)] = (key, i)
        done = 0
        for fut in as_completed(futures):
            key, i = futures[fut]
            try:
                chunk_results[key][i] = fut.result()
            except BudgetExceeded as e:
                errors.append((key, str(e)))
                print(f"  *** BUDGET GUARD TRIPPED for {key} chunk {i+1}: {e} ***", file=sys.stderr, flush=True)
            except Exception as e:
                errors.append((key, str(e)))
                print(f"  *** ERROR for {key} chunk {i+1}: {e} ***", file=sys.stderr, flush=True)
            done += 1
            if done % 50 == 0 or done == len(futures):
                print(f"  ...{done}/{len(futures)} chunk calls done (spend so far "
                      f"${budget.snapshot()['completed_spend_usd']:.4f})", flush=True)

    # --- Stage B: lead / reask calls, only for items whose chunks all succeeded ---
    lead_tasks = {}
    skipped = []
    for key, results_list in chunk_results.items():
        bucket, idn, condition = key
        if any(r is None for r in results_list):
            skipped.append(key)
            continue
        item = all_items[(bucket, idn)]
        lead_tasks[key] = make_lead_task(budget, checkpoint, condition, item, results_list, work_root, session_dir,
                                          raw_dir, args.timeout)
    if skipped:
        print(f"\nSkipping lead/reask for {len(skipped)} items with failed chunk(s): {skipped}", file=sys.stderr)

    print(f"\n=== Stage B: {len(lead_tasks)} lead/reask calls, max {args.concurrency} concurrent ===")
    lead_results = {}
    with ThreadPoolExecutor(max_workers=args.concurrency) as ex:
        futures = {ex.submit(t): key for key, t in lead_tasks.items()}
        for fut in as_completed(futures):
            key = futures[fut]
            try:
                lead_results[key] = fut.result()
                bucket, idn, condition = key
                v = "correct" if lead_results[key]["correct"] else "WRONG"
                print(f"  {condition} {bucket} id={idn}: {v} answer={lead_results[key].get('raw_answer')!r}",
                      flush=True)
            except BudgetExceeded as e:
                errors.append((key, str(e)))
                print(f"  *** BUDGET GUARD TRIPPED for {key}: {e} ***", file=sys.stderr, flush=True)
            except Exception as e:
                errors.append((key, str(e)))
                print(f"  *** ERROR for {key}: {e} ***", file=sys.stderr, flush=True)

    # --- Assemble final per-item records ---
    final_items = []
    for key, lead_rec in lead_results.items():
        bucket, idn, condition = key
        item = all_items[(bucket, idn)]
        rec = finalize_item(item, condition, chunk_results[key], lead_rec)
        final_items.append(rec)
    for idn in REUSED_768K_IDS:
        for condition in ("isolate", "summary"):
            final_items.append(reused_record_from_old(old_results, condition, idn))

    part_a_by_key = load_part_a_by_bucket_id()
    for rec in final_items:
        pa = part_a_by_key.get((rec["bucket"], rec["id"]))
        rec["part_a_correct"] = pa.get("correct") if pa else None
        rec["part_a_real_input_tokens"] = pa.get("real_input_tokens") if pa else None
        rec["part_a_cost_usd"] = pa.get("cost_usd") if pa else None

    if errors:
        print(f"\n{len(errors)} (item,condition) pairs failed: {errors}", file=sys.stderr)

    results = {
        "model": MODEL, "thinking": THINKING, "n_chunks_by_bucket": N_CHUNKS,
        "buckets": {b: ids_for_bucket(b) for b in ("256k", "512k", "768k")},
        "reused_768k_ids": REUSED_768K_IDS,
        "data_check": data_check,
        "items": sorted(final_items, key=lambda r: (r["bucket"], r["id"], r["condition"])),
        "n_errors": len(errors), "errors": [{"key": list(k), "error": e} for k, e in errors],
        "budget": budget.snapshot(),
    }
    write_json(str(part_b_dir / "results.json"), results)
    print(f"\nWrote {part_b_dir / 'results.json'} with {len(results['items'])} item-condition rows.")

    csv_path = part_b_dir / "results.csv"
    fieldnames = ["bucket", "id", "condition", "n_chunks", "correct", "raw_answer", "target", "total_tokens",
                  "peak_context_tokens", "cost_usd", "part_a_correct", "part_a_real_input_tokens",
                  "part_a_cost_usd"]
    with csv_path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for r in results["items"]:
            writer.writerow({k: (r.get(k) if r.get(k) is not None else "") for k in fieldnames})
    print(f"Wrote {csv_path}")

    snap = budget.snapshot()
    print(f"\nBudget after step 2: completed=${snap['completed_spend_usd']:.4f} "
          f"(target ${snap['target_usd']:.2f}, hard stop ${snap['hard_stop_usd']:.2f})")
    if errors:
        sys.exit(1)


if __name__ == "__main__":
    main()
