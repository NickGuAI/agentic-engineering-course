"""Static configuration: sources, paths, model."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

CODE_DIR = Path(__file__).resolve().parent.parent
STUDENT_DIR = CODE_DIR.parent
DEFAULT_OUTPUT_DIR = STUDENT_DIR / "outputs"

# Default summarization model. Override with --model or NEWSDIGEST_MODEL.
DEFAULT_MODEL = "claude-opus-5"

# A browser-like UA: anthropic.com serves plain HTML to it; openai.com's HTML
# pages sit behind a bot check (HTTP 403) regardless, so that source uses RSS.
USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/128.0 Safari/537.36"
)
FETCH_TIMEOUT_SECONDS = 25
FETCH_RETRIES = 2

# Per-article body cap sent to the model (characters). Article pages on
# anthropic.com run 15-25k characters, so this rarely truncates.
MAX_BODY_CHARS = 40_000
# Articles per summarization request.
SUMMARY_BATCH_SIZE = 8


@dataclass(frozen=True)
class Source:
    key: str
    name: str
    url: str          # the page the job is about (what the user asked for)
    kind: str         # "anthropic_listing" | "rss"
    fetch_url: str    # what we actually download for the listing
    path_prefix: str = ""   # article href prefix on anthropic_listing pages
    fetch_bodies: bool = True  # whether individual article pages are fetchable


SOURCES: tuple[Source, ...] = (
    Source(
        key="anthropic-news",
        name="Anthropic News",
        url="https://www.anthropic.com/news",
        kind="anthropic_listing",
        fetch_url="https://www.anthropic.com/news",
        path_prefix="/news/",
    ),
    Source(
        key="anthropic-engineering",
        name="Anthropic Engineering",
        url="https://www.anthropic.com/engineering",
        kind="anthropic_listing",
        fetch_url="https://www.anthropic.com/engineering",
        path_prefix="/engineering/",
    ),
    Source(
        key="openai-news",
        name="OpenAI News",
        url="https://openai.com/news/",
        kind="rss",
        fetch_url="https://openai.com/news/rss.xml",
        # openai.com article pages return 403 to non-browser clients, so the
        # feed's title + description is the ingested text for this source.
        fetch_bodies=False,
    ),
)

SOURCES_BY_KEY = {s.key: s for s in SOURCES}
