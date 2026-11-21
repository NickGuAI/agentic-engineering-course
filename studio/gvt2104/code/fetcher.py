"""Fetch and parse updates from the three configured sources.

Sources:
  * Anthropic News        -> https://www.anthropic.com/news        (HTML cards)
  * Anthropic Engineering -> https://www.anthropic.com/engineering (HTML cards)
  * OpenAI News           -> https://openai.com/news/rss.xml       (RSS feed)

Design goals:
  * stdlib only (urllib, html, re) -- no pip install required
  * resilient: a failure in one source never blanks the others; a total
    failure falls back to the on-disk cache and then to bundled seed data.
"""

from __future__ import annotations

import html
import re
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from email.utils import parsedate_to_datetime

import storage
from seed_data import SEED_ARTICLES

USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/122.0 Safari/537.36 agent-news-digest/1.0"
)
TIMEOUT = 12
BASE_ANTHROPIC = "https://www.anthropic.com"

SOURCES = [
    ("Anthropic News", "html", "https://www.anthropic.com/news", "/news/"),
    ("Anthropic Engineering", "html", "https://www.anthropic.com/engineering", "/engineering/"),
    ("OpenAI News", "rss", "https://openai.com/news/rss.xml", None),
]


def _http_get(url: str) -> str:
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(req, timeout=TIMEOUT) as resp:
        charset = resp.headers.get_content_charset() or "utf-8"
        return resp.read().decode(charset, errors="replace")


def _clean(text: str) -> str:
    """Unescape HTML entities and collapse whitespace."""
    return html.unescape(re.sub(r"\s+", " ", text or "")).strip()


def _strip_tags(text: str) -> str:
    return _clean(re.sub(r"<[^>]+>", " ", text or ""))


# --- Anthropic HTML card parsing -----------------------------------------
# Anthropic uses two card layouts:
#   /news        -> <a href="/news/.." class="..">..<h4 class="..title">..</a>
#   /engineering -> <a class=".." href="/engineering/..">..<h3 class="headline-4">..</a>
# The anchor regex therefore allows any attributes before OR after href.
_ANCHOR_RE_TMPL = r'<a\s+[^>]*?href="(%s[a-z0-9\-]+)"[^>]*>(.*?)</a>'
# Match the CSS-module suffix (``__title`` / ``__body`` / ``__date``) rather than
# a bare substring: Anthropic's date div is class="body-2 ...__date", which a
# loose "body" match would wrongly grab as the summary.
_TITLE_CLASS_RE = re.compile(r'class="[^"]*__title[^"]*"[^>]*>(.*?)<', re.I | re.S)
_HEADING_RE = re.compile(r"<h[1-6][^>]*>(.*?)</h[1-6]>", re.I | re.S)
_BODY_RE = re.compile(r'class="[^"]*__body[^"]*"[^>]*>(.*?)<', re.I | re.S)
_TIME_RE = re.compile(r"<time[^>]*>(.*?)</time>", re.I | re.S)
_DATE_CLASS_RE = re.compile(r'class="[^"]*__date[^"]*"[^>]*>(.*?)<', re.I | re.S)
_CATEGORY_RE = re.compile(r'class="caption bold"[^>]*>(.*?)<', re.I | re.S)


def _first(*matches):
    for m in matches:
        if m:
            return _strip_tags(m.group(1))
    return ""


def _parse_anthropic(source: str, path_prefix: str, htmltext: str) -> list[dict]:
    anchor_re = re.compile(_ANCHOR_RE_TMPL % re.escape(path_prefix), re.I | re.S)
    articles: list[dict] = []
    seen: set[str] = set()
    for m in anchor_re.finditer(htmltext):
        href, inner = m.group(1), m.group(2)
        if href in seen:
            continue
        title = _first(_TITLE_CLASS_RE.search(inner), _HEADING_RE.search(inner))
        if not title:
            continue  # not a real article card (nav/footer/image-only link)
        seen.add(href)
        articles.append({
            "source": source,
            "category": _first(_CATEGORY_RE.search(inner)) or "Article",
            "title": title,
            "url": BASE_ANTHROPIC + href,
            "date": _first(_TIME_RE.search(inner), _DATE_CLASS_RE.search(inner)),
            "summary": _first(_BODY_RE.search(inner)),
        })
    return articles


# --- OpenAI RSS parsing ---------------------------------------------------
_ITEM_RE = re.compile(r"<item>(.*?)</item>", re.I | re.S)


def _rss_field(item: str, tag: str) -> str:
    m = re.search(rf"<{tag}[^>]*>(.*?)</{tag}>", item, re.I | re.S)
    if not m:
        return ""
    val = m.group(1)
    cdata = re.match(r"\s*<!\[CDATA\[(.*?)\]\]>\s*$", val, re.S)
    if cdata:
        val = cdata.group(1)
    return _strip_tags(val)


def _fmt_rss_date(pubdate: str) -> str:
    try:
        dt = parsedate_to_datetime(pubdate)
        return dt.strftime("%b %-d, %Y")
    except (TypeError, ValueError):
        return ""


def _parse_openai(source: str, xmltext: str) -> list[dict]:
    articles: list[dict] = []
    for m in _ITEM_RE.finditer(xmltext):
        item = m.group(1)
        title = _rss_field(item, "title")
        link = _rss_field(item, "link")
        if not title or not link:
            continue
        articles.append({
            "source": source,
            "category": _rss_field(item, "category") or "News",
            "title": title,
            "url": link,
            "date": _fmt_rss_date(_rss_field(item, "pubDate")),
            "summary": _rss_field(item, "description"),
        })
    return articles


# --- orchestration --------------------------------------------------------
def _fetch_one(spec) -> tuple[str, list[dict], str | None]:
    source, kind, url, prefix = spec
    try:
        raw = _http_get(url)
        if kind == "rss":
            items = _parse_openai(source, raw)
        else:
            items = _parse_anthropic(source, prefix, raw)
        if not items:
            return source, [], "parsed 0 items"
        return source, items, None
    except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError, OSError) as exc:
        return source, [], f"{type(exc).__name__}: {exc}"


def fetch_all(limit_per_source: int = 8) -> dict:
    """Fetch every source concurrently.

    Returns {"articles": [...], "status": {source: "ok"|error}, "used_fallback": bool}.
    Sources that fail fall back to whatever the cache/seed holds for them.
    """
    fallback = _fallback_by_source()
    articles: list[dict] = []
    status: dict[str, str] = {}
    any_ok = False

    with ThreadPoolExecutor(max_workers=len(SOURCES)) as pool:
        results = list(pool.map(_fetch_one, SOURCES))

    for source, items, err in results:
        if items:
            any_ok = True
            status[source] = "ok"
            articles.extend(_enrich(items[:limit_per_source]))
        else:
            status[source] = f"fallback ({err})"
            articles.extend(fallback.get(source, []))

    if any_ok:
        storage.save_cache(articles)

    return {"articles": articles, "status": status, "used_fallback": not any_ok}


_SEED_BY_URL = {a["url"]: a for a in SEED_ARTICLES}


def _enrich(items: list[dict]) -> list[dict]:
    """Fill empty date/summary fields from bundled seed data (list pages often
    omit article descriptions). Never overwrites live values that are present."""
    for art in items:
        seed = _SEED_BY_URL.get(art["url"])
        if not seed:
            continue
        if not art.get("summary"):
            art["summary"] = seed.get("summary", "")
        if not art.get("date"):
            art["date"] = seed.get("date", "")
    return items


def _group_by_source(articles) -> dict[str, list[dict]]:
    grouped: dict[str, list[dict]] = {}
    for art in articles or []:
        grouped.setdefault(art["source"], []).append(art)
    return grouped


def _fallback_by_source() -> dict[str, list[dict]]:
    """Per source: prefer the cached articles, else the bundled seed."""
    seed = _group_by_source(SEED_ARTICLES)
    cached = _group_by_source(storage.load_cache().get("articles"))
    sources = set(seed) | set(cached)
    return {src: cached.get(src) or seed.get(src, []) for src in sources}


def get_articles(refresh: bool = False) -> dict:
    """Return articles, using the cache unless a refresh is requested."""
    if not refresh:
        cache = storage.load_cache()
        if cache.get("articles"):
            return {
                "articles": cache["articles"],
                "status": {"cache": f"served from cache ({cache.get('fetched_at')})"},
                "used_fallback": False,
            }
    return fetch_all()


if __name__ == "__main__":
    result = fetch_all()
    print("status:", result["status"])
    print("fetched", len(result["articles"]), "articles")
    for a in result["articles"]:
        print(f"  [{a['source']}] {a['date']:>14}  {a['title']}")
