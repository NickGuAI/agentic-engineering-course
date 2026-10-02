"""Offline tests: parsers, fallback summarizer, state, output, and an end-to-end run with a fake fetcher.

Run:  cd code && python3 -m unittest -v test_newsdigest
No network, no API key, no third-party packages required.
"""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from newsdigest.config import SOURCES_BY_KEY
from newsdigest.http import FetchError
from newsdigest.ingest import (extract_article_text, parse_anthropic_listing, parse_human_date,
                               parse_rss, strip_tags)
from newsdigest.job import RunOptions, parse_interval, run_loop, run_once
from newsdigest.models import Article, Digest, Summary, Theme
from newsdigest.output import render_markdown, write_digest
from newsdigest.state import State
from newsdigest.summarize import ExtractiveSummarizer, first_sentences

NEWS = SOURCES_BY_KEY["anthropic-news"]
ENG = SOURCES_BY_KEY["anthropic-engineering"]
OAI = SOURCES_BY_KEY["openai-news"]

LISTING_HTML = """
<nav><a href="/news">News</a><a href="/news/">All</a><a href="/engineering/foo">eng</a></nav>
<a href="/news/first-post" class="card"><div><span>Announcements</span>
<time class="date">Aug 31, 2026</time></div><h4 class="title">First &amp; Post</h4>
<p class="body">Teaser for the first post.</p></a>
<a href="https://www.anthropic.com/news/second-post"><img alt="Second post via alt"/></a>
<a href="/news/first-post">duplicate link</a>
<a href="/news/third?utm=x">tracked</a>
<a href="/news/list-style" class="listItem"><div class="meta"><time class="date">Jul 4, 2026</time>
<span class="subject">Announcements</span></div><span class="x__title body-3">List-style title</span></a>
<a href="/engineering/card-style" class="cardLink"><img alt="alt text"/><div class="content">
<h3 class="headline-4">Card-style title</h3><div class="body-2 x__date">Mar 25, 2026</div></div></a>
"""

ARTICLE_HTML = """<html><head><script>var x=1;</script><style>.a{}</style></head><body>
<header>Site chrome</header><nav>menu</nav>
<article><h1>First &amp; Post</h1><time>Aug 31, 2026</time>
<p>Sentence one is here. Sentence two follows it! Sentence three is last.</p>
<ul><li>bullet a</li><li>bullet b</li></ul></article>
<footer>footer stuff</footer></body></html>"""

RSS_XML = """<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0"><channel><title>OpenAI News</title>
<item><title><![CDATA[Item One]]></title><description><![CDATA[Desc <b>one</b>.]]></description>
<link>https://openai.com/index/one</link><category><![CDATA[Product]]></category>
<pubDate>Fri, 11 Sep 2026 10:00:00 GMT</pubDate></item>
<item><title>Item Two</title><description>Desc two.</description>
<link>https://openai.com/index/two</link><pubDate>Thu, 10 Sep 2026 16:00:00 GMT</pubDate></item>
<item><title>Dup</title><link>https://openai.com/index/one</link></item>
</channel></rss>"""


class ParserTests(unittest.TestCase):
    def test_anthropic_listing(self):
        items = parse_anthropic_listing(LISTING_HTML, NEWS)
        self.assertEqual([a.url for a in items], [
            "https://www.anthropic.com/news/first-post",
            "https://www.anthropic.com/news/second-post",
            "https://www.anthropic.com/news/list-style",
        ])
        first, second, third = items
        self.assertEqual((third.title, third.published), ("List-style title", "2026-07-04"))
        self.assertEqual(first.title, "First & Post")
        self.assertEqual(first.published, "2026-08-31")
        self.assertEqual(first.snippet, "Teaser for the first post.")
        self.assertEqual(second.title, "Second post via alt")
        self.assertEqual(second.published, "")
        self.assertTrue(all(a.source_key == "anthropic-news" for a in items))

    def test_engineering_prefix_isolated(self):
        items = parse_anthropic_listing(LISTING_HTML, ENG)
        self.assertEqual([a.url for a in items], ["https://www.anthropic.com/engineering/foo",
                                                  "https://www.anthropic.com/engineering/card-style"])
        self.assertEqual(items[0].title, "Foo")  # slug fallback
        self.assertTrue(items[0].title_is_fallback)
        self.assertEqual((items[1].title, items[1].published), ("Card-style title", "2026-03-25"))

    def test_rss(self):
        items = parse_rss(RSS_XML, OAI)
        self.assertEqual(len(items), 2)
        self.assertEqual(items[0].title, "Item One")
        self.assertEqual(items[0].snippet, "Desc one.")
        self.assertEqual(items[0].category, "Product")
        self.assertEqual(items[0].published, "2026-09-11")
        self.assertEqual(items[1].published, "2026-09-10")

    def test_rss_rejects_html(self):
        with self.assertRaises(ValueError):
            parse_rss("<!DOCTYPE html><html><body>Just a page</body></html>", OAI)
        with self.assertRaises(ValueError):
            parse_rss("<html><body><p>well-formed xml but not a feed</p></body></html>", OAI)

    def test_article_text(self):
        text = extract_article_text(ARTICLE_HTML)
        self.assertIn("Sentence one is here.", text)
        self.assertIn("bullet a", text)
        self.assertNotIn("var x", text)
        self.assertNotIn("Site chrome", text)
        self.assertNotIn("footer stuff", text)

    def test_page_date_from_header_outside_article(self):
        from newsdigest.ingest import _page_date
        page = "<html><body><div class='hero'><span>May 25, 2026</span></div><article><p>x</p></article></body></html>"
        self.assertEqual(_page_date(page, "x"), "2026-05-25")
        self.assertEqual(_page_date('<meta property="article:published_time" content="2026-01-02T00:00:00Z">', ""), "2026-01-02")
        self.assertEqual(_page_date("<article><p>Jan 9, 2026</p></article>", "Jan 9, 2026"), "2026-01-09")
        self.assertEqual(_page_date("<p>nothing</p>", "nothing"), "")

    def test_truncation(self):
        text = extract_article_text("<article><p>" + "x" * 100 + "</p></article>", max_chars=10)
        self.assertEqual(len(text), 10)

    def test_helpers(self):
        self.assertEqual(parse_human_date("August 5, 2026"), "2026-08-05")
        self.assertEqual(parse_human_date("2026-08-05T10:00:00Z"), "2026-08-05")
        self.assertEqual(parse_human_date("no date"), "")
        self.assertEqual(strip_tags("a <b>b</b>\n c"), "a b c")
        self.assertEqual(first_sentences("One. Two. Three."), "One. Two.")
        self.assertEqual(first_sentences(""), "")


class SummarizerTests(unittest.TestCase):
    def test_extractive(self):
        a = Article("k", "Src", "https://x/1", "Title",
                    body="Announcements\nTitle\nAug 31, 2026\nBody one. Body two. Body three.")
        b = Article("k", "Src", "https://x/2", "T2", snippet="Only a teaser.", category="Cat")
        s = ExtractiveSummarizer()
        out = s.summarize([a, b])
        self.assertEqual(out[0].summary, "Body one. Body two.")
        self.assertEqual(out[1].summary, "Only a teaser.")
        self.assertEqual(out[1].tags, ["Cat"])
        overview, themes = s.digest([a, b], out)
        self.assertIn("2 new item(s)", overview)
        self.assertEqual(themes, [])


class StateAndOutputTests(unittest.TestCase):
    def test_state_roundtrip(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "state.json"
            st = State(p)
            a = Article("k", "Src", "https://x/1", "T")
            self.assertFalse(st.is_seen(a.url))
            st.mark(a)
            st.save()
            st2 = State(p)
            self.assertTrue(st2.is_seen(a.url))
            self.assertTrue(st2.last_run)

    def test_write_digest(self):
        a = Article("k", "Src", "https://x/1", "T", published="2026-09-11", fetch_error="HTTP 403")
        s = Summary(a.url, "Headline", "Sum.", "Matters.", ["models"], method="extractive")
        d = Digest("2026-09-11T12:00:00+00:00", "Overview.", [Theme("Th", "Det")], [(a, s)], "extractive")
        with tempfile.TemporaryDirectory() as dd:
            paths = write_digest(d, Path(dd))
            md = paths["markdown"].read_text()
            self.assertIn("# AI News Digest — 2026-09-11", md)
            self.assertIn("[Headline](https://x/1)", md)
            self.assertIn("**Why it matters:** Matters.", md)
            self.assertIn("HTTP 403", md)
            self.assertIn("- **Th** — Det", md)
            data = json.loads(paths["json"].read_text())
            self.assertEqual(data["items"][0]["summary"]["headline"], "Headline")
            self.assertEqual(paths["latest"].read_text(), md)

    def test_render_groups_by_source(self):
        a1 = Article("a", "Alpha", "https://a/1", "A1")
        b1 = Article("b", "Beta", "https://b/1", "B1")
        a2 = Article("a", "Alpha", "https://a/2", "A2")
        items = [(x, Summary(x.url, x.title, "s")) for x in (a1, b1, a2)]
        md = render_markdown(Digest("2026-01-01T00:00:00+00:00", "o", [], items, "extractive"))
        self.assertLess(md.index("## Alpha"), md.index("## Beta"))
        self.assertEqual(md.count("## Alpha"), 1)


class JobTests(unittest.TestCase):
    def fake_fetcher(self, fail: set[str] = frozenset()):
        def f(url: str) -> str:
            if url in fail:
                raise FetchError(url, "HTTP 500", 500)
            if url == NEWS.fetch_url or url == ENG.fetch_url:
                return LISTING_HTML
            if url == OAI.fetch_url:
                return RSS_XML
            if url.startswith("https://www.anthropic.com/"):
                return ARTICLE_HTML
            raise FetchError(url, "HTTP 403", 403)
        return f

    def test_end_to_end_then_dedupe(self):
        with tempfile.TemporaryDirectory() as d:
            opts = RunOptions(outputs_dir=Path(d), no_llm=True)
            r1 = run_once(opts, fetcher=self.fake_fetcher())
            self.assertEqual(r1.status, "ok")
            self.assertEqual(r1.method, "extractive")
            self.assertEqual(r1.new, {"anthropic-news": 3, "anthropic-engineering": 2, "openai-news": 2})
            self.assertEqual(r1.summarized, 7)
            self.assertEqual(r1.body_errors, 0)  # openai bodies are not fetched by design
            self.assertTrue(Path(r1.outputs["markdown"]).exists())
            md = Path(d, "latest.md").read_text()
            self.assertIn("Sentence one is here.", md)
            self.assertIn("## OpenAI News", md)
            # second run: nothing new, no new digest
            r2 = run_once(opts, fetcher=self.fake_fetcher())
            self.assertEqual(r2.status, "ok-empty")
            self.assertEqual(r2.summarized, 0)
            self.assertEqual(len(list(Path(d, "digests").glob("*.md"))), 1)
            runs = Path(d, "runs.jsonl").read_text().strip().splitlines()
            self.assertEqual(len(runs), 2)
            # --force re-summarizes
            r3 = run_once(RunOptions(outputs_dir=Path(d), no_llm=True, force=True), fetcher=self.fake_fetcher())
            self.assertEqual(r3.summarized, 7)

    def test_partial_source_failure_is_degraded(self):
        with tempfile.TemporaryDirectory() as d:
            opts = RunOptions(outputs_dir=Path(d), no_llm=True)
            r = run_once(opts, fetcher=self.fake_fetcher(fail={OAI.fetch_url}))
            self.assertEqual(r.status, "degraded")
            self.assertIn("openai-news", r.source_errors)
            self.assertEqual(r.summarized, 5)
            self.assertTrue(r.outputs)

    def test_html_feed_is_source_failure_not_crash(self):
        with tempfile.TemporaryDirectory() as d:
            fetch = self.fake_fetcher()
            def f(url):
                return "<!DOCTYPE html><html><body>blocked</body></html>" if url == OAI.fetch_url else fetch(url)
            r = run_once(RunOptions(outputs_dir=Path(d), no_llm=True), fetcher=f)
            self.assertEqual(r.status, "degraded")
            self.assertIn("openai-news", r.source_errors)
            self.assertEqual(r.summarized, 5)

    def test_all_sources_fail_is_error(self):
        with tempfile.TemporaryDirectory() as d:
            opts = RunOptions(outputs_dir=Path(d), no_llm=True)
            r = run_once(opts, fetcher=self.fake_fetcher(fail={NEWS.fetch_url, ENG.fetch_url, OAI.fetch_url}))
            self.assertEqual(r.status, "error")
            self.assertFalse(r.outputs)
            self.assertFalse(Path(d, "state.json").exists())

    def test_body_fetch_failure_falls_back_to_snippet(self):
        with tempfile.TemporaryDirectory() as d:
            opts = RunOptions(outputs_dir=Path(d), no_llm=True, sources=(NEWS,))
            r = run_once(opts, fetcher=self.fake_fetcher(fail={"https://www.anthropic.com/news/first-post"}))
            self.assertEqual(r.body_errors, 1)
            md = Path(d, "latest.md").read_text()
            self.assertIn("Teaser for the first post.", md)
            self.assertIn("full text not fetched", md)

    def test_undated_card_gets_page_date_and_title_before_cap(self):
        # /engineering/foo is undated with a slug title; the fake article page supplies
        # "Aug 31, 2026" and <h1>First &amp; Post</h1>, so it must rank above card-style (Mar 2026).
        with tempfile.TemporaryDirectory() as d:
            r = run_once(RunOptions(outputs_dir=Path(d), no_llm=True, sources=(ENG,), max_per_source=1),
                         fetcher=self.fake_fetcher())
            self.assertEqual(r.summarized, 1)
            data = json.loads(Path(r.outputs["json"]).read_text())
            art = data["items"][0]["article"]
            self.assertEqual(art["url"], "https://www.anthropic.com/engineering/foo")
            self.assertEqual(art["published"], "2026-08-31")
            self.assertEqual(art["title"], "First & Post")

    def test_dry_run_writes_nothing(self):
        with tempfile.TemporaryDirectory() as d:
            r = run_once(RunOptions(outputs_dir=Path(d), dry_run=True), fetcher=self.fake_fetcher())
            self.assertEqual(r.status, "dry-run")
            self.assertEqual(list(Path(d).iterdir()), [])

    def test_max_per_source_marks_backlog_seen(self):
        with tempfile.TemporaryDirectory() as d:
            opts = RunOptions(outputs_dir=Path(d), no_llm=True, max_per_source=1)
            r = run_once(opts, fetcher=self.fake_fetcher())
            self.assertEqual(r.summarized, 3)
            r2 = run_once(opts, fetcher=self.fake_fetcher())
            self.assertEqual(r2.status, "ok-empty")  # backlog is not drained on later runs

    def test_loop_and_interval(self):
        self.assertEqual(parse_interval("6h"), 21600)
        self.assertEqual(parse_interval("30m"), 1800)
        self.assertEqual(parse_interval("900"), 900)
        with self.assertRaises(ValueError):
            parse_interval("10s")
        with self.assertRaises(ValueError):
            parse_interval("weekly")
        slept = []
        with tempfile.TemporaryDirectory() as d:
            results = run_loop(RunOptions(outputs_dir=Path(d), no_llm=True), 120, max_runs=2,
                               fetcher=self.fake_fetcher(), sleep=slept.append)
        self.assertEqual([r.status for r in results], ["ok", "ok-empty"])
        self.assertEqual(slept, [120])


if __name__ == "__main__":
    unittest.main()
