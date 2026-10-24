#!/usr/bin/env python3
"""Bounded recurring job for official AI news updates.

Each invocation is one bounded run. Schedule this script with cron, a task
runner, or Codex rather than keeping a long-running process alive.
"""

from __future__ import annotations

import argparse
import json
import logging
import re
import sys
from dataclasses import asdict, dataclass
from datetime import datetime, timedelta, timezone
from html.parser import HTMLParser
from pathlib import Path
from typing import Iterable
from urllib.error import HTTPError, URLError
from urllib.parse import urljoin, urlparse
from urllib.request import Request, urlopen


USER_AGENT = "impielOn-news-update/1.0 (+official-source-reader)"
MAX_RESPONSE_BYTES = 500_000
DATE_RE = re.compile(
    r"\b(?:Jan(?:uary)?|Feb(?:ruary)?|Mar(?:ch)?|Apr(?:il)?|May|Jun(?:e)?|"
    r"Jul(?:y)?|Aug(?:ust)?|Sep(?:tember)?|Oct(?:ober)?|Nov(?:ember)?|"
    r"Dec(?:ember)?)\s+\d{1,2},?\s+\d{4}\b",
    re.IGNORECASE,
)
WHITESPACE_RE = re.compile(r"\s+")


@dataclass(frozen=True)
class Source:
    name: str
    index_url: str
    allowed_prefixes: tuple[str, ...]


@dataclass
class Article:
    source: str
    title: str
    url: str
    date_text: str | None
    summary: str
    why_it_matters: str


SOURCES = (
    Source(
        "Anthropic News",
        "https://www.anthropic.com/news",
        ("https://www.anthropic.com/news/",),
    ),
    Source(
        "Anthropic Engineering",
        "https://www.anthropic.com/engineering",
        ("https://www.anthropic.com/engineering/",),
    ),
    Source(
        "OpenAI News",
        "https://openai.com/news/",
        ("https://openai.com/index/",),
    ),
)


def clean_text(value: str) -> str:
    return WHITESPACE_RE.sub(" ", value).strip()


class PageParser(HTMLParser):
    """Small HTML parser that keeps only metadata, headings, and links."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.meta: dict[str, str] = {}
        self.links: list[tuple[str, str]] = []
        self.headings: list[str] = []
        self.paragraphs: list[str] = []
        self._in_title = False
        self._heading_depth = 0
        self._in_paragraph = False
        self._text: list[str] = []
        self._link_href: str | None = None
        self._link_text: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attr = {key.lower(): value or "" for key, value in attrs}
        if tag.lower() == "meta":
            key = (attr.get("name") or attr.get("property") or "").lower()
            if key in {"description", "og:description", "twitter:description"}:
                self.meta.setdefault(key, clean_text(attr.get("content", "")))
        elif tag.lower() == "title":
            self._in_title = True
            self._text = []
        elif tag.lower() in {"h1", "h2", "h3"}:
            self._heading_depth = int(tag[1])
            self._text = []
        elif tag.lower() == "p":
            self._in_paragraph = True
            self._text = []
        elif tag.lower() == "a":
            self._link_href = attr.get("href") or None
            self._link_text = []

    def handle_endtag(self, tag: str) -> None:
        tag = tag.lower()
        value = clean_text(" ".join(self._text))
        if tag == "title":
            if value:
                self.meta.setdefault("title", value)
            self._in_title = False
            self._text = []
        elif tag in {"h1", "h2", "h3"}:
            if value:
                self.headings.append(value)
            self._heading_depth = 0
            self._text = []
        elif tag == "p":
            if value:
                self.paragraphs.append(value)
            self._in_paragraph = False
            self._text = []
        elif tag == "a" and self._link_href:
            self.links.append((self._link_href, clean_text(" ".join(self._link_text))))
            self._link_href = None
            self._link_text = []

    def handle_data(self, data: str) -> None:
        if self._link_href is not None:
            self._link_text.append(data)
        if self._in_title or self._heading_depth or self._in_paragraph:
            self._text.append(data)


def fetch(url: str, timeout: float) -> bytes:
    request = Request(url, headers={"User-Agent": USER_AGENT, "Accept": "text/html"})
    with urlopen(request, timeout=timeout) as response:
        content = response.read(MAX_RESPONSE_BYTES + 1)
    if len(content) > MAX_RESPONSE_BYTES:
        raise ValueError(f"response exceeded {MAX_RESPONSE_BYTES} bytes")
    return content


def parse_page(payload: bytes) -> PageParser:
    parser = PageParser()
    parser.feed(payload.decode("utf-8", errors="replace"))
    return parser


def article_links(source: Source, parser: PageParser) -> list[tuple[str, str]]:
    seen: set[str] = set()
    result: list[tuple[str, str]] = []
    for href, text in parser.links:
        absolute = urljoin(source.index_url, href).split("#", 1)[0]
        if not any(absolute.startswith(prefix) for prefix in source.allowed_prefixes):
            continue
        if absolute.rstrip("/") == source.index_url.rstrip("/") or absolute in seen:
            continue
        title = clean_text(text)
        if len(title) < 8 or title.lower() in {"read more", "learn more", "view all"}:
            continue
        seen.add(absolute)
        result.append((absolute, title))
    return result


def first_sentence(text: str, limit: int = 420) -> str:
    text = clean_text(text)
    if not text:
        return "Summary unavailable from the source page."
    sentences = re.split(r"(?<=[.!?])\s+", text)
    summary = " ".join(sentences[:2]).strip()
    return summary[:limit].rstrip() + ("…" if len(summary) > limit else "")


def article_summary(parser: PageParser, description: str, limit: int = 1000) -> str:
    """Create a bounded extractive summary from several article paragraphs."""
    boilerplate = (
        "AI safety and research company",
        "Anthropic is an AI safety",
        "© OpenAI",
        "all rights reserved",
    )
    paragraphs: list[str] = []
    for paragraph in parser.paragraphs:
        paragraph = clean_text(paragraph)
        if len(paragraph) < 45 or any(marker.lower() in paragraph.lower() for marker in boilerplate):
            continue
        if paragraph not in paragraphs:
            paragraphs.append(paragraph)
    if paragraphs:
        summary = " ".join(paragraphs[:4])
        return summary[:limit].rstrip() + ("…" if len(summary) > limit else "")
    return first_sentence(description, limit)


def article_from_page(source: Source, url: str, fallback_title: str, payload: bytes) -> Article:
    parser = parse_page(payload)
    title = parser.meta.get("og:title") or parser.meta.get("title") or fallback_title
    title = re.sub(r"\s*(?:[|\\·—-])\s*(Anthropic|OpenAI).*$", "", title, flags=re.I).strip()
    description = (
        parser.meta.get("og:description")
        or parser.meta.get("description")
        or parser.meta.get("twitter:description")
    )
    date_match = DATE_RE.search(" ".join(parser.headings))
    boilerplate = "AI safety and research company"
    if not description or boilerplate.lower() in description.lower():
        description = next((paragraph for paragraph in parser.paragraphs if boilerplate.lower() not in paragraph.lower()), "")
    why_it_matters = (
        f"It reports a development in {title}; its practical implications depend on how the "
        "described capabilities, safeguards, or policies are adopted."
    )
    return Article(
        source.name,
        title,
        url,
        date_match.group(0) if date_match else None,
        article_summary(parser, description),
        why_it_matters,
    )


def load_seen(path: Path) -> set[str]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return set(data.get("seen_urls", []))
    except (FileNotFoundError, json.JSONDecodeError, OSError, AttributeError):
        return set()


def write_json(path: Path, data: object) -> None:
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def render_markdown(run_at: datetime, articles: Iterable[Article], failures: list[str]) -> str:
    articles = list(articles)
    lines = [
        "# AI Research Update",
        "",
        f"Generated: {run_at.isoformat(timespec='seconds')}",
        "",
        "Sources: Anthropic News, Anthropic Engineering, and OpenAI News.",
        "",
    ]
    if articles:
        for article in articles:
            date = f" ({article.date_text})" if article.date_text else ""
            lines += [
                f"## [{article.title}]({article.url})",
                f"**{article.source}**{date}",
                "",
                article.summary,
                "",
                f"**Why it matters:** {article.why_it_matters}",
                "",
            ]
    elif failures:
        lines += [
            "No articles were reported because one or more permitted source requests failed.",
            "The specific failures are listed below.",
            "",
        ]
    else:
        lines += [
            "No new official articles were reported because discovered articles were already "
            "recorded or fell outside the configured lookback window.",
            "",
        ]
    if failures:
        lines += ["## Source fetch notes", ""]
        lines.extend(f"- {failure}" for failure in failures)
        lines.append("")
    return "\n".join(lines)


def run(args: argparse.Namespace) -> int:
    base_dir = Path(__file__).resolve().parent.parent
    output_dir = (base_dir / args.output_dir).resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    state_path = output_dir / "news_state.json"
    log_path = output_dir / "news_update.log"
    logging.basicConfig(filename=log_path, level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

    now = datetime.now(timezone.utc)
    cutoff = now - timedelta(days=args.lookback_days)
    seen = load_seen(state_path)
    failures: list[str] = []
    new_articles: list[Article] = []
    fetched_articles = 0
    discovered_urls: set[str] = set(seen)

    for source in SOURCES:
        try:
            index_parser = parse_page(fetch(source.index_url, args.timeout))
            candidates = article_links(source, index_parser)[: args.max_articles_per_source]
        except (HTTPError, URLError, TimeoutError, ValueError, OSError) as exc:
            failures.append(f"{source.name}: {exc}")
            logging.warning("Failed to read source index %s: %s", source.name, exc)
            continue

        for url, fallback_title in candidates:
            discovered_urls.add(url)
            if url in seen or fetched_articles >= args.max_article_fetches:
                continue
            try:
                article = article_from_page(source, url, fallback_title, fetch(url, args.timeout))
                fetched_articles += 1
                if article.date_text:
                    try:
                        date = None
                        for date_format in ("%B %d, %Y", "%b %d, %Y"):
                            try:
                                date = datetime.strptime(article.date_text, date_format).replace(tzinfo=timezone.utc)
                                break
                            except ValueError:
                                continue
                        if date is None:
                            raise ValueError("unrecognized article date")
                        if date < cutoff:
                            continue
                    except ValueError:
                        pass
                new_articles.append(article)
            except (HTTPError, URLError, TimeoutError, ValueError, OSError) as exc:
                failures.append(f"{source.name} article {url}: {exc}")
                logging.warning("Failed to read article %s: %s", url, exc)

    timestamp = now.strftime("%Y%m%dT%H%M%SZ")
    output_path = output_dir / f"ai-news-update-{timestamp}.md"
    output_path.write_text(render_markdown(now, new_articles, failures), encoding="utf-8")
    write_json(state_path, {"seen_urls": sorted(discovered_urls), "last_run": now.isoformat()})
    logging.info("run complete: %d new articles, %d failures", len(new_articles), len(failures))
    print(output_path)
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--max-articles-per-source", type=int, default=3)
    parser.add_argument("--max-article-fetches", type=int, default=6)
    parser.add_argument("--lookback-days", type=int, default=14)
    parser.add_argument("--timeout", type=float, default=10.0)
    parser.add_argument("--output-dir", default="outputs")
    return parser


if __name__ == "__main__":
    arguments = build_parser().parse_args()
    if any(value <= 0 for value in (arguments.max_articles_per_source, arguments.max_article_fetches, arguments.lookback_days, arguments.timeout)):
        print("All bounds must be positive.", file=sys.stderr)
        raise SystemExit(2)
    raise SystemExit(run(arguments))
