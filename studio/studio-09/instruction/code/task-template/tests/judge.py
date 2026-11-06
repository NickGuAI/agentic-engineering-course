"""One structured OpenAI call; scalar Harbor reward plus a detailed record."""

import hashlib
import json
import math
import time
from pathlib import Path

from openai import OpenAI

MODEL = "gpt-5.5"
CRITERIA = (
    "factual_accuracy", "citation_accuracy", "completeness",
    "source_quality", "tool_efficiency",
)
TESTS = Path("/tests")
LOGS = Path("/logs/verifier")
SCHEMA = {
    "type": "object",
    "properties": {
        "pass": {"type": "boolean"},
        "scores": {
            "type": "object",
            "properties": {key: {"type": "number", "minimum": 0, "maximum": 1} for key in CRITERIA},
            "required": list(CRITERIA),
            "additionalProperties": False,
        },
        "reason": {"type": "string"},
    },
    "required": ["pass", "scores", "reason"],
    "additionalProperties": False,
}


def validate(result: dict) -> None:
    if type(result.get("pass")) is not bool or not isinstance(result.get("reason"), str) or not result["reason"].strip():
        raise ValueError("Judge did not return a boolean pass and a reason")
    scores = result.get("scores", {})
    if set(scores) != set(CRITERIA):
        raise ValueError("Judge returned the wrong rubric criteria")
    for value in scores.values():
        if type(value) not in (int, float) or not math.isfinite(value) or not 0 <= value <= 1:
            raise ValueError("Judge scores must be finite numbers from 0 to 1")


def main() -> None:
    LOGS.mkdir(parents=True, exist_ok=True)
    start = time.monotonic()
    record = {"status": "error", "model": MODEL, "prompt_hash": None, "rubric_sha256": None}
    try:
        rubric_bytes = (TESTS / "rubric.md").read_bytes()
        record["rubric_sha256"] = hashlib.sha256(rubric_bytes).hexdigest()
        rubric = rubric_bytes.decode("utf-8")
        key = json.loads((TESTS / "answer.json").read_text())
        answer_path = Path("/app/answer.md")
        answer = answer_path.read_text() if answer_path.exists() else ""
        trace_path = Path("/app/trace.jsonl")
        trace = trace_path.read_text() if trace_path.exists() else ""
        # Bound the prompt explicitly rather than silently discarding evidence.
        if len(answer) > 100_000 or len(trace) > 200_000:
            raise ValueError("Answer or trace exceeds the starter judge's input limit")
        payload = json.dumps({
            "question": key["question"], "reference_answer": key["answer"],
            "pass_rule": key["pass_rule"], "reference_sources": key["sources"],
            "answer": answer, "trace": trace or None,
        }, ensure_ascii=False)
        request = {
            "model": MODEL,
            "instructions": rubric,
            "input": payload,
            "reasoning": {"effort": "none"},
            "temperature": 0,
            "text": {"format": {"type": "json_schema", "name": "research_judgment", "strict": True, "schema": SCHEMA}},
            "max_output_tokens": 1500,
            "store": False,
        }
        record.update({
            "question_id": key["id"],
            "prompt_hash": hashlib.sha256(json.dumps(request, sort_keys=True).encode()).hexdigest(),
            "settings": {"reasoning_effort": "none", "temperature": 0},
        })
        # Disable SDK retries: one request per trial, including when the API fails.
        response = OpenAI(max_retries=0, timeout=180).responses.create(**request)
        record["usage"] = response.usage.model_dump() if response.usage else None
        record["model"] = response.model
        record["response_id"] = response.id
        if response.status != "completed":
            raise ValueError("Judge response did not complete")
        result = json.loads(response.output_text)
        validate(result)
        unscored = []
        if not trace.strip():
            result["scores"]["tool_efficiency"] = 0.5
            unscored.append("tool_efficiency")
        # A judge can never pass a missing answer, even if it ignores the rubric.
        if not answer.strip():
            result["pass"] = False
        record.update(result, status="ok", unscored=unscored)
        record["wall_time_seconds"] = round(time.monotonic() - start, 3)
        (LOGS / "judge.json").write_text(json.dumps(record, indent=2) + "\n")
        (LOGS / "reward.txt").write_text("1\n" if result["pass"] else "0\n")
    except Exception as exc:
        # Error bodies may contain request data; record only the error type/status.
        record.update({"error_type": type(exc).__name__, "http_status": getattr(exc, "status_code", None),
                       "wall_time_seconds": round(time.monotonic() - start, 3)})
        (LOGS / "judge.json").write_text(json.dumps(record, indent=2) + "\n")
        raise RuntimeError(f"Judge failed ({type(exc).__name__}); see judge.json") from None


if __name__ == "__main__":
    main()
