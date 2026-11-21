import tempfile
import unittest
from pathlib import Path

import research_update as job


class ResearchUpdateTests(unittest.TestCase):
    def test_discovers_only_matching_official_article_links(self):
        source = dict(job.DEFAULT_SOURCES[0])
        markup = """
        <a href="/news/agent-update">Agent update</a>
        <a href="https://www.anthropic.com/engineering/other">Wrong section</a>
        <a href="https://example.com/news/fake">External</a>
        <a href="/news/agent-update?tracking=1">Duplicate</a>
        """
        found = job.discover_candidates(source, markup)
        self.assertEqual(
            found,
            [{"url": "https://www.anthropic.com/news/agent-update", "link_text": "Agent update"}],
        )

    def test_extracts_source_metadata_without_inventing_date(self):
        source = dict(job.DEFAULT_SOURCES[2])
        candidate = {"url": "https://openai.com/index/example", "link_text": "Example"}
        markup = """
        <html><head>
          <meta property="og:title" content="A coding agent update">
          <meta property="og:description" content="A source-provided description of a coding agent.">
          <meta property="og:url" content="https://openai.com/index/example/">
        </head></html>
        """
        item = job.extract_article(source, candidate, markup, candidate["url"])
        self.assertEqual(item["title"], "A coding agent update")
        self.assertIsNone(item["publication_date"])
        self.assertIn("source-provided description", item["summary"])
        self.assertGreater(item["relevance_score"], 0)

    def test_uses_article_text_and_visible_date_when_meta_is_generic(self):
        source = dict(job.DEFAULT_SOURCES[1])
        candidate = {
            "url": "https://www.anthropic.com/engineering/managed-agents",
            "link_text": "Managed agents",
        }
        markup = """
        <html><head>
          <meta property="og:title" content="Scaling Managed Agents">
          <meta property="og:description" content="Anthropic is an AI safety and research company that's working to build reliable AI systems.">
        </head><body>
          <div>Published Apr 08, 2026</div>
          <p>Harnesses encode assumptions that go stale as models improve, so stable interfaces matter for long-running agent work.</p>
        </body></html>
        """
        item = job.extract_article(source, candidate, markup, candidate["url"])
        self.assertEqual(item["publication_date"], "Apr 08, 2026")
        self.assertIn("Harnesses encode assumptions", item["summary"])

    def test_openai_discovery_excludes_news_category_pages(self):
        source = dict(job.DEFAULT_SOURCES[2])
        markup = """
        <a href="/news/safety-alignment/">Safety category</a>
        <a href="/index/introducing-the-agents-api/">Introducing the Agents API</a>
        """
        found = job.discover_candidates(source, markup)
        self.assertEqual(
            found,
            [{
                "url": "https://openai.com/index/introducing-the-agents-api/",
                "link_text": "Introducing the Agents API",
            }],
        )

    def test_run_directories_are_unique_and_do_not_overwrite(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            first_id, first = job.make_run_directory(root)
            second_id, second = job.make_run_directory(root)
            self.assertNotEqual(first_id, second_id)
            self.assertTrue(first.is_dir())
            self.assertTrue(second.is_dir())

    def test_verification_requires_selected_items(self):
        with tempfile.TemporaryDirectory() as temp:
            digest = Path(temp) / "digest.md"
            digest.write_text("# Digest\n", encoding="utf-8")
            sources = [
                {
                    "id": source["id"],
                    "status": "SUCCESS",
                    "selected_count": 0,
                }
                for source in job.DEFAULT_SOURCES
            ]
            checks = job.verification_checks(
                digest,
                sources,
                [],
                {source["id"] for source in job.DEFAULT_SOURCES},
            )
            self.assertFalse(checks["selected_items_present"])
            self.assertTrue(checks["all_configured_sources_attempted"])


if __name__ == "__main__":
    unittest.main()
