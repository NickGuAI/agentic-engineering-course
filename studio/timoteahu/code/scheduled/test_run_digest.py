"""Offline tests: no agent CLI, no network. Run: python3 -m unittest -v test_run_digest"""

import copy
import datetime as dt
import json
import tempfile
import unittest
import urllib.error
from pathlib import Path

import run_digest as rd

HERE = Path(__file__).resolve().parent
CONFIG = rd.load_config(HERE / "config.json")
SCHEMA = json.loads((HERE / "digest.schema.json").read_text())
SAMPLE = json.loads((HERE / "fixtures" / "sample_digest.json").read_text())
RUN_DATE = dt.date(2026, 9, 24)

# Fake web: article pages contain the quotes; the OpenAI HTML page 403s, its RSS has the text.
PAGES = {
    "https://www.anthropic.com/news/claude-discovers-novel-enzyme-system":
        "<p>&hellip; but we don&rsquo;t yet know its function.</p>",
    "https://www.anthropic.com/news/accenture-embedded-evaluation":
        "<div>evaluating and red-teaming models, conducting alignment assessments, and "
        "testing model safeguards</div><p>We expect to invest at least $1 billion</p>",
    "https://openai.com/news/rss.xml":
        "<description>OpenAI is extending access to its Daybreak program to the "
        "Government of Ukraine to support ...</description>",
}


def fake_fetch(url):
    if url in PAGES:
        return PAGES[url]
    raise urllib.error.HTTPError(url, 403, "Forbidden", {}, None)


def evaluate(data, **kw):
    return rd.evaluate(data, CONFIG, SCHEMA, RUN_DATE, True, fake_fetch, **kw)


def failed(checks):
    return {c["name"] for c in checks if not c["ok"]}


class EvaluateTests(unittest.TestCase):
    def test_sample_passes(self):
        checks, md = evaluate(SAMPLE)
        self.assertEqual(failed(checks), set(), checks)
        self.assertEqual(rd.overall_status(checks), "pass")
        self.assertIn("(from feed description only)", md)

    def test_shape_error_stops_early(self):
        bad = copy.deepcopy(SAMPLE)
        del bad["items"][0]["evidence_quotes"]
        bad["items"][1]["claim_basis"] = "vibes"
        checks, md = evaluate(bad)
        self.assertIsNone(md)
        details = " ".join(c["detail"] for c in checks)
        self.assertIn("missing 'evidence_quotes'", details)
        self.assertIn("'vibes' not in", details)

    def test_out_of_window_date_fails(self):
        bad = copy.deepcopy(SAMPLE)
        bad["items"][0]["date"] = "2026-09-01"
        checks, _ = evaluate(bad)
        self.assertIn("item1_date", failed(checks))
        self.assertEqual(rd.overall_status(checks), "fail")

    def test_unapproved_domain_fails(self):
        bad = copy.deepcopy(SAMPLE)
        bad["items"][0]["source_url"] = "https://anthropic.com.evil.example/post"
        checks, _ = evaluate(bad)
        self.assertIn("item1_domain", failed(checks))

    def test_fabricated_quote_fails_grounding(self):
        bad = copy.deepcopy(SAMPLE)
        bad["items"][1]["evidence_quotes"] = ["Accenture will acquire Anthropic"]
        checks, _ = evaluate(bad)
        self.assertIn("item2_grounding", failed(checks))
        self.assertEqual(rd.overall_status(checks), "fail")

    def test_unfetchable_page_is_warning_not_failure(self):
        data = copy.deepcopy(SAMPLE)
        data["items"][2]["claim_basis"] = "full_article"  # so the RSS fallback is not tried
        checks, _ = evaluate(data)
        g = next(c for c in checks if c["name"] == "item3_grounding")
        self.assertEqual(g["kind"], "warning")
        self.assertIn("unverifiable", g["detail"])
        self.assertEqual(rd.overall_status(checks), "pass")

    def test_failed_required_source_is_incomplete_not_filled(self):
        data = copy.deepcopy(SAMPLE)
        data["sources_checked"][1] = {"source_id": "openai-news", "status": "failed",
                                      "url_fetched": "https://openai.com/news/",
                                      "detail": "HTTP 403"}
        data["items"] = data["items"][:2]
        checks, md = evaluate(data)
        self.assertEqual(rd.overall_status(checks), "incomplete")
        self.assertIn("## Missing sources", md)
        self.assertIn("OpenAI News: could not be read (HTTP 403)", md)

    def test_item_from_failed_source_is_rejected(self):
        data = copy.deepcopy(SAMPLE)
        data["sources_checked"][1]["status"] = "failed"
        checks, _ = evaluate(data)
        self.assertIn("item3_from_failed_source", failed(checks))
        self.assertEqual(rd.overall_status(checks), "fail")

    def test_rendered_markdown_passes_original_verifier(self):
        _, md = evaluate(SAMPLE)
        res = rd.verify_digest.check(md, RUN_DATE, 7, ["anthropic.com", "openai.com"],
                                     ["anthropic.com", "openai.com"], 600)
        self.assertTrue(all(ok for _, ok, _ in res), res)


class RunTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.out, self.work = Path(self.tmp.name, "out"), Path(self.tmp.name, "work")

    def tearDown(self):
        self.tmp.cleanup()

    def args(self, *extra):
        return rd.parse_args(["--run-date", "2026-09-24", "--out-dir", str(self.out),
                              "--work-dir", str(self.work), *extra])

    def test_repair_attempt_gets_failures_in_prompt(self):
        bad = copy.deepcopy(SAMPLE)
        bad["items"][0]["date"] = "2026-08-01"
        prompts = []

        def agent(prompt, *_):
            prompts.append(prompt)
            return (bad if len(prompts) == 1 else SAMPLE), {"cost_usd": 0.5, "raw": {}}

        code = rd.run(self.args(), agent_fn=agent, fetch=fake_fetch)
        self.assertEqual(code, 0)
        self.assertEqual(len(prompts), 2)
        self.assertNotIn("previous attempt failed", prompts[0])
        self.assertIn("item1_date: 2026-08-01", prompts[1])
        day = self.out / "2026-09-24"
        self.assertTrue((day / "research-update-2026-09-24.md").exists())
        log = json.loads((self.out / "runs.jsonl").read_text().splitlines()[-1])
        self.assertEqual((log["status"], log["attempts"], log["cost_usd"]), ("pass", 2, 1.0))

    def test_persistent_failure_writes_rejected_file(self):
        bad = copy.deepcopy(SAMPLE)
        bad["items"][0]["date"] = "2026-08-01"
        code = rd.run(self.args(), agent_fn=lambda *_: (bad, {"raw": {}}), fetch=fake_fetch)
        self.assertEqual(code, 1)
        day = self.out / "2026-09-24"
        self.assertTrue((day / "research-update-2026-09-24.REJECTED.md").exists())
        self.assertFalse((day / "research-update-2026-09-24.md").exists())

    def test_agent_error_is_logged(self):
        def boom(*_):
            raise rd.AgentError("claude exited 1: rate limited")
        code = rd.run(self.args(), agent_fn=boom, fetch=fake_fetch)
        self.assertEqual(code, 1)
        report = json.loads((self.out / "2026-09-24" / "checks.json").read_text())
        self.assertEqual(report["status"], "fail")
        self.assertEqual(len(report["attempts"]), CONFIG["agent"]["max_attempts"])

    def test_already_passed_date_is_skipped(self):
        calls = []

        def agent(*_):
            calls.append(1)
            return SAMPLE, {"raw": {}}
        rd.run(self.args(), agent_fn=agent, fetch=fake_fetch)
        rd.run(self.args(), agent_fn=agent, fetch=fake_fetch)
        self.assertEqual(len(calls), 1)
        rd.run(self.args("--force"), agent_fn=agent, fetch=fake_fetch)
        self.assertEqual(len(calls), 2)


class CommandTests(unittest.TestCase):
    def test_claude_is_limited_to_webfetch_on_approved_domains(self):
        cmd = rd.claude_command(CONFIG, "{}", None)
        self.assertEqual(cmd[cmd.index("--tools") + 1], "WebFetch")
        self.assertEqual(cmd[cmd.index("--permission-mode") + 1], "dontAsk")
        self.assertIn("WebFetch(domain:www.anthropic.com)", cmd)
        self.assertIn("WebFetch(domain:openai.com)", cmd)
        self.assertFalse(any("WebSearch" in c for c in cmd))

    def test_prompt_lists_config_sources_not_hardcoded(self):
        p = rd.build_prompt(CONFIG, RUN_DATE)
        self.assertIn("https://openai.com/news/rss.xml", p)
        self.assertIn("2026-09-17 through 2026-09-24", p)
        self.assertNotIn("{", p.split("## What to return")[0])


if __name__ == "__main__":
    unittest.main()
