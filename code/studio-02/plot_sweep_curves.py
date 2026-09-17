"""Build evidence/benchmark_sweep/curves.png -- log-x score-vs-length plot
with 95% CI error bars (contract addendum v6). Same dataviz-skill palette
strategy as the v5 chart: 3 validated categorical slots (blue/orange/aqua),
one per BENCHMARK, with linestyle/marker distinguishing the two tasks within
Graphwalks and BABILong; our own two prior results are muted-ink reference
lines, not new hue slots (past 3 categorical slots on one plot starts
failing the palette's own all-pairs CVD checks -- see references/palette.md)."""
import json
import math
import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker

HERE = Path(__file__).resolve().parent
OUT = HERE / "evidence" / "benchmark_sweep"

SURFACE = "#fcfcfb"
INK_PRIMARY = "#0b0b0b"
INK_SECONDARY = "#52514e"
INK_MUTED = "#898781"
GRIDLINE = "#e1e0d9"

SLOT_BLUE = "#2a78d6"
SLOT_ORANGE = "#eb6834"
SLOT_AQUA = "#1baf7a"

results = json.load(open(OUT / "results_all.json"))["results"]
gw = [r for r in results if r["benchmark"] == "graphwalks"]
bl = [r for r in results if r["benchmark"] == "babilong"]
mr = [r for r in results if r["benchmark"] == "mrcr"]


def mean_ci(scores):
    scores = [s for s in scores if s is not None]
    n = len(scores)
    if n == 0:
        return None, None
    mean = sum(scores) / n
    if n < 2:
        return mean, 0.0
    var = sum((s - mean) ** 2 for s in scores) / (n - 1)
    se = math.sqrt(var / n)
    return mean, 1.96 * se


def bucket_points(rs, bucket_order, bucket_key="bucket"):
    """[(mean_real_tokens, mean_score_pct, (lo_err, hi_err))] -- asymmetric
    error bar half-widths, clipped so the whisker never crosses 0%/100%
    (the underlying Wald CI can extend past the valid range near a 0%/100%
    mean at small n; see analyze_benchmark_sweep.py's mean_ci docstring)."""
    pts = []
    for b in bucket_order:
        cell = [r for r in rs if r[bucket_key] == b]
        scored = [r for r in cell if r["score"] is not None]
        if not scored:
            continue
        toks = [r["real_input_tokens"] for r in scored]
        mean, half = mean_ci([r["score"] for r in scored])
        pct_mean, pct_half = 100 * mean, 100 * half
        lo_err = min(pct_half, pct_mean - 0.0)
        hi_err = min(pct_half, 100.0 - pct_mean)
        pts.append((sum(toks) / len(toks), pct_mean, (max(0.0, lo_err), max(0.0, hi_err))))
    return pts


GW_BUCKETS = ["~128K", "~256K"]
BL_BUCKETS = ["32k", "128k", "256k"]
MR_BUCKETS = ["(16384,32768]", "(65536,131072]", "(131072,262144]"]

gw_bfs = bucket_points([r for r in gw if r["task"] == "bfs"], GW_BUCKETS)
gw_parents = bucket_points([r for r in gw if r["task"] == "parents"], GW_BUCKETS)
bl_qa1 = bucket_points([r for r in bl if r["task"] == "qa1"], BL_BUCKETS)
bl_qa2 = bucket_points([r for r in bl if r["task"] == "qa2"], BL_BUCKETS)
mrcr_pts = bucket_points(mr, MR_BUCKETS)

NEEDLE_SWEEP_X = [16875, 32729, 64333, 127610, 198865, 253860, 580786]
NEEDLE_SWEEP_Y = [100] * 7
COMPREHENSION_X = [3076, 551863]
COMPREHENSION_Y = [100, 80]

fig, ax = plt.subplots(figsize=(11, 7), dpi=150)
fig.patch.set_facecolor(SURFACE)
ax.set_facecolor(SURFACE)


def plot_series(pts, color, label, linestyle="-", marker="o", zorder=3, linewidth=2.2, markersize=7,
                with_ci=True):
    if not pts:
        return
    xs = [p[0] for p in pts]
    ys = [p[1] for p in pts]
    if with_ci and len(pts[0]) == 3:
        lo_err = [p[2][0] for p in pts]
        hi_err = [p[2][1] for p in pts]
        ax.errorbar(xs, ys, yerr=[lo_err, hi_err], color=color, linestyle=linestyle, marker=marker,
                    markersize=markersize, linewidth=linewidth, label=label, zorder=zorder,
                    markeredgecolor=SURFACE, markeredgewidth=0.8, capsize=4, elinewidth=1.3,
                    ecolor=color, alpha=0.95)
    else:
        ax.plot(xs, ys, color=color, linestyle=linestyle, marker=marker, markersize=markersize,
                linewidth=linewidth, label=label, zorder=zorder, markeredgecolor=SURFACE,
                markeredgewidth=0.8)


plot_series(gw_bfs, SLOT_BLUE, "Graphwalks -- BFS (F1, 95% CI)", linestyle="-", marker="o")
plot_series(gw_parents, SLOT_BLUE, "Graphwalks -- Parents (F1, 95% CI)", linestyle="--", marker="s")
plot_series(bl_qa1, SLOT_ORANGE, "BABILong -- qa1 (exact match, 95% CI)", linestyle="-", marker="o")
plot_series(bl_qa2, SLOT_ORANGE, "BABILong -- qa2 (exact match, 95% CI)", linestyle="--", marker="s")
if len(bl_qa2) >= 3:
    x_last, y_last, _ = bl_qa2[-1]
    ax.annotate("n=2, budget cutoff\n(not n=20 like the rest)", xy=(x_last, y_last),
                xytext=(-90, 22), textcoords="offset points", fontsize=7.3, color=SLOT_ORANGE,
                ha="left", arrowprops=dict(arrowstyle="->", color=SLOT_ORANGE, lw=0.9))
plot_series(mrcr_pts, SLOT_AQUA, "MRCR 8-needle (SequenceMatcher ratio, 95% CI)", linestyle="-", marker="o")
plot_series([(x, y, None) for x, y in zip(NEEDLE_SWEEP_X, NEEDLE_SWEEP_Y)], INK_MUTED,
            "Our needle sweep (reference; keyword match, n=1/size)", linestyle=":", marker="",
            linewidth=1.8, zorder=2, with_ci=False)
plot_series([(x, y, None) for x, y in zip(COMPREHENSION_X, COMPREHENSION_Y)], INK_SECONDARY,
            "Our comprehension set (reference; 3-way label accuracy, n=20 total)",
            linestyle="-.", marker="D", linewidth=1.8, markersize=6, zorder=2, with_ci=False)

for x, label in [(272000, "pricing threshold (272K)"), (551000, "our corpus (551K)")]:
    ax.axvline(x, color=INK_MUTED, linewidth=1.2, linestyle="--", zorder=1, alpha=0.7)
    ax.annotate(label, xy=(x, 3), xytext=(4, 0), textcoords="offset points",
                rotation=90, va="bottom", ha="left", fontsize=7.5, color=INK_MUTED)

ax.set_xscale("log")
ax.set_xlim(2000, 900_000)
ax.set_ylim(-5, 115)
ax.grid(True, which="major", axis="y", color=GRIDLINE, linewidth=1, zorder=0)
ax.grid(True, which="major", axis="x", color=GRIDLINE, linewidth=0.6, zorder=0, alpha=0.6)
ax.xaxis.set_major_formatter(mticker.FuncFormatter(
    lambda x, _: f"{x/1e6:.1f}M" if x >= 1e6 else (f"{x/1e3:.0f}K" if x >= 1000 else f"{x:.0f}")))

for spine in ("top", "right"):
    ax.spines[spine].set_visible(False)
for spine in ("left", "bottom"):
    ax.spines[spine].set_color(GRIDLINE)

ax.set_xlabel("Real input tokens (log scale)", color=INK_SECONDARY, fontsize=10)
ax.set_ylabel("Score (0-100%)", color=INK_SECONDARY, fontsize=10)
ax.tick_params(colors=INK_SECONDARY, labelsize=9)
ax.set_title("Score vs. context length, n=20/cell with 95% CI: three public benchmarks vs. our own results",
             color=INK_PRIMARY, fontsize=12.5, loc="left", pad=14)

ax.legend(loc="lower left", frameon=False, fontsize=8, labelcolor=INK_SECONDARY, bbox_to_anchor=(0.0, 0.02))

caption = (
    "Metrics differ by benchmark and are NOT on a common scale: Graphwalks = node-set F1, "
    "BABILong = exact-match accuracy, MRCR = SequenceMatcher ratio, our needle sweep = keyword-match "
    "accuracy, our comprehension set = 3-way label accuracy. Curves are comparable in SHAPE only, "
    "never in absolute LEVEL. Error bars are 95% CIs (n=20/cell for the three new benchmarks); at "
    "this n only ~25-30-point differences are reliably distinguishable -- see summary.md. Our own "
    "two references have no error bars (n=1 per point / n=20 total, not resampled per length)."
)
fig.text(0.02, 0.005, caption, fontsize=7.2, color=INK_MUTED, wrap=True, va="bottom")

fig.subplots_adjust(bottom=0.24)
fig.savefig(OUT / "curves.png", facecolor=SURFACE, bbox_inches="tight")
print(f"wrote {OUT / 'curves.png'}")
