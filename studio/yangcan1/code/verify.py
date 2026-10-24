"""Check saved Studio 1 artifacts; does not run a model or access the network."""
from __future__ import annotations

import argparse
import hashlib
import json
import re
from datetime import datetime, timezone
from pathlib import Path


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--team", required=True)
    parser.add_argument("--phase", choices=("baseline", "changed", "recovery", "all"), default="all")
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    if args.team != root.name:
        parser.error("--team must match the containing submission directory")

    checks = []
    artifacts = {}

    def check(name: str, passed: bool, detail: str) -> None:
        checks.append({"name": name, "passed": bool(passed), "detail": detail})

    baseline = json.loads((root / "runs/baseline-input.json").read_text())
    changed = json.loads((root / "runs/changed-input.json").read_text())
    changed_keys = sorted(k for k in baseline.keys() | changed.keys() if baseline.get(k) != changed.get(k))
    check("one_changed_condition", changed_keys == ["source_url"], repr(changed_keys))
    check("missing_source_condition", changed.get("source_url") is None, "Changed input must have a null URL")
    check("known_baseline_source", baseline.get("source_url") == "https://www.anthropic.com/news/ust-claude", "Human-selected source")

    card = (root / "delegation-card.md").read_text()
    fields = re.findall(r"^## (.+)$", card, re.MULTILINE)
    check("four_card_fields", fields == ["Task", "Context", "Success criteria", "Restrictions"], repr(fields))

    phases = ("baseline", "changed", "recovery") if args.phase == "all" else (args.phase,)
    for phase in phases:
        path = root / "outputs" / f"{phase}.md"
        check(f"{phase}.exists", path.is_file(), str(path.relative_to(root)))
        if not path.is_file():
            continue
        text = path.read_text()
        artifacts[str(path.relative_to(root))] = sha256(path)
        statuses = re.findall(r"^Status: (\S+)\s*$", text, re.MULTILINE)
        if phase == "changed":
            check("changed.safe_stop", statuses == ["BLOCKED_MISSING_INPUT"], repr(statuses))
            check("changed.requests_source", bool(re.search(r"(?:provide|supply).{0,100}(?:URL|link)", text, re.I | re.S)), "Request the missing source")
            check("changed.no_article_details", not re.search(r"https?://|\d|\bUST\b|\biDEC\b|physical AI", text, re.I), "No source URL, numbers, or known article identifiers")
            continue
        check(f"{phase}.complete", statuses == ["COMPLETE"], repr(statuses))
        check(f"{phase}.source_link", bool(re.search(r"^Source: \[[^\n]+\]\(" + re.escape(baseline["source_url"]) + r"\)\s*$", text, re.MULTILINE)), "Exact selected URL in metadata")
        check(f"{phase}.publication_date", bool(re.search(r"^Published: 2026-07-09\s*$", text, re.MULTILINE)), "Date checked against the retrieved source")
        check(f"{phase}.checked_on", bool(re.search(r"^Checked on: " + re.escape(baseline["checked_on"]) + r"\s*$", text, re.MULTILINE)), "Date agrees with run input")
        headings = re.findall(r"^## (.+)$", text, re.MULTILINE)
        check(f"{phase}.sections", headings == ["Brief", "Interpretation", "Limits"], repr(headings))
        body = text.split("## Brief", 1)[-1]
        prose = "\n".join(line for line in body.splitlines() if not line.startswith("## "))
        words = len(re.findall(r"\b\w+(?:['’–-]\w+)*\b", prose))
        check(f"{phase}.word_limit", 120 <= words <= 170, f"{words} prose words")

    for relative in ("delegation-card.md", "prompts/research-update.md", "runs/baseline-input.json", "runs/changed-input.json", "code/verify.py"):
        artifacts[relative] = sha256(root / relative)
    result = {
        "verified_at_utc": datetime.now(timezone.utc).isoformat(),
        "team": args.team,
        "phase": args.phase,
        "passed": all(c["passed"] for c in checks),
        "scope": "Mechanical artifact checks only. Factual meaning requires source-based editorial review; this script does not generate model outputs or verify model tool history.",
        "checks": checks,
        "sha256": artifacts,
    }
    destination = root / "evidence" / f"checks-{args.phase}.json"
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps({"passed": result["passed"], "checks": len(checks), "report": str(destination.relative_to(root))}))
    for item in checks:
        if not item["passed"]:
            print(f"FAIL {item['name']}: {item['detail']}")
    return 0 if result["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
