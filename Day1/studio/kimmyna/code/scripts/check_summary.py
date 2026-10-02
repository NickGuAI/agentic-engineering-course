#!/usr/bin/env python3
"""Pre-written checker for lecture summaries. NOT to be created or edited by the
agent during a run -- this file defines the "observable check" and must stay
fixed so pass/fail means the same thing across runs.

Usage:
    python3 scripts/check_summary.py <n>

Reads:
    approved/{n}-keywords.json   -- human-approved keyword list (the gate)
    summaries/{n}.md             -- the agent's summary to check

Writes:
    summaries/{n}-report.md      -- always written, pass or fail

Exit code: 0 if all checks pass, 1 otherwise.
"""
from __future__ import annotations
import json
import random
import re
import sys
from pathlib import Path

TAG_RE = re.compile(r"\[p\.\d+\]|\[보충\]")
HEADER_RE = re.compile(r"^#{1,3}\s+(.*)")


def load_keywords(n: str) -> dict | None:
    path = Path(f"approved/{n}-keywords.json")
    if not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def load_summary(n: str) -> str:
    return Path(f"summaries/{n}.md").read_text(encoding="utf-8")


def split_sections(text: str) -> dict[str, str]:
    sections: dict[str, str] = {}
    current, buf = None, []
    for line in text.splitlines():
        m = HEADER_RE.match(line)
        if m:
            if current is not None:
                sections[current] = "\n".join(buf)
            current, buf = m.group(1).strip(), []
        else:
            buf.append(line)
    if current is not None:
        sections[current] = "\n".join(buf)
    return sections


def names_for(kw: dict) -> list[str]:
    return [kw["term"]] + kw.get("aliases", [])


def check_coverage(keywords: dict, text: str) -> list[str]:
    missing = []
    for kw in keywords["core"] + keywords.get("minor", []):
        if not any(re.search(re.escape(n), text, re.IGNORECASE) for n in names_for(kw)):
            missing.append(kw["term"])
    return missing


def check_traceability(sections: dict[str, str]) -> list[tuple[str, str]]:
    untagged = []
    for name, body in sections.items():
        if name.strip().lower().startswith("lecture flow"):
            continue  # flow section is checked separately, with its own rule
        for para in re.split(r"\n\s*\n", body):
            for line in (l for l in para.splitlines() if l.strip()):
                if not TAG_RE.search(line):
                    untagged.append((name, line.strip()[:70]))
    return untagged


def check_flow(sections: dict[str, str], keywords: dict, full_text: str) -> dict:
    flow_key = next((k for k in sections if k.strip().lower().startswith("lecture flow")), None)
    core_terms = [kw["term"] for kw in keywords["core"]]
    if flow_key is None:
        return {"exists": False, "missing_core": core_terms, "order_ok": False, "missing_page_tags": core_terms}

    flow_text = sections[flow_key]
    missing_core = [t for t in core_terms if not re.search(re.escape(t), flow_text, re.IGNORECASE)]

    missing_page_tags = []
    for t in core_terms:
        if t in missing_core:
            continue
        if not re.search(re.escape(t) + r".{0,40}?\[p\.\d+\]", flow_text, re.IGNORECASE | re.DOTALL):
            missing_page_tags.append(t)

    def first_pos(text: str, term: str) -> int:
        m = re.search(re.escape(term), text, re.IGNORECASE)
        return m.start() if m else 10**9

    present = [t for t in core_terms if t not in missing_core]
    doc_before_flow = full_text.split(flow_text, 1)[0]
    flow_order = sorted(present, key=lambda t: first_pos(flow_text, t))
    doc_order = sorted(present, key=lambda t: first_pos(doc_before_flow, t))
    order_ok = flow_order == doc_order

    return {"exists": True, "missing_core": missing_core, "order_ok": order_ok,
            "missing_page_tags": missing_page_tags}


def write_report(n: str, report: dict) -> None:
    out = Path(f"summaries/{n}-report.md")
    out.parent.mkdir(parents=True, exist_ok=True)
    lines = [f"# Check report — lecture {n}", "", f"**Passed:** {report.get('passed')}", ""]
    if "error" in report:
        lines.append(f"Error: {report['error']}")
    else:
        lines.append(f"## Coverage\nMissing keywords: {report['coverage_missing'] or 'none'}\n")
        lines.append(f"## Traceability\nUntagged lines: {report['traceability_untagged_count']}")
        for sec, snippet in report["traceability_untagged"][:20]:
            lines.append(f"- [{sec}] {snippet}")
        f = report["flow"]
        lines.append(f"\n## Lecture Flow\nExists: {f['exists']} | Missing core: {f['missing_core']} | "
                     f"Order OK: {f['order_ok']} | Missing page tags: {f['missing_page_tags']}")
        lines.append("\n## Spot-check sample (5 random tagged items — human reviews these)")
        for s in report["spot_check_sample"]:
            lines.append(f"- {s}")
    out.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    if len(sys.argv) != 2:
        print("Usage: check_summary.py <n>", file=sys.stderr)
        sys.exit(2)
    n = sys.argv[1]

    keywords = load_keywords(n)
    if keywords is None:
        report = {"lecture": n, "passed": False, "error": f"approved/{n}-keywords.json not found"}
        write_report(n, report)
        print(json.dumps(report, ensure_ascii=False, indent=2))
        sys.exit(1)

    text = load_summary(n)
    sections = split_sections(text)
    missing = check_coverage(keywords, text)
    untagged = check_traceability(sections)
    flow = check_flow(sections, keywords, text)

    passed = (not missing and not untagged and flow["exists"]
              and not flow["missing_core"] and flow["order_ok"] and not flow["missing_page_tags"])

    tagged_items = re.findall(r".{0,60}\[(?:p\.\d+|보충)\].{0,20}", text)
    sample = random.sample(tagged_items, min(5, len(tagged_items)))

    report = {
        "lecture": n, "passed": passed,
        "coverage_missing": missing,
        "traceability_untagged": untagged[:20],
        "traceability_untagged_count": len(untagged),
        "flow": flow,
        "spot_check_sample": sample,
    }
    write_report(n, report)
    print(json.dumps(report, ensure_ascii=False, indent=2))
    sys.exit(0 if passed else 1)


if __name__ == "__main__":
    main()
