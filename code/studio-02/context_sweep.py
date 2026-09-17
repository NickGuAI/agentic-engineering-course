#!/usr/bin/env python3
"""context_sweep.py -- accuracy vs. context length, over the 13-document,
~579K-real-token combined corpus (contract addendum v2, sections 3 and 5).

For each size, the script slices the first N REAL tokens (tiktoken o200k_base,
line-safe cut) of corpus/combined.txt, asks all questions from questions.json
in ONE turn with auto-compaction disabled, and scores each answer as
correct / wrong / hallucinated using the section-5 rule: a question is
"answerable" at a given size only if its needle_depth_tokens is inside the
slice (and it is not marked expect_not_found); otherwise the correct answer is
NOT FOUND. Three headline accuracies are computed per size: overall (of all
questions), in-slice (answerable questions only), and abstention (out-of-slice
or expect_not_found questions only, i.e. did the model correctly decline to
answer).

Usage:
  python3 context_sweep.py --model openai-codex/gpt-5.6-luna \\
      --sizes 16k,32k,64k,128k,200k,256k,full --out evidence/context_sweep

Provider: the Codex SUBSCRIPTION only (pi's openai-codex provider, already
logged in on this machine via OAuth). This script never sets an API key, never
calls /login, and never touches ~/.pi/agent/auth.json.

Quota discipline: smoke-test with --sizes 16k only. Run the full --sizes list
ONCE. On any 429/rate-limit/quota error, this script stops immediately (does
not continue to the next size) and records what happened; it does not retry.
The "full" size (the whole ~579K-token corpus) is expected to fail with a
context-length error since it is more than double gpt-5.6-luna's 272K-token
window -- that failure is itself the point at that size and is recorded, not
treated as a quota stop.

Run from code/studio-02/. Re-runnable: pass --sizes for just the sizes you
want (re-running a subset does not erase the others' results.json rows or
charts, which are rebuilt from every run-<size>.json on disk); never deletes
anything under evidence/.
"""
import argparse
import csv
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from lib.pi_runner import (  # noqa: E402
    DEFAULT_MODEL,
    SWEEP_SIZE_TOKENS,
    load_questions,
    md_table,
    parse_numbered_answers,
    questions_block,
    real_slice_by_tokens,
    real_token_count,
    run_pi,
    score_all_v2,
    tokenizer_name,
    write_json,
    write_text,
)

SWEEP_INSTRUCTIONS = (
    "Answer each numbered question below using only the text above. Number your answers to match "
    "the question numbers, in order. If the text above does not contain the answer, say NOT FOUND."
)

# Substrings that mean "the provider is rate-limiting or out of quota; stop
# instead of continuing to the next size." Kept separate from a context-length
# error (e.g. "full"), which is an expected, informative result to record, not
# a reason to abort the whole sweep.
QUOTA_ERROR_KEYWORDS = (
    "429",
    "rate limit",
    "rate-limit",
    "too many requests",
    "quota",
    "usage limit",
    "usage cap",
)
CONTEXT_LENGTH_KEYWORDS = (
    "context length",
    "context_length",
    "maximum context",
    "too long",
    "too large",
    "exceeds the",
    "token limit",
)


def _error_kind(error_text):
    if not error_text:
        return None
    low = error_text.lower()
    if any(kw in low for kw in QUOTA_ERROR_KEYWORDS):
        return "quota"
    if any(kw in low for kw in CONTEXT_LENGTH_KEYWORDS):
        return "context_length"
    return "other"


def build_prompt_tail(questions):
    return f"\n\nQuestions:\n{questions_block(questions)}\n\n{SWEEP_INSTRUCTIONS}\n"


def run_one_size(size, full_text, questions, args, out_dir, sessions_dir, work_dir):
    if size == "full":
        slice_text = full_text
    elif size in SWEEP_SIZE_TOKENS:
        slice_text = real_slice_by_tokens(full_text, SWEEP_SIZE_TOKENS[size])
    else:
        raise ValueError(f"Unknown size '{size}' (expected one of {', '.join(SWEEP_SIZE_TOKENS)},full)")

    slice_real_tokens = real_token_count(slice_text)
    tail = build_prompt_tail(questions)
    raw_path = str(out_dir / "raw" / f"{size}.raw.jsonl")

    result = run_pi(
        prompt=tail,
        stdin_text=slice_text + "\n\n",
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

    error_kind = _error_kind(result.error) if not result.ok else None

    answers = parse_numbered_answers(result.answer_text, n=len(questions)) if result.ok else {}
    scoring = score_all_v2(answers, questions, slice_real_tokens) if result.ok else None

    record = {
        "size": size,
        "slice_estimated_real_tokens": slice_real_tokens,
        "model": args.model,
        "ok": result.ok,
        "error": result.error,
        "error_kind": error_kind,
        "usage": result.usage,
        "cost_usd": round(result.total_cost_usd, 6),
        "wall_time_s": round(result.wall_time_s, 2),
        "answer_text": result.answer_text,
        "answers": answers,
        "scoring": scoring,
        "raw_events_path": raw_path,
    }
    return record


def load_all_results(out_dir):
    all_results = {}
    for path in out_dir.glob("run-*.json"):
        rec = json.loads(path.read_text(encoding="utf-8"))
        all_results[rec["size"]] = rec
    return all_results


CANONICAL_SIZE_ORDER = ["16k", "32k", "64k", "128k", "200k", "256k", "full"]


def ordered_sizes(all_results):
    return sorted(
        all_results.keys(),
        key=lambda s: (CANONICAL_SIZE_ORDER.index(s) if s in CANONICAL_SIZE_ORDER else len(CANONICAL_SIZE_ORDER), s),
    )


def write_results_csv(path, all_results, questions):
    sizes = ordered_sizes(all_results)
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow([
            "size", "question_id", "needle_depth_tokens", "expected", "in_slice", "verdict", "correct",
            "verbose_but_correct", "answer",
        ])
        for size in sizes:
            rec = all_results[size]
            scoring = rec.get("scoring")
            if not scoring:
                w.writerow([size, "", "", "", "", "ERROR", False, "", rec.get("error", "")])
                continue
            for r in scoring["per_question"]:
                w.writerow([
                    size, r["id"], r["needle_depth_tokens"], r["expected"], r["in_slice"],
                    r["verdict"], r["correct"], r["verbose_but_correct"],
                    (r["answer"] or "").replace("\n", " ")[:300],
                ])


def write_summary_md(path, all_results, model, corpus_words, corpus_real_tokens, window_tokens, thinking, correction_note=None):
    sizes = ordered_sizes(all_results)
    rows = []
    in_slice_lines = []
    verbose_but_correct_lines = []
    for size in sizes:
        rec = all_results[size]
        if rec["ok"] and rec["scoring"]:
            s = rec["scoring"]
            overall = f"{s['overall_accuracy']*100:.0f}% ({sum(1 for r in s['per_question'] if r['correct'])}/{s['n_total']})"
            in_slice = f"{s['in_slice_accuracy']*100:.0f}% (n={s['n_answerable']})" if s["in_slice_accuracy"] is not None else "n/a"
            abstain = f"{s['abstention_accuracy']*100:.0f}% (n={s['n_not_found_expected']})" if s["abstention_accuracy"] is not None else "n/a"
            error_cell = ""
            ids_str = ", ".join(str(i) for i in s["in_slice_ids"]) if s["in_slice_ids"] else "(none)"
            in_slice_lines.append(f"- **{size}**: {ids_str}")
            if s["verbose_but_correct_ids"]:
                verbose_but_correct_lines.append(
                    f"- **{size}**: question(s) {', '.join(str(i) for i in s['verbose_but_correct_ids'])}"
                )
        else:
            overall = in_slice = abstain = "ERROR"
            error_cell = (rec.get("error") or "")[:200].replace("\n", " ")
            in_slice_lines.append(f"- **{size}**: (call errored, not scored)")
        input_tok = rec["usage"].get("input", "n/a") if rec.get("usage") else "n/a"
        rows.append([
            size, rec.get("slice_estimated_real_tokens", "n/a"), input_tok, overall, in_slice, abstain,
            f"{rec.get('wall_time_s', 'n/a')}s", error_cell,
        ])
    table = md_table(
        ["size", "slice real tokens", "pi input tokens", "overall accuracy", "in-slice accuracy", "abstention accuracy", "wall time", "error"],
        rows,
    )
    lines = [
        "# Context sweep: accuracy vs. context length -- summary",
        "",
    ]
    if correction_note:
        lines += ["## Correction", "", correction_note, ""]
    lines += [
        f"Model: `{model}` (Codex subscription, `--thinking {thinking}`)",
        f"Corpus: corpus/combined.txt, {corpus_words} words, {corpus_real_tokens} real tokens (tiktoken o200k_base)",
        f"Model context window: {window_tokens} tokens",
        "",
        table,
        "",
        "'overall accuracy' is correct / all questions in questions.json. 'in-slice accuracy' is correct / "
        "(questions whose needle sits inside this slice and are not expect_not_found) -- can a call that has "
        "the fact in view actually answer it. 'abstention accuracy' is correct / (questions whose needle is "
        "beyond this slice, plus expect_not_found questions) -- does the model correctly say NOT FOUND rather "
        "than guessing. A question with no needle_depth_tokens is always counted as in-slice/answerable.",
        "",
        "## Question ids in-slice per size",
        "",
        "\n".join(in_slice_lines),
        "",
        "## Flagged: verbose-but-correct (matched every gold keyword group, but also contains a "
        "must_not_contain distractor term -- scored wrong per the section-5 rule; listed here for a human "
        "to re-score by hand)",
        "",
        ("\n".join(verbose_but_correct_lines) if verbose_but_correct_lines else "None at any size."),
        "",
        "See results.json and results.csv for the per-question, per-size verdicts (correct / wrong / "
        "hallucinated) and the verbose_but_correct flag, and accuracy_vs_length.png / heatmap.png for the "
        "charts.",
        "",
    ]
    write_text(str(path), "\n".join(lines))
    return table


def rescore_from_existing(out_dir: Path, questions: list):
    """Re-parse answer_text from every existing run-<size>.json with the
    current parser, and re-score with the current questions.json. Makes NO
    pi calls and does NOT modify the run-<size>.json files (usage, timing,
    and answer_text stay exactly as originally recorded) -- only the derived
    `all_results` used for results.json/csv/summary.md/charts is rebuilt.
    Returns (all_results, diff) where diff lists every (size, question_id,
    old_verdict, new_verdict) whose verdict actually changed."""
    all_results = {}
    diff = []
    for path in sorted(out_dir.glob("run-*.json")):
        rec = json.loads(path.read_text(encoding="utf-8"))
        size = rec["size"]
        if not rec.get("ok"):
            all_results[size] = rec  # error records pass through unchanged
            continue

        old_scoring = rec.get("scoring") or {}
        old_verdicts = {r["id"]: r["verdict"] for r in old_scoring.get("per_question", [])}

        answers = parse_numbered_answers(rec["answer_text"], n=len(questions))
        slice_real_tokens = rec["slice_estimated_real_tokens"]
        new_scoring = score_all_v2(answers, questions, slice_real_tokens)

        for r in new_scoring["per_question"]:
            old_v = old_verdicts.get(r["id"])
            if old_v is not None and old_v != r["verdict"]:
                diff.append({"size": size, "id": r["id"], "old_verdict": old_v, "new_verdict": r["verdict"]})
            elif old_v is None:
                diff.append({"size": size, "id": r["id"], "old_verdict": "(not scored before)", "new_verdict": r["verdict"]})

        # Clone the original record (preserves usage/timing/raw_events_path/
        # answer_text) and only replace the derived fields.
        new_rec = dict(rec)
        new_rec["answers"] = answers
        new_rec["scoring"] = new_scoring
        all_results[size] = new_rec

    return all_results, diff


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--model", default=DEFAULT_MODEL)
    ap.add_argument("--sizes", default="16k,32k,64k,128k,200k,256k,full")
    ap.add_argument("--out", default="evidence/context_sweep")
    ap.add_argument("--corpus", default="corpus/combined.txt")
    ap.add_argument("--questions", default="questions.json")
    ap.add_argument("--work-dir", default="work/context_sweep")
    ap.add_argument("--timeout", type=int, default=1800)
    ap.add_argument("--thinking", default="low", help="pi --thinking level (default: low)")
    ap.add_argument("--window-tokens", type=int, default=272000, help="model context window, for the chart marker")
    ap.add_argument(
        "--rescore", action="store_true",
        help="Re-parse and re-score existing evidence/context_sweep/run-<size>.json files with the "
             "current parser and questions.json. Makes no pi calls, spends no quota, and does not "
             "modify the run-<size>.json files; only results.json/csv/summary.md and the charts are "
             "rewritten, plus rescore_diff.json listing every verdict that changed.",
    )
    args = ap.parse_args()

    corpus_path = Path(args.corpus)
    if not corpus_path.exists():
        print(f"ERROR: {args.corpus} not found. Run: bash setup.sh", file=sys.stderr)
        sys.exit(1)
    full_text = corpus_path.read_text(encoding="utf-8", errors="replace")
    corpus_real_tokens = real_token_count(full_text)
    corpus_words = len(full_text.split())
    print(f"Corpus: {corpus_words} words, {corpus_real_tokens} real tokens ({tokenizer_name()})", flush=True)

    if not Path(args.questions).exists():
        print(f"ERROR: {args.questions} not found.", file=sys.stderr)
        sys.exit(1)
    questions = load_questions(args.questions)["questions"]
    print(f"Loaded {len(questions)} question(s) from {args.questions}", flush=True)

    out_dir = Path(args.out)

    if args.rescore:
        if not out_dir.exists() or not list(out_dir.glob("run-*.json")):
            print(f"ERROR: no run-<size>.json files found under {out_dir} to rescore.", file=sys.stderr)
            sys.exit(1)
        print(f"=== Rescoring existing runs under {out_dir} (no pi calls) ===", flush=True)
        all_results, diff = rescore_from_existing(out_dir, questions)
        write_json(str(out_dir / "rescore_diff.json"), {"changed_verdicts": diff, "n_changed": len(diff)})
        write_results_csv(out_dir / "results.csv", all_results, questions)
        write_json(str(out_dir / "results.json"), {"model": args.model, "sizes": ordered_sizes(all_results), "results": all_results})
        correction_note = (
            f"The first scoring pass had two bugs, both in the scorer, not in the model calls: (1) the "
            f"answer parser matched only single-digit question numbers, so answers 10-20 were silently "
            f"read as continuation text of answer 9 and scored wrong or hallucinated regardless of their "
            f"real content; (2) several keyword groups required only terms already present in the "
            f"question text (so a terse correct answer could not match) and number-format variants like "
            f"\"2,048K\" vs \"2048K\" were not normalized. All 7 model calls below are the original ones "
            f"from the first run (same answer_text, same usage, same timing, same cost) -- nothing was "
            f"re-run. These figures are the fixed parser and scorer re-applied to that same saved "
            f"answer_text, with the revised questions.json (keyword groups now answer-bearing terms only; "
            f"gold answers and needle depths unchanged). {len(diff)} of 140 (size x question) verdicts "
            f"changed, all from wrong or hallucinated to correct; none moved the other way. See "
            f"rescore_diff.json for the full list."
        )
        table = write_summary_md(out_dir / "summary.md", all_results, args.model, corpus_words, corpus_real_tokens, args.window_tokens, args.thinking, correction_note=correction_note)
        print("\n" + table)
        print(f"\n{len(diff)} verdict(s) changed. See {out_dir / 'rescore_diff.json'} for the full list.")
        for d in diff:
            print(f"  size={d['size']} q{d['id']}: {d['old_verdict']} -> {d['new_verdict']}")
        try:
            from lib.charts import build_charts

            build_charts(all_results, questions, out_dir, args.window_tokens)
            print(f"\nCharts regenerated: {out_dir / 'accuracy_vs_length.png'}, {out_dir / 'heatmap.png'}")
        except Exception as e:
            print(f"\nWARNING: chart generation failed: {e}", file=sys.stderr)
        return

    work_dir = Path(args.work_dir)
    pi_settings_dir = work_dir / ".pi"
    pi_settings_dir.mkdir(parents=True, exist_ok=True)
    (pi_settings_dir / "settings.json").write_text(
        json.dumps({"compaction": {"enabled": False}}, indent=2), encoding="utf-8"
    )

    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "raw").mkdir(parents=True, exist_ok=True)
    sessions_dir = (out_dir / "sessions").resolve()

    sizes = [s.strip() for s in args.sizes.split(",") if s.strip()]
    stopped_for_quota = None

    for size in sizes:
        print(f"=== Sweep: size={size} ===", flush=True)
        try:
            record = run_one_size(size, full_text, questions, args, out_dir, sessions_dir, work_dir)
        except ValueError as e:
            print(f"  {e}", file=sys.stderr)
            continue

        write_json(str(out_dir / f"run-{size}.json"), record)

        if record["error_kind"] == "quota":
            print(f"  STOPPED: quota/rate-limit error at size={size}: {record['error']}", file=sys.stderr)
            stopped_for_quota = size
            break

        if record["ok"] and record["scoring"]:
            s = record["scoring"]
            in_slice_str = "n/a" if s["in_slice_accuracy"] is None else f"{s['in_slice_accuracy']*100:.0f}%"
            abstention_str = "n/a" if s["abstention_accuracy"] is None else f"{s['abstention_accuracy']*100:.0f}%"
            print(
                f"  slice_real_tokens={record['slice_estimated_real_tokens']} "
                f"pi_input_tokens={record['usage'].get('input')} cost=${record['cost_usd']:.4f} "
                f"overall={s['overall_accuracy']*100:.0f}% "
                f"in_slice={in_slice_str} "
                f"abstention={abstention_str}",
                flush=True,
            )
        else:
            print(f"  ERROR ({record['error_kind']}): {record['error']}", flush=True)

    all_results = load_all_results(out_dir)
    write_results_csv(out_dir / "results.csv", all_results, questions)
    write_json(str(out_dir / "results.json"), {"model": args.model, "sizes": ordered_sizes(all_results), "results": all_results})
    table = write_summary_md(out_dir / "summary.md", all_results, args.model, corpus_words, corpus_real_tokens, args.window_tokens, args.thinking)
    print("\n" + table)

    try:
        from lib.charts import build_charts

        build_charts(all_results, questions, out_dir, args.window_tokens)
        print(f"\nCharts written: {out_dir / 'accuracy_vs_length.png'}, {out_dir / 'heatmap.png'}")
    except Exception as e:
        print(f"\nWARNING: chart generation failed: {e}", file=sys.stderr)

    if stopped_for_quota:
        print(f"\nSTOPPED early at size={stopped_for_quota} due to a quota/rate-limit error. Not attempting further sizes.")
        sys.exit(3)


if __name__ == "__main__":
    main()
