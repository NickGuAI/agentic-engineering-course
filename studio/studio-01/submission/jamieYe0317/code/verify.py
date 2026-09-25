"""Provenance and shape checks, not a substitute for reviewing factual support."""
import re
from evidence import fingerprint

VERSION = "verify-v1"
ITEM_FIELDS = {"article_id", "summary", "relevance", "evidence_ids", "insufficient_evidence"}


def words(text):
    return len(re.findall(r"\b[\w]+(?:['’-][\w]+)*\b", text))


def check_item(item, packet, policy):
    failures = []
    if not isinstance(item, dict) or set(item) != ITEM_FIELDS:
        return ["invalid_item_schema"]
    if item["article_id"] != packet["article_id"]:
        failures.append("unknown_article_id")
    if not isinstance(item["insufficient_evidence"], bool):
        failures.append("invalid_evidence_flag")
    elif item["insufficient_evidence"]:
        failures.append("insufficient_evidence")
    for field in ("summary", "relevance"):
        if not isinstance(item[field], str) or not item[field].strip():
            failures.append("missing_" + field)
        elif re.search(r"https?://|\]\(|<[^>]+>", item[field]):
            failures.append("untrusted_markup_or_link")
        elif re.search(r"\b(?:today|yesterday|this week)\b", item[field], re.I):
            failures.append("relative_date_in_cached_text")
    if isinstance(item["summary"], str):
        n = words(item["summary"])
        if not policy.get("summary_min_words", 40) <= n <= policy.get("summary_max_words", 70):
            failures.append("summary_word_limit")
    if isinstance(item["relevance"], str) and words(item["relevance"]) > policy.get("relevance_max_words", 35):
        failures.append("relevance_word_limit")
    ids = item["evidence_ids"]
    allowed = {p["id"] for p in packet["evidence"]}
    if not isinstance(ids, list) or not ids or any(not isinstance(x, str) or x not in allowed for x in ids):
        failures.append("unknown_or_missing_evidence_ids")
    elif len(ids) != len(set(ids)):
        failures.append("duplicate_evidence_ids")
    return failures


def check_items(items, packets, policy):
    lookup = {p["article_id"]: p for p in packets}
    valid, failures, seen = [], {}, set()
    if not isinstance(items, list):
        return [], {"batch": ["invalid_batch_schema"]}
    for index, item in enumerate(items):
        key = item.get("article_id") if isinstance(item, dict) else None
        if not isinstance(key, str) or key not in lookup:
            failures["item_%d" % index] = ["unknown_article_id"]
            continue
        if key in seen:
            failures[key] = ["duplicate_article_id"]
            valid = [v for v in valid if v["article_id"] != key]
            continue
        seen.add(key)
        errors = check_item(item, lookup[key], policy)
        if errors:
            failures[key] = errors
        else:
            valid.append(item)
    for key in lookup:
        if key not in seen:
            failures[key] = ["missing_article_summary"]
    return valid, failures


def verify_digest(digest, manifest, policy):
    from sources import approved_url, eligible
    from datetime import datetime
    failures = []
    required_digest = {"status", "items", "as_of", "window", "coverage_summary"}
    if not isinstance(digest, dict) or not required_digest.issubset(digest):
        return {"passed": False, "failures": ["invalid_digest_schema"], "version": VERSION}
    if not isinstance(manifest, dict) or not isinstance(manifest.get("selected_articles"), list):
        return {"passed": False, "failures": ["invalid_manifest_schema"], "version": VERSION}
    if any(not isinstance(digest.get(k), str) for k in ("status", "as_of", "window", "coverage_summary")):
        return {"passed": False, "failures": ["invalid_digest_field_type"], "version": VERSION}
    if digest.get("status") not in ("complete", "partial", "empty"):
        failures.append("nonpublishable_status")
    items = digest.get("items", [])
    if not isinstance(items, list) or len(items) > policy["max_items"]:
        return {"passed": False, "failures": ["invalid_item_count"], "version": VERSION}
    if (digest["status"] == "empty") != (len(items) == 0):
        failures.append("status_item_count_mismatch")
    if digest["status"] in ("empty", "complete") and manifest.get("coverage_limited"):
        failures.append("incomplete_coverage")
    source_records = manifest.get("sources", [])
    if not isinstance(source_records, list) or any(not isinstance(s, dict) for s in source_records):
        return {"passed": False, "failures": ["invalid_sources_schema"], "version": VERSION}
    if digest["status"] in ("empty", "complete") and (
            len(source_records) != 3 or any(x.get("status") != "ok" for x in source_records)):
        failures.append("sources_not_successfully_checked")
    ids, urls = set(), set()
    required_article = {"article_id", "url", "title", "published_at", "packet"}
    if any(not isinstance(a, dict) or not required_article.issubset(a)
           for a in manifest["selected_articles"]):
        return {"passed": False, "failures": ["invalid_selected_article_schema"], "version": VERSION}
    for article in manifest["selected_articles"]:
        packet = article["packet"]
        if (any(not isinstance(article[k], str) for k in ("article_id", "url", "title", "published_at"))
                or not isinstance(packet, dict) or packet.get("article_id") != article["article_id"]
                or not isinstance(packet.get("evidence"), list)
                or any(not isinstance(p, dict) or not isinstance(p.get("id"), str) for p in packet["evidence"])):
            return {"passed": False, "failures": ["invalid_selected_article_fields"], "version": VERSION}
    selected = {a["article_id"]: a for a in manifest["selected_articles"]}
    if len(selected) != len(manifest["selected_articles"]):
        failures.append("duplicate_manifest_article")
    try:
        as_of = datetime.fromisoformat(manifest["as_of"].replace("Z", "+00:00"))
        if as_of.tzinfo is None:
            raise ValueError("timezone required")
    except (KeyError, ValueError, AttributeError):
        return {"passed": False, "failures": ["invalid_manifest_clock"], "version": VERSION}
    for item in items:
        if not isinstance(item, dict) or not (ITEM_FIELDS | {"url", "title", "published_at"}).issubset(item):
            failures.append("invalid_digest_item_schema")
            continue
        if any(not isinstance(item[k], str) for k in ("article_id", "url", "title", "published_at")):
            failures.append("invalid_digest_item_field_type")
            continue
        article_id = item.get("article_id")
        if article_id not in selected or article_id in ids:
            failures.append("unknown_or_duplicate_article")
            continue
        ids.add(article_id)
        article = selected[article_id]
        if item["url"] != article["url"] or item["url"] in urls:
            failures.append("citation_mismatch")
        urls.add(item["url"])
        try:
            if approved_url(item["url"], article=True) is False:
                failures.append("unapproved_url")
        except ValueError:
            failures.append("unapproved_url")
        if item["title"] != article["title"] or item["published_at"] != article["published_at"]:
            failures.append("publication_metadata_mismatch")
        if not eligible(article, as_of, policy["days"], policy["timezone"]):
            failures.append("ineligible_publication_date")
        summary = {k: item[k] for k in ITEM_FIELDS if k in item}
        failures.extend(check_item(summary, article["packet"], policy))
    if ids != set(selected):
        failures.append("manifest_selection_mismatch")
    return {"passed": not failures, "failures": sorted(set(failures)), "version": VERSION,
            "checks": ["shape", "dates", "source_allowlist", "evidence_ids", "counts", "coverage", "metadata"],
            "human_review": "pending", "factual_support": "requires_source_comparison",
            "digest_hash": fingerprint(digest), "manifest_hash": fingerprint(manifest)}


def escape(text):
    text = str(text).replace("\n", " ")
    for char in ("\\", "[", "]", "*", "_", "<", ">", "#", "`"):
        text = text.replace(char, "\\" + char)
    return text


def render(digest):
    lines = ["# AI research digest", "", "Mode: " + digest.get("mode", "unknown"),
             "", "As of: " + digest["as_of"],
             "Window: " + digest["window"], "Status: **" + digest["status"] + "**", "",
             "Source coverage: " + escape(digest["coverage_summary"]), "",
             "Automated provenance checks passed. Human factual review: pending.", ""]
    if digest.get("mode") == "synthetic_fixture":
        lines[2:2] = ["**Synthetic fixtures and scripted responses; not live AI research.**", ""]
    if not digest["items"]:
        lines += ["No eligible updates found in the checked sources.", ""]
    for n, item in enumerate(digest["items"], 1):
        lines += ["## %d. %s" % (n, escape(item["title"])), "",
                  "Published: %s · [Publisher source](%s)" % (escape(item["published_at"]), item["url"]),
                  "", escape(item["summary"]), "",
                  "**Why it matters (interpretation):** " + escape(item["relevance"]), "",
                  "Evidence: " + ", ".join(item["evidence_ids"]), ""]
    for warning in digest.get("warnings", []):
        lines += ["- " + escape(warning)]
    return "\n".join(lines).rstrip() + "\n"
