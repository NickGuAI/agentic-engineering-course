import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from urllib.error import HTTPError


sys.path.insert(0, str(Path(__file__).parent))
import news_update  # noqa: E402


class NewsUpdateTests(unittest.TestCase):
    def test_summary_uses_multiple_article_paragraphs(self):
        parser = news_update.parse_page(
            b"<html><p>First substantive finding about the model evaluation.</p>"
            b"<p>Second substantive finding about deployment safeguards.</p>"
            b"<p>Third substantive finding about operational changes.</p></html>"
        )

        summary = news_update.article_summary(parser, "fallback")

        self.assertIn("First substantive finding", summary)
        self.assertIn("Second substantive finding", summary)
        self.assertIn("Third substantive finding", summary)

    def test_render_includes_objective_why_it_matters_line(self):
        article = news_update.Article(
            "Anthropic News",
            "New evaluation policy",
            "https://www.anthropic.com/news/example",
            None,
            "The article describes a change to evaluation policy.",
            "It reports a development in New evaluation policy; its practical implications depend on how the described capabilities, safeguards, or policies are adopted.",
        )

        report = news_update.render_markdown(news_update.datetime.now(news_update.timezone.utc), [article], [])

        self.assertEqual(report.count("**Why it matters:**"), 1)
        self.assertIn("practical implications depend", report)

    def test_http_errors_exit_cleanly_and_explain_empty_result(self):
        def fail_every_request(*_args, **_kwargs):
            raise HTTPError("https://example.invalid", 500, "simulated failure", {}, None)

        with tempfile.TemporaryDirectory() as directory:
            args = news_update.build_parser().parse_args(
                ["--output-dir", directory, "--timeout", "1"]
            )
            with patch.object(news_update, "urlopen", side_effect=fail_every_request):
                result = news_update.run(args)

            reports = list(Path(directory).glob("ai-news-update-*.md"))
            self.assertEqual(result, 0)
            self.assertEqual(len(reports), 1)
            report = reports[0].read_text(encoding="utf-8")
            self.assertIn("No articles were reported because", report)
            self.assertEqual(report.count("HTTP Error 500: simulated failure"), 3)


if __name__ == "__main__":
    unittest.main()
