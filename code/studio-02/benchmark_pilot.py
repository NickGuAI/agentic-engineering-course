#!/usr/bin/env python3
"""benchmark_pilot.py -- pilot 3 public long-context benchmarks (Graphwalks,
BABILong, MRCR 8-needle) against a pi model, using each benchmark's own
published grader (contract addendum v5). Items come from the fixed,
reproducible subset at benchmarks/subset.json (see benchmarks/prepare_subsets.py,
seed 7; 12 Graphwalks + 12 BABILong + 16 MRCR-8needle = 40).

Calls are fired CONCURRENTLY, at most --max-workers (default 6) in flight, one
pi call per item (--no-tools --no-context-files --thinking low, bulk prompt
via stdin). A request refused for length is recorded as data, not a crash.
Cumulative spend is checked after every single completion (not just per
batch); the run stops submitting new work immediately on a 429/quota error or
once cumulative cost crosses --hard-stop (default $4.00), and still drains and
records whatever was already in flight.

Usage:
  python3 benchmark_pilot.py --benchmark all --model openai/gpt-5.6-luna --thinking low
  python3 benchmark_pilot.py --benchmark graphwalks --limit 2 --dry-run   # mechanics only, no cost
"""
import argparse
import json
import re
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from difflib import SequenceMatcher
from pathlib import Path
from threading import Lock

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE / "lib"))
from pi_runner import run_pi, DEFAULT_MODEL, real_token_count  # noqa: E402

BENCH_DIR = HERE / "benchmarks"
SUBSET_PATH = BENCH_DIR / "subset.json"

QUOTA_KEYWORDS = ("429", "rate limit", "rate-limit", "too many requests", "quota", "usage limit", "usage cap")
LENGTH_KEYWORDS = (
    "context window", "context_length", "context length", "too long", "maximum context",
    "maximum_context", "exceeds", "too many tokens", "input is too large",
)


def is_quota_error(text):
    if not text:
        return False
    low = text.lower()
    return any(k in low for k in QUOTA_KEYWORDS)


def looks_like_length_refusal(result):
    """A hard refusal (pi/provider declines before generating) OR the silent
    empty-answer failure mode seen in the comprehension check: the model's
    turn ends with stopReason "length" and no real answer text, because the
    huge input left ~no computed output budget under pi's belief about the
    model's context window."""
    if result.error and any(k in result.error.lower() for k in LENGTH_KEYWORDS):
        return True
    if not result.answer_text.strip():
        for e in result.events:
            if e.get("type") == "message_end":
                msg = e.get("message", {})
                if msg.get("role") == "assistant" and msg.get("stopReason") == "length":
                    return True
    return False


# ---------------------------------------------------------------------
# Graders -- published, not invented (see CONTRACT-v5-benchmarks.md and each
# dataset card, fetched and quoted while building this script).
# ---------------------------------------------------------------------

def grade_graphwalks(response, answer_nodes):
    line = (response or "").split("\n")[-1]
    if "Final Answer:" not in line:
        return {"f1": 0.0, "precision": 0.0, "recall": 0.0, "failed_to_parse": True, "format_ok": False}
    m = re.search(r"\[.*\]", line)
    if not m:
        return {"f1": 0.0, "precision": 0.0, "recall": 0.0, "failed_to_parse": True, "format_ok": False}
    result_list = [x.strip() for x in m.group(0).strip("[]").split(",") if x.strip()]
    sampled, truth = set(result_list), set(answer_nodes)
    n_golden, n_sampled = len(truth), len(sampled)
    if n_golden == 0 and n_sampled == 0:
        return {"f1": 1.0, "precision": 1.0, "recall": 1.0, "failed_to_parse": False, "format_ok": True}
    n_overlap = len(sampled & truth)
    recall = n_overlap / n_golden if n_golden else 0.0
    precision = n_overlap / n_sampled if n_sampled else 0.0
    f1 = 2 * recall * precision / (recall + precision) if (recall + precision) else 0.0
    return {"f1": f1, "precision": precision, "recall": recall, "failed_to_parse": False, "format_ok": True}


def grade_babilong(response, target):
    return {"correct": (response or "").strip().lower() == target.strip().lower()}


def grade_mrcr(response, answer, random_string_to_prepend):
    response = response or ""
    if not response.startswith(random_string_to_prepend):
        return {"ratio": 0.0, "prefix_ok": False}
    resp = response[len(random_string_to_prepend):] if response.startswith(random_string_to_prepend) else response
    ans = answer[len(random_string_to_prepend):] if answer.startswith(random_string_to_prepend) else answer
    ratio = SequenceMatcher(None, resp, ans).ratio()
    return {"ratio": ratio, "prefix_ok": True}


# ---------------------------------------------------------------------
# Prompt construction
# ---------------------------------------------------------------------

GRAPHWALKS_SYSTEM = (
    "You may reason briefly, but the LAST line of your entire response must be exactly in this "
    "form, nothing else on that line and nothing after it: Final Answer: [node1, node2, ...] "
    "(or Final Answer: [] if the set is empty). Do not describe the answer in prose instead of "
    "that line -- e.g. do not end with a sentence like 'The parent nodes are X and Y.' with no "
    "'Final Answer:' line at all, and do not put the node list anywhere but inside that exact "
    "line's brackets. No markdown fences, no closing remarks after it."
)

MRCR_SYSTEM = (
    "The text below is a multi-turn conversation transcript, ending with the user's final "
    "request. Continue the transcript by writing ONLY the assistant's next reply to that final "
    "request -- follow its instructions exactly, including any prefix it asks you to prepend -- "
    "and output nothing else: no preamble, no meta-commentary, no markdown fences, no further turns."
)


def render_mrcr_prompt(messages):
    parts = []
    for m in messages:
        role = "User" if m["role"] == "user" else "Assistant"
        parts.append(f"{role}: {m['content']}")
    return "\n\n".join(parts)


SHORT_PROMPT = "(continue with the text and instructions given above on stdin)"


def build_call(item, model, thinking, work_root):
    """Returns (stdin_text, extra_args, work_dir). The bulk content always
    goes on stdin with a short placeholder as the actual `prompt` argument --
    passing a multi-hundred-KB (or multi-MB) string as the argv prompt would
    hit Linux's MAX_ARG_STRLEN and crash (this is exactly the bug fixed in
    run_pi's own auto-stdin-fallback; here the content is large enough on
    almost every item that we route to stdin unconditionally rather than
    rely on run_pi's 100KB auto-detection, which only fires when stdin_text
    is left as None)."""
    bench = item["benchmark"]
    extra_args = []
    if bench == "graphwalks":
        stdin_text = item["prompt"]
        extra_args = ["--append-system-prompt", GRAPHWALKS_SYSTEM]
    elif bench == "babilong":
        stdin_text = item["prompt"]
    elif bench == "mrcr":
        messages = json.loads(item["prompt"])
        stdin_text = render_mrcr_prompt(messages)
        extra_args = ["--append-system-prompt", MRCR_SYSTEM]
    else:
        raise ValueError(bench)
    work_dir = str(work_root / f"{bench}-{item['id']}")
    return stdin_text, extra_args, work_dir


def run_one_item(item, model, thinking, work_root, timeout):
    stdin_text, extra_args, work_dir = build_call(item, model, thinking, work_root)
    t0 = time.time()
    result = run_pi(
        SHORT_PROMPT, cwd=work_dir, model=model, no_tools=True, no_context_files=True,
        thinking=thinking, stdin_text=stdin_text, extra_args=extra_args, timeout=timeout,
    )
    wall = time.time() - t0
    u = result.usage or {}
    real_input = (u.get("input") or 0) + (u.get("cacheRead") or 0) + (u.get("cacheWrite") or 0)
    row = {
        "id": item["id"], "benchmark": item["benchmark"], "task": item["task"], "bucket": item["bucket"],
        "real_input_tokens": real_input, "output_tokens": u.get("output") or 0,
        "cost_usd": result.total_cost_usd, "wall_time_s": round(wall, 2),
        "raw_answer": result.answer_text, "error": result.error, "ok": result.ok,
        "length_refusal": looks_like_length_refusal(result),
    }
    row["format_ok"] = True  # default; graphwalks below is the only grader that can set False
    if item["benchmark"] == "graphwalks":
        row.update(grade_graphwalks(result.answer_text, item["answer_nodes"]))
        # Published grader unchanged: failed_to_parse -> f1=0.0, kept as-is in `score`.
        # format_ok/failed_to_parse are recorded per item so summary.md can report the
        # format-failure rate SEPARATELY (and an F1-among-parseable-items figure) rather
        # than letting a formatting miss hide silently inside the mean F1.
        row["score"] = row["f1"]
    elif item["benchmark"] == "babilong":
        row.update(grade_babilong(result.answer_text, item["target"]))
        row["score"] = 1.0 if row["correct"] else 0.0
    elif item["benchmark"] == "mrcr":
        row.update(grade_mrcr(result.answer_text, item["answer"], item["random_string_to_prepend"]))
        row["score"] = row["ratio"]
    if row["length_refusal"]:
        row["score"] = None  # refusal is data, not a zero score
    return row


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--benchmark", choices=["graphwalks", "babilong", "mrcr", "all"], default="all")
    ap.add_argument("--model", default=DEFAULT_MODEL)
    ap.add_argument("--thinking", default="low")
    ap.add_argument("--max-workers", type=int, default=6)
    ap.add_argument("--hard-stop", type=float, default=4.00)
    ap.add_argument("--limit", type=int, default=None, help="only process the first N selected items (debug)")
    ap.add_argument("--ids", default=None, help="comma-separated item ids to run (e.g. re-running refusals)")
    ap.add_argument("--dry-run", action="store_true", help="build prompts and print plan, no pi calls")
    ap.add_argument("--out", default="evidence/benchmark_pilot")
    ap.add_argument("--timeout", type=int, default=900)
    ap.add_argument("--subset", default=str(SUBSET_PATH), help="path to the subset JSON to run")
    args = ap.parse_args()

    items = json.load(open(args.subset))
    if args.benchmark != "all":
        items = [it for it in items if it["benchmark"] == args.benchmark]
    if args.ids:
        wanted = {int(x) for x in args.ids.split(",")}
        items = [it for it in items if it["id"] in wanted]
    # cheapest first, by whatever token estimate is available
    def est_tokens(it):
        if "real_tokens_estimate" in it:
            return it["real_tokens_estimate"]
        return 30000 if "32k" in it["bucket"] else (120000 if "128k" in it["bucket"] else 500000)
    items.sort(key=est_tokens)
    if args.limit:
        items = items[: args.limit]

    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)
    work_root = HERE / "work" / "benchmark_pilot"
    work_root.mkdir(parents=True, exist_ok=True)

    if args.dry_run:
        for it in items:
            stdin_text, extra_args, work_dir = build_call(it, args.model, args.thinking, work_root)
            print(f"id={it['id']} {it['benchmark']}/{it['task']}/{it['bucket']} "
                  f"stdin_chars={len(stdin_text)} extra_args={extra_args}")
        print(f"\n{len(items)} items planned, no pi calls made (--dry-run).")
        return

    print(f"Running {len(items)} items, max_workers={args.max_workers}, hard_stop=${args.hard_stop:.2f}")
    results = []
    cumulative_cost = 0.0
    stop_reason = None
    lock = Lock()

    with ThreadPoolExecutor(max_workers=args.max_workers) as pool:
        futures = {}
        idx = 0

        def submit_next():
            nonlocal idx
            if idx < len(items):
                it = items[idx]
                idx += 1
                fut = pool.submit(run_one_item, it, args.model, args.thinking, work_root, args.timeout)
                futures[fut] = it

        for _ in range(min(args.max_workers, len(items))):
            submit_next()

        while futures:
            done = next(as_completed(futures))
            it = futures.pop(done)
            try:
                row = done.result()
            except Exception as e:
                row = {"id": it["id"], "benchmark": it["benchmark"], "task": it["task"], "bucket": it["bucket"],
                       "error": f"exception in run_one_item: {e}", "ok": False, "score": None,
                       "real_input_tokens": 0, "cost_usd": 0.0, "wall_time_s": 0.0, "raw_answer": "",
                       "length_refusal": False}
            results.append(row)
            with lock:
                cumulative_cost += row.get("cost_usd", 0.0) or 0.0
                cur_cost = cumulative_cost
            tag = "REFUSAL" if row.get("length_refusal") else ("ERR" if row.get("error") else "ok")
            print(f"  [{len(results)}/{len(items)}] id={row['id']} {row['benchmark']}/{row.get('task')}/"
                  f"{row.get('bucket')} score={row.get('score')} cost=${row.get('cost_usd', 0) or 0:.4f} "
                  f"cum=${cur_cost:.4f} {tag}", flush=True)

            if stop_reason is None:
                if is_quota_error(row.get("error")):
                    stop_reason = f"429/quota error on item {row['id']}: {row.get('error')}"
                    print(f"STOPPING: {stop_reason}", file=sys.stderr)
                elif cur_cost > args.hard_stop:
                    stop_reason = f"cumulative cost ${cur_cost:.4f} exceeded hard stop ${args.hard_stop:.2f}"
                    print(f"STOPPING: {stop_reason}", file=sys.stderr)
                else:
                    submit_next()

    suffix = f"_ids-{args.ids.replace(',', '-')}" if args.ids else ""
    out_path = out_dir / f"results_{args.benchmark}{suffix}.json"
    json.dump({"results": results, "cumulative_cost_usd": cumulative_cost, "stop_reason": stop_reason,
               "model": args.model, "n_planned": len(items), "n_run": len(results)},
              open(out_path, "w"), indent=2)
    print(f"\nDone. {len(results)}/{len(items)} items run. Cumulative cost ${cumulative_cost:.4f}. "
          f"stop_reason={stop_reason}")
    print(f"wrote {out_path}")


if __name__ == "__main__":
    main()
