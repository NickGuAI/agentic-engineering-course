"""Build evidence/benchmark_pilot/curves.png -- log-x score-vs-length plot
comparing Graphwalks/BABILong/MRCR (this pilot) against our own two prior
results (needle sweep, comprehension check). dataviz-skill palette: the 3
validated categorical slots (blue/orange/aqua) for the 3 NEW pilot
benchmarks; the 2 "our own" results are reference lines in muted ink grays,
not new hue slots, since going past 3 categorical slots on one plot is
exactly the case the skill says to avoid (past 3, slot 4 starts failing its
own CVD/all-pairs checks) -- secondary encoding (linestyle/marker, and here
also a grayscale ink tier) substitutes instead of adding a hue.
"""
import json
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker

HERE = Path(__file__).resolve().parent
OUT = HERE / "evidence" / "benchmark_pilot"

# palette (matches lib/charts.py exactly -- validated, see dataviz skill)
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


def bucket_points(rs, bucket_order, bucket_key="bucket"):
    """[(mean_real_tokens, mean_score_pct)] for buckets that have >=1 scored item."""
    pts = []
    for b in bucket_order:
        cell = [r for r in rs if r[bucket_key] == b]
        scored = [r for r in cell if r["score"] is not None]
        if not scored:
            continue
        toks = [r["real_input_tokens"] for r in scored]
        pts.append((sum(toks) / len(toks), 100 * sum(r["score"] for r in scored) / len(scored)))
    return pts


GW_BUCKETS = ["~128K", "~256K", "~1M"]
BL_BUCKETS = ["32k", "128k", "512k"]
MR_BUCKETS = ["(4096,8192]", "(8192,16384]", "(16384,32768]", "(32768,65536]",
              "(65536,131072]", "(131072,262144]", "(262144,524288]", "(524288,1048576]"]

gw_bfs = bucket_points([r for r in gw if r["task"] == "bfs"], GW_BUCKETS)
gw_parents = bucket_points([r for r in gw if r["task"] == "parents"], GW_BUCKETS)
# BABILong (qa1+qa2 mean): pool both tasks' scored items per bucket together
bl_mean = bucket_points(bl, BL_BUCKETS)
mrcr_pts = bucket_points(mr, MR_BUCKETS)

# our own two prior results (see evidence/context_sweep, evidence/comprehension)
NEEDLE_SWEEP_X = [16875, 32729, 64333, 127610, 198865, 253860, 580786]
NEEDLE_SWEEP_Y = [100, 100, 100, 100, 100, 100, 100]
COMPREHENSION_X = [3076, 551863]
COMPREHENSION_Y = [100, 80]

fig, ax = plt.subplots(figsize=(10, 6.4), dpi=150)
fig.patch.set_facecolor(SURFACE)
ax.set_facecolor(SURFACE)

def plot_series(pts, color, label, linestyle="-", marker="o", zorder=3, linewidth=2.2, markersize=7):
    if not pts:
        return
    xs = [p[0] for p in pts]
    ys = [p[1] for p in pts]
    ax.plot(xs, ys, color=color, linestyle=linestyle, marker=marker, markersize=markersize,
            linewidth=linewidth, label=label, zorder=zorder, markeredgecolor=SURFACE, markeredgewidth=0.8)

plot_series(gw_bfs, SLOT_BLUE, "Graphwalks -- BFS (F1)", linestyle="-", marker="o")
plot_series(gw_parents, SLOT_BLUE, "Graphwalks -- Parents (F1)", linestyle="--", marker="s")
plot_series(bl_mean, SLOT_ORANGE, "BABILong -- qa1+qa2 mean (exact match)", linestyle="-", marker="o")
plot_series(mrcr_pts, SLOT_AQUA, "MRCR 8-needle (SequenceMatcher ratio)", linestyle="-", marker="o")
plot_series(list(zip(NEEDLE_SWEEP_X, NEEDLE_SWEEP_Y)), INK_MUTED,
            "Our needle sweep (reference; keyword match)", linestyle=":", marker="", linewidth=1.8, zorder=2)
plot_series(list(zip(COMPREHENSION_X, COMPREHENSION_Y)), INK_SECONDARY,
            "Our comprehension set (reference; SUPPORTED/CONTRADICTED/NOT_FOUND)",
            linestyle="-.", marker="D", linewidth=1.8, markersize=6, zorder=2)

# reference vertical lines
for x, label in [(272000, "Luna catalog window (272K)"), (551000, "our corpus (551K)")]:
    ax.axvline(x, color=INK_MUTED, linewidth=1.2, linestyle="--", zorder=1, alpha=0.7)
    ax.annotate(label, xy=(x, 3), xytext=(4, 0), textcoords="offset points",
                rotation=90, va="bottom", ha="left", fontsize=7.5, color=INK_MUTED)

ax.set_xscale("log")
ax.set_xlim(2000, 6_000_000)
ax.set_ylim(-3, 106)
ax.grid(True, which="major", axis="y", color=GRIDLINE, linewidth=1, zorder=0)
ax.grid(True, which="major", axis="x", color=GRIDLINE, linewidth=0.6, zorder=0, alpha=0.6)
ax.xaxis.set_major_formatter(mticker.FuncFormatter(
    lambda x, _: f"{x/1e6:.0f}M" if x >= 1e6 else (f"{x/1e3:.0f}K" if x >= 1000 else f"{x:.0f}")))

for spine in ("top", "right"):
    ax.spines[spine].set_visible(False)
for spine in ("left", "bottom"):
    ax.spines[spine].set_color(GRIDLINE)

ax.set_xlabel("Real input tokens (log scale)", color=INK_SECONDARY, fontsize=10)
ax.set_ylabel("Score (0-100%)", color=INK_SECONDARY, fontsize=10)
ax.tick_params(colors=INK_SECONDARY, labelsize=9)
ax.set_title("Score vs. context length: three public benchmarks vs. our own two results",
             color=INK_PRIMARY, fontsize=13, loc="left", pad=14)

legend = ax.legend(loc="lower left", frameon=False, fontsize=8.3, labelcolor=INK_SECONDARY,
                    bbox_to_anchor=(0.0, 0.02))

caption = (
    "Metrics differ by benchmark and are NOT on a common scale: Graphwalks = node-set F1, "
    "BABILong = exact-match accuracy, MRCR = difflib.SequenceMatcher ratio, our needle sweep = "
    "keyword-match accuracy, our comprehension set = 3-way label accuracy. Curves are comparable "
    "in SHAPE (how score moves with length) only, never in absolute LEVEL across benchmarks. "
    "Graphwalks has no ~1M point: both replicates in each ~1M task cell were refused outright "
    "(\"input exceeds the context window\"), at $0 cost -- see summary.md."
)
fig.text(0.02, 0.005, caption, fontsize=7.3, color=INK_MUTED, wrap=True, va="bottom")

fig.subplots_adjust(bottom=0.22)
fig.savefig(OUT / "curves.png", facecolor=SURFACE, bbox_inches="tight")
print(f"wrote {OUT / 'curves.png'}")
