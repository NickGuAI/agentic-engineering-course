#!/usr/bin/env python3
"""benchmarks/select_qa1_topend.py -- sample n BABILong qa1 items from each
requested bucket (256k and 512k native; 768k constructed by
prepare_qa1_topend.py) and write benchmarks/subset_qa1_topend.json.

Each item gets a per-bucket sequential id (1..n), the raw story text
("haystack"), the question, the gold target room, the extracted person name,
the fact's needle depth in real tokens, a provenance "source" record, and a
ready-to-send "prompt" (instructions + haystack + question) for a single-call
run. Sampling is seeded (seed=7) so re-running this script picks the same
rows.

Requires benchmarks/babilong/data/qa1/{256k,512k}.json and, for the 768k
bucket, benchmarks/qa1_768k_survivors.json (run prepare_qa1_topend.py first).

Usage:
  python3 benchmarks/select_qa1_topend.py --n 5 --buckets 256k,512k,768k
"""
import argparse
import json
import random
import sys
from pathlib import Path

BASE = Path(__file__).resolve().parent
sys.path.insert(0, str(BASE.parent))
sys.path.insert(0, str(BASE))
from lib.pi_runner import real_token_count  # noqa: E402
from prepare_qa1_topend import find_fact_span  # noqa: E402

SEED = 7

INSTRUCTION = (
    "I will give you a long story, then ask a question about it. Read the story carefully to find "
    "the relevant fact. Some facts name a place directly (e.g. 'Sandra moved to the garden'); others "
    "refer back to a place already mentioned using a word like 'there' or 'here' (e.g. 'Sandra took "
    "the milk there') -- if the sentence you find uses 'there'/'here' instead of naming the place, "
    "that is not your answer: look at the most recent earlier sentence about the same person that "
    "names an actual place, and use that place name instead. Never answer with the word 'there' or "
    "'here' itself.\n\n"
    "After the story, respond with ONLY the answer to the question -- the bare word or short phrase "
    "itself, exactly as it would appear in the story (e.g. 'bedroom', not 'the bedroom' or 'It is the "
    "bedroom.'): no leading article (a/an/the), no punctuation, no explanation, nothing else."
)


def _prompt_for(haystack: str, question: str) -> str:
    return f"{INSTRUCTION}\n\nStory:\n{haystack}\n\nQuestion: {question}\nAnswer:"


def sample_native_bucket(bucket: str, n: int) -> list:
    path = BASE / "babilong" / "data" / "qa1" / f"{bucket}.json"
    data = json.loads(path.read_text(encoding="utf-8"))
    rng = random.Random(SEED)
    idxs = sorted(rng.sample(range(len(data)), min(n, len(data))))
    items = []
    for k, idx in enumerate(idxs, start=1):
        row = data[idx]
        span = find_fact_span(row)
        person = span[0] if span else None
        needle_depth = real_token_count(row["input"][:span[1]]) if span else None
        items.append({
            "id": k, "bucket": bucket, "person": person, "target": row["target"],
            "question": row["question"].strip(), "haystack": row["input"],
            "prompt": _prompt_for(row["input"], row["question"].strip()),
            "needle_depth_tokens": needle_depth,
            "real_tokens_estimate": real_token_count(row["input"]),
            "source": {"file": f"data/qa1/{bucket}.json", "row_index": idx},
        })
    return items


def sample_768k_bucket(n: int) -> list:
    survivors_path = BASE / "qa1_768k_survivors.json"
    if not survivors_path.exists():
        print(f"ERROR: {survivors_path} not found. Run prepare_qa1_topend.py first.", file=sys.stderr)
        sys.exit(1)
    survivors = json.loads(survivors_path.read_text(encoding="utf-8"))
    rng = random.Random(SEED)
    picked = rng.sample(survivors, min(n, len(survivors)))
    items = []
    for k, s in enumerate(picked, start=1):
        items.append({
            "id": k, "bucket": "768k", "person": s["person"], "target": s["target"],
            "question": s["question"].strip(), "haystack": s["input_truncated"],
            "prompt": _prompt_for(s["input_truncated"], s["question"].strip()),
            "needle_depth_tokens": s["needle_depth_tokens"],
            "real_tokens_estimate": s["truncated_tokens"],
            "source": {"file": "data/qa1/1M.json (truncated)", "row_index": s["row_index"]},
        })
    return items


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--n", type=int, default=5, help="items to sample per bucket (default: 5)")
    ap.add_argument("--buckets", default="256k,512k,768k", help="comma-separated buckets to sample")
    args = ap.parse_args()

    buckets = [b.strip() for b in args.buckets.split(",") if b.strip()]
    all_items = []
    for bucket in buckets:
        if bucket == "768k":
            items = sample_768k_bucket(args.n)
        elif bucket in ("256k", "512k"):
            items = sample_native_bucket(bucket, args.n)
        else:
            print(f"Unknown bucket '{bucket}', skipping (expected 256k, 512k, or 768k)", file=sys.stderr)
            continue
        print(f"{bucket}: {len(items)} items")
        all_items.extend(items)

    out_path = BASE / "subset_qa1_topend.json"
    out_path.write_text(json.dumps(all_items, indent=2), encoding="utf-8")
    print(f"wrote {out_path} with {len(all_items)} items total")

    for bucket in buckets:
        rows = [it for it in all_items if it["bucket"] == bucket]
        depths = sorted(it["needle_depth_tokens"] for it in rows if it["needle_depth_tokens"] is not None)
        if depths:
            n = len(depths)
            print(f"{bucket} needle depth (n={n}): tokens min={depths[0]:,} median={depths[n // 2]:,} max={depths[-1]:,}")


if __name__ == "__main__":
    main()
