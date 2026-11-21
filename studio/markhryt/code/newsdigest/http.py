"""Minimal HTTP fetch with retries (stdlib only)."""

from __future__ import annotations

import gzip
import logging
import time
import urllib.error
import urllib.request
from typing import Callable

from .config import FETCH_RETRIES, FETCH_TIMEOUT_SECONDS, USER_AGENT

log = logging.getLogger(__name__)

Fetcher = Callable[[str], str]


class FetchError(Exception):
    def __init__(self, url: str, reason: str, status: int | None = None):
        super().__init__(f"{url}: {reason}")
        self.url = url
        self.reason = reason
        self.status = status


def fetch(url: str, timeout: float = FETCH_TIMEOUT_SECONDS, retries: int = FETCH_RETRIES) -> str:
    """GET `url` and return decoded text. Retries on 5xx / network errors, not on 4xx."""
    req = urllib.request.Request(
        url,
        headers={
            "User-Agent": USER_AGENT,
            "Accept": "text/html,application/xhtml+xml,application/xml,text/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.9",
            "Accept-Encoding": "gzip",
        },
    )
    last: Exception | None = None
    for attempt in range(retries + 1):
        try:
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                raw = resp.read()
                if resp.headers.get("Content-Encoding", "").lower() == "gzip":
                    raw = gzip.decompress(raw)
                charset = resp.headers.get_content_charset() or "utf-8"
                return raw.decode(charset, errors="replace")
        except urllib.error.HTTPError as e:
            if 400 <= e.code < 500:
                raise FetchError(url, f"HTTP {e.code}", e.code) from e
            last = FetchError(url, f"HTTP {e.code}", e.code)
        except (urllib.error.URLError, TimeoutError, OSError) as e:
            last = FetchError(url, f"{type(e).__name__}: {e}")
        if attempt < retries:
            delay = 1.5 * (attempt + 1)
            log.warning("fetch retry %d for %s after %s", attempt + 1, url, last)
            time.sleep(delay)
    assert last is not None
    raise last
