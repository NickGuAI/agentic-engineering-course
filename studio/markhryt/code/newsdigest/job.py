"""Orchestration: one run = ingest -> summarize -> output; plus a simple loop mode."""

from __future__ import annotations

import logging
import re
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .config import DEFAULT_OUTPUT_DIR, SOURCES, SOURCES_BY_KEY, Source
from .http import FetchError, Fetcher, fetch
from .ingest import enrich_article, list_articles, parse_published_for_sort
from .models import Article, Digest
from .output import append_run_log, write_digest
from .state import State
from .summarize import ClaudeSummarizer, ExtractiveSummarizer, Summarizer, has_claude_credentials

log = logging.getLogger(__name__)


@dataclass
class RunOptions:
    outputs_dir: Path = DEFAULT_OUTPUT_DIR
    sources: tuple[Source, ...] = SOURCES
    max_per_source: int = 10
    no_llm: bool = False
    force: bool = False          # re-summarize even if already seen
    dry_run: bool = False        # ingest only; write nothing
    always_write: bool = False   # write a digest even when nothing is new
    model: str | None = None


@dataclass
class RunResult:
    started_at: str
    status: str = "ok"           # ok | ok-empty | degraded | dry-run | error
    method: str = ""
    model: str = ""
    listed: dict[str, int] = field(default_factory=dict)
    new: dict[str, int] = field(default_factory=dict)
    source_errors: dict[str, str] = field(default_factory=dict)
    body_errors: int = 0
    summarized: int = 0
    usage: dict[str, int] = field(default_factory=dict)
    outputs: dict[str, str] = field(default_factory=dict)
    duration_s: float = 0.0
    notes: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return self.__dict__.copy()


def select_sources(keys: str | None) -> tuple[Source, ...]:
    if not keys:
        return SOURCES
    out = []
    for k in [k.strip() for k in keys.split(",") if k.strip()]:
        if k not in SOURCES_BY_KEY:
            raise SystemExit(f"unknown source {k!r}; choose from {', '.join(SOURCES_BY_KEY)}")
        out.append(SOURCES_BY_KEY[k])
    return tuple(out)


def _pick_summarizer(opts: RunOptions, result: RunResult, summarizer: Summarizer | None) -> Summarizer:
    if summarizer is not None:
        return summarizer
    if opts.no_llm:
        result.notes.append("--no-llm: extractive summaries")
        return ExtractiveSummarizer()
    if not has_claude_credentials():
        result.status = "degraded"
        result.notes.append("no Claude credentials (ANTHROPIC_API_KEY unset, no `ant auth login` profile); "
                            "fell back to extractive summaries")
        log.warning(result.notes[-1])
        return ExtractiveSummarizer()
    try:
        return ClaudeSummarizer(model=opts.model)
    except ImportError:
        result.status = "degraded"
        result.notes.append("anthropic SDK not installed (pip install -r requirements.txt); "
                            "fell back to extractive summaries")
        log.warning(result.notes[-1])
        return ExtractiveSummarizer()


def run_once(opts: RunOptions, fetcher: Fetcher = fetch, summarizer: Summarizer | None = None) -> RunResult:
    t0 = time.monotonic()
    now = datetime.now(timezone.utc).isoformat(timespec="seconds")
    result = RunResult(started_at=now)
    state = State(opts.outputs_dir / "state.json")

    # ---- 1. ingest -------------------------------------------------------
    fresh: list[tuple[Source, Article]] = []
    listed_all: list[Article] = []
    for src in opts.sources:
        try:
            listed = list_articles(src, fetcher)
        except (FetchError, ValueError) as e:
            log.error("source %s failed: %s", src.key, e)
            result.source_errors[src.key] = str(e)
            continue
        result.listed[src.key] = len(listed)
        listed_all.extend(listed)
        new = [a for a in listed if opts.force or not state.is_seen(a.url)]
        # Listing order is not chronological (featured cards, sidebar links), so rank by
        # date before capping. Cards without a date (e.g. the 'Featured' card) get their
        # date from the article page first; that fetch is reused for summarization.
        for a in new:
            if not a.published and src.fetch_bodies:
                enrich_article(a, src, fetcher)
        new.sort(key=parse_published_for_sort, reverse=True)
        new = new[: opts.max_per_source]
        result.new[src.key] = len(new)
        log.info("%s: %d new (cap %d)", src.key, len(new), opts.max_per_source)
        fresh.extend((src, a) for a in new)

    if not opts.sources or len(result.source_errors) == len(opts.sources):
        result.status = "error"
        result.notes.append("every source failed to fetch")
        result.duration_s = round(time.monotonic() - t0, 2)
        if not opts.dry_run:
            append_run_log(result.to_dict(), opts.outputs_dir)
        return result
    if result.source_errors:
        result.status = "degraded"

    if opts.dry_run:
        for src, a in fresh:
            log.info("[dry-run] %s | %s | %s | %s", src.key, a.published or "????-??-??", a.title, a.url)
        result.status = "dry-run"
        result.duration_s = round(time.monotonic() - t0, 2)
        return result

    articles: list[Article] = []
    for src, a in fresh:
        enrich_article(a, src, fetcher)
        if a.fetch_error:
            result.body_errors += 1
        articles.append(a)

    if not articles and not opts.always_write:
        result.status = "ok-empty" if result.status == "ok" else result.status
        result.notes.append("nothing new since last run")
        state.save()
        result.duration_s = round(time.monotonic() - t0, 2)
        append_run_log(result.to_dict(), opts.outputs_dir)
        return result

    # ---- 2. summarize ----------------------------------------------------
    summ = _pick_summarizer(opts, result, summarizer)
    result.method = summ.method
    result.model = getattr(summ, "model", "")
    summaries = summ.summarize(articles) if articles else []
    overview, themes = summ.digest(articles, summaries) if articles else ("Nothing new since the last run.", [])
    result.summarized = len(summaries)
    result.usage = dict(getattr(summ, "usage", {}) or {})

    # ---- 3. output -------------------------------------------------------
    by_url = {s.url: s for s in summaries}
    digest = Digest(
        generated_at=now, overview=overview, themes=themes,
        items=[(a, by_url[a.url]) for a in articles if a.url in by_url],
        method=summ.method, model=result.model,
    )
    paths = write_digest(digest, opts.outputs_dir)
    result.outputs = {k: str(p) for k, p in paths.items()}
    # Mark everything listed this run as seen, not just what was summarized: the cap
    # keeps each digest to the newest N per source, and older backlog is intentionally
    # skipped rather than drained over later runs (use --force --max-per-source N to get it).
    for a in listed_all:
        if not state.is_seen(a.url):
            state.mark(a, when=now)
    state.save()
    result.duration_s = round(time.monotonic() - t0, 2)
    append_run_log(result.to_dict(), opts.outputs_dir)
    log.info("run complete: %s -> %s", result.status, paths["markdown"])
    return result


_INTERVAL_RE = re.compile(r"^\s*(\d+(?:\.\d+)?)\s*([smhd]?)\s*$", re.I)


def parse_interval(text: str) -> float:
    """'30m' -> 1800, '6h' -> 21600, '1d' -> 86400, '900' -> 900 (seconds)."""
    m = _INTERVAL_RE.match(text or "")
    if not m:
        raise ValueError(f"bad interval {text!r}; use e.g. 30m, 6h, 1d")
    mult = {"": 1, "s": 1, "m": 60, "h": 3600, "d": 86400}[m.group(2).lower()]
    secs = float(m.group(1)) * mult
    if secs < 60:
        raise ValueError("interval must be at least 60 seconds")
    return secs


def run_loop(opts: RunOptions, interval_s: float, max_runs: int | None = None,
             fetcher: Fetcher = fetch, sleep=time.sleep) -> list[RunResult]:
    """Run forever (or `max_runs` times), sleeping `interval_s` between runs."""
    results = []
    n = 0
    while True:
        try:
            results.append(run_once(opts, fetcher))
        except Exception:  # keep the loop alive; the traceback is in the log
            log.exception("run failed")
            append_run_log({"status": "error", "started_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
                            "notes": ["unhandled exception; see logs/job.log"]}, opts.outputs_dir)
        n += 1
        if max_runs is not None and n >= max_runs:
            return results
        log.info("sleeping %.0fs until next run", interval_s)
        sleep(interval_s)
