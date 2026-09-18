#!/usr/bin/env python3
"""plot_qa1_curve.py -- regenerate part_a/summary.md and part_a/qa1_curve.png
from part_a/results.json (BABILong qa1 accuracy vs. real input tokens, with
95% Wald binomial CI error bars and n annotated per point).

Run from studio/studio-02/instruction/code/, after part_a_stress.py.

Usage:
  python3 plot_qa1_curve.py --team <name>
"""
import argparse
import json
import math
import re
import sys
from pathlib import Path

# matplotlib is imported lazily inside main(), not here at module level, so
# --help works even before `pip install -r requirements.txt` has been run.

CODE_DIR = Path(__file__).resolve().parent
SUBMISSION_ROOT = CODE_DIR.parent.parent / "submission"
TEAM_NAME_RE = re.compile(r"^[A-Za-z0-9._-]{1,40}$")
BUCKET_ORDER = ["256k", "512k", "768k"]

SURFACE = "#fcfcfb"
INK_PRIMARY = "#0b0b0b"
INK_SECONDARY = "#52514e"
INK_MUTED = "#898781"
GRIDLINE = "#e1e0d9"
SLOT_ORANGE = "#eb6834"

# gpt-5.6-luna's model catalog caps its context window at 272,000 tokens
# before setup.sh applies the ~/.pi/agent/models.json override (see
# README.md); marked on the chart as a reference point, not a limit that was
# ever actually hit.
PRICING_THRESHOLD_TOKENS = 272_000


def wald_ci(p: float, n: int):
    if n == 0:
        return 0.0, 0.0
    se = math.sqrt(p * (1 - p) / n)
    return max(0.0, p - 1.96 * se), min(1.0, p + 1.96 * se)


def resolve_team_and_out(team, out):
    """Shared --team/--out resolution (kept identical in part_a_stress.py,
    part_b_isolate_compress.py, part_c_memory.py, plot_qa1_curve.py).

    Returns (out_dir, sessions_dir). Exits 2 with a one-line stderr message if
    neither --team nor --out is given, or if --team fails validation."""
    if team is not None and (team == "_template" or not TEAM_NAME_RE.match(team)):
        print(f"error: --team must match {TEAM_NAME_RE.pattern!r} and must not be '_template'", file=sys.stderr)
        sys.exit(2)
    if out:
        out_dir = Path(out)
    elif team:
        out_dir = SUBMISSION_ROOT / team / "evidence"
    else:
        print("error: pass --team <name> (writes to studio/studio-02/submission/<name>/evidence/) "
              "or --out <dir>", file=sys.stderr)
        sys.exit(2)
    sessions_dir = (CODE_DIR / "work" / "sessions" / (team or "default")).resolve()
    return out_dir, sessions_dir


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--team", default=None, help="team name; reads from studio/studio-02/submission/<name>/evidence/")
    ap.add_argument("--out", default=None, help="output directory (overrides --team; default: derived from --team)")
    args = ap.parse_args()

    out_dir, _sessions_dir = resolve_team_and_out(args.team, args.out)
    PART_A_DIR = out_dir / "part_a"

    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    import matplotlib.ticker as mticker

    results_path = PART_A_DIR / "results.json"
    if not results_path.exists():
        print(f"ERROR: {results_path} not found. Run part_a_stress.py first.")
        raise SystemExit(1)
    results = json.loads(results_path.read_text(encoding="utf-8"))
    buckets = [b for b in BUCKET_ORDER if any(r["bucket"] == b for r in results)]
    by_bucket = {b: [r for r in results if r["bucket"] == b] for b in buckets}

    stats = {}
    for b in buckets:
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
        "Single-message delivery, compaction disabled, exact-match scoring.", "",
        "| bucket | n | mean | 95% CI | mean real input tokens |",
        "| --- | --- | --- | --- | --- |",
    ]
    for b in buckets:
        s = stats[b]
        lines.append(f"| {b} | {s['n']} | {s['mean_pct']:.1f}% | [{s['ci_lo_pct']:.1f}%, {s['ci_hi_pct']:.1f}%] | "
                      f"{s['mean_input_tokens']:,} |")
    lines.append("")
    lines.append(
        "The 768K bucket has no native BABILong equivalent: it is built by truncating 1M-bucket items "
        "to 768,000 tokens and keeping only those whose qa1 supporting fact survives truncation. "
        "Surviving needles never sit past about 80 percent of the original document, so that bucket is "
        "structurally somewhat easier than an unbiased sample of the same length; any decline it shows "
        "is, if anything, an understatement."
    )
    lines.append("")
    (PART_A_DIR / "summary.md").write_text("\n".join(lines), encoding="utf-8")
    print(f"wrote {PART_A_DIR / 'summary.md'}")
    for b in buckets:
        s = stats[b]
        print(f"  {b}: n={s['n']} {s['mean_pct']:.1f}% [{s['ci_lo_pct']:.1f}%, {s['ci_hi_pct']:.1f}%] "
              f"mean_input={s['mean_input_tokens']:,}")

    # --- qa1_curve.png ---
    points = [(stats[b]["mean_input_tokens"], stats[b]["mean_pct"], stats[b]["mean_pct"] - stats[b]["ci_lo_pct"],
               stats[b]["ci_hi_pct"] - stats[b]["mean_pct"], stats[b]["n"]) for b in buckets]

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

    ax.axvline(PRICING_THRESHOLD_TOKENS, color=INK_MUTED, linewidth=1.2, linestyle="--", zorder=1, alpha=0.7)
    ax.annotate(f"catalog context-window cap ({PRICING_THRESHOLD_TOKENS // 1000}K)",
                xy=(PRICING_THRESHOLD_TOKENS, 2), xytext=(4, 0), textcoords="offset points",
                rotation=90, va="bottom", ha="left", fontsize=7.5, color=INK_MUTED)

    ax.set_xscale("log")
    ax.set_xlim(50000, 1_100_000)
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
    ax.set_title("BABILong qa1: accuracy vs. context length, with 95% CI",
                 color=INK_PRIMARY, fontsize=13, loc="left", pad=14)
    ax.legend(loc="upper right", frameon=False, fontsize=9, labelcolor=INK_SECONDARY)

    caption = (
        "768K: constructed by truncating 1M-bucket items to 768,000 tokens and keeping only items "
        "whose qa1 supporting fact survives truncation -- see summary.md."
    )
    fig.text(0.02, 0.005, caption, fontsize=7.2, color=INK_MUTED, wrap=True, va="bottom")

    fig.subplots_adjust(bottom=0.2)
    fig.savefig(PART_A_DIR / "qa1_curve.png", facecolor=SURFACE, bbox_inches="tight")
    print(f"wrote {PART_A_DIR / 'qa1_curve.png'}")


if __name__ == "__main__":
    main()
