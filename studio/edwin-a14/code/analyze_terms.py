"""Count normalized technical terms across the nine Studio 01 article bodies.

The input HTML files are ephemeral snapshots downloaded from only the source URLs
listed in prompt.md. This script uses the first <article> element on each page and
ignores scripts, styles, SVG text, and navigation/footer text.
"""

from __future__ import annotations

import hashlib
import json
import re
from collections import Counter
from html.parser import HTMLParser
from pathlib import Path


FILES = {
    "anthropic-misuse": Path("/tmp/studio01-anthropic-misuse.html"),
    "anthropic-fable": Path("/tmp/studio01-anthropic-fable.html"),
    "anthropic-efs": Path("/tmp/studio01-anthropic-efs.html"),
    "anthropic-containment": Path("/tmp/studio01-anthropic-containment.html"),
    "anthropic-quality": Path("/tmp/studio01-anthropic-quality.html"),
    "anthropic-managed": Path("/tmp/studio01-anthropic-managed.html"),
    "openai-storage": Path("/tmp/studio01-openai-storage.html"),
    "openai-antimicrobials": Path("/tmp/studio01-openai-antimicrobials.html"),
    "openai-data-agent": Path("/tmp/studio01-openai-data-agent.html"),
}

# A transparent domain vocabulary prevents ordinary high-frequency prose words
# from being mislabeled as technical terms. Variants in each regex are combined.
TERMS = {
    "AI": r"\b(?:AI|artificial intelligence)\b",
    "agent/agentic": r"\bagents?\b|\bagentic\b",
    "API": r"\bAPIs?\b",
    "code/coding": r"\bcode\b|\bcoding\b",
    "context": r"\bcontexts?\b",
    "data": r"\bdata\b",
    "evaluation/eval": r"\bevaluations?\b|\bevals?\b",
    "infrastructure": r"\binfrastructures?\b",
    "model": r"\bmodels?\b",
    "privacy": r"\bprivacy\b",
    "research": r"\bresearch(?:er|ers)?\b",
    "risk": r"\brisks?\b",
    "sandbox": r"\bsandboxes?\b",
    "security/safeguards": r"\bsecurity\b|\bsecure\b|\bsafeguards?\b",
    "system": r"\bsystems?\b",
    "tool": r"\btools?\b",
    "workflow": r"\bworkflows?\b",
}


class ArticleText(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.article_depth = 0
        self.skip_depth = 0
        self.parts: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag == "article":
            self.article_depth += 1
        elif self.article_depth and tag in {"script", "style", "svg", "noscript"}:
            self.skip_depth += 1

    def handle_endtag(self, tag: str) -> None:
        if self.article_depth and tag in {"script", "style", "svg", "noscript"}:
            self.skip_depth = max(0, self.skip_depth - 1)
        elif tag == "article" and self.article_depth:
            self.article_depth -= 1

    def handle_data(self, data: str) -> None:
        if self.article_depth and not self.skip_depth:
            value = " ".join(data.split())
            if value:
                self.parts.append(value)


def extract_article(path: Path) -> str:
    parser = ArticleText()
    parser.feed(path.read_text(encoding="utf-8"))
    text = " ".join(parser.parts)
    if not text:
        raise RuntimeError(f"No <article> text extracted from {path}")
    return text


def main() -> None:
    texts = {name: extract_article(path) for name, path in FILES.items()}
    rows = []
    for term, pattern in TERMS.items():
        counts = {
            name: len(re.findall(pattern, text, flags=re.IGNORECASE))
            for name, text in texts.items()
        }
        rows.append(
            {
                "term": term,
                "distinct_posts": sum(count > 0 for count in counts.values()),
                "total_occurrences": sum(counts.values()),
                "per_post": counts,
            }
        )
    rows = [row for row in rows if row["distinct_posts"] >= 2]
    rows.sort(key=lambda row: (-row["distinct_posts"], -row["total_occurrences"], row["term"]))
    evidence = {
        "method": "first <article> element; case-insensitive regex; normalized variants",
        "documents": {
            name: {
                "characters": len(text),
                "sha256": hashlib.sha256(text.encode()).hexdigest(),
            }
            for name, text in texts.items()
        },
        "ranked_terms": rows,
    }
    print(json.dumps(evidence, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
