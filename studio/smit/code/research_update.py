#!/usr/bin/env python3
"""Filter verified article notes into a source-bounded Markdown update.

This small implementation does not crawl websites or generate research claims.
Article notes must first be collected and checked against the approved sources;
this script applies the date/source/deduplication rules and writes the report.
"""
from __future__ import annotations

import argparse
import json
import re
from datetime import date, timedelta
from pathlib import Path
from urllib.parse import urlparse

ALLOWED_SOURCES = {"Anthropic News", "Anthropic Engineering", "OpenAI News"}
REQUIRED_FIELDS = {"source", "date", "title", "summary", "why_it_matters", "url"}


def normalize_title(value: str) -> str:
    return re.sub(r"\W+", " ", value.casefold()).strip()


def load_articles(path: Path) -> list[dict[str, str]]:
    rows = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(rows, list):
        raise ValueError("Input must be a JSON list of article records")
    for number, row in enumerate(rows, start=1):
        if not isinstance(row, dict) or not REQUIRED_FIELDS <= row.keys():
            raise ValueError(f"Record {number} is missing required fields")
        if row["source"] not in ALLOWED_SOURCES:
            raise ValueError(f"Record {number} uses an unapproved source")
        date.fromisoformat(row["date"])
        parsed = urlparse(row["url"])
        if parsed.scheme != "https" or not parsed.netloc:
            raise ValueError(f"Record {number} has an invalid HTTPS link")
        for field in REQUIRED_FIELDS:
            if not isinstance(row[field], str) or not row[field].strip():
                raise ValueError(f"Record {number} has an empty {field}")
    return rows


def select_articles(rows: list[dict[str, str]], as_of: date, days: int) -> list[dict[str, str]]:
    if days < 1:
        raise ValueError("--days must be at least 1")
    start = as_of - timedelta(days=days - 1)
    selected: dict[str, dict[str, str]] = {}
    for row in rows:
        published = date.fromisoformat(row["date"])
        if start <= published <= as_of:
            key = normalize_title(row["title"])
            selected.setdefault(key, row)
    return sorted(selected.values(), key=lambda row: (row["date"], row["title"]), reverse=True)[:5]


def render_report(rows: list[dict[str, str]], as_of: date, days: int) -> str:
    start = as_of - timedelta(days=days - 1)
    lines = [
        "# Weekly AI research update",
        "",
        f"**Run date:** {as_of.isoformat()}  ",
        f"**Coverage:** {start.isoformat()}–{as_of.isoformat()} ({days}-day lookback)  ",
        "**Approved sources:** Anthropic News, Anthropic Engineering, OpenAI News",
        "",
        "## Updates",
        "",
    ]
    if not rows:
        lines += ["No qualifying updates were present in the verified input records.", ""]
    for row in rows:
        lines += [
            f"### {row['title']}",
            "",
            f"- **Source/date:** {row['source']} — {row['date']}",
            f"- **Summary:** {row['summary']}",
            f"- **Why it matters:** {row['why_it_matters']}",
            f"- **Link:** {row['url']}",
            "",
        ]
    lines += [
        "## Check",
        "",
        f"- Updates found: {len(rows)} (target: 3–5).",
        "- The script filters and formats supplied, verified notes; it does not fetch pages or independently verify article claims.",
        "- If fewer than three records qualify, the shortfall is reported without adding older or unapproved material.",
        "",
    ]
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, default=Path(__file__).with_name("articles.json"))
    parser.add_argument("--as-of", type=date.fromisoformat, default=date.today())
    parser.add_argument("--days", type=int, default=7)
    parser.add_argument("--output", type=Path, default=Path("research-update.md"))
    args = parser.parse_args()

    articles = load_articles(args.input)
    selected = select_articles(articles, args.as_of, args.days)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(render_report(selected, args.as_of, args.days), encoding="utf-8")
    print(f"Wrote {len(selected)} update(s) for {args.as_of} with a {args.days}-day lookback to {args.output}")


if __name__ == "__main__":
    main()
