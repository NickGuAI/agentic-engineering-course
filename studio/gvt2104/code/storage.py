"""Tiny JSON-file persistence for ratings and the fetched-article cache.

No database or third-party dependency: state lives in ``code/data/*.json`` so the
app is fully self-contained and easy to inspect.
"""

from __future__ import annotations

import json
import os
import threading
from datetime import datetime, timezone

DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")
RATINGS_FILE = os.path.join(DATA_DIR, "ratings.json")
CACHE_FILE = os.path.join(DATA_DIR, "cache.json")

_lock = threading.Lock()


def _ensure_dir() -> None:
    os.makedirs(DATA_DIR, exist_ok=True)


def _read_json(path: str, default):
    try:
        with open(path, encoding="utf-8") as fh:
            return json.load(fh)
    except (FileNotFoundError, json.JSONDecodeError):
        return default


def _write_json(path: str, data) -> None:
    _ensure_dir()
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as fh:
        json.dump(data, fh, indent=2, ensure_ascii=False)
    os.replace(tmp, path)  # atomic


# --- ratings --------------------------------------------------------------
def load_ratings() -> dict:
    """Return {article_id: {rating, note, tags, title, ts}}."""
    with _lock:
        return _read_json(RATINGS_FILE, {})


def save_rating(article_id: str, rating: int, note: str, tags: list[str], title: str) -> dict:
    """Upsert a rating; a rating of 0 with an empty note clears the entry."""
    with _lock:
        ratings = _read_json(RATINGS_FILE, {})
        if rating == 0 and not (note or "").strip():
            ratings.pop(article_id, None)
        else:
            ratings[article_id] = {
                "rating": int(rating),
                "note": (note or "").strip(),
                "tags": tags,
                "title": title,
                "ts": datetime.now(timezone.utc).isoformat(),
            }
        _write_json(RATINGS_FILE, ratings)
        return ratings


# --- article cache --------------------------------------------------------
def load_cache() -> dict:
    """Return {"fetched_at": iso, "articles": [...]} or {}."""
    with _lock:
        return _read_json(CACHE_FILE, {})


def save_cache(articles: list[dict]) -> None:
    with _lock:
        _write_json(CACHE_FILE, {
            "fetched_at": datetime.now(timezone.utc).isoformat(),
            "articles": articles,
        })
