"""qa1_curve.png -- BABILong qa1 accuracy vs. real input tokens, 32K-768K,
95% CI error bars, n annotated per point (contract addendum v7)."""
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker

HERE = Path(__file__).resolve().parent
OUT = HERE / "evidence" / "babilong_qa1_topend"

SURFACE = "#fcfcfb"
INK_PRIMARY = "#0b0b0b"
INK_SECONDARY = "#52514e"
INK_MUTED = "#898781"
GRIDLINE = "#e1e0d9"
SLOT_ORANGE = "#eb6834"  # matches the BABILong series color used in the v6 sweep chart

# (mean_tokens, mean_pct, lo_err, hi_err, n)
POINTS = [
    (30549, 85.0, 85.0 - 68.9, 100.0 - 85.0, 20),
    (122552, 75.0, 75.0 - 55.5, 94.5 - 75.0, 20),
    (241380, 65.0, 65.0 - 43.6, 86.4 - 65.0, 20),
    (481833, 70.0, 70.0 - 40.1, 99.9 - 70.0, 10),
    (766944, 40.0, 40.0 - 8.0, 72.0 - 40.0, 10),
]

fig, ax = plt.subplots(figsize=(9.5, 6.2), dpi=150)
fig.patch.set_facecolor(SURFACE)
ax.set_facecolor(SURFACE)

xs = [p[0] for p in POINTS]
ys = [p[1] for p in POINTS]
lo = [p[2] for p in POINTS]
hi = [p[3] for p in POINTS]
ns = [p[4] for p in POINTS]

ax.errorbar(xs, ys, yerr=[lo, hi], color=SLOT_ORANGE, linestyle="-", marker="o", markersize=8,
            linewidth=2.4, zorder=3, markeredgecolor=SURFACE, markeredgewidth=1.0, capsize=5,
            elinewidth=1.5, ecolor=SLOT_ORANGE, label="BABILong qa1 (exact match, 95% CI)")

for x, y, h, n in zip(xs, ys, hi, ns):
    marker = f"n={n}" + (" (new)" if n == 10 else "")
    ax.annotate(marker, xy=(x, y), xytext=(0, 14 + h * 0.9), textcoords="offset points",
                ha="center", fontsize=8.5, color=INK_SECONDARY)

for x, label in [(272000, "pricing threshold (272K)"), (767277, "largest verified success (767K)")]:
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
ax.set_title("BABILong qa1: full curve, 32K-768K, with 95% CI",
             color=INK_PRIMARY, fontsize=13, loc="left", pad=14)
ax.legend(loc="upper right", frameon=False, fontsize=9, labelcolor=INK_SECONDARY)

caption = (
    "32K/128K/256K: n=20 (evidence/benchmark_sweep/). 512K: n=10, native BABILong bucket. 768K: n=10, "
    "constructed by truncating 1M-bucket items to 768,000 tokens and keeping only items whose qa1 "
    "supporting fact survives truncation (68/100 survived) -- this selects for needles earlier in the "
    "original document (biased toward EASIER placement), so the observed 768K decline is, if anything, "
    "an underestimate. The 32K vs. 768K CIs overlap: a 45-point drop that is consistent with, but not "
    "confirmed as exceeding, sampling noise at n=10. See summary.md for full needle-depth distributions."
)
fig.text(0.02, 0.005, caption, fontsize=7.2, color=INK_MUTED, wrap=True, va="bottom")

fig.subplots_adjust(bottom=0.22)
fig.savefig(OUT / "qa1_curve.png", facecolor=SURFACE, bbox_inches="tight")
print(f"wrote {OUT / 'qa1_curve.png'}")
