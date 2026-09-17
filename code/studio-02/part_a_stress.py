#!/usr/bin/env python3
"""Part A: Context Window Stress Test.

Loads an increasing slice of the corpus plus the five questions in ONE turn,
with pi's auto-compaction disabled (via a project .pi/settings.json), and
records where the five-question score degrades or the call fails outright.

Usage:
  python3 part_a_stress.py --model google/gemini-3.1-flash-lite \\
      --sizes 8k,16k,32k,64k,full --out evidence

Run from code/studio-02/. Re-runnable: overwrites its own run-<size>.json /
run-<size>.raw.jsonl / summary.md files; never deletes anything under evidence/.
"""
import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from lib.pi_runner import (  # noqa: E402
    ANSWER_INSTRUCTIONS,
    DEFAULT_MODEL,
    SIZE_TOKEN_BUDGETS,
    build_distractor_padded_corpus,
    estimate_tokens,
    load_questions,
    md_table,
    parse_numbered_answers,
    questions_block,
    run_pi,
    score_all,
    slice_by_tokens,
    word_count,
    write_json,
    write_text,
)


def build_prompt(slice_text: str, questions: list) -> str:
    return (
        f"{slice_text}\n\n"
        f"Questions:\n{questions_block(questions)}\n\n"
        f"{ANSWER_INSTRUCTIONS}\n"
    )


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--model", default=DEFAULT_MODEL, help=f"provider/model-id (default: {DEFAULT_MODEL})")
    ap.add_argument("--sizes", default="8k,16k,32k,64k,full", help="comma-separated sizes to test")
    ap.add_argument("--out", default="evidence", help="output directory (default: evidence)")
    ap.add_argument("--corpus", default="corpus/survey.txt")
    ap.add_argument("--work-dir", default="work/part_a", help="scratch cwd for the pi process (holds .pi/settings.json)")
    ap.add_argument("--timeout", type=int, default=900)
    args = ap.parse_args()

    corpus_path = Path(args.corpus)
    if not corpus_path.exists():
        print(f"ERROR: {args.corpus} not found. Run: bash setup.sh", file=sys.stderr)
        sys.exit(1)
    full_text = corpus_path.read_text(encoding="utf-8", errors="replace")

    if not Path("questions.json").exists():
        print("ERROR: questions.json not found. It must live in code/studio-02/.", file=sys.stderr)
        sys.exit(1)
    questions = load_questions("questions.json")["questions"]

    # Scratch work dir with compaction disabled, so a real overflow (if the
    # slice ever exceeds the model's true context window) surfaces as a real
    # API error instead of being silently summarized away.
    work_dir = Path(args.work_dir)
    pi_settings_dir = work_dir / ".pi"
    pi_settings_dir.mkdir(parents=True, exist_ok=True)
    (pi_settings_dir / "settings.json").write_text(
        json.dumps({"compaction": {"enabled": False}}, indent=2), encoding="utf-8"
    )

    out_dir = Path(args.out)
    part_a_dir = out_dir / "part_a"
    part_a_dir.mkdir(parents=True, exist_ok=True)
    sessions_dir = (out_dir / "sessions").resolve()

    sizes = [s.strip() for s in args.sizes.split(",") if s.strip()]
    rows = []
    results_by_size = {}

    for size in sizes:
        print(f"=== Part A: size={size} ===", flush=True)
        if size == "full":
            slice_text = full_text
        elif size in ("2x", "3x"):
            # Optional sizes past "full": the whole corpus plus (multiplier - 1)
            # rounds of its own section files, reshuffled, appended as distractor
            # padding. Lets a huge-context model (ours has a 1M-token window, so
            # "full" alone never gets close to it) still be pushed toward
            # degradation or overflow. Not part of the default --sizes list.
            multiplier = int(size[0])
            slice_text = build_distractor_padded_corpus(full_text, "corpus/sections", multiplier)
        elif size in SIZE_TOKEN_BUDGETS:
            slice_text = slice_by_tokens(full_text, SIZE_TOKEN_BUDGETS[size])
        else:
            print(f"Unknown size '{size}', skipping (expected one of 8k,16k,32k,64k,full,2x,3x)", file=sys.stderr)
            continue

        est_tokens = estimate_tokens(slice_text)
        prompt = build_prompt(slice_text, questions)
        raw_path = str(part_a_dir / f"run-{size}.raw.jsonl")

        result = run_pi(
            prompt=prompt,
            cwd=str(work_dir),
            model=args.model,
            no_tools=True,
            session_dir=str(sessions_dir),
            raw_events_path=raw_path,
            timeout=args.timeout,
            approve=True,
            no_context_files=True,
        )

        answers = parse_numbered_answers(result.answer_text, n=5) if result.ok else {}
        if result.ok:
            score, wrong_or_missing = score_all(answers, questions)
        else:
            score, wrong_or_missing = 0, [q["id"] for q in questions]

        record = {
            "size": size,
            "estimated_input_tokens": est_tokens,
            "model": args.model,
            "ok": result.ok,
            "error": result.error,
            "usage": result.usage,
            "cost_usd": round(result.total_cost_usd, 6),
            "wall_time_s": round(result.wall_time_s, 2),
            "answer_text": result.answer_text,
            "answers": answers,
            "score": score,
            "wrong_or_missing": wrong_or_missing,
            "raw_events_path": raw_path,
        }
        results_by_size[size] = record
        write_json(str(part_a_dir / f"run-{size}.json"), record)

        input_tok = result.usage.get("input", "n/a")
        cached_tok = result.usage.get("cacheRead", "n/a")
        output_tok = result.usage.get("output", "n/a")
        rows.append([
            size, est_tokens, input_tok, cached_tok, output_tok,
            f"{score}/5" if result.ok else "ERROR",
            ", ".join(str(x) for x in wrong_or_missing) if result.ok else "all",
            (result.error or "").replace("\n", " ")[:150],
        ])

        status = f"score={score}/5" if result.ok else f"ERROR: {result.error}"
        print(f"  estimated_input_tokens={est_tokens} real_input_tokens={input_tok} cost=${result.total_cost_usd:.4f} {status}", flush=True)

    if not results_by_size:
        print("No sizes were run.", file=sys.stderr)
        sys.exit(1)

    # Rebuild the summary from EVERY run-*.json on disk, not just the sizes this
    # invocation was asked for, so re-running a subset (e.g. just the optional
    # 2x/3x sizes) still produces a complete, correct summary.md rather than one
    # that silently drops the sizes run earlier. CANONICAL_ORDER controls the
    # column order; anything else (there shouldn't be) sorts after, alphabetically.
    CANONICAL_ORDER = ["8k", "16k", "32k", "64k", "full", "2x", "3x"]
    all_results = {}
    for path in part_a_dir.glob("run-*.json"):
        rec = json.loads(path.read_text(encoding="utf-8"))
        all_results[rec["size"]] = rec
    all_sizes = sorted(
        all_results.keys(),
        key=lambda s: (CANONICAL_ORDER.index(s) if s in CANONICAL_ORDER else len(CANONICAL_ORDER), s),
    )

    all_rows = []
    for size in all_sizes:
        r = all_results[size]
        input_tok = r["usage"].get("input", "n/a")
        cached_tok = r["usage"].get("cacheRead", "n/a")
        output_tok = r["usage"].get("output", "n/a")
        all_rows.append([
            size, r["estimated_input_tokens"], input_tok, cached_tok, output_tok,
            f"{r['score']}/5" if r["ok"] else "ERROR",
            ", ".join(str(x) for x in r["wrong_or_missing"]) if r["ok"] else "all",
            (r["error"] or "").replace("\n", " ")[:150],
        ])

    # First failure: first size, in canonical order, where score drops below
    # the best score seen so far, or the call errors outright.
    first_failure = None
    running_best = -1
    for size in all_sizes:
        r = all_results[size]
        if not r["ok"]:
            first_failure = size
            break
        if r["score"] < running_best:
            first_failure = size
            break
        running_best = max(running_best, r["score"])

    table_md = md_table(
        ["size", "est. tokens", "input tokens", "cached tokens", "output tokens", "score", "wrong/missing Qs", "error"],
        all_rows,
    )

    lines = []
    lines.append("# Part A: Context Window Stress Test -- summary")
    lines.append("")
    lines.append(f"Model: `{args.model}`")
    lines.append(f"Corpus: {word_count(full_text)} words (~{estimate_tokens(full_text)} estimated tokens)")
    lines.append(f"Compaction: disabled for this run (`work/part_a/.pi/settings.json`)")
    if "2x" in all_sizes or "3x" in all_sizes:
        lines.append(
            "Sizes 2x/3x are optional and not part of the default `--sizes`: the full corpus "
            "followed by 1 or 2 extra rounds of its own section files, reshuffled, appended as "
            "distractor padding (for models whose context window is too large for \"full\" alone "
            "to stress)."
        )
    lines.append("")
    lines.append(table_md)
    lines.append("")
    if first_failure:
        r = all_results[first_failure]
        if not r["ok"]:
            lines.append(f"**First failure at: {first_failure}** -- the call errored: {r['error']}")
        else:
            lines.append(
                f"**First failure at: {first_failure}** -- score dropped to {r['score']}/5 "
                f"(best score at an earlier, smaller size was {running_best}/5)."
            )
    else:
        lines.append("**No failure observed: score never dropped below an earlier best, and no call errored.**")
    lines.append("")

    write_text(str(part_a_dir / "summary.md"), "\n".join(lines))

    print("\n" + table_md)
    if first_failure:
        print(f"\nFirst failure at: {first_failure}")
    else:
        print("\nNo failure observed across the tested sizes.")


if __name__ == "__main__":
    main()
