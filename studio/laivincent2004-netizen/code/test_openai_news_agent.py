import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from openai_news_agent import NEWS_URL, run_agent


ARTICLE_ONE = "https://openai.com/index/one"
ARTICLE_TWO = "https://openai.com/index/two"
ARTICLE_THREE = "https://openai.com/index/three"


NEWS_HTML = f"""<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0">
  <channel>
    <item>
      <title>First agent story</title>
      <description>AI agents can help teams inspect source evidence and complete bounded tasks.</description>
      <link>{ARTICLE_ONE}</link>
      <category>Engineering</category>
      <pubDate>Fri, 11 Sep 2026 10:00:00 GMT</pubDate>
    </item>
    <item>
      <title>Second workflow story</title>
      <description>The workflow stays useful when permissions are clear and the system records its run.</description>
      <link>{ARTICLE_TWO}</link>
      <category>Applied AI</category>
      <pubDate>Thu, 10 Sep 2026 16:00:00 GMT</pubDate>
    </item>
    <item>
      <title>Third data story</title>
      <description>Codex can support a beginner by linking claims to data and avoiding unsupported guesses.</description>
      <link>{ARTICLE_THREE}</link>
      <category>Product</category>
      <pubDate>Wed, 9 Sep 2026 15:00:00 GMT</pubDate>
    </item>
  </channel>
</rss>
"""


def fake_fetch(url: str) -> str:
    pages = {
        NEWS_URL: NEWS_HTML,
    }
    return pages[url]


class OpenAINewsAgentTests(unittest.TestCase):
    def test_normal_run_writes_summary_and_record(self):
        with TemporaryDirectory() as temp:
            result = run_agent(output_dir=Path(temp), fetch=fake_fetch, checked_at="September 11, 2026")
            self.assertEqual(result["status"], "completed")
            summary = Path(result["summary"]).read_text(encoding="utf-8")
            record = Path(result["run_record"]).read_text(encoding="utf-8")
            self.assertIn("First agent story", summary)
            self.assertIn("Source: https://openai.com/index/one", summary)
            self.assertIn("Unfamiliar terms:", summary)
            self.assertIn("Latest-post check", record)

    def test_unavailable_page_stops_without_summary(self):
        with TemporaryDirectory() as temp:
            result = run_agent(
                output_dir=Path(temp),
                fetch=fake_fetch,
                unavailable_url=ARTICLE_ONE,
                checked_at="September 11, 2026",
            )
            self.assertEqual(result["status"], "stopped")
            summary = Path(result["summary"]).read_text(encoding="utf-8")
            record = Path(result["run_record"]).read_text(encoding="utf-8")
            self.assertIn("Stopped Because One Source Page Was Unavailable", summary)
            self.assertIn("No complete three-item summary was produced", summary)
            self.assertIn("Simulated unavailable source page", record)

    def test_unavailable_page_outside_latest_three_is_not_applicable(self):
        with TemporaryDirectory() as temp:
            result = run_agent(
                output_dir=Path(temp),
                fetch=fake_fetch,
                unavailable_url="https://openai.com/index/not-in-latest-three/",
                checked_at="September 11, 2026",
            )
            self.assertEqual(result["status"], "not_applicable")
            summary = Path(result["summary"]).read_text(encoding="utf-8")
            self.assertIn("not one of the three latest", summary)
            self.assertIn("No changed-condition summary was produced", summary)


if __name__ == "__main__":
    unittest.main(verbosity=2)
