#!/usr/bin/env python3
"""Create an observable, no-API research digest from official AI sources."""

from __future__ import annotations

import argparse
import html
import json
import re
import sys
import uuid
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from html.parser import HTMLParser
from pathlib import Path
from typing import Any, Iterable
from urllib.error import HTTPError, URLError
from urllib.parse import urljoin, urlsplit, urlunsplit
from urllib.request import Request, urlopen


DEFAULT_SOURCES = (
    {
        "id": "anthropic-news",
        "name": "Anthropic News",
        "url": "https://www.anthropic.com/news",
        "host": "anthropic.com",
        "path_prefixes": ("/news/",),
    },
    {
        "id": "anthropic-engineering",
        "name": "Anthropic Engineering",
        "url": "https://www.anthropic.com/engineering",
        "host": "anthropic.com",
        "path_prefixes": ("/engineering/",),
    },
    {
        "id": "openai-news",
        "name": "OpenAI News",
        "url": "https://openai.com/news/",
        "host": "openai.com",
        # Current News cards point to /index/<article-slug>. Restricting discovery
        # to that route avoids category/filter pages under /news/.
        "path_prefixes": ("/index/",),
    },
)

RELEVANCE_TERMS = {
    "agent": 7,
    "agentic": 8,
    "coding": 6,
    "code": 4,
    "tool use": 6,
    "computer use": 7,
    "model": 3,
    "reasoning": 5,
    "developer": 4,
    "api": 3,
    "eval": 5,
    "safety": 4,
    "alignment": 4,
    "infrastructure": 3,
    "system card": 4,
    "benchmark": 4,
    "reliability": 5,
    "context": 3,
    "memory": 4,
}

USER_AGENT = (
    "Mozilla/5.0 (compatible; Studio01ResearchUpdate/1.0; "
    "+local-course-assignment)"
)

GENERIC_DESCRIPTION_FRAGMENTS = (
    "anthropic is an ai safety and research company",
    "stay up to speed on the rapid advancement of ai technology",
    "we're an ai research and deployment company",
)

MONTH_PATTERN = (
    r"(?:Jan(?:uary)?|Feb(?:ruary)?|Mar(?:ch)?|Apr(?:il)?|May|Jun(?:e)?|"
    r"Jul(?:y)?|Aug(?:ust)?|Sep(?:tember)?|Oct(?:ober)?|Nov(?:ember)?|Dec(?:ember)?)"
)


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def iso_now() -> str:
    return utc_now().isoformat(timespec="seconds").replace("+00:00", "Z")


def clean_text(value: str) -> str:
    value = html.unescape(value or "")
    return re.sub(r"\s+", " ", value).strip()


def shorten(value: str, limit: int = 420) -> str:
    value = clean_text(value)
    if len(value) <= limit:
        return value
    shortened = value[: limit + 1].rsplit(" ", 1)[0].rstrip(" ,;:")
    return shortened + "…"


class PageParser(HTMLParser):
    """Small HTML metadata/text/link extractor with no third-party dependency."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.meta: dict[str, str] = {}
        self.links: list[dict[str, str]] = []
        self.paragraphs: list[str] = []
        self.times: list[dict[str, str]] = []
        self.json_ld: list[str] = []
        self.title_parts: list[str] = []
        self.text_parts: list[str] = []
        self._anchor: dict[str, Any] | None = None
        self._paragraph_parts: list[str] | None = None
        self._time: dict[str, Any] | None = None
        self._script_parts: list[str] | None = None
        self._in_title = False
        self._hidden_depth = 0

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        values = {key.lower(): (value or "") for key, value in attrs}
        tag = tag.lower()
        if tag in {"script", "style", "noscript"}:
            self._hidden_depth += 1
        if tag == "meta":
            key = (values.get("property") or values.get("name") or "").lower()
            content = clean_text(values.get("content", ""))
            if key and content and key not in self.meta:
                self.meta[key] = content
        elif tag == "a" and values.get("href"):
            self._anchor = {"href": values["href"], "parts": []}
        elif tag == "p":
            self._paragraph_parts = []
        elif tag == "time":
            self._time = {"datetime": values.get("datetime", ""), "parts": []}
        elif tag == "script" and "ld+json" in values.get("type", "").lower():
            self._script_parts = []
        elif tag == "title":
            self._in_title = True

    def handle_endtag(self, tag: str) -> None:
        tag = tag.lower()
        if tag == "a" and self._anchor is not None:
            self.links.append(
                {
                    "href": self._anchor["href"],
                    "text": clean_text(" ".join(self._anchor["parts"])),
                }
            )
            self._anchor = None
        elif tag == "p" and self._paragraph_parts is not None:
            text = clean_text(" ".join(self._paragraph_parts))
            if text:
                self.paragraphs.append(text)
            self._paragraph_parts = None
        elif tag == "time" and self._time is not None:
            self.times.append(
                {
                    "datetime": clean_text(self._time["datetime"]),
                    "text": clean_text(" ".join(self._time["parts"])),
                }
            )
            self._time = None
        elif tag == "script" and self._script_parts is not None:
            raw = "".join(self._script_parts).strip()
            if raw:
                self.json_ld.append(raw)
            self._script_parts = None
        elif tag == "title":
            self._in_title = False
        if tag in {"script", "style", "noscript"} and self._hidden_depth:
            self._hidden_depth -= 1

    def handle_data(self, data: str) -> None:
        if self._anchor is not None:
            self._anchor["parts"].append(data)
        if self._paragraph_parts is not None:
            self._paragraph_parts.append(data)
        if self._time is not None:
            self._time["parts"].append(data)
        if self._script_parts is not None:
            self._script_parts.append(data)
        if self._in_title:
            self.title_parts.append(data)
        if not self._hidden_depth:
            self.text_parts.append(data)


@dataclass
class FetchResult:
    ok: bool
    requested_url: str
    final_url: str | None
    status_code: int | None
    text: str
    error: str | None


def fetch_url(url: str, timeout: float) -> FetchResult:
    request = Request(
        url,
        headers={
            "User-Agent": USER_AGENT,
            "Accept": "text/html,application/xhtml+xml",
            "Accept-Language": "en-US,en;q=0.8",
        },
    )
    try:
        with urlopen(request, timeout=timeout) as response:
            data = response.read()
            charset = response.headers.get_content_charset() or "utf-8"
            return FetchResult(
                ok=True,
                requested_url=url,
                final_url=response.geturl(),
                status_code=getattr(response, "status", 200),
                text=data.decode(charset, errors="replace"),
                error=None,
            )
    except HTTPError as exc:
        return FetchResult(False, url, exc.geturl(), exc.code, "", f"HTTP {exc.code}: {exc.reason}")
    except (URLError, TimeoutError, OSError) as exc:
        return FetchResult(False, url, None, None, "", f"{type(exc).__name__}: {exc}")


def parse_page(markup: str) -> PageParser:
    parser = PageParser()
    parser.feed(markup)
    parser.close()
    return parser


def normalize_url(base_url: str, href: str) -> str | None:
    href = clean_text(href)
    if not href or href.startswith(("#", "mailto:", "javascript:", "tel:")):
        return None
    absolute = urljoin(base_url, href)
    parts = urlsplit(absolute)
    if parts.scheme not in {"http", "https"}:
        return None
    path = re.sub(r"/{2,}", "/", parts.path)
    return urlunsplit((parts.scheme, parts.netloc.lower(), path, "", ""))


def host_matches(actual_host: str, expected_host: str) -> bool:
    actual = (actual_host or "").lower().split(":", 1)[0]
    expected = expected_host.lower()
    return actual == expected or actual == f"www.{expected}"


def discover_candidates(source: dict[str, Any], markup: str) -> list[dict[str, str]]:
    parser = parse_page(markup)
    seen: set[str] = set()
    candidates: list[dict[str, str]] = []
    landing_path = urlsplit(source["url"]).path.rstrip("/")
    for link in parser.links:
        url = normalize_url(source["url"], link["href"])
        if not url or url in seen:
            continue
        parts = urlsplit(url)
        path = parts.path.rstrip("/")
        if not host_matches(parts.netloc, source["host"]):
            continue
        if path == landing_path or not any(path.startswith(prefix) for prefix in source["path_prefixes"]):
            continue
        seen.add(url)
        candidates.append({"url": url, "link_text": clean_text(link["text"])})
    return candidates


def iter_json_objects(value: Any) -> Iterable[dict[str, Any]]:
    if isinstance(value, dict):
        yield value
        for child in value.values():
            yield from iter_json_objects(child)
    elif isinstance(value, list):
        for child in value:
            yield from iter_json_objects(child)


def json_ld_fields(raw_blocks: list[str]) -> dict[str, str]:
    fields: dict[str, str] = {}
    for raw in raw_blocks:
        try:
            value = json.loads(raw)
        except (json.JSONDecodeError, TypeError):
            continue
        for obj in iter_json_objects(value):
            obj_type = obj.get("@type", "")
            types = obj_type if isinstance(obj_type, list) else [obj_type]
            if not any(str(kind).lower() in {"article", "newsarticle", "blogposting", "techarticle"} for kind in types):
                continue
            for output_key, keys in {
                "title": ("headline", "name"),
                "description": ("description", "abstract"),
                "date": ("datePublished", "dateCreated"),
                "url": ("url",),
            }.items():
                for key in keys:
                    item = obj.get(key)
                    if isinstance(item, str) and clean_text(item):
                        fields.setdefault(output_key, clean_text(item))
                        break
    return fields


def first_value(values: Iterable[str | None]) -> str:
    for value in values:
        cleaned = clean_text(value or "")
        if cleaned:
            return cleaned
    return ""


def is_generic_description(value: str) -> bool:
    lowered = clean_text(value).lower()
    return not lowered or any(fragment in lowered for fragment in GENERIC_DESCRIPTION_FRAGMENTS)


def first_usable_description(values: Iterable[str | None]) -> str:
    for value in values:
        cleaned = clean_text(value or "")
        if cleaned and not is_generic_description(cleaned):
            return cleaned
    return ""


def visible_publication_date(parser: PageParser) -> str:
    visible_text = clean_text(" ".join(parser.text_parts))
    match = re.search(rf"\b(?:Published\s+)?({MONTH_PATTERN}\s+\d{{1,2}},\s+\d{{4}})\b", visible_text)
    return clean_text(match.group(1)) if match else ""


def extract_article(
    source: dict[str, Any], candidate: dict[str, str], markup: str, final_url: str
) -> dict[str, Any]:
    parser = parse_page(markup)
    structured = json_ld_fields(parser.json_ld)
    title = first_value(
        (
            parser.meta.get("og:title"),
            parser.meta.get("twitter:title"),
            structured.get("title"),
            candidate.get("link_text"),
            " ".join(parser.title_parts),
        )
    )
    description = first_usable_description(
        (
            parser.meta.get("og:description"),
            parser.meta.get("twitter:description"),
            parser.meta.get("description"),
            structured.get("description"),
            *(p for p in parser.paragraphs if len(p) >= 60),
        )
    )
    date = first_value(
        (
            parser.meta.get("article:published_time"),
            parser.meta.get("date"),
            structured.get("date"),
            next((item["datetime"] or item["text"] for item in parser.times if item["datetime"] or item["text"]), ""),
            visible_publication_date(parser),
        )
    )
    canonical = first_value(
        (
            parser.meta.get("og:url"),
            structured.get("url"),
            final_url,
            candidate["url"],
        )
    )
    canonical = normalize_url(candidate["url"], canonical) or candidate["url"]
    source_text = description or next((p for p in parser.paragraphs if len(p) >= 40), "")
    summary = shorten(source_text) if source_text else "No article description or usable excerpt was available from the fetched page."
    combined = f"{title} {description}".lower()
    score = sum(weight for term, weight in RELEVANCE_TERMS.items() if term in combined)
    return {
        "title": title or candidate.get("link_text") or "Untitled update",
        "source": source["name"],
        "source_id": source["id"],
        "publication_date": date or None,
        "url": canonical,
        "summary": summary,
        "summary_basis": "source metadata or article excerpt" if source_text else "unavailable",
        "why_it_matters": why_it_matters(combined),
        "relevance_score": score,
    }


def why_it_matters(text: str) -> str:
    if any(term in text for term in ("agent", "tool use", "computer use", "coding", "code")):
        return (
            "It bears directly on agentic engineering: designing systems that can reason, "
            "use tools, write code, or take reliable actions in an environment."
        )
    if any(term in text for term in ("safety", "alignment", "eval", "reliability", "system card")):
        return (
            "It provides evidence or methods for evaluating the safety and reliability of "
            "AI systems, both central concerns when agents can take consequential actions."
        )
    if any(term in text for term in ("infrastructure", "api", "developer", "context", "memory")):
        return (
            "It may affect how agentic applications are built, operated, or integrated, "
            "including their supporting infrastructure and developer interfaces."
        )
    if any(term in text for term in ("model", "reasoning", "benchmark")):
        return (
            "Changes in model capabilities and reasoning behavior can alter which agent "
            "workflows are feasible and how those workflows should be evaluated."
        )
    return (
        "It is a recent official AI update that may shape the technical or operational "
        "context in which agentic systems are designed."
    )


def sort_key(item: dict[str, Any]) -> tuple[int, str]:
    date = item.get("publication_date") or ""
    return (int(item.get("relevance_score", 0)), date)


def select_items(items: list[dict[str, Any]], max_items: int) -> list[dict[str, Any]]:
    """Select relevant items while retaining source coverage when possible."""
    ranked = sorted(items, key=sort_key, reverse=True)
    selected: list[dict[str, Any]] = []
    selected_urls: set[str] = set()
    for source in DEFAULT_SOURCES:
        candidate = next((item for item in ranked if item["source_id"] == source["id"]), None)
        if candidate and candidate["url"] not in selected_urls and len(selected) < max_items:
            selected.append(candidate)
            selected_urls.add(candidate["url"])
    for item in ranked:
        if len(selected) >= max_items:
            break
        if item["url"] not in selected_urls:
            selected.append(item)
            selected_urls.add(item["url"])
    return selected


def render_digest(run_id: str, status: str, selected: list[dict[str, Any]]) -> str:
    lines = [
        "# AI Research Update",
        "",
        f"- Run ID: `{run_id}`",
        f"- Final status: **{status}**",
        f"- Selected items: {len(selected)}",
        "- Method: deterministic extraction from official source metadata or page text; no external LLM",
        "",
    ]
    if not selected:
        lines.extend(
            [
                "No items could be selected from the sources that were successfully processed.",
                "See `evidence.json` and `events.jsonl` in this run directory for details.",
                "",
            ]
        )
    for item in selected:
        lines.extend(
            [
                f"## {item['title']}",
                "",
                f"- **Source:** {item['source']}",
                f"- **Publication date:** {item['publication_date'] or 'Not available from fetched page'}",
                f"- **URL:** {item['url']}",
                f"- **Concise summary:** {item['summary']}",
                f"- **Why it matters:** {item['why_it_matters']}",
                "",
            ]
        )
    return "\n".join(lines)


def verification_checks(
    output_path: Path,
    sources: list[dict[str, Any]],
    selected: list[dict[str, Any]],
    expected_source_ids: set[str],
) -> dict[str, bool]:
    required_item_fields = ("title", "source", "url", "summary", "why_it_matters")
    return {
        "digest_exists": output_path.is_file(),
        "digest_nonempty": output_path.is_file() and output_path.stat().st_size > 0,
        "all_configured_sources_attempted": {item["id"] for item in sources} == expected_source_ids,
        "each_source_has_explicit_status": all(item.get("status") in {"SUCCESS", "FAILED"} for item in sources),
        "selected_items_present": bool(selected),
        "selected_items_have_required_fields": all(
            all(clean_text(str(item.get(field, ""))) for field in required_item_fields)
            for item in selected
        ),
        "selected_counts_consistent": sum(item.get("selected_count", 0) for item in sources) == len(selected),
    }


def make_run_directory(output_root: Path) -> tuple[str, Path]:
    output_root.mkdir(parents=True, exist_ok=True)
    for _ in range(10):
        run_id = utc_now().strftime("%Y%m%dT%H%M%S.%fZ") + "-" + uuid.uuid4().hex[:8]
        run_dir = output_root / run_id
        try:
            run_dir.mkdir(exist_ok=False)
            return run_id, run_dir
        except FileExistsError:
            continue
    raise RuntimeError("Could not allocate a unique run directory")


def apply_source_overrides(overrides: list[str]) -> list[dict[str, Any]]:
    sources = [dict(source) for source in DEFAULT_SOURCES]
    by_id = {source["id"]: source for source in sources}
    for override in overrides:
        if "=" not in override:
            raise ValueError(f"Invalid source override {override!r}; expected SOURCE_ID=URL")
        source_id, url = override.split("=", 1)
        if source_id not in by_id:
            raise ValueError(f"Unknown source id {source_id!r}")
        if urlsplit(url).scheme not in {"http", "https"}:
            raise ValueError(f"Override for {source_id!r} must be an HTTP(S) URL")
        by_id[source_id]["url"] = url
    return sources


def run_job(args: argparse.Namespace) -> tuple[str, Path]:
    sources = apply_source_overrides(args.source_url)
    output_root = Path(args.output_root).resolve()
    run_id, run_dir = make_run_directory(output_root)
    started_at = iso_now()
    digest_path = run_dir / "digest.md"
    evidence_path = run_dir / "evidence.json"
    events_path = run_dir / "events.jsonl"
    events: list[dict[str, Any]] = []
    warnings: list[str] = []
    errors: list[str] = []
    source_results: list[dict[str, Any]] = []
    collected: list[dict[str, Any]] = []

    def record(level: str, event: str, message: str, **details: Any) -> None:
        events.append(
            {
                "timestamp": iso_now(),
                "level": level,
                "event": event,
                "message": message,
                **details,
            }
        )

    record("INFO", "run_started", "Research update run started", run_id=run_id)
    try:
        for source in sources:
            result: dict[str, Any] = {
                "id": source["id"],
                "name": source["name"],
                "configured_url": source["url"],
                "attempted": True,
                "attempted_at": iso_now(),
                "landing_http_status": None,
                "landing_final_url": None,
                "status": "FAILED",
                "items_discovered": 0,
                "items_processed": 0,
                "selected_count": 0,
                "warnings": [],
                "errors": [],
            }
            source_results.append(result)
            record("INFO", "source_attempt", f"Attempting {source['name']}", source_id=source["id"], url=source["url"])
            landing = fetch_url(source["url"], args.timeout)
            result["landing_http_status"] = landing.status_code
            result["landing_final_url"] = landing.final_url
            if not landing.ok:
                message = f"{source['name']} landing page failed: {landing.error}"
                result["errors"].append(message)
                errors.append(message)
                record("ERROR", "source_failed", message, source_id=source["id"])
                continue

            candidates = discover_candidates(source, landing.text)
            result["items_discovered"] = len(candidates)
            record(
                "INFO",
                "source_discovered",
                f"Discovered {len(candidates)} candidate links from {source['name']}",
                source_id=source["id"],
                count=len(candidates),
            )
            if not candidates:
                message = f"{source['name']} returned HTML but no matching article links were discovered"
                result["errors"].append(message)
                errors.append(message)
                record("ERROR", "source_failed", message, source_id=source["id"])
                continue

            for candidate in candidates[: args.max_candidates_per_source]:
                article_fetch = fetch_url(candidate["url"], args.timeout)
                if not article_fetch.ok:
                    message = f"Article fetch failed for {candidate['url']}: {article_fetch.error}"
                    result["warnings"].append(message)
                    warnings.append(message)
                    record("WARNING", "article_failed", message, source_id=source["id"], url=candidate["url"])
                    continue
                item = extract_article(
                    source,
                    candidate,
                    article_fetch.text,
                    article_fetch.final_url or candidate["url"],
                )
                collected.append(item)
                result["items_processed"] += 1
                record("INFO", "article_processed", f"Processed {item['title']}", source_id=source["id"], url=item["url"])

            if result["items_processed"]:
                result["status"] = "SUCCESS"
                record("INFO", "source_succeeded", f"Processed {result['items_processed']} items from {source['name']}", source_id=source["id"])
            else:
                message = f"{source['name']} had candidates, but none could be processed"
                result["errors"].append(message)
                errors.append(message)
                record("ERROR", "source_failed", message, source_id=source["id"])

        selected = select_items(collected, args.max_items)
        selected_by_source: dict[str, int] = {}
        for item in selected:
            selected_by_source[item["source_id"]] = selected_by_source.get(item["source_id"], 0) + 1
        for result in source_results:
            result["selected_count"] = selected_by_source.get(result["id"], 0)

        successful_sources = sum(result["status"] == "SUCCESS" for result in source_results)
        if not selected or successful_sources == 0:
            preliminary_status = "FAILED"
        elif successful_sources < len(source_results):
            preliminary_status = "DEGRADED"
        else:
            preliminary_status = "SUCCESS"

        digest_path.write_text(render_digest(run_id, preliminary_status, selected), encoding="utf-8")
        checks = verification_checks(
            digest_path,
            source_results,
            selected,
            {source["id"] for source in sources},
        )
        critical_checks = (
            "digest_exists",
            "digest_nonempty",
            "all_configured_sources_attempted",
            "each_source_has_explicit_status",
            "selected_items_present",
            "selected_items_have_required_fields",
            "selected_counts_consistent",
        )
        final_status = preliminary_status
        if not all(checks[name] for name in critical_checks):
            final_status = "FAILED"
            failed = [name for name in critical_checks if not checks[name]]
            message = "Required verification failed: " + ", ".join(failed)
            errors.append(message)
            record("ERROR", "verification_failed", message, failed_checks=failed)
        else:
            record("INFO", "verification_passed", "All required internal verification checks passed")

        if final_status != preliminary_status:
            digest_path.write_text(render_digest(run_id, final_status, selected), encoding="utf-8")

    except Exception as exc:  # preserve evidence even for unexpected implementation failures
        final_status = "FAILED"
        selected = []
        checks = {}
        message = f"Unexpected run failure: {type(exc).__name__}: {exc}"
        errors.append(message)
        record("ERROR", "run_exception", message)
        if not digest_path.exists():
            digest_path.write_text(render_digest(run_id, final_status, selected), encoding="utf-8")

    finished_at = iso_now()
    record("INFO", "run_finished", f"Run finished with status {final_status}", status=final_status)
    evidence = {
        "schema_version": 1,
        "run_id": run_id,
        "started_at": started_at,
        "finished_at": finished_at,
        "configured_sources": [
            {"id": source["id"], "name": source["name"], "url": source["url"]}
            for source in sources
        ],
        "sources_attempted": source_results,
        "counts": {
            "sources_configured": len(sources),
            "sources_succeeded": sum(item["status"] == "SUCCESS" for item in source_results),
            "sources_failed": sum(item["status"] == "FAILED" for item in source_results),
            "items_discovered": sum(item["items_discovered"] for item in source_results),
            "items_processed": sum(item["items_processed"] for item in source_results),
            "items_selected": len(selected),
        },
        "selected_items": selected,
        "warnings": warnings,
        "errors": errors,
        "generated_output_path": str(digest_path.resolve()),
        "event_log_path": str(events_path.resolve()),
        "verification_checks": checks,
        "final_status": final_status,
    }
    evidence_path.write_text(json.dumps(evidence, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    events_path.write_text("".join(json.dumps(event, ensure_ascii=False) + "\n" for event in events), encoding="utf-8")
    return final_status, run_dir


def build_parser() -> argparse.ArgumentParser:
    assignment_root = Path(__file__).resolve().parent.parent
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output-root",
        default=str(assignment_root / "outputs"),
        help="Directory in which a new, uniquely named run directory is created",
    )
    parser.add_argument("--max-items", type=int, default=6, help="Maximum items in the digest")
    parser.add_argument(
        "--max-candidates-per-source",
        type=int,
        default=6,
        help="Maximum linked article pages fetched from each landing page",
    )
    parser.add_argument("--timeout", type=float, default=20.0, help="Per-request timeout in seconds")
    parser.add_argument(
        "--source-url",
        action="append",
        default=[],
        metavar="SOURCE_ID=URL",
        help="Override a configured source URL for a controlled failure experiment",
    )
    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    if args.max_items < 1 or args.max_candidates_per_source < 1 or args.timeout <= 0:
        parser.error("item limits and timeout must be positive")
    try:
        status, run_dir = run_job(args)
    except ValueError as exc:
        parser.error(str(exc))
    print(f"Final status: {status}")
    print(f"Run directory: {run_dir}")
    print(f"Digest: {run_dir / 'digest.md'}")
    print(f"Evidence: {run_dir / 'evidence.json'}")
    return {"SUCCESS": 0, "DEGRADED": 2, "FAILED": 1}[status]


if __name__ == "__main__":
    sys.exit(main())
