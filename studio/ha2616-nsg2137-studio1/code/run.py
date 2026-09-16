#!/usr/bin/env python3
"""Run the saved briefing prompt and preserve real Codex events. Standard library only."""
import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("name", help="New folder name under outputs/")
    parser.add_argument("--sources", default="inputs/sources.txt")
    args = parser.parse_args()
    if not args.name or Path(args.name).name != args.name or args.name in (".", ".."):
        parser.error("name must be a single folder name")
    sources = (ROOT / args.sources).resolve()
    if not sources.is_relative_to(ROOT):
        parser.error("sources must be inside this studio folder")
    out = ROOT / "outputs" / args.name
    out.mkdir(exist_ok=False)  # Never overwrite evidence from an earlier run.
    started = datetime.now(timezone.utc).isoformat()
    prompt = (ROOT / "code/prompt.txt").read_text().format(
        sources=sources.relative_to(ROOT), as_of=started)
    (out / "prompt.txt").write_text(prompt)
    source_bytes = sources.read_bytes() if sources.is_file() else None
    if source_bytes is not None:
        (out / "sources.txt").write_bytes(source_bytes)
    command = ["codex", "--search", "exec", "--ignore-user-config", "--ephemeral",
               "--sandbox", "read-only", "--json", "--color", "never",
               "--output-last-message", str(out / "briefing.md"), "-"]
    record = {"started_at": started, "source_path": args.sources,
              "source_exists": source_bytes is not None,
              "source_sha256": hashlib.sha256(source_bytes).hexdigest() if source_bytes is not None else None,
              "command": command, "codex_version": subprocess.check_output(
                  ["codex", "--version"], text=True).strip(), "email_sent_by_runner": False}
    with (out / "trace.jsonl").open("w") as trace, (out / "stderr.log").open("w") as errors:
        try:
            result = subprocess.run(command, input=prompt, text=True, cwd=ROOT,
                                    stdout=trace, stderr=errors, timeout=600)
            record["exit_code"] = result.returncode
        except (subprocess.TimeoutExpired, OSError) as error:
            record["exit_code"] = 1
            record["runner_error"] = str(error)
    record["finished_at"] = datetime.now(timezone.utc).isoformat()
    final = out / "briefing.md"
    output = final.read_text() if final.exists() else ""
    events = [json.loads(line) for line in (out / "trace.jsonl").read_text().splitlines() if line.strip()]
    items = [e["item"] for e in events if e.get("type") == "item.completed"]
    web_calls = sum(item.get("type") == "web_search" for item in items)
    stopped = output.startswith("STOP: missing or invalid source input")
    checks = {"cli_succeeded": record["exit_code"] == 0,
              "turn_completed": any(e.get("type") == "turn.completed" for e in events),
              "output_present": bool(output.strip()), "word_count": len(output.split()),
              "under_800_words": len(output.split()) < 800,
              "responsible_stop": stopped,
              "web_tool_calls": web_calls,
              "within_web_budget": web_calls <= 12,
              "no_browsing_after_missing_input": source_bytes is not None or web_calls == 0,
              "both_sections": "## Anthropic" in output and "## OpenAI" in output,
              "manual_review_required": "Verify article dates, factual claims, links, freshness labels, and tool behavior in trace.jsonl."}
    expected_behavior = stopped if source_bytes is None else checks["both_sections"] and not stopped
    checks["basic_checks_pass"] = all(checks[k] for k in
        ("cli_succeeded", "turn_completed", "output_present", "under_800_words",
         "within_web_budget", "no_browsing_after_missing_input")) and expected_behavior
    (out / "run.json").write_text(json.dumps(record, indent=2) + "\n")
    (out / "checks.json").write_text(json.dumps(checks, indent=2) + "\n")
    print(json.dumps({"output": str(out), **checks}, indent=2))
    return 0 if checks["basic_checks_pass"] else 1


if __name__ == "__main__":
    sys.exit(main())
