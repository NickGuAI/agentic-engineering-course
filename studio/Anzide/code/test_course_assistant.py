"""Offline tests for the Course Assistant harness. No model, no network.

Run from this folder:  python3 -m unittest -v test_course_assistant
"""
from __future__ import annotations

import json
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import course_assistant as ca  # noqa: E402
from check_tutorial import check, parse_coverage, parse_errata  # noqa: E402
from source_blocks import number_blocks, parse_numbered, split_blocks  # noqa: E402

SOURCE = """# Lab 9: Ship it

## Prerequisites
- Node.js `>= 22.19`
- Run `npm install -g demo-tool` once.

## Steps
Run the following from the repo root:
```bash
python3 run.py --team <team>
```
Submit by Friday, September 25, 2026 at https://example.edu/submit?x=1.

Teams of at most 3 students.
"""

TUTORIAL = """---
title: "Lab 9: Step-by-Step Tutorial"
subtitle: "Session 2"
---

## At a glance
- **Goal:** ship the demo tool.
- **You will produce:** a submission.

## Before you start
### What you need
- Node.js `>= 22.19`
- Teams of at most 3 students.
### Concepts you may not know
- **Global install** — `npm install -g` puts a tool on your PATH for every project, like a system-wide pip install.

## Tutorial 1 — Ship it
### Step 1.1 — Install the tool
**Do:** Run `npm install -g demo-tool` once.
**Check:** the command exits without an error.

### Step 1.2 — Run it
**Do:** from the repo root:
```bash
python3 run.py --team <team>
```
**Check:** the script finishes.

## Wrap-up
Submit by Friday, September 25, 2026 at https://example.edu/submit?x=1.

## Errata
None found.

## Omitted
Nothing omitted.
"""

COVERAGE = """S1 -> At a glance
S2 -> Before you start
S3 -> Before you start
S4 -> Step 1.1
S5 -> Step 1.2
S6 -> Step 1.2
S7 -> Step 1.2
S8 -> Wrap-up
S9 -> Before you start
"""


def blocks_of(text: str) -> dict[int, str]:
    return parse_numbered(number_blocks(text))


class SourceBlocksTest(unittest.TestCase):
    def test_fences_stay_whole_and_list_items_split(self):
        blocks = split_blocks(SOURCE)
        self.assertEqual(blocks[0], "# Lab 9: Ship it")
        self.assertIn("- Node.js `>= 22.19`", blocks)
        self.assertIn("- Run `npm install -g demo-tool` once.", blocks)
        fence = [b for b in blocks if b.startswith("```")]
        self.assertEqual(len(fence), 1)
        self.assertEqual(fence[0].count("```"), 2)
        self.assertEqual(len(blocks), 9)

    def test_number_and_parse_roundtrip(self):
        numbered = number_blocks(SOURCE)
        self.assertTrue(numbered.startswith("[S1]\n# Lab 9"))
        parsed = parse_numbered(numbered)
        self.assertEqual(list(parsed), list(range(1, 10)))
        self.assertEqual(parsed[7], "```bash\npython3 run.py --team <team>\n```")

    def test_html_comments_are_not_blocks(self):
        blocks = split_blocks("<!-- snapshot header\n   two lines -->\n\n# Title\n\nBody <!-- inline --> text\n")
        self.assertEqual(blocks, ["# Title", "Body  text"])


class CheckTest(unittest.TestCase):
    def setUp(self):
        self.blocks = blocks_of(SOURCE)

    def ids_failed(self, result):
        return [c["id"] for c in result["checks"] if not c["passed"]]

    def test_good_tutorial_passes(self):
        result = check(self.blocks, TUTORIAL, COVERAGE)
        self.assertEqual(self.ids_failed(result), [], json.dumps(result["checks"], indent=1))
        self.assertEqual(result["stats"]["steps"], 2)
        self.assertEqual(result["stats"]["notes"], 1)

    def test_missing_command_fails_cover2(self):
        tutorial = TUTORIAL.replace("python3 run.py --team <team>", "python3 run.py --team myteam")
        result = check(self.blocks, tutorial, COVERAGE)
        self.assertIn("COVER-2", self.ids_failed(result))

    def test_missing_url_and_number_fail(self):
        tutorial = TUTORIAL.replace("https://example.edu/submit?x=1", "the portal").replace("September 25, 2026", "next Friday")
        result = check(self.blocks, tutorial, COVERAGE)
        self.assertIn("COVER-3", self.ids_failed(result))
        self.assertIn("COVER-4", self.ids_failed(result))

    def test_unmapped_block_fails_cover1(self):
        result = check(self.blocks, TUTORIAL, COVERAGE.replace("S9 -> Before you start\n", ""))
        failed = [c for c in result["checks"] if c["id"] == "COVER-1"][0]
        self.assertFalse(failed["passed"])
        self.assertIn("S9 not mapped", failed["failures"])

    def test_omitted_block_is_exempt_from_literal_checks_but_reported(self):
        tutorial = TUTORIAL.replace("Submit by Friday, September 25, 2026 at https://example.edu/submit?x=1.", "Submit on time.")
        coverage = COVERAGE.replace("S8 -> Wrap-up", "S8 -> OMITTED: deadline handled on CourseWorks")
        result = check(self.blocks, tutorial, coverage)
        self.assertNotIn("COVER-3", self.ids_failed(result))
        self.assertEqual(result["omitted"][0]["block"], 8)
        self.assertIn("CourseWorks", result["omitted"][0]["reason"])

    def test_step_numbering_gap_and_missing_check(self):
        tutorial = TUTORIAL.replace("### Step 1.2 — Run it", "### Step 1.3 — Run it").replace("**Check:** the script finishes.\n", "")
        coverage = COVERAGE.replace("Step 1.2", "Step 1.3")
        result = check(self.blocks, tutorial, coverage)
        self.assertIn("STRUCT-2", self.ids_failed(result))
        self.assertIn("STRUCT-3", self.ids_failed(result))

    def test_word_budget(self):
        padded = TUTORIAL.replace("Nothing omitted.", "Nothing omitted. " + "filler " * 800)
        result = check(self.blocks, padded, COVERAGE)
        self.assertIn("LENGTH-1", self.ids_failed(result))

    def test_long_note_fails_length2(self):
        long_note = "- **Global install** — " + "word " * 60
        tutorial = TUTORIAL.replace("- **Global install** — `npm install -g` puts a tool on your PATH for every project, like a system-wide pip install.", long_note)
        result = check(self.blocks, tutorial, COVERAGE)
        self.assertIn("LENGTH-2", self.ids_failed(result))

    def test_errata_must_quote_real_text(self):
        good = TUTORIAL.replace("None found.", "| Block | Source says | Should be | Evidence | Confidence |\n|---|---|---|---|---|\n"
                                               "| S3 | `>= 22.19` | `>= 22.20` | release notes | unsure |")
        self.assertNotIn("ERRATA-1", self.ids_failed(check(self.blocks, good, COVERAGE)))
        bad = TUTORIAL.replace("None found.", "| Block | Source says | Should be | Evidence | Confidence |\n|---|---|---|---|---|\n"
                                              "| S3 | `>= 18.0` | `>= 22.19` | made up | certain |")
        result = check(self.blocks, bad, COVERAGE)
        self.assertIn("ERRATA-1", self.ids_failed(result))
        bad_conf = good.replace("| unsure |", "| maybe |")
        self.assertIn("ERRATA-1", self.ids_failed(check(self.blocks, bad_conf, COVERAGE)))

    def test_parsers(self):
        targets, omitted, problems = parse_coverage("S1 -> Step 1.1, Reference\nS2 -> OMITTED: off topic\nbogus\n")
        self.assertEqual(targets[1], ["Step 1.1", "Reference"])
        self.assertEqual(omitted[2], "off topic")
        self.assertEqual(len(problems), 1)
        rows, problems = parse_errata("| Block | Source says | Should be | Evidence | Confidence |\n|---|---|---|---|---|\n| S3 | a | b | c | likely |\n| S4 | only | three |\n")
        self.assertEqual(rows[0]["block"], 3)
        self.assertEqual(len(problems), 1)


class HarnessTest(unittest.TestCase):
    def test_parse_response_markers(self):
        text = "preamble\n<<<TUTORIAL>>>\n## At a glance\n<<<COVERAGE>>>\nS1 -> At a glance\n<<<END>>>\n"
        tutorial, coverage, problem = ca.parse_response(text)
        self.assertEqual(problem, "")
        self.assertEqual(tutorial, "## At a glance\n")
        self.assertEqual(coverage, "S1 -> At a glance\n")
        self.assertTrue(ca.parse_response("CANNOT_COMPLETE: empty source")[2].startswith("CANNOT_COMPLETE"))
        self.assertIn("markers", ca.parse_response("no markers here")[2])

    def test_normalize_markdown_adds_blank_lines_outside_fences(self):
        raw = ("**Do:** pick one:\n1. a\n2. b\nDo not do c.\n**Check:** done.\n### Step 1.2 — Next\n"
               "```bash\nx\n- not a list\n```\n| a | b |\n|---|---|\n| 1 | 2 |\nAfter table.\n")
        out = ca.normalize_markdown(raw)
        self.assertIn("pick one:\n\n1. a\n2. b\n\nDo not do c.\n\n**Check:** done.\n\n### Step 1.2 — Next\n\n```bash", out)
        self.assertIn("```bash\nx\n- not a list\n```\n\n| a | b |\n|---|---|\n| 1 | 2 |\nAfter table.", out)
        self.assertEqual(ca.normalize_markdown(out), out)  # idempotent

    def test_trace_summary_lists_tool_calls_and_denials(self):
        events = [
            {"type": "system", "subtype": "init", "model": "m", "session_id": "s", "tools": ["Read"], "mcp_servers": [], "permissionMode": "default"},
            {"type": "assistant", "message": {"content": [{"type": "tool_use", "name": "Read", "input": {"file_path": "/x/y.md"}}]}},
            {"type": "user", "message": {"content": [{"type": "tool_result", "content": "hello", "is_error": False}]}},
            {"type": "result", "subtype": "success", "is_error": False, "num_turns": 2, "duration_ms": 1500, "total_cost_usd": 0.01,
             "usage": {"input_tokens": 10, "output_tokens": 5}, "permission_denials": [{"tool_name": "Bash", "tool_input": {"command": "ls"}}]},
        ]
        summary = ca.summarize_trace(events)
        self.assertIn("1. **Read**(file_path='/x/y.md')", summary)
        self.assertIn("result: 5 chars", summary)
        self.assertIn("Permission denials: 1", summary)
        self.assertIn("Bash(", summary)

    def test_find_documents_in_directory_skips_unsupported_and_hidden(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "b.md").write_text("# b")
            (root / "a.txt").write_text("a")
            (root / "c.png").write_bytes(b"\x89PNG")
            (root / ".hidden").mkdir()
            (root / ".hidden" / "d.md").write_text("# d")
            (root / "sub").mkdir()
            (root / "sub" / "e.md").write_text("# e")
            names = [p.relative_to(root).as_posix() for p in ca.find_documents(root)]
            self.assertEqual(names, ["a.txt", "b.md", "sub/e.md"])
            self.assertEqual(ca.find_documents(root / "b.md"), [root / "b.md"])

    def test_replay_pipeline_end_to_end(self):
        """The full harness with a fixture response: extraction, checks, report, and (if tools exist) the PDF."""
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / "lab9.md"
            source.write_text(SOURCE)
            fixture = root / "response.txt"
            fixture.write_text(f"<<<TUTORIAL>>>\n{TUTORIAL}<<<COVERAGE>>>\n{COVERAGE}<<<END>>>\n")
            out = root / "run"
            code = ca.main([str(source), "--replay", str(fixture), "--out", str(out)])
            report = (out / "report.md").read_text()
            result = json.loads((out / "check.json").read_text())
            self.assertTrue((out / "source.numbered.md").exists())
            self.assertTrue((out / "tutorial.md").exists())
            self.assertIn("REPLAY FIXTURE", report)
            core = [c for c in result["checks"] if c["id"] != "PDF-1"]
            self.assertTrue(all(c["passed"] for c in core), report)
            if shutil.which("pandoc") and (ca.find_chrome() or shutil.which("xelatex")):
                self.assertEqual(code, 0, report)
                self.assertTrue((out / "lab9-tutorial.pdf").exists())


if __name__ == "__main__":
    unittest.main()
