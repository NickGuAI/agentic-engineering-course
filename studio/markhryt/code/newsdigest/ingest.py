"""Stage 1: ingestion. Turn each source into a list of Article records."""

from __future__ import annotations

import html as htmllib
import logging
import re
from datetime import datetime
from email.utils import parsedate_to_datetime
from html.parser import HTMLParser
from urllib.parse import urljoin
import xml.etree.ElementTree as ET

from .config import MAX_BODY_CHARS, Source
from .http import FetchError, Fetcher, fetch
from .models import Article

log = logging.getLogger(__name__)

# ---------------------------------------------------------------- text helpers

_SKIP_TAGS = {"script", "style", "noscript", "svg", "nav", "header", "footer", "template"}
_BLOCK_TAGS = {"p", "div", "br", "li", "h1", "h2", "h3", "h4", "h5", "h6",
               "section", "article", "blockquote", "pre", "tr", "ul", "ol", "figcaption"}


class _TextExtractor(HTMLParser):
    """Collects visible text, dropping script/style/nav chrome."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self._parts: list[str] = []
        self._skip_depth = 0

    def handle_starttag(self, tag, attrs):
        if tag in _SKIP_TAGS:
            self._skip_depth += 1
        elif tag in _BLOCK_TAGS:
            self._parts.append("\n")

    def handle_endtag(self, tag):
        if tag in _SKIP_TAGS and self._skip_depth:
            self._skip_depth -= 1
        elif tag in _BLOCK_TAGS:
            self._parts.append("\n")

    def handle_data(self, data):
        if not self._skip_depth:
            self._parts.append(data)

    def text(self) -> str:
        raw = "".join(self._parts)
        lines = [re.sub(r"[ \t\r\f\v]+", " ", ln).strip() for ln in raw.split("\n")]
        return "\n".join(ln for ln in lines if ln)


def html_to_text(fragment: str) -> str:
    p = _TextExtractor()
    p.feed(fragment)
    p.close()
    return p.text()


def strip_tags(fragment: str) -> str:
    """Single-line text from an inline HTML fragment."""
    return re.sub(r"\s+", " ", html_to_text(fragment)).strip()


def extract_article_text(page_html: str, max_chars: int = MAX_BODY_CHARS) -> str:
    """Return the main article text of a page (prefers <article>, then <main>)."""
    region = page_html
    for tag in ("article", "main"):
        m = re.search(rf"<{tag}\b.*?</{tag}>", page_html, flags=re.S | re.I)
        if m:
            region = m.group(0)
            break
    text = html_to_text(region)
    if len(text) > max_chars:
        log.warning("article text truncated from %d to %d chars", len(text), max_chars)
        text = text[:max_chars]
    return text


# ---------------------------------------------------------------- date helpers

_MONTHS = {m: i for i, m in enumerate(
    ["jan", "feb", "mar", "apr", "may", "jun", "jul", "aug", "sep", "oct", "nov", "dec"], 1)}


def parse_human_date(s: str) -> str:
    """'Aug 31, 2026' / 'August 31, 2026' -> '2026-08-31'. Returns '' if unparseable."""
    m = re.search(r"([A-Za-z]{3})[a-z]*\.?\s+(\d{1,2}),?\s+(\d{4})", s or "")
    if not m or m.group(1).lower() not in _MONTHS:
        m2 = re.search(r"(\d{4})-(\d{2})-(\d{2})", s or "")
        return m2.group(0) if m2 else ""
    return f"{int(m.group(3)):04d}-{_MONTHS[m.group(1).lower()]:02d}-{int(m.group(2)):02d}"


def parse_rfc822_date(s: str) -> str:
    try:
        return parsedate_to_datetime(s).date().isoformat()
    except (TypeError, ValueError):
        return ""


# ---------------------------------------------------------------- listing parsers

_ANCHOR_RE = re.compile(r'<a\b([^>]*)>(.*?)</a>', re.S | re.I)
_HREF_RE = re.compile(r'href="([^"]+)"', re.I)
_TITLE_RE = re.compile(r"<h[1-6]\b[^>]*>(.*?)</h[1-6]>", re.S | re.I)
_ALT_RE = re.compile(r'<img\b[^>]*\balt="([^"]*)"', re.I)
_TIME_RE = re.compile(r"<time\b[^>]*>(.*?)</time>", re.S | re.I)
_PARA_RE = re.compile(r"<p\b[^>]*>(.*?)</p>", re.S | re.I)
# anthropic.com cards vary: FeaturedGrid uses <h4>+<time>, PublicationList uses
# <span class="...title"> + <time>, ArticleList (engineering) uses <h3> + <div class="...date">.
_CLASS_TITLE_RE = re.compile(r'<(span|div|p)\b[^>]*class="[^"]*title[^"]*"[^>]*>(.*?)</\1>', re.S | re.I)
_CLASS_DATE_RE = re.compile(r'<(span|div|p)\b[^>]*class="[^"]*date[^"]*"[^>]*>(.*?)</\1>', re.S | re.I)
_HUMAN_DATE_RE = re.compile(r"\b[A-Z][a-z]{2,8}\.? \d{1,2}, \d{4}\b")


def _card_title(inner: str) -> str:
    for rx, grp in ((_TITLE_RE, 1), (_CLASS_TITLE_RE, 2)):
        m = rx.search(inner)
        if m and strip_tags(m.group(grp)):
            return strip_tags(m.group(grp))
    m = _ALT_RE.search(inner)
    return htmllib.unescape(m.group(1)).strip() if m else ""


def _card_date(inner: str) -> str:
    for rx, grp in ((_TIME_RE, 1), (_CLASS_DATE_RE, 2)):
        m = rx.search(inner)
        if m:
            d = parse_human_date(strip_tags(m.group(grp)))
            if d:
                return d
    m = _HUMAN_DATE_RE.search(strip_tags(inner))
    return parse_human_date(m.group(0)) if m else ""


def parse_anthropic_listing(page_html: str, source: Source) -> list[Article]:
    """Extract article cards from an anthropic.com listing page.

    Cards are anchors whose href starts with `source.path_prefix` (e.g. /news/).
    Title comes from the card heading (or image alt), date from <time>.
    """
    base = source.url
    seen: set[str] = set()
    out: list[Article] = []
    for attrs, inner in _ANCHOR_RE.findall(page_html):
        hm = _HREF_RE.search(attrs)
        if not hm:
            continue
        href = htmllib.unescape(hm.group(1))
        path = re.sub(r"^https?://(www\.)?anthropic\.com", "", href)
        if not path.startswith(source.path_prefix) or path.rstrip("/") == source.path_prefix.rstrip("/"):
            continue
        if "#" in path or "?" in path:
            continue
        url = urljoin(base, path)
        if url in seen:
            continue
        title = _card_title(inner)
        fallback = not title
        if fallback:
            title = path.rstrip("/").rsplit("/", 1)[-1].replace("-", " ").strip().capitalize()
        published = _card_date(inner)
        pm = _PARA_RE.search(inner)
        snippet = strip_tags(pm.group(1)) if pm else ""
        seen.add(url)
        out.append(Article(
            source_key=source.key, source_name=source.name, url=url,
            title=title, published=published, snippet=snippet, title_is_fallback=fallback,
        ))
    return out


def parse_rss(xml_text: str, source: Source) -> list[Article]:
    """Parse an RSS 2.0 feed into Articles (feed order preserved: newest first)."""
    root = ET.fromstring(xml_text)
    out: list[Article] = []
    seen: set[str] = set()
    for item in root.iter("item"):
        link = (item.findtext("link") or item.findtext("guid") or "").strip()
        if not link or link in seen:
            continue
        seen.add(link)
        out.append(Article(
            source_key=source.key, source_name=source.name, url=link,
            title=strip_tags(item.findtext("title") or "") or link,
            published=parse_rfc822_date(item.findtext("pubDate") or ""),
            category=(item.findtext("category") or "").strip(),
            snippet=strip_tags(item.findtext("description") or ""),
        ))
    return out


# ---------------------------------------------------------------- public API

def list_articles(source: Source, fetcher: Fetcher = fetch) -> list[Article]:
    """Download the listing for `source` and parse it. Raises FetchError."""
    raw = fetcher(source.fetch_url)
    if source.kind == "anthropic_listing":
        items = parse_anthropic_listing(raw, source)
    elif source.kind == "rss":
        items = parse_rss(raw, source)
    else:
        raise ValueError(f"unknown source kind {source.kind!r}")
    log.info("%s: %d articles listed", source.key, len(items))
    return items


_H1_RE = re.compile(r"<h1\b[^>]*>(.*?)</h1>", re.S | re.I)


def enrich_article(article: Article, source: Source, fetcher: Fetcher = fetch) -> Article:
    """Fetch the article body (and page-level title/date) when the source allows it.
    Idempotent: a second call on an already-fetched article is a no-op. Never raises."""
    if not source.fetch_bodies or article.body or article.fetch_error:
        return article
    try:
        page = fetcher(article.url)
    except FetchError as e:
        log.warning("body fetch failed for %s (%s); using snippet", article.url, e.reason)
        article.fetch_error = e.reason
        return article
    article.body = extract_article_text(page)
    if article.title_is_fallback:
        h1 = _H1_RE.search(page)
        if h1 and strip_tags(h1.group(1)):
            article.title = strip_tags(h1.group(1))
            article.title_is_fallback = False
    if not article.published:
        article.published = _page_date(page, article.body)
    return article


def _page_date(page: str, body: str) -> str:
    """Published date of an article page: og meta, else the byline (which on anthropic.com sits
    in the page header *before* <article>), else the first date in the article text."""
    m = re.search(r'property="article:published_time"\s+content="([^"]+)"', page)
    if m:
        return parse_human_date(m.group(1))
    cut = re.search(r"<article\b", page, re.I)
    header_text = strip_tags(page[: cut.start()] if cut else "")
    for text in (header_text, body[:2000]):
        m = _HUMAN_DATE_RE.search(text)
        if m:
            return parse_human_date(m.group(0))
    return ""


def parse_published_for_sort(a: Article) -> datetime:
    """Sort key for newest-first ordering; undated items go last."""
    try:
        return datetime.fromisoformat(a.published)
    except ValueError:
        return datetime.min
