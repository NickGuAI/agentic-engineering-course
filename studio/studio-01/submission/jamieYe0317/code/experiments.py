"""Explicit synthetic demos and comparisons; never passed off as live research."""
import copy
from datetime import datetime, timezone
import json
from pathlib import Path
import uuid

from evidence import canonical, count_tokens, fingerprint


def fixture_collection():
    sources = [
        {"source_id": "openai_news", "url": "https://openai.com/news/", "status": "ok"},
        {"source_id": "anthropic_news", "url": "https://www.anthropic.com/news", "status": "ok"},
        {"source_id": "anthropic_engineering", "url": "https://www.anthropic.com/engineering", "status": "ok"}]
    articles = []
    for i in range(5):
        source = sources[i % 3]
        url = ("https://openai.com/index/" if i % 3 == 0 else source["url"] + "/") + "synthetic-fixture-%d" % i
        paragraphs = [
            {"id": "p001", "text": "Synthetic fixture %d: Example Lab announces a research assistant that sorts technical announcements and saves a cited reading list. The release adds source identifiers and a readable activity report so students can inspect which pages informed the result." % i},
            {"id": "p002", "text": "Availability is limited to a small preview. The assistant cannot independently verify publisher claims, and students must review the cited evidence before relying on a summary. This is invented test content, not an actual product announcement."}]
        for n in range(12):
            paragraphs.append({"id": "p%03d" % (n + 3), "text":
                "Background passage %d for synthetic article %d describes the color of the office walls, the arrangement of chairs, the weekly lunch menu, and a sequence of unrelated administrative details about desks, bookshelves, and meeting rooms." % (n, i)})
        articles.append({"article_id": "fixture-%d" % i, "source_id": source["source_id"],
                         "url": url, "title": "Synthetic fixture %d: research assistant preview" % i,
                         "published_at": "2026-09-15", "date_precision": "date",
                         "date_provenance": "synthetic_fixture", "paragraphs": paragraphs,
                         "content_hash": fingerprint(paragraphs), "parser_version": "synthetic-v1"})
    return {"articles": articles, "sources": sources, "coverage_limited": False, "exclusions": []}


class FixtureModel:
    """Deterministic test double: usage is simulated, never real provider usage."""
    def __init__(self, root, invalid_first=False, unknown_usage=False):
        self.root = Path(root)
        self.prompt = (self.root / "prompts/summarize.md").read_text()
        self.schema_text = (self.root / "prompts/summary.schema.json").read_text()
        self.identity = {"backend": "scripted_fixture", "model": "fixture-v1", "reasoning": "none"}
        self.calls = []
        self.invalid_first = invalid_first
        self.unknown_usage = unknown_usage

    def build_input(self, payload):
        return self.prompt + "\n" + canonical(payload)

    def generate(self, payload, timeout):
        self.calls.append(copy.deepcopy(payload))
        items = []
        for article in payload["articles"]:
            item = {"article_id": article["article_id"],
                    "summary": "In this synthetic fixture, Example Lab announces a research assistant that organizes technical announcements into a cited reading list. The preview includes source identifiers and an activity report for inspection. Availability remains limited, and the assistant cannot independently verify publisher claims, so students must review the evidence before trusting its summaries.",
                    "relevance": "Inspecting the cited evidence could help students practice evaluating automated research while recognizing the limits of a preview tool.",
                    "evidence_ids": [p["id"] for p in article["evidence"][:2]],
                    "insufficient_evidence": False}
            items.append(item)
        if self.invalid_first and len(self.calls) == 1 and items:
            items[0]["evidence_ids"] = ["invented-paragraph"]
        input_count = count_tokens(self.build_input(payload) + "\n" + self.schema_text)
        output_count = count_tokens(canonical(items))
        usage = {"input_tokens": input_count, "output_tokens": output_count,
                 "total_tokens": input_count + output_count, "cached_input_tokens": 0,
                 "reasoning_output_tokens": 0}
        return {"items": items, "usage": None if self.unknown_usage else usage,
                "usage_known": not self.unknown_usage}


def compare_runs(root, run_ids):
    from run import safe_id, write_json, load_policy, verify_saved
    from harness import Harness
    if len(run_ids) < 2:
        raise ValueError("compare_requires_at_least_two_runs")
    h = Harness(root, load_policy(root), "compare")
    rows = []
    for rid in run_ids:
        rid = safe_id(rid)
        def read(name):
            return json.loads(h.safe_path("outputs/%s/%s.json" % (rid, name)).read_text())
        status, manifest, usage, verification = (read(n) for n in ("status", "manifest", "usage", "verification"))
        fresh = False
        if status["status"] in ("complete", "partial"):
            try:
                fresh = verify_saved(root, rid)["passed"]
            except (OSError, ValueError, KeyError, TypeError):
                fresh = False
        rows.append({"run_id": rid, "mode": status["mode"], "status": status["status"],
                     "as_of": manifest["as_of"], "model": manifest["model"],
                     "source_failure_policy": manifest["source_failure_policy"],
                     "fault_injection": manifest["fault_injection"],
                     "snapshot_hash": manifest.get("input_snapshot_hash"),
                     "evidence_mode": manifest["evidence_mode"],
                     "implementation": manifest["implementation"]["hash"],
                     "policy_hash": manifest["policy_hash"],
                     "selected_items": len(manifest["selected_articles"]),
                     "selected_article_ids": sorted(a["article_id"] for a in manifest["selected_articles"]),
                     "automated_checks_passed": verification["passed"],
                     "fresh_verification_passed": fresh,
                     "application_count_method": usage["application_count_method"],
                     "usage_kind": usage["usage_kind"], "counters": usage["counters"],
                     "cache_hits": usage["cache_hits"], "provider_usage": usage["provider_usage"]})
    reduction = None
    left, right = rows[:2]
    if (left["evidence_mode"] == "full" and right["evidence_mode"] == "compact"
            and left["status"] in ("complete", "partial") and right["status"] in ("complete", "partial")
            and left["automated_checks_passed"] and right["automated_checks_passed"]
            and left["fresh_verification_passed"] and right["fresh_verification_passed"]
            and left["selected_items"] > 0
            and left["model"] == right["model"] and left["snapshot_hash"] == right["snapshot_hash"]
            and left["policy_hash"] == right["policy_hash"]
            and left["implementation"] == right["implementation"]
            and left["fault_injection"] == right["fault_injection"]
            and left["source_failure_policy"] == right["source_failure_policy"]
            and left["application_count_method"] == right["application_count_method"]
            and left["cache_hits"] == right["cache_hits"] == 0
            and left["counters"]["model_calls"] == right["counters"]["model_calls"] == 1
            and left["counters"]["application_input_tokens"] > 0
            and right["counters"]["application_input_tokens"] > 0
            and left["selected_article_ids"] == right["selected_article_ids"]):
        reduction = 1 - right["counters"]["application_input_tokens"] / left["counters"]["application_input_tokens"]
    result = {"runs": rows, "application_input_reduction": reduction,
              "counts_are_estimates": True, "quality_review": "pending",
              "notes": "Fixture usage is simulated. Live usage, if present, is provider reported. Quality must be reviewed separately."}
    name = "comparison-" + fingerprint(run_ids)[:12] + ".json"
    write_json(h.safe_path("evidence/" + name), result)
    return result


def demonstration(root):
    from run import research, load_policy, write_json
    from harness import Harness
    root = Path(root)
    policy = load_policy(root)
    as_of = datetime(2026, 9, 18, 16, tzinfo=timezone.utc)
    collection = fixture_collection()
    prefix = "fixture-" + uuid.uuid4().hex[:8]
    ids = {}
    # Freeze quality checks before comparing evidence compression.
    h = Harness(root, policy, prefix)
    write_json(h.safe_path("evidence/" + prefix + "-expected-facts.json"), {
        "mode": "synthetic_fixture", "snapshot_hash": fingerprint(collection),
        "required_facts": ["research assistant", "cited reading list", "source identifiers", "activity report"],
        "required_caveats": ["limited preview", "cannot independently verify publisher claims", "human evidence review"],
        "human_review": "pending"})
    for label, settings in [
        ("full", {"evidence_mode": "full", "use_cache": False}),
        ("compact", {"evidence_mode": "compact", "use_cache": False}),
        ("warm", {"evidence_mode": "compact", "use_cache": True}),
        ("baseline", {"source_failure_policy": "stop"}),
        ("failure", {"fail_source": "anthropic_news", "source_failure_policy": "stop"}),
        ("corrected", {"fail_source": "anthropic_news", "source_failure_policy": "partial"})]:
        rid = prefix + "-" + label
        report = research(root, policy, as_of, FixtureModel(root), run_id=rid,
                          collection=collection, mode="synthetic_fixture", **settings)
        ids[label] = report["run_id"]
    comparison = compare_runs(root, [ids[k] for k in ("full", "compact", "warm")])
    compare_runs(root, [ids[k] for k in ("baseline", "failure", "corrected")])
    return {"mode": "synthetic_fixture", "run_ids": ids,
            "application_input_reduction": comparison["application_input_reduction"],
            "human_review": "pending", "real_model_calls": 0}
