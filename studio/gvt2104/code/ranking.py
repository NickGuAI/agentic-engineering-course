"""Relevance tagging and the (learning) ranking function.

The ranking function combines three signals for each article:

    score = W_RELEVANCE * agent_relevance   # curated keyword match
          + W_RECENCY   * recency           # newer is better
          + learned_boost                   # sum of learned tag weights

``learned_boost`` is what makes the ranking *adapt*: every time the user rates a
block (thumbs up / down, plus an optional note) we nudge the weights of the tags
attached to that block. Highly-rated topics float to the top on the next render.
"""

from __future__ import annotations

import hashlib
import re
from datetime import datetime, timezone

# --- weights for the base ranking function --------------------------------
W_RELEVANCE = 1.0
W_RECENCY = 1.5
# how strongly a single rating moves a tag's learned weight
LEARN_RATE = 1.2
# a note mentioning a keyword nudges that tag too, but a bit more gently
NOTE_FACTOR = 0.6
# half-life (in days) used for the recency signal
RECENCY_HALFLIFE_DAYS = 45.0

# Curated vocabulary of terms that matter to *developers of agents*.
# Multi-word phrases are checked before single words. Values are the base
# weight each match contributes to agent-relevance. Longer/more-specific
# phrases are worth more.
AGENT_KEYWORDS = {
    "context engineering": 4,
    "model context protocol": 4,
    "long-running": 3,
    "function calling": 4,
    "multi-agent": 4,
    "tool use": 4,
    "agent skills": 4,
    "code execution": 3,
    "claude code": 3,
    "agentic": 3,
    "agents": 3,
    "agent": 3,
    "harness": 3,
    "mcp": 4,
    "sdk": 3,
    "codex": 3,
    "orchestration": 3,
    "sandboxing": 2,
    "sandbox": 2,
    "retrieval": 2,
    "rag": 3,
    "evals": 2,
    "eval": 2,
    "evaluation": 2,
    "context window": 3,
    "context": 2,
    "coding": 2,
    "reasoning": 2,
    "prompt": 2,
    "api": 2,
    "skills": 2,
    "permissions": 2,
    "tools": 1,
    "model": 1,
}

# normalized tag name -> keyword phrases that map to it (keeps tags tidy)
_TAG_ALIASES = {
    "agents": ["agent", "agents", "agentic", "multi-agent"],
    "tool-use": ["tool use", "tools", "function calling"],
    "mcp": ["mcp", "model context protocol", "code execution"],
    "claude-code": ["claude code"],
    "codex": ["codex"],
    "harness": ["harness", "long-running", "orchestration"],
    "sdk-api": ["sdk", "api"],
    "evals": ["eval", "evals", "evaluation"],
    "context": ["context", "context window", "context engineering"],
    "coding": ["coding"],
    "rag": ["rag", "retrieval"],
    "skills": ["skills", "agent skills"],
    "sandbox": ["sandbox", "sandboxing", "permissions"],
    "reasoning": ["reasoning", "prompt"],
}
_KEYWORD_TO_TAG = {kw: tag for tag, kws in _TAG_ALIASES.items() for kw in kws}


def article_id(url: str) -> str:
    """Stable id for an article, derived from its URL."""
    return hashlib.sha1(url.encode("utf-8")).hexdigest()[:12]


def _matched_keywords(text: str) -> list[str]:
    text = text.lower()
    hits = []
    for kw in AGENT_KEYWORDS:
        # word-ish boundary match so "api" doesn't fire inside "capital"
        if re.search(r"(?<![a-z])" + re.escape(kw) + r"(?![a-z])", text):
            hits.append(kw)
    return hits


def relevance_and_tags(title: str, summary: str) -> tuple[float, list[str]]:
    """Return (agent_relevance_score, sorted_unique_tags) for an article."""
    text = f"{title} {summary}"
    score = 0.0
    tags: set[str] = set()
    for kw in _matched_keywords(text):
        score += AGENT_KEYWORDS[kw]
        tag = _KEYWORD_TO_TAG.get(kw)
        if tag:
            tags.add(tag)
    return score, sorted(tags)


def keywords_from_note(note: str) -> list[str]:
    """Extract known tags mentioned in a free-text note."""
    tags: set[str] = set()
    for kw in _matched_keywords(note or ""):
        tag = _KEYWORD_TO_TAG.get(kw)
        if tag:
            tags.add(tag)
    return sorted(tags)


def _parse_date(date_str: str) -> datetime | None:
    if not date_str:
        return None
    for fmt in ("%b %d, %Y", "%B %d, %Y", "%Y-%m-%d"):
        try:
            return datetime.strptime(date_str, fmt).replace(tzinfo=timezone.utc)
        except ValueError:
            continue
    return None


def _recency_score(date_str: str, now: datetime) -> float:
    dt = _parse_date(date_str)
    if dt is None:
        return 0.0
    age_days = max(0.0, (now - dt).total_seconds() / 86400.0)
    # exponential decay: 1.0 today, 0.5 at one half-life, ...
    return 0.5 ** (age_days / RECENCY_HALFLIFE_DAYS)


def learned_weights(ratings: dict) -> dict[str, float]:
    """Recompute per-tag learned weights from the full ratings history.

    Recomputing from scratch (rather than incrementally mutating) keeps the
    weights deterministic and idempotent even when a block is re-rated.
    """
    weights: dict[str, float] = {}
    for rec in ratings.values():
        rating = rec.get("rating", 0)
        if not rating:
            continue
        for tag in rec.get("tags", []):
            weights[tag] = weights.get(tag, 0.0) + LEARN_RATE * rating
        for tag in keywords_from_note(rec.get("note", "")):
            weights[tag] = weights.get(tag, 0.0) + LEARN_RATE * NOTE_FACTOR * rating
    return weights


def rank(articles: list[dict], ratings: dict, now: datetime | None = None) -> list[dict]:
    """Return a new list of articles, scored and sorted best-first.

    Each article dict is enriched (non-destructively) with: ``id``, ``tags``,
    ``relevance``, ``recency``, ``learned``, ``score`` and the user's current
    ``rating`` / ``note`` for that block.
    """
    now = now or datetime.now(timezone.utc)
    weights = learned_weights(ratings)

    ranked = []
    for art in articles:
        aid = article_id(art["url"])
        relevance, tags = relevance_and_tags(art.get("title", ""), art.get("summary", ""))
        recency = _recency_score(art.get("date", ""), now)
        learned = sum(weights.get(t, 0.0) for t in tags)
        score = W_RELEVANCE * relevance + W_RECENCY * recency + learned

        rec = ratings.get(aid, {})
        ranked.append({
            **art,
            "id": aid,
            "tags": tags,
            "relevance": round(relevance, 2),
            "recency": round(recency, 3),
            "learned": round(learned, 3),
            "score": round(score, 3),
            "rating": rec.get("rating", 0),
            "note": rec.get("note", ""),
        })

    ranked.sort(key=lambda a: a["score"], reverse=True)
    return ranked
