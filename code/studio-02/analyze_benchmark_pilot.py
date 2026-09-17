"""Turn evidence/benchmark_pilot/results_all.json into results.csv,
summary.md, and curves.png (contract addendum v5)."""
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE / "lib"))
from pi_runner import write_text  # noqa: E402

OUT = HERE / "evidence" / "benchmark_pilot"
run_record = json.load(open(OUT / "results_all.json"))
results = run_record["results"]

# results.json: the contract's named deliverable -- the flat one-row-per-item
# list (same rows as results.csv). results_all.json (produced directly by
# benchmark_pilot.py) is kept too: it additionally carries the run-level
# metadata (cumulative cost, stop_reason, model, counts).
json.dump(sorted(results, key=lambda r: r["id"]), open(OUT / "results.json", "w"), indent=2)
print(f"wrote {OUT / 'results.json'}")

# ---------------------------------------------------------------------
# results.csv
# ---------------------------------------------------------------------
import csv

fields = ["id", "benchmark", "task", "bucket", "real_input_tokens", "output_tokens",
          "cost_usd", "wall_time_s", "score", "length_refusal", "error"]
with open(OUT / "results.csv", "w", newline="") as f:
    w = csv.writer(f)
    w.writerow(fields)
    for r in sorted(results, key=lambda r: r["id"]):
        w.writerow([r.get(k) for k in fields])
print(f"wrote {OUT / 'results.csv'}")

# ---------------------------------------------------------------------
# Per-benchmark summary tables
# ---------------------------------------------------------------------

def fmt_pct(x):
    return f"{x*100:.1f}%" if x is not None else "n/a"


def bucket_table(bench_results, bucket_key="bucket"):
    buckets = {}
    for r in bench_results:
        buckets.setdefault(r[bucket_key], []).append(r)
    rows = []
    for bucket, rs in buckets.items():
        scored = [r["score"] for r in rs if r["score"] is not None]
        errors = [r for r in rs if r.get("error")]
        mean_score = sum(scored) / len(scored) if scored else None
        mean_tokens = sum(r["real_input_tokens"] for r in rs) / len(rs)
        mean_wall = sum(r["wall_time_s"] for r in rs) / len(rs)
        rows.append({
            "bucket": bucket, "n": len(rs), "n_scored": len(scored),
            "mean_score": mean_score, "mean_tokens": mean_tokens, "mean_wall": mean_wall,
            "n_errors": len(errors),
        })
    return rows


gw = [r for r in results if r["benchmark"] == "graphwalks"]
bl = [r for r in results if r["benchmark"] == "babilong"]
mr = [r for r in results if r["benchmark"] == "mrcr"]

GW_BUCKET_ORDER = ["~128K", "~256K", "~1M"]
BL_BUCKET_ORDER = ["32k", "128k", "512k"]
MR_BUCKET_ORDER = ["(4096,8192]", "(8192,16384]", "(16384,32768]", "(32768,65536]",
                   "(65536,131072]", "(131072,262144]", "(262144,524288]", "(524288,1048576]"]

lines = ["# Benchmark pilot: Graphwalks / BABILong / MRCR 8-needle -- results", ""]
lines.append(
    "Three public long-context benchmarks piloted on `openai/gpt-5.6-luna` (`--thinking low`), "
    "against a fixed, reproducible 40-item stratified subset (seed 7, see `benchmarks/subset.json` "
    "and `benchmarks/prepare_subsets.py`). Each benchmark graded with its own published grader -- "
    "F1 on node sets (Graphwalks), exact match after lowercase+strip (BABILong), hash-prefix check "
    "+ `difflib.SequenceMatcher` ratio (MRCR). Scores are NOT comparable across benchmarks in level, "
    "only in shape (see `curves.png` caption)."
)
lines.append("")

total_cost = sum(r.get("cost_usd", 0) or 0 for r in results)
total_wall = sum(r.get("wall_time_s", 0) or 0 for r in results)
n_refused = sum(1 for r in results if r.get("length_refusal"))
lines.append(f"**Total: 40/40 items run, ${total_cost:.4f} spend (hard stop was $4.00), "
             f"{total_wall/60:.1f} minutes of summed per-item wall time (6-way concurrent, so real "
             f"wall clock was much less), {n_refused} length refusals.**")
lines.append("")

# --- Graphwalks (split bfs/parents within bucket) ---
lines.append("## Graphwalks (F1 on node sets; task = bfs or parents)")
lines.append("| bucket | task | n | n scored | mean F1 | mean real tokens | mean wall (s) | errors |")
lines.append("| --- | --- | --- | --- | --- | --- | --- | --- |")
def means_excluding_refusals(rs):
    ok = [r for r in rs if not r.get("length_refusal")]
    if not ok:
        return "n/a", "n/a"
    return (f"{sum(r['real_input_tokens'] for r in ok) / len(ok):,.0f}",
            f"{sum(r['wall_time_s'] for r in ok) / len(ok):.1f}")


for bucket in GW_BUCKET_ORDER:
    for task in ("bfs", "parents"):
        rs = [r for r in gw if r["bucket"] == bucket and r["task"] == task]
        if not rs:
            continue
        scored = [r["score"] for r in rs if r["score"] is not None]
        mean_score = sum(scored) / len(scored) if scored else None
        mean_tokens, mean_wall = means_excluding_refusals(rs)
        n_err = sum(1 for r in rs if r.get("length_refusal"))
        lines.append(f"| {bucket} | {task} | {len(rs)} | {len(scored)} | {fmt_pct(mean_score)} | "
                     f"{mean_tokens} | {mean_wall} | {n_err} refusal(s) |" if n_err else
                     f"| {bucket} | {task} | {len(rs)} | {len(scored)} | {fmt_pct(mean_score)} | "
                     f"{mean_tokens} | {mean_wall} | 0 |")
lines.append("")
lines.append(
    "Note on the BFS cells: since BFS answer-set sizes are strongly right-skewed (up to ~6,900 "
    "nodes in this data), the 2 replicates per BFS cell were chosen near that cell's MEDIAN "
    "answer-node count -- filtering on answer SIZE only, never on difficulty or correctness."
)
lines.append("")

# --- BABILong ---
lines.append("## BABILong (exact match, lowercase+strip; task = qa1 or qa2)")
lines.append("| bucket | task | n | n scored | accuracy | mean real tokens | mean wall (s) |")
lines.append("| --- | --- | --- | --- | --- | --- | --- |")
for bucket in BL_BUCKET_ORDER:
    for task in ("qa1", "qa2"):
        rs = [r for r in bl if r["bucket"] == bucket and r["task"] == task]
        if not rs:
            continue
        scored = [r["score"] for r in rs if r["score"] is not None]
        mean_score = sum(scored) / len(scored) if scored else None
        mean_tokens = sum(r["real_input_tokens"] for r in rs) / len(rs)
        mean_wall = sum(r["wall_time_s"] for r in rs) / len(rs)
        lines.append(f"| {bucket} | {task} | {len(rs)} | {len(scored)} | {fmt_pct(mean_score)} | "
                     f"{mean_tokens:,.0f} | {mean_wall:.1f} |")
lines.append("")

# --- MRCR ---
lines.append("## MRCR 8-needle (hash-prefix check + SequenceMatcher ratio)")
lines.append("| bucket (tokens) | n | n scored | mean ratio | mean real tokens | mean wall (s) | errors |")
lines.append("| --- | --- | --- | --- | --- | --- | --- |")
for bucket in MR_BUCKET_ORDER:
    rs = [r for r in mr if r["bucket"] == bucket]
    if not rs:
        continue
    scored = [r["score"] for r in rs if r["score"] is not None]
    mean_score = sum(scored) / len(scored) if scored else None
    mean_tokens, mean_wall = means_excluding_refusals(rs)
    n_err = sum(1 for r in rs if r.get("length_refusal"))
    lines.append(f"| {bucket} | {len(rs)} | {len(scored)} | {fmt_pct(mean_score)} | "
                 f"{mean_tokens} | {mean_wall} | {n_err} refusal(s) |" if n_err else
                 f"| {bucket} | {len(rs)} | {len(scored)} | {fmt_pct(mean_score)} | "
                 f"{mean_tokens} | {mean_wall} | 0 |")
lines.append("")

# --- Headline comparison: shortest vs longest bucket per benchmark ---
lines.append("## Headline comparison: shortest vs. longest bucket per benchmark")
lines.append("| benchmark | shortest bucket | score | longest bucket | score | delta |")
lines.append("| --- | --- | --- | --- | --- | --- |")


def mean_score_for(rs):
    scored = [r["score"] for r in rs if r["score"] is not None]
    return sum(scored) / len(scored) if scored else None


gw_short = mean_score_for([r for r in gw if r["bucket"] == "~128K"])
gw_long = mean_score_for([r for r in gw if r["bucket"] == "~1M"])
bl_short = mean_score_for([r for r in bl if r["bucket"] == "32k"])
bl_long = mean_score_for([r for r in bl if r["bucket"] == "512k"])
mr_short = mean_score_for([r for r in mr if r["bucket"] == "(4096,8192]"])
mr_long = mean_score_for([r for r in mr if r["bucket"] == "(524288,1048576]"])

for name, short_b, s, long_b, l in [
    ("Graphwalks (bfs+parents)", "~128K", gw_short, "~1M", gw_long),
    ("BABILong (qa1+qa2)", "32k", bl_short, "512k", bl_long),
    ("MRCR 8-needle", "(4096,8192]", mr_short, "(524288,1048576]", mr_long),
]:
    delta = (l - s) if (s is not None and l is not None) else None
    lines.append(f"| {name} | {short_b} | {fmt_pct(s)} | {long_b} | {fmt_pct(l)} | "
                 f"{fmt_pct(delta) if delta is not None else 'n/a'} |")
lines.append("")
lines.append(
    "For reference, our own two prior results on this course's own materials: the 20-question "
    "needle sweep (`evidence/context_sweep/`) scored 100% at every size from 16K to 580K real "
    "tokens; the 20-item comprehension check (`evidence/comprehension/`) scored 100% with only "
    "the 20 relevant excerpts (~5K tokens) and 80% with the full 551K-token corpus."
)
lines.append("")

# --- Refusals ---
refusals = [r for r in results if r.get("length_refusal")]
if refusals:
    lines.append("## Length refusals")
    lines.append(
        "5 items (4 Graphwalks `~1M`, 1 MRCR `(524288,1048576]`) were refused outright with the "
        "exact error text `\"Your input exceeds the context window of this model. Please adjust "
        "your input and try again.\"`, at $0 cost each (rejected before any tokens were billed). "
        "Per the contract, the `~/.pi/agent/models.json` `contextWindow` override for "
        "`openai/gpt-5.6-luna` was raised from 1,050,000 first to 1,400,000, then as a "
        "confirmatory test to 5,000,000 -- the refusal was byte-for-byte identical every time, "
        "including at 5,000,000, which rules out the override as the mechanism (it was load-bearing "
        "for the earlier ~552K-token comprehension-check run, but has no effect here). The real "
        "ceiling sits somewhere between the largest item that succeeded (MRCR, 673,520 real input "
        "tokens) and the smallest that was refused (MRCR, 998,200 real input tokens) -- independent "
        "of any client-side override we can set. The override was left at 1,050,000, its last "
        "proven-useful value. These 5 items are recorded with `score: null` (refusal, not a zero) "
        "and excluded from the means above."
    )
    lines.append("")
    lines.append("| id | benchmark | task | bucket | real input tokens (estimate) |")
    lines.append("| --- | --- | --- | --- | --- |")
    subset = json.load(open(HERE / "benchmarks" / "subset.json"))
    by_id = {it["id"]: it for it in subset}
    for r in sorted(refusals, key=lambda r: r["id"]):
        est = by_id[r["id"]].get("real_tokens_estimate", "n/a")
        lines.append(f"| {r['id']} | {r['benchmark']} | {r['task']} | {r['bucket']} | {est:,} |"
                     if isinstance(est, int) else f"| {r['id']} | {r['benchmark']} | {r['task']} | {r['bucket']} | {est} |")
    lines.append("")

lines.append("See `curves.png` for the plotted comparison across all three benchmarks plus our own two prior results.")
lines.append("")

write_text(str(OUT / "summary.md"), "\n".join(lines))
print(f"wrote {OUT / 'summary.md'}")
