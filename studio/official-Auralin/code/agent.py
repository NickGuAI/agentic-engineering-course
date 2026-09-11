#!/usr/bin/env python3
"""Local collection and publication tools for the Auralin Codex agent (stdlib only)."""
from __future__ import annotations

import argparse
import fcntl
import hashlib
import json
import re
import subprocess
import sys
import uuid
import xml.etree.ElementTree as ET
from contextlib import contextmanager
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from html import escape
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urljoin, urlsplit, urlunsplit
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parent.parent
SOURCES = json.loads((ROOT / 'code/sources.json').read_text())
VOID = {'area', 'base', 'br', 'col', 'embed', 'hr', 'img', 'input', 'link', 'meta', 'param', 'source', 'track', 'wbr'}
DATE = re.compile(r'\b(?:Jan(?:uary)?|Feb(?:ruary)?|Mar(?:ch)?|Apr(?:il)?|May|Jun(?:e)?|Jul(?:y)?|Aug(?:ust)?|Sep(?:tember)?|Oct(?:ober)?|Nov(?:ember)?|Dec(?:ember)?)\s+\d{1,2},?\s+\d{4}\b|\b\d{4}-\d{2}-\d{2}\b')


def now():
    return datetime.now(timezone.utc).isoformat()


def compact(value):
    return ' '.join(value.split())


def sha(value):
    return hashlib.sha256(value.encode()).hexdigest()


def canonical(url):
    p = urlsplit(url)
    host = (p.hostname or '').lower()
    host = {'anthropic.com': 'www.anthropic.com', 'www.openai.com': 'openai.com'}.get(host, host)
    if p.scheme != 'https' or p.username or p.password or p.port not in (None, 443):
        raise ValueError('Only ordinary HTTPS source URLs are permitted')
    # Articles linked by the approved indexes can live outside /news or /index.
    if host not in {'www.anthropic.com', 'openai.com'}:
        raise ValueError('URL outside the approved publisher hosts')
    if re.search(r'(?i)(%2e|%2f|%5c)', p.path) or '..' in p.path.split('/'):
        raise ValueError('Ambiguous URL path')
    return urlunsplit(('https', host, p.path.rstrip('/'), '', ''))


def fetch(url):
    # No shell, no redirect following, bounded request time and response size.
    result = subprocess.run(['curl', '--fail', '--silent', '--show-error', '--proto', '=https',
                             '--max-time', '25', '--max-filesize', '8000000',
                             '--retry', '1', '--retry-max-time', '40',
                             '--user-agent', 'official-Auralin/1.0 (personal research digest)',
                             canonical(url)], capture_output=True, timeout=65)
    if result.returncode:
        raise RuntimeError(compact(result.stderr.decode(errors='replace'))[:500])
    return result.stdout.decode('utf-8', errors='replace')


class Node:
    def __init__(self, tag='', attrs=()):
        self.tag, self.attrs, self.children = tag, dict(attrs), []

    def walk(self):
        yield self
        for child in self.children:
            if isinstance(child, Node):
                yield from child.walk()

    def text(self):
        if self.tag in {'script', 'style', 'nav', 'footer', 'button', 'svg'}:
            return ''
        return compact(' '.join(c.text() if isinstance(c, Node) else c for c in self.children))


class Document(HTMLParser):
    def __init__(self, html):
        super().__init__(convert_charrefs=True)
        self.root = Node()
        self.stack = [self.root]
        self.feed(html)

    def handle_starttag(self, tag, attrs):
        node = Node(tag, attrs)
        self.stack[-1].children.append(node)
        if tag not in VOID:
            self.stack.append(node)

    def handle_startendtag(self, tag, attrs):
        self.handle_starttag(tag, attrs)
        if tag not in VOID:
            self.handle_endtag(tag)

    def handle_endtag(self, tag):
        for i in range(len(self.stack) - 1, 0, -1):
            if self.stack[i].tag == tag:
                del self.stack[i:]
                break

    def handle_data(self, data):
        self.stack[-1].children.append(data)


def date_value(text):
    if not text:
        return None
    if re.match(r'^\d{4}-\d{2}-\d{2}T', text):
        text = text[:10]
    match = DATE.search(text)
    value = match.group(0) if match else text
    for fmt in ('%Y-%m-%d', '%b %d, %Y', '%B %d, %Y', '%b %d %Y', '%B %d %Y'):
        try:
            return datetime.strptime(value, fmt).date().isoformat()
        except ValueError:
            pass
    try:
        return parsedate_to_datetime(value).date().isoformat()
    except (ValueError, TypeError):
        return None


def parse_index(source, raw):
    records = {}
    if source['format'] == 'rss':
        for item in ET.fromstring(raw).findall('./channel/item'):
            try:
                url = canonical(item.findtext('link', ''))
            except ValueError:
                continue
            records[url] = dict(url=url, title=compact(item.findtext('title', '')),
                                date=date_value(item.findtext('pubDate')),
                                category=item.findtext('category', 'News'),
                                description=Document(item.findtext('description', '')).root.text())
    else:
        doc = Document(raw).root
        main = next((n for n in doc.walk() if n.tag == 'main'), doc)
        for node in main.walk():
            if node.tag != 'a' or not node.attrs.get('href'):
                continue
            try:
                url = canonical(urljoin(source['url'], node.attrs['href']))
            except ValueError:
                continue
            if not (url.startswith(source['url'].rstrip('/') + '/') or
                    (source['id'] == 'anthropic-news' and 'FeaturedGrid' in node.attrs.get('class', ''))):
                continue
            children = list(node.walk())
            heading = next((n.text() for n in children if n.tag in {'h2', 'h3', 'h4'}), '')
            title = heading or next((n.text() for n in children if '__title' in n.attrs.get('class', '')), '')
            if not title:
                continue  # Skip images, pagination, navigation and unrelated links.
            records[url] = dict(url=url, title=title, date=date_value(node.text()),
                                category='Engineering' if source['id'].endswith('engineering') else 'News')
    if not records:
        raise ValueError('No articles parsed; source may be blocked or its layout changed')
    return sorted(records.values(), key=lambda a: a['date'] or '9999', reverse=True)


def parse_article(raw):
    doc = Document(raw).root
    nodes = list(doc.walk())
    main = next((n for n in nodes if n.tag == 'main'), None)
    if main is None:
        raise ValueError('Article main element missing (blocked page or changed layout)')
    body = next((n for n in main.walk() if n.tag == 'article'), main)
    text = body.text()
    if len(text) < 200:
        raise ValueError('Article text too short to summarize reliably')
    title = next((n.text() for n in main.walk() if n.tag == 'h1'), '')
    published = next((n.attrs.get('content') for n in nodes if n.tag == 'meta' and
                      n.attrs.get('property') == 'article:published_time'), None)
    published = date_value(published) or date_value(' '.join(n.text() for n in main.walk()
        if n.tag == 'time' or '__date' in n.attrs.get('class', '')))
    if not published:
        published = date_value(text[:1000])
    return title, published, text


def atomic(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_name(path.name + '.tmp')
    temp.write_text(value, encoding='utf-8')
    temp.replace(path)


def write_json(path, value):
    atomic(path, json.dumps(value, ensure_ascii=False, indent=2) + '\n')


def read_state(runtime):
    path = runtime / 'state.json'
    return json.loads(path.read_text()) if path.exists() else {'revision': 0, 'sources': {}, 'articles': {}}


@contextmanager
def locked(runtime):
    runtime.mkdir(parents=True, exist_ok=True)
    with (runtime / '.lock').open('a') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        yield


def event(run, kind, **data):
    with (run / 'trace.jsonl').open('a', encoding='utf-8') as stream:
        stream.write(json.dumps(dict(at=now(), event=kind, **data), ensure_ascii=False) + '\n')


def collect(runtime, fetcher=fetch):
    state = read_state(runtime)
    run = runtime / 'runs' / (datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ-') + uuid.uuid4().hex[:8])
    run.mkdir(parents=True)
    packet = dict(run_id=run.name, collected_at=now(), revision=state['revision'], articles=[], sources=[], baseline={})
    event(run, 'started', revision=state['revision'])
    selected = {}
    for source in SOURCES:
        report = dict(id=source['id'], url=source['url'], status='ok', errors=[], warnings=[])
        packet['sources'].append(report)
        try:
            raw = fetcher(source.get('feed', source['url']))
            atomic(run / (source['id'] + '.index'), raw)
            index = parse_index(source, raw)
            report['discovered'] = len(index)
            known = set(state['sources'].get(source['id'], []))
            first = source['id'] not in state['sources']
            # Initial baseline reports five; later runs drain up to ten unseen URLs per source.
            unseen = [a for a in index if a['url'] not in known]
            chosen = unseen[:5 if first else 10]
            report['deferred'] = max(0, len(unseen) - len(chosen)) if not first else 0
            packet['baseline'][source['id']] = [a['url'] for a in index[5:]] if first else []
            # Recheck the five newest indexed articles that were previously summarized.
            if not first:
                chosen += [a for a in index[:5] if a['url'] in state['articles'] and a not in chosen]
            for article in chosen:
                item = selected.setdefault(article['url'], dict(article, sources=[]))
                item['sources'].append(source['id'])
        except (RuntimeError, ValueError, OSError, ET.ParseError, subprocess.TimeoutExpired) as exc:
            report['status'] = 'failed'
            report['errors'].append(str(exc))
        event(run, 'source', **report)
    for url, item in selected.items():
        try:
            item['coverage'] = 'full-article'
            try:
                raw = fetcher(url)
                title, published, text = parse_article(raw)
            except (RuntimeError, ValueError, OSError, subprocess.TimeoutExpired) as exc:
                if len(item.get('description', '')) < 50:
                    raise
                # The publisher's RSS description is evidence, but not a full article.
                raw = ''
                title, published, text = item['title'], item['date'], item['description']
                item['coverage'] = 'rss-description'
                for report in packet['sources']:
                    if report['id'] in item['sources']:
                        report['warnings'].append(f'{url}: using official RSS description; full article unavailable: {exc}')
            item.update(title=item['title'] or title, date=published or item['date'], text=text[:60000],
                        truncated=len(text) > 60000, content_sha256=sha(text))
            old = state['articles'].get(url)
            item['change'] = 'updated' if old else 'new'
            if not item['date']:
                raise ValueError('Publication date unavailable; article needs manual review')
            if item['date'] > datetime.now(timezone.utc).date().isoformat():
                raise ValueError('Future publication date; article deferred')
            if old and old['content_sha256'] == item['content_sha256']:
                event(run, 'unchanged', url=url)
                continue
            item['previous_summary'] = old.get('summary') if old else None
            if raw:
                atomic(run / (sha(url)[:16] + '.html'), raw)
            packet['articles'].append(item)
            event(run, 'article', url=url, change=item['change'], content_sha256=item['content_sha256'])
        except (RuntimeError, ValueError, OSError, subprocess.TimeoutExpired) as exc:
            for report in packet['sources']:
                if report['id'] in item['sources']:
                    report['status'] = 'partial'
                    report['errors'].append(f'{url}: {exc}')
            event(run, 'article_failed', url=url, error=str(exc))
    write_json(run / 'packet.json', packet)
    event(run, 'collected', articles=len(packet['articles']), sources=packet['sources'])
    return run


def validate_summaries(packet, summaries):
    if not isinstance(summaries, list) or not all(isinstance(s, dict) for s in summaries):
        raise ValueError('Summaries must be a JSON array of objects')
    expected = {a['url']: a for a in packet['articles']}
    if len(summaries) != len(expected) or {s.get('url') for s in summaries} != set(expected):
        raise ValueError('Supply exactly one summary for every packet article; no invented or missing URLs')
    for summary in summaries:
        for key in ('summary', 'why_it_matters', 'category', 'evidence'):
            if not isinstance(summary.get(key), str) or not 1 <= len(summary[key]) <= 3000:
                raise ValueError(f'Missing or oversized {key}')
        if type(summary.get('material')) is not bool:
            raise ValueError('material must be a boolean')
        if summary['category'] not in {'Research', 'Engineering', 'Product', 'Safety', 'Policy', 'Company'}:
            raise ValueError('Unsupported category')
        article = expected[summary['url']]
        quote = compact(summary['evidence'])
        if len(quote) < 15 or len(quote.split()) > 25 or quote not in compact(article['text']):
            raise ValueError('Evidence must be a verbatim 15+ character excerpt, at most 25 words')
        if article['change'] == 'new' and not summary['material']:
            raise ValueError('New articles must be included in the digest')


def md(value):
    return escape(compact(value)).replace('[', '\\[').replace(']', '\\]').replace('*', '\\*').replace('`', '\\`')


def report_day(packet):
    return datetime.fromisoformat(packet['collected_at']).astimezone(ZoneInfo('America/New_York')).date().isoformat()


def report_entries(packet, summaries):
    lookup = {s['url']: s for s in summaries}
    return {a['url']: (a, lookup[a['url']]) for a in packet['articles'] if lookup[a['url']]['material']}


def render_report(day, entries):
    lines = [f'# Auralin research update — {day}', '', 'Daily report · Eastern time', '']
    for article, summary in entries.values():
        lines += [f"## [{md(article['title'])}]({article['url']})", '',
                  f"{article['date']} · {', '.join(article['sources'])} · {md(summary['category'])} · {article['change']}", '',
                  md(summary['summary']), '', '**Why it matters (analysis):** ' + md(summary['why_it_matters']), '',
                  '> ' + md(summary['evidence']), '']
    if not entries:
        lines += ['No article summaries were published for this date.', '']
    return '\n'.join(lines)


def coverage_log(run, packet):
    lines = [f"Collected: {packet['collected_at']}"]
    for source in packet['sources']:
        lines.append(f"{source['id']}: {source['status']}; discovered {source.get('discovered', 0)}; deferred {source.get('deferred', 0)}")
        lines.extend('ERROR: ' + error for error in source['errors'])
        lines.extend('WARNING: ' + warning for warning in source.get('warnings', []))
    for article in packet['articles']:
        lines.append(f"{article['url']}: coverage={article.get('coverage', 'full-article')}; truncated={article['truncated']}")
    atomic(run / 'coverage.log', '\n'.join(lines) + '\n')


def completed_runs(runtime):
    for result in sorted((runtime / 'runs').glob('*/result.json')):
        run = result.parent
        yield run, json.loads((run / 'packet.json').read_text()), json.loads((run / 'summaries.json').read_text())


def write_daily_report(runtime, day, current=None):
    entries = {}
    for _, packet, summaries in completed_runs(runtime):
        if report_day(packet) == day:
            entries.update(report_entries(packet, summaries))
    if current:
        entries.update(report_entries(*current))
    path = runtime / 'reports' / (day + '.md')
    text = render_report(day, entries)
    # Do not even rewrite an unchanged day's report on an empty repeat run.
    if not path.exists() or path.read_text() != text:
        atomic(path, text)
    return path


def rebuild_reports(runtime):
    """Reformat completed runs without fetching, resummarizing, or changing state."""
    days = set()
    for run, packet, _ in completed_runs(runtime):
        coverage_log(run, packet)
        days.add(report_day(packet))
    return [str(write_daily_report(runtime, day)) for day in sorted(days)]


def publish(runtime, run_id, summaries):
    if not re.fullmatch(r'\d{8}T\d{6}Z-[a-f0-9]{8}', run_id):
        raise ValueError('Invalid run ID')
    run = runtime / 'runs' / run_id
    packet = json.loads((run / 'packet.json').read_text())
    state = read_state(runtime)
    if state['revision'] != packet['revision']:
        raise ValueError('Stale or already published run; collect a fresh packet')
    validate_summaries(packet, summaries)
    entries = report_entries(packet, summaries)
    count = len(entries)
    day = report_day(packet)
    digest = render_report(day, entries)
    lookup = {s['url']: s for s in summaries}
    for article in packet['articles']:
        summary = lookup[article['url']]
        state['articles'][article['url']] = dict(content_sha256=article['content_sha256'], summary=summary['summary'])
        for source_id in article['sources']:
            state['sources'].setdefault(source_id, []).append(article['url'])
    for source_id, urls in packet['baseline'].items():
        state['sources'][source_id] = sorted(set(state['sources'].get(source_id, []) + urls))
    # Persist output before advancing deduplication state. Revision makes publication single-use.
    write_json(run / 'summaries.json', summaries)
    coverage_log(run, packet)
    atomic(run / 'digest.md', digest)
    daily = write_daily_report(runtime, day, (packet, summaries))
    state['revision'] += 1
    state['last_run'] = run_id
    write_json(runtime / 'state.json', state)
    failures = sum(s['status'] != 'ok' for s in packet['sources'])
    event(run, 'published', articles=count, failed_sources=failures, digest_sha256=sha(digest))
    limited = sum(bool(s.get('warnings')) for s in packet['sources'])
    result = dict(run_id=run_id, articles=count, failed_sources=failures, limited_sources=limited,
                  notify=bool(count or failures), digest=str(daily), log=str(run / 'coverage.log'))
    write_json(run / 'result.json', result)
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--runtime', type=Path, default=ROOT / 'outputs/live')
    sub = parser.add_subparsers(dest='command', required=True)
    sub.add_parser('collect')
    sub.add_parser('rebuild-reports')
    pub = sub.add_parser('publish')
    pub.add_argument('run_id')
    pub.add_argument('summaries', type=Path)
    args = parser.parse_args()
    try:
        with locked(args.runtime):
            if args.command == 'collect':
                run = collect(args.runtime)
                print(json.dumps(dict(run_id=run.name, packet=str(run / 'packet.json'))))
            elif args.command == 'rebuild-reports':
                print(json.dumps({'reports': rebuild_reports(args.runtime)}))
            else:
                print(json.dumps(publish(args.runtime, args.run_id, json.loads(args.summaries.read_text()))))
    except (ValueError, OSError, KeyError) as exc:
        print(json.dumps({'error': str(exc)}), file=sys.stderr)
        sys.exit(1)


if __name__ == '__main__':
    main()
