"""Stage 3: output. Write the digest as Markdown + JSON and append a run-log line."""

from __future__ import annotations

import json
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .models import Digest


def _slug_time(iso: str) -> str:
    return iso.replace(":", "").replace("+00:00", "Z")


def render_markdown(d: Digest) -> str:
    lines = [f"# AI News Digest — {d.generated_at[:10]}", ""]
    lines.append(f"_Generated {d.generated_at} · {len(d.items)} new item(s) · "
                 f"method: {d.method}{' (' + d.model + ')' if d.model else ''}_")
    lines += ["", "## Overview", "", d.overview or "_(none)_", ""]
    if d.themes:
        lines += ["## Themes", ""]
        for t in d.themes:
            lines.append(f"- **{t.title}** — {t.detail}")
        lines.append("")
    # group by source, preserving first-appearance order
    order: list[str] = []
    groups: dict[str, list] = {}
    for a, s in d.items:
        if a.source_name not in groups:
            order.append(a.source_name)
            groups[a.source_name] = []
        groups[a.source_name].append((a, s))
    for src in order:
        lines += [f"## {src}", ""]
        for a, s in groups[src]:
            date = f" · {a.published}" if a.published else ""
            cat = f" · {a.category}" if a.category else ""
            lines.append(f"### [{s.headline}]({a.url})")
            lines.append(f"_{a.title}{date}{cat}_")
            lines += ["", s.summary, ""]
            if s.why_it_matters:
                lines += [f"**Why it matters:** {s.why_it_matters}", ""]
            if s.tags:
                lines += ["Tags: " + ", ".join(f"`{t}`" for t in s.tags), ""]
            if a.fetch_error:
                lines += [f"_Note: full text not fetched ({a.fetch_error}); summary based on teaser._", ""]
    return "\n".join(lines).rstrip() + "\n"


def write_digest(d: Digest, outputs_dir: Path) -> dict[str, Path]:
    digests = outputs_dir / "digests"
    digests.mkdir(parents=True, exist_ok=True)
    stem = _slug_time(d.generated_at)
    md = digests / f"{stem}.md"
    js = digests / f"{stem}.json"
    md.write_text(render_markdown(d), encoding="utf-8")
    js.write_text(json.dumps(d.to_dict(), indent=2, ensure_ascii=False), encoding="utf-8")
    latest = outputs_dir / "latest.md"
    shutil.copyfile(md, latest)
    return {"markdown": md, "json": js, "latest": latest}


def append_run_log(record: dict[str, Any], outputs_dir: Path) -> Path:
    outputs_dir.mkdir(parents=True, exist_ok=True)
    path = outputs_dir / "runs.jsonl"
    record = {"logged_at": datetime.now(timezone.utc).isoformat(timespec="seconds"), **record}
    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(record, ensure_ascii=False, default=str) + "\n")
    return path
