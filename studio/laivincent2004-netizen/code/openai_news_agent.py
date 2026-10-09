"""Bounded OpenAI News summarizer for Studio 01.

This agent uses only public OpenAI News pages, writes a summary plus a run
record, and can simulate an unavailable source page for the change-and-explain
part of the studio.
"""
from __future__ import annotations

import argparse
import html
import json
import re
import textwrap
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Callable
from urllib.error import URLError
from urllib.parse import urljoin, urlparse
from urllib.request import Request, urlopen


NEWS_INDEX_URL = "https://openai.com/news/"
NEWS_URL = "https://openai.com/news/rss.xml"
OPENAI_HOST = "openai.com"


class AgentStop(RuntimeError):
    """Raised when the agent cannot finish without inventing details."""


@dataclass(frozen=True)
class NewsItem:
    title: str
    category: str
    date: str
    url: str
    description: str


@dataclass(frozen=True)
class ArticleEvidence:
    item: NewsItem
    bullets: list[str]
    terms: list[tuple[str, str]]
    takeaway: str


def fetch_url(url: str, *, timeout: int = 20) -> str:
    parsed = urlparse(url)
    if parsed.scheme != "https" or parsed.netloc != OPENAI_HOST:
        raise AgentStop(f"Refusing non-OpenAI source: {url}")
    request = Request(
        url,
        headers={
            "User-Agent": "Studio01OpenAINewsAgent/1.0",
            "Accept": "application/rss+xml,text/xml,text/html;q=0.9,*/*;q=0.8",
        },
    )
    try:
        with urlopen(request, timeout=timeout) as response:
            return response.read().decode("utf-8", errors="replace")
    except URLError as exc:
        raise AgentStop(f"Could not fetch required source: {url}") from exc


def normalize_url(raw_url: str | None) -> str | None:
    if not raw_url:
        return None
    markdown_match = re.search(r"\((https://[^)]+)\)", raw_url.strip())
    url = markdown_match.group(1) if markdown_match else raw_url.strip()
    return url.rstrip("/")


def clean_text(raw: str) -> str:
    raw = re.sub(r"<script\b.*?</script>", " ", raw, flags=re.I | re.S)
    raw = re.sub(r"<style\b.*?</style>", " ", raw, flags=re.I | re.S)
    raw = re.sub(r"<[^>]+>", " ", raw)
    raw = html.unescape(raw)
    raw = re.sub(r"\s+", " ", raw)
    return raw.strip()


def parse_rss_items(news_xml: str, *, limit: int = 3) -> list[NewsItem]:
    import xml.etree.ElementTree as ET
    from email.utils import parsedate_to_datetime

    try:
        root = ET.fromstring(news_xml)
    except ET.ParseError as exc:
        raise AgentStop("OpenAI News RSS could not be parsed") from exc

    items: list[NewsItem] = []
    for node in root.findall("./channel/item"):
        title = (node.findtext("title") or "").strip()
        link = (node.findtext("link") or "").strip()
        category = (node.findtext("category") or "News").strip()
        description = clean_text(node.findtext("description") or "")
        pub_date = (node.findtext("pubDate") or "").strip()
        if not title or not link or not pub_date:
            continue
        try:
            parsed = parsedate_to_datetime(pub_date)
            date = f"{parsed.strftime('%B')} {parsed.day}, {parsed.year}"
        except ValueError:
            date = pub_date
        if date.startswith("0"):
            date = date[1:]
        items.append(NewsItem(title=title, category=category, date=date, url=link, description=description))
        if len(items) == limit:
            break
    if len(items) < limit:
        raise AgentStop(f"Expected {limit} OpenAI News RSS items, found {len(items)}")
    return items


def parse_news_items(news_html: str, *, limit: int = 3) -> list[NewsItem]:
    if "<rss" in news_html[:200].lower():
        return parse_rss_items(news_html, limit=limit)
    link_pattern = re.compile(
        r'<a[^>]+href="(?P<href>/index/[^"]+/)"[^>]*>(?P<body>.*?)</a>',
        re.I | re.S,
    )
    items: list[NewsItem] = []
    seen: set[str] = set()
    for match in link_pattern.finditer(news_html):
        url = urljoin(NEWS_URL, match.group("href"))
        if url in seen:
            continue
        body = clean_text(match.group("body"))
        date_match = re.search(r"([A-Z][a-z]{2}\s+\d{1,2},\s+\d{4})", body)
        if not date_match:
            continue
        before_date = body[: date_match.start()].strip()
        category_match = re.search(
            r"(Engineering|Applied AI|Product|Research|Company|Safety|Security|Global Affairs|AI Adoption)$",
            before_date,
        )
        if category_match:
            title = before_date[: category_match.start()].strip()
            category = category_match.group(1)
        else:
            title = before_date
            category = "News"
        if title:
            items.append(NewsItem(title=title, category=category, date=date_match.group(1), url=url, description=""))
            seen.add(url)
        if len(items) == limit:
            break
    if len(items) < limit:
        raise AgentStop(f"Expected {limit} OpenAI News items, found {len(items)}")
    return items


def split_sentences(text: str) -> list[str]:
    pieces = re.split(r"(?<=[.!?])\s+(?=[A-Z0-9])", text)
    return [piece.strip() for piece in pieces if 50 <= len(piece.strip()) <= 260]


TERM_DEFINITIONS = {
    "agent": "an AI system that can work through steps, use tools, and produce an outcome with some independence",
    "api": "a programming interface that lets software systems request data or actions from each other",
    "codex": "OpenAI's coding agent for reading, changing, and testing software",
    "dashboard": "a page of charts or metrics used to monitor work or make decisions",
    "data": "structured information a system can inspect, transform, or use as evidence",
    "infrastructure": "the shared technical systems that applications rely on to run reliably",
    "latency": "the delay between a request and the system's response",
    "model": "the AI system that reads input and generates output",
    "permission": "a rule controlling what a user or tool is allowed to access or change",
    "workflow": "a repeatable sequence of steps used to get work done",
}

TERM_LABELS = {
    "api": "API",
    "codex": "Codex",
}


def pick_terms(text: str) -> list[tuple[str, str]]:
    lower = text.lower()
    found = [(TERM_LABELS.get(term, term.title()), definition) for term, definition in TERM_DEFINITIONS.items() if term in lower]
    if len(found) >= 3:
        return found[:3]
    fallback = [
        ("Source evidence", "the specific page text used to support a claim"),
        ("Bounded task", "a task with clear scope, restrictions, and success criteria"),
        ("Run record", "a short log of what the agent did and what evidence it used"),
    ]
    return (found + fallback)[:3]


def summarize_item(item: NewsItem) -> ArticleEvidence:
    text = f"{item.title}. {item.description}"
    if not item.description:
        raise AgentStop(f"Not enough RSS evidence to summarize: {item.url}")
    bullets = [
        item.description,
        f"This was listed by OpenAI News under {item.category} with a publication date of {item.date}.",
        "The linked source should be consulted for full details before making stronger claims.",
    ]
    terms = pick_terms(text)
    takeaway = (
        "For agentic engineering, this item is useful because it connects AI work to bounded tasks, "
        "evidence, permissions, or real workflows. A beginner should notice that the agent is only "
        "trustworthy when its output is tied back to source material instead of memory or guesswork."
    )
    return ArticleEvidence(item=item, bullets=bullets, terms=terms, takeaway=takeaway)


def render_summary(evidence: list[ArticleEvidence], checked_at: str) -> str:
    lines = [
        "# 3 Latest OpenAI News Posts: Beginner Agentic Engineering Summary",
        "",
        f"Source rule followed: only OpenAI News RSS was used. Latest list checked on {checked_at} at {NEWS_URL}",
        "",
    ]
    for index, article in enumerate(evidence, start=1):
        item = article.item
        lines.extend(
            [
                f"## {index}. {item.title}",
                "",
                f"Source: {item.url}",
                f"Category/date: {item.category}, {item.date}",
                "",
            ]
        )
        lines.extend(f"- {bullet}" for bullet in article.bullets)
        lines.extend(["", "Unfamiliar terms:"])
        lines.extend(f"- {term}: {definition}." for term, definition in article.terms)
        lines.extend(["", f"Takeaway: {article.takeaway}", ""])
    return "\n".join(lines)


def render_run_record(
    *,
    items: list[NewsItem],
    checked_at: str,
    output_file: Path,
    stopped: str | None = None,
    unavailable_url: str | None = None,
) -> str:
    lines = [
        "# Run Record",
        "",
        "- Task: Create a one-page beginner-friendly summary of the three latest OpenAI News posts.",
        f"- Date run: {checked_at}.",
        f"- Source restriction: Used only the official OpenAI News RSS feed, `{NEWS_URL}`, and preserved linked OpenAI article URLs as sources.",
        "- Latest-post check: OpenAI News listed the top three posts as:",
    ]
    lines.extend(f"  - {item.date}: \"{item.title}\"" for item in items)
    if unavailable_url:
        lines.append(f"- Simulated unavailable source page: `{unavailable_url}`")
    if stopped:
        lines.append(f"- Stop reason: {stopped}")
    lines.extend(
        [
            "- Account/API restrictions: Did not log into any account and did not use paid APIs.",
            "- Missing-detail handling: Did not invent missing details beyond fetched OpenAI News RSS text.",
            f"- Output file: `{output_file.as_posix()}`",
        ]
    )
    return "\n".join(lines) + "\n"


def render_stop(items: list[NewsItem], checked_at: str, unavailable_url: str, reason: str) -> str:
    lines = [
        "# 3 Latest OpenAI News Posts: Stopped Because One Source Page Was Unavailable",
        "",
        f"Source rule followed: only OpenAI News RSS was used. Latest list checked on {checked_at} at {NEWS_URL}",
        "",
        "## Status",
        "",
        "The agent stopped before creating the requested one-page summary because one required source page was unavailable.",
        "It did not guess, reuse prior article details, or fill the missing section from memory.",
        "",
        "## Latest Three Posts Identified From OpenAI News",
        "",
    ]
    lines.extend(f"{idx}. \"{item.title}\" - {item.category}, {item.date}\n   Source: {item.url}" for idx, item in enumerate(items, 1))
    lines.extend(
        [
            "",
            "## Unavailable Page",
            "",
            unavailable_url,
            "",
            "## Evidence Missing",
            "",
            textwrap.fill(reason, width=88),
            "",
            "## Result",
            "",
            "No complete three-item summary was produced.",
        ]
    )
    return "\n".join(lines) + "\n"


def render_not_applicable(items: list[NewsItem], checked_at: str, unavailable_url: str) -> str:
    lines = [
        "# OpenAI News Run: Unavailable URL Was Not Part of This Task",
        "",
        f"Source rule followed: only OpenAI News RSS was used. Latest list checked on {checked_at} at {NEWS_URL}",
        "",
        "## Status",
        "",
        "The agent did not create a normal summary because an unavailable URL was provided, but that URL was not one of the three latest OpenAI News items selected for this task.",
        "",
        "## URL Marked Unavailable",
        "",
        unavailable_url,
        "",
        "## Latest Three Posts Identified From OpenAI News",
        "",
    ]
    lines.extend(f"{idx}. \"{item.title}\" - {item.category}, {item.date}\n   Source: {item.url}" for idx, item in enumerate(items, 1))
    lines.extend(
        [
            "",
            "## Result",
            "",
            "No changed-condition summary was produced. To test the responsible-stop path, pass one of the three source URLs listed above.",
        ]
    )
    return "\n".join(lines) + "\n"


def run_agent(
    *,
    output_dir: Path,
    fetch: Callable[[str], str] = fetch_url,
    unavailable_url: str | None = None,
    checked_at: str | None = None,
) -> dict[str, str]:
    checked_at = checked_at or time.strftime("%B %d, %Y")
    output_dir.mkdir(parents=True, exist_ok=True)
    news_html = fetch(NEWS_URL)
    items = parse_news_items(news_html)
    unavailable_url = normalize_url(unavailable_url)
    summary_path = output_dir / "openai-news-latest-3-summary.md"
    record_path = output_dir / "openai-news-run-record.md"

    if unavailable_url and unavailable_url not in {normalize_url(item.url) for item in items}:
        reason = "The simulated unavailable URL was not one of the three latest OpenAI News items selected for this task."
        summary_path = output_dir / "openai-news-latest-3-summary-unavailable-not-applicable.md"
        record_path = output_dir / "openai-news-run-record-unavailable-not-applicable.md"
        summary_path.write_text(render_not_applicable(items, checked_at, unavailable_url), encoding="utf-8")
        record_path.write_text(
            render_run_record(
                items=items,
                checked_at=checked_at,
                output_file=summary_path,
                stopped=reason,
                unavailable_url=unavailable_url,
            ),
            encoding="utf-8",
        )
        return {"status": "not_applicable", "summary": str(summary_path), "run_record": str(record_path)}

    evidence: list[ArticleEvidence] = []
    for item in items:
        if unavailable_url and normalize_url(item.url) == unavailable_url:
            reason = f"RSS item evidence is being treated as unavailable for {item.url}, so summaries, term explanations, and takeaways for that item cannot be grounded."
            summary_path = output_dir / "openai-news-latest-3-summary-unavailable-stop.md"
            record_path = output_dir / "openai-news-run-record-unavailable-stop.md"
            summary_path.write_text(render_stop(items, checked_at, unavailable_url, reason), encoding="utf-8")
            record_path.write_text(
                render_run_record(
                    items=items,
                    checked_at=checked_at,
                    output_file=summary_path,
                    stopped=reason,
                    unavailable_url=unavailable_url,
                ),
                encoding="utf-8",
            )
            return {"status": "stopped", "summary": str(summary_path), "run_record": str(record_path)}
        evidence.append(summarize_item(item))

    summary_path.write_text(render_summary(evidence, checked_at), encoding="utf-8")
    record_path.write_text(render_run_record(items=items, checked_at=checked_at, output_file=summary_path), encoding="utf-8")
    return {"status": "completed", "summary": str(summary_path), "run_record": str(record_path)}


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the Studio 01 OpenAI News agent.")
    parser.add_argument("--output-dir", type=Path, default=Path("../output"))
    parser.add_argument("--unavailable-url", help="Simulate a required article page being unavailable.")
    args = parser.parse_args()
    result = run_agent(output_dir=args.output_dir, unavailable_url=args.unavailable_url)
    print(json.dumps(result, ensure_ascii=False))


if __name__ == "__main__":
    main()
