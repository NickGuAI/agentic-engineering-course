import copy
import json
import unittest
from datetime import date
from pathlib import Path
from digest import build


class DigestTests(unittest.TestCase):
    def setUp(self):
        self.data = json.loads((Path(__file__).resolve().parents[1] / "outputs/source-readings.json").read_text())
        self.day = date(2026, 9, 18)

    def test_baseline(self):
        text, result, events = build(self.data, self.day)
        self.assertEqual(result["article_count"], 5)
        self.assertTrue(all(result["checks"].values()))
        self.assertNotIn("## How we contain", text)
        self.assertTrue(any(e.get("reason") == "outside_date_window" for e in events))

    def test_missing_source_is_visible_and_restoration_recovers(self):
        broken = copy.deepcopy(self.data)
        del broken["sources"]["openai-news"]
        text, result, events = build(broken, self.day)
        self.assertEqual(result["status"], "PARTIAL")
        self.assertEqual(result["article_count"], 2)
        self.assertEqual(result["missing_sources"], ["openai-news"])
        self.assertIn("MISSING INPUT", text)
        self.assertNotIn("Astra for Law", text)
        self.assertTrue(any(e["event"] == "source_error" for e in events))
        self.assertEqual(build(self.data, self.day)[1]["article_count"], 5)

    def test_duplicate_and_missing_date_rejected(self):
        articles = self.data["sources"]["anthropic-news"]["articles"]
        articles.append(copy.deepcopy(articles[0]))
        articles[1].pop("date")
        _, result, events = build(self.data, self.day)
        reasons = {e.get("reason") for e in events}
        self.assertIn("duplicate_url", reasons)
        self.assertIn("missing_or_invalid_date", reasons)
        self.assertEqual(result["article_count"], 4)

    def test_empty_window(self):
        text, result, _ = build(self.data, date(2026, 10, 1))
        self.assertEqual(result["article_count"], 0)
        self.assertIn("No eligible articles", text)


if __name__ == "__main__":
    unittest.main()
