from __future__ import annotations

import unittest
from datetime import datetime

from news_job import EASTERN, JobError, next_scheduled_time, render_markdown, validate_payload


def valid_payload() -> dict:
    return {
        "source_checks": [
            {
                "source": "Anthropic News",
                "status": "checked",
                "details": "No qualifying item found.",
                "url": "https://www.anthropic.com/news",
            },
            {
                "source": "Anthropic Engineering",
                "status": "checked",
                "details": "No qualifying item found.",
                "url": "https://www.anthropic.com/engineering",
            },
            {
                "source": "OpenAI News",
                "status": "checked",
                "details": "One qualifying item found.",
                "url": "https://openai.com/news/",
            },
            {
                "source": "X.com",
                "status": "unavailable",
                "details": "Public results could not be verified.",
                "url": "https://x.com/",
            },
        ],
        "stories": [
            {
                "headline": "A measured result",
                "source_name": "OpenAI",
                "published_at": "2026-09-11",
                "date_precision": "date_only",
                "kind": "paper",
                "summary": "Researchers reported a measured result on a public benchmark.",
                "description": "The paper explains its method and publishes the evaluation setup.",
                "url": "https://openai.com/news/measured-result/",
            }
        ],
    }


class ScheduleTests(unittest.TestCase):
    def test_before_eight_uses_same_day(self) -> None:
        now = datetime(2026, 9, 11, 7, 30, tzinfo=EASTERN)
        self.assertEqual(next_scheduled_time(now), datetime(2026, 9, 11, 7, 59, tzinfo=EASTERN))

    def test_after_eight_uses_next_day(self) -> None:
        now = datetime(2026, 9, 11, 8, 1, tzinfo=EASTERN)
        self.assertEqual(next_scheduled_time(now), datetime(2026, 9, 12, 7, 59, tzinfo=EASTERN))


class PayloadTests(unittest.TestCase):
    def setUp(self) -> None:
        self.end = datetime(2026, 9, 11, 8, 0, tzinfo=EASTERN)
        self.start = datetime(2026, 9, 10, 8, 0, tzinfo=EASTERN)

    def test_accepts_valid_payload(self) -> None:
        cleaned = validate_payload(valid_payload(), self.start, self.end)
        self.assertEqual(len(cleaned["source_checks"]), 4)
        self.assertEqual(len(cleaned["stories"]), 1)

    def test_rejects_more_than_five_stories(self) -> None:
        payload = valid_payload()
        payload["stories"] *= 6
        with self.assertRaisesRegex(JobError, "at most 5"):
            validate_payload(payload, self.start, self.end)

    def test_rejects_duplicate_source_check(self) -> None:
        payload = valid_payload()
        payload["source_checks"][3]["source"] = "OpenAI News"
        with self.assertRaisesRegex(JobError, "duplicated"):
            validate_payload(payload, self.start, self.end)

    def test_rejects_exact_timestamp_outside_window(self) -> None:
        payload = valid_payload()
        story = payload["stories"][0]
        story["published_at"] = "2026-09-10T07:59:59-04:00"
        story["date_precision"] = "timestamp"
        with self.assertRaisesRegex(JobError, "outside"):
            validate_payload(payload, self.start, self.end)

    def test_rejects_non_primary_story_url(self) -> None:
        payload = valid_payload()
        payload["stories"][0]["url"] = "https://clickbait.example/story"
        with self.assertRaisesRegex(JobError, "allowlist"):
            validate_payload(payload, self.start, self.end)

    def test_render_has_requested_story_fields(self) -> None:
        payload = validate_payload(valid_payload(), self.start, self.end)
        report = render_markdown(payload, self.end, self.start, self.end)
        self.assertIn("## Source check", report)
        self.assertIn("### 1. A measured result", report)
        self.assertIn("- Source: OpenAI", report)
        self.assertIn("- Published: 2026-09-11", report)
        self.assertIn("- Summary:", report)
        self.assertIn("- Link: [Original source]", report)


if __name__ == "__main__":
    unittest.main(verbosity=2)
