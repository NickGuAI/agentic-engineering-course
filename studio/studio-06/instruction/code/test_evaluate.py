"""Offline fixtures for report packaging and native score collection."""

import csv
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

SPEC = importlib.util.spec_from_file_location("studio06_evaluate", Path(__file__).with_name("evaluate.py"))
evaluate = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(evaluate)


class EvaluationFixtures(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.selected = evaluate.tasks()
        for mode in evaluate.MODES:
            directory = self.root / "reports" / mode
            directory.mkdir(parents=True)
            for task in self.selected:
                (directory / f"{task['id']}.md").write_text(f"Fixture report for {mode}, task {task['id']}.\n")
        self.output = self.root / "eval/race-01"

    def fixture_scores(self):
        for mode, score in (("single", 0.4), ("multi", 0.6)):
            destination = self.output / mode
            destination.mkdir(parents=True)
            rows = [{"id": task["id"], "prompt": task["prompt"], **{field: score for field in evaluate.SCORE_FIELDS}} for task in self.selected]
            (destination / "raw_results.jsonl").write_text("".join(json.dumps(row) + "\n" for row in rows))

    def test_packaging_preserves_prompts_and_reports(self):
        evaluate.prepare(self.root, self.output, self.selected)
        for mode in evaluate.MODES:
            rows = evaluate.read_jsonl(self.output / "input" / f"{mode}.jsonl")
            self.assertEqual([row["id"] for row in rows], [99, 93, 100])
            for row, task in zip(rows, self.selected):
                self.assertEqual(row["prompt"], task["prompt"])
                self.assertEqual(row["article"], (self.root / "reports" / mode / f"{task['id']}.md").read_text())
        self.assertEqual((self.output / "queries.jsonl").read_bytes(), evaluate.TASK_FILE.read_bytes())
        with self.assertRaises(FileExistsError):
            evaluate.prepare(self.root, self.output, self.selected)

    def test_missing_report_does_not_create_output(self):
        (self.root / "reports/multi/99.md").write_text("")
        with self.assertRaises(ValueError):
            evaluate.prepare(self.root, self.output, self.selected)
        self.assertFalse(self.output.exists())

    def test_summarize_six_native_scores(self):
        self.fixture_scores()
        evaluate.summarize(self.output, self.selected)
        with (self.output / "comparison.csv").open() as handle:
            rows = list(csv.DictReader(handle))
        self.assertEqual([row["task_id"] for row in rows], ["99", "93", "100", "mean"])
        self.assertEqual(rows[-1]["multi_minus_single"], "0.200000")

    def test_missing_or_wrong_prompt_score_is_rejected(self):
        self.fixture_scores()
        path = self.output / "multi/raw_results.jsonl"
        rows = evaluate.read_jsonl(path)
        path.write_text(json.dumps(rows[0]) + "\n")
        with self.assertRaises(ValueError):
            evaluate.summarize(self.output, self.selected)
        rows[0]["prompt"] = "Changed prompt"
        path.write_text("".join(json.dumps(row) + "\n" for row in rows))
        with self.assertRaises(ValueError):
            evaluate.summarize(self.output, self.selected)

    def test_native_models_and_defaults(self):
        with patch.dict(evaluate.os.environ, {"OPENAI_API_KEY": "offline-fixture", "MAX_OUTPUT_TOKENS": "12", "LLM_CONCURRENCY": "1"}):
            env = evaluate.evaluator_env()
        self.assertEqual(env["RACE_MODEL"], "gpt-5.5")
        self.assertEqual(env["CLEAN_MODEL"], "gpt-5.6-luna")
        self.assertEqual(env["OPENAI_API_KEY"], "offline-fixture")
        self.assertNotIn("MAX_OUTPUT_TOKENS", env)
        self.assertNotIn("LLM_CONCURRENCY", env)

    def test_missing_dimension_is_rejected(self):
        self.fixture_scores()
        path = self.output / "single/raw_results.jsonl"
        rows = evaluate.read_jsonl(path)
        del rows[0]["readability"]
        path.write_text("".join(json.dumps(row) + "\n" for row in rows))
        with self.assertRaisesRegex(ValueError, "readability"):
            evaluate.summarize(self.output, self.selected)


if __name__ == "__main__":
    unittest.main()
