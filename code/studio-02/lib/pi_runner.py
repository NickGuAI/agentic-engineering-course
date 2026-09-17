#!/usr/bin/env python3
"""lib/pi_runner.py -- shared helpers for Studio 02 (Context Window Stress Test & Memory Architecture).

Used two ways:
  1. Imported by part_a_stress.py, part_b_isolate_compress.py, and part_c_memory.py.
  2. Called directly by setup.sh for corpus splitting and provider probing:
       python3 lib/pi_runner.py split-sections <src.txt> <out_dir> [words_per_section]
       python3 lib/pi_runner.py corpus-stats <src.txt> <sections_dir>
       python3 lib/pi_runner.py probe-providers

Python 3.9+, standard library only. Never prints or returns secret values -- only
whether an environment variable/auth entry is present.
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

# Word-to-token estimate used throughout the studio (no tiktoken on this machine;
# pi's own reported usage is the real number whenever a run actually executes).
TOKENS_PER_WORD = 1.33

# Default model: the contract asks for the Codex spark model if it exists in pi's
# catalog. It does (confirmed both under openai-codex and under the plain openai
# API-key provider; see README.md "How we chose a model"). This default is UNTESTED
# on the validation machine, which has no Codex login and an exhausted quota; every
# run of real evidence in evidence/ actually used the validated fallback,
# google/gemini-3.1-flash-lite. Pass --model google/gemini-3.1-flash-lite explicitly
# if you hit an auth or model-not-found error with the default.
DEFAULT_MODEL = "openai-codex/gpt-5.3-codex-spark"
VALIDATED_FALLBACK_MODEL = "google/gemini-3.1-flash-lite"

# Environment variable pi reads for each provider's API key (from providers.md).
# Only used to check *presence*, never to read or print the value.
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

# Fallback context windows (tokens) for models we know we might use, in case
# ~/.pi/agent/models-store.json is not present (e.g. `pi update --models` was
# never run). Real runs should prefer the live catalog; see model_context_window().
KNOWN_CONTEXT_WINDOWS = {
    ("google", "gemini-3.1-flash-lite"): 1048576,
    ("google", "gemini-2.5-flash"): 1048576,
    ("google", "gemini-3.5-flash-lite"): 1048576,
    ("openai", "gpt-5-nano"): 400000,
    ("deepseek", "deepseek-flash"): 1000000,
    ("openai-codex", "gpt-5.3-codex-spark"): 128000,
    ("openai", "gpt-5.3-codex-spark"): 128000,
}

PI_AGENT_DIR = Path(os.environ.get("PI_CODING_AGENT_DIR", str(Path.home() / ".pi" / "agent")))


# ---------------------------------------------------------------------------
# Token / word estimation
# ---------------------------------------------------------------------------

def word_count(text: str) -> int:
    return len(text.split())


def estimate_tokens(text: str) -> int:
    """words * 1.33, rounded. Used for planning/reporting only; real runs use
    pi's own reported usage numbers."""
    return round(word_count(text) * TOKENS_PER_WORD)


def words_for_token_budget(token_budget: int) -> int:
    return max(1, round(token_budget / TOKENS_PER_WORD))


# ---------------------------------------------------------------------------
# Corpus splitting (used by setup.sh)
# ---------------------------------------------------------------------------

def split_into_sections(src_path: str, out_dir: str, words_per_section: int = 12000) -> List[str]:
    """Split src_path into out_dir/section-NN.txt files of ~words_per_section words
    each, in document order, splitting only on line boundaries so no line of the
    source is ever broken mid-word. Re-runnable: overwrites existing section files
    and removes stale ones from a previous run with a different section count."""
    src = Path(src_path)
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)

    lines = src.read_text(encoding="utf-8", errors="replace").splitlines(keepends=True)

    sections: List[List[str]] = []
    current: List[str] = []
    current_words = 0
    for line in lines:
        current.append(line)
        current_words += len(line.split())
        if current_words >= words_per_section:
            sections.append(current)
            current = []
            current_words = 0
    if current:
        sections.append(current)

    # Clear previously written section files so re-running with a different
    # chunk size does not leave stale extra files behind.
    for old in out.glob("section-*.txt"):
        old.unlink()

    written = []
    for i, sec_lines in enumerate(sections, start=1):
        path = out / f"section-{i:02d}.txt"
        path.write_text("".join(sec_lines), encoding="utf-8")
        written.append(str(path))
    return written


def slice_by_tokens(text: str, token_budget: int) -> str:
    """Return the first `token_budget` estimated tokens of text (word-based,
    line-safe cut)."""
    target_words = words_for_token_budget(token_budget)
    lines = text.splitlines(keepends=True)
    out_lines: List[str] = []
    count = 0
    for line in lines:
        w = len(line.split())
        if count + w > target_words and out_lines:
            break
        out_lines.append(line)
        count += w
        if count >= target_words:
            break
    return "".join(out_lines)


def build_distractor_padded_corpus(full_text: str, sections_dir: str, multiplier: int, seed: int = 42) -> str:
    """Full corpus followed by (multiplier - 1) rounds of its own section files,
    each round re-shuffled into a different order, appended as distractor
    padding. Used for the optional 2x/3x stress sizes: models with a huge
    context window (well past "full") can still be pushed toward degradation
    or overflow by padding with more (already-seen, shuffled) text rather than
    more corpus. Deterministic for a given seed, so repeats are comparable."""
    import random

    sections = sorted(Path(sections_dir).glob("section-*.txt"))
    texts = [p.read_text(encoding="utf-8", errors="replace") for p in sections]
    rng = random.Random(seed)
    parts = [full_text]
    for round_i in range(max(0, multiplier - 1)):
        order = list(range(len(texts)))
        rng.shuffle(order)
        parts.append(
            f"\n\n[Distractor padding, round {round_i + 1}, sections reshuffled]\n\n"
            + "\n\n".join(texts[i] for i in order)
        )
    return "".join(parts)


SIZE_TOKEN_BUDGETS = {
    "8k": 8000,
    "16k": 16000,
    "32k": 32000,
    "64k": 64000,
    # "full" handled specially: the entire corpus text, no slicing.
}


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
    return available


def model_context_window(provider: str, model_id: str) -> Optional[int]:
    """Look up a model's context window from ~/.pi/agent/models-store.json
    (written by `pi update --models`), falling back to KNOWN_CONTEXT_WINDOWS."""
    store_path = PI_AGENT_DIR / "models-store.json"
    if store_path.exists():
        try:
            store = json.loads(store_path.read_text(encoding="utf-8"))
            entry = store.get(provider)
            if entry:
                for m in entry.get("models", []):
                    if m.get("id") == model_id:
                        cw = m.get("contextWindow")
                        if isinstance(cw, int):
                            return cw
        except Exception:
            pass
    return KNOWN_CONTEXT_WINDOWS.get((provider, model_id))


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


def _split_provider_model(model: str) -> Tuple[str, str]:
    if "/" in model:
        provider, model_id = model.split("/", 1)
        return provider, model_id
    return "", model


_AUTH_HINT = (
    " Hint: run `pi` then `/login` to authenticate a subscription provider (e.g. ChatGPT/Codex "
    f"for the default spark model), or pass --model {VALIDATED_FALLBACK_MODEL} to use the "
    "validated fallback."
)
_AUTH_ERROR_KEYWORDS = (
    "no credits", "insufficient balance", "unauthorized", "401", "403", "not found", "404",
    "no longer available", "authentication", "auth", "login", "api key", "credential",
)


def _with_auth_hint(result: "RunResult") -> "RunResult":
    """If a run failed with what looks like an auth or model-not-found error, append one
    clear, actionable hint line (login, or fall back to the validated model)."""
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

    `--mode json` merges piped stdin into the initial prompt exactly like
    `-p` (verified directly on this machine: a piped file's text is
    concatenated in front of the prompt argument). We use `--mode json`
    everywhere in this studio so usage, answers, and compaction events can
    all be read from one structured stream instead of a plain-text reply.
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
        # Suppress pi's AGENTS.md/CLAUDE.md parent-directory walk. This machine has
        # unrelated personal AGENTS.md files above the repo root (~/AGENTS.md,
        # ~/PKMS/AGENTS.md) that would otherwise be injected into every run's system
        # prompt (confirmed by direct test: it changed model behavior, and once
        # leaked unrelated personal content into a Part C answer). Part A and Part B
        # pass this so their token accounting reflects only the corpus and
        # questions. Part C ALSO passes this, in every condition (with-memory,
        # no-memory, and every session in between), for reproducibility and
        # privacy; the with-memory condition still gets its AGENTS.md instructions
        # because part_c_memory.py passes the same text via --append-system-prompt
        # (see with_memory_extra_args there) instead of relying on this walk.
        args += ["--no-context-files"]
    if extra_args:
        args += extra_args

    # Linux caps a single argv entry at ~128KB (MAX_ARG_STRLEN), well below the
    # overall ARG_MAX for the whole argv+environ. A large corpus slice passed as
    # the prompt argument can exceed that per-argument cap even though the total
    # is tiny (observed directly: it failed at ~185KB). If the caller did not
    # already route bulk text through stdin_text, do it here automatically: `pi`
    # merges piped stdin with the prompt argument (verified: they are
    # concatenated directly with no inserted separator), so the full text is
    # preserved either way.
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
# Answer parsing and scoring
# ---------------------------------------------------------------------------

_NUM_LINE_RE = re.compile(r"^\s*\**\s*(?:Q)?(\d)\s*[\.\):]\s*(.*)$")


def parse_numbered_answers(text: str, n: int = 5) -> Dict[int, str]:
    """Best-effort parse of '1. ...' / '1) ...' / '**1.** ...' style numbered
    answers, one per question, allowing multi-line continuations until the
    next numbered line.

    A model's answer to one question can itself contain a nested numbered
    list (e.g. answer 5 enumerating "1. RAG 2. Memory Systems ..."). To avoid
    misreading that nested list as new top-level answers 1-4 (observed in a
    real run, which silently corrupted scoring), a line only starts a new
    top-level answer if its number is exactly the next one expected in
    strict sequence (1, then 2, ... then n). Anything else -- out-of-order,
    repeated, or past n -- is treated as continuation text of the current
    answer.
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


def score_answer(answer_text: str, keywords_any: List[List[str]]) -> bool:
    """True if every group in keywords_any has at least one keyword present
    in answer_text as a case-insensitive substring."""
    if not answer_text:
        return False
    haystack = answer_text.lower()
    for group in keywords_any:
        if not any(kw.lower() in haystack for kw in group):
            return False
    return True


def score_all(answers_by_num: Dict[int, str], questions: List[dict]) -> Tuple[int, List[int]]:
    """Return (score 0-len(questions), list of question ids that were wrong or missing)."""
    score = 0
    wrong_or_missing = []
    for q in questions:
        qid = q["id"]
        ans = answers_by_num.get(qid, "")
        if ans and score_answer(ans, q["keywords_any"]):
            score += 1
        else:
            wrong_or_missing.append(qid)
    return score, wrong_or_missing


def load_questions(path: str = "questions.json") -> dict:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def questions_block(questions: List[dict]) -> str:
    lines = []
    for q in questions:
        lines.append(f"{q['id']}. {q['question']}")
    return "\n".join(lines)


ANSWER_INSTRUCTIONS = (
    "Answer the five numbered questions from the text above only. "
    "Number your answers 1 to 5. If the text does not contain the answer, say NOT FOUND."
)


# ---------------------------------------------------------------------------
# Small formatting helpers shared by part_a/b/c for summary.md tables
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
# CLI dispatch for setup.sh
# ---------------------------------------------------------------------------

def _cli_split_sections(argv):
    src, out_dir = argv[0], argv[1]
    words = int(argv[2]) if len(argv) > 2 else 12000
    paths = split_into_sections(src, out_dir, words)
    print(f"Wrote {len(paths)} section files to {out_dir} (~{words} words each):")
    for p in paths:
        text = Path(p).read_text(encoding="utf-8", errors="replace")
        print(f"  {p}: {word_count(text)} words (~{estimate_tokens(text)} tokens)")


def _cli_corpus_stats(argv):
    src = argv[0]
    text = Path(src).read_text(encoding="utf-8", errors="replace")
    print(f"{src}: {word_count(text)} words (~{estimate_tokens(text)} estimated tokens)")
    if len(argv) > 1:
        sec_dir = Path(argv[1])
        for p in sorted(sec_dir.glob("section-*.txt")):
            t = p.read_text(encoding="utf-8", errors="replace")
            print(f"  {p.name}: {word_count(t)} words (~{estimate_tokens(t)} estimated tokens)")


def _cli_probe_providers(argv):
    available = probe_providers()
    print("Providers pi can currently use (API-key based; OAuth/subscription providers need `pi /login` interactively):")
    for provider, ok in sorted(available.items()):
        status = "available" if ok else "not configured"
        print(f"  {provider:12s} {status} (env var {ENV_VAR_BY_PROVIDER[provider]})")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)
    cmd, rest = sys.argv[1], sys.argv[2:]
    if cmd == "split-sections":
        _cli_split_sections(rest)
    elif cmd == "corpus-stats":
        _cli_corpus_stats(rest)
    elif cmd == "probe-providers":
        _cli_probe_providers(rest)
    else:
        print(f"Unknown command: {cmd}", file=sys.stderr)
        sys.exit(1)
