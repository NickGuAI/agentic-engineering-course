"""Bounded publisher collection. Public bodies stay only in ignored work storage."""
import hashlib
import http.client
import ipaddress
import json
import re
import socket
import ssl
import time
import xml.etree.ElementTree as ET
from datetime import date, datetime, timedelta, timezone
from email.utils import parsedate_to_datetime
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urljoin, urlsplit, urlunsplit
from zoneinfo import ZoneInfo

PARSER_VERSION = "publisher-html-v1"
SOURCES = (
    ("openai_news", "https://openai.com/news/", "https://openai.com/news/rss.xml"),
    ("anthropic_news", "https://www.anthropic.com/news", None),
    ("anthropic_engineering", "https://www.anthropic.com/engineering", None),
)
_DATE = re.compile(r"\b(?:Jan(?:uary)?|Feb(?:ruary)?|Mar(?:ch)?|Apr(?:il)?|May|Jun(?:e)?|Jul(?:y)?|Aug(?:ust)?|Sep(?:tember)?|Oct(?:ober)?|Nov(?:ember)?|Dec(?:ember)?)\s+\d{1,2},?\s+\d{4}\b")
_VOID = {"area", "base", "br", "col", "embed", "hr", "img", "input", "link", "meta", "param", "source", "track", "wbr"}
_SKIP = {"script", "style", "nav", "footer", "svg", "noscript", "button"}


class SourceError(Exception):
    def __init__(self, code):
        self.code = code
        super().__init__(code)


def approved_url(url, article=False):
    """Exact hosts/paths only; no credentials, ports, queries, escapes or fragments."""
    try:
        if not isinstance(url, str) or any(ord(c) < 33 for c in url):
            return False
        u = urlsplit(url)
        if u.scheme != "https" or u.username or u.password or u.port or u.query or u.fragment:
            return False
        if u.netloc != u.hostname or "%" in u.path or "\\" in url or "//" in u.path:
            return False
        if u.hostname == "openai.com":
            return bool(re.fullmatch(r"/index/[a-zA-Z0-9_-]+/?", u.path)) or (
                not article and u.path in {"/news", "/news/", "/news/rss.xml"})
        if u.hostname == "www.anthropic.com":
            return bool(re.fullmatch(r"/(news|engineering|institute)/[a-zA-Z0-9_-]+/?", u.path)) or (
                not article and u.path in {"/news", "/news/", "/engineering", "/engineering/"})
    except (ValueError, TypeError):
        pass
    return False


def canonical_url(url):
    u = urlsplit(url)
    return urlunsplit((u.scheme, u.netloc, u.path.rstrip("/"), "", ""))


def parse_date(value):
    """Return ISO value plus precision; timestamps must include an offset."""
    if not isinstance(value, str):
        raise SourceError("missing_date")
    value = value.strip()
    try:
        if re.fullmatch(r"\d{4}-\d{2}-\d{2}", value):
            return date.fromisoformat(value).isoformat(), "date"
        if re.match(r"^\d{4}-\d{2}-\d{2}T", value):
            d = datetime.fromisoformat(value.replace("Z", "+00:00"))
        else:
            try:
                d = parsedate_to_datetime(value)
            except (ValueError, TypeError):
                match = _DATE.search(value)
                if not match:
                    raise ValueError
                cleaned = match.group().replace(",", "")
                for fmt in ("%b %d %Y", "%B %d %Y"):
                    try:
                        return datetime.strptime(cleaned, fmt).date().isoformat(), "date"
                    except ValueError:
                        pass
                raise ValueError
        if d.tzinfo is None:
            raise ValueError
        return d.astimezone(timezone.utc).isoformat(), "timestamp"
    except (ValueError, TypeError, OverflowError):
        raise SourceError("invalid_date")


def exclusion_reason(article, as_of, days, timezone_name="America/New_York"):
    if article.get("date_conflict"):
        return "conflicting_dates"
    try:
        value, precision = parse_date(article.get("published_at"))
        if article.get("date_precision", precision) != precision:
            return "invalid_date_precision"
        if as_of.tzinfo is None:
            return "invalid_clock"
        tz = ZoneInfo(timezone_name)
        today = as_of.astimezone(tz).date()
        if precision == "timestamp":
            dt = datetime.fromisoformat(value)
            if dt > as_of:
                return "future_date"
            published = dt.astimezone(tz).date()
        else:
            published = date.fromisoformat(value)
        if published > today:
            return "future_date"
        if published < today - timedelta(days=days - 1):
            return "outside_window"
        return None
    except SourceError as exc:
        return exc.code
    except (ValueError, TypeError, KeyError):
        return "invalid_date"


def eligible(article, as_of, days, timezone="America/New_York"):
    return exclusion_reason(article, as_of, days, timezone) is None


class _Node:
    def __init__(self, tag="root", attrs=None):
        self.tag, self.attrs, self.children = tag, attrs or {}, []

    def _raw_text(self):
        if self.tag in _SKIP:
            return ""
        text = "".join(c if isinstance(c, str) else c._raw_text() for c in self.children)
        return text + (" " if self.tag in {"p", "div", "li", "time", "br", "h1", "h2", "h3", "h4"} else "")

    def text(self):
        return re.sub(r"\s+", " ", self._raw_text()).strip()

    def walk(self):
        yield self
        for c in self.children:
            if isinstance(c, _Node) and c.tag not in _SKIP:
                yield from c.walk()


class _HTML(HTMLParser):
    def __init__(self, body):
        super().__init__(convert_charrefs=True)
        self.root = _Node()
        self.stack = [self.root]
        self.feed(body)

    def handle_starttag(self, tag, attrs):
        node = _Node(tag, dict(attrs))
        self.stack[-1].children.append(node)
        if tag not in _VOID:
            self.stack.append(node)

    def handle_startendtag(self, tag, attrs):
        self.handle_starttag(tag, attrs)
        if tag not in _VOID:
            self.handle_endtag(tag)

    def handle_endtag(self, tag):
        for i in range(len(self.stack) - 1, 0, -1):
            if self.stack[i].tag == tag:
                del self.stack[i:]
                return

    def handle_data(self, data):
        self.stack[-1].children.append(data)


def _choose_date(values):
    parsed = []
    for value, provenance in values:
        if value:
            normalized, precision = parse_date(value)
            parsed.append((normalized, precision, provenance))
    if not parsed:
        raise SourceError("missing_date")
    timestamps = [datetime.fromisoformat(v) for v, p, _ in parsed if p == "timestamp"]
    dates = {date.fromisoformat(v) for v, p, _ in parsed if p == "date"}
    if len(set(timestamps)) > 1 or len(dates) > 1:
        raise SourceError("conflicting_dates")
    if timestamps and dates:
        d = timestamps[0]
        if next(iter(dates)) not in {d.date(), d.astimezone(ZoneInfo("America/New_York")).date()}:
            raise SourceError("conflicting_dates")
    winner = next((p for p in parsed if p[1] == "timestamp"), parsed[0])
    return winner[0], winner[1], sorted({p[2] for p in parsed})


def parse_feed(body, source_id="openai_news"):
    if "<!DOCTYPE" in body.upper() or "<!ENTITY" in body.upper():
        raise SourceError("unsafe_xml")
    try:
        root = ET.fromstring(body)
    except ET.ParseError:
        raise SourceError("index_parse_error")
    channel = root.find("channel")
    if root.tag != "rss" or channel is None:
        raise SourceError("index_parse_error")
    candidates = []
    for item in channel.findall("item"):
        url = (item.findtext("link") or "").strip()
        if not approved_url(url, article=True):
            continue
        record = {"source_id": source_id, "url": canonical_url(url),
                  "title": (item.findtext("title") or "").strip(), "date_provenance": ["rss:pubDate"]}
        try:
            record["published_at"], record["date_precision"] = parse_date(item.findtext("pubDate"))
        except SourceError:
            record["published_at"] = None
        candidates.append(record)
    if channel.findall("item") and not candidates:
        raise SourceError("index_parse_error")
    return candidates


def parse_index(body, url, source_id):
    root = _HTML(body).root
    main = next((n for n in root.walk() if n.tag == "main"), None)
    if main is None:
        raise SourceError("index_parse_error")
    candidates, seen = [], set()
    for node in main.walk():
        if node.tag != "a":
            continue
        link = urljoin(url, node.attrs.get("href", ""))
        if not approved_url(link, article=True):
            continue
        if source_id == "anthropic_engineering" and "/engineering/" not in link:
            continue
        if source_id == "anthropic_news" and not any(p in link for p in ("/news/", "/institute/")):
            continue
        link = canonical_url(link)
        if link in seen:
            continue
        seen.add(link)
        headings = [n.text() for n in node.walk() if n.tag in {"h2", "h3", "h4"}]
        record = {"source_id": source_id, "url": link, "title": headings[0] if headings else node.text(),
                  "published_at": None, "date_provenance": ["index:visible_date"]}
        times = [(n.attrs.get("datetime") or n.text(), "index:time") for n in node.walk() if n.tag == "time"]
        if not times:
            times = [(m.group(), "index:visible_date") for m in _DATE.finditer(node.text())]
        try:
            record["published_at"], record["date_precision"], record["date_provenance"] = _choose_date(times)
        except SourceError as exc:
            if exc.code == "conflicting_dates":
                record["date_conflict"] = True
        candidates.append(record)
    if not candidates:
        # A changed/challenge page is not proof that a publisher has no news.
        raise SourceError("index_parse_error")
    return candidates


def parse_article(body, url, source_id, candidate=None):
    root = _HTML(body).root
    main = next((n for n in root.walk() if n.tag == "main"), None)
    if main is None:
        raise SourceError("article_parse_error")
    scope = next((n for n in main.walk() if n.tag == "article"), main)
    # Institute stories place their title in a main/header before the article body.
    title = next((n.text() for n in main.walk() if n.tag == "h1"), "")
    if not title:
        raise SourceError("missing_title")
    values = []
    for n in root.walk():
        if n.tag == "meta" and (n.attrs.get("property") or n.attrs.get("name")) in {"article:published_time", "datePublished", "date"}:
            values.append((n.attrs.get("content"), "html:publication_meta"))
    paragraphs = []
    before_body = True
    for n in scope.walk():
        text = n.text()
        if n.tag in {"h2", "h3"} and text.lower() in {"related content", "keep reading", "related articles"}:
            break
        if n.tag == "p" and len(text) >= 30 and n.attrs.get("aria-hidden") != "true":
            paragraphs.append(text)
            before_body = False
        if n.tag == "li" and len(text) >= 30 and not any(c.tag == "p" for c in n.walk()):
            paragraphs.append(text)
        if before_body and n.tag == "time":
            values.append((n.attrs.get("datetime") or text, "html:time"))
        elif before_body and n.tag in {"div", "span", "p"} and len(text) < 55:
            match = _DATE.search(text)
            if match:
                values.append((match.group(), "html:visible_publication_date"))
    if candidate and candidate.get("published_at"):
        values.append((candidate["published_at"], "discovery:" + "+".join(candidate.get("date_provenance", []))))
    published, precision, provenance = _choose_date(values)
    paragraphs = list(dict.fromkeys(paragraphs))
    if not paragraphs or sum(len(p) for p in paragraphs) < 150:
        raise SourceError("insufficient_article_text")
    canonical = canonical_url(url)
    for n in root.walk():
        if n.tag == "link" and n.attrs.get("rel") == "canonical":
            proposed = urljoin(url, n.attrs.get("href", ""))
            if not approved_url(proposed, article=True) or urlsplit(proposed).hostname != urlsplit(url).hostname:
                raise SourceError("unapproved_canonical")
            canonical = canonical_url(proposed)
    return {"article_id": "a-" + hashlib.sha256(canonical.encode()).hexdigest()[:16],
            "source_id": source_id, "url": canonical, "title": title,
            "published_at": published, "date_precision": precision, "date_provenance": provenance,
            "paragraphs": [{"id": "p%03d" % (i + 1), "text": p} for i, p in enumerate(paragraphs)],
            "content_hash": hashlib.sha256("\n\n".join(paragraphs).encode()).hexdigest(),
            "parser_version": PARSER_VERSION}


class _PinnedHTTPS(http.client.HTTPSConnection):
    def __init__(self, host, address, timeout):
        super().__init__(host, timeout=timeout, context=ssl.create_default_context())
        self.address = address

    def connect(self):
        # Resolve once, validate all answers, and connect to the validated numeric IP.
        sock = socket.create_connection((self.address, 443), self.timeout)
        self.sock = self._context.wrap_socket(sock, server_hostname=self.host)


def _request_once(url, timeout, byte_limit):
    host = urlsplit(url).hostname
    deadline = time.monotonic() + timeout
    try:
        addresses = [r[4][0] for r in socket.getaddrinfo(host, 443, type=socket.SOCK_STREAM)]
        if not addresses or any(not ipaddress.ip_address(a).is_global for a in addresses):
            raise SourceError("private_destination")
        connection = _PinnedHTTPS(host, addresses[0], max(0.01, deadline - time.monotonic()))
        try:
            connection.request("GET", urlsplit(url).path or "/", headers={
                "User-Agent": "Studio1ResearchAgent/0.1", "Accept-Encoding": "identity",
                "Accept": "text/html,application/rss+xml,application/xml,text/xml"})
            # getresponse() may detach a Connection: close socket from connection;
            # retain it so each streaming read still gets the remaining deadline.
            transport_socket = connection.sock
            transport_socket.settimeout(max(0.01, deadline - time.monotonic()))
            response = connection.getresponse()
            if response.status in {301, 302, 303, 307, 308}:
                return response.status, response.getheader("Location"), b""
            if response.status != 200:
                return response.status, None, b""
            declared = response.getheader("Content-Length")
            if declared and int(declared) > byte_limit:
                raise SourceError("response_too_large")
            if response.getheader("Content-Encoding", "identity") != "identity":
                raise SourceError("unsupported_encoding")
            content_type = response.getheader("Content-Type", "").split(";")[0].strip()
            if content_type not in {"text/html", "application/xhtml+xml", "application/rss+xml", "application/xml", "text/xml"}:
                raise SourceError("unsupported_content_type")
            chunks, size = [], 0
            while True:
                remaining = deadline - time.monotonic()
                if remaining <= 0:
                    raise SourceError("network_error")
                transport_socket.settimeout(remaining)
                chunk = response.read1(min(65536, byte_limit + 1 - size))
                if time.monotonic() >= deadline:
                    raise SourceError("network_error")
                if not chunk:
                    break
                chunks.append(chunk)
                size += len(chunk)
                if size > byte_limit:
                    raise SourceError("response_too_large")
            body = b"".join(chunks)
            return response.status, None, body
        finally:
            connection.close()
    except SourceError:
        raise
    except (OSError, http.client.HTTPException, ValueError):
        raise SourceError("network_error")


class _HTTP:
    def __init__(self, policy, before_request):
        self.policy, self.before_request = policy, before_request
        self.attempts = self.retries = 0

    def get(self, url):
        current, redirects, retried = url, 0, set()
        while True:
            if not approved_url(current):
                raise SourceError("unapproved_url")
            if self.attempts >= self.policy.get("max_http_attempts", 16):
                raise SourceError("http_attempt_limit")
            try:
                self.before_request(current)
            except Exception:
                raise SourceError("request_policy_limit")
            self.attempts += 1
            try:
                timeout = self.policy.get("http_timeout_seconds", 10)
                supervisor = getattr(self.before_request, "__self__", None)
                if supervisor is not None and hasattr(supervisor, "remaining_seconds"):
                    timeout = min(timeout, supervisor.remaining_seconds())
                    if timeout <= 0:
                        raise SourceError("request_policy_limit")
                status, location, body = _request_once(current, timeout, self.policy.get("max_response_bytes", 2097152))
            except SourceError as exc:
                if exc.code != "network_error":
                    raise
                status, location, body = 503, None, None
            if status in {301, 302, 303, 307, 308}:
                redirects += 1
                next_url = urljoin(current, location or "")
                if redirects > 3 or not location or next_url == current:
                    raise SourceError("redirect_limit")
                if not approved_url(next_url) or urlsplit(next_url).hostname != urlsplit(url).hostname:
                    raise SourceError("unapproved_redirect")
                current = next_url
                continue
            if status in {408, 429, 500, 502, 503, 504} and current not in retried and self.retries < self.policy.get("max_http_retries", 3):
                retried.add(current)
                self.retries += 1
                continue
            if status != 200:
                raise SourceError("network_error" if body is None else "http_%d" % status)
            try:
                return body.decode("utf-8"), current
            except UnicodeDecodeError:
                raise SourceError("invalid_encoding")


def _save_snapshot(work_dir, identifier, body):
    path = Path(work_dir) / (identifier + ".html")
    if path.is_symlink():
        raise SourceError("unsafe_snapshot_path")
    if path.exists():
        if path.read_text(encoding="utf-8") == body:
            return
        raise SourceError("snapshot_conflict")
    with path.open("x", encoding="utf-8") as stream:
        stream.write(body)


def collect_sources(policy, as_of, before_request, work_dir):
    """Collect all indexes before article fetches; return explicit partial coverage."""
    work_dir = Path(work_dir)
    work_dir.mkdir(parents=True, exist_ok=True)
    http = _HTTP(policy, before_request)
    result = {"articles": [], "sources": [], "coverage_limited": False, "coverage_reasons": [], "exclusions": []}
    queues = []
    days = policy.get("days", 7)
    timezone_name = policy.get("timezone", "America/New_York")
    for source_id, index_url, feed_url in SOURCES:
        status = {"source_id": source_id, "url": index_url, "status": "ok", "candidate_count": 0}
        result["sources"].append(status)
        try:
            # This publisher-linked RSS endpoint was verified during the adapter spike.
            body, final_url = http.get(feed_url or index_url)
            _save_snapshot(work_dir, source_id + "-" + hashlib.sha256(body.encode()).hexdigest()[:12], body)
            candidates = parse_feed(body, source_id) if feed_url else parse_index(body, final_url, source_id)
            status.update({"final_url": final_url, "retrieved_at": datetime.now(timezone.utc).isoformat(),
                           "body_hash": hashlib.sha256(body.encode()).hexdigest()})
            usable = []
            for candidate in candidates:
                reason = exclusion_reason(candidate, as_of, days, timezone_name)
                if reason is None or reason == "missing_date":
                    usable.append(candidate)
                elif reason != "outside_window":
                    result["exclusions"].append({"source_id": source_id, "url": candidate["url"], "reason": reason})
                    if reason != "future_date":
                        result["coverage_limited"] = True
                        status.update({"status": "error", "error_code": reason, "coverage_limited": True})
            status["candidate_count"] = len(usable)
            queues.append(sorted(usable, key=lambda a: (a.get("published_at") or "", a["url"]), reverse=True))
        except SourceError as exc:
            status.update({"status": "error", "error_code": exc.code})
            result["coverage_limited"] = True
            queues.append([])
    # Round-robin candidate admission prevents the first publisher exhausting the cap.
    candidates, seen = [], set()
    while any(queues):
        for queue in queues:
            if queue:
                item = queue.pop(0)
                if item["url"] not in seen:
                    seen.add(item["url"])
                    candidates.append(item)
        if len(candidates) >= policy.get("max_candidates", 30):
            break
    cap = policy.get("max_candidates", 30)
    if any(queues) or len(candidates) > cap:
        result["coverage_limited"] = True
        result["coverage_reasons"].append("candidate_limit")
    candidates = candidates[:cap]
    candidates.sort(key=lambda a: (a.get("published_at") or "", a["url"]), reverse=True)
    max_fetches = policy.get("max_article_fetches", 10)
    if len(candidates) > max_fetches:
        result["coverage_limited"] = True
        result["coverage_reasons"].append("article_fetch_limit")
    statuses = {s["source_id"]: s for s in result["sources"]}
    for skipped in candidates[max_fetches:]:
        statuses[skipped["source_id"]]["coverage_limited"] = True
        result["exclusions"].append({"source_id": skipped["source_id"], "url": skipped["url"], "reason": "article_fetch_limit"})
    for candidate in candidates[:max_fetches]:
        source_id, url = candidate["source_id"], candidate["url"]
        try:
            body, final_url = http.get(url)
            _save_snapshot(work_dir, "article-" + hashlib.sha256((url + body).encode()).hexdigest()[:20], body)
            article = parse_article(body, final_url, source_id, candidate)
            article.update({"requested_url": url, "final_url": final_url,
                            "retrieved_at": datetime.now(timezone.utc).isoformat(), "http_status": 200})
            reason = exclusion_reason(article, as_of, days, timezone_name)
            if reason:
                result["exclusions"].append({"source_id": source_id, "url": url, "reason": reason})
                if reason not in {"outside_window", "future_date"}:
                    result["coverage_limited"] = True
                    statuses[source_id].update({"status": "error", "error_code": reason, "coverage_limited": True})
                continue
            result["articles"].append(article)
        except SourceError as exc:
            result["coverage_limited"] = True
            statuses[source_id].update({"status": "error", "error_code": exc.code})
            result["exclusions"].append({"source_id": source_id, "url": url, "reason": exc.code})
    result["articles"].sort(key=lambda a: (a["published_at"], a["url"]), reverse=True)
    result["http_attempts"] = http.attempts
    return result
