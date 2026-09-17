#!/usr/bin/env python3
"""lib/charts.py -- the two context_sweep.py charts (contract addendum v2
section 6), built with matplotlib and the validated reference palette from
the `dataviz` skill (references/palette.md): categorical slots 1-3 (blue/
orange/aqua) for the three accuracy lines, and the fixed status palette
(good/warning/critical) for the correct/wrong/hallucinated heatmap cells.
These are static PNGs, not live HTML, so there is one render (the light
chart surface): a light-surface PNG with dark ink reads fine embedded on
either a light or a dark page, the same as any documentation screenshot.

Both charts degrade gracefully to a single column when only one size has been
run (e.g. the 16k-only smoke test): the code does not assume len(sizes) > 1.
"""
from pathlib import Path
from typing import Dict, List

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.patches import Patch  # noqa: E402

# --- Reference palette (dataviz skill, references/palette.md), light mode ---
SURFACE = "#fcfcfb"
INK_PRIMARY = "#0b0b0b"
INK_SECONDARY = "#52514e"
INK_MUTED = "#898781"
GRIDLINE = "#e1e0d9"
BASELINE = "#c3c2b7"

# Categorical slots 1-3 (the three that validate all-pairs in both modes).
SERIES_OVERALL = "#2a78d6"  # slot 1, blue
SERIES_IN_SLICE = "#eb6834"  # slot 2, orange
SERIES_ABSTENTION = "#1baf7a"  # slot 3, aqua

# Status palette (fixed, never themed).
STATUS_CORRECT = "#0ca30c"  # good
STATUS_WRONG = "#fab219"  # warning
STATUS_HALLUCINATED = "#d03b3b"  # critical

CANONICAL_SIZE_ORDER = ["16k", "32k", "64k", "128k", "200k", "256k", "full"]


def _ordered_sizes(all_results: Dict[str, dict]) -> List[str]:
    return sorted(
        all_results.keys(),
        key=lambda s: (CANONICAL_SIZE_ORDER.index(s) if s in CANONICAL_SIZE_ORDER else len(CANONICAL_SIZE_ORDER), s),
    )


def _apply_chart_chrome(ax):
    ax.set_facecolor(SURFACE)
    for spine in ("top", "right"):
        ax.spines[spine].set_visible(False)
    for spine in ("left", "bottom"):
        ax.spines[spine].set_color(BASELINE)
        ax.spines[spine].set_linewidth(1)
    ax.tick_params(colors=INK_SECONDARY, labelsize=9)
    ax.xaxis.label.set_color(INK_SECONDARY)
    ax.yaxis.label.set_color(INK_SECONDARY)


def build_accuracy_vs_length_chart(all_results: Dict[str, dict], out_path: Path, window_tokens: int):
    sizes = [s for s in _ordered_sizes(all_results) if all_results[s].get("ok") and all_results[s].get("scoring")]
    if not sizes:
        return  # nothing scoreable yet (e.g. every size errored) -- skip rather than emit a blank chart

    xs, overall, in_slice, abstention = [], [], [], []
    for size in sizes:
        rec = all_results[size]
        s = rec["scoring"]
        xs.append(rec["usage"].get("input") or rec.get("slice_estimated_real_tokens", 0))
        overall.append(s["overall_accuracy"] * 100)
        in_slice.append(None if s["in_slice_accuracy"] is None else s["in_slice_accuracy"] * 100)
        abstention.append(None if s["abstention_accuracy"] is None else s["abstention_accuracy"] * 100)

    fig, ax = plt.subplots(figsize=(9, 5.5), dpi=200)
    fig.patch.set_facecolor(SURFACE)
    _apply_chart_chrome(ax)

    log_scale = len(xs) > 1 and max(xs) / max(1, min(xs)) > 8
    if log_scale:
        ax.set_xscale("log")

    def _plot_series(ys, color, label):
        pts = [(x, y) for x, y in zip(xs, ys) if y is not None]
        if not pts:
            return
        px, py = zip(*pts)
        ax.plot(px, py, color=color, linewidth=2, marker="o", markersize=6, label=label, zorder=3)

    _plot_series(overall, SERIES_OVERALL, "Overall accuracy (of all questions)")
    _plot_series(in_slice, SERIES_IN_SLICE, "In-slice accuracy (needle inside the window)")
    _plot_series(abstention, SERIES_ABSTENTION, "Abstention accuracy (correctly says NOT FOUND)")

    for x, size in zip(xs, sizes):
        ax.annotate(
            size, (x, overall[sizes.index(size)]), textcoords="offset points", xytext=(0, 10),
            ha="center", fontsize=8, color=INK_SECONDARY,
        )

    if min(xs) <= window_tokens <= max(xs) * 1.05:
        ax.axvline(window_tokens, color=INK_MUTED, linewidth=1.5, linestyle="--", zorder=2)
        ax.annotate(
            f"Luna window ({window_tokens:,} tok)", (window_tokens, 100), textcoords="offset points",
            xytext=(6, -4), fontsize=8, color=INK_MUTED, va="top",
        )

    ax.set_ylim(-3, 105)
    ax.set_xlabel("Real input tokens per run (tiktoken o200k_base)")
    ax.set_ylabel("Accuracy (%)")
    ax.grid(True, which="major", axis="y", color=GRIDLINE, linewidth=1, zorder=0)
    ax.set_axisbelow(True)

    n_q = None
    for rec in all_results.values():
        if rec.get("scoring"):
            n_q = rec["scoring"]["n_total"]
            break
    title_n = f" ({n_q} questions)" if n_q else ""
    ax.set_title(f"Accuracy vs. context length{title_n}", color=INK_PRIMARY, fontsize=13, loc="left", pad=14)

    legend = ax.legend(loc="lower left", frameon=False, fontsize=9, labelcolor=INK_SECONDARY)
    for text in legend.get_texts():
        text.set_color(INK_SECONDARY)

    fig.tight_layout()
    fig.savefig(out_path, facecolor=SURFACE)
    plt.close(fig)


def _question_row_label(q: dict) -> str:
    parts = [f"Q{q['id']}"]
    if q.get("doc") is not None:
        parts.append(f"doc {q['doc']}")
    depth = q.get("needle_depth_tokens")
    if depth is not None:
        parts.append(f"{depth // 1000}K" if depth >= 1000 else str(depth))
    elif q.get("expect_not_found"):
        parts.append("not in corpus")
    else:
        parts.append("early")
    return " · ".join(parts)


def build_heatmap_chart(all_results: Dict[str, dict], questions: List[dict], out_path: Path):
    sizes = [s for s in _ordered_sizes(all_results) if all_results[s].get("ok") and all_results[s].get("scoring")]
    if not sizes or not questions:
        return

    # Rows ordered by needle depth ascending; questions with no needle_depth_tokens
    # (not expect_not_found) sort first (they are answerable from the very first byte).
    def _depth_key(q):
        if q.get("expect_not_found"):
            return float("inf")
        d = q.get("needle_depth_tokens")
        return -1 if d is None else d

    ordered_questions = sorted(questions, key=_depth_key)
    n_rows, n_cols = len(ordered_questions), len(sizes)

    verdict_by_id = {}
    in_slice_by_id = {}
    for size in sizes:
        by_q = {r["id"]: r for r in all_results[size]["scoring"]["per_question"]}
        for q in ordered_questions:
            r = by_q.get(q["id"])
            verdict_by_id.setdefault(q["id"], {})[size] = r["verdict"] if r else None
            in_slice_by_id.setdefault(q["id"], {})[size] = r["in_slice"] if r else None

    color_map = {"correct": STATUS_CORRECT, "wrong": STATUS_WRONG, "hallucinated": STATUS_HALLUCINATED}

    cell_w, cell_h = 1.1, 0.42
    fig_w = max(5.5, 2.2 + cell_w * n_cols)
    fig_h = max(3.0, 1.3 + cell_h * n_rows)
    fig, ax = plt.subplots(figsize=(fig_w, fig_h), dpi=200)
    fig.patch.set_facecolor(SURFACE)
    ax.set_facecolor(SURFACE)

    boundary_points = []  # (col_index, row_count_in_slice) for the staircase overlay
    for ci, size in enumerate(sizes):
        n_in = 0
        for ri, q in enumerate(ordered_questions):
            verdict = verdict_by_id[q["id"]][size]
            color = color_map.get(verdict, INK_MUTED)
            ax.add_patch(plt.Rectangle((ci, n_rows - 1 - ri), 1, 1, facecolor=color, edgecolor=SURFACE, linewidth=2))
            if in_slice_by_id[q["id"]][size]:
                n_in += 1
        boundary_points.append(n_in)

    # Staircase boundary: draws the edge between "needle inside this column's
    # slice" (above the line) and "needle beyond it" (below), so a hallucinated
    # or correctly-abstained cell's context is visible at a glance.
    for ci, n_in in enumerate(boundary_points):
        y = n_rows - n_in
        ax.plot([ci, ci + 1], [y, y], color=INK_PRIMARY, linewidth=1.6, zorder=5)
        if ci + 1 < n_cols:
            y_next = n_rows - boundary_points[ci + 1]
            ax.plot([ci + 1, ci + 1], [y, y_next], color=INK_PRIMARY, linewidth=1.6, zorder=5)

    ax.set_xlim(0, n_cols)
    ax.set_ylim(0, n_rows)
    ax.set_yticks([n_rows - 1 - i + 0.5 for i in range(n_rows)])
    ax.set_yticklabels([_question_row_label(q) for q in ordered_questions], color=INK_SECONDARY, fontsize=8)
    ax.tick_params(length=0)
    for spine in ax.spines.values():
        spine.set_visible(False)

    # Column (size) labels go on TOP of the grid, not the bottom, so the
    # caption and legend below have their own clear strip and never collide
    # with a tick label.
    ax.xaxis.set_ticks_position("top")
    ax.set_xticks([i + 0.5 for i in range(n_cols)])
    ax.set_xticklabels(sizes, color=INK_SECONDARY, fontsize=9)

    n_q = len(ordered_questions)
    ax.set_title(
        f"Correctness by question and context size ({n_q} questions x {n_cols} sizes)\n",
        color=INK_PRIMARY, fontsize=12, loc="left", pad=16,
    )

    legend_handles = [
        Patch(facecolor=STATUS_CORRECT, label="Correct"),
        Patch(facecolor=STATUS_WRONG, label="Wrong"),
        Patch(facecolor=STATUS_HALLUCINATED, label="Hallucinated (answered instead of NOT FOUND)"),
    ]
    # Caption first, legend below it, both anchored below the axes in axes
    # fraction coordinates -- bbox_inches="tight" on save expands the canvas
    # to include both, so nothing needs a hand-tuned margin.
    caption_gap = 0.6 / n_rows  # a roughly constant absolute gap regardless of row count
    ax.text(
        0, -caption_gap, "Black step line marks the in-window / out-of-window boundary for each size.",
        transform=ax.transAxes, fontsize=7.5, color=INK_MUTED, ha="left", va="top",
    )
    legend = ax.legend(
        handles=legend_handles, loc="upper left", bbox_to_anchor=(0, -caption_gap - 1.1 / n_rows),
        ncol=1, frameon=False, fontsize=8,
    )
    for text in legend.get_texts():
        text.set_color(INK_SECONDARY)

    fig.savefig(out_path, facecolor=SURFACE, bbox_inches="tight")
    plt.close(fig)


def build_charts(all_results: Dict[str, dict], questions: List[dict], out_dir: Path, window_tokens: int):
    build_accuracy_vs_length_chart(all_results, Path(out_dir) / "accuracy_vs_length.png", window_tokens)
    build_heatmap_chart(all_results, questions, Path(out_dir) / "heatmap.png")
