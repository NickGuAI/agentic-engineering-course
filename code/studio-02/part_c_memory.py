#!/usr/bin/env python3
"""Part C: file-based memory across three sessions vs. a memoryless baseline.

work/part_c/with-memory/ gets an AGENTS.md that tells pi to read decisions.md
before starting any task and to append a dated entry whenever it makes a
decision. Three separate ("new") pi sessions run in that directory:

  Session 1: plan a small note-taking tool; make and record three decisions
             (storage format, command name, date format).
  Session 2: an unrelated task (write fib.py); append at least one decision.
  Session 3: "What did we decide in session 1 about the note-taking tool, and why?"

The identical Session 3 prompt also runs in work/part_c/no-memory/ (a fresh
directory with no AGENTS.md and no decisions.md) as the memoryless baseline.

Every call in every condition passes --no-context-files, so pi never walks
parent directories looking for AGENTS.md/CLAUDE.md (this machine has unrelated
personal ones above the repo root that once leaked into an answer -- see
README.md). The with-memory condition still gets its AGENTS.md instructions:
the same text is also passed via --append-system-prompt (with_memory_extra_args
below), so the comparison is reproducible and the only real difference between
the two directories is the presence of AGENTS.md and decisions.md. Today's real
date is injected into that same system-prompt text so decisions.md gets a real
date instead of whatever the model would otherwise guess.

Usage:
  python3 part_c_memory.py --model google/gemini-3.1-flash-lite --out evidence

Run from code/studio-02/. Re-runnable: pass --fresh to wipe work/part_c/ and
start the three sessions over (evidence/ is still never deleted).
"""
import argparse
import datetime as _dt
import json
import re
import shutil
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from lib.pi_runner import (  # noqa: E402
    DEFAULT_MODEL,
    md_table,
    run_pi,
    write_json,
    write_text,
)

FALLBACK_AGENTS_MD = """# Project memory

Before starting any task, read `decisions.md` in this directory if it exists, and follow any
decisions already recorded there.

Whenever you make a decision while working, append a new dated entry to `decisions.md` with the
decision and the reason for it. Use this format:

## YYYY-MM-DD: <short title>
Decision: <what you decided>
Reason: <why>

Never delete or rewrite earlier entries in `decisions.md`; only append.
"""

# Where subagent B's student-facing copy lives, per the shared contract (section 4).
# Preferred if present at run time; the fallback above carries the same instructions
# so this script works whether or not that file has been written yet.
STARTER_AGENTS_MD = Path(__file__).resolve().parent.parent.parent / "studio" / "studio-02" / "starter" / "AGENTS.md"

SESSION1_PROMPT = (
    "Plan a small command-line note-taking tool. You must make and record ALL THREE of the "
    "following decisions, each with a one-sentence reason. Do not skip any of them and do not "
    "stop until all three are recorded:\n"
    "1. The storage format for notes.\n"
    "2. The command name for the tool.\n"
    "3. The date format used when recording each note.\n"
    "Follow the project instructions for where and how to record decisions. Before you finish, "
    "re-read decisions.md and confirm it contains all three decisions above; if one is missing, "
    "add it. Do not write any other code or files for this task."
)

SESSION2_PROMPT = (
    "Write fib.py that prints the first 20 Fibonacci numbers. While doing this, make at least "
    "one small implementation decision (for example, whether to start the sequence at 0 or 1, "
    "or iterative vs. recursive), and record it following the project instructions."
)

SESSION3_PROMPT = "What did we decide in session 1 about the note-taking tool, and why?"

# Applied to BOTH conditions' recall step (session 3, with-memory and baseline alike), via
# --append-system-prompt. Giving the recall step only a "read" tool (no "ls") was not enough
# on its own: observed directly, a no-memory baseline still found the sibling with-memory
# directory's decisions.md by guessing relative paths and climbing to code/studio-02/README.md
# (which documents the with-memory/no-memory layout) with plain `read` calls, no listing
# needed. This instruction is the second, load-bearing half of that fix.
SCOPE_INSTRUCTION = (
    "Only use information already available in your current working directory to answer. "
    "Do not read, open, or guess the contents of any file in a parent directory, a sibling "
    "directory, or anywhere else outside your current working directory."
)

DATE_ENTRY_RE = re.compile(r"\d{4}-\d{2}-\d{2}")

CATEGORIES = {
    "storage_format": {
        "anchor": re.compile(r"storage format|storage", re.IGNORECASE),
        "label": "storage format for notes",
    },
    "command_name": {
        "anchor": re.compile(r"command name|command", re.IGNORECASE),
        "label": "command name for the tool",
    },
    "date_format": {
        "anchor": re.compile(r"date format", re.IGNORECASE),
        "label": "date format for entries",
    },
}

STOPWORDS = set(
    "the a an of for to in on with and or is are was were be been being this that these those "
    "it its as at by from will would should could note notes tool decision decided record "
    "recording use used using format name command storage date reason because".split()
)


def significant_words(text: str) -> set:
    return {w for w in re.findall(r"[a-zA-Z0-9]+", text.lower()) if len(w) > 2 and w not in STOPWORDS}


def extract_ground_truth(decisions_md_text: str) -> dict:
    """For each of the three decision categories, find the block of decisions.md
    that mentions it and return that block's text (or '' if not found)."""
    blocks = re.split(r"\n\s*\n", decisions_md_text)
    ground_truth = {}
    for key, spec in CATEGORIES.items():
        found = ""
        for block in blocks:
            if spec["anchor"].search(block):
                found = block.strip()
                break
        ground_truth[key] = found
    return ground_truth


def classify_recall(answer_text: str, ground_truth: dict) -> dict:
    """For each category: 'correct' / 'invented' / 'missing'."""
    result = {}
    for key, spec in CATEGORIES.items():
        truth_block = ground_truth.get(key, "")
        mentions_category = bool(spec["anchor"].search(answer_text))
        if not mentions_category:
            result[key] = "missing"
            continue
        if not truth_block:
            # We have no record of this decision at all (e.g. session 1 never made
            # it), so anything the answer says about it is unverifiable/invented.
            result[key] = "invented"
            continue
        truth_words = significant_words(truth_block)
        # Only count words specific enough to indicate a real match (drop the
        # category's own anchor words, already required above).
        truth_words -= significant_words(spec["label"])
        answer_words = significant_words(answer_text)
        overlap = truth_words & answer_words
        result[key] = "correct" if overlap else "invented"
    return result


def count_dated_entries(text: str) -> int:
    return len(DATE_ENTRY_RE.findall(text))


def get_agents_md_text() -> str:
    if STARTER_AGENTS_MD.exists():
        return STARTER_AGENTS_MD.read_text(encoding="utf-8")
    return FALLBACK_AGENTS_MD


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--model", default=DEFAULT_MODEL)
    ap.add_argument("--out", default="evidence")
    ap.add_argument("--timeout", type=int, default=600)
    ap.add_argument("--fresh", action="store_true", help="wipe work/part_c/ and start the three sessions over")
    args = ap.parse_args()

    out_dir = Path(args.out)
    part_c_dir = out_dir / "part_c"
    part_c_dir.mkdir(parents=True, exist_ok=True)
    sessions_dir = (out_dir / "sessions").resolve()

    with_memory_dir = Path("work/part_c/with-memory")
    no_memory_dir = Path("work/part_c/no-memory")

    if args.fresh:
        shutil.rmtree("work/part_c", ignore_errors=True)

    with_memory_dir.mkdir(parents=True, exist_ok=True)
    no_memory_dir.mkdir(parents=True, exist_ok=True)

    agents_md_text = get_agents_md_text()
    if STARTER_AGENTS_MD.exists():
        repo_root = Path(__file__).resolve().parent.parent.parent
        try:
            agents_md_source = str(STARTER_AGENTS_MD.relative_to(repo_root))
        except ValueError:
            agents_md_source = str(STARTER_AGENTS_MD)
    else:
        agents_md_source = "(built-in fallback, matching contract section 5.4)"
    (with_memory_dir / "AGENTS.md").write_text(agents_md_text, encoding="utf-8")
    print(f"AGENTS.md source: {agents_md_source}")

    tool_list = "read,write,edit,ls"
    raw_dir = part_c_dir / "raw"
    raw_dir.mkdir(parents=True, exist_ok=True)

    # All Part C calls pass no_context_files=True. This machine has unrelated
    # personal AGENTS.md files above the repo root (~/AGENTS.md, ~/PKMS/AGENTS.md)
    # that pi's normal parent-directory walk would otherwise load into every
    # call's system prompt. A first run without this confirmed real damage: the
    # no-memory baseline, lacking any real memory to ground on, picked up on
    # unrelated content from those ambient files and answered with a hallucinated
    # story about a different, unrelated personal system -- and that content is
    # not safe to ship in a public course repo's evidence. AGENTS.md is still
    # written to with_memory_dir as a real file (so it is there to inspect and
    # so the with-memory agent's own read tool can find it if it goes looking),
    # and its instructions are also passed via --append-system-prompt so the
    # with-memory condition still reliably gets them without depending on pi's
    # directory walk. decisions.md remains 100% real, file-based memory, read
    # and written by the agent's own tool calls across separate sessions.
    #
    # The model otherwise has no clock and will guess a plausible-looking but
    # wrong date for every decisions.md entry (observed directly: entries dated
    # 2025-05-14 on a machine running in September 2026). Today's real date, from
    # the system clock, is appended to the same system-prompt text so every
    # dated entry the agent writes is actually dated today.
    todays_date = _dt.date.today().isoformat()
    with_memory_extra_args = [
        "--append-system-prompt",
        agents_md_text + f"\n\nToday's date is {todays_date}.",
    ]

    # --- Session 1: plan the note-taking tool, record three decisions --------
    print("=== Part C, session 1 (with memory): plan note-taking tool ===", flush=True)
    s1 = run_pi(
        prompt=SESSION1_PROMPT,
        cwd=str(with_memory_dir),
        model=args.model,
        tools=tool_list,
        session_dir=str(sessions_dir),
        raw_events_path=str(raw_dir / "session1.raw.jsonl"),
        timeout=args.timeout,
        approve=True,
        no_context_files=True,
        extra_args=with_memory_extra_args,
    )
    decisions_path = with_memory_dir / "decisions.md"
    decisions_after_s1 = decisions_path.read_text(encoding="utf-8") if decisions_path.exists() else ""
    entries_after_s1 = count_dated_entries(decisions_after_s1)
    missing_categories = [spec["label"] for key, spec in CATEGORIES.items() if not extract_ground_truth(decisions_after_s1).get(key)]
    print(f"  session 1 ok={s1.ok} cost=${s1.total_cost_usd:.4f} decisions.md exists={decisions_path.exists()} dated_entries~={entries_after_s1} missing={missing_categories}", flush=True)

    # A small/cheap model does not always follow a three-part instruction fully
    # (observed directly: one run recorded only 2 of 3 decisions). Retry once,
    # asking only for what is missing, rather than silently shipping incomplete
    # evidence -- this also makes the script more robust for students re-running it.
    s1_retry_cost = 0.0
    if missing_categories:
        print(f"  session 1 is missing {len(missing_categories)} decision(s); retrying once: {missing_categories}", flush=True)
        retry_prompt = (
            "decisions.md is still missing a decision for: " + "; ".join(missing_categories) + ". "
            "Add the missing one(s) now, each with a one-sentence reason, following the project "
            "instructions for how and where to record decisions. Do not change or remove any "
            "existing entries."
        )
        s1_retry = run_pi(
            prompt=retry_prompt,
            cwd=str(with_memory_dir),
            model=args.model,
            tools=tool_list,
            session_dir=str(sessions_dir),
            raw_events_path=str(raw_dir / "session1-retry.raw.jsonl"),
            timeout=args.timeout,
            approve=True,
            no_context_files=True,
            extra_args=with_memory_extra_args,
        )
        s1_retry_cost = s1_retry.total_cost_usd
        decisions_after_s1 = decisions_path.read_text(encoding="utf-8") if decisions_path.exists() else ""
        entries_after_s1 = count_dated_entries(decisions_after_s1)
        missing_categories = [spec["label"] for key, spec in CATEGORIES.items() if not extract_ground_truth(decisions_after_s1).get(key)]
        print(f"  after retry: dated_entries~={entries_after_s1} missing={missing_categories}", flush=True)

    if not decisions_path.exists():
        print("  WARNING: decisions.md was not created after session 1.", file=sys.stderr)
    elif missing_categories:
        print(f"  WARNING: still missing after retry: {missing_categories}.", file=sys.stderr)

    # --- Session 2: unrelated task, at least one more decision ---------------
    print("=== Part C, session 2 (with memory): write fib.py ===", flush=True)
    s2 = run_pi(
        prompt=SESSION2_PROMPT,
        cwd=str(with_memory_dir),
        model=args.model,
        tools=tool_list,
        session_dir=str(sessions_dir),
        raw_events_path=str(raw_dir / "session2.raw.jsonl"),
        timeout=args.timeout,
        approve=True,
        no_context_files=True,
        extra_args=with_memory_extra_args,
    )
    decisions_after_s2 = decisions_path.read_text(encoding="utf-8") if decisions_path.exists() else ""
    entries_after_s2 = count_dated_entries(decisions_after_s2)
    fib_path = with_memory_dir / "fib.py"
    print(f"  session 2 ok={s2.ok} cost=${s2.total_cost_usd:.4f} fib.py exists={fib_path.exists()} dated_entries~={entries_after_s2}", flush=True)
    if entries_after_s2 <= entries_after_s1:
        print("  WARNING: session 2 does not appear to have appended a new decision.", file=sys.stderr)

    ground_truth = extract_ground_truth(decisions_after_s2 or decisions_after_s1)

    # --- Session 3: recall query, with memory ---------------------------------
    # Tools are deliberately just "read", with no "ls". That alone turned out not
    # to be enough: a run gave the no-memory baseline just "read" and it still
    # found the sibling with-memory/decisions.md, by guessing relative paths and
    # climbing with plain `read` calls to code/studio-02/README.md (which
    # documents the with-memory/no-memory layout), then reading the sibling
    # directly -- no directory listing needed. SCOPE_INSTRUCTION, applied to both
    # conditions via --append-system-prompt, is the fix that actually stopped it.
    print("=== Part C, session 3 (with memory): recall query ===", flush=True)
    s3_mem = run_pi(
        prompt=SESSION3_PROMPT,
        cwd=str(with_memory_dir),
        model=args.model,
        tools="read",
        session_dir=str(sessions_dir),
        raw_events_path=str(raw_dir / "session3-with-memory.raw.jsonl"),
        timeout=args.timeout,
        approve=True,
        no_context_files=True,
        extra_args=["--append-system-prompt", with_memory_extra_args[1] + "\n\n" + SCOPE_INSTRUCTION],
    )
    recall_with_memory = classify_recall(s3_mem.answer_text, ground_truth)
    print(f"  session 3 (with memory) ok={s3_mem.ok} cost=${s3_mem.total_cost_usd:.4f} recall={recall_with_memory}", flush=True)

    # --- Session 3 baseline: identical prompt, fresh dir, no memory -----------
    print("=== Part C, baseline (no memory): recall query ===", flush=True)
    s3_baseline = run_pi(
        prompt=SESSION3_PROMPT,
        cwd=str(no_memory_dir),
        model=args.model,
        tools="read",
        session_dir=str(sessions_dir),
        raw_events_path=str(raw_dir / "session3-no-memory.raw.jsonl"),
        timeout=args.timeout,
        approve=True,
        no_context_files=True,
        extra_args=["--append-system-prompt", SCOPE_INSTRUCTION],
    )
    recall_no_memory = classify_recall(s3_baseline.answer_text, ground_truth)
    print(f"  baseline (no memory) ok={s3_baseline.ok} cost=${s3_baseline.total_cost_usd:.4f} recall={recall_no_memory}", flush=True)

    # --- Save evidence files ---------------------------------------------------
    write_text(str(part_c_dir / "decisions.md"), decisions_after_s2 or decisions_after_s1 or "(decisions.md was never created)")
    write_text(str(part_c_dir / "fib.py"), fib_path.read_text(encoding="utf-8") if fib_path.exists() else "(fib.py was never created)")
    write_text(str(part_c_dir / "session3-with-memory-answer.md"), s3_mem.answer_text)
    write_text(str(part_c_dir / "session3-no-memory-answer.md"), s3_baseline.answer_text)

    record = {
        "model": args.model,
        "agents_md_source": agents_md_source,
        "session1": {
            "ok": s1.ok, "error": s1.error, "usage": s1.usage,
            "cost_usd": round(s1.total_cost_usd + s1_retry_cost, 6),
            "retried": s1_retry_cost > 0,
            "decisions_md_created": decisions_path.exists(), "dated_entries": entries_after_s1,
            "missing_after_retry": missing_categories,
        },
        "session2": {
            "ok": s2.ok, "error": s2.error, "usage": s2.usage, "cost_usd": round(s2.total_cost_usd, 6),
            "fib_py_created": fib_path.exists(), "dated_entries_after": entries_after_s2,
        },
        "session3_with_memory": {
            "ok": s3_mem.ok, "error": s3_mem.error, "usage": s3_mem.usage, "cost_usd": round(s3_mem.total_cost_usd, 6),
            "answer_text": s3_mem.answer_text, "recall": recall_with_memory,
        },
        "session3_no_memory_baseline": {
            "ok": s3_baseline.ok, "error": s3_baseline.error, "usage": s3_baseline.usage,
            "cost_usd": round(s3_baseline.total_cost_usd, 6),
            "answer_text": s3_baseline.answer_text, "recall": recall_no_memory,
        },
        "ground_truth_blocks": ground_truth,
        "total_cost_usd": round(
            s1.total_cost_usd + s1_retry_cost + s2.total_cost_usd + s3_mem.total_cost_usd + s3_baseline.total_cost_usd, 6
        ),
    }
    write_json(str(part_c_dir / "part_c.json"), record)

    rows = []
    for key, spec in CATEGORIES.items():
        rows.append([spec["label"], recall_with_memory[key], recall_no_memory[key]])
    table_md = md_table(["decision", "with memory (session 3)", "no memory baseline (session 3)"], rows)

    lines = [
        "# Part C: File-based Memory vs. Memoryless Baseline -- summary",
        "",
        f"Model: `{args.model}`",
        f"AGENTS.md source: {agents_md_source}",
        "",
        f"Session 1 wrote decisions.md with ~{entries_after_s1} dated entries.",
        f"Session 2 (unrelated fib.py task) left decisions.md with ~{entries_after_s2} dated entries.",
        "",
        "Recall of the three session-1 decisions, asked fresh in session 3:",
        "",
        table_md,
        "",
        "'correct' = the answer's content for that decision overlaps with what decisions.md actually "
        "recorded. 'invented' = the answer addresses that decision but does not match what was "
        "recorded (or nothing was ever recorded for it). 'missing' = the answer does not address "
        "that decision at all. This is an automated keyword-overlap heuristic; the actual answer "
        "text is saved alongside this file for a human to check.",
        "",
        f"With-memory session 3 answer: see session3-with-memory-answer.md",
        f"No-memory baseline session 3 answer: see session3-no-memory-answer.md",
        "",
    ]
    write_text(str(part_c_dir / "summary.md"), "\n".join(lines))
    print("\n" + table_md)


if __name__ == "__main__":
    main()
