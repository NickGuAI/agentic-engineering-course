#!/usr/bin/env python3
"""Daily, source-linked news briefing. Requires curl; delivery uses local sendmail."""
import argparse
import datetime as dt
import email.message
import fcntl
import html
from html.parser import HTMLParser
import os
from pathlib import Path
import re
import subprocess
import sys
import xml.etree.ElementTree as ET
from email.utils import parsedate_to_datetime
from urllib.parse import urljoin, urlparse
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "outputs"
TZ = ZoneInfo("America/New_York")
ANTHROPIC = "https://www.anthropic.com/news"
OPENAI_RSS = "https://openai.com/news/rss.xml"
DATE = re.compile(r"\b(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec) \d{1,2}, 20\d{2}")
SENTENCES = re.compile(r"(?<=[.!?])\s+(?=[A-Z])")


class Links(HTMLParser):
    def __init__(self):
        super().__init__()
        self.current = None
        self.links = []

    def handle_starttag(self, tag, attrs):
        if tag == "a":
            self.current = [dict(attrs).get("href", ""), ""]

    def handle_data(self, data):
        if self.current is not None:
            self.current[1] += data

    def handle_endtag(self, tag):
        if tag == "a" and self.current is not None:
            self.links.append(tuple(self.current))
            self.current = None


class Paragraphs(HTMLParser):
    def __init__(self):
        super().__init__()
        self.active = False
        self.parts = []
        self.paragraphs = []

    def handle_starttag(self, tag, attrs):
        if tag == "p":
            self.active = True
            self.parts = []

    def handle_data(self, data):
        if self.active:
            self.parts.append(data)

    def handle_endtag(self, tag):
        if tag == "p" and self.active:
            value = " ".join(" ".join(self.parts).split())
            if 70 <= len(value) <= 1000:
                self.paragraphs.append(value)
            self.active = False


def article_summary(url):
    parser = Paragraphs()
    parser.feed(fetch(url))
    paragraphs = [p for p in parser.paragraphs if not any(x in p.lower() for x in ("cookie", "privacy policy", "subscribe"))]
    if len(paragraphs) < 2:
        raise ValueError("not enough official article text to summarize")
    first = SENTENCES.split(paragraphs[0])
    summary = " ".join(first[:2])
    why = SENTENCES.split(paragraphs[1])[0]
    launch = re.match(r"Today, we are introducing (.*?), which gives (.*?) access to (.*?) with (.*?)\.", first[0])
    opening = re.match(r"We have already onboarded (.*?), and are now opening applications to (.*?)\.", first[1]) if len(first) > 1 else None
    if launch and opening:
        program, audience, models, _ = launch.groups()
        early_users, new_audience = opening.groups()
        early_users = re.sub(r" through an early-access program$", "", early_users)
        models = models.replace("our ", "Anthropic's ")
        new_audience = re.sub(r"\s*\([^)]*\)", "", new_audience)
        summary = (f"Anthropic introduced {program} to give {audience} access to {models}. "
                   f"After early access with {early_users}, applications are open to {new_audience}.")
    impact = re.search(r"like (.*?)(?:\. |\.$)", paragraphs[1])
    if impact:
        why = f"The program is intended to support {impact.group(1)}, work that Anthropic's generally available models currently block."
    return summary, why


def feed_summary(description, title):
    description = " ".join(description.split()).rstrip(".!?")
    if not description:
        raise ValueError("RSS item lacks a description")
    if ", helping " in description:
        claim, benefit = description.split(", helping ", 1)
        if " and " in benefit:
            first, second = benefit.rsplit(" and ", 1)
            audience = first.split(" ", 1)[0]
            return claim + ". The source says it helps " + first + ".", "It also aims to help " + audience + " " + second + "."
        return claim + ". The source says it helps " + benefit + ".", "The stated benefit is " + benefit + "."
    if ", " in description:
        claim, detail = description.split(", ", 1)
        detail = detail.removeprefix("and ")
        if ", and " in detail:
            features, impact = detail.rsplit(", and ", 1)
            if features.count(", ") == 1:
                features = features.replace(", ", " and ")
            return claim + ". The feed also lists " + features + ".", "The source highlights " + impact + "."
        return claim + ". The feed also lists " + detail + ".", "The source highlights " + detail + "."
    return description + ". OpenAI lists this development as “" + title + ".”", "The stated development is " + description[0].lower() + description[1:] + "."


def fetch(url):
    p = subprocess.run(["curl", "-fsSL", "--retry", "2", "--max-time", "25", url],
                       capture_output=True, text=True, timeout=85)
    if p.returncode:
        raise RuntimeError(p.stderr.strip().splitlines()[-1] if p.stderr.strip() else "fetch failed")
    return p.stdout


def anthropic_items(html_text, days):
    parser = Links()
    parser.feed(html_text)
    seen = set()
    found = []
    for href, label in parser.links:
        url = urljoin(ANTHROPIC, href)
        path = urlparse(url).path
        if urlparse(url).netloc != urlparse(ANTHROPIC).netloc or url in seen:
            continue
        if not path.startswith("/news/"):
            continue
        match = DATE.search(label)
        if not match:
            continue
        published = dt.datetime.strptime(match.group(), "%b %d, %Y").date()
        if published not in days:
            continue
        title = label[match.end():].strip()
        title = re.sub(r"^(Announcements|Product|Research|Safety|Engineering|Applied AI|Company|Policy|Features)", "", title).strip()
        if not title:
            continue
        seen.add(url)
        found.append((published, title, url))
    return sorted(found, reverse=True)[:3]


def openai_items(xml_text, days):
    root = ET.fromstring(xml_text)
    if root.tag != "rss":
        raise ValueError("not an RSS feed")
    found = []
    for item in root.findall("./channel/item"):
        title = (item.findtext("title") or "").strip()
        link = (item.findtext("link") or "").strip()
        description = (item.findtext("description") or "").strip()
        date_text = (item.findtext("pubDate") or "").strip()
        if not all((title, link, description, date_text)):
            continue
        parsed = urlparse(link)
        if parsed.scheme != "https" or parsed.netloc != "openai.com" or not parsed.path.startswith("/index/"):
            continue
        published = parsedate_to_datetime(date_text).date()
        if published in days:
            found.append((published, title, link, description))
    return sorted(found, reverse=True)[:3]


def markdown(now, sections):
    lines = [f"# AI research news briefing — {now:%B %d, %Y}", "",
             "Official headlines dated today or yesterday. Summaries use only the linked official article or official OpenAI RSS description.", ""]
    for name, articles, note in sections:
        lines += [f"## {name}", ""]
        if note:
            lines += [note, ""]
        for published, title, link, summary, why in articles:
            lines += [f"- **{title}** ({published.isoformat()}) — [Original source]({link})",
                      f"  - Summary: {summary}", f"  - Why it matters: {why}"]
        if not articles and not note:
            lines.append("- No dated headlines found in this briefing window.")
        lines.append("")
    return "\n".join(lines)


def email_html(now, sections):
    esc = html.escape
    parts = ["<!doctype html><html><body style='font-family:Arial,sans-serif;line-height:1.5;max-width:700px;margin:auto;color:#222'>",
             f"<h1>AI research news briefing — {esc(now.strftime('%B %d, %Y'))}</h1>",
             "<p>Official headlines dated today or yesterday. Summaries use only official source text.</p>"]
    for name, articles, note in sections:
        parts.append(f"<h2>{esc(name)}</h2>")
        if note:
            parts.append(f"<p>{esc(note.lstrip('- '))}</p>")
        if articles:
            parts.append("<ul>")
            for published, title, link, summary, why in articles:
                parts.append(f"<li><strong>{esc(title)}</strong> ({published.isoformat()}) — <a href='{esc(link, quote=True)}'>Original source</a>"
                             f"<p>{esc(summary)}</p><p><strong>Why it matters:</strong> {esc(why)}</p></li>")
            parts.append("</ul>")
        elif not note:
            parts.append("<p>No dated headlines found in this briefing window.</p>")
    parts.append("</body></html>")
    return "\n".join(parts)


def briefing(now):
    # Include today's and yesterday's dated posts because an 8 AM run spans both dates.
    days = {now.date(), now.date() - dt.timedelta(days=1)}
    sections = []
    log = []
    try:
        posts = anthropic_items(fetch(ANTHROPIC), days)
        articles = []
        for published, title, link in posts:
            try:
                summary, why = article_summary(link)
                articles.append((published, title, link, summary, why))
            except Exception as exc:
                log.append(f"Anthropic article unavailable: {link} ({exc})")
        note = "- Source articles unavailable; no summaries inferred." if posts and not articles else ""
        sections.append(("Anthropic News", articles, note))
        log.append(f"Anthropic News: {len(articles)} verified article(s)")
    except Exception as exc:
        sections.append(("Anthropic News", [], "- Source unavailable; no headlines inferred."))
        log.append(f"Anthropic News: unavailable ({exc})")
    try:
        posts = openai_items(fetch(OPENAI_RSS), days)
        articles = []
        for published, title, link, description in posts:
            try:
                summary, why = feed_summary(description, title)
                articles.append((published, title, link, summary, why))
            except ValueError:
                log.append(f"OpenAI RSS item unavailable: {link}")
        sections.append(("OpenAI News", articles, ""))
        log.append(f"OpenAI News: {len(articles)} verified RSS item(s)")
    except Exception as exc:
        sections.append(("OpenAI News", [], "- Source unavailable; no headlines inferred."))
        log.append(f"OpenAI News: unavailable ({exc})")
    result = markdown(now, sections)
    if len(result.split()) >= 800:
        raise RuntimeError("briefing exceeded 800 words")
    return result, email_html(now, sections), log


def main():
    ap = argparse.ArgumentParser()
    sending = ap.add_mutually_exclusive_group()
    sending.add_argument("--send", action="store_true", help="send one daily email via local sendmail")
    sending.add_argument("--test-send", action="store_true", help="send a test email without using the daily sent marker")
    args = ap.parse_args()
    OUT.mkdir(exist_ok=True)
    now = dt.datetime.now(TZ)
    day = now.date().isoformat()
    with (OUT / "briefing.lock").open("a") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        body, html_body, events = briefing(now)
        (OUT / f"briefing-{day}.md").write_text(body, encoding="utf-8")
        (OUT / f"briefing-{day}.html").write_text(html_body, encoding="utf-8")
        if args.send or args.test_send:
            recipients = [x.strip() for x in os.environ.get("BRIEFING_TO", "").split(",") if x.strip()]
            if not recipients or any("@" not in x or "\n" in x for x in recipients):
                ap.error("set BRIEFING_TO to one or two email addresses at runtime")
            if len(recipients) > 2:
                raise RuntimeError("at most two recipients are allowed")
            marker = OUT / f"sent-{day}.txt"
            if args.send and marker.exists():
                events.append("email: already submitted today; skipped")
            else:
                msg = email.message.EmailMessage()
                msg["To"] = ", ".join(recipients)
                msg["Subject"] = f"{'[TEST] ' if args.test_send else ''}AI research news briefing — {day}"
                msg.set_content(body)
                msg.add_alternative(html_body, subtype="html")
                if args.send:
                    # A marker before submission prevents a second daily message after an ambiguous failure.
                    marker.write_text("submission attempted\n", encoding="utf-8")
                p = subprocess.run(["/usr/sbin/sendmail", "-t", "-oi"], input=msg.as_string(), text=True, capture_output=True)
                if p.returncode:
                    events.append(f"{'test email' if args.test_send else 'email'}: sendmail failed ({p.stderr.strip()})")
                else:
                    if args.send:
                        marker.write_text("submitted to local sendmail\n", encoding="utf-8")
                    events.append(f"{'test email' if args.test_send else 'email'}: submitted to local sendmail")
        else:
            events.append("email: preview only")
        log_name = f"test-send-{day}.log" if args.test_send else f"run-{day}.log"
        (OUT / log_name).write_text("\n".join(events) + "\n", encoding="utf-8")
    print(body)
    print("\nRun log: " + "; ".join(events), file=sys.stderr)


if __name__ == "__main__":
    main()
