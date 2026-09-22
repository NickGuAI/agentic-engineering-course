"""Data records passed between pipeline stages."""

from __future__ import annotations

from dataclasses import dataclass, field, asdict
from typing import Any


@dataclass
class Article:
    source_key: str
    source_name: str
    url: str
    title: str
    published: str = ""     # ISO date (YYYY-MM-DD) when known, else ""
    category: str = ""
    snippet: str = ""       # listing-page teaser / feed description
    body: str = ""          # full article text when fetchable, else ""
    fetch_error: str = ""   # why the body could not be fetched, if so
    title_is_fallback: bool = False  # title was derived from the URL slug, not the page

    @property
    def text(self) -> str:
        """Best available text for summarization."""
        return self.body or self.snippet

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class Summary:
    url: str
    headline: str
    summary: str
    why_it_matters: str = ""
    tags: list[str] = field(default_factory=list)
    method: str = "llm"     # "llm" | "extractive"

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class Theme:
    title: str
    detail: str


@dataclass
class Digest:
    generated_at: str       # ISO timestamp
    overview: str
    themes: list[Theme]
    items: list[tuple[Article, Summary]]
    method: str             # "llm" | "extractive"
    model: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "generated_at": self.generated_at,
            "method": self.method,
            "model": self.model,
            "overview": self.overview,
            "themes": [asdict(t) for t in self.themes],
            "items": [
                {"article": a.to_dict(), "summary": s.to_dict()} for a, s in self.items
            ],
        }
