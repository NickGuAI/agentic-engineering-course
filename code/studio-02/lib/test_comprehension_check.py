#!/usr/bin/env python3
"""Regression test for comprehension_check.py's label parser and results
writer, on a synthetic 20-item file with fake answers. Makes NO pi calls.

Plain functions, plain asserts, standard library only -- run directly:

  python3 lib/test_comprehension_check.py
"""
import json
import shutil
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from lib.pi_runner import parse_labeled_lines, write_json  # noqa: E402
import comprehension_check as cc  # noqa: E402

FAILURES = []


def check(label, condition):
    status = "ok" if condition else "FAIL"
    print(f"[{status}] {label}")
    if not condition:
        FAILURES.append(label)


# ---------------------------------------------------------------------------
# Synthetic 20-item file: 10 SUPPORTED, 7 CONTRADICTED, 3 NOT_FOUND, one item
# per document 1-13, the remaining 7 spread over the "longer" documents
# (4, 5, 6, 7, 9, 12, 13), matching the quota shape in the contract.
# ---------------------------------------------------------------------------
DOC_TITLES = {
    1: "A Survey of Context Engineering for LLMs (Mei 2025)", 2: "Lost in the Middle (Liu 2023)",
    3: "MemGPT (Packer 2023)", 4: "ACE: Agentic Context Engineering (Zhang 2025)", 5: "RULER (Hsieh 2024)",
    6: "LongMemEval (Wu 2024)", 7: "ReAct (Yao 2022)", 8: "RAG (Lewis 2020)",
    9: "Generative Agents (Park 2023)", 10: "NoLiMa (Modarressi 2025)", 11: "Mem0 (2025)",
    12: "GPT-3 (Brown 2020)", 13: "Gemini 1.5 technical report (2024)",
}
ITEM_DOCS = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 4, 5, 6, 7, 9, 12, 13]
ITEM_LABELS = ["SUPPORTED"] * 10 + ["CONTRADICTED"] * 7 + ["NOT_FOUND"] * 3
ALTERATIONS = ["none"] * 10 + ["number", "entity", "negation", "scope", "attribution", "number", "entity"] + ["none"] * 3


def build_synthetic_items():
    items = []
    for i in range(1, 21):
        doc = ITEM_DOCS[i - 1]
        items.append({
            "id": i,
            "doc": doc,
            "doc_title": DOC_TITLES[doc],
            "excerpt": f"Synthetic excerpt text for item {i}, standing in for a real 30-90 word quotation.",
            "excerpt_depth_tokens": doc * 10000 + i * 37,  # monotonic-ish, distinct, not the real depths
            "kind": ["definition", "claim", "reference"][i % 3],
            "statement": f"Synthetic paraphrased statement number {i}, for item in {DOC_TITLES[doc]}.",
            "label": ITEM_LABELS[i - 1],
            "alteration": ALTERATIONS[i - 1],
            "why": f"Synthetic reason for item {i}.",
            "verification": f"grep -n 'synthetic marker {i}' combined.txt",
        })
    return items


def fake_answer_text(items, wrong_ids_mode):
    """Build a plausible model answer_text: every item gets the expected
    label EXCEPT the ids in wrong_ids_mode, which get a deliberately wrong
    one, so scoring and the results writer can be exercised on real misses,
    not just an all-correct run. Mixes 1-2 digit ids, both NOT FOUND and
    NOT_FOUND spellings, and a justification that itself contains numbered
    text (to exercise the strict-sequence guard)."""
    lines = []
    other_label = {"SUPPORTED": "CONTRADICTED", "CONTRADICTED": "SUPPORTED", "NOT_FOUND": "SUPPORTED"}
    for item in items:
        label = other_label[item["label"]] if item["id"] in wrong_ids_mode else item["label"]
        label_text = "NOT FOUND" if label == "NOT_FOUND" and item["id"] % 2 == 0 else label
        just = f"See {item['doc_title']}, which discusses point 1, point 2, and point 3 of the claim."
        lines.append(f"{item['id']}. {label_text} - {just}")
    return "\n".join(lines)


def test_parser_handles_two_digit_ids_and_both_not_found_spellings():
    items = build_synthetic_items()
    text = fake_answer_text(items, wrong_ids_mode=set())
    parsed = parse_labeled_lines(text, n=20)
    check("all 20 ids parsed", set(parsed.keys()) == set(range(1, 21)))
    check("id 18 (two-digit, NOT_FOUND expected) parsed with a label", parsed[18]["label"] in ("NOT_FOUND",))
    check("id 20 parsed", parsed[20]["label"] is not None)
    # item 18's label_text alternates NOT FOUND / NOT_FOUND by id parity; both
    # must normalize to the same canonical string.
    for i in (18, 19, 20):
        check(f"id {i} label canonicalized to NOT_FOUND", parsed[i]["label"] == "NOT_FOUND")
    check(
        "justification captured despite containing 'point 1, point 2, point 3'",
        "point 1" in parsed[1]["justification"] and "point 3" in parsed[1]["justification"],
    )
    check(
        "the embedded 'point 1/2/3' text did not reset the strict sequence",
        parsed[2]["label"] == items[1]["label"] or parsed[2]["label"] in ("SUPPORTED", "CONTRADICTED", "NOT_FOUND"),
    )


def test_score_items_marks_wrong_ids_wrong():
    items = build_synthetic_items()
    text = fake_answer_text(items, wrong_ids_mode={5, 15})
    parsed = parse_labeled_lines(text, n=20)
    rows = cc.score_items(items, parsed)
    by_id = {r["id"]: r for r in rows}
    check("item 5 scored incorrect (deliberately flipped)", by_id[5]["correct"] is False)
    check("item 15 scored incorrect (deliberately flipped)", by_id[15]["correct"] is False)
    check("item 1 scored correct", by_id[1]["correct"] is True)
    check("18 of 20 correct overall", sum(1 for r in rows if r["correct"]) == 18)


def test_excerpts_block_is_in_corpus_order_and_labeled():
    items = build_synthetic_items()
    block = cc.excerpts_block(items)
    check("every item's excerpt text appears", all(it["excerpt"] in block for it in items))
    check("every item is labeled with its doc_title", all(f"from {it['doc_title']}" in block for it in items))
    # corpus order = ascending excerpt_depth_tokens; doc 1's item (id=1) has the
    # smallest depth in this synthetic set and must appear before doc 13's.
    check("doc 1's excerpt appears before doc 13's (corpus order)", block.index(items[0]["excerpt"]) < block.index(items[12]["excerpt"]))


def test_results_md_end_to_end_no_pi_calls():
    """Build fake run-full.json / run-excerpts.json (the exact shape
    run_one_mode() would produce) directly -- no run_pi, no pi calls -- then
    exercise load_all_runs() and write_results_md() as comprehension_check.py
    itself would after two real runs."""
    import tempfile

    with tempfile.TemporaryDirectory() as tmp:
        out_dir = Path(tmp)
        (out_dir / "raw").mkdir(parents=True, exist_ok=True)
        items = build_synthetic_items()

        full_text = fake_answer_text(items, wrong_ids_mode={5, 15})
        excerpts_text = fake_answer_text(items, wrong_ids_mode={15})  # item 5 "fixed" by excerpts-only

        for mode, text, wrong_ids in (("full", full_text, {5, 15}), ("excerpts", excerpts_text, {15})):
            parsed = parse_labeled_lines(text, n=20)
            rows = cc.score_items(items, parsed)
            record = {
                "mode": mode, "model": "openai-codex/gpt-5.6-luna", "n_items": 20, "ok": True, "error": None,
                "quota_error": False,
                "usage": {"input": 12345 if mode == "full" else 2345, "output": 300, "cacheRead": 0, "cacheWrite": 0},
                "cost_usd": 0.01, "wall_time_s": 5.0, "answer_text": text, "items": rows,
                "raw_events_path": str(out_dir / "raw" / f"{mode}.raw.jsonl"),
            }
            write_json(str(out_dir / f"run-{mode}.json"), record)

        runs = cc.load_all_runs(out_dir)
        check("both modes loaded from disk", set(runs.keys()) == {"full", "excerpts"})

        table = cc.write_results_md(out_dir / "results.md", items, runs)
        check("results.md was written", (out_dir / "results.md").exists())
        content = (out_dir / "results.md").read_text(encoding="utf-8")

        check("table returned equals table in the file", table in content)
        check("all 20 statements section present", "## All 20 statements" in content)
        for item in items:
            check(f"statement {item['id']} printed in full", item["statement"] in content)

        check(
            "item 5 shows the length-attributable verdict (wrong at full, correct with excerpts)",
            "wrong at full -- correct with excerpts only" in content and "| 5 |" in content,
        )
        # Confirm it's specifically on item 5's row, not a coincidental substring match.
        row5 = [line for line in content.splitlines() if line.startswith("| 5 |")]
        check("exactly one row for item 5", len(row5) == 1)
        check("item 5's row contains the length-attributable verdict", "length-attributable" in row5[0])

        row15 = [line for line in content.splitlines() if line.startswith("| 15 |")]
        check("item 15's row is plain 'wrong' (excerpts did not fix it)", row15 and "| wrong |" in row15[0])

        row1 = [line for line in content.splitlines() if line.startswith("| 1 |")]
        check("item 1's row is 'correct'", row1 and "| correct |" in row1[0])


def main():
    test_parser_handles_two_digit_ids_and_both_not_found_spellings()
    test_score_items_marks_wrong_ids_wrong()
    test_excerpts_block_is_in_corpus_order_and_labeled()
    test_results_md_end_to_end_no_pi_calls()

    print()
    if FAILURES:
        print(f"{len(FAILURES)} check(s) FAILED:")
        for f in FAILURES:
            print(f"  - {f}")
        sys.exit(1)
    print("All checks passed.")


if __name__ == "__main__":
    main()
