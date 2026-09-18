#!/usr/bin/env python3
"""Regression tests for lib/pi_runner.py's answer parsing and small helpers.

No test framework, no third-party dependencies -- plain functions, plain
asserts, run directly:

  python3 lib/test_pi_runner.py

Covers a real bug found in an earlier multi-question sweep: `_NUM_LINE_RE`
used to match only a single digit, so answers numbered 10 and above were
never recognized as top-level answers at all and were silently swallowed as
continuation text of answer 9. Fixed by matching 1-2 digits while keeping the
strict-sequence rule (a line only starts a new answer if its number is
exactly the next one expected), so a nested numbered list inside one answer
(e.g. answer 5 enumerating its own "1. ... 2. ... 3. ... 4. ...") still
cannot be misread as new top-level answers.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from lib.pi_runner import md_table, parse_numbered_answers  # noqa: E402

FAILURES = []


def check(label, condition):
    status = "ok" if condition else "FAIL"
    print(f"[{status}] {label}")
    if not condition:
        FAILURES.append(label)


# ---------------------------------------------------------------------------
# 20-answer sample, with answer 5 modified to add a nested numbered list --
# the exact "nested list inside one answer" shape that motivated the
# strict-sequence rule in the first place, combined with 2-digit ids.
# ---------------------------------------------------------------------------
SAMPLE_20 = (
    "1. Over 1,400 research papers.\n"
    "2. 2,048K tokens, using a two-stage approach.\n"
    "3. Approximately 20%.\n"
    "4. Humans: 92%; advanced models such as GPT-4: 15%.\n"
    "5. The four categories are, namely: 1. Retrieval-Augmented Generation "
    "2. Memory Systems 3. Tool-Integrated Reasoning 4. Multi-Agent Systems.\n"
    "6. 56.1%.\n"
    "7. A U-shaped curve: best at the beginning and end, worst in the middle.\n"
    "8. 8,192 tokens.\n"
    "9. System instructions, working context, and FIFO queue.\n"
    "10. 10.6%.\n"
    "11. TGC means Task Goal Completion; online ACE surpasses IBM CUGA by 8.4% on test-challenge TGC.\n"
    "12. NOT FOUND.\n"
    "13. NOT FOUND.\n"
    "14. NOT FOUND.\n"
    "15. NOT FOUND.\n"
    "16. NOT FOUND.\n"
    "17. NOT FOUND.\n"
    "18. NOT FOUND.\n"
    "19. NOT FOUND.\n"
    "20. NOT FOUND."
)


def test_parses_all_20_with_two_digit_ids():
    answers = parse_numbered_answers(SAMPLE_20, n=20)
    check("all 20 ids present", set(answers.keys()) == set(range(1, 21)))
    check("answer 10 parsed (was swallowed by the single-digit bug)", answers.get(10) == "10.6%.")
    check(
        "answer 11 parsed in full",
        answers.get(11)
        == "TGC means Task Goal Completion; online ACE surpasses IBM CUGA by 8.4% on test-challenge TGC.",
    )
    check("answer 20 parsed", answers.get(20) == "NOT FOUND.")
    check(
        "answer 9 does NOT absorb answers 10+ (the actual bug)",
        answers.get(9) == "System instructions, working context, and FIFO queue.",
    )


def test_nested_list_inside_answer_5_does_not_reset_sequence():
    answers = parse_numbered_answers(SAMPLE_20, n=20)
    # Answer 5's own nested "1./2./3./4." must stay inside answer 5's text,
    # not be misread as new top-level answers overwriting 1-4.
    check(
        "answer 1 is untouched by answer 5's nested list",
        answers.get(1) == "Over 1,400 research papers.",
    )
    check(
        "answer 2 is untouched by answer 5's nested list",
        answers.get(2) == "2,048K tokens, using a two-stage approach.",
    )
    check("answer 5 contains its own nested list text", "Tool-Integrated Reasoning" in answers.get(5, ""))
    check(
        "answer 6 starts correctly right after answer 5 (sequence not corrupted)",
        answers.get(6) == "56.1%.",
    )


def test_default_n_no_longer_truncates_at_5():
    # A caller that forgets to pass n explicitly must still see ids past 5.
    answers = parse_numbered_answers(SAMPLE_20)
    check("default n parses id 20 too", 20 in answers)


def test_single_answer_one_line():
    answers = parse_numbered_answers("1. kitchen", n=1)
    check("single-item parse", answers.get(1) == "kitchen")


def test_md_table_shape():
    table = md_table(["a", "b"], [["1", "2"], ["3", "4"]])
    lines = table.splitlines()
    check("md_table has a header, separator, and one line per row", len(lines) == 4)
    check("md_table header row", lines[0] == "| a | b |")
    check("md_table separator row", lines[1] == "| --- | --- |")


def main():
    test_parses_all_20_with_two_digit_ids()
    test_nested_list_inside_answer_5_does_not_reset_sequence()
    test_default_n_no_longer_truncates_at_5()
    test_single_answer_one_line()
    test_md_table_shape()

    print()
    if FAILURES:
        print(f"{len(FAILURES)} check(s) FAILED:")
        for f in FAILURES:
            print(f"  - {f}")
        sys.exit(1)
    print("All checks passed.")


if __name__ == "__main__":
    main()
