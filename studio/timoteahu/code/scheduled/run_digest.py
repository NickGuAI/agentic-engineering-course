"""One-shot runner for the weekly AI research-update digest.

Replaces the old "loop forever and sleep until next run" process. Each call does one run and
exits; launchd (see schedule/) decides when to call it. Pipeline:

    config.json + prompt.md -> agent (claude | codex | fixture) -> JSON
      -> shape check against digest.schema.json
      -> semantic checks (window, domains, item count, source coverage)
      -> grounding check (evidence quotes re-fetched and matched against the live page)
      -> render Markdown -> verify_digest.py checks on the rendered file
      -> write outputs + append one line to runs.jsonl

Failed checks are fed back to the agent for one repair attempt (config agent.max_attempts).

Exit codes: 0 pass, 1 failed checks / agent error, 2 incomplete (a required source could not be
read, so the digest was published with a missing-source note instead of filled from memory),
3 another run holds the lock.

Stdlib only; Python 3.9+.
"""

from __future__ import annotations

import argparse
import datetime as dt
import fcntl
import html
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.request
from pathlib import Path
from urllib.parse import urlparse

HERE = Path(__file__).resolve().parent
TEAM_DIR = HERE.parent.parent  # studio/timoteahu
sys.path.insert(0, str(HERE.parent))
import verify_digest  # noqa: E402  (code/verify_digest.py, reused unchanged)

DEFAULT_OUT = TEAM_DIR / "outputs" / "scheduled"
DEFAULT_WORK = TEAM_DIR / "work" / "scheduled"  # gitignored: raw agent output lives here
USER_AGENT = "Mozilla/5.0 (research-digest grounding check)"


# ---------------------------------------------------------------- config and prompt

def load_config(path: Path) -> dict:
    with open(path) as f:
        return json.load(f)


def host_matches(host: str, domain: str) -> bool:
    return host == domain or host.endswith("." + domain)


def build_prompt(config: dict, run_date: dt.date, repair_errors: list[str] | None = None) -> str:
    since = run_date - dt.timedelta(days=config["window_days"])
    lines = []
    for s in config["sources"]:
        req = "required" if s["required"] else "optional"
        lines.append(f"- `{s['id']}` ({s['name']}, {req}): {s['index_url']}")
        for fb in s.get("fallback_urls", []):
            lines.append(f"  - fallback: {fb}")
    repair = ""
    if repair_errors:
        repair = ("\n## Your previous attempt failed these checks; fix them\n\n"
                  + "\n".join(f"- {e}" for e in repair_errors) + "\n")
    template = (HERE / "prompt.md").read_text()
    return template.format(
        audience=config["audience"], run_date=run_date.isoformat(), since=since.isoformat(),
        sources_block="\n".join(lines), min_items=config["min_items"],
        max_items=config["max_items"], word_budget=int(config["max_words"] * 0.85),
        repair_block=repair,
    )


# ---------------------------------------------------------------- agent adapters

class AgentError(Exception):
    pass


def _parse_json_text(text: str) -> dict:
    text = text.strip()
    fence = re.match(r"^```(?:json)?\s*(.*?)\s*```$", text, re.DOTALL)
    if fence:
        text = fence.group(1)
    try:
        return json.loads(text)
    except json.JSONDecodeError as e:
        raise AgentError(f"agent output is not JSON: {e}") from e


def allowed_fetch_rules(config: dict) -> list[str]:
    rules = []
    for s in config["sources"]:
        for d in (s["domain"], "www." + s["domain"]):
            rules.append(f"WebFetch(domain:{d})")
    return rules


def claude_command(config: dict, schema_text: str, model: str | None) -> list[str]:
    # Only WebFetch is loaded, and only for approved domains; dontAsk denies anything else
    # instead of prompting. This enforces the card's "approved domains only" rule in the
    # harness rather than trusting the prompt.
    cmd = ["claude", "-p", "--output-format", "json", "--json-schema", schema_text,
           "--tools", "WebFetch", "--allowedTools", *allowed_fetch_rules(config),
           "--permission-mode", "dontAsk", "--no-session-persistence",
           "--max-budget-usd", str(config["agent"]["max_budget_usd"])]
    if model:
        cmd += ["--model", model]
    return cmd


def run_claude(prompt: str, config: dict, schema_path: Path, model: str | None,
               cwd: Path) -> tuple[dict, dict]:
    cmd = claude_command(config, schema_path.read_text(), model)
    proc = subprocess.run(cmd, input=prompt, capture_output=True, text=True, cwd=cwd,
                          timeout=config["agent"]["timeout_seconds"])
    if proc.returncode != 0:
        raise AgentError(f"claude exited {proc.returncode}: {proc.stderr.strip()[:500]}")
    envelope = _parse_json_text(proc.stdout)
    meta = {"cost_usd": envelope.get("total_cost_usd"), "num_turns": envelope.get("num_turns"),
            "raw": envelope}
    if envelope.get("is_error"):
        raise AgentError(f"claude reported error: {str(envelope.get('result'))[:500]}")
    data = envelope.get("structured_output")
    if data is None:
        data = _parse_json_text(envelope.get("result", ""))
    return data, meta


def run_codex(prompt: str, config: dict, schema_path: Path, model: str | None,
              cwd: Path) -> tuple[dict, dict]:
    # Codex cannot restrict fetches to a domain list, so the domain and grounding checks
    # below are the only enforcement on this path.
    with tempfile.NamedTemporaryFile("r", suffix=".json", delete=False) as tmp:
        last_msg = Path(tmp.name)
    cmd = ["codex", "exec", "--output-schema", str(schema_path),
           "--output-last-message", str(last_msg), "--sandbox", "read-only",
           "--skip-git-repo-check", "-c", "tools.web_search=true"]
    if model:
        cmd += ["--model", model]
    cmd.append("-")
    try:
        proc = subprocess.run(cmd, input=prompt, capture_output=True, text=True, cwd=cwd,
                              timeout=config["agent"]["timeout_seconds"])
        if proc.returncode != 0:
            raise AgentError(f"codex exited {proc.returncode}: {proc.stderr.strip()[:500]}")
        text = last_msg.read_text()
    finally:
        last_msg.unlink(missing_ok=True)
    return _parse_json_text(text), {"cost_usd": None, "raw": {"stdout_tail": proc.stdout[-2000:]}}


def fixture_agent(path: Path):
    def run(prompt, config, schema_path, model, cwd):
        return json.loads(path.read_text()), {"cost_usd": 0, "raw": {"fixture": str(path)}}
    return run


# ---------------------------------------------------------------- shape check

_TYPES = {"object": dict, "array": list, "string": str}


def check_shape(value, schema: dict, path: str = "$") -> list[str]:
    """Validate the subset of JSON Schema that digest.schema.json uses."""
    errs = []
    t = schema.get("type")
    if t and not isinstance(value, _TYPES[t]):
        return [f"{path}: expected {t}, got {type(value).__name__}"]
    if "enum" in schema and value not in schema["enum"]:
        errs.append(f"{path}: {value!r} not in {schema['enum']}")
    if t == "object":
        props = schema.get("properties", {})
        for k in schema.get("required", []):
            if k not in value:
                errs.append(f"{path}: missing '{k}'")
        for k, v in value.items():
            if k in props:
                errs += check_shape(v, props[k], f"{path}.{k}")
            elif schema.get("additionalProperties") is False:
                errs.append(f"{path}: unexpected key '{k}'")
    if t == "array" and "items" in schema:
        for i, v in enumerate(value):
            errs += check_shape(v, schema["items"], f"{path}[{i}]")
    return errs


# ---------------------------------------------------------------- semantic checks

def semantic_checks(data: dict, config: dict, run_date: dt.date) -> list[dict]:
    """Checks on the JSON itself. Each result: name, ok, detail, kind."""
    res = []

    def add(name, ok, detail, kind="error"):
        res.append({"name": name, "ok": bool(ok), "detail": detail, "kind": kind})

    since = run_date - dt.timedelta(days=config["window_days"])
    sources = {s["id"]: s for s in config["sources"]}
    items = data["items"]

    add("run_date", data["run_date"] == run_date.isoformat(),
        f"agent said {data['run_date']}, expected {run_date}")
    add("item_count", config["min_items"] <= len(items) <= config["max_items"] or
        any(c["status"] != "ok" for c in data["sources_checked"]),
        f"{len(items)} items (want {config['min_items']}-{config['max_items']})")

    status = {c["source_id"]: c for c in data["sources_checked"]}
    for sid, s in sources.items():
        c = status.get(sid)
        if c is None:
            add(f"source_{sid}", False, "not reported in sources_checked")
        elif c["status"] == "failed":
            # A required source that could not be read is an honest stop, not a bad output.
            kind = "missing_input" if s["required"] else "warning"
            add(f"source_{sid}", False, f"failed: {c['detail']}", kind)
        else:
            add(f"source_{sid}", True, f"{c['status']} via {c['url_fetched']}")
    for sid in status:
        if sid not in sources:
            add(f"source_{sid}", False, "unknown source id")

    seen_urls = set()
    for i, it in enumerate(items, 1):
        tag = f"item{i}"
        src = sources.get(it["source_id"])
        if src is None:
            add(f"{tag}_source_id", False, f"unknown source id {it['source_id']!r}")
            continue
        try:
            d = dt.date.fromisoformat(it["date"])
            add(f"{tag}_date", since <= d <= run_date, f"{d} (window {since}..{run_date})")
        except ValueError:
            add(f"{tag}_date", False, f"bad date {it['date']!r}")
        host = urlparse(it["source_url"]).hostname or ""
        add(f"{tag}_domain", host_matches(host, src["domain"]),
            f"{host} vs {src['domain']}")
        is_index = it["source_url"].rstrip("/") in [u.rstrip("/") for u in
                                                    [src["index_url"], *src["fallback_urls"]]]
        add(f"{tag}_article_url", not is_index, it["source_url"])
        add(f"{tag}_unique", it["source_url"] not in seen_urls, it["source_url"])
        seen_urls.add(it["source_url"])
        if status.get(it["source_id"], {}).get("status") == "failed":
            add(f"{tag}_from_failed_source", False,
                "item cites a source the agent reported as failed")
        n_q = len(it["evidence_quotes"])
        add(f"{tag}_quotes", config["grounding"]["min_quotes_per_item"] <= n_q <= 3,
            f"{n_q} quotes")
    return res


# ---------------------------------------------------------------- grounding check

def normalize(text: str) -> str:
    text = html.unescape(text)
    text = re.sub(r"<script.*?</script>|<style.*?</style>", " ", text, flags=re.DOTALL | re.I)
    text = re.sub(r"<[^>]+>", " ", text)
    text = html.unescape(text)  # RSS often double-escapes
    for a, b in (("‘", "'"), ("’", "'"), ("“", '"'), ("”", '"'),
                 ("–", "-"), ("—", "-"), (" ", " ")):
        text = text.replace(a, b)
    return re.sub(r"\s+", " ", text).strip().lower()


def http_fetch(url: str) -> str:
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(req, timeout=20) as r:
        return r.read().decode(r.headers.get_content_charset() or "utf-8", "replace")


def grounding_checks(data: dict, config: dict, fetch=http_fetch) -> list[dict]:
    """Re-fetch each item's page and confirm every evidence quote appears on it.

    feed_description items are also matched against the source's fallback feeds. A page we
    cannot fetch (e.g. 403) makes the item 'unverifiable', which is a warning by default.
    """
    sources = {s["id"]: s for s in config["sources"]}
    cache: dict[str, str | None] = {}
    fetch_errors: dict[str, str] = {}

    def page(url):
        if url not in cache:
            try:
                cache[url] = normalize(fetch(url))
            except Exception as e:  # network errors, HTTP errors, timeouts
                cache[url], fetch_errors[url] = None, f"{type(e).__name__}: {e}"
        return cache[url]

    res = []
    for i, it in enumerate(data["items"], 1):
        src = sources.get(it["source_id"])
        if src is None:
            continue
        urls = [it["source_url"]]
        if it["claim_basis"] == "feed_description":
            urls += src["fallback_urls"] + [src["index_url"]]
        texts = [t for t in (page(u) for u in urls) if t is not None]
        if not texts:
            ok = not config["grounding"]["fail_on_unverifiable"]
            res.append({"name": f"item{i}_grounding", "ok": ok, "kind": "warning",
                        "detail": f"unverifiable: {fetch_errors.get(it['source_url'])}"})
            continue
        missing = [q for q in it["evidence_quotes"]
                   if not any(normalize(q) in t for t in texts)]
        res.append({"name": f"item{i}_grounding", "ok": not missing, "kind": "error",
                    "detail": (f"{len(it['evidence_quotes'])} quotes found" if not missing
                               else "not on page: " + "; ".join(repr(q[:60]) for q in missing))})
    return res


# ---------------------------------------------------------------- render

def render_markdown(data: dict, config: dict) -> str:
    names = {s["id"]: s["name"] for s in config["sources"]}
    run_date = data["run_date"]
    out = [f"# AI Research Update: week of {run_date}", ""]
    ok = [names.get(c["source_id"], c["source_id"]) for c in data["sources_checked"]
          if c["status"] != "failed"]
    out += [f"Sources read: {', '.join(ok) or 'none'}.", ""]
    missing = [c for c in data["sources_checked"] if c["status"] == "failed"]
    if missing:
        out += ["## Missing sources", ""]
        for c in missing:
            out.append(f"- {names.get(c['source_id'], c['source_id'])}: could not be read "
                       f"({c['detail']}). No items were filled in for it.")
        out.append("")
    for it in sorted(data["items"], key=lambda x: x["date"], reverse=True):
        basis = " (from feed description only)" if it["claim_basis"] == "feed_description" else ""
        out += [f"### {it['title']}", f"Date: {it['date']}", f"Source: {it['source_url']}", "",
                it["summary"].strip() + basis, "",
                f"Why it matters: {it['why_it_matters'].strip()}", ""]
    return "\n".join(out).rstrip() + "\n"


def markdown_checks(md: str, config: dict, run_date: dt.date, data: dict) -> list[dict]:
    """Reuse code/verify_digest.py on the rendered file so both paths agree."""
    failed = {c["source_id"] for c in data["sources_checked"] if c["status"] == "failed"}
    domains = [s["domain"] for s in config["sources"]]
    required = [s["domain"] for s in config["sources"] if s["required"] and s["id"] not in failed]
    res = verify_digest.check(md, run_date, config["window_days"], domains, required,
                              config["max_words"])
    return [{"name": f"md_{n}", "ok": ok, "detail": d, "kind": "error"} for n, ok, d in res]


# ---------------------------------------------------------------- orchestration

def overall_status(checks: list[dict]) -> str:
    bad = [c for c in checks if not c["ok"]]
    if any(c["kind"] == "error" for c in bad):
        return "fail"
    if any(c["kind"] == "missing_input" for c in bad):
        return "incomplete"
    return "pass"


def evaluate(data: dict, config: dict, schema: dict, run_date: dt.date, grounding: bool,
             fetch=http_fetch) -> tuple[list[dict], str | None]:
    shape = check_shape(data, schema)
    if shape:
        return [{"name": "shape", "ok": False, "detail": e, "kind": "error"} for e in shape], None
    checks = semantic_checks(data, config, run_date)
    if grounding:
        checks += grounding_checks(data, config, fetch)
    else:
        checks.append({"name": "grounding", "ok": True, "detail": "skipped (--skip-grounding)",
                       "kind": "warning"})
    md = render_markdown(data, config)
    checks += markdown_checks(md, config, run_date, data)
    return checks, md


def write_atomic(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(text)
    os.replace(tmp, path)


def run(args, agent_fn=None, fetch=http_fetch) -> int:
    config = load_config(Path(args.config))
    schema_path = HERE / "digest.schema.json"
    schema = json.loads(schema_path.read_text())
    run_date = dt.date.fromisoformat(args.run_date) if args.run_date else dt.date.today()
    out_dir, work_dir = Path(args.out_dir) / run_date.isoformat(), Path(args.work_dir)
    if args.dry_run:
        print(build_prompt(config, run_date))
        print("\n$ " + " ".join(claude_command(config, "<schema>", args.model)))
        return 0
    out_dir.mkdir(parents=True, exist_ok=True)
    work_dir.mkdir(parents=True, exist_ok=True)

    lock = open(work_dir / "run.lock", "w")
    try:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except BlockingIOError:
        print("another run is in progress; exiting", file=sys.stderr)
        return 3

    checks_path = out_dir / "checks.json"
    if checks_path.exists() and not args.force:
        prev = json.loads(checks_path.read_text())
        if prev.get("status") == "pass":
            print(f"{run_date} already passed; use --force to rerun")
            return 0

    if agent_fn is None:
        agent_name = args.agent or config["agent"]["default"]
        if agent_name == "fixture":
            agent_fn = fixture_agent(Path(args.fixture))
        else:
            if not shutil.which(agent_name):
                print(f"'{agent_name}' CLI not found on PATH", file=sys.stderr)
                return 1
            agent_fn = {"claude": run_claude, "codex": run_codex}[agent_name]
    else:
        agent_name = "injected"

    started = time.time()
    repair, attempts, total_cost = None, [], 0.0
    checks, md, data, status = [], None, None, "fail"
    for attempt in range(1, config["agent"]["max_attempts"] + 1):
        prompt = build_prompt(config, run_date, repair)
        try:
            data, meta = agent_fn(prompt, config, schema_path, args.model, work_dir)
        except (AgentError, subprocess.TimeoutExpired, OSError) as e:
            checks = [{"name": "agent", "ok": False, "detail": str(e)[:500], "kind": "error"}]
            attempts.append({"attempt": attempt, "status": "agent_error", "detail": str(e)[:500]})
            repair = None
            continue
        total_cost += meta.get("cost_usd") or 0
        write_atomic(work_dir / run_date.isoformat() / f"agent-attempt-{attempt}.json",
                     json.dumps(meta.get("raw"), indent=2))
        checks, md = evaluate(data, config, schema, run_date, not args.skip_grounding, fetch)
        status = overall_status(checks)
        attempts.append({"attempt": attempt, "status": status,
                         "failed": [c["name"] for c in checks if not c["ok"]]})
        if status != "fail":
            break
        repair = [f"{c['name']}: {c['detail']}" for c in checks
                  if not c["ok"] and c["kind"] == "error"]

    if data is not None and md is not None:
        write_atomic(out_dir / "digest.json", json.dumps(data, indent=2) + "\n")
        name = f"research-update-{run_date}.md" if status != "fail" \
            else f"research-update-{run_date}.REJECTED.md"
        write_atomic(out_dir / name, md)
        if status != "fail":
            (out_dir / f"research-update-{run_date}.REJECTED.md").unlink(missing_ok=True)
    report = {"run_date": run_date.isoformat(), "status": status, "agent": agent_name,
              "attempts": attempts, "checks": checks}
    write_atomic(checks_path, json.dumps(report, indent=2) + "\n")

    log = {"started": dt.datetime.fromtimestamp(started).isoformat(timespec="seconds"),
           "seconds": round(time.time() - started, 1), "run_date": run_date.isoformat(),
           "agent": agent_name, "attempts": len(attempts), "status": status,
           "cost_usd": round(total_cost, 4),
           "failed_checks": [c["name"] for c in checks if not c["ok"]]}
    with open(Path(args.out_dir) / "runs.jsonl", "a") as f:
        f.write(json.dumps(log) + "\n")

    for c in checks:
        flag = "PASS" if c["ok"] else ("WARN" if c["kind"] == "warning" else "FAIL")
        print(f"{flag}  {c['name']}: {c['detail']}")
    print(f"RESULT: {status.upper()} ({len(attempts)} attempt(s)) -> {out_dir}")
    return {"pass": 0, "incomplete": 2}.get(status, 1)


def parse_args(argv=None):
    p = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    p.add_argument("--config", default=str(HERE / "config.json"))
    p.add_argument("--agent", choices=["claude", "codex", "fixture"])
    p.add_argument("--model", help="passed through to the agent CLI")
    p.add_argument("--fixture", help="JSON file used by --agent fixture")
    p.add_argument("--run-date", help="YYYY-MM-DD (default: today)")
    p.add_argument("--out-dir", default=str(DEFAULT_OUT))
    p.add_argument("--work-dir", default=str(DEFAULT_WORK))
    p.add_argument("--skip-grounding", action="store_true", help="no network re-fetch of quotes")
    p.add_argument("--force", action="store_true", help="rerun even if this date already passed")
    p.add_argument("--dry-run", action="store_true", help="print prompt and command, call nothing")
    a = p.parse_args(argv)
    if a.agent == "fixture" and not a.fixture:
        p.error("--agent fixture needs --fixture")
    return a


if __name__ == "__main__":
    sys.exit(run(parse_args()))
