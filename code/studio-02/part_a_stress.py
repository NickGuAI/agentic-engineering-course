#!/usr/bin/env python3
"""Part A: Context Window Stress Test.

Loads an increasing slice of the corpus plus the questions in ONE turn, with
pi's auto-compaction disabled (via a project .pi/settings.json), and records
where the score degrades or the call fails outright.

Since contract addendum v2 section 7, Part A defaults to the same 13-document
combined corpus and the same real-token slicing and section-5 scoring as
context_sweep.py (shared code in lib/pi_runner.py: real_slice_by_tokens,
score_all_v2), just with a shorter, cheaper size list -- this is the quick,
default-quota-friendly version of the same stress test the sweep runs in
full. Questions without needle_depth_tokens are always counted as
in-slice/answerable (see lib/pi_runner.py score_question_v2).

Usage:
  python3 part_a_stress.py --model openai-codex/gpt-5.6-luna \\
      --sizes 64k,128k,256k,full --out evidence

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
    SWEEP_SIZE_TOKENS,
    build_distractor_padded_corpus,
    estimate_tokens,
    load_questions,
    md_table,
    parse_numbered_answers,
    questions_block,
    real_slice_by_tokens,
    real_token_count,
    run_pi,
    score_all_v2,
    word_count,
    write_json,
    write_text,
)

# Real-token budget for every size label Part A has ever accepted. SWEEP_SIZE_TOKENS
# (16k..256k) takes priority; 8k/32k's legacy-only labels fall back to
# SIZE_TOKEN_BUDGETS so old `--sizes 8k,...` invocations still work. Both are
# sliced with real_slice_by_tokens (tiktoken) now, not the old word estimate.
ALL_SIZE_TOKENS = {**SIZE_TOKEN_BUDGETS, **SWEEP_SIZE_TOKENS}


def build_prompt(slice_text: str, questions: list) -> str:
    return (
        f"{slice_text}\n\n"
        f"Questions:\n{questions_block(questions)}\n\n"
        f"{ANSWER_INSTRUCTIONS}\n"
    )


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--model", default=DEFAULT_MODEL, help=f"provider/model-id (default: {DEFAULT_MODEL})")
    ap.add_argument("--sizes", default="64k,128k,256k,full", help="comma-separated sizes to test")
    ap.add_argument("--out", default="evidence", help="output directory (default: evidence)")
    ap.add_argument("--corpus", default="corpus/combined.txt")
    ap.add_argument("--work-dir", default="work/part_a", help="scratch cwd for the pi process (holds .pi/settings.json)")
    ap.add_argument("--timeout", type=int, default=1800)
    ap.add_argument("--thinking", default="low")
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
    results_by_size = {}

    for size in sizes:
        print(f"=== Part A: size={size} ===", flush=True)
        if size == "full":
            slice_text = full_text
        elif size in ("2x", "3x"):
            # Optional sizes past "full": the whole corpus plus (multiplier - 1)
            # rounds of its own section files, reshuffled, appended as distractor
            # padding. Not part of the default --sizes list.
            multiplier = int(size[0])
            slice_text = build_distractor_padded_corpus(full_text, "corpus/sections", multiplier)
        elif size in ALL_SIZE_TOKENS:
            slice_text = real_slice_by_tokens(full_text, ALL_SIZE_TOKENS[size])
        else:
            print(f"Unknown size '{size}', skipping (expected one of {', '.join(sorted(ALL_SIZE_TOKENS))},full,2x,3x)", file=sys.stderr)
            continue

        slice_real_tokens = real_token_count(slice_text)
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
            thinking=args.thinking,
        )

        answers = parse_numbered_answers(result.answer_text, n=len(questions)) if result.ok else {}
        scoring = score_all_v2(answers, questions, slice_real_tokens) if result.ok else None

        record = {
            "size": size,
            "slice_estimated_real_tokens": slice_real_tokens,
            "model": args.model,
            "ok": result.ok,
            "error": result.error,
            "usage": result.usage,
            "cost_usd": round(result.total_cost_usd, 6),
            "wall_time_s": round(result.wall_time_s, 2),
            "answer_text": result.answer_text,
            "answers": answers,
            "scoring": scoring,
            "raw_events_path": raw_path,
        }
        results_by_size[size] = record
        write_json(str(part_a_dir / f"run-{size}.json"), record)

        input_tok = result.usage.get("input", "n/a")
        if result.ok and scoring:
            print(
                f"  slice_real_tokens={slice_real_tokens} pi_input_tokens={input_tok} "
                f"cost=${result.total_cost_usd:.4f} overall={scoring['overall_accuracy']*100:.0f}%",
                flush=True,
            )
        else:
            print(f"  slice_real_tokens={slice_real_tokens} pi_input_tokens={input_tok} ERROR: {result.error}", flush=True)

    if not results_by_size:
        print("No sizes were run.", file=sys.stderr)
        sys.exit(1)

    # Rebuild the summary from EVERY run-*.json on disk, not just the sizes this
    # invocation was asked for, so re-running a subset still produces a
    # complete, correct summary.md rather than one that silently drops the
    # sizes run earlier. CANONICAL_ORDER controls the column order.
    CANONICAL_ORDER = ["8k", "16k", "32k", "64k", "128k", "200k", "256k", "full", "2x", "3x"]
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
        if r["ok"] and r.get("scoring"):
            s = r["scoring"]
            overall = f"{s['overall_accuracy']*100:.0f}% ({sum(1 for x in s['per_question'] if x['correct'])}/{s['n_total']})"
            error_cell = ""
        else:
            overall = "ERROR"
            error_cell = (r.get("error") or "").replace("\n", " ")[:150]
        all_rows.append([size, r.get("slice_estimated_real_tokens", "n/a"), input_tok, overall, f"{r.get('wall_time_s', 'n/a')}s", error_cell])

    # First failure: first size, in canonical order, where overall accuracy
    # drops below the best seen so far, or the call errors outright.
    first_failure = None
    running_best = -1.0
    for size in all_sizes:
        r = all_results[size]
        if not r["ok"] or not r.get("scoring"):
            first_failure = size
            break
        acc = r["scoring"]["overall_accuracy"]
        if acc < running_best:
            first_failure = size
            break
        running_best = max(running_best, acc)

    table_md = md_table(["size", "slice real tokens", "pi input tokens", "overall accuracy", "wall time", "error"], all_rows)

    lines = []
    lines.append("# Part A: Context Window Stress Test -- summary")
    lines.append("")
    lines.append(f"Model: `{args.model}`")
    lines.append(f"Corpus: {args.corpus}, {word_count(full_text)} words (~{estimate_tokens(full_text)} estimated tokens, "
                  f"{real_token_count(full_text)} real tokens)")
    lines.append("Compaction: disabled for this run (`work/part_a/.pi/settings.json`)")
    if "2x" in all_sizes or "3x" in all_sizes:
        lines.append(
            "Sizes 2x/3x are optional and not part of the default `--sizes`: the full corpus "
            "followed by 1 or 2 extra rounds of its own section files, reshuffled, appended as "
            "distractor padding."
        )
    lines.append("")
    lines.append(table_md)
    lines.append("")
    if first_failure:
        r = all_results[first_failure]
        if not r["ok"] or not r.get("scoring"):
            lines.append(f"**First failure at: {first_failure}** -- the call errored: {r['error']}")
        else:
            lines.append(
                f"**First failure at: {first_failure}** -- overall accuracy dropped to "
                f"{r['scoring']['overall_accuracy']*100:.0f}% (best at an earlier, smaller size was {running_best*100:.0f}%)."
            )
    else:
        lines.append("**No failure observed: accuracy never dropped below an earlier best, and no call errored.**")
    lines.append("")

    write_text(str(part_a_dir / "summary.md"), "\n".join(lines))

    print("\n" + table_md)
    if first_failure:
        print(f"\nFirst failure at: {first_failure}")
    else:
        print("\nNo failure observed across the tested sizes.")


if __name__ == "__main__":
    main()
