"""Check a research-update digest against the delegation card's success criteria.

Stdlib only. Exits 0 on pass, 1 on any failed check, and prints one line per check.
"""

import argparse
import datetime as dt
import json
import re
import sys
from urllib.parse import urlparse

ITEM_RE = re.compile(r"^### ", re.MULTILINE)
DATE_RE = re.compile(r"^Date:\s*(\d{4}-\d{2}-\d{2})", re.MULTILINE)
SOURCE_RE = re.compile(r"^Source:\s*(\S+)", re.MULTILINE)


def check(digest_text, run_date, window_days, allowed, required, max_words):
    results = []
    items = ITEM_RE.split(digest_text)[1:]
    results.append(("has_items", len(items) >= 1, f"{len(items)} items"))

    since = run_date - dt.timedelta(days=window_days)
    seen_domains = set()
    for i, item in enumerate(items, 1):
        title = item.splitlines()[0].strip()
        date_m = DATE_RE.search(item)
        src_m = SOURCE_RE.search(item)
        if not date_m:
            results.append((f"item{i}_date", False, f"{title}: no Date line"))
        else:
            d = dt.date.fromisoformat(date_m.group(1))
            ok = since <= d <= run_date
            results.append((f"item{i}_date", ok, f"{title}: {d} (window {since}..{run_date})"))
        if not src_m:
            results.append((f"item{i}_source", False, f"{title}: no Source line"))
        else:
            host = urlparse(src_m.group(1)).hostname or ""
            ok = any(host == a or host.endswith("." + a) for a in allowed)
            seen_domains.add(host.removeprefix("www."))
            results.append((f"item{i}_source", ok, f"{title}: {host}"))

    for req in required:
        ok = req in seen_domains
        results.append((f"coverage_{req}", ok, "present" if ok else "MISSING"))

    words = len(digest_text.split())
    results.append(("word_limit", words <= max_words, f"{words}/{max_words} words"))
    return results


def main():
    p = argparse.ArgumentParser()
    p.add_argument("digest")
    p.add_argument("--run-date", required=True, help="YYYY-MM-DD")
    p.add_argument("--window-days", type=int, default=7)
    p.add_argument("--allow", nargs="+", default=["anthropic.com", "openai.com"])
    p.add_argument("--require", nargs="*", default=["anthropic.com", "openai.com"])
    p.add_argument("--max-words", type=int, default=600)
    p.add_argument("--json-out", help="also write results as JSON")
    a = p.parse_args()

    with open(a.digest) as f:
        text = f.read()
    results = check(text, dt.date.fromisoformat(a.run_date), a.window_days,
                    a.allow, a.require, a.max_words)
    for name, ok, detail in results:
        print(f"{'PASS' if ok else 'FAIL'}  {name}: {detail}")
    passed = all(ok for _, ok, _ in results)
    print("RESULT:", "PASS" if passed else "FAIL")
    if a.json_out:
        with open(a.json_out, "w") as f:
            json.dump({"digest": a.digest, "passed": passed,
                       "checks": [{"name": n, "ok": o, "detail": d} for n, o, d in results]},
                      f, indent=2)
    sys.exit(0 if passed else 1)


if __name__ == "__main__":
    main()
