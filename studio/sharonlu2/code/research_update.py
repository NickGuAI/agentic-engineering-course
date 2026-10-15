#!/usr/bin/env python3
"""Collect recent AI news and write a Markdown digest plus a run record."""

from __future__ import annotations

import argparse
import email.utils
import html
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
import socket
import urllib.error
import urllib.parse
import urllib.request
import uuid
import xml.etree.ElementTree as ET
from dataclasses import asdict, dataclass, field
from datetime import date, datetime, timedelta, timezone
from html.parser import HTMLParser
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo


EASTERN = ZoneInfo("America/New_York")
DEFAULT_SOURCES = [
    ("Anthropic News", "https://www.anthropic.com/news"),
    ("Anthropic Engineering", "https://www.anthropic.com/engineering"),
    ("OpenAI News", "https://openai.com/news/"),
]
USER_AGENT = "ResearchUpdate/1.0 (+personal research digest)"
MAX_BODY_BYTES = 2_000_000
MAX_ARTICLES_PER_SOURCE = 30
MAX_ARTICLE_TEXT = 12_000


@dataclass
class Article:
    title: str
    published: date
    source: str
    url: str
    content: str = field(repr=False)
    summary: str = ""


@dataclass
class SourceResult:
    name: str
    url: str
    outcome: str
    detail: str = ""
    candidates: int = 0
    eligible_articles: int = 0
    failure_kind: str | None = None


class FetchError(Exception):
    def __init__(self, message: str, *, kind: str = "request_failure"):
        super().__init__(message)
        self.kind = kind


class ModelInvocationError(RuntimeError):
    def __init__(self, message: str, *, log_id: str, invoked: bool, status: str):
        super().__init__(message)
        self.log_id = log_id
        self.invoked = invoked
        self.status = status


class PageParser(HTMLParser):
    """Collect links, article metadata and readable page text without dependencies."""

    def __init__(self, base_url: str):
        super().__init__(convert_charrefs=True)
        self.base_url = base_url
        self.links: list[dict[str, str]] = []
        self.meta: dict[str, str] = {}
        self.feed_links: list[str] = []
        self.time_values: list[str] = []
        self.jsonld: list[str] = []
        self.title_parts: list[str] = []
        self.h1_parts: list[str] = []
        self.text_parts: list[str] = []
        self._anchor: dict[str, str] | None = None
        self._in_title = False
        self._in_h1 = False
        self._skip_depth = 0
        self._jsonld_depth = 0
        self._jsonld_parts: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attrs_dict = {key.lower(): (value or "") for key, value in attrs}
        if tag in {"script", "style", "noscript", "svg"}:
            self._skip_depth += 1
            if tag == "script" and "ld+json" in attrs_dict.get("type", "").lower():
                self._jsonld_depth = 1
                self._jsonld_parts = []
            return
        if self._skip_depth:
            return
        if tag == "a" and attrs_dict.get("href"):
            self._anchor = {"href": urllib.parse.urljoin(self.base_url, attrs_dict["href"]), "text": ""}
        if tag == "meta":
            key = attrs_dict.get("property") or attrs_dict.get("name") or attrs_dict.get("itemprop")
            content = attrs_dict.get("content", "")
            if key and content:
                self.meta[key.lower()] = content.strip()
        if tag == "link" and "alternate" in attrs_dict.get("rel", "").lower():
            mime = attrs_dict.get("type", "").lower()
            if "rss" in mime or "atom" in mime or "xml" in mime:
                href = attrs_dict.get("href")
                if href:
                    self.feed_links.append(urllib.parse.urljoin(self.base_url, href))
        if tag == "time" and attrs_dict.get("datetime"):
            self.time_values.append(attrs_dict["datetime"].strip())
        if tag == "title":
            self._in_title = True
        if tag == "h1":
            self._in_h1 = True

    def handle_endtag(self, tag: str) -> None:
        if tag in {"script", "style", "noscript", "svg"}:
            if self._jsonld_depth:
                self.jsonld.append("".join(self._jsonld_parts))
                self._jsonld_depth = 0
            self._skip_depth = max(0, self._skip_depth - 1)
            return
        if self._skip_depth:
            return
        if tag == "a" and self._anchor is not None:
            self._anchor["text"] = " ".join(self._anchor["text"].split())
            self.links.append(self._anchor)
            self._anchor = None
        if tag == "title":
            self._in_title = False
        if tag == "h1":
            self._in_h1 = False

    def handle_data(self, data: str) -> None:
        value = data.strip()
        if not value:
            return
        if self._jsonld_depth:
            self._jsonld_parts.append(data)
        if self._skip_depth:
            return
        if self._anchor is not None:
            self._anchor["text"] += " " + value
        if self._in_title:
            self.title_parts.append(value)
        if self._in_h1:
            self.h1_parts.append(value)
        self.text_parts.append(value)


def _fetch(url: str, timeout: float, retries: int = 1) -> tuple[bytes, str, str]:
    """Fetch a page with bounded retries; return bytes, final URL and content type."""
    last_error: Exception | None = None
    for attempt in range(retries + 1):
        request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT, "Accept": "text/html,application/atom+xml,application/rss+xml,application/xml,*/*;q=0.7"})
        try:
            with urllib.request.urlopen(request, timeout=timeout) as response:
                payload = response.read(MAX_BODY_BYTES + 1)
                if len(payload) > MAX_BODY_BYTES:
                    raise FetchError(f"response exceeded {MAX_BODY_BYTES} bytes")
                return payload, response.geturl(), response.headers.get_content_type()
        except urllib.error.HTTPError as exc:
            last_error = exc
            if exc.code in (404, 410):
                raise FetchError(f"HTTP {exc.code}: requested page unavailable", kind="unavailable_page") from exc
            retryable = exc.code == 429 or 500 <= exc.code <= 599
        except (urllib.error.URLError, TimeoutError, OSError) as exc:
            last_error = exc
            reason = getattr(exc, "reason", exc)
            if isinstance(reason, socket.gaierror) and reason.errno in {
                getattr(socket, "EAI_NONAME", None),
                getattr(socket, "EAI_NODATA", None),
            }:
                raise FetchError("host name does not resolve (DNS reported a nonexistent name)", kind="nonexistent_host") from exc
            retryable = True
        except FetchError:
            raise
        if attempt >= retries or not retryable:
            break
        time.sleep(0.25 * (attempt + 1))
    raise FetchError(f"request failed: {type(last_error).__name__}: {last_error}") from last_error

def _decode(payload: bytes, content_type: str) -> str:
    match = re.search(r"charset=([\w-]+)", content_type, re.IGNORECASE)
    encoding = match.group(1) if match else "utf-8"
    try:
        return payload.decode(encoding, errors="replace")
    except LookupError:
        return payload.decode("utf-8", errors="replace")


def _parse_date(value: str | None) -> date | None:
    if not value:
        return None
    value = html.unescape(value.strip())
    if not value:
        return None
    try:
        normalized = value.replace("Z", "+00:00")
        parsed = datetime.fromisoformat(normalized)
    except ValueError:
        try:
            parsed = email.utils.parsedate_to_datetime(value)
        except (TypeError, ValueError, OverflowError):
            return None
    if parsed is None:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=EASTERN)
    return parsed.astimezone(EASTERN).date()


def _walk_jsonld(value: Any) -> list[dict[str, Any]]:
    found: list[dict[str, Any]] = []
    if isinstance(value, dict):
        found.append(value)
        for child in value.values():
            found.extend(_walk_jsonld(child))
    elif isinstance(value, list):
        for child in value:
            found.extend(_walk_jsonld(child))
    return found


def _page_metadata(parser: PageParser) -> tuple[str, date | None]:
    title = " ".join(parser.h1_parts).strip() or " ".join(parser.title_parts).strip()
    date_values = [
        parser.meta.get("article:published_time"),
        parser.meta.get("datepublished"),
        parser.meta.get("date"),
        parser.meta.get("pubdate"),
        parser.meta.get("parsely-pub-date"),
        *parser.time_values,
    ]
    for raw_json in parser.jsonld:
        try:
            nodes = _walk_jsonld(json.loads(raw_json))
        except (json.JSONDecodeError, TypeError):
            continue
        for node in nodes:
            if not title and isinstance(node.get("headline"), str):
                title = node["headline"].strip()
            date_values.append(node.get("datePublished"))
    published = next((parsed for value in date_values if (parsed := _parse_date(str(value)) if value else None)), None)
    return title, published


def _parse_feed(text: str, base_url: str) -> list[dict[str, str]]:
    try:
        root = ET.fromstring(text)
    except ET.ParseError:
        return []
    candidates = []
    for node in root.iter():
        if node.tag.rsplit("}", 1)[-1].lower() not in {"item", "entry"}:
            continue
        item: dict[str, str] = {}
        for child in node:
            name = child.tag.rsplit("}", 1)[-1].lower()
            if name == "link":
                href = child.attrib.get("href") or (child.text or "").strip()
                if href:
                    item["url"] = urllib.parse.urljoin(base_url, href)
            elif name in {"title", "published", "pubdate", "summary", "description"}:
                if child.text:
                    item[name] = " ".join(child.itertext()).strip()
            elif name == "guid" and child.text and "url" not in item:
                item["url"] = urllib.parse.urljoin(base_url, child.text.strip())
        if item.get("url") and item.get("title"):
            candidates.append(item)
    return candidates


def _is_article_link(href: str, source_url: str) -> bool:
    parsed = urllib.parse.urlsplit(href)
    if parsed.scheme not in ("http", "https") or not parsed.netloc:
        return False
    if parsed.netloc.lower() != urllib.parse.urlsplit(source_url).netloc.lower():
        return False
    path = parsed.path.rstrip("/")
    if not path or path == urllib.parse.urlsplit(source_url).path.rstrip("/"):
        return False
    low = path.lower()
    if any(part in low for part in ("/tag/", "/category/", "/author/", "/search", "/privacy", "/terms", "/careers", "/contact")):
        return False
    if re.search(r"\.(?:png|jpe?g|gif|svg|pdf|css|js|zip)$", low):
        return False
    return True


def _discover(source_url: str, timeout: float) -> tuple[list[dict[str, str]], str]:
    payload, final_url, content_type = _fetch(source_url, timeout)
    text = _decode(payload, content_type)
    parser = PageParser(final_url)
    parser.feed(text)
    candidates: list[dict[str, str]] = []
    for feed_url in parser.feed_links[:3]:
        try:
            feed_payload, feed_final_url, feed_type = _fetch(feed_url, timeout)
            feed_items = _parse_feed(_decode(feed_payload, feed_type), feed_final_url)
            if feed_items:
                candidates.extend(feed_items)
                break
        except FetchError:
            continue
    if not candidates:
        seen: set[str] = set()
        for link in parser.links:
            href = link["href"].split("#", 1)[0]
            if _is_article_link(href, final_url) and href not in seen:
                seen.add(href)
                candidates.append({"url": href, "title": link["text"]})
                if len(candidates) >= MAX_ARTICLES_PER_SOURCE:
                    break
    return candidates[:MAX_ARTICLES_PER_SOURCE], final_url


def _article_from_candidate(candidate: dict[str, str], source_name: str, timeout: float) -> Article | None:
    payload, final_url, content_type = _fetch(candidate["url"], timeout)
    text = _decode(payload, content_type)
    parser = PageParser(final_url)
    parser.feed(text)
    title, published = _page_metadata(parser)
    if not title:
        title = html.unescape(candidate.get("title", "")).strip()
    if not published:
        for key in ("published", "pubdate"):
            published = _parse_date(candidate.get(key))
            if published:
                break
    if not title or not published:
        return None
    content = " ".join(parser.text_parts)
    content = re.sub(r"\s+", " ", html.unescape(content)).strip()[:MAX_ARTICLE_TEXT]
    if not content:
        return None
    return Article(title=title, published=published, source=source_name, url=final_url, content=content)


def retrieve_source(name: str, url: str, timeout: float, window_start: date, window_end: date) -> tuple[list[Article], SourceResult]:
    try:
        candidates, final_url = _discover(url, timeout)
    except FetchError as exc:
        return [], SourceResult(name, url, "failed", str(exc), failure_kind=exc.kind)
    articles: list[Article] = []
    errors: list[FetchError] = []
    for candidate in candidates:
        try:
            article = _article_from_candidate(candidate, name, timeout)
        except FetchError as exc:
            errors.append(exc)
            continue
        if article and window_start <= article.published <= window_end:
            articles.append(article)
    if errors:
        counts: dict[str, int] = {}
        for error in errors:
            counts[error.kind] = counts.get(error.kind, 0) + 1
        error_summary = ", ".join(f"{kind}: {count}" for kind, count in sorted(counts.items()))
        result = SourceResult(name, final_url, "partial", f"{len(errors)} article page(s) could not be fetched ({error_summary})", len(candidates), len(articles), "article_page_failure")
    elif not candidates:
        result = SourceResult(name, final_url, "partial", "source page fetched, but no feed entries or article links were discovered", 0, 0)
    else:
        result = SourceResult(name, final_url, "checked", "source checked successfully", len(candidates), len(articles))
    return articles, result


def _prompt_for_summaries(articles: list[Article]) -> str:
    payload = [{"id": str(i), "title": a.title, "source": a.source, "url": a.url, "content": a.content} for i, a in enumerate(articles)]
    return (
        "Summarize these retrieved news articles for CS graduate students and AI researchers. "
        "Use only facts supported by each article's supplied content. Do not add background from memory. "
        "Return only a JSON array of objects with fields id and summary. Each summary must be concise (1-3 sentences). "
        "If content does not support a useful summary, use an empty string.\n\n"
        + json.dumps(payload, ensure_ascii=False)
    )


def _within(path: Path, parent: Path) -> bool:
    try:
        path.relative_to(parent)
        return True
    except ValueError:
        return False


def summarize_with_codex(articles: list[Article], model: str, timeout: float, binary: str, raw_log_dir: Path) -> str | None:
    """Invoke Codex once and return its persistent raw-log identifier."""
    if not articles:
        return None

    invocation_id = f"codex-{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}-{uuid.uuid4().hex[:8]}"
    log_dir = raw_log_dir / invocation_id
    try:
        log_dir.mkdir(parents=True, exist_ok=False)
        prompt = _prompt_for_summaries(articles).encode("utf-8")
        (log_dir / "prompt.txt").write_bytes(prompt)
    except OSError as exc:
        raise ModelInvocationError(
            f"Could not create raw model log directory: {exc}",
            log_id=invocation_id,
            invoked=False,
            status="logging_failed_before_call",
        ) from exc

    events_path = log_dir / "events.jsonl"
    stderr_path = log_dir / "stderr.log"
    response_path = log_dir / "response.txt"
    settings_path = log_dir / "invocation.json"
    executable = shutil.which(binary)
    if executable:
        command = [
            executable, "exec", "--json", "--ephemeral", "--model", model,
            "--sandbox", "read-only", "--cd", str(log_dir), "--skip-git-repo-check",
            "--output-last-message", str(response_path), "-",
        ]
    else:
        command = [binary, "exec", "--json", "--ephemeral", "--model", model]

    started_at = datetime.now(timezone.utc).isoformat()
    settings: dict[str, Any] = {
        "invocation_id": invocation_id,
        "provider": "Codex CLI",
        "model": model,
        "command": command,
        "timeout_seconds": timeout,
        "started_at": started_at,
        "working_directory": str(log_dir),
        "flags": {"json_events": True, "ephemeral": True, "sandbox": "read-only"},
        "exit_status": None,
        "invoked": False,
        "status": "not_started",
        "events_file": events_path.name,
        "stderr_file": stderr_path.name,
        "prompt_file": "prompt.txt",
        "response_file": response_path.name,
    }
    if not executable:
        settings["launch_error"] = f"Codex CLI executable not found: {binary}"
        events_path.write_bytes(b"")
        stderr_path.write_bytes(b"")
        response_path.write_bytes(b"")
        settings["finished_at"] = datetime.now(timezone.utc).isoformat()
        settings_path.write_text(json.dumps(settings, indent=2) + "\n", encoding="utf-8")
        raise ModelInvocationError(settings["launch_error"], log_id=invocation_id, invoked=False, status="not_started")

    try:
        with tempfile.TemporaryDirectory(prefix="research-update-work-") as temp_dir:
            settings["working_directory"] = temp_dir
            command[command.index("--cd") + 1] = temp_dir
            settings["command"] = command
            completed = subprocess.run(
                command,
                input=prompt,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                timeout=timeout,
                check=False,
            )
    except subprocess.TimeoutExpired as exc:
        stdout = exc.stdout or b""
        stderr = exc.stderr or b""
        events_path.write_bytes(stdout if isinstance(stdout, bytes) else stdout.encode())
        stderr_path.write_bytes(stderr if isinstance(stderr, bytes) else stderr.encode())
        if not response_path.exists():
            response_path.write_bytes(b"")
        settings.update({
            "invoked": True,
            "status": "timed_out",
            "exit_status": None,
            "timed_out": True,
            "finished_at": datetime.now(timezone.utc).isoformat(),
        })
        settings_path.write_text(json.dumps(settings, indent=2) + "\n", encoding="utf-8")
        raise ModelInvocationError(f"Codex summary request timed out after {timeout:g} seconds", log_id=invocation_id, invoked=True, status="timed_out") from exc
    except OSError as exc:
        events_path.write_bytes(b"")
        stderr_path.write_bytes(b"")
        response_path.write_bytes(b"")
        settings.update({
            "status": "launch_failed",
            "launch_error": str(exc),
            "finished_at": datetime.now(timezone.utc).isoformat(),
        })
        settings_path.write_text(json.dumps(settings, indent=2) + "\n", encoding="utf-8")
        raise ModelInvocationError(f"Could not launch Codex CLI: {exc}", log_id=invocation_id, invoked=False, status="launch_failed") from exc

    events_path.write_bytes(completed.stdout)
    stderr_path.write_bytes(completed.stderr)
    response_bytes = response_path.read_bytes() if response_path.exists() else b""
    if not response_path.exists():
        response_path.write_bytes(response_bytes)
    settings.update({
        "invoked": True,
        "status": "succeeded" if completed.returncode == 0 else "failed",
        "exit_status": completed.returncode,
        "finished_at": datetime.now(timezone.utc).isoformat(),
        "response_present": bool(response_bytes),
    })
    settings_path.write_text(json.dumps(settings, indent=2) + "\n", encoding="utf-8")
    if completed.returncode != 0:
        raise ModelInvocationError(f"Codex summary request failed with exit code {completed.returncode}", log_id=invocation_id, invoked=True, status="failed")
    if not response_bytes:
        raise ModelInvocationError("Codex completed without writing its final message", log_id=invocation_id, invoked=True, status="failed")
    response = response_bytes.decode("utf-8", errors="replace").strip()
    response = re.sub(r"\A```(?:json)?\s*|\s*```\Z", "", response, flags=re.IGNORECASE)
    try:
        values = json.loads(response)
    except json.JSONDecodeError as exc:
        raise ModelInvocationError("Codex returned invalid JSON for article summaries", log_id=invocation_id, invoked=True, status="invalid_response") from exc
    if not isinstance(values, list):
        raise ModelInvocationError("Codex returned a summary response that was not a JSON array", log_id=invocation_id, invoked=True, status="invalid_response")
    by_id = {str(item.get("id")): item.get("summary") for item in values if isinstance(item, dict)}
    for i, article in enumerate(articles):
        summary = by_id.get(str(i))
        if isinstance(summary, str) and summary.strip():
            article.summary = " ".join(summary.split())
        else:
            article.summary = "Summary unavailable: the model did not return a usable summary."
    return invocation_id


def _valid_custom_url(raw_url: str) -> tuple[str, str] | None:
    try:
        parsed = urllib.parse.urlsplit(raw_url.strip())
        if parsed.scheme not in {"http", "https"} or not parsed.hostname:
            return None
        if parsed.username or parsed.password:
            return None
        _ = parsed.port  # Validate malformed ports before attempting DNS or HTTP.
        host = parsed.hostname
        if any(char.isspace() for char in host) or "/" in host or "\\" in host:
            return None
        host.encode("idna")
        normalized = urllib.parse.urlunsplit((parsed.scheme.lower(), parsed.netloc, parsed.path or "/", parsed.query, ""))
        return (host.lower(), normalized)
    except (UnicodeError, ValueError):
        return None


def _custom_source_name(url: str) -> str:
    host = urllib.parse.urlsplit(url).hostname or url
    return host.removeprefix("www.")


def _unique_path(output_dir: Path, stem: str, suffix: str) -> Path:
    path = output_dir / f"{stem}{suffix}"
    if not path.exists():
        return path
    index = 2
    while (output_dir / f"{stem}-{index}{suffix}").exists():
        index += 1
    return output_dir / f"{stem}-{index}{suffix}"


def _markdown_report(articles: list[Article], results: list[SourceResult], run_date: date, window_start: date, window_end: date, warning: str | None, incomplete: bool, model_error: str | None) -> str:
    status = "INCOMPLETE — some source checks or summaries failed" if incomplete else "Complete"
    lines = [
        "# AI Research Update",
        "",
        f"**Run date (Eastern Time):** {run_date.isoformat()}  ",
        f"**Publication window:** {window_start.isoformat()} through {window_end.isoformat()} (previous seven complete Eastern Time dates)  ",
        f"**Status:** {status}",
    ]
    if warning:
        lines.extend(["", f"**Source selection notice:** {warning}"])
    if model_error:
        lines.extend(["", f"**Summary notice:** {model_error}"])
    lines.extend(["", "## Articles", ""])
    if articles:
        for i, article in enumerate(articles[:10], start=1):
            lines.extend([
                f"### {i}. {article.title}",
                "",
                f"- **Publication date:** {article.published.isoformat()}",
                f"- **Source:** {article.source}",
                f"- **Article:** [{article.url}]({article.url})",
                f"- **Summary:** {article.summary or 'Summary unavailable.'}",
                "",
            ])
    elif all(result.outcome == "checked" for result in results):
        lines.extend(["No eligible articles with verifiable publication dates were found in the configured sources.", ""])
    else:
        lines.extend(["No eligible articles could be confirmed. One or more configured sources failed or were only partially checked.", ""])
    lines.extend(["## Source checks", ""])
    for result in results:
        detail = f" — {result.detail}" if result.detail else ""
        lines.append(f"- **{result.name}** ({result.url}): {result.outcome}{detail}; {result.candidates} candidate(s), {result.eligible_articles} eligible article(s).")
    lines.append("")
    return "\n".join(lines)


def _run(args: argparse.Namespace) -> tuple[Path, Path, dict[str, Any]]:
    run_time = datetime.now(EASTERN)
    run_date = run_time.date()
    window_start = run_date - timedelta(days=7)
    window_end = run_date - timedelta(days=1)
    warning = None
    custom_sources: list[tuple[str, str]] = []
    custom_invalid = []
    for raw in args.source:
        parsed = _valid_custom_url(raw)
        if parsed is None:
            custom_invalid.append(raw)
        else:
            host, normalized = parsed
            custom_sources.append((_custom_source_name(normalized), normalized))
    # Malformed URLs and hosts positively reported nonexistent by DNS fall back to defaults.
    use_defaults = not args.source or bool(custom_invalid)
    source_results: list[SourceResult] = [
        SourceResult(raw, raw, "failed", "invalid custom URL; using default sources", failure_kind="invalid_url")
        for raw in custom_invalid
    ]
    if custom_invalid:
        warning = "Invalid custom URL(s): " + ", ".join(custom_invalid) + ". Falling back to default sources."
        custom_sources = []
    configured_sources = list(DEFAULT_SOURCES) if use_defaults else custom_sources
    articles: list[Article] = []
    missing_custom_sites: list[SourceResult] = []
    for name, url in configured_sources:
        source_articles, result = retrieve_source(name, url, args.timeout, window_start, window_end)
        source_results.append(result)
        articles.extend(source_articles)
        if not use_defaults and result.outcome == "failed" and result.failure_kind == "nonexistent_host":
            missing_custom_sites.append(result)
    if missing_custom_sites:
        sites = ", ".join(result.url for result in missing_custom_sites)
        warning = f"Custom website(s) {sites} do not appear to exist. Falling back to default sources."
        articles = []
        for name, url in DEFAULT_SOURCES:
            source_articles, result = retrieve_source(name, url, args.timeout, window_start, window_end)
            source_results.append(result)
            articles.extend(source_articles)
    articles.sort(key=lambda article: (article.published, article.title.lower()), reverse=True)
    articles = articles[:10]
    model_error = None
    model_log_id = None
    model_invoked = False
    model_status = "not_called"
    model_not_called_reason = "no_eligible_articles" if not articles else None
    raw_log_root = Path(args.raw_log_dir).expanduser().resolve()
    if articles:
        repo_root = Path(__file__).resolve().parents[3]
        try:
            if _within(raw_log_root, repo_root):
                raise ValueError("--raw-log-dir must resolve outside the repository")
            model_log_id = summarize_with_codex(articles, args.model, args.model_timeout, args.codex_binary, raw_log_root)
            model_invoked = model_log_id is not None
            model_status = "succeeded" if model_invoked else "not_called"
        except ModelInvocationError as exc:
            model_log_id = exc.log_id
            model_invoked = exc.invoked
            model_status = exc.status
            model_error = str(exc)
            if not model_invoked:
                model_not_called_reason = exc.status
            for article in articles:
                article.summary = "Summary unavailable because the model step failed."
        except (RuntimeError, OSError, ValueError) as exc:
            model_error = str(exc)
            model_status = "not_called"
            model_not_called_reason = "raw_log_dir_invalid"
            for article in articles:
                article.summary = "Summary unavailable because the model step failed."
    incomplete = any(result.outcome in {"failed", "partial"} for result in source_results) or bool(model_error) or any(article.summary.startswith("Summary unavailable") for article in articles)
    timestamp = run_time.strftime("%Y%m%d-%H%M%S")
    run_id = f"research-update-{timestamp}-{uuid.uuid4().hex[:6]}"
    output_dir = Path(args.output_dir).expanduser().resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    report_path = _unique_path(output_dir, run_id, ".md")
    record_path = _unique_path(output_dir, run_id, ".json")
    report_path.write_text(_markdown_report(articles, source_results, run_date, window_start, window_end, warning, incomplete, model_error), encoding="utf-8")
    record = {
        "run_id": run_id,
        "started_at": run_time.isoformat(),
        "timezone": "America/New_York",
        "window": {"start_inclusive": window_start.isoformat(), "end_inclusive": window_end.isoformat(), "run_date_excluded": run_date.isoformat()},
        "status": "incomplete" if incomplete else "complete",
        "model": {
            "provider": "Codex CLI",
            "name": args.model,
            "invoked": model_invoked,
            "status": model_status,
            "not_called_reason": model_not_called_reason,
            "log_id": model_log_id,
            "raw_log_dir": str(raw_log_root),
            "error": model_error,
        },
        "source_selection_notice": warning,
        "sources": [asdict(result) for result in source_results],
        "articles": [
            {"title": article.title, "publication_date": article.published.isoformat(), "source": article.source, "url": article.url, "summary": article.summary}
            for article in articles
        ],
        "report_file": report_path.name,
    }
    record_path.write_text(json.dumps(record, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return report_path, record_path, record


def build_parser() -> argparse.ArgumentParser:
    default_output = Path(__file__).resolve().parent.parent / "outputs"
    default_raw_log_dir = Path.home() / ".local" / "state" / "research-update" / "raw-logs"
    parser = argparse.ArgumentParser(description="Create a seven-day AI research news digest.")
    parser.add_argument("--team", required=True, choices=("sharonlu2",), help="Team folder receiving this run's evidence (required by course instructions).")
    parser.add_argument("--source", action="append", default=[], metavar="URL", help="Use a custom website URL; repeat for multiple sources. Defaults are used when omitted.")
    parser.add_argument("--output-dir", default=str(default_output), help="Directory for reports and JSON run records.")
    parser.add_argument("--raw-log-dir", default=str(default_raw_log_dir), help="Persistent Codex invocation logs; must resolve outside the repository.")
    parser.add_argument("--timeout", type=float, default=12.0, help="Timeout in seconds for each HTTP request (default: 12).")
    parser.add_argument("--model-timeout", type=float, default=150.0, help="Timeout in seconds for the Codex summary step (default: 150).")
    parser.add_argument("--model", default=os.environ.get("RESEARCH_UPDATE_MODEL", "gpt-6-luna"), help="Codex model (default: RESEARCH_UPDATE_MODEL or gpt-6-luna).")
    parser.add_argument("--codex-binary", default="codex", help="Codex CLI executable name or path (default: codex).")
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if args.timeout <= 0 or args.model_timeout <= 0:
        parser.error("timeouts must be positive")
    try:
        report, record, run = _run(args)
    except Exception as exc:
        print(f"Research update failed before reports were saved: {exc}", file=sys.stderr)
        return 1
    print(f"Status: {run['status']}")
    print(f"Report: {report}")
    print(f"Run record: {record}")
    if run.get("source_selection_notice"):
        print(f"Notice: {run['source_selection_notice']}")
    return 0 if run["status"] == "complete" else 2


if __name__ == "__main__":
    raise SystemExit(main())
