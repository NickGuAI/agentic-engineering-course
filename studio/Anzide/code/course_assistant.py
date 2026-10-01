#!/usr/bin/env python3
"""Course Assistant harness.

Rewrites one course document (or every supported file in a directory) into a
step-by-step tutorial PDF for the reader described in reader_profile.md.

Pipeline per document:
    extract text -> number source blocks -> writer agent (claude -p, read-only tools)
    -> deterministic checks -> one repair round if needed -> PDF -> report

The agent never writes files. This harness writes only under outputs/.

Usage:
    python3 studio/Anzide/code/course_assistant.py <file-or-directory> [options]
"""
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from check_tutorial import check, format_report  # noqa: E402
from source_blocks import FENCE, HEADING, LIST_ITEM, extract_text, number_blocks, parse_numbered, word_count  # noqa: E402

CODE_DIR = Path(__file__).resolve().parent
BASE_DIR = CODE_DIR.parent                      # studio/Anzide
OUTPUTS_DIR = BASE_DIR / "outputs"
REFERENCES_DIR = BASE_DIR / "references"
WRITER_PROMPT = CODE_DIR / "prompts" / "writer.md"
READER_PROFILE = CODE_DIR / "reader_profile.md"
STYLE_CSS = CODE_DIR / "pdf" / "style.css"
SUPPORTED = {".md", ".markdown", ".txt", ".text", ".pdf", ".pptx", ".docx", ".html", ".htm", ".rst", ".ipynb", ".odt", ".epub"}
AGENT_TOOLS = "Read,Glob,Grep"                  # the whole permission boundary of the agent
RESPONSE = re.compile(r"<<<TUTORIAL>>>\s*\n(.*?)\n\s*<<<COVERAGE>>>\s*\n(.*?)\n\s*<<<END>>>", re.S)
LABEL_LINE = re.compile(r"^\*\*(Do|Why|Check|Correction):\*\*")
TABLE_LINE = re.compile(r"^\s*\|")
QUOTE_LINE = re.compile(r"^\s*>")
CHROME_CANDIDATES = [
    os.environ.get("CHROME_BIN", ""),
    "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
    "/Applications/Chromium.app/Contents/MacOS/Chromium",
    "google-chrome", "chromium", "chromium-browser", "chrome",
]


def repo_root() -> Path:
    try:
        out = subprocess.run(["git", "rev-parse", "--show-toplevel"], cwd=BASE_DIR,
                             capture_output=True, text=True, check=True).stdout.strip()
        return Path(out)
    except (subprocess.CalledProcessError, FileNotFoundError):
        return BASE_DIR.parent.parent


REPO = repo_root()


# ----------------------------------------------------------------------------- inputs

def find_documents(path: Path) -> list[Path]:
    """One file, or every supported file under a directory (sorted, hidden dirs skipped)."""
    if path.is_file():
        return [path]
    if not path.is_dir():
        raise FileNotFoundError(f"{path} does not exist")
    docs = [p for p in sorted(path.rglob("*"))
            if p.is_file() and p.suffix.lower() in SUPPORTED
            and not any(part.startswith(".") for part in p.relative_to(path).parts)]
    return docs


def build_prompt(doc_name: str, numbered: str, block_count: int, source_words: int,
                 budget: int, extra: str) -> str:
    profile = READER_PROFILE.read_text() if READER_PROFILE.exists() else "(no reader profile found)"
    references = REFERENCES_DIR.relative_to(REPO) if REFERENCES_DIR.exists() else "(references folder missing)"
    parts = [
        "Task: rewrite the source document below into step-by-step tutorial(s) for the reader described below, "
        "following your role instructions exactly.",
        "",
        f"Word budget for the tutorial: at most {budget} words (the source has {source_words} words in {block_count} blocks).",
        f"References: {references} (start with INDEX.md) and this repository; use them only as your instructions describe.",
    ]
    if extra:
        parts += ["", f"Additional instruction from the human: {extra}"]
    parts += [
        "", "=== READER PROFILE ===", profile.strip(), "",
        f"=== SOURCE: {doc_name} ({block_count} blocks) ===", numbered.rstrip(), "=== END OF SOURCE ===", "",
        "Reply with the <<<TUTORIAL>>> / <<<COVERAGE>>> / <<<END>>> format only.",
    ]
    return "\n".join(parts)


def repair_prompt(report: str) -> str:
    return ("Your previous response failed these automated checks:\n\n" + report +
            "\n\nFix only these problems, keeping everything else as it was. Reply again with the complete "
            "response in the same <<<TUTORIAL>>> / <<<COVERAGE>>> / <<<END>>> format (full text, not a diff).")


# ----------------------------------------------------------------------------- the agent call

def run_claude(prompt: str, raw_trace: Path, *, model: str | None, max_budget_usd: float,
               timeout: int, resume: str | None = None) -> tuple[list[dict], dict]:
    """Call `claude -p` with read-only tools and no MCP servers; return (events, result_event)."""
    cmd = ["claude", "-p", "--output-format", "stream-json", "--verbose",
           "--tools", AGENT_TOOLS, "--strict-mcp-config", "--mcp-config", '{"mcpServers":{}}',
           "--max-budget-usd", str(max_budget_usd),
           "--append-system-prompt", WRITER_PROMPT.read_text()]
    if model:
        cmd += ["--model", model]
    if resume:
        cmd += ["--resume", resume]
    try:
        proc = subprocess.run(cmd, input=prompt, capture_output=True, text=True, cwd=REPO, timeout=timeout)
        stdout, stderr = proc.stdout, proc.stderr
    except subprocess.TimeoutExpired as exc:
        stdout = (exc.stdout or b"").decode() if isinstance(exc.stdout, bytes) else (exc.stdout or "")
        stderr = f"timeout after {timeout}s"
    except FileNotFoundError:
        return [], {"type": "result", "is_error": True, "result": "claude CLI not found on PATH"}
    with raw_trace.open("a") as fh:
        fh.write(stdout)
        if not stdout.endswith("\n"):
            fh.write("\n")
    events = []
    for line in stdout.splitlines():
        line = line.strip()
        if line.startswith("{"):
            try:
                events.append(json.loads(line))
            except json.JSONDecodeError:
                pass
    result = next((e for e in reversed(events) if e.get("type") == "result"), None)
    if result is None:
        result = {"type": "result", "is_error": True,
                  "result": f"no result event from claude ({stderr.strip()[:300] or 'no stderr'})"}
    return events, result


def normalize_markdown(text: str) -> str:
    """Insert the blank lines pandoc needs so lists, labels, headings, and tables render as such.

    Writers often put a list or a **Check:** line directly under the previous line; pandoc then folds
    them into that paragraph, and a heading without a blank line before it is not a heading at all.
    Only blank lines are added; nothing inside code fences is touched.
    """
    out: list[str] = []
    in_fence = False
    prev = ""
    for line in text.splitlines():
        if not in_fence and prev.strip():
            prev_list = bool(LIST_ITEM.match(prev))
            needs_gap = (
                FENCE.match(line) or HEADING.match(line) or LABEL_LINE.match(line)
                or (TABLE_LINE.match(line) and not TABLE_LINE.match(prev))
                or (QUOTE_LINE.match(line) and not QUOTE_LINE.match(prev))
                or (LIST_ITEM.match(line) and not prev_list)
                or (prev_list and line.strip() and not LIST_ITEM.match(line) and not line.startswith((" ", "\t")))
            )
            if needs_gap:
                out.append("")
        if FENCE.match(line):
            in_fence = not in_fence
        out.append(line)
        prev = line
    return "\n".join(out) + "\n"


def parse_response(text: str) -> tuple[str | None, str | None, str]:
    """Return (tutorial, coverage, problem). problem is '' when parsing succeeded."""
    stripped = text.strip()
    if stripped.startswith("CANNOT_COMPLETE:"):
        return None, None, stripped
    match = RESPONSE.search(text)
    if not match:
        return None, None, "response did not contain the <<<TUTORIAL>>>/<<<COVERAGE>>>/<<<END>>> markers"
    return match.group(1).strip() + "\n", match.group(2).strip() + "\n", ""


# ----------------------------------------------------------------------------- trace summary

def summarize_trace(events: list[dict]) -> str:
    """Human-readable list of what the agent did, without the raw payloads."""
    home = str(Path.home())
    lines = ["# Agent trace", ""]
    init = next((e for e in events if e.get("type") == "system" and e.get("subtype") == "init"), None)
    if init:
        lines += [f"- Model: {init.get('model')}", f"- Session: {init.get('session_id')}",
                  f"- Tools available: {', '.join(init.get('tools', []))}",
                  f"- MCP servers: {init.get('mcp_servers') or 'none'}",
                  f"- Permission mode: {init.get('permissionMode')}", ""]
    step = 0
    for event in events:
        if event.get("type") == "assistant":
            for block in event.get("message", {}).get("content", []):
                if block.get("type") == "tool_use":
                    step += 1
                    args = ", ".join(f"{k}={str(v)[:120]!r}" for k, v in block.get("input", {}).items())
                    lines.append(f"{step}. **{block.get('name')}**({args})".replace(home, "~"))
                elif block.get("type") == "text" and block.get("text", "").strip():
                    text = block["text"].strip().replace("\n", " ")
                    lines.append(f"   - says: {text[:160]}{'...' if len(text) > 160 else ''}")
        elif event.get("type") == "user":
            for block in event.get("message", {}).get("content", []):
                if isinstance(block, dict) and block.get("type") == "tool_result":
                    content = block.get("content")
                    size = len(content) if isinstance(content, str) else len(json.dumps(content))
                    flag = " (error)" if block.get("is_error") else ""
                    lines.append(f"   - result: {size} chars{flag}")
        elif event.get("type") == "result":
            usage = event.get("usage", {})
            lines += ["", "## Outcome",
                      f"- Status: {'error' if event.get('is_error') else 'ok'} ({event.get('subtype')})",
                      f"- Turns: {event.get('num_turns')}",
                      f"- Duration: {event.get('duration_ms', 0) / 1000:.1f}s (API {event.get('duration_api_ms', 0) / 1000:.1f}s)",
                      f"- Cost: ${event.get('total_cost_usd', 0):.4f}",
                      f"- Tokens: in={usage.get('input_tokens')} out={usage.get('output_tokens')} "
                      f"cache_read={usage.get('cache_read_input_tokens')} cache_write={usage.get('cache_creation_input_tokens')}"]
            denials = event.get("permission_denials") or []
            lines.append(f"- Permission denials: {len(denials)}")
            for denial in denials:
                lines.append(f"  - {denial.get('tool_name')}({json.dumps(denial.get('tool_input'))[:160]})".replace(home, "~"))
            lines.append("")
    if step == 0 and not init:
        lines.append("(no agent events; this was a replay or the call failed before starting)")
    return "\n".join(lines) + "\n"


# ----------------------------------------------------------------------------- PDF

def find_chrome() -> str | None:
    for candidate in CHROME_CANDIDATES:
        if not candidate:
            continue
        if os.path.isabs(candidate) and os.access(candidate, os.X_OK):
            return candidate
        found = shutil.which(candidate)
        if found:
            return found
    return None


def render_pdf(markdown_path: Path, pdf_path: Path, *, draft: bool, toc: bool) -> str:
    """Markdown -> HTML (pandoc) -> PDF (headless Chrome); falls back to pandoc+xelatex."""
    html_path = pdf_path.with_suffix(".html")
    cmd = ["pandoc", str(markdown_path), "--from", "markdown+yaml_metadata_block+pipe_tables",
           "--to", "html5", "--standalone", "--embed-resources", "--css", str(STYLE_CSS),
           "--metadata", f"pagetitle={markdown_path.stem}", "-o", str(html_path)]
    if toc:
        cmd += ["--toc", "--toc-depth=2"]
    subprocess.run(cmd, check=True, capture_output=True, text=True)
    if draft:
        html_path.write_text(html_path.read_text().replace("<body>", '<body class="draft">', 1))
    chrome = find_chrome()
    if chrome:
        subprocess.run([chrome, "--headless=new", "--disable-gpu", "--no-pdf-header-footer",
                        f"--print-to-pdf={pdf_path}", html_path.as_uri()],
                       check=True, capture_output=True, text=True, timeout=120)
        html_path.unlink(missing_ok=True)
        return f"chrome ({chrome})"
    subprocess.run(["pandoc", str(markdown_path), "-o", str(pdf_path), "--pdf-engine=xelatex",
                    "-V", "mainfont=Helvetica Neue", "-V", "monofont=Menlo", "-V", "geometry:margin=2cm"],
                   check=True, capture_output=True, text=True, timeout=180)
    html_path.unlink(missing_ok=True)
    return "pandoc+xelatex (Chrome not found)"


def pdf_check(pdf_path: Path) -> dict:
    failures = []
    if not pdf_path.exists() or pdf_path.stat().st_size == 0:
        failures.append("PDF missing or empty")
    else:
        try:
            from pypdf import PdfReader
            reader = PdfReader(str(pdf_path))
            text = " ".join((page.extract_text() or "") for page in reader.pages[:2])
            if len(reader.pages) < 1:
                failures.append("PDF has no pages")
            if word_count(text) < 20:
                failures.append("PDF text is not extractable")
        except ImportError:
            pass  # pypdf missing: existence check only
    return {"id": "PDF-1", "name": "PDF exists, has pages, text extractable", "passed": not failures,
            "detail": f"{pdf_path.stat().st_size // 1024} KB" if pdf_path.exists() else "", "failures": failures}


# ----------------------------------------------------------------------------- one document

def process_document(doc: Path, run_dir: Path, args: argparse.Namespace) -> dict:
    run_dir.mkdir(parents=True, exist_ok=True)
    started = dt.datetime.now()
    outcome = {"source": str(doc), "run_dir": str(run_dir), "status": "FAILED", "cost_usd": 0.0,
               "turns": 0, "pdf": None, "checks": None, "message": ""}

    # 1. Extract and number the source. This copy is what the agent sees (evidence).
    try:
        text = extract_text(doc)
    except Exception as exc:  # noqa: BLE001 - report any extraction failure
        outcome["message"] = f"could not read source: {exc}"
        return finish(outcome, run_dir, started, [], None)
    numbered = number_blocks(text)
    blocks = parse_numbered(numbered)
    if not blocks:
        outcome["message"] = "source is empty after extraction"
        return finish(outcome, run_dir, started, [], None)
    (run_dir / "source.numbered.md").write_text(numbered)
    source_words = sum(word_count(b) for b in blocks.values())
    budget = max(int(source_words * args.max_ratio), source_words + args.min_extra)
    outcome["sha256"] = hashlib.sha256(doc.read_bytes()).hexdigest()[:16]

    # 2. Writer agent (or replay fixture), then checks, then at most one repair round.
    raw_trace = run_dir / "trace.raw.jsonl"
    events: list[dict] = []
    session_id = None
    result_text = ""
    if args.replay:
        result_text = Path(args.replay).read_text()
        outcome["writer"] = f"REPLAY FIXTURE {args.replay} (no model call)"
    else:
        prompt = build_prompt(doc.name, numbered, len(blocks), source_words, budget, args.extra_instruction)
        (run_dir / "prompt.txt").write_text(prompt)
        events, result = run_claude(prompt, raw_trace, model=args.model, max_budget_usd=args.max_budget_usd,
                                    timeout=args.timeout)
        outcome["cost_usd"] += result.get("total_cost_usd", 0) or 0
        outcome["turns"] += result.get("num_turns", 0) or 0
        session_id = result.get("session_id")
        init = next((e for e in events if e.get("type") == "system"), {})
        outcome["writer"] = f"claude -p, model {init.get('model', '?')}, session {session_id}"
        if result.get("is_error"):
            outcome["message"] = f"agent call failed: {str(result.get('result', ''))[:300]}"
            return finish(outcome, run_dir, started, events, None)
        result_text = result.get("result", "") or ""

    check_result = None
    for attempt in ("initial", "repair"):
        tutorial, coverage, problem = parse_response(result_text)
        if tutorial is None:
            check_result = {"passed": False, "checks": [{"id": "FORMAT", "name": "Response in the required format",
                            "passed": False, "detail": "", "failures": [problem]}], "stats": {}, "omitted": [], "errata": []}
        else:
            tutorial = normalize_markdown(tutorial)   # blank lines only; the checks ignore whitespace
            (run_dir / "tutorial.md").write_text(tutorial)
            (run_dir / "coverage.md").write_text(coverage)
            check_result = check(blocks, tutorial, coverage, max_ratio=args.max_ratio, min_extra=args.min_extra)
        check_result["attempt"] = attempt
        if check_result["passed"] or attempt == "repair" or args.no_repair or args.replay or not session_id:
            break
        # One repair round: same session, so the agent keeps what it read.
        report = format_report(check_result)
        (run_dir / "repair-prompt.txt").write_text(repair_prompt(report))
        more_events, result = run_claude(repair_prompt(report), raw_trace, model=args.model,
                                         max_budget_usd=args.max_budget_usd, timeout=args.timeout, resume=session_id)
        events += more_events
        outcome["cost_usd"] += result.get("total_cost_usd", 0) or 0
        outcome["turns"] += result.get("num_turns", 0) or 0
        if result.get("is_error"):
            outcome["message"] = f"repair call failed: {str(result.get('result', ''))[:300]}"
            break
        result_text = result.get("result", "") or ""
    outcome["checks"] = check_result

    # 3. PDF. A tutorial that failed checks is still rendered, but as a clearly marked DRAFT.
    if (run_dir / "tutorial.md").exists():
        passed = check_result["passed"]
        pdf_name = f"{doc.stem}-tutorial{'' if passed else '.DRAFT'}.pdf"
        pdf_path = run_dir / pdf_name
        try:
            outcome["pdf_engine"] = render_pdf(run_dir / "tutorial.md", pdf_path, draft=not passed,
                                               toc=check_result.get("stats", {}).get("tutorials", 0) >= 2)
            pdf_result = pdf_check(pdf_path)
        except (subprocess.CalledProcessError, subprocess.TimeoutExpired) as exc:
            detail = getattr(exc, "stderr", "") or str(exc)
            pdf_result = {"id": "PDF-1", "name": "PDF exists, has pages, text extractable", "passed": False,
                          "detail": "", "failures": [f"rendering failed: {str(detail)[-300:]}"]}
        check_result["checks"].append(pdf_result)
        check_result["passed"] = check_result["passed"] and pdf_result["passed"]
        if pdf_path.exists():
            outcome["pdf"] = str(pdf_path)
        outcome["status"] = "ACCEPTED" if check_result["passed"] else "DRAFT"
    return finish(outcome, run_dir, started, events, check_result)


def finish(outcome: dict, run_dir: Path, started: dt.datetime, events: list[dict], check_result: dict | None) -> dict:
    outcome["elapsed_s"] = round((dt.datetime.now() - started).total_seconds(), 1)
    (run_dir / "trace.md").write_text(summarize_trace(events))
    if check_result is not None:
        (run_dir / "check.json").write_text(json.dumps(check_result, indent=2))
    (run_dir / "report.md").write_text(document_report(outcome, check_result))
    return outcome


def rel(path: str | Path | None) -> str:
    """Repo-relative when inside the repo, absolute otherwise (never ../../.. chains)."""
    if not path:
        return "-"
    path = Path(path).resolve()
    return str(path.relative_to(REPO)) if path.is_relative_to(REPO) else str(path)


def document_report(outcome: dict, check_result: dict | None) -> str:
    lines = ["# Course Assistant run report", "",
             f"- **Status:** {outcome['status']}" + (f" — {outcome['message']}" if outcome.get("message") else ""),
             f"- **Source:** `{rel(outcome['source'])}`" + (f" (sha256 {outcome['sha256']}...)" if outcome.get("sha256") else ""),
             f"- **Writer:** {outcome.get('writer', '-')}",
             f"- **PDF:** `{rel(outcome['pdf'])}`" + (f" via {outcome['pdf_engine']}" if outcome.get("pdf_engine") else ""),
             f"- **Cost / turns / wall time:** ${outcome['cost_usd']:.4f} / {outcome['turns']} / {outcome.get('elapsed_s', 0)}s",
             f"- **Run folder:** `{rel(outcome['run_dir'])}` (see `trace.md` for every tool call)", ""]
    if check_result:
        stats = check_result.get("stats", {})
        lines += ["## Checks", "", f"Attempt: {check_result.get('attempt', '-')}", "", "```text",
                  format_report(check_result), "```", ""]
        if stats:
            lines += ["| Source words | Tutorial words | Budget | Blocks | Tutorials | Steps | Notes | Errata | Omitted |",
                      "|---|---|---|---|---|---|---|---|---|",
                      f"| {stats.get('source_words')} | {stats.get('tutorial_words')} | {stats.get('word_budget')} | "
                      f"{stats.get('source_blocks')} | {stats.get('tutorials')} | {stats.get('steps')} | {stats.get('notes')} | "
                      f"{stats.get('errata')} | {stats.get('omitted')} |", ""]
        lines += ["## Errata proposed by the agent (review before trusting)", ""]
        if check_result.get("errata"):
            lines += ["| Block | Source says | Should be | Evidence | Confidence |", "|---|---|---|---|---|"]
            lines += [f"| S{e['block']} | {e['source_says']} | {e['should_be']} | {e['evidence']} | {e['confidence']} |"
                      for e in check_result["errata"]]
        else:
            lines.append("None.")
        lines += ["", "## Omitted source blocks (approve or reject)", ""]
        if check_result.get("omitted"):
            for item in check_result["omitted"]:
                lines += [f"- **S{item['block']}** — {item['reason']}", "", "  > " + item["text"].replace("\n", "\n  > "), ""]
        else:
            lines.append("None.")
    lines += ["", "## Human checks still owed", "",
              "- [ ] Level match: I can follow every step without looking anything up; no note explains what I already know.",
              "- [ ] Every Errata row is right (or rejected).", "- [ ] Every Omitted block may be dropped (or must be restored).",
              "- [ ] Accept the PDF." if outcome["status"] == "ACCEPTED" else "- [ ] Decide: fix and re-run, or stop.", ""]
    return "\n".join(lines)


# ----------------------------------------------------------------------------- batch

def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("path", type=Path, help="a course document, or a directory of them")
    parser.add_argument("--model", help="model passed to claude (default: your CLI default)")
    parser.add_argument("--max-budget-usd", type=float, default=3.0, help="spend cap per document (default 3)")
    parser.add_argument("--timeout", type=int, default=900, help="seconds per agent call (default 900)")
    parser.add_argument("--max-ratio", type=float, default=1.75, help="tutorial/source word budget (default 1.75)")
    parser.add_argument("--min-extra", type=int, default=400, help="minimum extra words allowed for short sources")
    parser.add_argument("--no-repair", action="store_true", help="skip the repair round")
    parser.add_argument("--replay", help="offline: a saved writer response used instead of calling claude")
    parser.add_argument("--extra-instruction", default="", help="appended to the task prompt (for experiments)")
    parser.add_argument("--out", type=Path, help="run directory (default outputs/<timestamp>-<name>)")
    args = parser.parse_args(argv)

    try:
        docs = find_documents(args.path)
    except FileNotFoundError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    if not docs:
        print(f"error: no supported documents under {args.path} (supported: {' '.join(sorted(SUPPORTED))})", file=sys.stderr)
        return 2
    if shutil.which("pandoc") is None:
        print("error: pandoc is required to build the PDF (brew install pandoc)", file=sys.stderr)
        return 2

    stamp = dt.datetime.now().strftime("%Y%m%d-%H%M%S")
    batch = args.path.is_dir()
    name = args.path.name if batch else args.path.stem
    run_dir = args.out or OUTPUTS_DIR / f"{stamp}-{name}{'-replay' if args.replay else ''}"
    outcomes = []
    for doc in docs:
        doc_dir = run_dir / doc.stem if batch else run_dir
        print(f"→ {doc}")
        outcome = process_document(doc, doc_dir, args)
        outcomes.append(outcome)
        print(f"  {outcome['status']}" + (f": {outcome['message']}" if outcome.get("message") else "") +
              (f"  →  {rel(outcome['pdf'])}" if outcome.get("pdf") else ""))
    if batch:
        lines = ["# Course Assistant batch report", "", f"Input directory: `{args.path}`", "",
                 "| Document | Status | PDF | Cost | Report |", "|---|---|---|---|---|"]
        for o in outcomes:
            lines.append(f"| `{Path(o['source']).name}` | {o['status']} | "
                         f"{('`' + os.path.relpath(o['pdf'], run_dir) + '`') if o.get('pdf') else '-'} | "
                         f"${o['cost_usd']:.4f} | `{os.path.relpath(o['run_dir'], run_dir)}/report.md` |")
        (run_dir / "report.md").write_text("\n".join(lines) + "\n")
    print(f"\nRun folder: {rel(run_dir)}")
    statuses = {o["status"] for o in outcomes}
    return 0 if statuses == {"ACCEPTED"} else (2 if "FAILED" in statuses else 1)


if __name__ == "__main__":
    sys.exit(main())
