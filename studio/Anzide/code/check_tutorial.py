"""Deterministic checks for a tutorial produced by the Course Assistant.

This is the independent gate: it never trusts the writer agent's own claims.
It reads the numbered source, the tutorial, and the coverage map, and reports
which success criteria from the delegation card hold. No model is involved.

Usage (standalone):
    python3 check_tutorial.py --source source.numbered.md --tutorial tutorial.md --coverage coverage.md
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from source_blocks import is_code_block, parse_numbered, word_count  # noqa: E402

REQUIRED_HEADINGS = ["## At a glance", "## Before you start", "### Concepts you may not know", "## Errata", "## Omitted"]
CONFIDENCE = {"certain", "likely", "unsure"}
TUTORIAL_HEADING = re.compile(r"^##\s+Tutorial\s+(\d+)\b", re.M)
STEP_HEADING = re.compile(r"^###\s+Step\s+(\d+)\.(\d+)\b(.*)$", re.M)
ANY_HEADING = re.compile(r"^#{1,6}\s", re.M)
COVERAGE_LINE = re.compile(r"^\s*S(\d+)\s*(?:->|→|:)\s*(.+?)\s*$")
SIMPLE_TARGETS = {"at a glance", "before you start", "wrap-up", "wrap up", "reference"}
STEP_TARGET = re.compile(r"^step\s+(\d+)\.(\d+)$", re.I)
TUTORIAL_TARGET = re.compile(r"^tutorial\s+(\d+)$", re.I)
URL = re.compile(r"https?://[^\s<>()\[\]\"']+")
NUMBER = re.compile(r"\d+(?:[.,]\d+)*")
INLINE_CODE = re.compile(r"`([^`\n]+)`")
LIST_MARKER = re.compile(r"^\s*(?:\d+[.)]|#+\s*\d+(?:\.\d+)*\.?)\s+", re.M)
FRONT_MATTER = re.compile(r"\A---\n.*?\n---\n", re.S)


def _norm(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def _numbers(text: str) -> set[str]:
    return {token.replace(",", "") for token in NUMBER.findall(LIST_MARKER.sub("", text))}


def _section(tutorial: str, heading: str) -> str:
    """Body of the first section whose heading line equals ``heading``."""
    lines = tutorial.splitlines()
    for index, line in enumerate(lines):
        if line.strip() == heading:
            level = len(line) - len(line.lstrip("#"))
            body = []
            for later in lines[index + 1:]:
                if ANY_HEADING.match(later) and (len(later) - len(later.lstrip("#"))) <= level:
                    break
                body.append(later)
            return "\n".join(body)
    return ""


def _steps(tutorial: str) -> list[dict]:
    """Each step heading with its tutorial number, step number, and body."""
    steps = []
    current_tutorial = None
    lines = tutorial.splitlines()
    for index, line in enumerate(lines):
        tutorial_match = TUTORIAL_HEADING.match(line)
        if tutorial_match:
            current_tutorial = int(tutorial_match.group(1))
            continue
        step_match = STEP_HEADING.match(line)
        if not step_match:
            continue
        body = []
        for later in lines[index + 1:]:
            if ANY_HEADING.match(later):
                break
            body.append(later)
        steps.append({
            "tutorial": int(step_match.group(1)),
            "number": int(step_match.group(2)),
            "under": current_tutorial,
            "body": "\n".join(body),
            "heading": line.strip(),
        })
    return steps


def parse_coverage(coverage: str) -> tuple[dict[int, list[str]], dict[int, str], list[str]]:
    """Return (block_id -> targets, block_id -> omission reason, parse problems)."""
    targets: dict[int, list[str]] = {}
    omitted: dict[int, str] = {}
    problems: list[str] = []
    for raw in coverage.splitlines():
        if not raw.strip():
            continue
        match = COVERAGE_LINE.match(raw)
        if not match:
            problems.append(f"unparseable line: {raw.strip()!r}")
            continue
        block_id, rest = int(match.group(1)), match.group(2)
        if block_id in targets:
            problems.append(f"S{block_id} listed more than once")
            continue
        if rest.upper().startswith("OMITTED"):
            omitted[block_id] = rest.split(":", 1)[1].strip() if ":" in rest else ""
            targets[block_id] = ["OMITTED"]
            continue
        targets[block_id] = [t.strip() for t in re.split(r"[,;]", rest) if t.strip()]
    return targets, omitted, problems


def check(source: dict[int, str], tutorial: str, coverage: str, *,
          max_ratio: float = 1.75, min_extra: int = 400, max_note_words: int = 50) -> dict:
    """Run every check and return ``{"passed", "checks", "stats", "omitted"}``."""
    checks: list[dict] = []

    def add(check_id: str, name: str, failures: list[str], detail: str = "") -> None:
        checks.append({"id": check_id, "name": name, "passed": not failures,
                       "detail": detail, "failures": failures})

    body = FRONT_MATTER.sub("", tutorial, count=1)   # structure and length ignore the title block
    tutorial_norm = _norm(tutorial)                    # literal checks scan everything, title included

    # STRUCT-1: skeleton sections and at least one tutorial with steps.
    missing = [h for h in REQUIRED_HEADINGS if not re.search(rf"^{re.escape(h)}\s*$", body, re.M)]
    steps = _steps(body)
    tutorials = [int(m) for m in TUTORIAL_HEADING.findall(body)]
    if not tutorials:
        missing.append("## Tutorial 1")
    if not steps:
        missing.append("### Step 1.1")
    add("STRUCT-1", "Skeleton sections present", [f"missing {h}" for h in missing])

    # STRUCT-2: step numbering is sequential and nested under the right tutorial.
    numbering = []
    if tutorials != list(range(1, len(tutorials) + 1)):
        numbering.append(f"tutorial headings numbered {tutorials}, expected 1..{len(tutorials)}")
    for tutorial_number in tutorials:
        found = [s["number"] for s in steps if s["under"] == tutorial_number]
        if found != list(range(1, len(found) + 1)):
            numbering.append(f"Tutorial {tutorial_number} steps numbered {found}, expected 1..{len(found)}")
    for step in steps:
        if step["tutorial"] != step["under"]:
            numbering.append(f"{step['heading']} sits under Tutorial {step['under']}")
    add("STRUCT-2", "Steps numbered in sequence", numbering)

    # STRUCT-3: every step has Do and Check.
    add("STRUCT-3", "Every step has Do and Check", [
        f"{s['heading']} lacks {' and '.join(label for label in ('**Do:**', '**Check:**') if label not in s['body'])}"
        for s in steps if "**Do:**" not in s["body"] or "**Check:**" not in s["body"]
    ])

    # COVER-1: every source block is mapped exactly once to a real target.
    targets, omitted, problems = parse_coverage(coverage)
    step_ids = {f"{s['tutorial']}.{s['number']}" for s in steps}
    for block_id in sorted(set(source) - set(targets)):
        problems.append(f"S{block_id} not mapped")
    for block_id in sorted(set(targets) - set(source)):
        problems.append(f"S{block_id} does not exist in the source")
    for block_id, block_targets in sorted(targets.items()):
        for target in block_targets:
            if target == "OMITTED":
                continue
            step_match = STEP_TARGET.match(target)
            tutorial_match = TUTORIAL_TARGET.match(target)
            if step_match:
                if f"{int(step_match.group(1))}.{int(step_match.group(2))}" not in step_ids:
                    problems.append(f"S{block_id} -> {target}: no such step in the tutorial")
            elif tutorial_match:
                if int(tutorial_match.group(1)) not in tutorials:
                    problems.append(f"S{block_id} -> {target}: no such tutorial section")
            elif target.lower() not in SIMPLE_TARGETS:
                problems.append(f"S{block_id} -> {target!r}: unknown target")
    add("COVER-1", "Every source block mapped or explicitly omitted", problems,
        f"{len(source)} blocks, {len(omitted)} omitted")

    # COVER-2/3/4: literal content of kept blocks survives verbatim.
    kept = {i: b for i, b in source.items() if i not in omitted}
    code_missing, url_missing, number_missing = [], [], []
    tutorial_numbers = _numbers(tutorial)
    for block_id, block in sorted(kept.items()):
        if is_code_block(block):
            for line in block.splitlines()[1:-1]:
                if line.strip() and _norm(line) not in tutorial_norm:
                    code_missing.append(f"S{block_id}: {line.strip()!r}")
            continue
        for span in INLINE_CODE.findall(block):
            if _norm(span) not in tutorial_norm:
                code_missing.append(f"S{block_id}: `{span}`")
        for url in URL.findall(block):
            url = url.rstrip(".,;:!?")
            if url not in tutorial:
                url_missing.append(f"S{block_id}: {url}")
        for token in sorted(_numbers(block) - tutorial_numbers):
            number_missing.append(f"S{block_id}: {token}")
    add("COVER-2", "Code lines and inline code kept verbatim", code_missing)
    add("COVER-3", "URLs kept verbatim", url_missing)
    add("COVER-4", "Numbers kept", number_missing)

    # LENGTH-1: word budget.
    source_words = sum(word_count(b) for b in source.values())
    tutorial_words = word_count(body)
    budget = max(int(source_words * max_ratio), source_words + min_extra)
    add("LENGTH-1", "Tutorial within word budget",
        [f"{tutorial_words} words > budget {budget}"] if tutorial_words > budget else [],
        f"{tutorial_words} words vs {source_words} in source (budget {budget})")

    # LENGTH-2: prerequisite notes are short.
    notes = _notes(_section(body, "### Concepts you may not know"))
    add("LENGTH-2", f"Each prerequisite note <= {max_note_words} words",
        [f"{word_count(n)} words: {n[:60]!r}..." for n in notes if word_count(n) > max_note_words],
        f"{len(notes)} notes")

    # ERRATA-1: every correction cites a real block, quotes text that is really there, and rates confidence.
    errata, errata_problems = parse_errata(_section(body, "## Errata"))
    for row in errata:
        block = source.get(row["block"])
        if block is None:
            errata_problems.append(f"S{row['block']}: no such source block")
        elif _norm(row["source_says"].strip("`")) not in _norm(block.replace("`", "")):
            errata_problems.append(f"S{row['block']}: quoted text {row['source_says']!r} is not in that block")
        if row["confidence"].lower() not in CONFIDENCE:
            errata_problems.append(f"S{row['block']}: confidence {row['confidence']!r} not in {sorted(CONFIDENCE)}")
    add("ERRATA-1", "Each correction quotes real source text and rates confidence", errata_problems,
        f"{len(errata)} corrections")

    return {
        "passed": all(c["passed"] for c in checks),
        "checks": checks,
        "stats": {"source_blocks": len(source), "source_words": source_words,
                  "tutorial_words": tutorial_words, "word_budget": budget,
                  "tutorials": len(tutorials), "steps": len(steps), "notes": len(notes),
                  "omitted": len(omitted), "errata": len(errata)},
        "omitted": [{"block": i, "reason": omitted[i], "text": source.get(i, "")} for i in sorted(omitted)],
        "errata": errata,
    }


def parse_errata(section: str) -> tuple[list[dict], list[str]]:
    """Rows of the Errata pipe table: Block | Source says | Should be | Evidence | Confidence."""
    rows: list[dict] = []
    problems: list[str] = []
    for line in section.splitlines():
        if not line.strip().startswith("|"):
            continue
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        if not cells or cells[0].lower() == "block" or set(cells[0]) <= set("-: "):
            continue  # header or separator row
        if len(cells) != 5:
            problems.append(f"errata row has {len(cells)} cells, expected 5: {line.strip()!r}")
            continue
        block_match = re.fullmatch(r"\[?S(\d+)\]?", cells[0])
        if not block_match:
            problems.append(f"errata row has no block id: {line.strip()!r}")
            continue
        rows.append({"block": int(block_match.group(1)), "source_says": cells[1], "should_be": cells[2],
                     "evidence": cells[3], "confidence": cells[4]})
    return rows, problems


def _notes(section: str) -> list[str]:
    notes: list[str] = []
    for line in section.splitlines():
        if re.match(r"^\s*[-*+]\s+", line):
            notes.append(re.sub(r"^\s*[-*+]\s+", "", line))
        elif line.strip() and notes:
            notes[-1] += " " + line.strip()
    return notes


def format_report(result: dict) -> str:
    lines = [f"Overall: {'PASS' if result['passed'] else 'FAIL'}"]
    for c in result["checks"]:
        lines.append(f"[{'ok' if c['passed'] else 'FAIL'}] {c['id']} {c['name']}" + (f" ({c['detail']})" if c["detail"] else ""))
        lines.extend(f"      - {f}" for f in c["failures"][:20])
        if len(c["failures"]) > 20:
            lines.append(f"      ... {len(c['failures']) - 20} more")
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--source", required=True, type=Path, help="numbered source ([S1] blocks)")
    parser.add_argument("--tutorial", required=True, type=Path)
    parser.add_argument("--coverage", required=True, type=Path)
    parser.add_argument("--max-ratio", type=float, default=1.75)
    parser.add_argument("--json", action="store_true", help="print JSON instead of text")
    args = parser.parse_args()
    result = check(parse_numbered(args.source.read_text()), args.tutorial.read_text(),
                   args.coverage.read_text(), max_ratio=args.max_ratio)
    print(json.dumps(result, indent=2) if args.json else format_report(result))
    return 0 if result["passed"] else 1


if __name__ == "__main__":
    sys.exit(main())
