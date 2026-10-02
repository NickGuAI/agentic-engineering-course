#!/usr/bin/env python3
"""Automated spot-check of [p.N] citations in a lecture summary.

check_summary.py verifies that every line *carries* a tag. It cannot verify that
the tag points at the right page -- that step is left to a human who opens the
PDF. This script automates that step lexically: for each [p.N] line it pulls the
text of PDF page N and measures how much of the claim's vocabulary is actually
there.

Usage:
    python3 scripts/spot_check_auto.py <n> [--threshold 0.60] [--verbose]

Reads:
    summaries/{n}.md                   -- the summary to spot-check
    course-materials/lecture-{n}.pdf   -- the source of truth

Writes nothing. Prints a pass/fail report.

Exit code: 0 if every cited claim is grounded on its page, 1 otherwise.

This is a lexical check, not a semantic one. It is good at catching a claim
attributed to the wrong page and at surfacing text that appears nowhere in the
deck; it cannot catch a claim whose words are on the page but whose meaning is
wrong. FAIL means "a human must look at this one", not "this is false".
"""
from __future__ import annotations

import argparse
import re
import shutil
import subprocess
import sys
import unicodedata
from pathlib import Path

PAGE_TAG_RE = re.compile(r"\[p\.(\d+)\]")
SUPP_TAG_RE = re.compile(r"\[보충\]")

# Dropped before scoring: too common to carry evidence either way.
STOPWORDS = {
    "a", "an", "the", "and", "or", "but", "if", "then", "than", "so", "as", "of",
    "to", "in", "on", "at", "by", "for", "with", "from", "into", "onto", "that",
    "this", "these", "those", "it", "its", "is", "are", "was", "were", "be",
    "been", "being", "has", "have", "had", "do", "does", "did", "can", "could",
    "will", "would", "may", "might", "must", "should", "we", "our", "us", "you",
    "they", "their", "them", "he", "she", "his", "her", "one", "also", "not",
    "no", "all", "any", "each", "every", "both", "which", "who", "what", "when",
    "where", "how", "why", "there", "here", "such", "e", "g", "eg", "ie",
    "other", "others", "some", "more", "most", "only", "very", "up", "out",
    "about", "over", "under", "between", "while", "thus", "therefore", "however",
}

# Summary prose paraphrases the slides; these map paraphrase back onto slide
# vocabulary so that a faithful rewording is not scored as ungrounded.
SYNONYMS = {
    "vertices": "nodes", "vertex": "node", "arcs": "edges", "arc": "edge",
    "instantiates": "", "instantiate": "", "formally": "", "entries": "",
}


def norm(text: str) -> str:
    """Fold unicode math letters (𝑆 -> S) and dashes, then lowercase."""
    text = unicodedata.normalize("NFKC", text)
    text = text.replace("’", "'").replace("‘", "'")
    text = re.sub(r"[‐-―−]", "-", text)
    return text.lower()


def tokens(text: str) -> list[str]:
    raw = re.findall(r"[a-z0-9]+", norm(text))
    out = []
    for t in raw:
        t = SYNONYMS.get(t, t)
        if not t or t in STOPWORDS:
            continue
        out.append(stem(t))
    return out


def stem(t: str) -> str:
    """Crude suffix stripping -- enough to match 'expanding'/'expansion'."""
    for suf in ("ations", "ation", "ings", "ing", "ies", "ers", "er", "es", "s"):
        if len(t) > len(suf) + 3 and t.endswith(suf):
            base = t[: -len(suf)]
            if suf in ("ies",):
                base += "y"
            return base
    return t


def pdf_pages(pdf: Path) -> dict[int, str]:
    """Extract every page's text via poppler's pdftotext, keyed by page number."""
    if shutil.which("pdftotext") is None:
        sys.exit("ERROR: pdftotext (poppler) not found. Install with: brew install poppler")
    proc = subprocess.run(
        ["pdftotext", "-layout", str(pdf), "-"],
        capture_output=True, text=True, check=True,
    )
    # pdftotext separates pages with a form feed.
    return dict(enumerate(proc.stdout.split("\f"), start=1))


BULLET_RE = re.compile(r"^\s*(?:[-*+•]|\d+[.)])\s+")
ABBREV_RE = re.compile(r"\b(?:e\.g|i\.e|etc|cf|vs|Dr|Fig|approx|no)\.$", re.IGNORECASE)


def split_sentences(text: str) -> list[str]:
    """Split prose on sentence boundaries, leaving 'e.g.' and the like intact."""
    parts, buf = [], []
    for chunk in re.split(r"(?<=[.!?])\s+", text):
        buf.append(chunk)
        if ABBREV_RE.search(chunk):
            continue  # abbreviation, not a sentence end -- keep accumulating
        parts.append(" ".join(buf))
        buf = []
    if buf:
        parts.append(" ".join(buf))
    return [p.strip() for p in parts if p.strip()]


def iter_units(md: str):
    """Yield (lineno, section, text) for each checkable unit of the summary.

    A bullet is one unit (continuation lines folded back in). A prose paragraph
    is hard-wrapped in the source, so it is reflowed and then split into
    sentences -- otherwise a wrapped sentence is scored as two half-claims,
    each missing the vocabulary that landed on the other line.
    """
    section = "(no section)"
    block: list[tuple[int, str]] = []

    def flush():
        if not block:
            return
        if any(BULLET_RE.match(l) for _, l in block):
            cur_no, cur = None, []
            for lineno, line in block:
                if BULLET_RE.match(line):
                    if cur:
                        yield cur_no, section, " ".join(cur)
                    cur_no, cur = lineno, [BULLET_RE.sub("", line).strip()]
                elif cur:
                    cur.append(line.strip())
            if cur:
                yield cur_no, section, " ".join(cur)
        else:
            lineno = block[0][0]
            for sent in split_sentences(" ".join(l.strip() for _, l in block)):
                yield lineno, section, sent
        block.clear()

    for lineno, line in enumerate(md.splitlines(), start=1):
        stripped = line.strip()
        if stripped.startswith("#"):
            yield from flush()
            section = stripped.lstrip("#").strip()
        elif not stripped:
            yield from flush()
        else:
            block.append((lineno, line))
    yield from flush()


def extract_claims(md: str) -> list[dict]:
    """One entry per checkable unit that carries a [p.N] tag."""
    claims = []
    for lineno, section, text in iter_units(md):
        pages = [int(p) for p in PAGE_TAG_RE.findall(text)]
        if not pages:
            continue  # untagged, or [보충] only -- no page claim to verify
        claim = SUPP_TAG_RE.sub("", PAGE_TAG_RE.sub("", text))
        claim = re.sub(r"\s{2,}", " ", claim).strip()
        claims.append({"lineno": lineno, "section": section, "pages": pages, "text": claim})
    return claims


def score(claim_tokens: list[str], page_tokens: set[str]) -> float:
    """Fraction of the claim's distinct content words present on the page."""
    uniq = set(claim_tokens)
    if not uniq:
        return 1.0
    return len(uniq & page_tokens) / len(uniq)


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("n", help="lecture number, e.g. 01")
    ap.add_argument("--threshold", type=float, default=0.60,
                    help="min fraction of claim words that must appear on the cited page (default 0.60)")
    ap.add_argument("--warn-threshold", type=float, default=0.40,
                    help="below this a claim FAILs; between the two it WARNs (default 0.40)")
    ap.add_argument("--verbose", action="store_true", help="list every claim, not just problems")
    args = ap.parse_args()

    n = args.n
    summary_path = Path(f"summaries/{n}.md")
    pdf_path = Path(f"course-materials/lecture-{n}.pdf")
    for p in (summary_path, pdf_path):
        if not p.exists():
            sys.exit(f"ERROR: {p} not found (run from the outputs/ directory)")

    pages = pdf_pages(pdf_path)
    page_tokens = {num: set(tokens(text)) for num, text in pages.items()}
    claims = extract_claims(summary_path.read_text(encoding="utf-8"))

    results = []
    for c in claims:
        ct = tokens(c["text"])
        per_page = {p: score(ct, page_tokens.get(p, set())) for p in c["pages"]}
        best_cited = max(per_page.values()) if per_page else 0.0
        out_of_range = [p for p in c["pages"] if p not in page_tokens]
        # Where would this claim have scored best across the whole deck?
        best_page, best_any = max(
            ((p, score(ct, tk)) for p, tk in page_tokens.items()),
            key=lambda kv: kv[1], default=(0, 0.0),
        )
        if out_of_range:
            status = "FAIL"
        elif best_cited >= args.threshold:
            status = "PASS"
        elif best_cited >= args.warn_threshold:
            status = "WARN"
        else:
            status = "FAIL"
        best_cited_page = max(per_page, key=per_page.get) if per_page else None
        surface = {}
        for w in re.findall(r"[A-Za-z0-9^]+", norm(c["text"])):
            surface.setdefault(stem(SYNONYMS.get(w, w)), w)
        absent = sorted(surface.get(t, t) for t in set(ct) - page_tokens.get(best_cited_page, set()))
        results.append({**c, "per_page": per_page, "best_cited": best_cited, "absent": absent,
                        "best_page": best_page, "best_any": best_any,
                        "out_of_range": out_of_range, "status": status,
                        "n_tokens": len(set(ct))})

    report(n, pdf_path, results, args)

    failed = sum(1 for r in results if r["status"] == "FAIL")
    sys.exit(0 if failed == 0 else 1)


def report(n: str, pdf_path: Path, results: list[dict], args) -> None:
    counts = {s: sum(1 for r in results if r["status"] == s) for s in ("PASS", "WARN", "FAIL")}
    print(f"# Automated spot-check — lecture {n}")
    print(f"\nSource: {pdf_path}")
    print(f"Cited claims checked: {len(results)}")
    print(f"Thresholds: PASS >= {args.threshold:.2f} | WARN >= {args.warn_threshold:.2f} | FAIL below")
    print(f"\n**PASS {counts['PASS']}  |  WARN {counts['WARN']}  |  FAIL {counts['FAIL']}**")

    shown = [r for r in results if args.verbose or r["status"] != "PASS"]
    if shown:
        print("\n## Items" if args.verbose else "\n## Items needing a human look")
        for r in shown:
            cited = ", ".join(f"p.{p}={r['per_page'][p]:.2f}" for p in r["pages"])
            print(f"\n[{r['status']}] line {r['lineno']} — {r['section']}")
            print(f"  claim : {r['text'][:150]}")
            print(f"  cited : {cited}  ({r['n_tokens']} content words)")
            if r["absent"]:
                print(f"  absent: {', '.join(r['absent'][:12])}"
                      + (" …" if len(r["absent"]) > 12 else ""))
            if r["out_of_range"]:
                print(f"  !! cited page(s) {r['out_of_range']} do not exist in the PDF")
            elif r["best_page"] not in r["pages"] and r["best_any"] > r["best_cited"] + 0.15:
                print(f"  ?? better match on p.{r['best_page']} ({r['best_any']:.2f}) — possible wrong page")

    # Per-page rollup: where are the weak citations concentrated?
    by_page: dict[int, list[dict]] = {}
    for r in results:
        for p in r["pages"]:
            by_page.setdefault(p, []).append(r)
    print("\n## Per-page summary")
    print("page  claims  pass  warn  fail  mean")
    for p in sorted(by_page):
        rs = by_page[p]
        mean = sum(r["best_cited"] for r in rs) / len(rs)
        c = {s: sum(1 for r in rs if r["status"] == s) for s in ("PASS", "WARN", "FAIL")}
        print(f"{p:>4}  {len(rs):>6}  {c['PASS']:>4}  {c['WARN']:>4}  {c['FAIL']:>4}  {mean:>5.2f}")

    verdict = "PASS — every cited claim is grounded on its page" if counts["FAIL"] == 0 \
        else f"FAIL — {counts['FAIL']} claim(s) not grounded on the cited page"
    print(f"\n## Verdict\n{verdict}")
    if counts["WARN"]:
        print(f"({counts['WARN']} WARN item(s): paraphrased far enough that a human should confirm.)")
    print("\nNote: lexical check only. It catches wrong-page and invented text; it cannot\n"
          "catch a claim whose words are on the page but whose meaning is wrong.")


if __name__ == "__main__":
    main()
