#!/usr/bin/env python3
"""Part B: fix Part A with Isolate and Compress.

Three demonstrations, each scored the same way as Part A:

  1. Isolate: one pi sub-agent per corpus section returns short findings only;
     a lead pi process answers the five questions from the findings alone.
  2. Compress (summary artifact): pi writes a short briefing from Part A's best
     run, then the five questions are re-asked with only that briefing as context.
  3. Compress (pi's own auto-compaction): the corpus is read section-by-section
     through tool calls in a work dir whose .pi/settings.json lowers the
     compaction threshold so compaction fires mid-run; the five questions are
     asked after compaction.

Usage:
  python3 part_b_isolate_compress.py --model google/gemini-3.1-flash-lite --out evidence

Run from code/studio-02/. Requires evidence/part_a/run-*.json to exist for the
summary-artifact demonstration (run part_a_stress.py first). Re-runnable.
"""
import argparse
import glob
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from lib.pi_runner import (  # noqa: E402
    ANSWER_INSTRUCTIONS,
    DEFAULT_MODEL,
    estimate_tokens,
    load_questions,
    md_table,
    model_context_window,
    parse_numbered_answers,
    questions_block,
    run_pi,
    score_all,
    word_count,
    write_json,
    write_text,
)

ISOLATE_INSTRUCTIONS = (
    "Read the section of the survey above. Return ONLY a numbered list (1 to 5, one line per "
    "question below) of findings from THIS section that are relevant to each question. If this "
    "section has nothing relevant to a question, write 'nothing relevant in this section' for "
    "that number. At most 150 words total. Do not summarize or transcribe the section itself, "
    "and do not answer questions this section does not address."
)


def load_part_a_best(out_dir: Path):
    """Return the record dict for the best successful Part A run: highest score
    first, and among ties the smallest estimated_input_tokens (the cheapest run
    that already reached that score) -- not glob/filename order, which changed
    meaning once the optional 2x/3x sizes started sorting before 32k/64k/full."""
    part_a_dir = out_dir / "part_a"
    best = None
    for path in sorted(part_a_dir.glob("run-*.json")):
        rec = json.loads(path.read_text(encoding="utf-8"))
        if not rec.get("ok"):
            continue
        if best is None or (
            rec["score"] > best["score"]
            or (rec["score"] == best["score"] and rec["estimated_input_tokens"] < best["estimated_input_tokens"])
        ):
            best = rec
    return best


def run_isolate(model, questions, out_dir, sessions_dir, timeout):
    sections = sorted(Path("corpus/sections").glob("section-*.txt"))
    if not sections:
        print("ERROR: no corpus/sections/section-*.txt found. Run: bash setup.sh", file=sys.stderr)
        sys.exit(1)

    findings_dir = out_dir / "part_b" / "findings"
    findings_dir.mkdir(parents=True, exist_ok=True)
    raw_dir = out_dir / "part_b" / "raw"
    raw_dir.mkdir(parents=True, exist_ok=True)

    subagent_records = []
    concatenated_findings = []

    for sec_path in sections:
        sec_text = sec_path.read_text(encoding="utf-8", errors="replace")
        prompt = f"{sec_text}\n\nQuestions:\n{questions_block(questions)}\n\n{ISOLATE_INSTRUCTIONS}\n"
        raw_path = str(raw_dir / f"isolate-{sec_path.stem}.raw.jsonl")
        print(f"  isolate sub-agent: {sec_path.name} ...", flush=True)
        result = run_pi(
            prompt=prompt,
            cwd="work/part_b/isolate",
            model=model,
            no_tools=True,
            session_dir=str(sessions_dir),
            raw_events_path=raw_path,
            timeout=timeout,
            approve=True,
            no_context_files=True,
        )
        findings_text = result.answer_text if result.ok else f"[ERROR: {result.error}]"
        write_text(str(findings_dir / f"{sec_path.stem}.md"), findings_text)
        concatenated_findings.append(f"## Findings from {sec_path.name}\n{findings_text}\n")

        rec = {
            "section": sec_path.name,
            "ok": result.ok,
            "error": result.error,
            "usage": result.usage,
            "cost_usd": round(result.total_cost_usd, 6),
            "wall_time_s": round(result.wall_time_s, 2),
        }
        subagent_records.append(rec)
        print(f"    input={result.usage.get('input', 'n/a')} output={result.usage.get('output', 'n/a')} cost=${result.total_cost_usd:.4f}", flush=True)

    lead_prompt = (
        "\n".join(concatenated_findings)
        + f"\n\nQuestions:\n{questions_block(questions)}\n\n{ANSWER_INSTRUCTIONS}\n"
    )
    lead_raw_path = str(raw_dir / "isolate-lead.raw.jsonl")
    print("  isolate lead process ...", flush=True)
    lead_result = run_pi(
        prompt=lead_prompt,
        cwd="work/part_b/isolate",
        model=model,
        no_tools=True,
        session_dir=str(sessions_dir),
        raw_events_path=lead_raw_path,
        timeout=timeout,
        approve=True,
        no_context_files=True,
    )
    answers = parse_numbered_answers(lead_result.answer_text, n=5) if lead_result.ok else {}
    score, wrong = score_all(answers, questions) if lead_result.ok else (0, [q["id"] for q in questions])

    record = {
        "subagents": subagent_records,
        "lead": {
            "ok": lead_result.ok,
            "error": lead_result.error,
            "usage": lead_result.usage,
            "cost_usd": round(lead_result.total_cost_usd, 6),
            "wall_time_s": round(lead_result.wall_time_s, 2),
            "answer_text": lead_result.answer_text,
            "answers": answers,
            "score": score,
            "wrong_or_missing": wrong,
            "input_tokens": lead_result.usage.get("input"),
        },
        "total_cost_usd": round(sum(r["cost_usd"] for r in subagent_records) + lead_result.total_cost_usd, 6),
    }
    write_json(str(out_dir / "part_b" / "isolate.json"), record)
    print(f"  isolate lead score={score}/5 input_tokens={lead_result.usage.get('input', 'n/a')}", flush=True)
    return record


def run_compress_summary(model, questions, out_dir, sessions_dir, timeout):
    best = load_part_a_best(out_dir)
    if best is None:
        print("ERROR: no successful Part A run found under evidence/part_a/. Run part_a_stress.py first.", file=sys.stderr)
        sys.exit(1)

    wrong_list = ", ".join(str(x) for x in best["wrong_or_missing"]) or "none"
    briefing_prompt = (
        f"A language model answered five numbered questions about a survey paper after reading "
        f"only part of it (a {best['size']} slice, ~{best['estimated_input_tokens']} tokens). "
        f"Its answers were:\n\n{best['answer_text']}\n\n"
        f"Questions it got wrong or could not find: {wrong_list}\n\n"
        "Write a concise markdown briefing, at most 200 words, that keeps every concrete fact, "
        "number, and name from the answers above that was actually found (do not invent facts), "
        "and clearly lists which question numbers are still unanswered. This briefing will be the "
        "ONLY context given to answer the same five questions again, so preserve wording precisely "
        "for anything you keep. Output only the briefing in markdown, nothing else."
    )
    raw_path = str(out_dir / "part_b" / "raw" / "summary-writer.raw.jsonl")
    print(f"  writing summary-of-part-a.md from Part A's best run ({best['size']}, score {best['score']}/5) ...", flush=True)
    writer_result = run_pi(
        prompt=briefing_prompt,
        cwd="work/part_b/summary",
        model=model,
        no_tools=True,
        session_dir=str(sessions_dir),
        raw_events_path=raw_path,
        timeout=timeout,
        approve=True,
        no_context_files=True,
    )
    summary_text = writer_result.answer_text if writer_result.ok else f"[ERROR writing summary: {writer_result.error}]"
    write_text(str(out_dir / "part_b" / "summary-of-part-a.md"), summary_text)
    summary_tokens = estimate_tokens(summary_text)

    reask_prompt = f"{summary_text}\n\nQuestions:\n{questions_block(questions)}\n\n{ANSWER_INSTRUCTIONS}\n"
    reask_raw_path = str(out_dir / "part_b" / "raw" / "summary-reask.raw.jsonl")
    print("  re-asking the five questions with only the summary as context ...", flush=True)
    reask_result = run_pi(
        prompt=reask_prompt,
        cwd="work/part_b/summary",
        model=model,
        no_tools=True,
        session_dir=str(sessions_dir),
        raw_events_path=reask_raw_path,
        timeout=timeout,
        approve=True,
        no_context_files=True,
    )
    answers = parse_numbered_answers(reask_result.answer_text, n=5) if reask_result.ok else {}
    score, wrong = score_all(answers, questions) if reask_result.ok else (0, [q["id"] for q in questions])

    record = {
        "based_on_part_a_size": best["size"],
        "based_on_part_a_score": best["score"],
        "summary_writer": {
            "ok": writer_result.ok,
            "error": writer_result.error,
            "usage": writer_result.usage,
            "cost_usd": round(writer_result.total_cost_usd, 6),
        },
        "summary_text": summary_text,
        "summary_estimated_tokens": summary_tokens,
        "reask": {
            "ok": reask_result.ok,
            "error": reask_result.error,
            "usage": reask_result.usage,
            "cost_usd": round(reask_result.total_cost_usd, 6),
            "answer_text": reask_result.answer_text,
            "answers": answers,
            "score": score,
            "wrong_or_missing": wrong,
            "input_tokens": reask_result.usage.get("input"),
        },
        "total_cost_usd": round(writer_result.total_cost_usd + reask_result.total_cost_usd, 6),
    }
    write_json(str(out_dir / "part_b" / "summary-artifact.json"), record)
    print(f"  summary-artifact score={score}/5 summary_tokens~={summary_tokens} reask_input_tokens={reask_result.usage.get('input', 'n/a')}", flush=True)
    return record


def run_compress_compaction(model, questions, out_dir, sessions_dir, timeout, target_threshold=50000):
    sections = sorted(Path("corpus/sections").glob("section-*.txt"))
    if not sections:
        print("ERROR: no corpus/sections/section-*.txt found. Run: bash setup.sh", file=sys.stderr)
        sys.exit(1)

    work_dir = Path("work/part_b/compaction")
    work_corpus_dir = work_dir / "corpus" / "sections"
    work_corpus_dir.mkdir(parents=True, exist_ok=True)
    for sec_path in sections:
        (work_corpus_dir / sec_path.name).write_text(
            sec_path.read_text(encoding="utf-8", errors="replace"), encoding="utf-8"
        )

    provider, model_id = (model.split("/", 1) + [""])[:2] if "/" in model else ("", model)
    context_window = model_context_window(provider, model_id) or 128000
    reserve_tokens = max(1024, context_window - target_threshold)
    keep_recent_tokens = 10000

    pi_settings_dir = work_dir / ".pi"
    pi_settings_dir.mkdir(parents=True, exist_ok=True)
    (pi_settings_dir / "settings.json").write_text(
        json.dumps(
            {"compaction": {"enabled": True, "reserveTokens": reserve_tokens, "keepRecentTokens": keep_recent_tokens}},
            indent=2,
        ),
        encoding="utf-8",
    )

    file_list = ", ".join(f"corpus/sections/{p.name}" for p in sections)
    prompt = (
        f"Using the read tool, read these files IN ORDER, one at a time: {file_list}. "
        "After you have read all of them, answer the five numbered questions below using only "
        "what you read. Number your answers 1 to 5. If you did not find the answer in what you "
        "read, say NOT FOUND.\n\n"
        f"Questions:\n{questions_block(questions)}\n\n{ANSWER_INSTRUCTIONS}\n"
    )
    raw_path = str(out_dir / "part_b" / "raw" / "compaction-run.raw.jsonl")
    print(
        f"  compaction demo: context_window={context_window} reserveTokens={reserve_tokens} "
        f"(threshold ~{context_window - reserve_tokens}) keepRecentTokens={keep_recent_tokens} ...",
        flush=True,
    )
    result = run_pi(
        prompt=prompt,
        cwd=str(work_dir),
        model=model,
        tools="read,ls",
        session_dir=str(sessions_dir),
        raw_events_path=raw_path,
        timeout=timeout,
        approve=True,
        no_context_files=True,
    )
    answers = parse_numbered_answers(result.answer_text, n=5) if result.ok else {}
    score, wrong = score_all(answers, questions) if result.ok else (0, [q["id"] for q in questions])

    compactions = []
    for ev in result.compactions:
        # `compaction_start` carries only {type, reason}; the token count and
        # summary are attached to the matching `compaction_end` event, nested
        # under `result` (confirmed by inspecting a real run's raw event log).
        inner = ev.get("result") or {}
        compactions.append({
            "type": ev.get("type"),
            "reason": ev.get("reason"),
            "tokensBefore": inner.get("tokensBefore"),
            "estimatedTokensAfter": inner.get("estimatedTokensAfter"),
            "raw": ev,
        })

    record = {
        "model": model,
        "context_window": context_window,
        "reserve_tokens": reserve_tokens,
        "keep_recent_tokens": keep_recent_tokens,
        "threshold_tokens": context_window - reserve_tokens,
        "ok": result.ok,
        "error": result.error,
        "usage": result.usage,
        "cost_usd": round(result.total_cost_usd, 6),
        "wall_time_s": round(result.wall_time_s, 2),
        "compactions": compactions,
        "num_compactions": len([c for c in compactions if c["type"] == "compaction_start"]),
        "answer_text": result.answer_text,
        "answers": answers,
        "score": score,
        "wrong_or_missing": wrong,
        "input_tokens": result.usage.get("input"),
    }
    write_json(str(out_dir / "part_b" / "compaction.json"), record)
    print(
        f"  compaction-demo score={score}/5 compactions={record['num_compactions']} "
        f"final_input_tokens={result.usage.get('input', 'n/a')}",
        flush=True,
    )
    return record


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--model", default=DEFAULT_MODEL)
    ap.add_argument("--out", default="evidence")
    ap.add_argument("--timeout", type=int, default=1200)
    ap.add_argument("--compaction-threshold", type=int, default=50000, help="target token count at which compaction should fire")
    args = ap.parse_args()

    if not Path("questions.json").exists():
        print("ERROR: questions.json not found. Run from code/studio-02/.", file=sys.stderr)
        sys.exit(1)
    questions = load_questions("questions.json")["questions"]

    out_dir = Path(args.out)
    (out_dir / "part_b").mkdir(parents=True, exist_ok=True)
    sessions_dir = (out_dir / "sessions").resolve()

    print("=== Part B (1/3): Isolate ===", flush=True)
    isolate_rec = run_isolate(args.model, questions, out_dir, sessions_dir, args.timeout)

    print("=== Part B (2/3): Compress -- summary artifact ===", flush=True)
    summary_rec = run_compress_summary(args.model, questions, out_dir, sessions_dir, args.timeout)

    print("=== Part B (3/3): Compress -- pi's own compaction ===", flush=True)
    compaction_rec = run_compress_compaction(args.model, questions, out_dir, sessions_dir, args.timeout, args.compaction_threshold)

    best = load_part_a_best(out_dir)
    rows = [
        [
            f"Part A best ({best['size'] if best else 'n/a'})",
            f"{best['score']}/5" if best else "n/a",
            best["usage"].get("input", "n/a") if best else "n/a",
            f"${best['cost_usd']:.4f}" if best else "n/a",
        ],
        [
            "Isolate (lead, from findings)",
            f"{isolate_rec['lead']['score']}/5" if isolate_rec["lead"]["ok"] else "ERROR",
            isolate_rec["lead"]["input_tokens"] if isolate_rec["lead"]["ok"] else "n/a",
            f"${isolate_rec['total_cost_usd']:.4f}",
        ],
        [
            "Compress: summary artifact",
            f"{summary_rec['reask']['score']}/5" if summary_rec["reask"]["ok"] else "ERROR",
            f"{summary_rec['reask']['input_tokens']} (summary ~{summary_rec['summary_estimated_tokens']} tok)" if summary_rec["reask"]["ok"] else "n/a",
            f"${summary_rec['total_cost_usd']:.4f}",
        ],
        [
            "Compress: pi auto-compaction",
            f"{compaction_rec['score']}/5" if compaction_rec["ok"] else "ERROR",
            f"{compaction_rec['input_tokens']} ({compaction_rec['num_compactions']} compaction(s) fired)" if compaction_rec["ok"] else "n/a",
            f"${compaction_rec['cost_usd']:.4f}",
        ],
    ]
    table_md = md_table(["method", "score", "tokens (final scored call)", "cost"], rows)

    lines = [
        "# Part B: Isolate and Compress -- summary",
        "",
        f"Model: `{args.model}`",
        "",
        table_md,
        "",
        "Isolate: one pi sub-agent per corpus section returns short findings only; a lead pi process "
        "answers the five questions from the concatenated findings alone (no raw corpus text).",
        "",
        f"Compress (summary artifact): a {summary_rec['summary_estimated_tokens']}-token briefing was "
        f"written from Part A's best run ({summary_rec['based_on_part_a_size']}, "
        f"{summary_rec['based_on_part_a_score']}/5), then the five questions were re-asked with only "
        "that briefing as context.",
        "",
        f"Compress (pi's own compaction): reserveTokens was set to {compaction_rec['reserve_tokens']} "
        f"(context window {compaction_rec['context_window']}) so auto-compaction should fire around "
        f"{compaction_rec['threshold_tokens']} tokens; {compaction_rec['num_compactions']} compaction(s) "
        "fired while the agent read the corpus section files one by one via the read tool"
        + (
            f" (actual tokensBefore: {', '.join(str(c['tokensBefore']) for c in compaction_rec['compactions'] if c['type'] == 'compaction_end')}; "
            "pi only checks the threshold between tool batches, so the observed value can run higher than the "
            "configured threshold if the agent reads several files back to back before pi's next check)."
            if any(c["type"] == "compaction_end" for c in compaction_rec["compactions"])
            else "."
        ),
        "",
    ]
    write_text(str(out_dir / "part_b" / "summary.md"), "\n".join(lines))
    print("\n" + table_md)


if __name__ == "__main__":
    main()
