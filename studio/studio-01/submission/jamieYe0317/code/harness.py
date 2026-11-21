"""Bounded orchestration and auditable completion for the research workflow.

This is an application supervisor, not an operating-system security boundary.
Callbacks own their work; all HTTP and model effects must use the reservations.
"""

import copy
import hashlib
import json
import math
import threading
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Dict, Optional


class HarnessError(ValueError):
    """A policy or state check rejected an operation before its next effect."""


@dataclass(frozen=True)
class Action:
    operation_id: str
    name: str
    arguments: dict


def canonical_json(value: Any) -> bytes:
    """The same manifest encoding is used when checking and finishing."""
    return json.dumps(value, sort_keys=True, separators=(",", ":"),
                      ensure_ascii=False, allow_nan=False).encode("utf-8")


def digest_hash(value: bytes) -> str:
    if not isinstance(value, bytes):
        raise HarnessError("digest must be bytes")
    return hashlib.sha256(value).hexdigest()


def manifest_hash(value: dict) -> str:
    if not isinstance(value, dict):
        raise HarnessError("manifest must be a dictionary")
    try:
        return hashlib.sha256(canonical_json(value)).hexdigest()
    except (TypeError, ValueError) as exc:
        raise HarnessError("manifest must contain finite JSON values") from exc


class Harness:
    """Reserve limits before dispatch and require a fresh passing final check."""

    _SCHEMAS = {
        "discover": {"source_id"},
        "fetch": {"url"},
        "select": {"article_ids"},
        "summarize": {"article_ids", "repair"},
        "verify": {"digest_hash", "manifest_hash"},
        "finish": set(),
    }
    _TRANSITIONS = {
        "created": {"collecting", "verifying"},
        "collecting": {"evidence_ready", "verifying"},
        "evidence_ready": {"summarizing", "verifying"},
        "summarizing": {"verifying"},
        "verifying": {"summarizing"},
        "finished": set(),
    }
    _DEFAULTS = {
        "max_actions": 50,
        "max_http_requests": 16,
        "max_model_calls": 2,
        "max_run_seconds": 300,
        "initial_input_tokens": 8000,
        "initial_input_bytes": 48 * 1024,
        "repair_input_tokens": 4000,
        "repair_input_bytes": 24 * 1024,
        "max_application_input_tokens": 12000,
        "observed_total_token_alert": 40000,
    }
    _REDACTED_KEYS = {
        "authorization", "api_key", "access_token", "refresh_token",
        "password", "secret", "headers", "environment", "env",
        "prompt", "raw", "raw_events", "page_body", "body",
    }

    def __init__(self, root: Path, policy: dict, run_id: str):
        if not isinstance(policy, dict):
            raise HarnessError("policy must be a dictionary")
        if not isinstance(run_id, str) or not run_id.strip():
            raise HarnessError("run_id must be nonempty")
        self.root = Path(root).resolve()
        self.run_id = run_id
        self._policy = copy.deepcopy(policy)
        limits = self._policy.get("limits", {})
        if not isinstance(limits, dict):
            raise HarnessError("policy limits must be a dictionary")
        self._limits = {}
        for name, default in self._DEFAULTS.items():
            value = limits.get(name, self._policy.get(name, default))
            if (isinstance(value, bool) or not isinstance(value, (int, float))
                    or not math.isfinite(value) or value <= 0
                    or (name != "max_run_seconds" and not isinstance(value, int))):
                raise HarnessError("invalid limit: " + name)
            # These are ceiling contracts. A policy may tighten but not raise them.
            self._limits[name] = min(value, default)
        self._lock = threading.RLock()
        self._started = time.monotonic()
        self._deadline = self._started + self._limits["max_run_seconds"]
        self._state = "created"
        self.events = []
        self.usages = []
        self.counters = {
            "actions": 0,
            "http_requests": 0,
            "model_calls": 0,
            "application_input_tokens": 0,
            "application_input_bytes": 0,
            "observed_total_tokens": 0,
        }
        self._operations = {}
        self._pending_usage = False
        self._unknown_usage = False
        self._repair_reserved = False
        self._verified = None
        self.event("run", "created", {"policy_hash": manifest_hash(self._policy)})

    @property
    def policy(self) -> dict:
        return copy.deepcopy(self._policy)

    @property
    def state(self) -> str:
        return self._state

    def remaining_seconds(self) -> float:
        return max(0.0, self._deadline - time.monotonic())

    def _active(self) -> None:
        if self._state == "finished":
            raise HarnessError("run is terminal")
        if self.remaining_seconds() <= 0:
            raise HarnessError("run deadline exceeded")

    @classmethod
    def _clean_details(cls, value: Any) -> Any:
        if isinstance(value, dict):
            return {str(key): ("[redacted]" if str(key).lower() in cls._REDACTED_KEYS
                              else cls._clean_details(item))
                    for key, item in value.items()}
        if isinstance(value, (list, tuple)):
            return [cls._clean_details(item) for item in value]
        if value is None or isinstance(value, (str, int, bool)):
            return value
        if isinstance(value, float) and math.isfinite(value):
            return value
        return "[unsupported detail]"

    def event(self, name: str, status: str, details: dict) -> dict:
        """Record sanitized metadata; callers must not provide source bodies."""
        with self._lock:
            entry = {
                "event_id": len(self.events) + 1,
                "run_id": self.run_id,
                "name": name,
                "status": status,
                "state": self.state,
                "elapsed_seconds": round(max(0.0, time.monotonic() - self._started), 6),
                "details": self._clean_details(details),
                "counters": copy.deepcopy(self.counters),
            }
            self.events.append(entry)
            return copy.deepcopy(entry)

    def transition(self, state: str) -> None:
        with self._lock:
            self._active()
            if state == self.state:
                return
            if state not in self._TRANSITIONS.get(self.state, set()):
                raise HarnessError("invalid state transition")
            if self.state == "verifying" and state == "summarizing":
                if self._repair_reserved:
                    raise HarnessError("repair already reserved")
            previous = self.state
            self._state = state
            self._verified = None
            self.event("state", "changed", {"previous": previous, "current": state})

    @classmethod
    def _validate_action(cls, action: Action) -> None:
        if not isinstance(action, Action):
            raise HarnessError("action must be an Action")
        if not isinstance(action.operation_id, str) or not action.operation_id.strip():
            raise HarnessError("operation_id must be nonempty")
        if not isinstance(action.name, str) or action.name not in cls._SCHEMAS:
            raise HarnessError("unknown action")
        args = action.arguments
        if not isinstance(args, dict) or set(args) != cls._SCHEMAS[action.name]:
            raise HarnessError("action arguments do not match schema")
        for field in ("source_id", "url"):
            if field in args and (not isinstance(args[field], str) or not args[field].strip()):
                raise HarnessError(field + " must be nonempty")
        if "article_ids" in args:
            identifiers = args["article_ids"]
            if (not isinstance(identifiers, list)
                    or any(not isinstance(item, str) or not item.strip() for item in identifiers)
                    or len(set(identifiers)) != len(identifiers)):
                raise HarnessError("article_ids must be unique nonempty strings")
        if "repair" in args and type(args["repair"]) is not bool:
            raise HarnessError("repair must be a boolean")
        for field in ("digest_hash", "manifest_hash"):
            if field in args:
                value = args[field]
                if (not isinstance(value, str) or len(value) != 64
                        or any(char not in "0123456789abcdef" for char in value)):
                    raise HarnessError(field + " must be a lowercase SHA256 digest")

    def execute(self, action: Action, callback: Callable[[], Any]) -> Any:
        """Run one effect, retaining successful results and uncertain failures."""
        with self._lock:
            self._active()
            if self.counters["actions"] >= self._limits["max_actions"]:
                raise HarnessError("action budget exhausted")
            self.counters["actions"] += 1
            try:
                self._validate_action(action)
                if not callable(callback):
                    raise HarnessError("callback must be callable")
            except HarnessError:
                self.event("action", "rejected", {"reason": "invalid_action"})
                raise
            signature = hashlib.sha256(canonical_json({
                "name": action.name, "arguments": action.arguments,
            })).hexdigest()
            previous = self._operations.get(action.operation_id)
            metadata = {"operation_id": action.operation_id, "action": action.name,
                        "argument_hash": signature}
            if previous is not None:
                if previous["signature"] != signature:
                    self.event("action", "rejected", dict(metadata, reason="operation_id_conflict"))
                    raise HarnessError("operation ID reused with different arguments")
                if previous["status"] != "succeeded":
                    self.event("action", "rejected", dict(metadata, reason="uncertain_operation"))
                    raise HarnessError("failed or pending operation needs a new attempt ID")
                self.event("action", "replayed", metadata)
                return copy.deepcopy(previous["result"])
            self._operations[action.operation_id] = {
                "signature": signature, "status": "pending", "name": action.name,
            }
            if action.name != "finish":
                self._verified = None
            self.event("action", "started", metadata)
        try:
            result = callback()
            recorded_result = copy.deepcopy(result)
        except BaseException as exc:
            with self._lock:
                self._operations[action.operation_id]["status"] = "failed"
                self.event("action", "failed", dict(metadata, error_type=type(exc).__name__))
            raise
        with self._lock:
            self._operations[action.operation_id].update(status="succeeded", result=recorded_result)
            self.event("action", "succeeded", metadata)
        return result

    def before_http(self, url: str) -> None:
        """Reserve one attempt, including redirects and explicit retries."""
        with self._lock:
            self._active()
            if not isinstance(url, str) or not url:
                raise HarnessError("HTTP URL must be nonempty")
            if self.counters["http_requests"] >= self._limits["max_http_requests"]:
                raise HarnessError("HTTP request budget exhausted")
            self.counters["http_requests"] += 1
            # URL validation belongs to sources; log its hash instead of query data.
            self.event("http", "reserved", {"url_hash": hashlib.sha256(url.encode()).hexdigest()})

    def reserve_model(self, input_tokens: int, input_bytes: int, repair: bool = False) -> None:
        """Consume the invocation allowance before any model process is started."""
        with self._lock:
            self._active()
            if (type(input_tokens) is not int or input_tokens < 0
                    or type(input_bytes) is not int or input_bytes < 0
                    or type(repair) is not bool):
                raise HarnessError("invalid model reservation")
            if self._pending_usage or self._unknown_usage:
                raise HarnessError("previous model usage is unknown")
            if self.counters["observed_total_tokens"] >= self._limits["observed_total_token_alert"]:
                raise HarnessError("observed model token alert prevents further calls")
            if self.counters["model_calls"] >= self._limits["max_model_calls"]:
                raise HarnessError("model invocation budget exhausted")
            if repair:
                if self.counters["model_calls"] != 1 or self._repair_reserved:
                    raise HarnessError("repair requires one previous invocation")
                prefix = "repair"
            else:
                if self.counters["model_calls"] != 0:
                    raise HarnessError("only one initial model invocation is allowed")
                prefix = "initial"
            if input_tokens > self._limits[prefix + "_input_tokens"]:
                raise HarnessError("model application token envelope exceeded")
            if input_bytes > self._limits[prefix + "_input_bytes"]:
                raise HarnessError("model application byte envelope exceeded")
            if self.counters["application_input_tokens"] + input_tokens > self._limits["max_application_input_tokens"]:
                raise HarnessError("cumulative application input allowance exceeded")
            self.counters["model_calls"] += 1
            self.counters["application_input_tokens"] += input_tokens
            self.counters["application_input_bytes"] += input_bytes
            self._pending_usage = True
            self._repair_reserved = self._repair_reserved or repair
            self._verified = None
            self.event("model", "reserved", {"repair": repair, "input_tokens": input_tokens,
                                                "input_bytes": input_bytes})

    def record_usage(self, usage: Optional[Dict[str, Any]]) -> None:
        with self._lock:
            if not self._pending_usage:
                raise HarnessError("usage requires an outstanding model reservation")
            if usage is not None and not isinstance(usage, dict):
                raise HarnessError("usage must be a dictionary or None")
            total = usage.get("total_tokens") if usage is not None else None
            known = type(total) is int and total >= 0
            if known and "input_tokens" in usage and "output_tokens" in usage:
                inputs, outputs = usage["input_tokens"], usage["output_tokens"]
                known = (type(inputs) is int and type(outputs) is int
                         and inputs >= 0 and outputs >= 0 and inputs + outputs == total)
            record = {"invocation_id": self.counters["model_calls"],
                      "usage_known": known, "usage": copy.deepcopy(usage)}
            self.usages.append(record)
            self._pending_usage = False
            if known:
                # Cached input and reasoning tokens are subsets, never added again.
                if self.counters["observed_total_tokens"] is not None:
                    self.counters["observed_total_tokens"] += total
            else:
                self._unknown_usage = True
                self.counters["observed_total_tokens"] = None
            self.event("model", "usage_recorded", record)

    def safe_path(self, relative: str) -> Path:
        """Resolve fixed artifact paths and reject traversal or escaping symlinks."""
        if not isinstance(relative, (str, Path)):
            raise HarnessError("artifact path must be relative")
        path = Path(relative)
        if path.is_absolute() or ".." in path.parts or str(path) in ("", "."):
            raise HarnessError("artifact path must stay inside submission root")
        try:
            resolved = (self.root / path).resolve()
            resolved.relative_to(self.root)
        except (ValueError, RuntimeError, OSError) as exc:
            raise HarnessError("artifact path escapes submission root") from exc
        return resolved

    def mark_verified(self, digest_bytes: bytes, manifest: dict, passed: bool) -> None:
        with self._lock:
            self._active()
            if self.state != "verifying":
                raise HarnessError("verification must run in verifying state")
            if type(passed) is not bool:
                raise HarnessError("verification result must be boolean")
            self._verified = {"digest_hash": digest_hash(digest_bytes),
                              "manifest_hash": manifest_hash(manifest), "passed": passed}
            self.event("verification", "passed" if passed else "failed", self._verified)

    def finish(self, digest_bytes: bytes, manifest: dict) -> dict:
        """Authorize finalization only for the exact freshly checked artifacts."""
        with self._lock:
            self._active()
            current = {"digest_hash": digest_hash(digest_bytes),
                       "manifest_hash": manifest_hash(manifest), "passed": True}
            if self.state != "verifying" or self._verified != current:
                raise HarnessError("finish requires a fresh passing artifact and manifest check")
            if self._pending_usage:
                raise HarnessError("record outstanding model usage before finish")
            if any(operation["status"] == "pending" and operation["name"] != "finish"
                   for operation in self._operations.values()):
                raise HarnessError("outstanding action must complete before finish")
            self._state = "finished"
            self.event("run", "finished", current)
            return {"run_id": self.run_id, "state": self.state,
                    "digest_hash": current["digest_hash"], "manifest_hash": current["manifest_hash"]}
