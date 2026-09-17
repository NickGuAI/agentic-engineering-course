#!/usr/bin/env python3
"""lib/pi_runner.py -- shared helpers for Studio 02 (Context Window Stress Test & Memory Architecture).

Used two ways:
  1. Imported by part_a_stress.py, part_b_isolate_compress.py, part_c_memory.py,
     and context_sweep.py (contract addendum v2).
  2. Called directly by setup.sh for corpus building and provider probing:
       python3 lib/pi_runner.py split-sections <src.txt> <out_dir> [words_per_section]
       python3 lib/pi_runner.py corpus-stats <src.txt> <sections_dir>
       python3 lib/pi_runner.py probe-providers
       python3 lib/pi_runner.py build-combined-corpus <corpus_dir> <combined.txt> <manifest.json>

Python 3.9+, standard library only EXCEPT real-token counting (real_token_count,
real_slice_by_tokens), which uses tiktoken if installed and otherwise falls back
to the words*1.33 estimate -- every function that needs it degrades safely, so
this module still imports and the estimate-only functions still work without
tiktoken. Never prints or returns secret values -- only whether an environment
variable/auth entry is present.
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

# Default model (contract addendum v2 section 1, hard rule): the Codex
# SUBSCRIPTION provider only, via pi's openai-codex provider (already logged
# in via OAuth on this machine; never an API key, never /login from these
# scripts). This is the model every run of real evidence in evidence/ and
# evidence/context_sweep/ actually used, with --thinking low. An earlier round
# of this studio (before the addendum) defaulted to the Codex "spark" model,
# openai-codex/gpt-5.3-codex-spark, and separately validated
# google/gemini-3.1-flash-lite as an API-key fallback; VALIDATED_FALLBACK_MODEL
# below still points at that fallback for the auth-hint message, since a
# student without Codex access needs *some* working suggestion.
DEFAULT_MODEL = "openai-codex/gpt-5.6-luna"
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
    ("openai-codex", "gpt-5.6-luna"): 272000,
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


def split_into_sections_by_real_tokens(src_path: str, out_dir: str, tokens_per_section: int = 30000) -> List[str]:
    """Same as split_into_sections, but chunks by REAL tokens (tiktoken
    o200k_base) instead of words -- used to split corpus/combined.txt for
    Part B (contract addendum v2 section 7: ~30K-token sections instead of
    the original ~12,000-word sections of the single-document survey)."""
    src = Path(src_path)
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)

    enc = _get_tiktoken_encoding()
    lines = src.read_text(encoding="utf-8", errors="replace").splitlines(keepends=True)

    sections: List[List[str]] = []
    current: List[str] = []
    current_tokens = 0
    for line in lines:
        current.append(line)
        current_tokens += len(enc.encode(line)) if enc else round(len(line.split()) * TOKENS_PER_WORD)
        if current_tokens >= tokens_per_section:
            sections.append(current)
            current = []
            current_tokens = 0
    if current:
        sections.append(current)

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


# ---------------------------------------------------------------------------
# Real tokenization (tiktoken o200k_base) -- contract addendum v2 section 3.
# Falls back to the words*1.33 estimate above only if tiktoken is not
# installed, so these are safe to call unconditionally.
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
    """Real o200k token count via tiktoken; falls back to the words*1.33
    estimate if tiktoken is not installed for this user."""
    enc = _get_tiktoken_encoding()
    if enc is None:
        return estimate_tokens(text)
    return len(enc.encode(text))


def real_slice_by_tokens(text: str, token_budget: int) -> str:
    """Line-safe cut of the first `token_budget` REAL tokens (tiktoken
    o200k_base). Falls back to the word-based slice_by_tokens() above if
    tiktoken is unavailable. Tokenizes line by line (not the whole text at
    once) so this stays fast on a ~600K-token combined corpus."""
    enc = _get_tiktoken_encoding()
    if enc is None:
        return slice_by_tokens(text, token_budget)
    lines = text.splitlines(keepends=True)
    out_lines: List[str] = []
    count = 0
    for line in lines:
        n = len(enc.encode(line))
        if count + n > token_budget and out_lines:
            break
        out_lines.append(line)
        count += n
        if count >= token_budget:
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


# ---------------------------------------------------------------------------
# Corpus v2: the 13-document, ~579K-token combined corpus (contract addendum
# v2 section 2). Document 1 is the original survey; documents 2-13 are noise/
# context-engineering-adjacent papers used only as bulk length and distractor
# content past the survey's own facts.
# ---------------------------------------------------------------------------

CORPUS_V2_DOCUMENTS = [
    {"n": 1, "id": "2507.13334", "title": "A Survey of Context Engineering for LLMs (Mei 2025)"},
    {"n": 2, "id": "2307.03172", "title": "Lost in the Middle (Liu 2023)"},
    {"n": 3, "id": "2310.08560", "title": "MemGPT (Packer 2023)"},
    {"n": 4, "id": "2510.04618", "title": "ACE: Agentic Context Engineering (Zhang 2025)"},
    {"n": 5, "id": "2404.06654", "title": "RULER (Hsieh 2024)"},
    {"n": 6, "id": "2410.10813", "title": "LongMemEval (Wu 2024)"},
    {"n": 7, "id": "2210.03629", "title": "ReAct (Yao 2022)"},
    {"n": 8, "id": "2005.11401", "title": "RAG (Lewis 2020)"},
    {"n": 9, "id": "2304.03442", "title": "Generative Agents (Park 2023)"},
    {"n": 10, "id": "2502.05167", "title": "NoLiMa (Modarressi 2025)"},
    {"n": 11, "id": "2504.19413", "title": "Mem0 (2025)"},
    {"n": 12, "id": "2005.14165", "title": "GPT-3 (Brown 2020)"},
    {"n": 13, "id": "2403.05530", "title": "Gemini 1.5 technical report (2024)"},
]


def corpus_v2_doc_header(n: int, title: str, arxiv_id: str) -> str:
    return f"===== DOCUMENT {n}: {title} (arXiv {arxiv_id}) =====\n"


def build_combined_corpus(corpus_dir: str, combined_path: str, manifest_path: str) -> dict:
    """Concatenate CORPUS_V2_DOCUMENTS's already-converted text files into
    combined_path, one header line (corpus_v2_doc_header) before each
    document's text, and write manifest_path recording order, id, title,
    words, real tokens, and the cumulative REAL-token offset where each
    document (its header included) starts in combined.txt. Document 1 reads
    <corpus_dir>/survey.txt if <corpus_dir>/2507.13334.txt is absent (the
    already-converted copy from the single-document setup). Raises
    FileNotFoundError naming the missing document if any converted .txt is
    absent -- run setup.sh's download/convert step first."""
    corpus_dir_path = Path(corpus_dir)
    entries = []
    combined_parts = []
    cumulative = 0
    sep = "\n\n"
    sep_tokens = real_token_count(sep)

    for doc in CORPUS_V2_DOCUMENTS:
        txt_path = corpus_dir_path / f"{doc['id']}.txt"
        if not txt_path.exists() and doc["n"] == 1:
            txt_path = corpus_dir_path / "survey.txt"
        if not txt_path.exists():
            raise FileNotFoundError(
                f"Missing converted text for document {doc['n']} ({doc['id']} -- {doc['title']}): "
                f"expected {txt_path}. Run setup.sh's corpus download/convert step first."
            )
        text = txt_path.read_text(encoding="utf-8", errors="replace")
        header = corpus_v2_doc_header(doc["n"], doc["title"], doc["id"])
        header_tokens = real_token_count(header)
        doc_tokens = real_token_count(text)

        entries.append({
            "n": doc["n"],
            "id": doc["id"],
            "title": doc["title"],
            "words": word_count(text),
            "tokens": doc_tokens,
            "cumulative_start": cumulative,
        })
        combined_parts.append(header)
        combined_parts.append(text)
        combined_parts.append(sep)
        cumulative += header_tokens + doc_tokens + sep_tokens

    combined_text = "".join(combined_parts)
    Path(combined_path).parent.mkdir(parents=True, exist_ok=True)
    Path(combined_path).write_text(combined_text, encoding="utf-8")

    manifest = {
        "documents": entries,
        "total_words": sum(e["words"] for e in entries),
        "total_tokens_sum": sum(e["tokens"] for e in entries),
        "combined_real_tokens": real_token_count(combined_text),
        "tokenizer": tokenizer_name(),
    }
    Path(manifest_path).parent.mkdir(parents=True, exist_ok=True)
    Path(manifest_path).write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    return manifest


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

_NUM_LINE_RE = re.compile(r"^\s*\**\s*(?:Q)?(\d{1,2})\s*[\.\):]\s*(.*)$")


def parse_numbered_answers(text: str, n: int = 20) -> Dict[int, str]:
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

    The number group matches 1-2 digits (`\\d{1,2}`), not 1 (observed in a
    real 20-question sweep run: answers 10-20 were never recognized as
    top-level answers at all with a single-digit pattern, and were silently
    swallowed as continuation text of answer 9 -- every one of them was
    actually correct and got scored wrong). `n` defaults to 20, the current
    question count, but every caller should still pass n=len(questions)
    explicitly rather than rely on the default.
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


def _normalize_for_match(text: str) -> str:
    """Lowercase and strip thousands-separator commas, so '2,048K' matches
    '2048K' and all keyword/must_not_contain matching is both case- and
    comma-insensitive. Applied to both sides of every substring check."""
    return (text or "").lower().replace(",", "")


# (question_id, group_index) pairs already logged as non-discriminative, so a
# question scored at every sweep size only logs the skip once, not per size.
_LOGGED_NON_DISCRIMINATIVE = set()


def score_answer(
    answer_text: str,
    keywords_any: List[List[str]],
    question_text: str = "",
    question_id=None,
) -> bool:
    """True if every DISCRIMINATIVE group in keywords_any has at least one
    keyword present in answer_text as a normalized (lowercased, comma-
    stripped) substring. A group is skipped -- never required -- when every
    one of its keywords already appears (same normalization) in
    question_text: such a group cannot distinguish a real answer from an
    echo of the question itself (e.g. a keyword group of just "LongRoPE" for
    a question that already says "LongRoPE"). Each skip is logged once per
    (question_id, group). question_text/question_id are optional so this
    stays backward compatible with callers that only have the keyword list."""
    if not answer_text:
        return False
    haystack = _normalize_for_match(answer_text)
    norm_question = _normalize_for_match(question_text)
    for group_index, group in enumerate(keywords_any):
        if norm_question and all(_normalize_for_match(kw) in norm_question for kw in group):
            log_key = (question_id, group_index)
            if log_key not in _LOGGED_NON_DISCRIMINATIVE:
                _LOGGED_NON_DISCRIMINATIVE.add(log_key)
                print(
                    f"  [scoring] non-discriminative group skipped for question {question_id}: "
                    f"{group} (already present in the question text)",
                    file=sys.stderr,
                )
            continue
        if not any(_normalize_for_match(kw) in haystack for kw in group):
            return False
    return True


def score_all(answers_by_num: Dict[int, str], questions: List[dict]) -> Tuple[int, List[int]]:
    """Return (score 0-len(questions), list of question ids that were wrong or missing)."""
    score = 0
    wrong_or_missing = []
    for q in questions:
        qid = q["id"]
        ans = answers_by_num.get(qid, "")
        if ans and score_answer(ans, q["keywords_any"], question_text=q.get("question", ""), question_id=qid):
            score += 1
        else:
            wrong_or_missing.append(qid)
    return score, wrong_or_missing


# ---------------------------------------------------------------------------
# Scoring v2 -- contract addendum v2 section 5. Handles the 20-question schema
# (needle_depth_tokens, expect_not_found, must_not_contain) but degrades
# safely for the original 5-question schema, which has none of those fields:
# a question with no needle_depth_tokens and no expect_not_found is always
# "answerable"/in_slice, matching the original part_a_stress.py behavior.
# ---------------------------------------------------------------------------

# Sizes used by context_sweep.py (real-token budgets; "full" is the whole
# combined corpus, handled specially by the caller, not listed here).
SWEEP_SIZE_TOKENS = {
    "16k": 16000,
    "32k": 32000,
    "64k": 64000,
    "128k": 128000,
    "200k": 200000,
    "256k": 256000,
}

_NOT_FOUND_RE = re.compile(r"\bnot\s+found\b", re.IGNORECASE)


def expected_verdict(question: dict, slice_real_tokens: int) -> str:
    """'not_found' if the question is marked expect_not_found, or its needle
    sits at or beyond this slice's real-token budget; else 'answerable'."""
    if question.get("expect_not_found"):
        return "not_found"
    depth = question.get("needle_depth_tokens")
    if depth is not None and depth >= slice_real_tokens:
        return "not_found"
    return "answerable"


def score_question_v2(answer_text: str, question: dict, slice_real_tokens: int) -> dict:
    """Score one question's answer at one slice size against the section-5
    rule. verdict is one of 'correct' / 'wrong' / 'hallucinated' (hallucinated
    = confidently answered when the correct behavior was NOT FOUND)."""
    expected = expected_verdict(question, slice_real_tokens)
    depth = question.get("needle_depth_tokens")
    in_slice = (not question.get("expect_not_found")) and (depth is None or depth < slice_real_tokens)
    said_not_found = bool(_NOT_FOUND_RE.search(answer_text or ""))
    haystack = _normalize_for_match(answer_text)
    must_not_contain = question.get("must_not_contain") or []
    must_not_contain_hit = any(_normalize_for_match(kw) in haystack for kw in must_not_contain)
    keyword_groups = question.get("keywords_any") or []
    keyword_match = (
        score_answer(
            answer_text, keyword_groups,
            question_text=question.get("question", ""), question_id=question.get("id"),
        )
        if keyword_groups else False
    )
    # "Verbose-but-correct": every gold keyword group matched, but the answer
    # also contains a must_not_contain distractor term (e.g. it correctly says
    # 8,192 but also mentions the nearby 128,000 in passing). Scored as wrong
    # per the section-5 rule either way -- this flag exists only so a human can
    # re-score these by hand; it never changes `correct` or `verdict` below.
    verbose_but_correct = bool(keyword_groups) and keyword_match and must_not_contain_hit

    if expected == "not_found":
        correct = said_not_found and not must_not_contain_hit
        verdict = "correct" if correct else "hallucinated"
    else:
        correct = keyword_match and not must_not_contain_hit
        verdict = "correct" if correct else "wrong"

    return {
        "id": question.get("id"),
        "needle_depth_tokens": depth,
        "expected": expected,
        "in_slice": in_slice,
        "answer": answer_text,
        "said_not_found": said_not_found,
        "keyword_match": keyword_match,
        "must_not_contain_hit": must_not_contain_hit,
        "verbose_but_correct": verbose_but_correct,
        "correct": correct,
        "verdict": verdict,
    }


def score_all_v2(answers_by_num: Dict[int, str], questions: List[dict], slice_real_tokens: int) -> dict:
    """Score every question at one slice size. Returns per-question results
    plus the three headline accuracies from section 5: overall (of all
    questions), in-slice/answerable, and abstention (out-of-slice or
    expect_not_found). An accuracy is None when its question group is empty."""
    per_question = []
    for q in questions:
        ans = answers_by_num.get(q["id"], "")
        per_question.append(score_question_v2(ans, q, slice_real_tokens))

    n_total = len(per_question)
    n_correct = sum(1 for r in per_question if r["correct"])
    answerable = [r for r in per_question if r["expected"] == "answerable"]
    not_found_expected = [r for r in per_question if r["expected"] == "not_found"]

    def _acc(rows):
        return (sum(1 for r in rows if r["correct"]) / len(rows)) if rows else None

    return {
        "per_question": per_question,
        "overall_accuracy": (n_correct / n_total) if n_total else 0.0,
        "in_slice_accuracy": _acc(answerable),
        "abstention_accuracy": _acc(not_found_expected),
        "n_total": n_total,
        "n_answerable": len(answerable),
        "n_not_found_expected": len(not_found_expected),
        "in_slice_ids": [r["id"] for r in per_question if r["in_slice"]],
        "verbose_but_correct_ids": [r["id"] for r in per_question if r["verbose_but_correct"]],
    }


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
# Comprehension check label parsing (contract addendum v3) -- comprehension_check.py
# ---------------------------------------------------------------------------

COMPREHENSION_LABELS = ("SUPPORTED", "CONTRADICTED", "NOT_FOUND")

# Matches "<n>. LABEL - justification" (1-2 digit id; SUPPORTED / CONTRADICTED /
# "NOT FOUND" / "NOT_FOUND", case-insensitive; the "- justification" tail is
# optional and, if present, may itself start with any punctuation).
_LABEL_LINE_RE = re.compile(
    r"^\s*\**\s*(?:Q)?(\d{1,2})\s*[\.\):]\s*"
    r"(SUPPORTED|CONTRADICTED|NOT[\s_]FOUND)\b"
    r"\s*[-:–—]?\s*(.*)$",
    re.IGNORECASE,
)


def _canonical_label(raw: str) -> str:
    return "NOT_FOUND" if re.match(r"NOT[\s_]FOUND", raw, re.IGNORECASE) else raw.upper()


def parse_labeled_lines(text: str, n: int = 20) -> Dict[int, Dict[str, str]]:
    """Parse '<n>. SUPPORTED|CONTRADICTED|NOT FOUND|NOT_FOUND - justification'
    lines, one per comprehension item, tolerating a 1-2 digit id and an
    optional trailing justification. Same strict-sequence rule as
    parse_numbered_answers (a line only starts a new item if its id is
    exactly the next one expected), so a justification sentence that itself
    contains "... 2. ..." style text cannot be misread as a new item.
    Returns {id: {"label": "SUPPORTED"|"CONTRADICTED"|"NOT_FOUND"|None,
    "justification": str, "raw": str}}; label is None if a line matched the
    id but not a recognized label word (raw still captured for debugging)."""
    items: Dict[int, Dict[str, List[str]]] = {}
    current = None
    expected_next = 1
    for raw_line in text.splitlines():
        m = _LABEL_LINE_RE.match(raw_line)
        if m and int(m.group(1)) == expected_next and expected_next <= n:
            current = expected_next
            label = _canonical_label(m.group(2))
            items[current] = {
                "label": label if label in COMPREHENSION_LABELS else None,
                "justification": [m.group(3).strip()],
                "raw": [raw_line.strip()],
            }
            expected_next += 1
            continue
        if current is not None and raw_line.strip():
            items[current]["justification"].append(raw_line.strip())
            items[current]["raw"].append(raw_line.strip())
    return {
        k: {
            "label": v["label"],
            "justification": " ".join(v["justification"]).strip(),
            "raw": " ".join(v["raw"]).strip(),
        }
        for k, v in items.items()
    }


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


def _cli_split_sections_real_tokens(argv):
    src, out_dir = argv[0], argv[1]
    tokens = int(argv[2]) if len(argv) > 2 else 30000
    paths = split_into_sections_by_real_tokens(src, out_dir, tokens)
    print(f"Wrote {len(paths)} section files to {out_dir} (~{tokens} real tokens each, {tokenizer_name()}):")
    for p in paths:
        text = Path(p).read_text(encoding="utf-8", errors="replace")
        print(f"  {p}: {word_count(text)} words (~{real_token_count(text)} real tokens)")


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


def _cli_build_combined_corpus(argv):
    corpus_dir, combined_path, manifest_path = argv[0], argv[1], argv[2]
    manifest = build_combined_corpus(corpus_dir, combined_path, manifest_path)
    print(
        f"{combined_path}: {manifest['total_words']} words, {manifest['total_tokens_sum']} tokens "
        f"summed per document, {manifest['combined_real_tokens']} real tokens measured on the whole "
        f"file (tokenizer: {manifest['tokenizer']})"
    )
    print(f"{manifest_path} written. Documents:")
    for e in manifest["documents"]:
        print(f"  {e['n']:>2} | {e['id']:>11} | {e['tokens']:>7} tok | start={e['cumulative_start']:>7} | {e['title']}")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)
    cmd, rest = sys.argv[1], sys.argv[2:]
    if cmd == "split-sections":
        _cli_split_sections(rest)
    elif cmd == "split-sections-real-tokens":
        _cli_split_sections_real_tokens(rest)
    elif cmd == "corpus-stats":
        _cli_corpus_stats(rest)
    elif cmd == "probe-providers":
        _cli_probe_providers(rest)
    elif cmd == "build-combined-corpus":
        _cli_build_combined_corpus(rest)
    else:
        print(f"Unknown command: {cmd}", file=sys.stderr)
        sys.exit(1)
