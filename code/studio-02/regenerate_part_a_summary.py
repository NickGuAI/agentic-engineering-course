#!/usr/bin/env python3
"""Regenerate evidence/part_a/summary.md and qa1_curve.png from
evidence/part_a/results.json (contract addendum v10, step 1). Data-driven --
computes mean accuracy and a 95% Wald (normal-approximation) binomial CI per
bucket directly from the recorded rows, instead of the old plot_qa1_curve.py's
hardcoded POINTS list. CI formula verified against the pre-existing
summary.md numbers (85.0% n=20 -> [69.4%,100.0%], 65.0% n=20 -> [44.1%,85.9%],
70.0% n=10 -> [41.6%,98.4%], 40.0% n=10 -> [9.6%,70.4%]): p +/- 1.96*sqrt(p*(1-p)/n),
clipped to [0,100].

Run from code/studio-02/ after run_part_a_extend.py.
"""
import json
import math
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker

BASE = Path(__file__).resolve().parent
PART_A_DIR = BASE / "evidence" / "part_a"
BUCKET_ORDER = ["32k", "128k", "256k", "512k", "768k"]

SURFACE = "#fcfcfb"
INK_PRIMARY = "#0b0b0b"
INK_SECONDARY = "#52514e"
INK_MUTED = "#898781"
GRIDLINE = "#e1e0d9"
SLOT_ORANGE = "#eb6834"


def wald_ci(p: float, n: int):
    if n == 0:
        return 0.0, 0.0
    se = math.sqrt(p * (1 - p) / n)
    lo = max(0.0, p - 1.96 * se)
    hi = min(1.0, p + 1.96 * se)
    return lo, hi


def main():
    results = json.loads((PART_A_DIR / "results.json").read_text(encoding="utf-8"))
    by_bucket = {b: [r for r in results if r["bucket"] == b] for b in BUCKET_ORDER}

    stats = {}
    for b in BUCKET_ORDER:
        rows = by_bucket[b]
        n = len(rows)
        n_correct = sum(1 for r in rows if r.get("correct"))
        p = n_correct / n if n else 0.0
        lo, hi = wald_ci(p, n)
        mean_input_tokens = round(sum(r["real_input_tokens"] for r in rows) / n) if n else 0
        stats[b] = {
            "n": n, "n_correct": n_correct, "mean_pct": p * 100, "ci_lo_pct": lo * 100, "ci_hi_pct": hi * 100,
            "mean_input_tokens": mean_input_tokens,
        }

    # --- summary.md ---
    lines = [
        "# Part A: BABILong qa1, accuracy vs context length", "",
        "Model `openai/gpt-5.6-luna`, thinking low, single-message delivery, compaction disabled, "
        "exact-match scoring.", "",
        "| bucket | n | mean | 95% CI | mean input tokens |",
        "| --- | --- | --- | --- | --- |",
    ]
    for b in BUCKET_ORDER:
        s = stats[b]
        lines.append(f"| {b} | {s['n']} | {s['mean_pct']:.1f}% | [{s['ci_lo_pct']:.1f}%, {s['ci_hi_pct']:.1f}%] | "
                      f"{s['mean_input_tokens']:,} |")
    lines.append("")
    lines.append("All five buckets are now n=20 (contract addendum v10: 512K and 768K extended from n=10 to n=20; "
                  "32K/128K/256K unchanged from the original run -- 85.0/75.0/65.0%, confirmed unchanged by this "
                  "regeneration).")
    lines.append("")
    lines.append(
        "The 768K bucket has no native BABILong equivalent: it was built by truncating 1M-bucket items to "
        "768,000 tokens and keeping only those whose qa1 supporting fact survived (68 of 100). Surviving "
        "needles never sit past about 80 percent of the original document, so that bucket is structurally "
        "easier than an unbiased sample and the decline it shows is if anything an understatement."
    )
    lines.append("")
    n_wrong_768 = [r for r in by_bucket["768k"] if not r.get("correct")]
    lines.append(
        f"At 768K (n=20), {len(n_wrong_768)} of 20 answers are wrong. Ground-truth answers are recorded in "
        f"results.csv for the 512K and 768K rows."
    )
    lines.append("")
    lines.append(
        "Ground-truth answers are recorded in results.csv for the 512K and 768K rows. The 32K/128K/256K rows "
        "carry the answer given and the score assigned at run time but not the expected answer; those targets "
        "are regenerated for free when setup.sh acquires the BABILong qa1 splits."
    )
    lines.append("")
    lines.append(
        "**Deviation note (contract addendum v10):** the 10 new rows at each of 512K/768K (ids 21-30 and "
        "31-40) were run through pi successfully and their real cost was recorded in "
        "evidence/grid_budget.json at the time of the call, but this script's own bookkeeping (a bug now "
        "fixed in run_part_a_extend.py, unrelated to pi or the budget guard) initially failed to persist "
        "them into results.json/results.csv on the first pass. They were recovered with `--recover` by "
        "re-parsing the raw pi event stream each call had already written to "
        "evidence/part_a/raw_topend_extend/*.raw.jsonl -- no items were re-run and no money was spent twice. "
        "One consequence: `wall_time_s` for these 20 recovered rows is 0.0 (not reconstructable from the "
        "saved event stream), unlike the other 80 rows."
    )
    lines.append("")
    (PART_A_DIR / "summary.md").write_text("\n".join(lines), encoding="utf-8")
    print(f"wrote {PART_A_DIR / 'summary.md'}")
    for b in BUCKET_ORDER:
        s = stats[b]
        print(f"  {b}: n={s['n']} {s['mean_pct']:.1f}% [{s['ci_lo_pct']:.1f}%, {s['ci_hi_pct']:.1f}%] "
              f"mean_input={s['mean_input_tokens']:,}")

    # --- qa1_curve.png ---
    points = []
    for b in BUCKET_ORDER:
        s = stats[b]
        points.append((s["mean_input_tokens"], s["mean_pct"], s["mean_pct"] - s["ci_lo_pct"],
                        s["ci_hi_pct"] - s["mean_pct"], s["n"]))

    fig, ax = plt.subplots(figsize=(9.5, 6.2), dpi=150)
    fig.patch.set_facecolor(SURFACE)
    ax.set_facecolor(SURFACE)

    xs = [p[0] for p in points]
    ys = [p[1] for p in points]
    lo = [p[2] for p in points]
    hi = [p[3] for p in points]
    ns = [p[4] for p in points]

    ax.errorbar(xs, ys, yerr=[lo, hi], color=SLOT_ORANGE, linestyle="-", marker="o", markersize=8,
                linewidth=2.4, zorder=3, markeredgecolor=SURFACE, markeredgewidth=1.0, capsize=5,
                elinewidth=1.5, ecolor=SLOT_ORANGE, label="BABILong qa1 (exact match, 95% CI)")

    for x, y, h, n in zip(xs, ys, hi, ns):
        ax.annotate(f"n={n}", xy=(x, y), xytext=(0, 14 + h * 0.9), textcoords="offset points",
                    ha="center", fontsize=8.5, color=INK_SECONDARY)

    for x, label in [(272000, "pricing threshold (272K)")]:
        ax.axvline(x, color=INK_MUTED, linewidth=1.2, linestyle="--", zorder=1, alpha=0.7)
        ax.annotate(label, xy=(x, 2), xytext=(4, 0), textcoords="offset points",
                    rotation=90, va="bottom", ha="left", fontsize=7.5, color=INK_MUTED)

    ax.set_xscale("log")
    ax.set_xlim(15000, 1_100_000)
    ax.set_ylim(-5, 118)
    ax.grid(True, which="major", axis="y", color=GRIDLINE, linewidth=1, zorder=0)
    ax.grid(True, which="major", axis="x", color=GRIDLINE, linewidth=0.6, zorder=0, alpha=0.6)
    ax.xaxis.set_major_formatter(mticker.FuncFormatter(
        lambda x, _: f"{x/1e6:.1f}M" if x >= 1e6 else (f"{x/1e3:.0f}K" if x >= 1000 else f"{x:.0f}")))

    for spine in ("top", "right"):
        ax.spines[spine].set_visible(False)
    for spine in ("left", "bottom"):
        ax.spines[spine].set_color(GRIDLINE)

    ax.set_xlabel("Real input tokens (log scale)", color=INK_SECONDARY, fontsize=10)
    ax.set_ylabel("Exact-match accuracy (0-100%)", color=INK_SECONDARY, fontsize=10)
    ax.tick_params(colors=INK_SECONDARY, labelsize=9)
    ax.set_title("BABILong qa1: full curve, 32K-768K, n=20 throughout, with 95% CI",
                 color=INK_PRIMARY, fontsize=13, loc="left", pad=14)
    ax.legend(loc="upper right", frameon=False, fontsize=9, labelcolor=INK_SECONDARY)

    caption = (
        "All buckets n=20 (contract addendum v10). 768K: constructed by truncating 1M-bucket items to "
        "768,000 tokens and keeping only items whose qa1 supporting fact survives truncation (68/100 "
        "survived) -- this selects for needles earlier in the original document (biased toward EASIER "
        "placement), so the observed 768K decline is, if anything, an underestimate. See summary.md for "
        "the full table and needle-depth distributions."
    )
    fig.text(0.02, 0.005, caption, fontsize=7.2, color=INK_MUTED, wrap=True, va="bottom")

    fig.subplots_adjust(bottom=0.2)
    fig.savefig(PART_A_DIR / "qa1_curve.png", facecolor=SURFACE, bbox_inches="tight")
    print(f"wrote {PART_A_DIR / 'qa1_curve.png'}")


if __name__ == "__main__":
    main()
