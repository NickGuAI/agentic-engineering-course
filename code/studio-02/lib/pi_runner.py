#!/usr/bin/env python3
"""lib/pi_runner.py -- shared helpers for Studio 02 (Context Window Stress
Test & Memory Architecture): running `pi` non-interactively and parsing its
output.

Imported by part_a_stress.py, part_b_isolate_compress.py, and
part_c_memory.py. Also runnable directly for one diagnostic:

  python3 lib/pi_runner.py probe-providers

Python 3.9+. Real-token counting (real_token_count, real_slice_by_tokens)
uses tiktoken if installed; every other function is standard library only.
Never prints or returns a secret value -- only whether an environment
variable or a saved credential is present.
"""
from __future__ import annotations

import json
import os
import re
import subprocess
import sys
import time
from pathlib import Path
from typing import Dict, List, Optional, Tuple

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

# Primary path: an OpenAI API key (OPENAI_API_KEY), provider "openai".
# Alternative: a ChatGPT Plus/Pro login (`pi` then `/login`), provider
# "openai-codex". Both use the same model id; see setup.sh and README.md for
# the contextWindow override this model needs above 272,000 input tokens.
DEFAULT_MODEL = "openai/gpt-5.6-luna"

# Environment variable pi reads for each provider's API key. Used only to
# check *presence*, never to read or print the value. Subscription providers
# (openai-codex among them) authenticate via `pi` -> `/login` instead of an
# environment variable and so have no entry here.
ENV_VAR_BY_PROVIDER = {
    "anthropic": "ANTHROPIC_API_KEY",
    "openai": "OPENAI_API_KEY",
    "deepseek": "DEEPSEEK_API_KEY",
    "google": "GEMINI_API_KEY",
    "xai": "XAI_API_KEY",
    "openrouter": "OPENROUTER_API_KEY",
    "mistral": "MISTRAL_API_KEY",
    "groq": "GROQ_API_KEY",
    "cerebras": "CEREBRAS_API_KEY",
    "nvidia": "NVIDIA_API_KEY",
    "azure-openai-responses": "AZURE_OPENAI_API_KEY",
    "amazon-bedrock": "AWS_BEARER_TOKEN_BEDROCK",
}

PI_AGENT_DIR = Path(os.environ.get("PI_CODING_AGENT_DIR", str(Path.home() / ".pi" / "agent")))


# ---------------------------------------------------------------------------
# Real tokenization (tiktoken o200k_base), with a word-count fallback if
# tiktoken is not installed.
# ---------------------------------------------------------------------------

_TIKTOKEN_ENCODING = None
_TIKTOKEN_TRIED = False


def _get_tiktoken_encoding():
    global _TIKTOKEN_ENCODING, _TIKTOKEN_TRIED
    if not _TIKTOKEN_TRIED:
        _TIKTOKEN_TRIED = True
        try:
            import tiktoken

            _TIKTOKEN_ENCODING = tiktoken.get_encoding("o200k_base")
        except Exception:
            _TIKTOKEN_ENCODING = None
    return _TIKTOKEN_ENCODING


def tokenizer_name() -> str:
    return "tiktoken o200k_base" if _get_tiktoken_encoding() is not None else "estimate (words x 1.33; tiktoken unavailable)"


def real_token_count(text: str) -> int:
    """Real o200k token count via tiktoken; falls back to a words*1.33
    estimate if tiktoken is not installed."""
    enc = _get_tiktoken_encoding()
    if enc is None:
        return round(len((text or "").split()) * 1.33)
    return len(enc.encode(text))


def real_slice_by_tokens(text: str, token_budget: int) -> str:
    """Line-safe cut of the first `token_budget` REAL tokens (tiktoken
    o200k_base), or an equivalent word-based cut if tiktoken is unavailable.
    Tokenizes line by line (not the whole text at once) so this stays fast on
    long haystacks."""
    enc = _get_tiktoken_encoding()
    lines = (text or "").splitlines(keepends=True)
    out_lines: List[str] = []
    count = 0
    for line in lines:
        n = len(enc.encode(line)) if enc is not None else round(len(line.split()) * 1.33)
        if count + n > token_budget and out_lines:
            break
        out_lines.append(line)
        count += n
        if count >= token_budget:
            break
    return "".join(out_lines)


# ---------------------------------------------------------------------------
# Provider probing (no secrets ever printed)
# ---------------------------------------------------------------------------

def probe_providers() -> Dict[str, bool]:
    """Return {provider_id: available} based on presence of the documented
    environment variable, or a saved credential in ~/.pi/agent/auth.json.
    Never reads or returns the secret value itself."""
    available = {}
    auth_providers = set()
    auth_path = PI_AGENT_DIR / "auth.json"
    if auth_path.exists():
        try:
            auth = json.loads(auth_path.read_text(encoding="utf-8"))
            if isinstance(auth, dict):
                auth_providers = set(auth.keys())
        except Exception:
            pass
    for provider, env_var in ENV_VAR_BY_PROVIDER.items():
        available[provider] = bool(os.environ.get(env_var)) or provider in auth_providers
    # openai-codex has no API-key env var (it authenticates via `pi` -> `/login`);
    # report it as available whenever a saved credential for it exists.
    available["openai-codex"] = "openai-codex" in auth_providers
    return available


# ---------------------------------------------------------------------------
# Running pi non-interactively
# ---------------------------------------------------------------------------

class RunResult:
    def __init__(self):
        self.ok = False
        self.answer_text = ""
        self.usage: Dict = {}          # last assistant turn's usage
        self.total_cost_usd: float = 0.0
        self.compactions: List[dict] = []
        self.error: Optional[str] = None
        self.wall_time_s: float = 0.0
        self.raw_events_path: Optional[str] = None
        self.events: List[dict] = []
        self.exit_code: Optional[int] = None
        self.model: str = ""

    def to_json(self) -> dict:
        return {
            "ok": self.ok,
            "answer_text": self.answer_text,
            "usage": self.usage,
            "total_cost_usd": round(self.total_cost_usd, 6),
            "compactions": self.compactions,
            "error": self.error,
            "wall_time_s": round(self.wall_time_s, 2),
            "raw_events_path": self.raw_events_path,
            "exit_code": self.exit_code,
            "model": self.model,
        }


_AUTH_HINT = (
    " Hint: run `pi` then `/login` to authenticate the ChatGPT/Codex subscription provider "
    "and pass --model openai-codex/gpt-5.6-luna, or set OPENAI_API_KEY and use the default "
    "--model openai/gpt-5.6-luna."
)
_AUTH_ERROR_KEYWORDS = (
    "no credits", "insufficient balance", "unauthorized", "401", "403", "not found", "404",
    "no longer available", "authentication", "auth", "login", "api key", "credential",
)


def _with_auth_hint(result: "RunResult") -> "RunResult":
    """If a run failed with what looks like an auth or model-not-found error, append one
    clear, actionable hint line (login, or the API-key path)."""
    if not result.ok and result.error:
        low = result.error.lower()
        if any(kw in low for kw in _AUTH_ERROR_KEYWORDS) and _AUTH_HINT.strip() not in result.error:
            result.error = result.error + _AUTH_HINT
    return result


def run_pi(
    prompt: str,
    cwd: str,
    model: str = DEFAULT_MODEL,
    tools: Optional[str] = None,
    no_tools: bool = False,
    stdin_text: Optional[str] = None,
    session_dir: Optional[str] = None,
    raw_events_path: Optional[str] = None,
    timeout: int = 900,
    approve: bool = True,
    extra_args: Optional[List[str]] = None,
    thinking: Optional[str] = "low",
    no_context_files: bool = False,
) -> RunResult:
    """Run pi once, non-interactively, via `pi --mode json`, and parse the
    resulting JSON-lines event stream.

    `--mode json` merges piped stdin into the initial prompt exactly like a
    trailing message argument: a piped file's text is concatenated in front
    of the prompt argument. We use `--mode json` everywhere in this studio so
    usage, answers, and compaction events can all be read from one
    structured stream instead of a plain-text reply.
    """
    result = RunResult()
    result.model = model
    args = ["pi", "--mode", "json", "--model", model]
    if no_tools:
        args += ["--no-tools"]
    elif tools:
        args += ["--tools", tools]
    if session_dir:
        args += ["--session-dir", session_dir]
    if approve:
        args += ["--approve"]
    if thinking:
        args += ["--thinking", thinking]
    if no_context_files:
        # Suppress pi's AGENTS.md/CLAUDE.md parent-directory walk, so a run's
        # token accounting and behavior reflect only what this script itself
        # supplies, regardless of what unrelated AGENTS.md/CLAUDE.md files
        # might exist above the repo root on whichever machine this runs on.
        args += ["--no-context-files"]
    if extra_args:
        args += extra_args

    # Linux caps a single argv entry at ~128KB (MAX_ARG_STRLEN), well below the
    # overall ARG_MAX for the whole argv+environ. A large haystack passed as
    # the prompt argument can exceed that per-argument cap even though the
    # total is tiny. If the caller did not already route bulk text through
    # stdin_text, do it here automatically: `pi` merges piped stdin with the
    # prompt argument (concatenated directly, no inserted separator), so the
    # full text is preserved either way.
    MAX_ARG_BYTES = 100_000
    if stdin_text is None and len(prompt.encode("utf-8", errors="ignore")) > MAX_ARG_BYTES:
        stdin_text = prompt + "\n\n"
        prompt = "(continue with the text and instructions given above on stdin)"

    args += ["--", prompt]

    os.makedirs(cwd, exist_ok=True)

    start = time.time()
    try:
        proc = subprocess.run(
            args,
            cwd=cwd,
            input=stdin_text,
            capture_output=True,
            text=True,
            timeout=timeout,
        )
    except subprocess.TimeoutExpired as e:
        result.wall_time_s = time.time() - start
        result.error = f"pi timed out after {timeout}s"
        result.ok = False
        stdout = e.stdout or ""
        if raw_events_path:
            Path(raw_events_path).parent.mkdir(parents=True, exist_ok=True)
            Path(raw_events_path).write_text(stdout, encoding="utf-8")
            result.raw_events_path = raw_events_path
        return _with_auth_hint(result)

    result.wall_time_s = time.time() - start
    result.exit_code = proc.returncode
    stdout = proc.stdout or ""

    if raw_events_path:
        Path(raw_events_path).parent.mkdir(parents=True, exist_ok=True)
        Path(raw_events_path).write_text(stdout, encoding="utf-8")
        result.raw_events_path = raw_events_path

    events = []
    for line in stdout.splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            events.append(json.loads(line))
        except json.JSONDecodeError:
            continue
    result.events = events

    # Pre-flight failures (e.g. unknown/deprecated model) come back as a single
    # bare `{"error": {...}}` object with no "type" field and no session stream.
    if len(events) == 1 and "error" in events[0] and "type" not in events[0]:
        err = events[0]["error"]
        result.error = err.get("message", str(err)) if isinstance(err, dict) else str(err)
        result.ok = False
        return _with_auth_hint(result)

    if not events:
        result.error = (
            f"pi produced no parseable JSON output (exit={proc.returncode}). "
            f"stderr: {proc.stderr.strip()[:2000]}"
        )
        result.ok = False
        return _with_auth_hint(result)

    assistant_ends = [e for e in events if e.get("type") == "message_end" and e.get("message", {}).get("role") == "assistant"]
    total_cost = 0.0
    last_usage = {}
    error_message = None
    for e in assistant_ends:
        msg = e.get("message", {})
        usage = msg.get("usage") or {}
        cost = usage.get("cost") or {}
        total_cost += cost.get("total", 0) or 0
        if usage:
            last_usage = usage
        if msg.get("stopReason") == "error":
            error_message = msg.get("errorMessage") or "pi reported an error stopReason"

    result.total_cost_usd = total_cost
    result.usage = last_usage

    for e in events:
        if e.get("type") in ("compaction_start", "compaction_end"):
            result.compactions.append(e)

    if assistant_ends:
        last_msg = assistant_ends[-1].get("message", {})
        text_parts = [c.get("text", "") for c in last_msg.get("content", []) if c.get("type") == "text"]
        result.answer_text = "\n".join(t for t in text_parts if t)

    if error_message:
        result.error = error_message
        result.ok = False
    elif proc.returncode != 0 and not result.answer_text:
        result.error = f"pi exited {proc.returncode} with no answer text. stderr: {proc.stderr.strip()[:2000]}"
        result.ok = False
    else:
        result.ok = True

    return _with_auth_hint(result)


# ---------------------------------------------------------------------------
# Answer parsing
# ---------------------------------------------------------------------------

_NUM_LINE_RE = re.compile(r"^\s*\**\s*(?:Q)?(\d{1,2})\s*[\.\):]\s*(.*)$")


def parse_numbered_answers(text: str, n: int = 20) -> Dict[int, str]:
    """Best-effort parse of '1. ...' / '1) ...' / '**1.** ...' style numbered
    answers, one per question, allowing multi-line continuations until the
    next numbered line.

    A model's answer to one question can itself contain a nested numbered
    list (e.g. answer 5 enumerating "1. RAG 2. Memory Systems ..."). To avoid
    misreading that nested list as new top-level answers 1-4, a line only
    starts a new top-level answer if its number is exactly the next one
    expected in strict sequence (1, then 2, ... then n). Anything else --
    out-of-order, repeated, or past n -- is treated as continuation text of
    the current answer. The number group matches 1-2 digits, not 1, so ids
    past 9 are recognized correctly.
    """
    answers: Dict[int, List[str]] = {}
    current = None
    expected_next = 1
    for raw_line in text.splitlines():
        m = _NUM_LINE_RE.match(raw_line)
        if m and int(m.group(1)) == expected_next and expected_next <= n:
            current = expected_next
            answers[current] = [m.group(2).strip()]
            expected_next += 1
            continue
        if current is not None and raw_line.strip():
            answers[current].append(raw_line.strip())
    return {k: " ".join(v).strip() for k, v in answers.items()}


# ---------------------------------------------------------------------------
# Small formatting/IO helpers shared by part_a/b/c
# ---------------------------------------------------------------------------

def md_table(headers: List[str], rows: List[List[str]]) -> str:
    lines = ["| " + " | ".join(headers) + " |", "| " + " | ".join(["---"] * len(headers)) + " |"]
    for row in rows:
        lines.append("| " + " | ".join(str(c) for c in row) + " |")
    return "\n".join(lines)


def write_json(path: str, obj: dict) -> None:
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    Path(path).write_text(json.dumps(obj, indent=2), encoding="utf-8")


def write_text(path: str, text: str) -> None:
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    Path(path).write_text(text, encoding="utf-8")


# ---------------------------------------------------------------------------
# CLI: one diagnostic subcommand, used by setup.sh
# ---------------------------------------------------------------------------

def _cli_probe_providers(argv):
    available = probe_providers()
    print("Providers pi can currently use (API-key based; subscription providers like "
          "openai-codex need `pi` then `/login` interactively):")
    for provider, ok in sorted(available.items()):
        env_var = ENV_VAR_BY_PROVIDER.get(provider, "(no API-key env var; uses `pi /login`)")
        status = "available" if ok else "not configured"
        print(f"  {provider:14s} {status} ({env_var})")


if __name__ == "__main__":
    if len(sys.argv) < 2 or sys.argv[1] != "probe-providers":
        print(__doc__)
        sys.exit(1)
    _cli_probe_providers(sys.argv[2:])
