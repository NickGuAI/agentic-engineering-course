#!/usr/bin/env python3
"""Recovery utility: rebuild evidence/part_b/grid_checkpoint.json from the
raw pi event-stream files already on disk (evidence/part_b/raw/*.raw.jsonl),
instead of trusting the checkpoint file itself.

Why this is needed: a session restart interrupted part_b_grid.py mid-run.
evidence/grid_budget.json (the cost ledger) shows 131 real, paid-for part_b
calls (67 isolate + 64 summary), and every one of them has a matching raw
event file under evidence/part_b/raw/ (run_pi always writes raw_events_path
right after the subprocess returns, unconditionally -- independent of this
script's own checkpoint bookkeeping). But grid_checkpoint.json itself only
had 11 entries recorded -- its persistence fell behind the actual work
before the process died, for reasons not fully diagnosed (no duplicate
ledger labels were found, so this was not two processes racing each other;
most likely the checkpoint file's periodic rewrite lost ground right before
the kill). Trusting the stale checkpoint.json would make part_b_grid.py
re-run and re-pay for 120 calls that are already done and already paid for.

This script re-derives every completed call's result record directly from
its raw file (same parse used by run_part_a_extend.py's recovery path) and
writes a correct, complete checkpoint.json, keyed exactly the way
part_b_grid.py's make_chunk_task/make_lead_task expect
("{condition}/{bucket}-item-{id}/chunk-{NN}" or ".../lead" or ".../reask").
Idempotent and read-only with respect to pi/the budget: makes no pi calls,
spends no money, only reads raw/*.jsonl and rewrites grid_checkpoint.json.
"""
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from part_b_grid import prompt_tokens_from_usage  # noqa: E402
from part_b_isolate_compress import score_babilong  # noqa: E402
import part_b_grid as pbg  # noqa: E402

BASE = Path(__file__).resolve().parent
RAW_DIR = BASE / "evidence" / "part_b" / "raw"
CHECKPOINT_PATH = BASE / "evidence" / "part_b" / "grid_checkpoint.json"

# New-grid raw file naming (from part_b_grid.py's make_chunk_task/make_lead_task):
#   {condition}-{bucket}-item-{id}-chunk-{NN}.raw.jsonl
#   {condition}-{bucket}-item-{id}-lead.raw.jsonl      (isolate)
#   {condition}-{bucket}-item-{id}-reask.raw.jsonl     (summary)
# (The OLD reused ids 11/12/13 use a bucket-less name, e.g.
# "isolate-item-11-chunk-01.raw.jsonl" -- excluded by this regex on purpose;
# those 6 items are handled by part_b_grid.py's reused_record_from_old(),
# not by the checkpoint.)
FNAME_RE = re.compile(
    r"^(isolate|summary)-(256k|512k|768k)-item-(\d+)-(chunk-(\d+)|lead|reask)\.raw\.jsonl$"
)


def parse_raw_jsonl(raw_path: Path):
    """Same event parsing lib.pi_runner.run_pi does on its subprocess
    stdout, applied here to an already-saved capture."""
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
    total_cost, last_usage, error_message = 0.0, {}, None
    for e in assistant_ends:
        msg = e.get("message", {})
        usage = msg.get("usage") or {}
        cost = usage.get("cost") or {}
        total_cost += cost.get("total", 0) or 0
        if usage:
            last_usage = usage
        if msg.get("stopReason") == "error":
            error_message = msg.get("errorMessage") or "pi reported an error stopReason"
    answer_text = ""
    if assistant_ends:
        last_msg = assistant_ends[-1].get("message", {})
        text_parts = [c.get("text", "") for c in last_msg.get("content", []) if c.get("type") == "text"]
        answer_text = "\n".join(t for t in text_parts if t)
    ok = bool(assistant_ends) and not error_message
    return {
        "ok": ok, "error": error_message, "answer_text": answer_text,
        "usage": last_usage, "cost_usd": total_cost,
    }


def main():
    all_items = pbg.load_all_items()
    target_by_key = {(b, i): it["target"] for (b, i), it in all_items.items()}

    checkpoint = json.loads(CHECKPOINT_PATH.read_text(encoding="utf-8")) if CHECKPOINT_PATH.exists() else {}
    before_n = len(checkpoint)

    files = sorted(RAW_DIR.glob("*.raw.jsonl"))
    n_matched, n_added, n_skipped_existing, n_unparseable = 0, 0, 0, 0
    for f in files:
        m = FNAME_RE.match(f.name)
        if not m:
            continue
        condition, bucket, idn_s, stage_or_chunk, chunk_num = m.groups()
        idn = int(idn_s)
        n_matched += 1

        if stage_or_chunk.startswith("chunk-"):
            chunk_idx = int(chunk_num)
            label = f"{condition}/{bucket}-item-{idn}/chunk-{chunk_idx:02d}"
        else:
            suffix = stage_or_chunk  # "lead" or "reask"
            label = f"{condition}/{bucket}-item-{idn}/{suffix}"

        if label in checkpoint:
            n_skipped_existing += 1
            continue

        parsed = parse_raw_jsonl(f)
        if not parsed["ok"] and not parsed["answer_text"]:
            n_unparseable += 1
            print(f"  WARNING: {f.name} did not parse to a usable result (error={parsed['error']!r}); "
                  f"leaving unrecorded so part_b_grid.py will re-run it.", file=sys.stderr)
            continue

        usage = parsed["usage"]
        input_tokens = prompt_tokens_from_usage(usage)
        output_tokens = usage.get("output")

        if stage_or_chunk.startswith("chunk-"):
            text = parsed["answer_text"].strip() if parsed["ok"] else f"[ERROR: {parsed['error']}]"
            record = {
                "chunk": chunk_idx, "ok": parsed["ok"], "error": parsed["error"],
                ("report" if condition == "isolate" else "summary"): text,
                "input_tokens": input_tokens, "output_tokens": output_tokens,
                "cost_usd": round(parsed["cost_usd"], 6),
            }
        else:
            target = target_by_key.get((bucket, idn))
            scoring = score_babilong(parsed["answer_text"], target) if (parsed["ok"] and target is not None) else {
                "raw_answer": None, "correct": False, "score": 0.0}
            record = {
                "ok": parsed["ok"], "error": parsed["error"], "answer_text": parsed["answer_text"], **scoring,
                "input_tokens": input_tokens, "output_tokens": output_tokens,
                "cost_usd": round(parsed["cost_usd"], 6),
            }

        checkpoint[label] = record
        n_added += 1

    CHECKPOINT_PATH.write_text(json.dumps(checkpoint), encoding="utf-8")
    print(f"Matched {n_matched} new-grid raw files. Checkpoint: {before_n} -> {len(checkpoint)} entries "
          f"(+{n_added} recovered, {n_skipped_existing} already present, {n_unparseable} unparseable/left for re-run).")


if __name__ == "__main__":
    main()
