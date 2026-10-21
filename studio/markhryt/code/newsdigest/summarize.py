"""Stage 2: summarization.

Two interchangeable summarizers:
  * ClaudeSummarizer   - calls the Claude API with structured (JSON schema) output.
  * ExtractiveSummarizer - offline fallback: first sentences of the article text.
"""

from __future__ import annotations

import json
import logging
import os
import re
from pathlib import Path
from typing import Any, Protocol

from .config import DEFAULT_MODEL, SUMMARY_BATCH_SIZE
from .models import Article, Summary, Theme

log = logging.getLogger(__name__)


class Summarizer(Protocol):
    method: str

    def summarize(self, articles: list[Article]) -> list[Summary]: ...
    def digest(self, articles: list[Article], summaries: list[Summary]) -> tuple[str, list[Theme]]: ...


# ---------------------------------------------------------------- credentials

def has_claude_credentials() -> bool:
    """Mirror the SDK's credential resolution: env vars or an `ant auth login` profile."""
    if os.environ.get("ANTHROPIC_API_KEY") or os.environ.get("ANTHROPIC_AUTH_TOKEN"):
        return True
    return (Path.home() / ".config" / "anthropic").exists()


# ---------------------------------------------------------------- extractive fallback

_SENT_SPLIT = re.compile(r"(?<=[.!?])\s+(?=[A-Z\"'(])")


def first_sentences(text: str, n: int = 2, max_chars: int = 400) -> str:
    text = re.sub(r"\s+", " ", text or "").strip()
    if not text:
        return ""
    sents = _SENT_SPLIT.split(text)
    out = " ".join(sents[:n]).strip()
    if len(out) > max_chars:
        out = out[:max_chars].rsplit(" ", 1)[0] + "…"
    return out


_DATE_LINE = re.compile(r"^[A-Z][a-z]{2,8}\.? \d{1,2}, \d{4}$")


def _drop_header_echo(body: str, title: str, window: int = 8) -> str:
    """Article pages start with category / title / date lines before the prose. Drop them."""
    lines = body.split("\n")
    start = 0
    t = (title or "").strip().casefold()
    for i, ln in enumerate(lines[:window]):
        if t and t in ln.casefold():
            start = i + 1
    while start < len(lines) and (_DATE_LINE.match(lines[start].strip()) or len(lines[start].strip()) < 4):
        start += 1
    return "\n".join(lines[start:]) if start < len(lines) else body


class ExtractiveSummarizer:
    """No-network, no-LLM summarizer. Used with --no-llm or when credentials are missing."""

    method = "extractive"

    def summarize(self, articles: list[Article]) -> list[Summary]:
        out = []
        for a in articles:
            text = _drop_header_echo(a.body, a.title) if a.body else a.snippet
            out.append(Summary(
                url=a.url, headline=a.title,
                summary=first_sentences(text) or "(no text available)",
                why_it_matters="", tags=[t for t in [a.category] if t],
                method=self.method,
            ))
        return out

    def digest(self, articles: list[Article], summaries: list[Summary]) -> tuple[str, list[Theme]]:
        by_src: dict[str, int] = {}
        for a in articles:
            by_src[a.source_name] = by_src.get(a.source_name, 0) + 1
        parts = ", ".join(f"{n} from {s}" for s, n in by_src.items())
        return (f"{len(articles)} new item(s): {parts}. "
                "Summaries are extractive (first sentences); no model was used."), []


# ---------------------------------------------------------------- Claude summarizer

SYSTEM_PROMPT = """You write a daily AI-industry digest for engineers who build on LLM platforms.
You are given recent posts from Anthropic News, Anthropic Engineering, and OpenAI News.
For each post, produce a neutral, specific summary grounded only in the provided text. Do not speculate
beyond it; if a post's text is only a short teaser, say what is known and keep the summary short.
"why_it_matters" is one or two sentences for a practitioner: what changes for someone building with these
platforms, or why the news is notable. Tags are 1-4 short lowercase topics (e.g. "models", "safety",
"agents", "pricing", "research", "product", "policy")."""

ITEMS_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "items": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "id": {"type": "string", "description": "the article id given in the input"},
                    "headline": {"type": "string", "description": "a concise, factual headline (<= 15 words)"},
                    "summary": {"type": "string", "description": "2-4 sentences"},
                    "why_it_matters": {"type": "string"},
                    "tags": {"type": "array", "items": {"type": "string"}},
                },
                "required": ["id", "headline", "summary", "why_it_matters", "tags"],
                "additionalProperties": False,
            },
        }
    },
    "required": ["items"],
    "additionalProperties": False,
}

DIGEST_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "overview": {"type": "string", "description": "3-5 sentence overview of what happened across all sources"},
        "themes": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {"title": {"type": "string"}, "detail": {"type": "string"}},
                "required": ["title", "detail"],
                "additionalProperties": False,
            },
        },
    },
    "required": ["overview", "themes"],
    "additionalProperties": False,
}


def _article_block(idx: str, a: Article) -> str:
    text = a.text or "(no text available)"
    return (
        f"<article id=\"{idx}\">\n"
        f"source: {a.source_name}\ntitle: {a.title}\nurl: {a.url}\n"
        f"published: {a.published or 'unknown'}\n"
        f"text_kind: {'full article' if a.body else 'teaser only'}\n\n{text}\n</article>"
    )


class ClaudeSummarizer:
    method = "llm"

    def __init__(self, model: str | None = None, client: Any = None, effort: str = "medium"):
        self.model = model or os.environ.get("NEWSDIGEST_MODEL") or DEFAULT_MODEL
        self.effort = effort
        self.usage: dict[str, int] = {"input_tokens": 0, "output_tokens": 0, "requests": 0}
        self._fallback = ExtractiveSummarizer()
        if client is None:
            import anthropic  # imported lazily so the offline path needs no SDK
            client = anthropic.Anthropic()
        self.client = client

    # -- one structured-output request ---------------------------------------
    def _request(self, user_text: str, schema: dict[str, Any], max_tokens: int = 16000) -> dict[str, Any] | None:
        response = self.client.messages.create(
            model=self.model,
            max_tokens=max_tokens,
            system=[{"type": "text", "text": SYSTEM_PROMPT, "cache_control": {"type": "ephemeral"}}],
            messages=[{"role": "user", "content": user_text}],
            output_config={"effort": self.effort, "format": {"type": "json_schema", "schema": schema}},
        )
        usage = getattr(response, "usage", None)
        if usage is not None:
            self.usage["input_tokens"] += getattr(usage, "input_tokens", 0) or 0
            self.usage["output_tokens"] += getattr(usage, "output_tokens", 0) or 0
        self.usage["requests"] += 1
        if response.stop_reason == "refusal":
            details = getattr(response, "stop_details", None)
            log.warning("model declined the request (%s); falling back to extractive", details)
            return None
        if response.stop_reason == "max_tokens":
            log.warning("response hit max_tokens; output may be incomplete")
        text = "".join(b.text for b in response.content if getattr(b, "type", "") == "text")
        try:
            return json.loads(text)
        except json.JSONDecodeError as e:
            log.error("could not parse structured output: %s", e)
            return None

    def summarize(self, articles: list[Article]) -> list[Summary]:
        results: list[Summary] = []
        for start in range(0, len(articles), SUMMARY_BATCH_SIZE):
            batch = articles[start:start + SUMMARY_BATCH_SIZE]
            ids = {f"a{start + i + 1}": a for i, a in enumerate(batch)}
            prompt = ("Summarize each of the following posts. Return one item per article id.\n\n"
                      + "\n\n".join(_article_block(k, a) for k, a in ids.items()))
            data = self._request(prompt, ITEMS_SCHEMA)
            got: dict[str, dict[str, Any]] = {}
            if data:
                got = {it.get("id", ""): it for it in data.get("items", []) if isinstance(it, dict)}
            for k, a in ids.items():
                it = got.get(k)
                if it:
                    results.append(Summary(
                        url=a.url, headline=it.get("headline") or a.title,
                        summary=it.get("summary", ""), why_it_matters=it.get("why_it_matters", ""),
                        tags=[str(t) for t in it.get("tags", [])][:4], method="llm",
                    ))
                else:
                    log.warning("no summary returned for %s; using extractive fallback", a.url)
                    results.extend(self._fallback.summarize([a]))
        return results

    def digest(self, articles: list[Article], summaries: list[Summary]) -> tuple[str, list[Theme]]:
        by_url = {a.url: a for a in articles}
        lines = []
        for s in summaries:
            a = by_url.get(s.url)
            src = a.source_name if a else ""
            lines.append(f"- [{src}] {s.headline} ({s.url})\n  {s.summary}")
        prompt = ("Here are per-article summaries from today's run. Write the digest overview and "
                  "2-5 cross-cutting themes (fewer if the items are unrelated).\n\n" + "\n".join(lines))
        data = self._request(prompt, DIGEST_SCHEMA, max_tokens=4000)
        if not data:
            return self._fallback.digest(articles, summaries)
        themes = [Theme(title=str(t.get("title", "")), detail=str(t.get("detail", "")))
                  for t in data.get("themes", []) if isinstance(t, dict)]
        return str(data.get("overview", "")), themes
