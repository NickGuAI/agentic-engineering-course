#!/usr/bin/env python3
"""Contract addendum v10, step 3: analysis and deliverables for the Part B
grid (evidence/part_b/{results.csv is already written by part_b_grid.py};
this script writes summary.md and comparison.png from results.json).

3x3 table = bucket (256K/512K/768K) x condition (Part A baseline, Isolate,
Targeted summary), each cell: correct/20, mean%, 95% Wald CI (same formula
as evidence/part_a/summary.md: p +/- 1.96*sqrt(p*(1-p)/n), clipped to
[0,100]), mean total tokens, mean peak single-call context, total cost.
"""
import json
import math
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker

from lib.pi_runner import md_table, write_text

BASE = Path(__file__).resolve().parent
PART_A_DIR = BASE / "evidence" / "part_a"
PART_B_DIR = BASE / "evidence" / "part_b"
BUCKETS = ["256k", "512k", "768k"]
CONDITIONS = ["Part A (single call)", "Isolate", "Targeted summary"]

# dataviz skill categorical palette, first three slots (validated all-pairs,
# both light and dark): blue / orange / aqua, assigned by series identity
# (never re-ordered by rank).
COLOR_PART_A = "#2a78d6"
COLOR_ISOLATE = "#eb6834"
COLOR_SUMMARY = "#1baf7a"
SURFACE = "#fcfcfb"
INK_PRIMARY = "#0b0b0b"
INK_SECONDARY = "#52514e"
INK_MUTED = "#898781"
GRIDLINE = "#e1e0d9"


def wald_ci(p: float, n: int):
    if n == 0:
        return 0.0, 0.0
    se = math.sqrt(p * (1 - p) / n)
    lo = max(0.0, p - 1.96 * se)
    hi = min(1.0, p + 1.96 * se)
    return lo, hi


def stats_for(rows, correct_key="correct"):
    n = len(rows)
    n_correct = sum(1 for r in rows if r.get(correct_key))
    p = n_correct / n if n else 0.0
    lo, hi = wald_ci(p, n)
    return {
        "n": n, "n_correct": n_correct, "mean_pct": p * 100, "ci_lo_pct": lo * 100, "ci_hi_pct": hi * 100,
    }


def main():
    part_a = json.loads((PART_A_DIR / "results.json").read_text(encoding="utf-8"))
    part_a_by_key = {(r["bucket"], r["id"]): r for r in part_a}

    part_b = json.loads((PART_B_DIR / "results.json").read_text(encoding="utf-8"))
    items = part_b["items"]
    by_bucket_cond = {}
    for b in BUCKETS:
        by_bucket_cond[(b, "isolate")] = [r for r in items if r["bucket"] == b and r["condition"] == "isolate"]
        by_bucket_cond[(b, "summary")] = [r for r in items if r["bucket"] == b and r["condition"] == "summary"]

    # --- table cells ---
    cells = {}  # (bucket, condition_label) -> stats dict (+ mean_total_tokens, mean_peak_context, cost)
    for b in BUCKETS:
        ids = part_b["buckets"][b]
        pa_rows = [part_a_by_key[(b, idn)] for idn in ids if (b, idn) in part_a_by_key]
        s = stats_for(pa_rows, "correct")
        s["mean_total_tokens"] = round(sum(r["real_input_tokens"] for r in pa_rows) / len(pa_rows)) if pa_rows else 0
        s["mean_peak_context"] = s["mean_total_tokens"]  # single call: peak == total input
        s["cost_usd"] = sum(r["cost_usd"] for r in pa_rows)
        cells[(b, "Part A (single call)")] = s

        iso_rows = by_bucket_cond[(b, "isolate")]
        s = stats_for(iso_rows, "correct")
        s["mean_total_tokens"] = round(sum(r["total_tokens"] for r in iso_rows) / len(iso_rows)) if iso_rows else 0
        s["mean_peak_context"] = round(sum(r["peak_context_tokens"] for r in iso_rows) / len(iso_rows)) if iso_rows else 0
        s["cost_usd"] = sum(r["cost_usd"] for r in iso_rows)
        cells[(b, "Isolate")] = s

        summ_rows = by_bucket_cond[(b, "summary")]
        s = stats_for(summ_rows, "correct")
        s["mean_total_tokens"] = round(sum(r["total_tokens"] for r in summ_rows) / len(summ_rows)) if summ_rows else 0
        s["mean_peak_context"] = round(sum(r["peak_context_tokens"] for r in summ_rows) / len(summ_rows)) if summ_rows else 0
        s["cost_usd"] = sum(r["cost_usd"] for r in summ_rows)
        cells[(b, "Targeted summary")] = s

    # --- summary.md ---
    lines = [
        "# Part B grid: Isolate and Targeted summary, n=20 x 3 buckets x 2 conditions -- summary",
        "",
        f"Model `{part_b['model']}`, thinking `{part_b['thinking']}`, chunk counts per bucket: "
        f"{part_b['n_chunks_by_bucket']}. Compaction is NOT part of this run (contract addendum v10). "
        f"768K ids {part_b['reused_768k_ids']} are reused from the pre-v10 run, not re-run and not "
        f"re-charged (see evidence/part_b/results_v9_pre_grid.json for that run's own record).",
        "",
        "## 3 x 3 table (bucket x condition)",
        "",
    ]
    rows = []
    for b in BUCKETS:
        for cond in CONDITIONS:
            s = cells[(b, cond)]
            rows.append([
                b, cond, f"{s['n_correct']}/{s['n']}", f"{s['mean_pct']:.1f}%",
                f"[{s['ci_lo_pct']:.1f}%, {s['ci_hi_pct']:.1f}%]",
                f"{s['mean_total_tokens']:,}", f"{s['mean_peak_context']:,}", f"${s['cost_usd']:.4f}",
            ])
    lines.append(md_table(
        ["bucket", "condition", "correct/n", "mean", "95% CI", "mean total tokens",
         "mean peak single-call context", "total cost"], rows))
    lines.append("")

    # --- per-item table ---
    lines += ["## Per-item results (same ids Part A scored in every bucket)", ""]
    item_rows = []
    for b in BUCKETS:
        ids = part_b["buckets"][b]
        for idn in ids:
            pa = part_a_by_key.get((b, idn))
            pa_cell = ("correct" if pa.get("correct") else "WRONG") if pa else "n/a"
            iso = next((r for r in items if r["bucket"] == b and r["id"] == idn and r["condition"] == "isolate"), None)
            summ = next((r for r in items if r["bucket"] == b and r["id"] == idn and r["condition"] == "summary"), None)
            iso_cell = ("correct" if iso and iso["correct"] else "WRONG") if iso else "MISSING"
            summ_cell = ("correct" if summ and summ["correct"] else "WRONG") if summ else "MISSING"
            item_rows.append([
                f"{idn} ({b})", pa_cell, iso_cell,
                f"{iso['peak_context_tokens']:,}" if iso else "n/a",
                summ_cell, f"{summ['peak_context_tokens']:,}" if summ else "n/a",
            ])
    lines.append(md_table(
        ["id (bucket)", "Part A", "Isolate", "Isolate peak context", "Targeted summary",
         "Targeted summary peak context"], item_rows))
    lines.append("")

    # --- plain-English paragraph ---
    lines += ["## What this grid does and does not show", "", (
        "Every cell above is n=20, so its 95% CI spans roughly +/-20-25 percentage points -- wide enough "
        "that this grid resolves large, consistent gaps (for example Part A's baseline falling from 65% "
        "at 256K to 45% at 768K) but cannot distinguish two conditions that differ by 10-15 points; at "
        "this n, a fair reading only trusts differences that are large AND consistent across buckets, or "
        "confirms with a CI-aware test rather than eyeballing point estimates. The chunked conditions "
        "(Isolate, Targeted summary) cut the PEAK context any single call has to hold -- to roughly one "
        "chunk's worth (a 256K haystack: ~3x smaller; 512K: ~6x; 768K: ~8x) -- while total tokens moved "
        "barely change, since the same haystack is still read in full, just split across more, smaller "
        "calls. Whether that peak-context reduction also recovers accuracy lost at long context is the "
        "empirical question this table answers per bucket: compare each bucket's Isolate/Targeted-summary "
        "row against its own Part A row, not against a different bucket's Part A row."
    ), ""]

    lines += ["## Deviations from the contract", "", (
        "A session restart interrupted the first attempt to run this grid partway through Stage A (chunk "
        "calls). 131 chunk calls (all of 256K's isolate and targeted-summary chunks, plus 11 of 512K's) had "
        "already been made and paid for -- real pi calls, real cost, recorded in evidence/grid_budget.json "
        "-- before the interruption, but this script's own checkpoint file "
        "(evidence/part_b/grid_checkpoint.json) had fallen behind and only reflected 11 of them. Rather "
        "than re-running (and re-paying for) those 120 calls, they were recovered by re-parsing the raw pi "
        "event stream each one had already written to evidence/part_b/raw/*.raw.jsonl -- ledger cost and "
        "recovered-record cost matched to the penny for all 131 (see backfill_part_b_checkpoint.py) -- and "
        "the run resumed from there. No item was ever charged twice and no completed call was re-run."
    ), ""]

    budget = part_b.get("budget", {})
    lines += ["## Budget", "", (
        f"Target ${budget.get('target_usd', 0):.2f}, hard stop ${budget.get('hard_stop_usd', 0):.2f}. "
        f"Cumulative completed spend across Part A's extension and this grid (shared ledger, "
        f"evidence/grid_budget.json): ${budget.get('completed_spend_usd', 0):.4f}."
    ), ""]

    write_text(str(PART_B_DIR / "summary.md"), "\n".join(lines))
    print(f"wrote {PART_B_DIR / 'summary.md'}")
    for (b, cond), s in cells.items():
        print(f"  {b} / {cond}: {s['n_correct']}/{s['n']} {s['mean_pct']:.1f}% "
              f"[{s['ci_lo_pct']:.1f}%, {s['ci_hi_pct']:.1f}%]")

    # --- comparison.png ---
    fig, ax = plt.subplots(figsize=(9.5, 6.2), dpi=150)
    fig.patch.set_facecolor(SURFACE)
    ax.set_facecolor(SURFACE)

    x_positions = {b: i for i, b in enumerate(BUCKETS)}
    series = [("Part A (single call)", COLOR_PART_A), ("Isolate", COLOR_ISOLATE),
              ("Targeted summary", COLOR_SUMMARY)]
    offsets = {"Part A (single call)": -0.12, "Isolate": 0.0, "Targeted summary": 0.12}

    for cond, color in series:
        xs, ys, lo, hi, ns = [], [], [], [], []
        for b in BUCKETS:
            s = cells[(b, cond)]
            xs.append(x_positions[b] + offsets[cond])
            ys.append(s["mean_pct"])
            lo.append(s["mean_pct"] - s["ci_lo_pct"])
            hi.append(s["ci_hi_pct"] - s["mean_pct"])
            ns.append(s["n"])
        ax.errorbar(xs, ys, yerr=[lo, hi], color=color, linestyle="-", marker="o", markersize=8,
                    linewidth=2.2, zorder=3, markeredgecolor=SURFACE, markeredgewidth=1.0, capsize=5,
                    elinewidth=1.5, ecolor=color, label=f"{cond} (95% CI, n={ns[0]})")

    ax.set_xticks(list(x_positions.values()))
    ax.set_xticklabels([b.upper() for b in BUCKETS])
    ax.set_xlim(-0.5, len(BUCKETS) - 0.5)
    ax.set_ylim(-5, 118)
    ax.grid(True, which="major", axis="y", color=GRIDLINE, linewidth=1, zorder=0)
    for spine in ("top", "right"):
        ax.spines[spine].set_visible(False)
    for spine in ("left", "bottom"):
        ax.spines[spine].set_color(GRIDLINE)

    ax.set_xlabel("Bucket", color=INK_SECONDARY, fontsize=10)
    ax.set_ylabel("Exact-match accuracy (0-100%)", color=INK_SECONDARY, fontsize=10)
    ax.tick_params(colors=INK_SECONDARY, labelsize=9)
    ax.set_title("BABILong qa1 grid: Part A baseline vs. Isolate vs. Targeted summary, n=20, 95% CI",
                 color=INK_PRIMARY, fontsize=12.5, loc="left", pad=14)
    ax.legend(loc="upper right", frameon=False, fontsize=9, labelcolor=INK_SECONDARY)

    caption = (
        "All cells n=20 (contract addendum v10). Error bars are 95% Wald binomial CIs -- wide at this n; "
        "see summary.md for the full table and a reading of what the grid can and cannot resolve at n=20."
    )
    fig.text(0.02, 0.005, caption, fontsize=7.5, color=INK_MUTED, wrap=True, va="bottom")
    fig.subplots_adjust(bottom=0.16)
    fig.savefig(PART_B_DIR / "comparison.png", facecolor=SURFACE, bbox_inches="tight")
    print(f"wrote {PART_B_DIR / 'comparison.png'}")


if __name__ == "__main__":
    main()
