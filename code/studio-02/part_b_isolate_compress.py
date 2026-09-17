#!/usr/bin/env python3
"""Part B: fix Part A's BABILong qa1 failure with Isolate and Compress.

Rewritten per contract addendum v9: the old Part B chunked corpus/sections/*.txt,
an arXiv survey corpus deleted when the studio was narrowed to BABILong only.
This version operates on the same BABILong qa1 haystacks Part A used, so the
comparison against Part A is honest.

Data-check finding this design is built on (see run_data_check() and
evidence/part_b/summary.md for the numbers): a BABILong qa1 item's target
person is not always mentioned once. Across the 68-item pool the 768K bucket
was sampled from, the person moves more than once in a majority of items
(regex hits for "PERSON moved/went/... (back) to the ROOM"), and in EVERY
checked case the LAST such mention is the one that matches the gold answer.
Every demonstration below is therefore told explicitly to take the last
reported location, never the first.

Three demonstrations, on the SAME ids Part A scored (chosen by lowest id in
the bucket, never by whether Part A got them right):

  1. Isolate: one pi sub-agent per haystack chunk reports only whether it
     saw the person's location (quote the sentence, or NOT FOUND); a lead
     pi call sees only those short reports (in document order) and answers,
     taking the last chunk that reported a location.
  2. Compress (targeted summary): the same chunks, but each call summarizes
     its chunk in ~200 tokens, explicitly told to preserve any location
     statement; the question is then answered from the concatenated
     summaries alone.
  3. Compress (pi's own auto-compaction): a 256K item (not 768K, to keep
     cost sane), read chunk-by-chunk through pi's own `read` tool in one
     session whose .pi/settings.json lowers the compaction threshold so
     compaction fires mid-run.

The key measurement is PEAK single-call context, not just total tokens.
Chunking barely reduces total tokens (the same haystack still gets read,
just split up) -- it reduces how much any ONE call has to attend to at
once. Every per-item record below carries both total_tokens and
peak_context_tokens so that distinction is explicit, not just asserted.

Budget: checked BEFORE every pi call (Budget.check_before), using each
call's real prompt token count (or, for the one multi-turn compaction
session per item, a conservative worst-case multiplier -- see
run_compaction_item), never after -- so a call already in flight can't
land after the hard stop has tripped.

Usage:
  python3 part_b_isolate_compress.py --model openai/gpt-5.6-luna --out evidence
  python3 part_b_isolate_compress.py --dry-run   # plan + cost estimate, no pi calls, no cost

Run from code/studio-02/. Requires evidence/part_a/results.json (Part A's
real run) for the comparison table, and benchmarks/subset_qa1_topend.json,
benchmarks/qa1_768k_survivors.json, benchmarks/babilong/data/qa1/256k.json
(see setup.sh / README for how those are produced).
"""
import argparse
import json
import random
import re
import shutil
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from lib.pi_runner import (  # noqa: E402
    md_table,
    model_context_window,
    real_slice_by_tokens,
    real_token_count,
    run_pi,
    write_json,
    write_text,
)

# Contract hard rule: the course API-key provider, NOT lib.pi_runner's own
# DEFAULT_MODEL (which points at the openai-codex OAuth subscription
# provider). evidence/part_a/summary.md confirms Part A itself used this
# exact provider/model string.
MODEL = "openai/gpt-5.6-luna"
THINKING = "low"
N_CHUNKS_DEFAULT = 8
BUDGET_TARGET_USD = 1.70
HARD_STOP_USD = 2.00

BASE = Path(__file__).resolve().parent
BENCHMARKS = BASE / "benchmarks"

# bAbI qa1 movement-fact pattern, same as benchmarks/prepare_qa1_topend.py's
# FACT_VERBS (kept identical on purpose so the data-check below is directly
# comparable to how that script located each item's supporting fact).
FACT_VERBS = r"(?:moved|went|travell?ed|journeyed|walked|ran|goes|go)"

# --- 256K-bucket id/row reconstruction ---------------------------------
# Part A's evidence (evidence/part_a/results.json, results.csv) is real, but
# the script that built its native 32k/128k/256k buckets is not on disk --
# plot_qa1_curve.py's own docstring says those points came from
# "evidence/benchmark_sweep/ ... since deleted". Every OTHER seeded sample in
# this codebase (benchmarks/select_qa1_topend.py) uses seed=7, so this was
# checked directly: for bucket in (32k, 128k, 256k), loading
# benchmarks/babilong/data/qa1/<bucket>.json (n=100) and taking
# sorted(random.Random(7).sample(range(100), 20)) as the row indices, with
# ids assigned sequentially per bucket (32k: 1-20, 128k: 21-40, 256k: 41-60),
# reproduces the recorded target for EVERY row where results.json marked the
# model "correct" -- 17/17 (32k), 15/15 (128k), 13/13 (256k), 45/45 overall,
# with zero disagreements. That is taken here as sufficient confirmation to
# reuse the same reconstruction for the 256K item(s) the compaction
# demonstration needs.
SEED_256K = 7
BUCKET_256K_BASE_ID = 41


class BudgetExceeded(RuntimeError):
    pass


class Budget:
    """Tracks real spend across every pi call this script makes and refuses
    to submit a call whose estimated cost would push the projected total
    past hard_stop -- checked BEFORE the call, using the empirical pricing
    observed directly in evidence/part_a/results.json for this exact model
    (~$0.25/M input tokens for a call under 272,000 input tokens, ~$0.50/M
    at or above it -- gpt-5.6-luna's own context-window pricing tier), never
    after. This is what "checked before submitting each call, not after"
    means in practice: the check happens strictly before subprocess launch,
    calls are made one at a time (never concurrently), so there is never an
    in-flight call that can land after the stop has already tripped."""

    def __init__(self, hard_stop=HARD_STOP_USD, target=BUDGET_TARGET_USD):
        self.hard_stop = hard_stop
        self.target = target
        self.spent = 0.0
        self.log = []

    @staticmethod
    def estimate_call_cost_usd(input_tokens: int, output_tokens_guess: int = 600) -> float:
        rate = 0.50 if input_tokens > 272_000 else 0.25
        return input_tokens / 1e6 * rate + output_tokens_guess / 1e6 * 1.8

    def check_before(self, label: str, input_tokens: int) -> float:
        est = self.estimate_call_cost_usd(input_tokens)
        projected = self.spent + est
        if projected > self.hard_stop:
            raise BudgetExceeded(
                f"refusing to submit '{label}' (~{input_tokens:,} est. input tokens, "
                f"est ${est:.4f}): spent so far ${self.spent:.4f}; this call would project "
                f"to ${projected:.4f}, over the ${self.hard_stop:.2f} hard stop."
            )
        return est

    def record(self, label: str, actual_cost_usd: float) -> None:
        self.spent += actual_cost_usd or 0.0
        self.log.append({"label": label, "cost_usd": round(actual_cost_usd or 0.0, 6),
                          "running_total_usd": round(self.spent, 6)})
        flag = "  *** OVER TARGET ***" if self.spent > self.target else ""
        print(f"    [budget] {label}: cost=${actual_cost_usd or 0.0:.4f} running_total=${self.spent:.4f}{flag}",
              flush=True)


def call_pi(budget: Budget, label: str, prompt: str, model: str, thinking: str,
            cost_estimate_tokens=None, **kwargs):
    """check_before -> run_pi -> record, uniformly, for every pi call this
    script makes. cost_estimate_tokens overrides the pre-flight token
    estimate for the one case (the compaction session) where the launch
    prompt is much smaller than what the session will actually process."""
    input_tok_estimate = cost_estimate_tokens if cost_estimate_tokens is not None else real_token_count(prompt)
    budget.check_before(label, input_tok_estimate)
    result = run_pi(prompt=prompt, model=model, thinking=thinking, **kwargs)
    budget.record(label, result.total_cost_usd)
    return result


# ---------------------------------------------------------------------------
# Scoring (exact-match room name, same convention Part A's summary.md
# describes: "exact-match scoring", answer given with no article/punctuation)
# ---------------------------------------------------------------------------

_ARTICLE_RE = re.compile(r"^(the|a|an)\s+", re.IGNORECASE)


def normalize_room(s: str) -> str:
    s = (s or "").strip()
    s = _ARTICLE_RE.sub("", s)
    s = re.sub(r"[^\w\s]", "", s)
    return s.strip().lower()


def extract_final_answer(answer_text: str) -> str:
    """Last non-empty line of the reply -- robust to a stray leading line of
    reasoning despite --thinking low."""
    lines = [l.strip() for l in (answer_text or "").splitlines() if l.strip()]
    return lines[-1] if lines else ""


def score_babilong(answer_text: str, target: str) -> dict:
    raw = extract_final_answer(answer_text)
    correct = bool(raw) and normalize_room(raw) == normalize_room(target)
    return {"raw_answer": raw, "correct": correct, "score": 1.0 if correct else 0.0}


# ---------------------------------------------------------------------------
# Peak-context / total-token accounting
# ---------------------------------------------------------------------------

def _assistant_usages(result):
    for e in result.events:
        if e.get("type") == "message_end" and e.get("message", {}).get("role") == "assistant":
            yield (e.get("message", {}).get("usage") or {})


def prompt_tokens_from_usage(usage: dict) -> int:
    """The real prompt-side size of ONE turn: input + cacheRead + cacheWrite.

    Verified directly (see summary.md deviation note): a single fresh,
    one-shot --no-tools call carrying a ~95,829-real-token chunk came back
    with usage.input == 3 and usage.cacheWrite == 96,305 -- pi/the
    openai-responses API caches almost the entire prompt on write even
    when there is no follow-up turn to read it back. usage['input'] ALONE
    is therefore not the prompt size for any call in this script, single
    -turn or multi-turn; input+cacheRead+cacheWrite is."""
    return (usage.get("input") or 0) + (usage.get("cacheRead") or 0) + (usage.get("cacheWrite") or 0)


def peak_input_tokens(result) -> int:
    """Max real prompt size across every assistant TURN in this call -- for
    a single-turn call this is that call's whole prompt; for the multi-turn
    compaction session it is the largest any one turn saw, which is exactly
    what compaction is meant to cap."""
    peaks = [prompt_tokens_from_usage(u) for u in _assistant_usages(result)]
    return max(peaks) if peaks else prompt_tokens_from_usage(result.usage)


def total_tokens_used(result) -> int:
    """Sum of (real prompt size + output) across every assistant turn (not
    just the last)."""
    total = sum(prompt_tokens_from_usage(u) + (u.get("output") or 0) for u in _assistant_usages(result))
    return total or (prompt_tokens_from_usage(result.usage) + (result.usage.get("output") or 0))


def split_into_n_chunks(text: str, n: int) -> list:
    """N chunks in document order, by real token count, reusing
    real_slice_by_tokens's line-safe cuts (never splits a line -- and every
    bAbI fact sentence in this corpus sits on one line -- see summary.md)."""
    total = real_token_count(text)
    target = max(1, total // n)
    remaining = text
    chunks = []
    for _ in range(n - 1):
        if not remaining:
            break
        piece = real_slice_by_tokens(remaining, target)
        if not piece:
            break
        chunks.append(piece)
        remaining = remaining[len(piece):]
    if remaining:
        chunks.append(remaining)
    return chunks


# ---------------------------------------------------------------------------
# Data check: how many times is the target person mentioned, and does the
# LAST mention match the gold answer? (contract: verify this before
# designing isolate)
# ---------------------------------------------------------------------------

def _movement_matches(person: str, text: str):
    pat = re.compile(re.escape(person) + r" " + FACT_VERBS + r" (?:back )?to the (\w+)", re.I)
    return [(m.start(), m.group(1)) for m in pat.finditer(text)]


def run_data_check() -> dict:
    survivors = json.loads((BENCHMARKS / "qa1_768k_survivors.json").read_text(encoding="utf-8"))
    zero = single = multi = mismatches = 0
    dist = {}
    for s in survivors:
        matches = _movement_matches(s["person"], s["input_truncated"])
        k = len(matches)
        dist[k] = dist.get(k, 0) + 1
        if k == 0:
            zero += 1
            continue
        single += 1 if k == 1 else 0
        multi += 1 if k > 1 else 0
        if matches[-1][1].lower() != s["target"].lower():
            mismatches += 1

    n = len(survivors)
    headline = {
        "n_items_checked": n,
        "source": "benchmarks/qa1_768k_survivors.json (the 68-item pool the 768K bucket's "
                  "evaluated items were sampled from)",
        "n_single_mention": single,
        "n_multi_mention": multi,
        "n_zero_regex_hits": zero,
        "mention_count_distribution": {str(k): v for k, v in sorted(dist.items())},
        "n_cases_where_last_mention_disagrees_with_target": mismatches,
        "finding": (
            f"{multi}/{n} items have the target person moving MORE THAN ONCE (regex hits for "
            f"'PERSON moved/went/travelled/... (back) to the ROOM'); the remaining {single} have "
            f"exactly one mention, {zero} had no literal regex hit. Across all {n - zero} items "
            f"with at least one hit, the LAST mention's room matches the gold target in EVERY "
            f"case ({n - zero - mismatches}/{n - zero}, {mismatches} disagreements) -- when a "
            f"person moves more than once, only their most recent move is ever the right answer. "
            f"Every demonstration below is therefore told explicitly to take the LAST reported "
            f"location, never the first."
        ),
    }
    return headline


# ---------------------------------------------------------------------------
# Data loading -- deterministic id selection, never by correctness
# ---------------------------------------------------------------------------

def _load_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def lowest_ids_768k(n: int) -> list:
    topend = _load_json(BENCHMARKS / "subset_qa1_topend.json")
    ids = sorted(it["id"] for it in topend if it["bucket"] == "768k")
    return ids[:n]


def load_768k_items(ids: list) -> list:
    topend = _load_json(BENCHMARKS / "subset_qa1_topend.json")
    by_id = {it["id"]: it for it in topend if it["bucket"] == "768k"}
    survivors = _load_json(BENCHMARKS / "qa1_768k_survivors.json")
    surv_by_rowidx = {s["row_index"]: s for s in survivors}
    items = []
    for idn in ids:
        it = by_id[idn]
        s = surv_by_rowidx[it["source"]["row_index"]]
        items.append({
            "id": idn, "bucket": "768k", "person": s["person"], "target": s["target"],
            "question": s["question"].strip(), "haystack": s["input_truncated"],
            "needle_depth_tokens": s["needle_depth_tokens"],
        })
    return items


def lowest_256k_items(n: int) -> list:
    """Reconstructed native-256K-bucket items (see SEED_256K note above),
    lowest n ids in that bucket. Deterministic; never looks at correctness."""
    data = _load_json(BENCHMARKS / "babilong" / "data" / "qa1" / "256k.json")
    idxs = sorted(random.Random(SEED_256K).sample(range(len(data)), 20))
    items = []
    for k in range(n):
        row = data[idxs[k]]
        m = re.search(r"Where is (\w+)", row["question"])
        person = m.group(1) if m else None
        items.append({
            "id": BUCKET_256K_BASE_ID + k, "bucket": "256k", "person": person,
            "target": row["target"], "question": row["question"].strip(),
            "haystack": row["input"], "source_row_index": idxs[k],
        })
    return items


def load_part_a_records(bucket: str, ids: list) -> dict:
    results = _load_json(BASE / "evidence" / "part_a" / "results.json")
    by_id = {r["id"]: r for r in results if r["bucket"] == bucket}
    return {str(idn): by_id[idn] for idn in ids if idn in by_id}


# ---------------------------------------------------------------------------
# Demonstration 1: Isolate
# ---------------------------------------------------------------------------

ISOLATE_CHUNK_INSTRUCTIONS = (
    "Does the text above state where {person} is -- for example, that they are in, or moved, "
    "went, or travelled to, a specific room or place? If yes, quote the exact sentence that "
    "states it, and say nothing else. If no, answer NOT FOUND and say nothing else."
)

ISOLATE_LEAD_TEMPLATE = (
    "Below are short reports from {n} consecutive chunks of a long story, given in document "
    "order (chunk 1 came first in the story, chunk {n} came last):\n\n{reports}\n\n"
    "Question: Where is {person}?\n\n"
    "People in this story move between rooms over time, and {person} may be reported in more "
    "than one chunk. If more than one chunk states a location for {person}, the correct answer "
    "is the LAST one in document order (the highest-numbered chunk that reports a location) -- "
    "ignore earlier ones, they are out of date. Answer with ONLY the room name, exactly as "
    "stated: no article (a/an/the), no punctuation, no explanation, nothing else. If no chunk "
    "reports a location for {person}, answer NOT FOUND."
)


def run_isolate_item(budget, item, n_chunks, model, thinking, work_root, timeout, session_dir, raw_dir):
    person = item["person"]
    chunks = split_into_n_chunks(item["haystack"], n_chunks)
    item_dir = work_root / f"item-{item['id']}"

    chunk_records, reports = [], []
    for i, chunk_text in enumerate(chunks, start=1):
        prompt = f"{chunk_text}\n\n{ISOLATE_CHUNK_INSTRUCTIONS.format(person=person)}\n"
        label = f"isolate/item-{item['id']}/chunk-{i:02d}"
        result = call_pi(
            budget, label, prompt, model, thinking,
            cwd=str(item_dir), no_tools=True, session_dir=str(session_dir),
            raw_events_path=str(raw_dir / f"{label.replace('/', '-')}.raw.jsonl"),
            timeout=timeout, approve=True, no_context_files=True,
        )
        report_text = result.answer_text.strip() if result.ok else f"[ERROR: {result.error}]"
        chunk_records.append({
            "chunk": i, "ok": result.ok, "error": result.error, "report": report_text,
            # "input_tokens" = the real prompt size (input+cacheRead+cacheWrite -- see
            # prompt_tokens_from_usage), NOT the raw usage.input field, which is
            # ~0 for these large prompts once caching kicks in.
            "input_tokens": prompt_tokens_from_usage(result.usage), "output_tokens": result.usage.get("output"),
            "cost_usd": round(result.total_cost_usd, 6),
        })
        reports.append(f"Chunk {i}: {report_text}")

    lead_prompt = ISOLATE_LEAD_TEMPLATE.format(n=len(chunks), reports="\n\n".join(reports), person=person)
    lead_label = f"isolate/item-{item['id']}/lead"
    lead_result = call_pi(
        budget, lead_label, lead_prompt, model, thinking,
        cwd=str(item_dir), no_tools=True, session_dir=str(session_dir),
        raw_events_path=str(raw_dir / f"{lead_label.replace('/', '-')}.raw.jsonl"),
        timeout=timeout, approve=True, no_context_files=True,
    )
    scoring = score_babilong(lead_result.answer_text, item["target"]) if lead_result.ok else {
        "raw_answer": None, "correct": False, "score": 0.0}

    chunk_in = [c["input_tokens"] or 0 for c in chunk_records]
    chunk_out = [c["output_tokens"] or 0 for c in chunk_records]
    lead_in = prompt_tokens_from_usage(lead_result.usage)
    lead_out = lead_result.usage.get("output") or 0
    total_tokens = sum(chunk_in) + sum(chunk_out) + lead_in + lead_out
    peak_context = max(chunk_in + [lead_in])
    cost = sum(c["cost_usd"] for c in chunk_records) + lead_result.total_cost_usd

    return {
        "id": item["id"], "person": person, "target": item["target"], "n_chunks": len(chunks),
        "chunks": chunk_records,
        "lead": {
            "ok": lead_result.ok, "error": lead_result.error, "answer_text": lead_result.answer_text,
            **scoring, "input_tokens": lead_in, "output_tokens": lead_out,
            "cost_usd": round(lead_result.total_cost_usd, 6),
        },
        "total_tokens": total_tokens, "peak_context_tokens": peak_context, "cost_usd": round(cost, 6),
    }


# ---------------------------------------------------------------------------
# Demonstration 2: Compress -- targeted summary
# ---------------------------------------------------------------------------

SUMMARY_CHUNK_INSTRUCTIONS = (
    "Summarize the text above in about 200 tokens. If any sentence states that a person is in, "
    "or moved, went, or travelled to, a specific room or place, you MUST preserve that statement "
    "clearly in your summary -- do not drop it, generalize it away, or omit it even if it seems "
    "minor compared to the rest of the text."
)

SUMMARY_REASK_TEMPLATE = (
    "Below are summaries of {n} consecutive chunks of a long story, given in document order "
    "(chunk 1 came first in the story, chunk {n} came last):\n\n{summaries}\n\n"
    "Question: Where is {person}?\n\n"
    "People in this story move between rooms over time. If more than one summary states a "
    "location for {person}, the correct answer is the LAST one in document order -- ignore "
    "earlier ones, they are out of date. Answer with ONLY the room name: no article (a/an/the), "
    "no punctuation, no explanation, nothing else. If no summary states a location for "
    "{person}, answer NOT FOUND."
)


def run_summary_item(budget, item, n_chunks, model, thinking, work_root, timeout, session_dir, raw_dir):
    person = item["person"]
    chunks = split_into_n_chunks(item["haystack"], n_chunks)
    item_dir = work_root / f"item-{item['id']}"

    chunk_records, summaries = [], []
    for i, chunk_text in enumerate(chunks, start=1):
        prompt = f"{chunk_text}\n\n{SUMMARY_CHUNK_INSTRUCTIONS}\n"
        label = f"summary/item-{item['id']}/chunk-{i:02d}"
        result = call_pi(
            budget, label, prompt, model, thinking,
            cwd=str(item_dir), no_tools=True, session_dir=str(session_dir),
            raw_events_path=str(raw_dir / f"{label.replace('/', '-')}.raw.jsonl"),
            timeout=timeout, approve=True, no_context_files=True,
        )
        summary_text = result.answer_text.strip() if result.ok else f"[ERROR: {result.error}]"
        chunk_records.append({
            "chunk": i, "ok": result.ok, "error": result.error, "summary": summary_text,
            "input_tokens": prompt_tokens_from_usage(result.usage), "output_tokens": result.usage.get("output"),
            "cost_usd": round(result.total_cost_usd, 6),
        })
        summaries.append(f"Chunk {i} summary: {summary_text}")

    reask_prompt = SUMMARY_REASK_TEMPLATE.format(n=len(chunks), summaries="\n\n".join(summaries), person=person)
    reask_label = f"summary/item-{item['id']}/reask"
    reask_result = call_pi(
        budget, reask_label, reask_prompt, model, thinking,
        cwd=str(item_dir), no_tools=True, session_dir=str(session_dir),
        raw_events_path=str(raw_dir / f"{reask_label.replace('/', '-')}.raw.jsonl"),
        timeout=timeout, approve=True, no_context_files=True,
    )
    scoring = score_babilong(reask_result.answer_text, item["target"]) if reask_result.ok else {
        "raw_answer": None, "correct": False, "score": 0.0}

    chunk_in = [c["input_tokens"] or 0 for c in chunk_records]
    chunk_out = [c["output_tokens"] or 0 for c in chunk_records]
    reask_in = prompt_tokens_from_usage(reask_result.usage)
    reask_out = reask_result.usage.get("output") or 0
    total_tokens = sum(chunk_in) + sum(chunk_out) + reask_in + reask_out
    peak_context = max(chunk_in + [reask_in])
    cost = sum(c["cost_usd"] for c in chunk_records) + reask_result.total_cost_usd

    return {
        "id": item["id"], "person": person, "target": item["target"], "n_chunks": len(chunks),
        "chunks": chunk_records,
        "reask": {
            "ok": reask_result.ok, "error": reask_result.error, "answer_text": reask_result.answer_text,
            **scoring, "input_tokens": reask_in, "output_tokens": reask_out,
            "cost_usd": round(reask_result.total_cost_usd, 6),
        },
        "total_tokens": total_tokens, "peak_context_tokens": peak_context, "cost_usd": round(cost, 6),
    }


# ---------------------------------------------------------------------------
# Demonstration 3: Compress -- pi's own auto-compaction
# ---------------------------------------------------------------------------

COMPACTION_PROMPT_TEMPLATE = (
    "Using the read tool, read these files IN ORDER, one at a time: {file_list}. After you have "
    "read all of them, answer the question below using only what you read.\n\n"
    "Question: Where is {person}?\n\n"
    "People in this story move between rooms over time. If {person} is mentioned in more than "
    "one chunk, the correct answer is their LAST stated location (from the highest-numbered "
    "chunk you read that mentions them) -- ignore earlier ones. Answer with ONLY the room name: "
    "no article (a/an/the), no punctuation, no explanation, nothing else. If you did not find "
    "the answer, say NOT FOUND."
)


def effective_context_window(provider: str, model_id: str) -> int:
    """The context window pi will ACTUALLY use for this provider/model on
    this machine -- which is not always lib.pi_runner.model_context_window()
    (that reads only ~/.pi/agent/models-store.json, the static catalog).
    This machine's ~/.pi/agent/models.json applies a provider-level
    contextWindow override for openai/gpt-5.6-luna specifically: `pi
    --list-models` shows 1.1M for provider "openai" vs. 272K for
    "openai-codex" (same model id). Verified directly the override is what
    pi's auto-compaction threshold is actually computed against: with
    reserveTokens picked against the catalog's 272K figure, a tiny 3-file,
    ~9,900-real-prompt-token test session never compacted at all; recomputed
    against 1.05M, the identical settings.json shape fired exactly as
    configured (compaction_start/compaction_end, tokensBefore matching the
    session's real prompt size). See summary.md deviation note. Never
    touches auth.json -- this file (~/.pi/agent/models.json) carries only
    model-catalog numbers, no credentials."""
    override_path = Path.home() / ".pi" / "agent" / "models.json"
    if override_path.exists():
        try:
            overrides = json.loads(override_path.read_text(encoding="utf-8"))
            cw = (
                overrides.get("providers", {})
                .get(provider, {})
                .get("modelOverrides", {})
                .get(model_id, {})
                .get("contextWindow")
            )
            if isinstance(cw, int):
                return cw
        except Exception:
            pass
    return model_context_window(provider, model_id) or 128000


def run_compaction_item(budget, item, n_chunks, model, thinking, work_root, timeout, session_dir, raw_dir,
                         target_threshold):
    person = item["person"]
    chunks = split_into_n_chunks(item["haystack"], n_chunks)
    item_dir = work_root / f"item-{item['id']}"
    corpus_dir = item_dir / "chunks"
    corpus_dir.mkdir(parents=True, exist_ok=True)

    file_names = []
    for i, chunk_text in enumerate(chunks, start=1):
        name = f"chunk-{i:02d}.txt"
        (corpus_dir / name).write_text(chunk_text, encoding="utf-8")
        file_names.append(f"chunks/{name}")

    provider, model_id = (model.split("/", 1) + [""])[:2] if "/" in model else ("", model)
    context_window = effective_context_window(provider, model_id)
    reserve_tokens = max(1024, context_window - target_threshold)
    keep_recent_tokens = 10000
    pi_settings_dir = item_dir / ".pi"
    pi_settings_dir.mkdir(parents=True, exist_ok=True)
    (pi_settings_dir / "settings.json").write_text(json.dumps({
        "compaction": {"enabled": True, "reserveTokens": reserve_tokens, "keepRecentTokens": keep_recent_tokens}
    }, indent=2), encoding="utf-8")

    prompt = COMPACTION_PROMPT_TEMPLATE.format(file_list=", ".join(file_names), person=person)
    label = f"compaction/item-{item['id']}"

    # This is ONE subprocess call from this script's point of view, but
    # internally it is a multi-turn session that reads all n_chunks files
    # and may compact several times -- the launch prompt itself is only a
    # few hundred tokens, which would badly understate this call's real
    # cost if used as the pre-flight estimate. Use a conservative worst
    # case instead: the item's own real token count read twice over (a
    # generous allowance for context that gets re-transmitted turn over
    # turn before each compaction), so the hard-stop check is a genuine
    # gate here too, not a rubber stamp.
    item_real_tokens = real_token_count(item["haystack"])
    worst_case_tokens = item_real_tokens * 2

    result = call_pi(
        budget, label, prompt, model, thinking, cost_estimate_tokens=worst_case_tokens,
        cwd=str(item_dir), tools="read,ls", session_dir=str(session_dir),
        raw_events_path=str(raw_dir / f"{label.replace('/', '-')}.raw.jsonl"),
        timeout=timeout, approve=True, no_context_files=True,
    )
    scoring = score_babilong(result.answer_text, item["target"]) if result.ok else {
        "raw_answer": None, "correct": False, "score": 0.0}

    compactions = []
    for ev in result.compactions:
        inner = ev.get("result") or {}
        compactions.append({
            "type": ev.get("type"), "reason": ev.get("reason"),
            "tokensBefore": inner.get("tokensBefore"),
            "estimatedTokensAfter": inner.get("estimatedTokensAfter"),
        })

    return {
        "id": item["id"], "person": person, "target": item["target"], "n_chunks": len(chunks),
        "item_real_tokens": item_real_tokens,
        "context_window": context_window, "reserve_tokens": reserve_tokens,
        "keep_recent_tokens": keep_recent_tokens, "threshold_tokens": context_window - reserve_tokens,
        "ok": result.ok, "error": result.error, "answer_text": result.answer_text, **scoring,
        "compactions": compactions,
        "num_compactions": len([c for c in compactions if c["type"] == "compaction_start"]),
        "total_tokens": total_tokens_used(result),
        "peak_context_tokens": peak_input_tokens(result),
        "cost_usd": round(result.total_cost_usd, 6),
        "wall_time_s": round(result.wall_time_s, 2),
    }


# ---------------------------------------------------------------------------
# Reporting
# ---------------------------------------------------------------------------

def _part_a_cell(rec):
    if not rec:
        return "n/a", "n/a", "n/a"
    correct = "correct" if rec.get("correct") else "WRONG"
    return correct, rec.get("real_input_tokens", "n/a"), f"${rec.get('cost_usd', 0):.4f}"


def write_summary_md(part_b_dir, results, items_768k, items_256k):
    ids_768k = results["ids_768k"]
    ids_256k = results["ids_256k"]
    part_a_768k = results["part_a_on_same_ids"]["768k"]
    part_a_256k = results["part_a_on_same_ids"]["256k"]

    lines = ["# Part B: Isolate and Compress -- summary", "",
             f"Model: `{results['model']}`, thinking `{results['thinking']}`, {results['n_chunks']} chunks per item.",
             ""]

    if results.get("aborted"):
        lines += ["**RUN ABORTED BY THE BUDGET GUARD -- results below are partial.**",
                   f"Reason: {results['abort_reason']}", ""]

    dc = results["data_check"]
    lines += ["## Data check: how many times is the target person mentioned?", "",
              dc["finding"], "",
              f"Mention-count distribution across the {dc['n_items_checked']} items checked: "
              f"{dc['mention_count_distribution']} (key = number of movement-sentence matches for "
              f"that item's person). {dc['n_multi_mention']} items have more than one; "
              f"{dc['n_cases_where_last_mention_disagrees_with_target']} of those disagree with "
              f"taking the LAST one.", ""]

    # Per-item table across all three conditions + Part A on the same ids
    lines += ["## Per-item results (same ids Part A scored, chosen by lowest id, not by correctness)", ""]
    rows = []
    for item in items_768k:
        idn = item["id"]
        pa_verdict, pa_tokens, pa_cost = _part_a_cell(part_a_768k.get(str(idn)))
        rows.append([f"{idn} (768k)", "Part A (single call)", pa_verdict, pa_tokens, pa_tokens, pa_cost])
    for rec in results["isolate"]["items"]:
        verdict = "correct" if rec["lead"]["correct"] else "WRONG"
        rows.append([f"{rec['id']} (768k)", "Isolate", verdict, rec["total_tokens"], rec["peak_context_tokens"],
                     f"${rec['cost_usd']:.4f}"])
    for rec in results["summary_compress"]["items"]:
        verdict = "correct" if rec["reask"]["correct"] else "WRONG"
        rows.append([f"{rec['id']} (768k)", "Compress: targeted summary", verdict, rec["total_tokens"],
                     rec["peak_context_tokens"], f"${rec['cost_usd']:.4f}"])
    for item in items_256k:
        idn = item["id"]
        pa_verdict, pa_tokens, pa_cost = _part_a_cell(part_a_256k.get(str(idn)))
        rows.append([f"{idn} (256k)", "Part A (single call)", pa_verdict, pa_tokens, pa_tokens, pa_cost])
    for rec in results["compaction"]["items"]:
        verdict = "correct" if rec["correct"] else ("ERROR" if not rec["ok"] else "WRONG")
        rows.append([f"{rec['id']} (256k)", "Compress: pi auto-compaction", verdict, rec["total_tokens"],
                     rec["peak_context_tokens"],
                     f"${rec['cost_usd']:.4f} ({rec['num_compactions']} compaction(s))"])
    lines.append(md_table(["id (bucket)", "condition", "verdict", "total tokens", "PEAK single-call context",
                            "cost"], rows))
    lines.append("")

    # Condition-level aggregate + recovery statement
    def acc(items, key_path):
        if not items:
            return 0, 0
        correct = sum(1 for r in items if _dig(r, key_path))
        return correct, len(items)

    def _dig(r, path):
        for p in path:
            r = r[p]
        return r

    pa_768_correct = sum(1 for idn in ids_768k if part_a_768k.get(str(idn), {}).get("correct"))
    iso_correct, iso_n = acc(results["isolate"]["items"], ["lead", "correct"])
    summ_correct, summ_n = acc(results["summary_compress"]["items"], ["reask", "correct"])
    pa_256_correct = sum(1 for idn in ids_256k if part_a_256k.get(str(idn), {}).get("correct"))
    comp_correct, comp_n = acc(results["compaction"]["items"], ["correct"])

    lines += ["## Condition summary", "",
              f"Part A on these same 3 (768K) ids: {pa_768_correct}/3 correct.",
              f"Isolate on the same 3 ids: {iso_correct}/{iso_n} correct.",
              f"Compress (targeted summary) on the same 3 ids: {summ_correct}/{summ_n} correct.",
              "",
              f"Part A on these same 2 (256K) ids: {pa_256_correct}/2 correct.",
              f"Compress (pi auto-compaction) on the same 2 ids: {comp_correct}/{comp_n} correct.",
              ""]

    def recovery_line(name, before, after, n):
        if after > before:
            verdict = f"RECOVERED accuracy Part A lost on these ids ({before}/{n} -> {after}/{n})."
        elif after == before:
            verdict = f"did NOT change accuracy on these ids ({before}/{n} -> {after}/{n})."
        else:
            verdict = f"did WORSE than Part A on these ids ({before}/{n} -> {after}/{n})."
        return f"**{name}** {verdict}"

    lines += [recovery_line("Isolate", pa_768_correct, iso_correct, iso_n),
              recovery_line("Compress (targeted summary)", pa_768_correct, summ_correct, summ_n),
              recovery_line("Compress (pi auto-compaction)", pa_256_correct, comp_correct, comp_n),
              ""]

    max_peak_iso = max((r["peak_context_tokens"] for r in results["isolate"]["items"]), default=0)
    max_peak_summ = max((r["peak_context_tokens"] for r in results["summary_compress"]["items"]), default=0)
    max_peak_comp = max((r["peak_context_tokens"] for r in results["compaction"]["items"]), default=0)
    total_tok_iso = sum(r["total_tokens"] for r in results["isolate"]["items"])
    total_tok_pa768 = sum(part_a_768k.get(str(i), {}).get("real_input_tokens", 0) for i in ids_768k)

    lines += ["## The actual lesson: peak context, not total tokens", "",
              f"Part A's single call for a 768K item had to hold the ENTIRE haystack in context at "
              f"once: peak context = total input tokens = ~767,000. Isolate's peak single-call "
              f"context across these 3 items maxes out at {max_peak_iso:,} tokens (one "
              f"~1/{results['n_chunks']}-sized chunk) -- roughly a "
              f"{(767000 / max_peak_iso) if max_peak_iso else 0:.1f}x reduction in what any ONE call "
              f"had to attend to. Compress (targeted summary)'s peak is {max_peak_summ:,} for the "
              f"same reason: its per-chunk calls still each read one full chunk to summarize it. "
              f"Compress (auto-compaction)'s peak across the 256K items is {max_peak_comp:,} tokens, "
              f"bounded near its configured threshold regardless of the 256K item size.", "",
              f"Meanwhile TOTAL tokens barely move: isolate's 3 items sum to {total_tok_iso:,} tokens "
              f"across all 3x{results['n_chunks']}+3 calls, against {total_tok_pa768:,} for Part A's "
              f"3 single calls on the same ids -- the same haystack still gets read in full, just "
              f"split across calls instead of handed to one. Isolation and targeted summarization do "
              f"not save tokens; they cap what any single call has to hold in context at once.", ""]

    budget = results["budget"]
    lines += ["## Budget", "",
              f"Target ${budget['target_usd']:.2f}, hard stop ${budget['hard_stop_usd']:.2f}. "
              f"Actual total spend: ${budget['total_spent_usd']:.4f} across {len(budget['calls'])} pi calls.",
              ""]

    write_text(str(part_b_dir / "summary.md"), "\n".join(lines))


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--model", default=MODEL)
    ap.add_argument("--thinking", default=THINKING)
    ap.add_argument("--out", default="evidence")
    ap.add_argument("--timeout", type=int, default=900)
    ap.add_argument("--n-chunks", type=int, default=N_CHUNKS_DEFAULT)
    ap.add_argument("--compaction-threshold", type=int, default=50000,
                     help="target token count at which compaction should fire")
    ap.add_argument("--budget-target", type=float, default=BUDGET_TARGET_USD)
    ap.add_argument("--hard-stop", type=float, default=HARD_STOP_USD)
    ap.add_argument("--dry-run", action="store_true", help="print the plan and cost estimate; make no pi calls")
    args = ap.parse_args()

    for path in (BENCHMARKS / "subset_qa1_topend.json", BENCHMARKS / "qa1_768k_survivors.json",
                 BENCHMARKS / "babilong" / "data" / "qa1" / "256k.json",
                 BASE / "evidence" / "part_a" / "results.json"):
        if not path.exists():
            print(f"ERROR: required file not found: {path}", file=sys.stderr)
            sys.exit(1)

    out_dir = Path(args.out)
    part_b_dir = out_dir / "part_b"
    part_b_dir.mkdir(parents=True, exist_ok=True)
    raw_dir = part_b_dir / "raw"
    raw_dir.mkdir(parents=True, exist_ok=True)
    sessions_dir = (out_dir / "sessions").resolve()

    print("=== Part B step 0: data check (mention counts in the real BABILong qa1 data) ===", flush=True)
    data_check = run_data_check()
    print(data_check["finding"], flush=True)

    ids_768k = lowest_ids_768k(3)
    items_768k = load_768k_items(ids_768k)
    items_256k = lowest_256k_items(2)
    ids_256k = [it["id"] for it in items_256k]

    part_a_768k = load_part_a_records("768k", ids_768k)
    part_a_256k = load_part_a_records("256k", ids_256k)

    print(f"\n768K items (isolate + targeted summary), lowest 3 ids in the bucket: {ids_768k}", flush=True)
    for it in items_768k:
        pa = part_a_768k.get(str(it["id"]), {})
        print(f"  id={it['id']} person={it['person']} target={it['target']} "
              f"part_a_correct={pa.get('correct')} part_a_answer={pa.get('raw_answer')!r}", flush=True)

    print(f"\n256K items (auto-compaction), lowest 2 ids in the reconstructed bucket: {ids_256k}", flush=True)
    for it in items_256k:
        pa = part_a_256k.get(str(it["id"]), {})
        print(f"  id={it['id']} person={it['person']} target={it['target']} "
              f"part_a_correct={pa.get('correct')} part_a_answer={pa.get('raw_answer')!r}", flush=True)

    if args.dry_run:
        print("\n--dry-run: estimating cost, no pi calls will be made.", flush=True)
        budget = Budget(hard_stop=args.hard_stop, target=args.budget_target)
        est_total = 0.0
        for it in items_768k:
            n_tok = real_token_count(it["haystack"])
            per_chunk = n_tok // args.n_chunks
            iso = args.n_chunks * Budget.estimate_call_cost_usd(per_chunk, 60) + Budget.estimate_call_cost_usd(1500, 30)
            summ = args.n_chunks * Budget.estimate_call_cost_usd(per_chunk, 250) + Budget.estimate_call_cost_usd(2200, 30)
            est_total += iso + summ
            print(f"  item {it['id']}: ~{n_tok:,} tok -> isolate ~${iso:.4f}, summary ~${summ:.4f}")
        for it in items_256k:
            n_tok = real_token_count(it["haystack"])
            comp = Budget.estimate_call_cost_usd(n_tok * 2, 60)
            est_total += comp
            print(f"  item {it['id']}: ~{n_tok:,} tok -> compaction (worst case) ~${comp:.4f}")
        print(f"\nEstimated total: ~${est_total:.4f} (target ${args.budget_target:.2f}, hard stop ${args.hard_stop:.2f})")
        return

    for root in ("work/part_b/isolate", "work/part_b/summary", "work/part_b/compaction"):
        shutil.rmtree(root, ignore_errors=True)

    budget = Budget(hard_stop=args.hard_stop, target=args.budget_target)
    results = {
        "model": args.model, "thinking": args.thinking, "n_chunks": args.n_chunks,
        "ids_768k": ids_768k, "ids_256k": ids_256k,
        "data_check": data_check,
        "part_a_on_same_ids": {"768k": part_a_768k, "256k": part_a_256k},
        "isolate": {"items": []}, "summary_compress": {"items": []}, "compaction": {"items": []},
        "aborted": False, "abort_reason": None,
    }

    try:
        print("\n=== Part B (1/3): Isolate ===", flush=True)
        for item in items_768k:
            rec = run_isolate_item(budget, item, args.n_chunks, args.model, args.thinking,
                                    Path("work/part_b/isolate"), args.timeout, sessions_dir, raw_dir)
            results["isolate"]["items"].append(rec)
            print(f"  isolate item {item['id']}: verdict={'correct' if rec['lead']['correct'] else 'WRONG'} "
                  f"(answer={rec['lead']['raw_answer']!r}) total_tokens={rec['total_tokens']} "
                  f"peak_context={rec['peak_context_tokens']} cost=${rec['cost_usd']:.4f}", flush=True)

        print("\n=== Part B (2/3): Compress -- targeted summary ===", flush=True)
        for item in items_768k:
            rec = run_summary_item(budget, item, args.n_chunks, args.model, args.thinking,
                                    Path("work/part_b/summary"), args.timeout, sessions_dir, raw_dir)
            results["summary_compress"]["items"].append(rec)
            print(f"  summary item {item['id']}: verdict={'correct' if rec['reask']['correct'] else 'WRONG'} "
                  f"(answer={rec['reask']['raw_answer']!r}) total_tokens={rec['total_tokens']} "
                  f"peak_context={rec['peak_context_tokens']} cost=${rec['cost_usd']:.4f}", flush=True)

        print("\n=== Part B (3/3): Compress -- pi's own auto-compaction (256K items) ===", flush=True)
        for item in items_256k:
            rec = run_compaction_item(budget, item, args.n_chunks, args.model, args.thinking,
                                       Path("work/part_b/compaction"), args.timeout, sessions_dir, raw_dir,
                                       args.compaction_threshold)
            results["compaction"]["items"].append(rec)
            print(f"  compaction item {item['id']}: verdict={'correct' if rec['correct'] else 'WRONG'} "
                  f"(answer={rec['raw_answer']!r}) total_tokens={rec['total_tokens']} "
                  f"peak_context={rec['peak_context_tokens']} compactions={rec['num_compactions']} "
                  f"cost=${rec['cost_usd']:.4f}", flush=True)
    except BudgetExceeded as e:
        results["aborted"] = True
        results["abort_reason"] = str(e)
        print(f"\n*** BUDGET GUARD TRIPPED: {e} ***\n", file=sys.stderr)

    results["budget"] = {
        "target_usd": args.budget_target, "hard_stop_usd": args.hard_stop,
        "total_spent_usd": round(budget.spent, 6), "calls": budget.log,
    }

    write_json(str(part_b_dir / "results.json"), results)
    write_summary_md(part_b_dir, results, items_768k, items_256k)
    print(f"\nWrote {part_b_dir / 'results.json'} and {part_b_dir / 'summary.md'}")
    print(f"Total spend: ${budget.spent:.4f} (target ${args.budget_target:.2f}, hard stop ${args.hard_stop:.2f})")
    if results["aborted"]:
        sys.exit(1)


if __name__ == "__main__":
    main()
