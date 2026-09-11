#!/usr/bin/env python3
"""Inspect the saved Step 3 run and compare it with its preserved baseline."""
from pathlib import Path
from datetime import datetime, date
from urllib.parse import urlparse
import hashlib
import json
import re

BASE = Path(__file__).resolve().parent
def read(name):
    return json.loads((BASE / name).read_text())
def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

m = read("run-manifest.json")
policy = read("source-policy.json")
before = read("evidence/preservation-before.json")
preflight = read("evidence/policy-preflight.json")
baseline = BASE.parent / m["baseline_run"]
old = json.loads((baseline / "run-manifest.json").read_text())
reports = [read(p) for p in m["source_reports"]]
candidates = {c["id"]: c for r in reports for c in r.get("eligible_candidates", r.get("candidates", []))}
old_reports = [json.loads((baseline / p).read_text()) for p in old["source_reports"]]
old_candidates = {c["id"]: c for r in old_reports for c in r.get("eligible_candidates", r.get("candidates", []))}
digest = (BASE / "research-update.md").read_text()
trace = [json.loads(line) for line in (BASE / "execution-trace.jsonl").read_text().splitlines() if line.strip()]
web_events = [e for e in trace if e.get("event") == "source_inspection"]
actual_urls = [url for e in web_events for url in e["target_urls"]]
items = m["selected_items"]
old_items = old["selected_items"]
old_urls = {i["url"] for i in old_items}
new_urls = {i["url"] for i in items}
words = {i["id"]: len(candidates[i["id"]]["summary"].split()) for i in items}
window = m["publication_window"]
lo, hi = date.fromisoformat(window["start"]), date.fromisoformat(window["end"])

def allowed(url):
    parsed = urlparse(url)
    if parsed.scheme != "https":
        return False
    if parsed.hostname == "www.anthropic.com":
        return parsed.path == "/news" or url in {i["url"] for r in reports if r["source"] == "Anthropic News" for i in r.get("candidates", [])}
    return parsed.hostname == "openai.com" and (parsed.path == "/news/" or url in {i["url"] for r in reports if r["source"] == "OpenAI News" for i in r.get("eligible_candidates", [])})

current_hashes = {str(p.relative_to(baseline)): sha(p) for p in sorted(baseline.rglob("*")) if p.is_file()}
baseline_added = sorted(set(current_hashes) - set(before["baseline_files"]))
explanation_now = sha(BASE / "../../explanation-ey2419.md")
checks = {
    "baseline_original_files_unchanged": all(current_hashes.get(name) == digest for name, digest in before["baseline_files"].items()),
    "baseline_additions_only_macos_metadata": all(Path(name).name == ".DS_Store" for name in baseline_added),
    "card_unchanged": sha(BASE / "../../delegation-card.md") == before["card_sha256"] == old["card_sha256"],
    "one_allowed_source_removed": set(old["allowed_listing_urls"]) - set(m["allowed_listing_urls"]) == {"https://www.anthropic.com/engineering"} and set(m["allowed_listing_urls"]) <= set(old["allowed_listing_urls"]),
    "date_window_timezone_limits_selection_unchanged": all(m[k] == old[k] for k in ["publication_window", "timezone", "limits", "selection_policy"]),
    "source_page_allocations_unchanged": policy["inherited_controls"]["max_distinct_article_pages_per_remaining_source"] == 5 and all(r.get("distinct_article_pages", 0) <= 5 for r in reports),
    "baseline_plan_fails_changed_policy": preflight["baseline_plan_allowed"] is False and preflight["rejected_baseline_targets"] == ["https://www.anthropic.com/engineering"],
    "corrected_plan_passes_changed_policy": preflight["corrected_plan_allowed"] is True and preflight["corrected_listing_plan"] == m["allowed_listing_urls"],
    "no_excluded_engineering_fetch": all(not (urlparse(u).hostname in {"www.anthropic.com", "anthropic.com"} and urlparse(u).path.startswith("/engineering")) for u in actual_urls),
    "all_requested_targets_allowed": bool(actual_urls) and all(allowed(u) for u in actual_urls),
    "fresh_inspection_after_run_start": all(datetime.fromisoformat(e["timestamp"].replace(" UTC", "+00:00").replace(" ", "T")) >= datetime.fromisoformat(m["started_at"]) for e in web_events),
    "two_allowed_listings_retrieved": set(e["target_urls"][0] for e in web_events if "open" in e["request"]) == set(m["allowed_listing_urls"]),
    "at_most_five_digest_entries": 0 <= len(items) <= 5 and len(re.findall(r"^## [0-9]+[.]", digest, re.M)) == len(items),
    "dates_in_window_and_sorted": all(lo <= date.fromisoformat(i["publication_date"]) <= hi for i in items) and [i["publication_date"] for i in items] == sorted([i["publication_date"] for i in items], reverse=True),
    "no_duplicate_urls_or_ids": len(new_urls) == len(items) == len({i["id"] for i in items}),
    "summary_word_limits": all(n <= 100 for n in words.values()),
    "selected_items_match_fresh_reports": all(i["id"] in candidates and i["url"] == candidates[i["id"]]["url"] and i["publication_date"] == candidates[i["id"]].get("publication_date", candidates[i["id"]].get("published_date")) and candidates[i["id"]].get("date_evidence") for i in items),
    "digest_contains_verified_content": all(all(v in digest for v in [i["title"], i["publication_date"], i["url"], candidates[i["id"]]["summary"]]) for i in items),
    "exclusion_and_reduced_coverage_disclosed": "Anthropic Engineering is excluded by policy" in digest and "Coverage is incomplete" in digest,
    "article_budget_respected": m["measurements"]["distinct_article_pages"] <= 15 and m["measurements"]["article_target_operations_including_find"] <= 15,
    "recorded_web_call_count_matches": len(web_events) == m["measurements"]["web_tool_calls"],
    "recorded_url_operations_match": len(actual_urls) == m["measurements"]["article_target_operations_including_find"] + m["measurements"]["listing_target_operations"],
    "no_failed_url_retries": m["measurements"]["failed_urls"] == 0 and m["measurements"]["retries"] == 0,
    "comparison_and_log_present": all((BASE / f).is_file() for f in ["comparison.md", "run-log.md"]),
    "saved_json_parses": all(json.loads(p.read_text()) is not None for p in BASE.rglob("*.json")),
}
checks = {key: bool(value) for key, value in checks.items()}
summary_changes = [i["id"] for i in items if i["id"] in old_candidates and candidates[i["id"]]["summary"] != old_candidates[i["id"]]["summary"]]
comparison = {
    "baseline_run": baseline.name, "changed_run": BASE.name,
    "added_item_urls": sorted(new_urls - old_urls), "removed_item_urls": sorted(old_urls - new_urls),
    "same_item_order": [i["url"] for i in items] == [i["url"] for i in old_items],
    "summary_wording_changed_ids": summary_changes,
    "baseline_file_count": len(before["baseline_files"]),
    "baseline_original_files_unchanged": checks["baseline_original_files_unchanged"],
    "baseline_added_files": baseline_added,
    "personal_explanation_changed_during_run": explanation_now != before["explanation_sha256"],
    "metric_differences": {k: {"baseline": old["measurements"][k], "changed": m["measurements"][k], "delta": m["measurements"][k] - old["measurements"][k]} for k in ["eligible_candidates", "selected_items", "distinct_article_pages", "article_target_operations_including_find", "listing_target_operations", "web_tool_calls", "failed_urls", "retries"]},
}
(BASE / "comparison-data.json").write_text(json.dumps(comparison, indent=2) + "\n")
observations = {"baseline_added_files": baseline_added, "personal_explanation_changed_during_run": explanation_now != before["explanation_sha256"], "explanation_sha256_before": before["explanation_sha256"], "explanation_sha256_after": explanation_now, "note": "Current explanation text is preserved. Hashes detect a change but do not identify its author. No explanation edits were performed by the agents in this run."}
status = "FAIL" if not all(checks.values()) else ("PASS_WITH_NOTES" if baseline_added or observations["personal_explanation_changed_during_run"] else "PASS")
result = {"inspected_at": datetime.now().astimezone().isoformat(timespec="seconds"), "status": status, "passed_checks": sum(checks.values()), "total_checks": len(checks), "checks": checks, "observations": observations, "summary_word_counts": words, "limits_of_automation": "Checks saved artifacts and recorded requests, not independent factual truth or the absence of unlogged actions."}
(BASE / "validation.json").write_text(json.dumps(result, indent=2) + "\n")
with (BASE / "execution-trace.jsonl").open("a") as f:
    f.write(json.dumps({"timestamp": result["inspected_at"], "event": "artifact_inspection", "tool": "inspect_run.py", "outcome": result["status"], "passed": result["passed_checks"], "total": result["total_checks"]}) + "\n")
print(json.dumps(result, indent=2))
raise SystemExit(0 if all(checks.values()) else 1)
