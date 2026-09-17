#!/usr/bin/env python3
"""Regression tests for lib/pi_runner.py's answer parsing and scoring.

No test framework, no third-party dependencies (matches the rest of this
studio: Python 3.9+, standard library only) -- plain functions, plain
asserts, run directly:

  python3 lib/test_pi_runner.py

Covers two real bugs found in the 20-question context sweep:

1. `_NUM_LINE_RE` used to match only a single digit, so answers 10-20 were
   never recognized as top-level answers at all and were silently swallowed
   as continuation text of answer 9 -- every one of them was actually
   correct and got scored wrong or "hallucinated". Fixed by matching 1-2
   digits while keeping the strict-sequence rule (a line only starts a new
   answer if its number is exactly the next one expected), so a nested
   numbered list inside one answer (e.g. answer 5 enumerating its own
   "1. ... 2. ... 3. ... 4. ...") still cannot be misread as new top-level
   answers.
2. keywords_any groups made entirely of terms already present in the
   question text turn correct terse answers into misses, and number-format
   variants ("2,048K" vs "2048K") were not normalized. Fixed by normalizing
   both sides of every match (lowercase, strip thousands-separator commas)
   and skipping any keyword group that is fully echoed by the question text.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from lib.pi_runner import parse_numbered_answers, score_answer, score_question_v2  # noqa: E402

FAILURES = []


def check(label, condition):
    status = "ok" if condition else "FAIL"
    print(f"[{status}] {label}")
    if not condition:
        FAILURES.append(label)


# ---------------------------------------------------------------------------
# Bug 1: 20-answer sample, real text from evidence/context_sweep/run-200k.json
# (a real sweep run), with answer 5 modified to add a nested numbered list --
# the exact "nested list inside one answer" shape that motivated the
# strict-sequence rule in the first place, now combined with 2-digit ids.
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
    # The regression this guards against: with the old single-digit regex,
    # "10." through "20." never matched _NUM_LINE_RE as a new top-level
    # answer at all (a single leading digit followed by a second digit does
    # not satisfy `\d` alone followed immediately by `.`... in practice the
    # old pattern's `(\d)` captured just "1" and left a stray "0." in the
    # text, which never equalled the strict-sequence's `expected_next`
    # either) -- so everything from "10." onward was appended as
    # continuation of answer 9. Assert that did not happen here.
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


# ---------------------------------------------------------------------------
# Bug 2a: normalization -- comma-insensitive, case-insensitive matching.
# ---------------------------------------------------------------------------
def test_comma_and_case_normalization():
    check(
        "'2,048K' in keywords matches '2048K' in the answer",
        score_answer("The window is 2048K tokens.", [["2,048K"]]),
    )
    check(
        "'2048K' in keywords matches '2,048,000' style answer text",
        score_answer("about 2,048,000 tokens total", [["2048000"]]),
    )
    check(
        "case-insensitive still works alongside comma stripping",
        score_answer("Context window: 8,192 TOKENS", [["8192 tokens"]]),
    )


# ---------------------------------------------------------------------------
# Bug 2b: a keyword group made entirely of terms already in the question
# text is skipped, not required.
# ---------------------------------------------------------------------------
def test_non_discriminative_group_skipped():
    question_text = "According to the survey, what maximum context window does LongRoPE achieve?"
    # Group 1 ("LongRoPE") is fully present in the question text and must be
    # skipped; group 2 (the number) is not in the question text and must
    # still be required.
    keywords_any = [["LongRoPE", "longrope"], ["2048K", "2,048K"]]
    check(
        "terse correct answer (no method name, just the number) now scores correct",
        score_answer("2048K tokens.", keywords_any, question_text=question_text, question_id="q2-test"),
    )
    check(
        "an answer missing the actual number still fails (the real group still required)",
        not score_answer("It achieves a very long context window.", keywords_any, question_text=question_text, question_id="q2-test"),
    )


def test_non_discriminative_skip_does_not_affect_v2_scoring_integration():
    question = {
        "id": 2,
        "question": "According to the survey, what does LongRoPE achieve?",
        "keywords_any": [["LongRoPE"], ["2048K", "2,048K"]],
        "must_not_contain": [],
    }
    result = score_question_v2("2048K tokens, via a two-stage approach.", question, slice_real_tokens=999999)
    check("score_question_v2 verdict is correct with the non-discriminative fix", result["verdict"] == "correct")


def main():
    test_parses_all_20_with_two_digit_ids()
    test_nested_list_inside_answer_5_does_not_reset_sequence()
    test_default_n_no_longer_truncates_at_5()
    test_comma_and_case_normalization()
    test_non_discriminative_group_skipped()
    test_non_discriminative_skip_does_not_affect_v2_scoring_integration()

    print()
    if FAILURES:
        print(f"{len(FAILURES)} check(s) FAILED:")
        for f in FAILURES:
            print(f"  - {f}")
        sys.exit(1)
    print("All checks passed.")


if __name__ == "__main__":
    main()
