"""Turn a course document into numbered source blocks.

The harness gives the writer agent the source as ``[S1]``, ``[S2]``, ... blocks so
that every block can be traced to a tutorial section afterwards (see
check_tutorial.py). Supported inputs: Markdown/text as-is, PDF via pypdf, PPTX
via its slide XML, and anything pandoc can read (.docx, .html, .rst, .ipynb, ...).
"""
from __future__ import annotations

import re
import subprocess
import xml.etree.ElementTree as ET
import zipfile
from pathlib import Path

FENCE = re.compile(r"^\s*(```|~~~)")
LIST_ITEM = re.compile(r"^\s*(?:[-*+]|\d+[.)])\s+")
HEADING = re.compile(r"^\s{0,3}#{1,6}\s")
TAG = re.compile(r"^\[S(\d+)\]$")
TEXT_SUFFIXES = {".md", ".markdown", ".txt", ".text"}
DRAWINGML = "{http://schemas.openxmlformats.org/drawingml/2006/main}"


def extract_text(path: Path) -> str:
    """Return the document as Markdown-ish text."""
    suffix = path.suffix.lower()
    if suffix in TEXT_SUFFIXES:
        return path.read_text(encoding="utf-8", errors="replace")
    if suffix == ".pdf":
        return _pdf_text(path)
    if suffix == ".pptx":
        return _pptx_text(path)
    return _pandoc_text(path)


def _pdf_text(path: Path) -> str:
    try:
        from pypdf import PdfReader
    except ImportError as exc:  # pragma: no cover - environment dependent
        raise RuntimeError("PDF input needs the pypdf package: pip install pypdf") from exc
    pages = []
    for number, page in enumerate(PdfReader(str(path)).pages, 1):
        pages.append(f"## Page {number}\n\n{_reflow(page.extract_text() or '')}")
    return "\n\n".join(pages)


def _reflow(text: str) -> str:
    """Some PDFs extract one word per line; join those back into paragraphs."""
    lines = [line for line in text.splitlines() if line.strip()]
    if not lines:
        return ""
    words_per_line = sum(len(line.split()) for line in lines) / len(lines)
    if words_per_line < 2.5:
        return re.sub(r" {2,}", " ", " ".join(line.strip() for line in lines))
    return "\n".join(line.rstrip() for line in lines)


def _pptx_text(path: Path) -> str:
    slides = []
    with zipfile.ZipFile(path) as archive:
        names = archive.namelist()
        slide_names = sorted(
            (n for n in names if re.fullmatch(r"ppt/slides/slide\d+\.xml", n)),
            key=lambda n: int(re.search(r"(\d+)", n.rsplit("/", 1)[1]).group(1)),
        )
        for name in slide_names:
            number = re.search(r"(\d+)", name.rsplit("/", 1)[1]).group(1)
            parts = [f"## Slide {number}", ""]
            parts.extend(_drawingml_paragraphs(archive.read(name)))
            notes = f"ppt/notesSlides/notesSlide{number}.xml"
            if notes in names:
                note_lines = _drawingml_paragraphs(archive.read(notes))
                if note_lines:
                    parts.append("")
                    parts.extend(f"> Notes: {line}" for line in note_lines)
            slides.append("\n".join(parts))
    return "\n\n".join(slides)


def _drawingml_paragraphs(xml: bytes) -> list[str]:
    paragraphs = []
    for para in ET.fromstring(xml).iter(f"{DRAWINGML}p"):
        text = "".join(t.text or "" for t in para.iter(f"{DRAWINGML}t")).strip()
        if text:
            paragraphs.append(text)
    return paragraphs


def _pandoc_text(path: Path) -> str:
    result = subprocess.run(
        ["pandoc", "--to", "gfm", "--wrap=none", str(path)],
        capture_output=True, text=True, check=False,
    )
    if result.returncode != 0:
        raise RuntimeError(f"pandoc could not read {path.name}: {result.stderr.strip()}")
    return result.stdout


def split_blocks(text: str) -> list[str]:
    """Split Markdown into blocks: one per heading, paragraph, list item, or code fence.

    HTML comments are dropped first: they are invisible in the rendered document, so
    they are not content the tutorial has to keep.
    """
    text = re.sub(r"<!--.*?-->", "", text, flags=re.S)
    blocks: list[str] = []
    current: list[str] = []
    in_fence = False

    def flush() -> None:
        if any(line.strip() for line in current):
            blocks.append("\n".join(current).strip("\n"))
        current.clear()

    for line in text.splitlines():
        if FENCE.match(line):
            if in_fence:
                current.append(line)
                in_fence = False
                flush()
            else:
                flush()
                current.append(line)
                in_fence = True
            continue
        if in_fence:
            current.append(line)
            continue
        if not line.strip():
            flush()
            continue
        if HEADING.match(line) or LIST_ITEM.match(line):
            flush()
        current.append(line)
        if HEADING.match(line):
            flush()
    flush()
    return blocks


def number_blocks(text: str) -> str:
    """Render blocks as ``[S1]``-tagged sections, one blank line apart."""
    return "\n\n".join(f"[S{i}]\n{block}" for i, block in enumerate(split_blocks(text), 1)) + "\n"


def parse_numbered(text: str) -> dict[int, str]:
    """Inverse of number_blocks: ``{1: block text, 2: ...}``."""
    blocks: dict[int, str] = {}
    current: int | None = None
    lines: list[str] = []
    for line in text.splitlines():
        match = TAG.match(line.strip())
        if match:
            if current is not None:
                blocks[current] = "\n".join(lines).strip("\n")
            current, lines = int(match.group(1)), []
        elif current is not None:
            lines.append(line)
    if current is not None:
        blocks[current] = "\n".join(lines).strip("\n")
    return blocks


def is_code_block(block: str) -> bool:
    return bool(FENCE.match(block.splitlines()[0])) if block else False


def word_count(text: str) -> int:
    return len(re.findall(r"\S+", text))
