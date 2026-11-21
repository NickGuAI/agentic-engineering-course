#!/usr/bin/env python3
"""Bounded research digest. Every command requires the individual --team name."""
import argparse
import copy
from datetime import datetime, timedelta, timezone
import hashlib
import json
from pathlib import Path
import re
import subprocess
import sys
import uuid
from zoneinfo import ZoneInfo

from evidence import (SummaryCache, cache_key, canonical, count_tokens, fingerprint,
                      measurement, packet_for)
from harness import Action, Harness, HarnessError
from verify import check_items, render, verify_digest

ROOT = Path(__file__).resolve().parent.parent
TEAM = "jamieYe0317"
SOURCE_IDS = ("openai_news", "anthropic_news", "anthropic_engineering")


def write_json(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    if path.is_symlink() or temporary.is_symlink():
        raise ValueError("unsafe_artifact_path")
    temporary.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    temporary.replace(path)


def load_policy(root):
    policy = json.loads((root / "policy.json").read_text(encoding="utf-8"))
    if policy.get("team") != TEAM:
        raise ValueError("unsupported_team")
    numeric = ("days", "max_items", "max_candidates", "max_article_fetches", "max_http_attempts",
               "max_model_calls", "max_run_seconds", "initial_input_tokens", "repair_input_tokens",
               "max_application_input_tokens", "article_evidence_tokens")
    if any(type(policy.get(k)) is not int or policy[k] <= 0 for k in numeric):
        raise ValueError("invalid_policy_limit")
    if policy["max_items"] > 5 or policy["max_model_calls"] > 2:
        raise ValueError("policy_exceeds_contract")
    ZoneInfo(policy["timezone"])
    return policy


def parse_as_of(value):
    if not value:
        return datetime.now(timezone.utc)
    result = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if result.tzinfo is None:
        raise ValueError("as_of_requires_timezone")
    return result.astimezone(timezone.utc)


def implementation(root):
    hashes = {}
    for directory in ("code", "prompts"):
        for path in sorted((root / directory).glob("*")):
            if path.is_file() and not path.is_symlink():
                hashes[str(path.relative_to(root))] = hashlib.sha256(path.read_bytes()).hexdigest()
    commit = "unknown"
    try:
        result = subprocess.run(["git", "rev-parse", "HEAD"], cwd=str(root),
                                capture_output=True, text=True, timeout=5)
        if result.returncode == 0:
            commit = result.stdout.strip()
    except (OSError, subprocess.TimeoutExpired):
        pass
    return {"git_commit": commit, "files": hashes, "hash": fingerprint(hashes)}


def safe_id(value):
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_-]{0,100}", value):
        raise ValueError("invalid_run_id")
    return value


def sanitize_collection(collection):
    # No page bodies, excerpts, low-level provider errors or arbitrary keys.
    return [{k: row[k] for k in ("source_id", "url", "status", "error_code", "candidate_count")
             if k in row} for row in collection.get("sources", [])]


def research(root, policy, as_of, model, run_id=None, collection=None,
             mode="live", evidence_mode="compact", use_cache=True,
             snapshot_id=None, fail_source=None, source_failure_policy="partial"):
    from sources import collect_sources, eligible
    root = Path(root).resolve()
    run_id = safe_id(run_id or (datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ") + "-" + uuid.uuid4().hex[:8]))
    h = Harness(root, policy, run_id)
    output = h.safe_path("outputs/" + run_id)
    if output.exists():
        raise ValueError("run_id_already_exists")
    output.mkdir(parents=True)
    work = h.safe_path("work")
    work.mkdir(parents=True, exist_ok=True)
    run_work = h.safe_path("work/runs/" + run_id)
    run_work.mkdir(parents=True, exist_ok=True)
    manifest = {"run_id": run_id, "mode": mode, "team": TEAM,
                "as_of": as_of.isoformat(), "policy": copy.deepcopy(policy),
                "policy_hash": fingerprint(policy), "model": copy.deepcopy(model.identity),
                "implementation": implementation(root), "sources": [],
                "selected_articles": [], "coverage_limited": False,
                "snapshot_id": snapshot_id, "fault_injection": fail_source,
                "source_failure_policy": source_failure_policy, "evidence_mode": evidence_mode,
                "human_acceptance": "pending"}
    warnings, failures, packets, articles, items = [], {}, [], [], []
    cache_hits = 0
    status = "blocked"
    digest = None
    verification = {"passed": False, "failures": ["run_not_finished"]}
    try:
        h.transition("collecting")
        if collection is None:
            collection = collect_sources(policy, as_of, h.before_http, run_work)
        else:
            collection = copy.deepcopy(collection)
        # Snapshots contain full normalized text and stay in ignored local work.
        snapshot = {"as_of": as_of.isoformat(), "collection": collection,
                    "policy": copy.deepcopy(policy), "model": copy.deepcopy(model.identity),
                    "source_implementation": manifest["implementation"]}
        snapshot_path = h.safe_path("work/snapshots/" + run_id + ".json")
        write_json(snapshot_path, snapshot)
        manifest["input_snapshot_hash"] = fingerprint({"as_of": snapshot["as_of"], "collection": collection})
        manifest["local_snapshot_id"] = run_id
        if fail_source:
            if mode == "live":
                raise ValueError("fault_injection_requires_replay")
            for source in collection["sources"]:
                if source["source_id"] == fail_source:
                    source.update(status="error", error_code="injected_http_failure")
            collection["articles"] = [a for a in collection["articles"] if a["source_id"] != fail_source]
            collection["coverage_limited"] = True
        manifest["sources"] = sanitize_collection(collection)
        manifest["source_exclusions"] = collection.get("exclusions", [])
        manifest["coverage_reasons"] = collection.get("coverage_reasons", [])
        manifest["coverage_limited"] = bool(collection.get("coverage_limited"))
        bad_sources = [s for s in manifest["sources"] if s.get("status") != "ok"]
        manifest["coverage_limited"] |= bool(bad_sources)
        for source in bad_sources:
            warnings.append("Source unavailable: %s (%s)." %
                            (source["source_id"], source.get("error_code", "source_error")))
        for reason in manifest["coverage_reasons"]:
            warnings.append("Collection coverage limit: %s." % reason)
        h.event("source_collection", "partial" if manifest["coverage_limited"] else "ok",
                {"sources": manifest["sources"], "article_count": len(collection.get("articles", []))})
        if bad_sources and source_failure_policy == "stop":
            raise ValueError("source_failure_policy_stop")
        candidates = sorted(collection.get("articles", []),
                            key=lambda a: (a.get("published_at", ""), a.get("url", "")), reverse=True)
        eligible_count = sum(eligible(a, as_of, policy["days"], policy["timezone"]) for a in candidates)
        # Reallocate unused article slots without increasing the shared prompt
        # budget: a sparse week should not discard a well-supported long article.
        packet_limit = max(policy["article_evidence_tokens"],
                           policy.get("total_evidence_tokens", 6000) // max(1, min(policy["max_items"], eligible_count)))
        manifest["article_evidence_allowance"] = packet_limit
        seen_url, seen_content = set(), set()
        excluded = []
        for article in candidates:
            if not eligible(article, as_of, policy["days"], policy["timezone"]):
                excluded.append({"article_id": article["article_id"], "reason": "outside_window_or_invalid_date"})
                continue
            if article["url"] in seen_url or article["content_hash"] in seen_content:
                continue
            seen_url.add(article["url"])
            seen_content.add(article["content_hash"])
            if len(articles) >= policy["max_items"]:
                break
            try:
                packet = packet_for(article, packet_limit, evidence_mode)
            except ValueError as exc:
                excluded.append({"article_id": article["article_id"], "reason": str(exc)})
                manifest["coverage_limited"] = True
                warnings.append("Article omitted because essential evidence did not fit its allowance: %s." % article["title"])
                continue
            articles.append(article)
            packets.append(packet)
        manifest["exclusions"] = excluded
        h.execute(Action("select-1", "select", {"article_ids": [a["article_id"] for a in articles]}),
                  lambda: {"selected": len(articles), "excluded": len(excluded)})
        h.transition("evidence_ready")
        if not articles:
            if manifest["coverage_limited"] or len(manifest["sources"]) != 3:
                raise ValueError("no_trustworthy_items_with_incomplete_coverage")
            status = "empty"
        else:
            cache = SummaryCache(h.safe_path("work/summary-cache"))
            keys = {}
            pending = []
            prompt_hash = fingerprint(model.build_input({"articles": []}))
            schema_hash = fingerprint(model.schema_text)
            for article, packet in zip(articles, packets):
                key = cache_key(article, packet, model.identity, prompt_hash, schema_hash)
                keys[article["article_id"]] = key
                cached = cache.get(key) if use_cache else None
                valid, _ = check_items([cached], [packet], policy) if cached else ([], {})
                if valid:
                    items.extend(valid)
                    cache_hits += 1
                else:
                    pending.append(packet)
            h.event("summary_cache", "ok", {"hits": cache_hits, "misses": len(pending)})
            if pending:
                h.transition("summarizing")
                payload = {"articles": pending}
                response = None
                try:
                    response = invoke_model(h, model, payload, policy, False)
                    valid, failures = check_items(response.get("items"), pending, policy)
                    items.extend(valid)
                except (ValueError, RuntimeError, OSError) as exc:
                    reason = safe_error(exc)
                    warnings.append("Model batch unavailable: %s." % reason)
                    failures = {p["article_id"]: [reason] for p in pending}
                if failures and response is not None:
                    repair_packets = [p for p in pending if p["article_id"] in failures]
                    h.event("summary_validation", "failed", {"failures": failures})
                    if repair_packets:
                        previous = [i for i in response.get("items", []) if isinstance(i, dict)
                                    and i.get("article_id") in {p["article_id"] for p in repair_packets}]
                        try:
                            repair_payload = {"articles": repair_packets, "errors": failures,
                                              "previous_items": previous}
                            repair = invoke_model(h, model, repair_payload, policy, True)
                            repaired, repair_failures = check_items(repair.get("items"), repair_packets, policy)
                            items.extend(repaired)
                            failures = repair_failures
                        except (ValueError, RuntimeError, OSError) as exc:
                            warnings.append("Repair unavailable: %s." % safe_error(exc))
                # Validate the whole retained set again; no failed item can enter cache.
                valid, remaining = check_items(items, packets, policy)
                items = valid
                failures.update(remaining)
                for item in items:
                    cache.put(keys[item["article_id"]], item)
            if failures:
                manifest["coverage_limited"] = True
                warnings.append("Some selected articles could not be summarized within validation and repair limits.")
            if h.counters.get("observed_total_tokens", 0) is not None and h.counters.get("observed_total_tokens", 0) >= policy["observed_total_token_alert"]:
                manifest["coverage_limited"] = True
                warnings.append("Observed provider-token alert exceeded; no further model calls allowed.")
            if not items:
                raise ValueError("no_valid_summaries")
            status = "partial" if manifest["coverage_limited"] else "complete"
        accepted = {item["article_id"]: item for item in items}
        for article, packet in zip(articles, packets):
            if article["article_id"] in accepted:
                record = {k: v for k, v in article.items() if k != "paragraphs"}
                # Share only paragraph IDs and hashes, not downloaded excerpts.
                record["packet"] = {"article_id": packet["article_id"], "evidence":
                                    [{"id": p["id"], "text_hash": fingerprint(p["text"])} for p in packet["evidence"]]}
                record["packet_hash"] = fingerprint(packet)
                manifest["selected_articles"].append(record)
        manifest["summary_failures"] = failures
        manifest["cache_hits"] = cache_hits
        date = as_of.astimezone(ZoneInfo(policy["timezone"])).date()
        digest = {"run_id": run_id, "mode": mode, "as_of": as_of.isoformat(),
                  "window": "%s through %s (%s)" % ((date - timedelta(days=policy["days"] - 1)).isoformat(), date.isoformat(), policy["timezone"]),
                  "status": status, "coverage_summary": "%d/%d sources checked successfully; at most %d selected updates." %
                  (sum(s.get("status") == "ok" for s in manifest["sources"]), len(SOURCE_IDS), policy["max_items"]),
                  "warnings": warnings, "items": []}
        for record in manifest["selected_articles"]:
            item = accepted[record["article_id"]]
            digest["items"].append(dict(item, title=record["title"], url=record["url"], published_at=record["published_at"]))
        h.transition("verifying")
        verification = verify_digest(digest, manifest, policy)
        markdown = render(digest)
        material = canonical(digest).encode() + b"\n" + markdown.encode()
        h.execute(Action("verify-1", "verify", {"digest_hash": fingerprint(digest), "manifest_hash": fingerprint(manifest)}),
                  lambda: h.mark_verified(material, manifest, verification["passed"]))
        if not verification["passed"]:
            raise ValueError("final_verification_failed")
        # Authorize the exact candidate before making final artifact names visible.
        h.execute(Action("finish-1", "finish", {}), lambda: h.finish(material, manifest))
        write_json(h.safe_path("outputs/%s/digest.json" % run_id), digest)
        mdpath = h.safe_path("outputs/%s/digest.md" % run_id)
        temporary = h.safe_path("outputs/%s/digest.md.tmp" % run_id)
        temporary.write_text(markdown, encoding="utf-8")
        temporary.replace(mdpath)
        verification["markdown_sha256"] = hashlib.sha256(markdown.encode()).hexdigest()
    except (ValueError, RuntimeError, OSError, KeyError, TypeError) as exc:
        status = "blocked"
        reason = safe_error(exc)
        warnings.append(reason)
        verification = {"passed": False, "failures": [reason], "human_review": "pending"}
        # No unchecked candidate is saved as a digest.
        for name in ("digest.json", "digest.md"):
            path = h.safe_path("outputs/%s/%s" % (run_id, name))
            if path.exists():
                path.unlink()
        h.event("run", "blocked", {"reason": reason})
    usage = {"model": model.identity, "usage_kind": "simulated_fixture" if mode == "synthetic_fixture" else "provider_reported_or_unknown",
             "application_count_method": "utf8_bytes_div_3_estimate",
             "application_counts_exact": False, "provider_usage": h.usages,
             "counters": h.counters, "cache_hits": cache_hits,
             "hard_total_token_cap": False}
    report = {"run_id": run_id, "mode": mode, "status": status, "warnings": warnings,
              "output": str(output), "human_acceptance": "pending"}
    for name, value in (("manifest.json", manifest), ("verification.json", verification),
                        ("usage.json", usage), ("status.json", report)):
        write_json(h.safe_path("outputs/%s/%s" % (run_id, name)), value)
    h.safe_path("outputs/%s/trace.jsonl" % run_id).write_text(
        "".join(canonical(event) + "\n" for event in h.events), encoding="utf-8")
    return report


def safe_error(error):
    code = getattr(error, "code", None)
    if isinstance(code, str) and re.fullmatch(r"[a-zA-Z0-9_. -]{1,120}", code):
        return code
    text = str(error)
    if isinstance(error, HarnessError) and re.fullmatch(r"[a-zA-Z0-9_ .:-]{1,150}", text):
        return text.lower().replace(" ", "_")
    if re.fullmatch(r"[a-z][a-z0-9_]{0,100}", text):
        return text
    return type(error).__name__


def invoke_model(h, model, payload, policy, repair):
    text = model.build_input(payload)
    # Schema is delivered out of band to Codex but still application input.
    full = text + "\n" + model.schema_text
    budget = measurement(full)
    h.reserve_model(budget["tokens"], budget["bytes"], repair=repair)
    h.event("model_input", "reserved", dict(budget, repair=repair,
                                           payload_hash=fingerprint(payload)))
    def call():
        try:
            result = model.generate(payload, timeout=min(policy["model_timeout_seconds"], h.remaining_seconds()))
            h.record_usage(result.get("usage") if result.get("usage_known") else None)
            return result
        except Exception as exc:
            h.record_usage(getattr(exc, "usage", None))
            raise
    return h.execute(Action("model-%d" % h.counters["model_calls"], "summarize",
                            {"article_ids": [p["article_id"] for p in payload["articles"]], "repair": repair}), call)


def verify_saved(root, run_id):
    run_id = safe_id(run_id)
    h = Harness(root, load_policy(root), "verify")
    directory = h.safe_path("outputs/" + run_id)
    digest = json.loads(h.safe_path("outputs/%s/digest.json" % run_id).read_text())
    manifest = json.loads(h.safe_path("outputs/%s/manifest.json" % run_id).read_text())
    previous = json.loads(h.safe_path("outputs/%s/verification.json" % run_id).read_text())
    report = verify_digest(digest, manifest, manifest["policy"])
    if not report["passed"]:
        return report
    markdown = h.safe_path("outputs/%s/digest.md" % run_id).read_text()
    if render(digest) != markdown or hashlib.sha256(markdown.encode()).hexdigest() != previous.get("markdown_sha256"):
        report["failures"].append("markdown_changed_since_check")
    if fingerprint(digest) != previous.get("digest_hash") or fingerprint(manifest) != previous.get("manifest_hash"):
        report["failures"].append("artifact_or_manifest_changed_since_check")
    report["passed"] = not report["failures"]
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=["run", "replay", "verify", "compare", "demo"])
    parser.add_argument("--team", required=True, choices=[TEAM])
    parser.add_argument("--as-of", help="ISO timestamp with timezone (replay keeps the saved clock)")
    parser.add_argument("--days", type=int)
    parser.add_argument("--max-items", type=int)
    parser.add_argument("--run-id")
    parser.add_argument("--snapshot", help="Local snapshot ID for replay")
    parser.add_argument("--fail-source", choices=SOURCE_IDS)
    parser.add_argument("--source-failure-policy", choices=["stop", "partial"])
    parser.add_argument("--model")
    parser.add_argument("--reasoning")
    parser.add_argument("--evidence", choices=["compact", "full"], default="compact")
    parser.add_argument("--no-cache", action="store_true")
    parser.add_argument("--runs", nargs="+", help="Existing run IDs for comparison")
    args = parser.parse_args()
    try:
        policy = load_policy(ROOT)
        if args.days is not None:
            if not 1 <= args.days <= 7:
                raise ValueError("days_must_be_between_1_and_7")
            policy["days"] = args.days
        if args.max_items is not None:
            if not 1 <= args.max_items <= 5:
                raise ValueError("max_items_must_be_between_1_and_5")
            policy["max_items"] = args.max_items
        if args.command == "verify":
            result = verify_saved(ROOT, args.run_id or "")
            print(json.dumps(result, indent=2))
            return 0 if result["passed"] else 3
        if args.command == "compare":
            from experiments import compare_runs
            print(json.dumps(compare_runs(ROOT, args.runs or []), indent=2))
            return 0
        if args.command == "demo":
            from experiments import demonstration
            print(json.dumps(demonstration(ROOT), indent=2))
            return 0
        if args.command == "run" and (args.fail_source or args.snapshot):
            raise ValueError("snapshot_or_injection_requires_replay")
        collection = None
        snapshot = None
        as_of = parse_as_of(args.as_of)
        if args.command == "replay":
            sid = safe_id(args.snapshot or "")
            h = Harness(ROOT, policy, "snapshot-read")
            snapshot = json.loads(h.safe_path("work/snapshots/" + sid + ".json").read_text())
            as_of = parse_as_of(snapshot["as_of"])
            if args.as_of and parse_as_of(args.as_of) != as_of:
                raise ValueError("replay_clock_must_match_snapshot")
            collection = snapshot["collection"]
        from model import CodexModel
        selected_model = args.model or (snapshot or {}).get("model", {}).get("model")
        selected_reasoning = args.reasoning or (snapshot or {}).get("model", {}).get("reasoning") or policy["summary_reasoning"]
        model = CodexModel(ROOT, model=selected_model, reasoning=selected_reasoning)
        report = research(ROOT, policy, as_of, model, run_id=args.run_id,
                          collection=collection, mode="live" if args.command == "run" else "snapshot_replay",
                          evidence_mode=args.evidence, use_cache=not args.no_cache,
                          snapshot_id=args.snapshot, fail_source=args.fail_source,
                          source_failure_policy=args.source_failure_policy or policy["source_failure_policy"])
        print(json.dumps(report, indent=2))
        return {"complete": 0, "empty": 0, "partial": 2, "blocked": 3}[report["status"]]
    except (ValueError, OSError, RuntimeError, KeyError) as exc:
        print(json.dumps({"status": "blocked", "reason": safe_error(exc)}))
        return 3


if __name__ == "__main__":
    sys.exit(main())
