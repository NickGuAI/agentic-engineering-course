import copy
from datetime import datetime, timezone
import json
from pathlib import Path
import shutil
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "code"))
from evidence import SummaryCache, fingerprint, packet_for
from experiments import FixtureModel, fixture_collection, demonstration, compare_runs
from run import load_policy, research, verify_saved
from verify import verify_digest


class WorkflowTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        shutil.copy(ROOT / "policy.json", self.root / "policy.json")
        shutil.copytree(ROOT / "prompts", self.root / "prompts")
        self.policy = load_policy(self.root)
        self.as_of = datetime(2026, 9, 18, 16, tzinfo=timezone.utc)
        self.collection = fixture_collection()

    def run_research(self, rid, **kwargs):
        return research(self.root, self.policy, self.as_of,
                        kwargs.pop("model", FixtureModel(self.root)), run_id=rid,
                        collection=kwargs.pop("collection", self.collection),
                        mode="synthetic_fixture", **kwargs)

    def read(self, rid, name):
        return json.loads((self.root / "outputs" / rid / (name + ".json")).read_text())

    def test_valid_run_one_batch_then_zero_call_cache_replay(self):
        model = FixtureModel(self.root)
        first = self.run_research("cold", model=model)
        self.assertEqual(first["status"], "complete", first)
        self.assertEqual(len(model.calls), 1)
        self.assertEqual(len(self.read("cold", "digest")["items"]), 5)
        self.assertTrue(verify_saved(self.root, "cold")["passed"])
        second_model = FixtureModel(self.root)
        second = self.run_research("warm", model=second_model)
        self.assertEqual(second["status"], "complete", second)
        self.assertEqual(second_model.calls, [])
        self.assertEqual(self.read("warm", "usage")["cache_hits"], 5)
        # Exported manifests hold paragraph IDs/hashes, not downloaded full text.
        for article in self.read("cold", "manifest")["selected_articles"]:
            self.assertNotIn("paragraphs", article)
            self.assertNotIn("text", article["packet"]["evidence"][0])

    def test_repair_only_invalid_article_once(self):
        model = FixtureModel(self.root, invalid_first=True)
        report = self.run_research("repair", model=model, use_cache=False)
        self.assertEqual(report["status"], "complete", report)
        self.assertEqual(len(model.calls), 2)
        self.assertEqual(len(model.calls[1]["articles"]), 1)

    def test_unknown_usage_disables_repair_but_keeps_valid_subset(self):
        model = FixtureModel(self.root, invalid_first=True, unknown_usage=True)
        report = self.run_research("unknown", model=model, use_cache=False)
        self.assertEqual(report["status"], "partial", report)
        self.assertEqual(len(model.calls), 1)
        self.assertEqual(len(self.read("unknown", "digest")["items"]), 4)
        self.assertTrue(verify_saved(self.root, "unknown")["passed"])

    def test_cached_subset_survives_new_model_failure(self):
        baseline = copy.deepcopy(self.collection)
        baseline["articles"] = baseline["articles"][:1]
        self.assertEqual(self.run_research("baseline", collection=baseline)["status"], "complete")
        class FailingModel(FixtureModel):
            def generate(self, payload, timeout):
                raise RuntimeError("fixture_timeout")
        report = self.run_research("new-fails", model=FailingModel(self.root))
        self.assertEqual(report["status"], "partial", report)
        self.assertEqual(len(self.read("new-fails", "digest")["items"]), 1)
        self.assertTrue(verify_saved(self.root, "new-fails")["passed"])

    def test_failure_stop_then_corrected_partial(self):
        before = self.run_research("before", fail_source="anthropic_news", source_failure_policy="stop")
        after = self.run_research("after", fail_source="anthropic_news", source_failure_policy="partial")
        self.assertEqual(before["status"], "blocked", before)
        self.assertFalse((self.root / "outputs/before/digest.md").exists())
        self.assertEqual(after["status"], "partial", after)
        self.assertTrue(verify_saved(self.root, "after")["passed"])
        self.assertEqual(self.read("before", "manifest")["input_snapshot_hash"],
                         self.read("after", "manifest")["input_snapshot_hash"])

    def test_outage_is_blocked_and_successful_empty_has_no_model_calls(self):
        empty = copy.deepcopy(self.collection)
        empty["articles"] = []
        model = FixtureModel(self.root)
        self.assertEqual(self.run_research("empty", collection=empty, model=model)["status"], "empty")
        self.assertEqual(model.calls, [])
        for source in empty["sources"]:
            source["status"] = "error"
            source["error_code"] = "fixture_outage"
        self.assertEqual(self.run_research("outage", collection=empty)["status"], "blocked")

    def test_editing_saved_digest_invalidates_verification(self):
        self.run_research("editable")
        md = self.root / "outputs/editable/digest.md"
        md.write_text(md.read_text() + "unverified edit\n")
        result = verify_saved(self.root, "editable")
        self.assertFalse(result["passed"])
        self.assertIn("markdown_changed_since_check", result["failures"])

    def test_malformed_cache_is_a_miss(self):
        cache = SummaryCache(self.root / "work/cache")
        key = fingerprint("test")
        (self.root / "work/cache" / (key + ".json")).write_text("[]")
        self.assertIsNone(cache.get(key))

    def test_malformed_saved_digest_returns_failed_check(self):
        self.run_research("malformed")
        path = self.root / "outputs/malformed/digest.json"
        value = json.loads(path.read_text())
        value["items"] = [None]
        path.write_text(json.dumps(value))
        self.assertFalse(verify_saved(self.root, "malformed")["passed"])

    def test_changed_content_invalidates_only_one_summary(self):
        self.run_research("original")
        collection = copy.deepcopy(self.collection)
        collection["articles"][0]["paragraphs"][0]["text"] += " The preview adds a changelog."
        collection["articles"][0]["content_hash"] = fingerprint(collection["articles"][0]["paragraphs"])
        model = FixtureModel(self.root)
        result = self.run_research("changed", collection=collection, model=model)
        self.assertEqual(result["status"], "complete", result)
        self.assertEqual(len(model.calls), 1)
        self.assertEqual(len(model.calls[0]["articles"]), 1)

    def test_old_cached_article_is_not_published(self):
        self.run_research("recent")
        self.as_of = datetime(2026, 10, 1, 16, tzinfo=timezone.utc)
        model = FixtureModel(self.root)
        result = self.run_research("old", model=model)
        self.assertEqual(result["status"], "empty", result)
        self.assertEqual(model.calls, [])

    def test_essential_caveats_cannot_be_dropped_to_fit_budget(self):
        article = self.collection["articles"][0]
        with self.assertRaisesRegex(ValueError, "essential_evidence_exceeds_budget"):
            packet_for(article, limit=10)

    def test_demo_measures_compression_separately_from_cache(self):
        report = demonstration(self.root)
        self.assertGreaterEqual(report["application_input_reduction"], 0.30)
        self.assertEqual(report["real_model_calls"], 0)
        warm = self.read(report["run_ids"]["warm"], "usage")
        self.assertEqual(warm["counters"]["model_calls"], 0)

    def test_failed_runs_cannot_claim_token_savings(self):
        class FailedModel(FixtureModel):
            def generate(self, payload, timeout):
                raise RuntimeError("fixture_failure")
        for mode in ("full", "compact"):
            result = self.run_research("failed-" + mode, model=FailedModel(self.root),
                                       evidence_mode=mode, use_cache=False)
            self.assertEqual(result["status"], "blocked")
        report = compare_runs(self.root, ["failed-full", "failed-compact"])
        self.assertIsNone(report["application_input_reduction"])

    def test_changed_output_cannot_claim_token_savings(self):
        self.run_research("full", evidence_mode="full", use_cache=False)
        self.run_research("compact", evidence_mode="compact", use_cache=False)
        md = self.root / "outputs/compact/digest.md"
        md.write_text(md.read_text() + "unverified content\n")
        report = compare_runs(self.root, ["full", "compact"])
        self.assertIsNone(report["application_input_reduction"])
        self.assertFalse(report["runs"][1]["fresh_verification_passed"])


if __name__ == "__main__":
    unittest.main()
