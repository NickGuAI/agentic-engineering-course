"""Offline checks for effects, global reservations, and fresh completion."""

import concurrent.futures
from pathlib import Path
import sys
import tempfile
import threading
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "code"))
from harness import Action, Harness, HarnessError


class HarnessTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.root = Path(self.directory.name)
        self.harness = Harness(self.root, {}, "test-run")

    def test_successful_replay_never_repeats_effect_or_shares_mutable_result(self):
        calls = []
        action = Action("discover-1", "discover", {"source_id": "anthropic_news"})
        result = self.harness.execute(action, lambda: calls.append(1) or {"items": ["a"]})
        result["items"].append("edited")
        replay = self.harness.execute(action, lambda: self.fail("effect repeated"))
        self.assertEqual(replay, {"items": ["a"]})
        self.assertEqual(calls, [1])
        with self.assertRaises(HarnessError):
            self.harness.execute(Action("discover-1", "discover", {"source_id": "openai_news"}),
                                 lambda: self.fail("conflicting effect"))

    def test_failed_effect_requires_new_attempt_id_and_consumes_action(self):
        action = Action("fetch-1", "fetch", {"url": "https://www.anthropic.com/news"})
        def fail():
            raise TimeoutError("private low-level exception text")
        with self.assertRaises(TimeoutError):
            self.harness.execute(action, fail)
        with self.assertRaises(HarnessError):
            self.harness.execute(action, lambda: self.fail("uncertain effect replayed"))
        self.assertEqual(self.harness.counters["actions"], 2)
        self.assertNotIn("private low-level exception", str(self.harness.events))
        self.assertEqual(self.harness.execute(Action("fetch-2", "fetch", action.arguments), lambda: "ok"), "ok")

    def test_strict_action_schema_rejects_extra_keys_and_wrong_types(self):
        bad = [
            Action("1", "shell", {}),
            Action("2", "fetch", {"url": "https://example.com", "path": "/tmp"}),
            Action("3", "summarize", {"article_ids": ["a"], "repair": 1}),
            Action("4", "select", {"article_ids": ["a", "a"]}),
            Action("5", "verify", {"digest_hash": "short", "manifest_hash": "short"}),
        ]
        for action in bad:
            with self.subTest(action=action), self.assertRaises(HarnessError):
                self.harness.execute(action, lambda: self.fail("invalid effect"))
        self.assertEqual(self.harness.counters["actions"], len(bad))

    def test_action_limit_counts_rejections_and_prevents_next_effect(self):
        limited = Harness(self.root, {"limits": {"max_actions": 2}}, "limited")
        for unused in range(2):
            with self.assertRaises(HarnessError):
                limited.execute(Action("bad", "unknown", {}), lambda: None)
        with self.assertRaisesRegex(HarnessError, "action budget"):
            limited.execute(Action("ok", "select", {"article_ids": []}), lambda: self.fail("over budget"))

    def test_http_budget_is_reserved_atomically_and_includes_retries(self):
        def reserve(unused):
            try:
                self.harness.before_http("https://www.anthropic.com/news")
                return True
            except HarnessError:
                return False
        with concurrent.futures.ThreadPoolExecutor(max_workers=8) as pool:
            outcomes = list(pool.map(reserve, range(40)))
        self.assertEqual(sum(outcomes), 16)
        self.assertEqual(self.harness.counters["http_requests"], 16)

    def test_deadline_blocks_http_model_and_action_before_effect(self):
        with patch("harness.time.monotonic", return_value=self.harness._deadline + 1):
            self.assertEqual(self.harness.remaining_seconds(), 0)
            with self.assertRaisesRegex(HarnessError, "deadline"):
                self.harness.before_http("https://www.anthropic.com/news")
            with self.assertRaisesRegex(HarnessError, "deadline"):
                self.harness.reserve_model(1, 1)
            with self.assertRaisesRegex(HarnessError, "deadline"):
                self.harness.execute(Action("1", "select", {"article_ids": []}), lambda: self.fail("late"))
        self.assertEqual(self.harness.counters["actions"], 0)

    def test_initial_and_repair_payload_envelopes_and_two_call_ceiling(self):
        for tokens, size in [(8001, 1), (1, 48 * 1024 + 1)]:
            with self.subTest(tokens=tokens, size=size), self.assertRaises(HarnessError):
                self.harness.reserve_model(tokens, size)
        self.assertEqual(self.harness.counters["model_calls"], 0)
        self.harness.reserve_model(8000, 48 * 1024)
        self.harness.record_usage({"input_tokens": 9000, "output_tokens": 1000,
                                   "cached_input_tokens": 100, "total_tokens": 10000})
        for tokens, size in [(4001, 1), (1, 24 * 1024 + 1)]:
            with self.subTest(tokens=tokens, size=size), self.assertRaises(HarnessError):
                self.harness.reserve_model(tokens, size, repair=True)
        self.harness.reserve_model(4000, 24 * 1024, repair=True)
        self.harness.record_usage({"total_tokens": 5000})
        self.assertEqual(self.harness.counters["application_input_tokens"], 12000)
        self.assertEqual(self.harness.counters["observed_total_tokens"], 15000)
        with self.assertRaisesRegex(HarnessError, "invocation budget"):
            self.harness.reserve_model(1, 1, repair=True)

    def test_tighter_cumulative_limit_and_no_second_initial_call(self):
        limited = Harness(self.root, {"max_application_input_tokens": 9000}, "limited")
        limited.reserve_model(8000, 100)
        limited.record_usage({"total_tokens": 8001})
        with self.assertRaisesRegex(HarnessError, "cumulative"):
            limited.reserve_model(1001, 100, repair=True)
        with self.assertRaisesRegex(HarnessError, "one initial"):
            limited.reserve_model(1000, 100)
        limited.reserve_model(1000, 100, repair=True)

    def test_ambiguous_failure_reservation_is_never_refunded(self):
        self.harness.reserve_model(50, 100)
        with self.assertRaisesRegex(HarnessError, "unknown"):
            self.harness.reserve_model(50, 100, repair=True)
        self.harness.record_usage(None)
        self.assertIsNone(self.harness.counters["observed_total_tokens"])
        self.assertFalse(self.harness.usages[0]["usage_known"])
        with self.assertRaisesRegex(HarnessError, "unknown"):
            self.harness.reserve_model(50, 100, repair=True)
        self.assertEqual(self.harness.counters["model_calls"], 1)

    def test_missing_total_is_unknown_and_subsets_are_not_added(self):
        self.harness.reserve_model(50, 100)
        self.harness.record_usage({"input_tokens": 100, "output_tokens": 20})
        with self.assertRaisesRegex(HarnessError, "unknown"):
            self.harness.reserve_model(1, 1, repair=True)
        known = Harness(self.root, {}, "known")
        known.reserve_model(1, 1)
        known.record_usage({"input_tokens": 30000, "output_tokens": 10000,
                            "reasoning_output_tokens": 9000,
                            "cached_input_tokens": 25000, "total_tokens": 40000})
        self.assertEqual(known.counters["observed_total_tokens"], 40000)
        with self.assertRaisesRegex(HarnessError, "token alert"):
            known.reserve_model(1, 1, repair=True)

    def test_usage_requires_one_outstanding_reservation(self):
        with self.assertRaises(HarnessError):
            self.harness.record_usage({"total_tokens": 1})
        self.harness.reserve_model(1, 1)
        self.harness.record_usage({"total_tokens": 1})
        with self.assertRaises(HarnessError):
            self.harness.record_usage({"total_tokens": 1})

    def test_inconsistent_reported_usage_remains_unknown(self):
        self.harness.reserve_model(1, 1)
        self.harness.record_usage({"total_tokens": 1, "input_tokens": 30000, "output_tokens": 10000})
        self.assertFalse(self.harness.usages[0]["usage_known"])
        with self.assertRaisesRegex(HarnessError, "unknown"):
            self.harness.reserve_model(1, 1, repair=True)

    def test_policy_is_defensively_copied_and_cannot_raise_ceiling(self):
        policy = {"limits": {"max_http_requests": 1}}
        limited = Harness(self.root, policy, "limited")
        policy["limits"]["max_http_requests"] = 100
        retrieved = limited.policy
        retrieved["limits"]["max_http_requests"] = 100
        limited.before_http("https://www.anthropic.com/news")
        with self.assertRaises(HarnessError):
            limited.before_http("https://www.anthropic.com/news")
        wide = Harness(self.root, {"max_model_calls": 100}, "wide")
        wide.reserve_model(1, 1)
        wide.record_usage({"total_tokens": 1})
        wide.reserve_model(1, 1, repair=True)
        wide.record_usage({"total_tokens": 1})
        with self.assertRaises(HarnessError):
            wide.reserve_model(1, 1, repair=True)

    def test_paths_reject_traversal_absolute_and_escaping_symlink(self):
        self.assertEqual(self.harness.safe_path("outputs/run/digest.md"),
                         self.root.resolve() / "outputs/run/digest.md")
        for path in ("../outside", "/tmp/outside", "outputs/../../outside", "."):
            with self.subTest(path=path), self.assertRaises(HarnessError):
                self.harness.safe_path(path)
        with tempfile.TemporaryDirectory() as outside:
            (self.root / "escape").symlink_to(outside, target_is_directory=True)
            with self.assertRaises(HarnessError):
                self.harness.safe_path("escape/digest.md")
        (self.root / "inside").mkdir()
        (self.root / "alias").symlink_to(self.root / "inside", target_is_directory=True)
        self.assertEqual(self.harness.safe_path("alias/digest.md"), self.root.resolve() / "inside/digest.md")

    def test_finish_requires_fresh_matching_digest_and_manifest(self):
        self.harness.transition("collecting")
        self.harness.transition("verifying")
        digest = b"checked digest"
        manifest = {"selected": ["a"], "settings": {"version": 1}}
        with self.assertRaises(HarnessError):
            self.harness.finish(digest, manifest)
        self.harness.mark_verified(digest, manifest, False)
        with self.assertRaises(HarnessError):
            self.harness.finish(digest, manifest)
        self.harness.mark_verified(digest, manifest, True)
        with self.assertRaises(HarnessError):
            self.harness.finish(digest + b"edited", manifest)
        manifest["settings"]["version"] = 2
        with self.assertRaises(HarnessError):
            self.harness.finish(digest, manifest)
        self.harness.mark_verified(digest, manifest, True)
        self.assertEqual(self.harness.finish(digest, manifest)["state"], "finished")
        with self.assertRaisesRegex(HarnessError, "terminal"):
            self.harness.execute(Action("new", "select", {"article_ids": []}), lambda: self.fail("terminal effect"))
        with self.assertRaises(HarnessError):
            self.harness.before_http("https://www.anthropic.com/news")
        with self.assertRaises(HarnessError):
            self.harness.reserve_model(1, 1)

    def test_effect_after_verification_invalidates_prior_pass(self):
        self.harness.transition("verifying")
        self.harness.mark_verified(b"digest", {}, True)
        self.harness.execute(Action("select-1", "select", {"article_ids": []}), lambda: [])
        with self.assertRaises(HarnessError):
            self.harness.finish(b"digest", {})
        with self.assertRaises(HarnessError):
            self.harness.transition("finished")

    def test_finish_waits_for_inflight_effect(self):
        started, release = threading.Event(), threading.Event()
        def fetch():
            started.set()
            release.wait(timeout=2)
            return "done"
        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
            result = pool.submit(self.harness.execute,
                                 Action("fetch", "fetch", {"url": "https://www.anthropic.com/news"}), fetch)
            self.assertTrue(started.wait(timeout=2))
            try:
                self.harness.transition("verifying")
                self.harness.mark_verified(b"digest", {}, True)
                with self.assertRaisesRegex(HarnessError, "outstanding action"):
                    self.harness.finish(b"digest", {})
            finally:
                release.set()
            self.assertEqual(result.result(timeout=2), "done")
        self.harness.mark_verified(b"digest", {}, True)
        result = self.harness.execute(Action("finish", "finish", {}),
                                      lambda: self.harness.finish(b"digest", {}))
        self.assertEqual(result["state"], "finished")

    def test_event_redacts_sensitive_fields_without_losing_token_counts(self):
        event = self.harness.event("test", "ok", {"api_key": "do-not-keep", "nested": {
            "prompt": "private prompt", "input_tokens": 123}})
        self.assertEqual(event["details"]["api_key"], "[redacted]")
        self.assertEqual(event["details"]["nested"]["input_tokens"], 123)
        self.assertNotIn("private prompt", str(self.harness.events))


if __name__ == "__main__":
    unittest.main()
