#!/usr/bin/env python3
"""Run a bounded AI-news pass once or for an 8:00 a.m. Eastern delivery."""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time
from contextlib import contextmanager
from datetime import date, datetime, time as clock_time, timedelta
from pathlib import Path
from typing import Any, Iterator
from urllib.parse import urlparse
from zoneinfo import ZoneInfo


EASTERN = ZoneInfo("America/New_York")
DELIVERY_HOUR = 8
START_LEAD = timedelta(minutes=1)
DELIVERY_GRACE = timedelta(minutes=1)
LOOKBACK = timedelta(hours=24)
MAX_STORIES = 5
TIMEOUT_SECONDS = 110
DELIVERY_BUDGET_SECONDS = int((START_LEAD + DELIVERY_GRACE).total_seconds())

WORKSPACE = Path(__file__).resolve().parent.parent
OUTPUTS = WORKSPACE / "outputs"
SCHEMA = Path(__file__).with_name("report_schema.json")
LOCK = OUTPUTS / ".lock"

REQUIRED_SOURCES = {
    "Anthropic News": "https://www.anthropic.com/news",
    "Anthropic Engineering": "https://www.anthropic.com/engineering",
    "OpenAI News": "https://openai.com/news/",
    "X.com": "https://x.com/",
}

PRIMARY_SOURCE_HOSTS = {
    "anthropic.com",
    "www.anthropic.com",
    "openai.com",
    "www.openai.com",
    "x.com",
    "www.x.com",
    "arxiv.org",
    "openreview.net",
    "proceedings.mlr.press",
    "aclanthology.org",
    "nature.com",
    "www.nature.com",
    "science.org",
    "www.science.org",
    "github.com",
    "www.github.com",
}


class JobError(RuntimeError):
    """The research pass could not produce a verified briefing."""


def eastern_now() -> datetime:
    return datetime.now(EASTERN)


def iso_minutes(value: datetime) -> str:
    return value.isoformat(timespec="minutes")


def run_id(value: datetime) -> str:
    return value.strftime("%Y%m%dT%H%M%S%z")


def next_scheduled_time(now: datetime) -> datetime:
    """Return the next research start for an 8:00 a.m. Eastern delivery."""
    local = now.astimezone(EASTERN)
    delivery = datetime.combine(
        local.date(), clock_time(DELIVERY_HOUR), tzinfo=EASTERN
    )
    target = delivery - START_LEAD
    if local >= target:
        delivery = datetime.combine(
            local.date() + timedelta(days=1),
            clock_time(DELIVERY_HOUR),
            tzinfo=EASTERN,
        )
        target = delivery - START_LEAD
    return target


def build_prompt(window_start: datetime, window_end: datetime) -> str:
    start = iso_minutes(window_start)
    end = iso_minutes(window_end)
    return f"""Perform one bounded research pass for an undergraduate student who follows AI.

Research window: {start} inclusive through {end} inclusive. This is the previous 24 hours in America/New_York.

Use live web search and open the original pages. You must inspect all four of these sources:
1. Anthropic News: https://www.anthropic.com/news
2. Anthropic Engineering: https://www.anthropic.com/engineering
3. OpenAI News: https://openai.com/news/
4. X.com: public, first-party posts from relevant AI labs, researchers, or paper authors

After those four checks, make one bounded paper scan of https://www.anthropic.com/research and https://openai.com/research/. This extra scan exists because a notable research result may not appear on a newsroom or engineering index. Mention any useful result in the closest matching source-check details; do not add extra source-check rows.

Selection rules:
- Return zero to {MAX_STORIES} stories. Never add filler to reach a quota.
- Include only work first published or substantially updated inside the stated window.
- Prefer technically interesting work, especially papers, evaluations, systems work, or findings a student could learn from.
- Product news can qualify when it changes what students or builders can do.
- Exclude ads, sponsored posts, lead-generation pages, repost farms, rumors, and promotional threads without primary evidence.
- Use the original article, paper, or first-party post as each story URL. Do not use search-result or aggregator URLs.
- Open each selected source and base the summary on its contents, not its search snippet.
- If a page supplies an exact time, set date_precision to "timestamp" and published_at to an ISO 8601 timestamp with an offset.
- If a page supplies only a date, set date_precision to "date_only" and published_at to YYYY-MM-DD. A date-only item can qualify only when that date overlaps the window. Do not invent a time.
- If X.com cannot be read without signing in or cannot be verified, mark that source unavailable. Do not replace it with hearsay.

Writing rules:
- The summary must be one factual sentence.
- The description must be short, concrete, and useful to this student. Explain the mechanism, result, or practical significance.
- Avoid hype, vague claims, and press-release language.
- Every source-check entry must state what was found or why the source was unavailable.
- Return only JSON matching the supplied schema. Do not wrap it in Markdown fences.
"""


def _clean_text(value: Any, field: str, *, limit: int) -> str:
    if not isinstance(value, str):
        raise JobError(f"{field} must be text")
    cleaned = " ".join(value.split())
    if not cleaned:
        raise JobError(f"{field} cannot be empty")
    if len(cleaned) > limit:
        raise JobError(f"{field} exceeds {limit} characters")
    return cleaned


def _https_url(value: Any, field: str, *, primary_only: bool) -> str:
    url = _clean_text(value, field, limit=2_000)
    parsed = urlparse(url)
    if parsed.scheme != "https" or not parsed.netloc or parsed.username or parsed.password:
        raise JobError(f"{field} must be a public HTTPS URL")
    hostname = (parsed.hostname or "").lower()
    if primary_only and hostname not in PRIMARY_SOURCE_HOSTS:
        raise JobError(f"{field} is not on the primary-source allowlist: {hostname}")
    if any(character.isspace() for character in url):
        raise JobError(f"{field} cannot contain whitespace")
    return url


def _parse_timestamp(value: str) -> datetime:
    normalized = value[:-1] + "+00:00" if value.endswith("Z") else value
    try:
        parsed = datetime.fromisoformat(normalized)
    except ValueError as exc:
        raise JobError(f"Invalid ISO 8601 timestamp: {value}") from exc
    if parsed.tzinfo is None:
        raise JobError(f"Timestamp lacks a UTC offset: {value}")
    return parsed.astimezone(EASTERN)


def validate_payload(
    payload: Any,
    window_start: datetime,
    window_end: datetime,
) -> dict[str, Any]:
    """Validate model output before it can replace the visible briefing."""
    if not isinstance(payload, dict) or set(payload) != {"source_checks", "stories"}:
        raise JobError("Response must contain only source_checks and stories")

    checks = payload["source_checks"]
    if not isinstance(checks, list) or len(checks) != len(REQUIRED_SOURCES):
        raise JobError("Response must contain exactly four source checks")

    clean_checks: list[dict[str, str]] = []
    seen_sources: set[str] = set()
    for index, check in enumerate(checks, 1):
        if not isinstance(check, dict) or set(check) != {"source", "status", "details", "url"}:
            raise JobError(f"Source check {index} has unexpected fields")
        source = _clean_text(check["source"], f"source check {index} source", limit=80)
        if source not in REQUIRED_SOURCES or source in seen_sources:
            raise JobError(f"Source check {index} is missing, unknown, or duplicated: {source}")
        status = check["status"]
        if status not in {"checked", "unavailable"}:
            raise JobError(f"Source check {index} has invalid status")
        clean_checks.append(
            {
                "source": source,
                "status": status,
                "details": _clean_text(check["details"], f"source check {index} details", limit=500),
                "url": _https_url(check["url"], f"source check {index} URL", primary_only=False),
            }
        )
        seen_sources.add(source)
    if seen_sources != set(REQUIRED_SOURCES):
        raise JobError("Not every required source was checked")

    stories = payload["stories"]
    if not isinstance(stories, list) or len(stories) > MAX_STORIES:
        raise JobError(f"Response must contain at most {MAX_STORIES} stories")

    clean_stories: list[dict[str, str]] = []
    seen_urls: set[str] = set()
    for index, story in enumerate(stories, 1):
        expected = {
            "headline",
            "source_name",
            "published_at",
            "date_precision",
            "kind",
            "summary",
            "description",
            "url",
        }
        if not isinstance(story, dict) or set(story) != expected:
            raise JobError(f"Story {index} has unexpected fields")

        precision = story["date_precision"]
        published_at = _clean_text(story["published_at"], f"story {index} published_at", limit=80)
        if precision == "timestamp":
            published = _parse_timestamp(published_at)
            if not window_start <= published <= window_end:
                raise JobError(f"Story {index} timestamp falls outside the research window")
        elif precision == "date_only":
            try:
                published_date = date.fromisoformat(published_at)
            except ValueError as exc:
                raise JobError(f"Story {index} date must use YYYY-MM-DD") from exc
            if not window_start.date() <= published_date <= window_end.date():
                raise JobError(f"Story {index} date falls outside the research window")
        else:
            raise JobError(f"Story {index} has invalid date_precision")

        kind = story["kind"]
        if kind not in {"news", "engineering", "paper", "official_post"}:
            raise JobError(f"Story {index} has invalid kind")
        url = _https_url(story["url"], f"story {index} URL", primary_only=True)
        if url in seen_urls:
            raise JobError(f"Story {index} duplicates an earlier URL")
        seen_urls.add(url)
        clean_stories.append(
            {
                "headline": _clean_text(story["headline"], f"story {index} headline", limit=180),
                "source_name": _clean_text(story["source_name"], f"story {index} source", limit=100),
                "published_at": published_at,
                "date_precision": precision,
                "kind": kind,
                "summary": _clean_text(story["summary"], f"story {index} summary", limit=360),
                "description": _clean_text(story["description"], f"story {index} description", limit=900),
                "url": url,
            }
        )

    return {"source_checks": clean_checks, "stories": clean_stories}


def render_markdown(
    payload: dict[str, Any],
    generated_at: datetime,
    window_start: datetime,
    window_end: datetime,
) -> str:
    lines = [
        "# AI news briefing",
        "",
        f"Generated: {iso_minutes(generated_at)}",
        f"Research window: {iso_minutes(window_start)} to {iso_minutes(window_end)}",
        "",
        "## Source check",
        "",
        "| Source | Status | What the pass found |",
        "| --- | --- | --- |",
    ]
    checks_by_name = {check["source"]: check for check in payload["source_checks"]}
    for source in REQUIRED_SOURCES:
        check = checks_by_name[source]
        details = check["details"].replace("|", "\\|")
        lines.append(f"| [{source}]({check['url']}) | {check['status']} | {details} |")

    lines.extend(["", "## Stories", ""])
    if not payload["stories"]:
        lines.extend(
            [
                "No qualifying stories were verified in this 24-hour window. That is a valid result, not a reason to add older filler.",
                "",
            ]
        )
    else:
        for index, story in enumerate(payload["stories"], 1):
            published = story["published_at"]
            if story["date_precision"] == "date_only":
                published += " (source gives a date but no publication time)"
            kind = story["kind"].replace("_", " ")
            lines.extend(
                [
                    f"### {index}. {story['headline']}",
                    "",
                    f"- Source: {story['source_name']}",
                    f"- Published: {published}",
                    f"- Type: {kind}",
                    f"- Summary: {story['summary']}",
                    f"- Link: [Original source]({story['url']})",
                    "",
                    story["description"],
                    "",
                ]
            )
    return "\n".join(lines)


def atomic_write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.{os.getpid()}.tmp")
    temporary.write_text(text, encoding="utf-8")
    os.replace(temporary, path)


def append_jsonl(path: Path, event: dict[str, Any]) -> None:
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(event, ensure_ascii=False, sort_keys=True) + "\n")


@contextmanager
def exclusive_run() -> Iterator[None]:
    OUTPUTS.mkdir(parents=True, exist_ok=True)
    try:
        descriptor = os.open(LOCK, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
    except FileExistsError as exc:
        raise JobError(f"Another pass appears to be running: {LOCK}") from exc
    try:
        os.write(descriptor, f"pid={os.getpid()}\n".encode())
        os.close(descriptor)
        yield
    finally:
        try:
            LOCK.unlink()
        except FileNotFoundError:
            pass


def resolve_codex_binary(requested: str | None) -> str:
    candidate = requested or os.environ.get("STUDIO01_CODEX_BIN") or "codex"
    resolved = shutil.which(candidate)
    if not resolved:
        raise JobError(f"Codex executable not found: {candidate}")
    return resolved


def run_once(*, codex_bin: str | None = None, now: datetime | None = None) -> Path:
    started = (now or eastern_now()).astimezone(EASTERN)
    window_start = started - LOOKBACK
    identifier = run_id(started)
    trace_path = OUTPUTS / f"trace-{identifier}.jsonl"
    stderr_path = OUTPUTS / f"stderr-{identifier}.log"
    record_path = OUTPUTS / f"run-{identifier}.json"
    briefing_path = OUTPUTS / f"briefing-{identifier}.md"
    prompt = build_prompt(window_start, started)
    metadata: dict[str, Any] = {
        "run_id": identifier,
        "status": "running",
        "started_at": started.isoformat(),
        "window_start": window_start.isoformat(),
        "window_end": started.isoformat(),
        "trace": trace_path.name,
    }

    with exclusive_run():
        append_jsonl(
            trace_path,
            {
                "type": "studio01.wrapper_start",
                "run_id": identifier,
                "started_at": started.isoformat(),
                "window_start": window_start.isoformat(),
                "window_end": started.isoformat(),
            },
        )
        try:
            executable = resolve_codex_binary(codex_bin)
            metadata["codex_binary"] = executable
            with tempfile.TemporaryDirectory(prefix="studio01-news-") as temp_dir:
                response_path = Path(temp_dir) / "response.json"
                command = [
                    executable,
                    "exec",
                    "--config",
                    'model_reasoning_effort="low"',
                    "--ephemeral",
                    "--sandbox",
                    "read-only",
                    "--color",
                    "never",
                    "--json",
                    "--output-schema",
                    str(SCHEMA),
                    "--output-last-message",
                    str(response_path),
                    "--cd",
                    str(WORKSPACE),
                    "-",
                ]
                completed = subprocess.run(
                    command,
                    input=prompt,
                    text=True,
                    capture_output=True,
                    timeout=TIMEOUT_SECONDS,
                    check=False,
                )
                with trace_path.open("a", encoding="utf-8") as trace:
                    trace.write(completed.stdout)
                    if completed.stdout and not completed.stdout.endswith("\n"):
                        trace.write("\n")
                atomic_write(stderr_path, completed.stderr)
                metadata["codex_exit_code"] = completed.returncode
                if completed.returncode != 0:
                    raise JobError(f"Codex exited with status {completed.returncode}")
                if not response_path.exists():
                    raise JobError("Codex returned no final response")
                try:
                    raw_payload = json.loads(response_path.read_text(encoding="utf-8"))
                except json.JSONDecodeError as exc:
                    raise JobError(f"Codex returned invalid JSON: {exc}") from exc

            payload = validate_payload(raw_payload, window_start, started)
            finished = eastern_now()
            markdown = render_markdown(payload, finished, window_start, started)
            atomic_write(briefing_path, markdown)
            atomic_write(OUTPUTS / "latest.md", markdown)
            metadata.update(
                {
                    "status": "succeeded",
                    "finished_at": finished.isoformat(),
                    "duration_seconds": round((finished - started).total_seconds(), 3),
                    "delivery_budget_seconds": DELIVERY_BUDGET_SECONDS,
                    "delivery_budget_met": (finished - started).total_seconds()
                    <= DELIVERY_BUDGET_SECONDS,
                    "briefing": briefing_path.name,
                    "story_count": len(payload["stories"]),
                    "source_count": len(payload["source_checks"]),
                }
            )
            append_jsonl(
                trace_path,
                {
                    "type": "studio01.wrapper_finish",
                    "run_id": identifier,
                    "status": "succeeded",
                    "briefing": briefing_path.name,
                    "story_count": len(payload["stories"]),
                },
            )
            atomic_write(record_path, json.dumps(metadata, indent=2, sort_keys=True) + "\n")
            return briefing_path
        except (JobError, OSError, subprocess.SubprocessError) as exc:
            finished = eastern_now()
            metadata.update(
                {
                    "status": "failed",
                    "finished_at": finished.isoformat(),
                    "duration_seconds": round((finished - started).total_seconds(), 3),
                    "error": str(exc),
                }
            )
            append_jsonl(
                trace_path,
                {
                    "type": "studio01.wrapper_finish",
                    "run_id": identifier,
                    "status": "failed",
                    "error": str(exc),
                },
            )
            atomic_write(record_path, json.dumps(metadata, indent=2, sort_keys=True) + "\n")
            raise JobError(str(exc)) from exc


def run_loop(*, codex_bin: str | None = None) -> None:
    """Sleep in the foreground and prepare each 8:00 a.m. Eastern briefing."""
    while True:
        now = eastern_now()
        target = next_scheduled_time(now)
        wait_seconds = max(0.0, (target - now).total_seconds())
        print(
            f"Waiting to start at {target.isoformat()} for the 8:00 a.m. delivery "
            f"({wait_seconds:.0f} seconds). "
            "Press Ctrl-C to stop.",
            flush=True,
        )
        time.sleep(wait_seconds)
        try:
            briefing = run_once(codex_bin=codex_bin)
            print(f"Published {briefing}", flush=True)
        except JobError as exc:
            print(f"Pass failed: {exc}", file=sys.stderr, flush=True)


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)
    for name in ("once", "loop"):
        command = subparsers.add_parser(name)
        command.add_argument(
            "--codex-bin",
            help="Codex executable name or path. STUDIO01_CODEX_BIN is also supported.",
        )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    try:
        if args.command == "once":
            print(run_once(codex_bin=args.codex_bin))
        else:
            run_loop(codex_bin=args.codex_bin)
    except KeyboardInterrupt:
        print("Stopped; no scheduler remains installed.", file=sys.stderr)
        return 130
    except JobError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
