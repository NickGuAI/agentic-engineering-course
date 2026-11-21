"""Seen-URL state so each run only summarizes new articles."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .models import Article


class State:
    def __init__(self, path: Path):
        self.path = path
        self.seen: dict[str, dict[str, Any]] = {}
        self.last_run: str = ""
        if path.exists():
            data = json.loads(path.read_text(encoding="utf-8"))
            self.seen = data.get("seen", {})
            self.last_run = data.get("last_run", "")

    def is_seen(self, url: str) -> bool:
        return url in self.seen

    def mark(self, article: Article, when: str | None = None) -> None:
        self.seen[article.url] = {
            "first_seen": when or datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "title": article.title,
            "source": article.source_key,
            "published": article.published,
        }

    def save(self) -> None:
        self.last_run = datetime.now(timezone.utc).isoformat(timespec="seconds")
        self.path.parent.mkdir(parents=True, exist_ok=True)
        tmp = self.path.with_suffix(".tmp")
        tmp.write_text(json.dumps({"last_run": self.last_run, "seen": self.seen},
                                  indent=2, sort_keys=True), encoding="utf-8")
        tmp.replace(self.path)
