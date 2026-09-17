"""Turn evidence/benchmark_sweep/results_all.json into results.csv,
summary.md, and (via plot_sweep_curves.py) curves.png -- contract addendum
v6: n=20/cell, 95% CI error bars, format-failure rate reported separately."""
import csv
import json
import math
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE / "lib"))
from pi_runner import write_text  # noqa: E402

OUT = HERE / "evidence" / "benchmark_sweep"
run_record = json.load(open(OUT / "results_all.json"))
results = run_record["results"]

# ---------------------------------------------------------------------
# results.json / results.csv -- one row per call
# ---------------------------------------------------------------------
json.dump(sorted(results, key=lambda r: r["id"]), open(OUT / "results.json", "w"), indent=2)
print(f"wrote {OUT / 'results.json'}")

fields = ["id", "benchmark", "task", "bucket", "real_input_tokens", "output_tokens",
          "cost_usd", "wall_time_s", "score", "format_ok", "length_refusal", "error", "raw_answer"]
with open(OUT / "results.csv", "w", newline="") as f:
    w = csv.writer(f)
    w.writerow(fields)
    for r in sorted(results, key=lambda r: r["id"]):
        w.writerow([r.get(k) for k in fields])
print(f"wrote {OUT / 'results.csv'}")


# ---------------------------------------------------------------------
# 95% CI (normal approximation, sample SD) -- valid for a 0-1-bounded score
# whether binary (BABILong exact match) or continuous (Graphwalks F1, MRCR
# ratio): for a 0/1 variable, sample SD reduces to sqrt(p(1-p)*n/(n-1)),
# i.e. the same formula as a binomial Wald CI.
# ---------------------------------------------------------------------
def mean_ci(scores):
    """Normal-approximation (Wald) 95% CI: mean +/- 1.96*SD/sqrt(n). Matches
    the ~11-point SE figure quoted in the contract at p=0.5,n=20. Near a 0%
    or 100% mean with small n this symmetric interval can extend past the
    valid [0,1] range (a known limitation of this method, not a computation
    error) -- clipped to [0,1] before returning; see summary.md's note."""
    scores = [s for s in scores if s is not None]
    n = len(scores)
    if n == 0:
        return None, None, None, 0
    mean = sum(scores) / n
    if n < 2:
        return mean, None, None, n
    var = sum((s - mean) ** 2 for s in scores) / (n - 1)
    se = math.sqrt(var / n)
    lo = max(0.0, mean - 1.96 * se)
    hi = min(1.0, mean + 1.96 * se)
    return mean, lo, hi, n


def fmt_pct(x):
    return f"{x*100:.1f}%" if x is not None else "n/a"


def cell_rows(rs, group_keys):
    groups = {}
    for r in rs:
        key = tuple(r[k] for k in group_keys)
        groups.setdefault(key, []).append(r)
    return groups


gw = [r for r in results if r["benchmark"] == "graphwalks"]
bl = [r for r in results if r["benchmark"] == "babilong"]
mr = [r for r in results if r["benchmark"] == "mrcr"]

N_TARGET_PER_CELL = 20
GW_BUCKETS = ["~128K", "~256K"]
BL_BUCKETS = ["32k", "128k", "256k"]
MR_BUCKETS = ["(16384,32768]", "(65536,131072]", "(131072,262144]"]

total_cost = sum(r.get("cost_usd", 0) or 0 for r in results)
total_wall = sum(r.get("wall_time_s", 0) or 0 for r in results)
n_refused = sum(1 for r in results if r.get("length_refusal"))
n_errors = sum(1 for r in results if r.get("error") and not r.get("length_refusal"))

all_items = json.load(open(HERE / "benchmarks" / "subset_sweep.json"))
done_ids = {r["id"] for r in results}
missing = [it for it in all_items if it["id"] not in done_ids]
stop_reason = run_record.get("stop_reason")

lines = ["# Benchmark sweep (v6): Graphwalks / BABILong / MRCR 8-needle, n=20 per cell", ""]
lines.append(
    "Properly-powered rerun of the v5 pilot (n=2/cell, which could only ever read 0/50/100% and "
    "was sampling noise, not measurement). n=20 per cell this time, seed 7, all cells at or below "
    "272K real input tokens (the cheap pricing tier). Each benchmark graded with its own published "
    "grader, unchanged. 95% CI = mean +/- 1.96 * sample SD / sqrt(n) (normal/Wald approximation), "
    "clipped to [0%, 100%] where the symmetric interval would otherwise extend past the valid range "
    "-- a known limitation of this method near a 0%/100% mean at small n, not a computation error."
)
lines.append("")
lines.append(f"**Total: {len(results)}/260 calls run, ${total_cost:.4f} spend, "
             f"{total_wall/60:.1f} minutes of summed per-item wall time (6-way concurrent), "
             f"{n_refused} length refusals, {n_errors} other errors.**")
lines.append("")
if missing:
    lines.append(
        f"**Budget note (read before the tables): the hard stop tripped at $8.0248, "
        f"$0.0248 over the $8.00 cap** -- 5 calls already in flight when that item completed "
        f"landed afterward (the harness stops SUBMITTING new work immediately but drains "
        f"already-dispatched concurrent calls rather than abandoning them mid-request), taking "
        f"the final total to ${total_cost:.4f}. No further calls were made once this was seen. "
        f"This left **{len(missing)} of 260 items unrun, all in `babilong/qa2/256k`**, which "
        f"therefore has only n=2 in the table below -- the exact underpowered condition this "
        f"whole redo exists to avoid. Its row is marked accordingly; do not read it as a "
        f"measured result."
    )
    lines.append("")

# --- Graphwalks ---
lines.append("## Graphwalks (F1 on node sets; published grader unchanged)")
lines.append("| bucket | task | n | mean F1 | 95% CI | format-ok rate | F1 among format-ok | mean tokens | mean wall (s) |")
lines.append("| --- | --- | --- | --- | --- | --- | --- | --- | --- |")
for bucket in GW_BUCKETS:
    for task in ("bfs", "parents"):
        rs = [r for r in gw if r["bucket"] == bucket and r["task"] == task]
        if not rs:
            continue
        scores = [r["score"] for r in rs]
        mean, lo, hi, n = mean_ci(scores)
        n_format_ok = sum(1 for r in rs if r.get("format_ok"))
        ok_scores = [r["score"] for r in rs if r.get("format_ok")]
        ok_mean = sum(ok_scores) / len(ok_scores) if ok_scores else None
        mean_tok = sum(r["real_input_tokens"] for r in rs) / len(rs)
        mean_wall = sum(r["wall_time_s"] for r in rs) / len(rs)
        ci_str = f"[{fmt_pct(lo)}, {fmt_pct(hi)}]" if lo is not None else "n/a"
        lines.append(f"| {bucket} | {task} | {n} | {fmt_pct(mean)} | {ci_str} | "
                     f"{n_format_ok}/{len(rs)} ({100*n_format_ok/len(rs):.0f}%) | {fmt_pct(ok_mean)} | "
                     f"{mean_tok:,.0f} | {mean_wall:.1f} |")
lines.append("")

# --- BABILong ---
lines.append("## BABILong (exact match, lowercase+strip; published grader unchanged)")
lines.append("| bucket | task | n | accuracy | 95% CI | mean tokens | mean wall (s) |")
lines.append("| --- | --- | --- | --- | --- | --- | --- |")
for bucket in BL_BUCKETS:
    for task in ("qa1", "qa2"):
        rs = [r for r in bl if r["bucket"] == bucket and r["task"] == task]
        if not rs:
            continue
        scores = [r["score"] for r in rs]
        mean, lo, hi, n = mean_ci(scores)
        mean_tok = sum(r["real_input_tokens"] for r in rs) / len(rs)
        mean_wall = sum(r["wall_time_s"] for r in rs) / len(rs)
        ci_str = f"[{fmt_pct(lo)}, {fmt_pct(hi)}]" if lo is not None else "n/a"
        flag = " **[UNDERPOWERED -- budget ran out, see note above]**" if n < N_TARGET_PER_CELL else ""
        lines.append(f"| {bucket} | {task} | {n}{flag} | {fmt_pct(mean)} | {ci_str} | {mean_tok:,.0f} | {mean_wall:.1f} |")
lines.append("")

# --- MRCR ---
lines.append("## MRCR 8-needle (hash-prefix check + SequenceMatcher ratio; published grader unchanged)")
lines.append("| bucket (tokens) | n | mean ratio | 95% CI | prefix-ok rate | mean tokens | mean wall (s) |")
lines.append("| --- | --- | --- | --- | --- | --- | --- |")
for bucket in MR_BUCKETS:
    rs = [r for r in mr if r["bucket"] == bucket]
    if not rs:
        continue
    scores = [r["score"] for r in rs]
    mean, lo, hi, n = mean_ci(scores)
    n_prefix_ok = sum(1 for r in rs if r.get("prefix_ok"))
    mean_tok = sum(r["real_input_tokens"] for r in rs) / len(rs)
    mean_wall = sum(r["wall_time_s"] for r in rs) / len(rs)
    ci_str = f"[{fmt_pct(lo)}, {fmt_pct(hi)}]" if lo is not None else "n/a"
    lines.append(f"| {bucket} | {n} | {fmt_pct(mean)} | {ci_str} | {n_prefix_ok}/{len(rs)} "
                 f"({100*n_prefix_ok/len(rs):.0f}%) | {mean_tok:,.0f} | {mean_wall:.1f} |")
lines.append("")

# --- Plain-English power statement ---
lines.append("## What n=20 can and cannot detect")
lines.append(
    "At n=20 per cell, the worst-case (p=0.5) standard error is `sqrt(0.5*0.5/20) ~= 11.2` "
    "percentage points, so a 95% CI half-width is roughly +/-22 points in the worst case (narrower "
    "wherever the true rate sits far from 50%, as several cells above do). Two cells' CIs overlapping "
    "is not evidence of no difference, but as a practical guide: reliably distinguishing two means at "
    "this n needs a true gap on the order of 25-30 points or more; a 10-point difference between two "
    "buckets of the same task is within noise and should not be reported as a trend. Where a "
    "benchmark's CIs across buckets overlap substantially in the table above, that is read here as "
    "'no detected degradation across this token range,' not as 'no degradation exists' -- a flat line "
    "at n=20 is a real, reportable result, unlike the same-looking flat line at n=2 in the v5 pilot."
)
lines.append("")
lines.append(
    "For reference, our own two prior results on this course's own materials: the 20-question needle "
    "sweep (`evidence/context_sweep/`) scored 100% at every size from 16K to 580K real tokens; the "
    "20-item comprehension check (`evidence/comprehension/`) scored 100% with only the 20 relevant "
    "excerpts (~5K tokens) and 80% with the full 551K-token corpus."
)
lines.append("")
lines.append("See `curves.png` for the plotted comparison, with 95% CI error bars, across all three "
             "benchmarks plus our own two prior results.")
lines.append("")

write_text(str(OUT / "summary.md"), "\n".join(lines))
print(f"wrote {OUT / 'summary.md'}")
