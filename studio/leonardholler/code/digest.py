"""Render and check a digest from source readings collected by local Codex.
No network or model calls: weekly refresh requires the agent to read sources again.
"""
import argparse
import hashlib
import json
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parents[1]
SOURCES = {
    "anthropic-news": "https://www.anthropic.com/news",
    "anthropic-engineering": "https://www.anthropic.com/engineering",
    "openai-news": "https://openai.com/news/",
}


def build(readings, run_date):
    start = run_date - timedelta(days=6)
    events, candidates, missing = [], [], []
    seen = set()
    for name, url in SOURCES.items():
        source = readings["sources"].get(name)
        if not source or source.get("status") != "read":
            missing.append(name)
            events.append({"event": "source_error", "source": name,
                           "url": url, "reason": "Source input missing or unreadable"})
            continue
        if source["url"] != url:
            raise ValueError("Unapproved source URL")
        events.append({"event": "source_checked", "source": name, "url": url,
                       "note": source["note"]})
        for article in source["articles"]:
            reason = None
            try:
                published = date.fromisoformat(article["date"])
            except (KeyError, ValueError, TypeError):
                published = None
                reason = "missing_or_invalid_date"
            link = urlparse(article.get("url", ""))
            if link.scheme != "https" or link.netloc != urlparse(url).netloc:
                reason = "unapproved_article_url"
            elif not article.get("read") or not article.get("date_evidence"):
                reason = "missing_reading_or_date_evidence"
            elif published is not None and not start <= published <= run_date:
                reason = "outside_date_window"
            elif not article.get("summary") or not article.get("title"):
                reason = "missing_summary_or_title"
            elif article["url"].rstrip("/") in seen:
                reason = "duplicate_url"
            if reason:
                events.append({"event": "article_excluded", "url": article.get("url"),
                               "reason": reason})
                continue
            seen.add(article["url"].rstrip("/"))
            candidates.append({**article, "source": name})
    candidates.sort(key=lambda a: (-date.fromisoformat(a["date"]).toordinal(), a["title"]))
    selected = candidates[:5]
    for article in candidates:
        events.append({"event": "article_selected" if article in selected else "article_excluded",
                       "url": article["url"], "reason": "eligible" if article in selected else "five_article_limit"})
    checks = {
        "at_most_five": len(selected) <= 5,
        "unique_urls": len({a["url"].rstrip("/") for a in selected}) == len(selected),
        "dates_in_window": all(start <= date.fromisoformat(a["date"]) <= run_date for a in selected),
        "required_fields": all(all(a.get(k) for k in ("title", "date", "url", "summary", "date_evidence")) for a in selected),
        "all_sources_available": not missing,
    }
    status = "PARTIAL" if missing else "COMPLETE WITHIN INSPECTED COVERAGE"
    lines = ["# Weekly AI news digest", "", f"Date window: {start} through {run_date} (inclusive, America/New_York).",
             f"Status: {status}", "", "Coverage is limited to the source pages and articles read by Codex; it is not exhaustive.", ""]
    for name, url in SOURCES.items():
        lines.append(f"- [{name}]({url}): " + ("MISSING INPUT — coverage unavailable." if name in missing else readings["sources"][name]["note"]))
    if not selected:
        lines.extend(["", "No eligible articles found in the available inspected inputs."])
    for a in selected:
        lines.extend(["", f"## {a['title']}", "", f"{a['date']} | {a['source']} | [Source]({a['url']})", "", a["summary"]])
    events.append({"event": "checks", "results": checks,
                   "limitation": "Checks validate recorded metadata, not factual accuracy or current link availability; those require article reading."})
    return "\n".join(lines) + "\n", {"status": status, "article_count": len(selected), "missing_sources": missing, "checks": checks}, events


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--date", type=date.fromisoformat, required=True)
    args = parser.parse_args()
    if not args.run_id or any(c not in "abcdefghijklmnopqrstuvwxyz0123456789-_" for c in args.run_id):
        parser.error("run-id must use lowercase letters, digits, hyphens or underscores")
    input_path = args.input.resolve()
    if not input_path.is_relative_to(ROOT):
        parser.error("input must remain inside this studio folder")
    raw = input_path.read_bytes()
    readings = json.loads(raw)
    digest, result, events = build(readings, args.date)
    out = ROOT / "outputs" / args.run_id
    out.mkdir(exist_ok=False)  # Preserve previous evidence.
    result["input_sha256"] = hashlib.sha256(raw).hexdigest()
    result["run_date"] = str(args.date)
    result["executed_at_utc"] = datetime.now(timezone.utc).isoformat()
    result["mode"] = "Replay of agent-collected source readings; no fresh network requests"
    (out / "digest.md").write_text(digest)
    (out / "result.json").write_text(json.dumps(result, indent=2) + "\n")
    (out / "trace.jsonl").write_text("".join(json.dumps(e) + "\n" for e in events))
    print(json.dumps({"run": args.run_id, **result}, indent=2))
    return 2 if result["missing_sources"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
