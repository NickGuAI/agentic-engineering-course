"""Weekly AI news digest scraper for Studio 01.

This script fetches public Anthropic and OpenAI news pages, extracts likely
article links, ranks them with an Agentic Engineering relevance heuristic, and
writes a markdown digest plus a JSONL run trace into ../outputs.

It does not use credentials, bypass access controls, or enable real scheduling.
"""
from __future__ import annotations

import argparse
import html
import json
import re
import sys
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Iterable
from urllib.error import HTTPError, URLError
from urllib.parse import urljoin, urlparse
from urllib.request import Request, urlopen


SOURCES = [
    {
        "name": "Anthropic News",
        "url": "https://www.anthropic.com/news",
        "allowed_prefixes": ["/news/"],
    },
    {
        "name": "Anthropic Engineering",
        "url": "https://www.anthropic.com/engineering",
        "allowed_prefixes": ["/engineering/"],
    },
    {
        "name": "OpenAI News",
        "url": "https://openai.com/news/",
        "allowed_prefixes": ["/news/"],
    },
]

INTEREST_KEYWORDS = {
    "agent": 6,
    "agents": 6,
    "agentic": 6,
    "coding": 5,
    "developer": 5,
    "api": 5,
    "model": 4,
    "evaluation": 4,
    "eval": 4,
    "safety": 4,
    "reliability": 4,
    "tool": 3,
    "tools": 3,
    "workflow": 3,
    "engineering": 3,
    "alignment": 2,
    "research": 2,
    "release": 2,
}

CATEGORY_SLUGS = {
    "announcements",
    "api",
    "chatgpt",
    "company",
    "engineering",
    "product",
    "research",
    "safety-alignment",
    "safety",
    "safety-and-alignment",
    "sora",
    "stories",
}


@dataclass(frozen=True)
class Article:
    source: str
    title: str
    url: str
    date: str
    score: int
    reason: str


def fetch(url: str, timeout: int = 20) -> tuple[str | None, str | None]:
    request = Request(
        url,
        headers={
            "User-Agent": (
                "Mozilla/5.0 (compatible; Studio01AINewsDigest/1.0; "
                "+https://course.nickgu.me/)"
            )
        },
    )
    try:
        with urlopen(request, timeout=timeout) as response:
            data = response.read()
            try:
                return data.decode("utf-8"), None
            except UnicodeDecodeError:
                charset = response.headers.get_content_charset() or "utf-8"
                return data.decode(charset, errors="replace"), None
    except (HTTPError, URLError, TimeoutError) as exc:
        return None, str(exc)


def clean_text(value: str) -> str:
    value = re.sub(r"<[^>]+>", " ", value)
    value = html.unescape(value)
    value = value.replace("’", "'").replace("‘", "'").replace("“", '"').replace("”", '"')
    value = value.replace("–", "-").replace("—", "-")
    value = value.replace("â€™", "'").replace("â€œ", '"').replace("â€\u009d", '"')
    value = value.replace("â€“", "-").replace("â€”", "-")
    value = re.sub(r"\s+", " ", value)
    return value.strip(" -|\t\r\n")


def extract_date(text: str) -> str:
    patterns = [
        r"\b(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Sept|Oct|Nov|Dec)[a-z]*\.?\s+\d{1,2},\s+\d{4}\b",
        r"\b\d{4}-\d{2}-\d{2}\b",
    ]
    for pattern in patterns:
        match = re.search(pattern, text, flags=re.IGNORECASE)
        if match:
            return match.group(0)
    return "date not found"


def title_from_url(url: str) -> str:
    slug = urlparse(url).path.rstrip("/").split("/")[-1]
    words = slug.replace("-", " ").replace("_", " ").split()
    small_words = {"a", "an", "and", "as", "for", "from", "in", "of", "on", "the", "to", "with"}
    titled = []
    for index, word in enumerate(words):
        if word.lower() in {"ai", "api", "gpt"}:
            titled.append(word.upper())
        elif index > 0 and word.lower() in small_words:
            titled.append(word.lower())
        else:
            titled.append(word.capitalize())
    return " ".join(titled)


def clean_title(raw_title: str, url: str) -> str:
    title = clean_text(raw_title)
    title = re.sub(
        r"\b(Announcements|Company|Engineering|Product|Research|Safety|Stories)\b",
        " ",
        title,
        flags=re.IGNORECASE,
    )
    title = re.sub(
        r"\b(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Sept|Oct|Nov|Dec)[a-z]*\.?\s+\d{1,2},\s+\d{4}\b",
        " ",
        title,
        flags=re.IGNORECASE,
    )
    title = re.sub(r"\b\d{4}-\d{2}-\d{2}\b", " ", title)
    title = clean_text(title)
    if len(title) > 90 or len(title) < 8:
        return title_from_url(url)
    return title


def score_title(title: str, source_name: str) -> tuple[int, str]:
    lowered = title.lower()
    matched: list[str] = []
    score = 0
    for keyword, weight in INTEREST_KEYWORDS.items():
        if re.search(rf"\b{re.escape(keyword)}\b", lowered):
            score += weight
            matched.append(keyword)
    if "Engineering" in source_name:
        score += 2
        matched.append("engineering source")
    if not matched:
        return 1, "General AI update; relevance should be checked manually."
    return score, "Matches: " + ", ".join(sorted(set(matched)))


def is_allowed_article(source: dict[str, object], href: str) -> bool:
    parsed = urlparse(href)
    source_host = urlparse(str(source["url"])).netloc
    if parsed.netloc and parsed.netloc != source_host:
        return False
    path = parsed.path
    slug = path.rstrip("/").split("/")[-1]
    if slug in CATEGORY_SLUGS:
        return False
    return any(path.startswith(prefix) and path.rstrip("/") != prefix.rstrip("/") for prefix in source["allowed_prefixes"])


def extract_articles(source: dict[str, object], page_html: str, limit: int) -> list[Article]:
    seen: set[str] = set()
    articles: list[Article] = []
    anchor_pattern = re.compile(
        r"<a\b[^>]*href=[\"'](?P<href>[^\"']+)[\"'][^>]*>(?P<body>.*?)</a>",
        flags=re.IGNORECASE | re.DOTALL,
    )
    for match in anchor_pattern.finditer(page_html):
        href = html.unescape(match.group("href"))
        full_url = urljoin(str(source["url"]), href)
        if full_url in seen or not is_allowed_article(source, full_url):
            continue
        title = clean_title(match.group("body"), full_url)
        if len(title) < 8:
            continue
        nearby = page_html[max(0, match.start() - 500) : min(len(page_html), match.end() + 500)]
        date = extract_date(clean_text(nearby))
        score, reason = score_title(title, str(source["name"]))
        seen.add(full_url)
        articles.append(
            Article(
                source=str(source["name"]),
                title=title,
                url=full_url,
                date=date,
                score=score,
                reason=reason,
            )
        )
        if len(articles) >= limit:
            break
    return articles


def rank_articles(articles: Iterable[Article], limit: int) -> list[Article]:
    return sorted(articles, key=lambda item: (-item.score, item.source, item.title))[:limit]


def render_markdown(
    articles: list[Article],
    events: list[dict[str, object]],
    generated_at: str,
    partial: bool,
) -> str:
    lines = [
        "# Weekly AI News Digest",
        "",
        f"Generated: {generated_at}",
        "",
        "Schedule target: Monday 7:00 AM Eastern Time",
        "",
        "## Sources Checked",
        "",
    ]
    for event in events:
        status = "ok" if event["ok"] else "failed"
        lines.append(f"- {event['source']}: {event['url']} ({status})")
    lines.extend(
        [
            "",
            "## Executive Summary",
            "",
        ]
    )
    if not articles:
        lines.append("No candidate articles were extracted. Check the source pages manually or adjust the scraper.")
    else:
        lines.append(
            "The most relevant updates are ranked by a simple Agentic Engineering heuristic that favors agents, "
            "developer tooling, models, evaluation, safety, reliability, and engineering lessons."
        )
    if partial:
        lines.append("")
        lines.append("This digest is partial because at least one source could not be accessed.")
    lines.extend(["", "## Ranked Updates", ""])
    lines.append("| Rank | Source | Date | Title | Why It Matters | Link |")
    lines.append("| --- | --- | --- | --- | --- | --- |")
    for index, article in enumerate(articles, start=1):
        lines.append(
            f"| {index} | {article.source} | {article.date} | {article.title} | "
            f"{article.reason} | [source]({article.url}) |"
        )
    lines.extend(
        [
            "",
            "## Worth Reading Fully",
            "",
        ]
    )
    for article in articles[:3]:
        lines.append(f"- {article.title} ({article.source}): {article.url}")
    lines.extend(
        [
            "",
            "## Run Notes",
            "",
            "- Source facts are the article titles, links, source names, and dates when found.",
            "- Relevance notes are heuristic interpretations by the script.",
            "- The script does not enable scheduling; use an external scheduler only after approval.",
        ]
    )
    return "\n".join(lines) + "\n"


def write_jsonl(path: Path, events: list[dict[str, object]]) -> None:
    path.write_text("".join(json.dumps(event, ensure_ascii=False) + "\n" for event in events), encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description="Fetch AI news pages and write a weekly digest.")
    parser.add_argument("--output-dir", type=Path, default=Path(__file__).resolve().parents[1] / "outputs")
    parser.add_argument("--per-source", type=int, default=8)
    parser.add_argument("--top", type=int, default=10)
    args = parser.parse_args()

    generated_at = datetime.now().astimezone().isoformat(timespec="seconds")
    events: list[dict[str, object]] = []
    all_articles: list[Article] = []

    for source in SOURCES:
        page_html, error = fetch(str(source["url"]))
        event: dict[str, object] = {
            "time": datetime.now().astimezone().isoformat(timespec="seconds"),
            "source": source["name"],
            "url": source["url"],
            "ok": error is None,
            "error": error,
            "articles_found": 0,
        }
        if page_html is not None:
            articles = extract_articles(source, page_html, args.per_source)
            all_articles.extend(articles)
            event["articles_found"] = len(articles)
        events.append(event)

    ranked = rank_articles(all_articles, args.top)
    partial = any(not event["ok"] for event in events)
    args.output_dir.mkdir(parents=True, exist_ok=True)
    digest_path = args.output_dir / "weekly-ai-news-digest.md"
    trace_path = args.output_dir / "weekly-ai-news-trace.jsonl"

    digest_path.write_text(render_markdown(ranked, events, generated_at, partial), encoding="utf-8")
    write_jsonl(trace_path, events)

    print(json.dumps({"digest": str(digest_path), "trace": str(trace_path), "articles": len(ranked)}, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
