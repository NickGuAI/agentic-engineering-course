import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import agent

FIXTURES = Path(__file__).parent / 'fixtures'
ARTICLE = (FIXTURES / 'article.html').read_text()


def draft(packet):
    return [dict(url=a['url'], summary='Synthetic fixture summary, not an LLM response.',
                 why_it_matters='This tests publication validation.', category='Engineering',
                 evidence='This is synthetic evidence for a local collector test.', material=True)
            for a in packet['articles']]


class AgentTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.runtime = Path(self.tmp.name)
        self.fail_urls = set()
        self.article = ARTICLE

    def fetch(self, url):
        if url in self.fail_urls:
            raise RuntimeError('Synthetic network failure')
        for source in agent.SOURCES:
            if url == source.get('feed', source['url']):
                return (FIXTURES / ('openai.xml' if source['format'] == 'rss' else 'anthropic.html')).read_text()
        return self.article

    def collect(self):
        run = agent.collect(self.runtime, self.fetch)
        return run, json.loads((run / 'packet.json').read_text())

    def test_html_dedup_scope_and_dates(self):
        items = agent.parse_index(agent.SOURCES[0], (FIXTURES / 'anthropic.html').read_text())
        self.assertEqual(len(items), 2)
        self.assertEqual(items[0]['date'], '2026-09-10')
        self.assertNotIn('?', items[0]['url'])
        engineering = agent.parse_index(agent.SOURCES[1], (FIXTURES / 'anthropic.html').read_text())
        self.assertEqual(len(engineering), 1)
        self.assertEqual(engineering[0]['date'], '2026-04-08')

    def test_article_ignores_script_navigation_footer(self):
        title, date, text = agent.parse_article(ARTICLE)
        self.assertEqual(date, '2026-09-10')
        self.assertEqual(title, 'Fixture announcement')
        self.assertNotIn('execute a command', text)
        self.assertNotIn('Changing', text)

    def test_no_duplicate_digest_on_second_run(self):
        run, packet = self.collect()
        result = agent.publish(self.runtime, run.name, draft(packet))
        self.assertEqual(result['articles'], 4)
        self.assertTrue(result['notify'])
        second, packet = self.collect()
        self.assertEqual(packet['articles'], [])
        self.assertFalse(agent.publish(self.runtime, second.name, [])['notify'])

    def test_failed_source_does_not_discard_other_results(self):
        self.fail_urls.add(agent.SOURCES[0]['url'])
        run, packet = self.collect()
        result = agent.publish(self.runtime, run.name, draft(packet))
        self.assertEqual(result['failed_sources'], 1)
        self.assertEqual(result['articles'], 2)
        self.assertNotIn('anthropic-news', agent.read_state(self.runtime)['sources'])

    def test_invalid_evidence_does_not_advance_state(self):
        run, packet = self.collect()
        summaries = draft(packet)
        summaries[0]['evidence'] = 'An invented claim unsupported by the input text.'
        with self.assertRaises(ValueError):
            agent.publish(self.runtime, run.name, summaries)
        self.assertFalse((self.runtime / 'state.json').exists())
        self.assertFalse((run / 'digest.md').exists())

    def test_missing_and_invented_urls_rejected(self):
        run, packet = self.collect()
        with self.assertRaises(ValueError):
            agent.publish(self.runtime, run.name, draft(packet)[:-1])
        summaries = draft(packet)
        summaries[0]['url'] = 'https://openai.com/index/invented'
        with self.assertRaises(ValueError):
            agent.publish(self.runtime, run.name, summaries)

    def test_concurrent_and_replayed_publication_rejected(self):
        first, packet = self.collect()
        second, packet2 = self.collect()
        agent.publish(self.runtime, first.name, draft(packet))
        with self.assertRaises(ValueError):
            agent.publish(self.runtime, first.name, draft(packet))
        with self.assertRaises(ValueError):
            agent.publish(self.runtime, second.name, draft(packet2))

    def test_failed_digest_write_does_not_advance_state(self):
        run, packet = self.collect()
        original = agent.atomic
        def fail_digest(path, value):
            if path.name == 'digest.md':
                raise OSError('Synthetic disk failure')
            return original(path, value)
        with patch.object(agent, 'atomic', side_effect=fail_digest):
            with self.assertRaises(OSError):
                agent.publish(self.runtime, run.name, draft(packet))
        self.assertFalse((self.runtime / 'state.json').exists())

    def test_changed_content_resummarized_and_nonmaterial_edit_silent(self):
        run, packet = self.collect()
        agent.publish(self.runtime, run.name, draft(packet))
        self.article = ARTICLE.replace('bounded research', 'carefully bounded research')
        run, packet = self.collect()
        self.assertTrue(all(a['change'] == 'updated' for a in packet['articles']))
        summaries = draft(packet)
        for item in summaries:
            item['material'] = False
        self.assertFalse(agent.publish(self.runtime, run.name, summaries)['notify'])
        _, next_packet = self.collect()
        self.assertEqual(next_packet['articles'], [])

    def test_failed_article_is_retried_after_baseline(self):
        url = 'https://www.anthropic.com/news/example-one'
        self.fail_urls.add(url)
        run, packet = self.collect()
        agent.publish(self.runtime, run.name, draft(packet))
        self.fail_urls.clear()
        _, packet = self.collect()
        self.assertEqual([a['url'] for a in packet['articles']], [url])

    def test_first_run_baseline_does_not_backfill_older_articles(self):
        original_fetch = self.fetch
        def seven(url):
            if url == agent.SOURCES[0]['url']:
                return '<main>' + ''.join(f'<a href="/news/item-{i}"><h2>Item {i}</h2><time>Sep 0{7-i}, 2026</time></a>' for i in range(7)) + '</main>'
            return original_fetch(url)
        run = agent.collect(self.runtime, seven)
        packet = json.loads((run / 'packet.json').read_text())
        self.assertEqual(len(packet['baseline']['anthropic-news']), 2)
        agent.publish(self.runtime, run.name, draft(packet))
        run = agent.collect(self.runtime, seven)
        self.assertEqual(json.loads((run / 'packet.json').read_text())['articles'], [])

    def test_future_dates_and_blocked_pages_are_not_success(self):
        self.article = ARTICLE.replace('2026-09-10T16:00:00Z', '2099-09-10T16:00:00Z')
        run, packet = self.collect()
        self.assertEqual(packet['articles'], [])
        self.assertEqual(agent.publish(self.runtime, run.name, [])['failed_sources'], 3)
        with self.assertRaises(ValueError):
            agent.parse_article('<html><h1>Access denied</h1></html>')
        with self.assertRaises(ValueError):
            agent.parse_index(agent.SOURCES[0], '<html>Challenge required</html>')

    def test_url_boundary(self):
        for url in ('http://openai.com/news', 'https://openai.com.evil.test/news',
                    'https://openai.com/news/../admin', 'https://openai.com/news/%2e%2e/admin',
                    'https://user:secret@openai.com/news', 'file:///etc/passwd',
                    'https://unrelated.example/news/article'):
            with self.subTest(url=url), self.assertRaises(ValueError):
                agent.canonical(url)

    def test_featured_root_article_and_mixed_rss_paths(self):
        raw = '<main><a class="FeaturedGrid__content" href="/root-article"><h2>Root article</h2><time>Sep 10, 2026</time></a><a href="/careers"><h2>Careers</h2></a></main>'
        items = agent.parse_index(agent.SOURCES[0], raw)
        self.assertEqual([a['url'] for a in items], ['https://www.anthropic.com/root-article'])
        rss = (FIXTURES / 'openai.xml').read_text().replace('/index/fixture', '/academy/fixture')
        self.assertEqual(len(agent.parse_index(agent.SOURCES[2], rss)), 1)

    def test_date_in_article_hero_outside_article_body(self):
        raw = ARTICLE.replace('<meta property="article:published_time" content="2026-09-10T16:00:00Z">', '')
        raw = raw.replace('<main>', '<main><p class="HeroEngineering__date">Published May 25, 2026</p>')
        self.assertEqual(agent.parse_article(raw)[1], '2026-05-25')

    def test_blocked_article_uses_explicit_rss_coverage(self):
        original = self.fetch
        def rss_fallback(url):
            if url == agent.SOURCES[2]['feed']:
                return original(url).replace('<category>', '<description>This is synthetic evidence for a local collector test.</description><category>')
            if url == 'https://openai.com/index/fixture':
                raise RuntimeError('HTTP 403')
            return original(url)
        run = agent.collect(self.runtime, rss_fallback)
        packet = json.loads((run / 'packet.json').read_text())
        self.assertEqual(packet['articles'][-1]['coverage'], 'rss-description')
        result = agent.publish(self.runtime, run.name, draft(packet))
        self.assertEqual(result['failed_sources'], 0)
        self.assertEqual(result['limited_sources'], 1)
        self.assertIn('HTTP 403', (run / 'coverage.log').read_text())
        self.assertIn('coverage=rss-description', (run / 'coverage.log').read_text())
        for report in (run / 'digest.md', Path(result['digest'])):
            self.assertNotIn('HTTP 403', report.read_text())
            self.assertNotIn('Coverage', report.read_text())
        second = agent.collect(self.runtime, rss_fallback)
        self.assertFalse(agent.publish(self.runtime, second.name, [])['notify'])

    def test_unchanged_run_preserves_daily_report(self):
        run, packet = self.collect()
        result = agent.publish(self.runtime, run.name, draft(packet))
        report = Path(result['digest'])
        content, modified = report.read_bytes(), report.stat().st_mtime_ns
        second, _ = self.collect()
        again = agent.publish(self.runtime, second.name, [])
        self.assertEqual(result['digest'], again['digest'])
        self.assertEqual(report.read_bytes(), content)
        self.assertEqual(report.stat().st_mtime_ns, modified)
        self.assertFalse((self.runtime / 'latest.md').exists())

    def test_new_day_gets_own_file_and_preserves_previous_day(self):
        run, packet = self.collect()
        packet['collected_at'] = '2026-09-11T13:00:00+00:00'
        agent.write_json(run / 'packet.json', packet)
        first = agent.publish(self.runtime, run.name, draft(packet))
        content = Path(first['digest']).read_bytes()
        second, packet = self.collect()
        packet['collected_at'] = '2026-09-14T13:00:00+00:00'
        agent.write_json(second / 'packet.json', packet)
        result = agent.publish(self.runtime, second.name, [])
        self.assertEqual(Path(first['digest']).name, '2026-09-11.md')
        self.assertEqual(Path(result['digest']).name, '2026-09-14.md')
        self.assertEqual(Path(first['digest']).read_bytes(), content)
        self.assertIn('No article summaries', Path(result['digest']).read_text())

    def test_same_day_recovery_combines_articles_without_duplicates(self):
        self.fail_urls.add(agent.SOURCES[0]['url'])
        run, packet = self.collect()
        first = agent.publish(self.runtime, run.name, draft(packet))
        self.fail_urls.clear()
        second, packet = self.collect()
        result = agent.publish(self.runtime, second.name, draft(packet))
        self.assertEqual(first['digest'], result['digest'])
        text = Path(result['digest']).read_text()
        self.assertEqual(text.count('\n## ['), 4)
        self.assertNotIn('Synthetic network failure', text)

    def test_report_day_uses_eastern_timezone_and_dst(self):
        self.assertEqual(agent.report_day({'collected_at': '2026-09-12T02:00:00+00:00'}), '2026-09-11')
        self.assertEqual(agent.report_day({'collected_at': '2026-01-02T04:30:00+00:00'}), '2026-01-01')
        self.assertEqual(agent.report_day({'collected_at': '2026-07-02T04:30:00+00:00'}), '2026-07-02')

    def test_rebuild_uses_completed_runs_and_preserves_state(self):
        run, packet = self.collect()
        result = agent.publish(self.runtime, run.name, draft(packet))
        state = (self.runtime / 'state.json').read_bytes()
        # An unpublished packet must not become part of a reading report.
        self.article = ARTICLE.replace('bounded research', 'different research')
        self.collect()
        paths = agent.rebuild_reports(self.runtime)
        self.assertEqual(paths, [result['digest']])
        self.assertEqual((self.runtime / 'state.json').read_bytes(), state)
        self.assertEqual(Path(paths[0]).read_text().count('\n## ['), 4)


if __name__ == '__main__':
    unittest.main()
