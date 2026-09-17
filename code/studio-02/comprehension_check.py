#!/usr/bin/env python3
"""comprehension_check.py -- SUPPORTED / CONTRADICTED / NOT_FOUND comprehension
check over corpus/combined.txt (contract addendum v3).

Part A and context_sweep.py both showed the model can locate and repeat a
short fact ("needle") anywhere in the corpus. This check asks something
different: given a *paraphrase* of a claim, definition, or reference found
verbatim somewhere in the corpus (sharing no content words with the original
except proper names and unavoidable technical terms), can the model correctly
judge whether the corpus SUPPORTS it, CONTRADICTS it, or never addresses it
(NOT_FOUND) -- once with the whole corpus as context, once with only the 20
source excerpts, so a miss at full length is attributable to length rather
than to the paraphrase itself.

Two modes, each ONE pi call for all 20 items at once:
  --context full      (default) text = the whole corpus/combined.txt.
  --context excerpts   text = just the 20 excerpts, each labeled
                        "[Excerpt k, from <doc_title>]", in corpus order.

Usage:
  python3 comprehension_check.py --model openai-codex/gpt-5.6-luna \\
      --items questions_comprehension.json --out evidence/comprehension \\
      --context full

Provider: the Codex subscription only (pi's openai-codex provider, already
logged in on this machine). This script never sets an API key, never calls
/login, and never touches ~/.pi/agent/auth.json.

Run from code/studio-02/. Re-runnable: each --context mode only overwrites
its own run-<mode>.json; results.md is rebuilt from whichever run-*.json
files exist on disk (so it can be regenerated after only one mode has run,
and picks up the other automatically once it exists too). Never deletes
anything under evidence/.
"""
import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from lib.pi_runner import (  # noqa: E402
    COMPREHENSION_LABELS,
    DEFAULT_MODEL,
    md_table,
    parse_labeled_lines,
    run_pi,
    write_json,
    write_text,
)

INSTRUCTION = (
    "For each numbered statement, answer SUPPORTED if the text above states or clearly implies it, "
    "CONTRADICTED if the text states something incompatible with it, or NOT FOUND if the text does not "
    "address it. Use exactly this format per line: `<n>. <LABEL> - <one sentence naming the paper and "
    "the evidence>`."
)

QUOTA_ERROR_KEYWORDS = ("429", "rate limit", "rate-limit", "too many requests", "quota", "usage limit", "usage cap")


def _looks_like_quota_error(error_text):
    if not error_text:
        return False
    low = error_text.lower()
    return any(kw in low for kw in QUOTA_ERROR_KEYWORDS)


def load_items(path: str) -> list:
    """Load questions_comprehension.json, tolerant of a couple of plausible
    top-level shapes (a bare list of items, or a dict wrapping them under
    "items" or "questions"), since this file is authored separately."""
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    if isinstance(data, list):
        items = data
    elif isinstance(data, dict):
        items = data.get("items") or data.get("questions")
        if items is None:
            raise ValueError(f"{path}: expected a top-level list, or a dict with an 'items' or 'questions' key")
    else:
        raise ValueError(f"{path}: expected a JSON list or object")
    for item in items:
        if item.get("label") not in COMPREHENSION_LABELS:
            raise ValueError(f"item id={item.get('id')}: label {item.get('label')!r} is not one of {COMPREHENSION_LABELS}")
    return items


def statements_block(items: list) -> str:
    return "\n".join(f"{item['id']}. {item['statement']}" for item in items)


def excerpts_block(items: list) -> str:
    """The 20 excerpts only, in corpus order (by excerpt_depth_tokens, the
    items' position in combined.txt), each labeled per item."""
    ordered = sorted(items, key=lambda it: it.get("excerpt_depth_tokens", 0) or 0)
    parts = []
    for item in ordered:
        parts.append(f"[Excerpt {item['id']}, from {item.get('doc_title', 'document ' + str(item.get('doc')))}]")
        parts.append(item["excerpt"])
        parts.append("")
    return "\n".join(parts)


def build_stdin_text(mode: str, items: list, full_text: str) -> str:
    if mode == "full":
        return full_text + "\n\n"
    return excerpts_block(items) + "\n\n"


def score_items(items: list, parsed: dict) -> list:
    """Return one dict per item: id, doc, depth, kind, alteration, expected,
    model_label, justification, correct."""
    rows = []
    for item in items:
        p = parsed.get(item["id"]) or {}
        model_label = p.get("label")
        rows.append({
            "id": item["id"],
            "doc": item.get("doc"),
            "excerpt_depth_tokens": item.get("excerpt_depth_tokens"),
            "kind": item.get("kind"),
            "alteration": item.get("alteration"),
            "expected": item["label"],
            "model_label": model_label,
            "justification": p.get("justification", ""),
            "raw": p.get("raw", ""),
            "correct": model_label == item["label"],
        })
    return rows


def run_one_mode(mode: str, items: list, full_text: str, args, out_dir: Path, sessions_dir: Path, work_dir: Path):
    stdin_text = build_stdin_text(mode, items, full_text)
    prompt = f"Statements:\n{statements_block(items)}\n\n{INSTRUCTION}\n"
    raw_path = str(out_dir / "raw" / f"{mode}.raw.jsonl")

    result = run_pi(
        prompt=prompt,
        stdin_text=stdin_text,
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

    parsed = parse_labeled_lines(result.answer_text, n=len(items)) if result.ok else {}
    rows = score_items(items, parsed) if result.ok else score_items(items, {})

    record = {
        "mode": mode,
        "model": args.model,
        "n_items": len(items),
        "ok": result.ok,
        "error": result.error,
        "quota_error": _looks_like_quota_error(result.error),
        "usage": result.usage,
        "cost_usd": round(result.total_cost_usd, 6),
        "wall_time_s": round(result.wall_time_s, 2),
        "answer_text": result.answer_text,
        "items": rows,
        "raw_events_path": raw_path,
    }
    return record


def load_all_runs(out_dir: Path) -> dict:
    runs = {}
    for mode in ("full", "excerpts"):
        path = out_dir / f"run-{mode}.json"
        if path.exists():
            runs[mode] = json.loads(path.read_text(encoding="utf-8"))
    return runs


def write_results_md(path: Path, items: list, runs: dict):
    by_id_full = {r["id"]: r for r in runs["full"]["items"]} if "full" in runs else {}
    by_id_excerpts = {r["id"]: r for r in runs["excerpts"]["items"]} if "excerpts" in runs else {}

    rows = []
    n_correct_full = 0
    n_scored_full = 0
    for item in sorted(items, key=lambda it: it["id"]):
        iid = item["id"]
        f = by_id_full.get(iid)
        e = by_id_excerpts.get(iid)
        full_label = f["model_label"] or "(no label parsed)" if f else "(not run)"
        excerpts_label = e["model_label"] or "(no label parsed)" if e else "(not run)"
        justification = f["justification"] if f else ""

        if f is None:
            verdict = "(not run)"
        elif f["correct"]:
            verdict = "correct"
            n_correct_full += 1
            n_scored_full += 1
        else:
            n_scored_full += 1
            if e is not None and e["correct"]:
                verdict = "wrong at full -- correct with excerpts only (length-attributable)"
            else:
                verdict = "wrong"

        rows.append([
            iid, item.get("doc"), item.get("excerpt_depth_tokens"), item.get("kind"), item.get("alteration"),
            item["label"], full_label, excerpts_label, verdict, justification,
        ])

    table = md_table(
        ["id", "doc", "depth", "kind", "alteration", "expected", "label (full)", "label (excerpts)", "verdict", "justification (full)"],
        rows,
    )

    lines = [
        "# Comprehension check: SUPPORTED / CONTRADICTED / NOT_FOUND -- results",
        "",
    ]
    for mode in ("full", "excerpts"):
        if mode in runs:
            r = runs[mode]
            if r["ok"]:
                acc = f"{n_correct_full}/{n_scored_full} ({n_correct_full/n_scored_full*100:.0f}%)" if mode == "full" and n_scored_full else "n/a"
                # usage["input"] alone is only the FRESH (non-cached) input tokens;
                # a huge single-turn prompt like this one is almost entirely written
                # to the prompt cache in one shot, so the real total sent is
                # input + cacheRead + cacheWrite, not the bare "input" field.
                u = r["usage"]
                total_input = u.get("input", 0) + u.get("cacheRead", 0) + u.get("cacheWrite", 0)
                lines.append(
                    f"**{mode}**: model `{r['model']}`, {total_input} real input tokens "
                    f"({u.get('input', 0)} fresh + {u.get('cacheRead', 0)} cache-read + {u.get('cacheWrite', 0)} cache-write), "
                    f"cost ${r['cost_usd']:.4f}, wall time {r['wall_time_s']}s"
                    + (f", accuracy {acc}" if mode == "full" else "")
                )
            else:
                lines.append(f"**{mode}**: ERROR -- {r['error']}")
        else:
            lines.append(f"**{mode}**: not run yet")
    lines.append("")
    lines.append(table)
    lines.append("")
    lines.append(
        "'verdict' compares the full-context label to the expected label. A miss at full length that "
        "the model gets right with only the 20 excerpts is called out explicitly, since that means the "
        "paraphrase itself was not the problem -- length was."
    )
    lines.append("")
    lines.append("## All 20 statements")
    lines.append("")
    for item in sorted(items, key=lambda it: it["id"]):
        lines.append(f"{item['id']}. [{item['label']}] {item['statement']}")
    lines.append("")

    write_text(str(path), "\n".join(lines))
    return table


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--model", default=DEFAULT_MODEL)
    ap.add_argument("--items", default="questions_comprehension.json")
    ap.add_argument("--out", default="evidence/comprehension")
    ap.add_argument("--corpus", default="corpus/combined.txt")
    ap.add_argument("--context", choices=["full", "excerpts"], default="full")
    ap.add_argument("--work-dir", default="work/comprehension")
    ap.add_argument("--timeout", type=int, default=1800)
    ap.add_argument("--thinking", default="low")
    args = ap.parse_args()

    corpus_path = Path(args.corpus)
    if not corpus_path.exists():
        print(f"ERROR: {args.corpus} not found. Run: bash setup.sh", file=sys.stderr)
        sys.exit(1)
    full_text = corpus_path.read_text(encoding="utf-8", errors="replace")

    if not Path(args.items).exists():
        print(f"ERROR: {args.items} not found.", file=sys.stderr)
        sys.exit(1)
    items = load_items(args.items)
    print(f"Loaded {len(items)} comprehension item(s) from {args.items}", flush=True)

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

    print(f"=== Comprehension check: --context {args.context} ===", flush=True)
    record = run_one_mode(args.context, items, full_text, args, out_dir, sessions_dir, work_dir)
    write_json(str(out_dir / f"run-{args.context}.json"), record)

    if record["quota_error"]:
        print(f"STOPPED: quota/rate-limit error: {record['error']}", file=sys.stderr)
    elif record["ok"]:
        n_correct = sum(1 for r in record["items"] if r["correct"])
        u = record["usage"]
        total_input = u.get("input", 0) + u.get("cacheRead", 0) + u.get("cacheWrite", 0)
        print(
            f"  input_tokens={total_input} (fresh={u.get('input', 0)} cacheRead={u.get('cacheRead', 0)} "
            f"cacheWrite={u.get('cacheWrite', 0)}) cost=${record['cost_usd']:.4f} "
            f"wall_time={record['wall_time_s']}s score={n_correct}/{len(items)}",
            flush=True,
        )
    else:
        print(f"  ERROR: {record['error']}", flush=True)

    runs = load_all_runs(out_dir)
    table = write_results_md(out_dir / "results.md", items, runs)
    print("\n" + table)

    if record["quota_error"]:
        sys.exit(3)


if __name__ == "__main__":
    main()
