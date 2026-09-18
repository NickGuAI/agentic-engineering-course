#!/usr/bin/env python3
"""benchmarks/prepare_qa1_topend.py -- measure BABILong qa1 real-token sizes
for the 512K and 1M buckets, then build the 768K bucket: truncate every 1M
item to 768,000 real tokens and keep only the items whose single supporting
fact ("PERSON moved/went/... (back) to the ROOM") still survives inside the
truncated text.

No model calls. Requires benchmarks/babilong/data/qa1/512k.json and
benchmarks/babilong/data/qa1/1M.json (setup.sh downloads these).

Usage:
  python3 benchmarks/prepare_qa1_topend.py
"""
import argparse
import json
import re
import sys
from pathlib import Path

BASE = Path(__file__).resolve().parent
sys.path.insert(0, str(BASE.parent))
from lib.pi_runner import real_slice_by_tokens, real_token_count  # noqa: E402

TRUNCATE_TOKENS = 768_000

FACT_VERBS = r"(?:moved|went|travell?ed|journeyed|walked|ran|goes|go)"


def find_fact_span(row):
    """(person, char_start, char_end) of the LAST 'PERSON verb (back) to the
    TARGET' sentence -- the single supporting fact for this qa1 row -- or
    None if no such sentence is found."""
    m = re.search(r"Where is (\w+)", row["question"])
    if not m:
        return None
    person = m.group(1)
    target = row["target"]
    pat = re.compile(re.escape(person) + r" " + FACT_VERBS + r" (?:back )?to the " + re.escape(target) + r"\b", re.I)
    matches = list(pat.finditer(row["input"]))
    if not matches:
        return None
    last = matches[-1]
    return person, last.start(), last.end()


def report_bucket_tokens(bucket):
    data = json.loads((BASE / "babilong" / "data" / "qa1" / f"{bucket}.json").read_text(encoding="utf-8"))
    toks = sorted(real_token_count(row["input"]) for row in data)
    n = len(toks)
    print(f"qa1/{bucket}: n={n} tokens min={toks[0]:,} median={toks[n // 2]:,} max={toks[-1]:,}")
    return data


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.parse_args()

    print("=== Step 1: measure, no model calls ===")
    data_512k = report_bucket_tokens("512k")
    data_1m = report_bucket_tokens("1M")

    misses_512k = sum(1 for row in data_512k if find_fact_span(row) is None)
    misses_1m = sum(1 for row in data_1m if find_fact_span(row) is None)
    print(f"512k: fact sentence located in {len(data_512k) - misses_512k}/{len(data_512k)} rows")
    print(f"1M:   fact sentence located in {len(data_1m) - misses_1m}/{len(data_1m)} rows")

    print(f"\n=== Step 2: truncate 1M items to {TRUNCATE_TOKENS:,} tokens, keep survivors ===")
    survivors = []
    for i, row in enumerate(data_1m):
        span = find_fact_span(row)
        if span is None:
            continue
        person, fact_start, fact_end = span
        truncated = real_slice_by_tokens(row["input"], TRUNCATE_TOKENS)
        survives = fact_end <= len(truncated)
        if survives:
            trunc_tokens = real_token_count(truncated)
            survivors.append({
                "row_index": i, "person": person, "target": row["target"], "question": row["question"],
                "input_truncated": truncated, "truncated_tokens": trunc_tokens,
                "fact_char_start": fact_start, "fact_char_end": fact_end,
                "original_char_len": len(row["input"]),
                "needle_depth_tokens": real_token_count(row["input"][:fact_start]),
                "needle_depth_fraction_of_original": fact_start / len(row["input"]),
                "needle_depth_fraction_of_truncated": fact_start / len(truncated),
            })

    print(f"{len(survivors)}/{len(data_1m)} 1M-bucket items survive truncation to {TRUNCATE_TOKENS:,} tokens "
          f"(fact sentence still inside the truncated text).")
    out_path = BASE / "qa1_768k_survivors.json"
    out_path.write_text(json.dumps(survivors, indent=2), encoding="utf-8")
    print(f"wrote {out_path}")


if __name__ == "__main__":
    main()
