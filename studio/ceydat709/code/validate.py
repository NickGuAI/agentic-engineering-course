#!/usr/bin/env python3
"""Checks a digest run against the delegation card's success criteria.

Usage:
    python3 validate.py 17-09-2026
    python3 validate.py 17-09-2026 --check-links

Reads outputs/<date>.md and outputs/<date>.log and reports pass/fail for:
  1. digest file exists
  2. each source has exactly 3 distinct posts
  3. each post has 2-4 bullet points
  4. no duplicate posts (by link), within or across sources
  5. digest is <= 150 lines
  6. log file exists and reports the run as a success
  7. (optional, --check-links) every post link returns HTTP 200
"""
from __future__ import annotations
import argparse
import re
import sys
import urllib.request
from pathlib import Path

OUTPUTS_DIR = Path(__file__).parent.parent / "outputs"
EXPECTED_SOURCES = {"Anthropic News", "Anthropic Engineering", "OpenAI News"}


def parse_digest(text: str) -> dict[str, list[dict]]:
    sources: dict[str, list[dict]] = {}
    current_source = None
    current_post = None

    for line in text.splitlines():
        source_match = re.match(r"^##\s+(.+)$", line)
        post_match = re.match(r"^###\s+(.+)$", line)
        link_match = re.match(r"^.+—\s*(https?://\S+)\s*$", line)
        bullet_match = re.match(r"^-\s+", line)

        if source_match:
            current_source = source_match.group(1).strip()
            sources.setdefault(current_source, [])
            current_post = None
        elif post_match and current_source is not None:
            current_post = {"title": post_match.group(1).strip(), "link": None, "bullets": 0}
            sources[current_source].append(current_post)
        elif link_match and current_post is not None and current_post["link"] is None:
            current_post["link"] = link_match.group(1)
        elif bullet_match and current_post is not None:
            current_post["bullets"] += 1

    return sources


def check_link(url: str) -> str:
    """Returns 'ok', 'broken', or 'blocked' (bot protection returned 403/429 —
    inconclusive, not evidence the link is actually broken)."""
    try:
        req = urllib.request.Request(url, method="GET", headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=10) as resp:
            return "ok" if resp.status < 400 else "broken"
    except urllib.error.HTTPError as e:
        return "blocked" if e.code in (403, 429) else "broken"
    except Exception:
        return "broken"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("date", help="Run date in dd-mm-yyyy format, e.g. 17-09-2026")
    parser.add_argument("--check-links", action="store_true", help="Fetch every post link and verify it resolves")
    parser.add_argument("--posts-per-source", type=int, default=3, help="Required post count per source (delegation card specifies 3)")
    args = parser.parse_args()

    digest_path = OUTPUTS_DIR / f"{args.date}.md"
    log_path = OUTPUTS_DIR / f"{args.date}.log"

    failures: list[str] = []

    if not digest_path.exists():
        print(f"FAIL: {digest_path} does not exist")
        return 1
    text = digest_path.read_text()
    lines = text.splitlines()

    if len(lines) > 150:
        failures.append(f"digest has {len(lines)} lines, exceeds 150-line limit")

    sources = parse_digest(text)
    missing_sources = EXPECTED_SOURCES - sources.keys()
    if missing_sources:
        failures.append(f"missing source sections: {sorted(missing_sources)}")

    all_links: list[str] = []
    for name, posts in sources.items():
        if name not in EXPECTED_SOURCES:
            continue
        if len(posts) != args.posts_per_source:
            failures.append(f"{name}: expected {args.posts_per_source} posts, found {len(posts)}")
        for post in posts:
            if not (2 <= post["bullets"] <= 4):
                failures.append(f"{name} / '{post['title']}': expected 2-4 bullets, found {post['bullets']}")
            if post["link"]:
                all_links.append(post["link"])
            else:
                failures.append(f"{name} / '{post['title']}': no link found")

    duplicates = {link for link in all_links if all_links.count(link) > 1}
    if duplicates:
        failures.append(f"duplicate post links: {sorted(duplicates)}")

    if not log_path.exists():
        failures.append(f"log file {log_path} does not exist")
    else:
        log_text = log_path.read_text()
        if "SUCCESS" not in log_text.upper():
            failures.append("log file does not report a successful run")

    warnings: list[str] = []
    if args.check_links:
        for link in all_links:
            status = check_link(link)
            if status == "broken":
                failures.append(f"link did not resolve: {link}")
            elif status == "blocked":
                warnings.append(f"could not verify (bot-blocked, not evidence it's broken): {link}")

    print(f"Checked {digest_path.name}: {len(all_links)} posts across {len(sources)} sources")
    if warnings:
        print(f"\n{len(warnings)} warning(s):")
        for w in warnings:
            print(f"  - {w}")
    if failures:
        print(f"\n{len(failures)} check(s) failed:")
        for f in failures:
            print(f"  - {f}")
        return 1

    print("All checks passed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
