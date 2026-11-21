"""Bounded Codex CLI summarization using the user's existing login.

The controller reserves calls, time and application input before invoking this
adapter. CLI-added context and generated reasoning have no hard token ceiling.
No authentication file is read or copied, and raw CLI events are never persisted.

Capability controls checked against the pinned CLI and official sources:
https://learn.chatgpt.com/docs/config-file/config-reference
https://github.com/openai/codex/blob/main/codex-rs/core/src/tools/spec_plan.rs
The per-invocation catalog narrows tools; it preserves model instructions. A
local Responses-request audit on 2026-09-18 observed an empty tools array.
"""
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import signal
import subprocess
import tempfile
from typing import Optional


ADAPTER_VERSION = "codex-summary-1"
# Revalidate this contract before using a different CLI version. Fail closed.
SUPPORTED_CLI = "codex-cli 0.154.0-alpha.6.2"
DISABLED_FEATURES = (
    "shell_tool", "unified_exec", "hooks", "plugins", "remote_plugin", "apps",
    "enable_mcp_apps", "browser_use", "browser_use_external",
    "browser_use_full_cdp_access", "computer_use", "image_generation",
    "view_image", "multi_agent", "multi_agent_v2", "code_mode", "code_mode_host",
    "goals", "sleep_tool", "skill_search", "skill_mcp_dependency_install",
    "tool_suggest", "workspace_dependencies", "shell_snapshot", "in_app_browser",
    "memories", "request_permissions_tool", "unbounded_connection_retries",
    "token_budget", "current_time_reminder", "deferred_executor",
    "standalone_web_search", "code_mode_only", "code_mode_prewarm",
)
_USAGE_FIELDS = ("input_tokens", "cached_input_tokens", "cache_write_input_tokens", "output_tokens",
                 "reasoning_output_tokens")
_ITEM_FIELDS = {"article_id", "summary", "relevance", "evidence_ids",
                "insufficient_evidence"}
CAPABILITY_OVERRIDES = {
    "shell_type": "disabled", "apply_patch_tool_type": None,
    "experimental_supported_tools": [], "tool_mode": "direct",
    "node_repl_disabled": True, "supports_search_tool": False,
}


def _restricted_catalog(catalog, model):
    if not isinstance(catalog, dict) or not isinstance(catalog.get("models"), list):
        raise ModelError("model_catalog_invalid")
    matches = [m for m in catalog["models"] if m.get("slug") == model]
    if len(matches) != 1:
        raise ModelError("model_not_in_bundled_catalog")
    selected = dict(matches[0])
    # Preserve model identity, instructions, provider and reasoning capabilities;
    # only remove tool capabilities from this invocation's local metadata.
    selected.update(CAPABILITY_OVERRIDES)
    return {"models": [selected]}


class ModelError(RuntimeError):
    """Safe diagnostic code; never include child stderr or prompt contents."""

    def __init__(self, code, usage=None):
        super().__init__(code)
        self.code = code
        self.usage = usage
        self.usage_known = bool(usage and usage.get("total_tokens") is not None)


def _safe_defaults(config_path):
    """Read only model/provider/effort strings, not arbitrary config values.

    Python 3.9 has no tomllib. This intentionally limited parser rejects complex
    target strings and named profiles instead of guessing their effective model.
    It does not read auth.json, environment secrets or MCP credentials.
    """
    if not config_path.is_file():
        return {}
    sections = {"": {}, "models.new_thread": {}}
    section = ""
    for line in config_path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if stripped.startswith("["):
            section = stripped.strip("[] ")
            continue
        if section not in sections:
            continue
        match = re.match(r"^(model|model_reasoning_effort|model_provider|profile)\s*=\s*([^#]+)", stripped)
        if match:
            value = match.group(2).strip()
            if not re.fullmatch(r"[\"'][A-Za-z0-9_.:/-]+[\"']", value):
                raise ModelError("unsupported_model_configuration")
            sections[section][match.group(1)] = value[1:-1]
    result = sections[""]
    if "profile" in result:
        raise ModelError("explicit_model_required_for_profile")
    result.update(sections["models.new_thread"])
    return result


def _environment():
    # Keep CLI auth lookup and TLS support; exclude API keys, proxy injection,
    # parent thread identity and arbitrary inherited tool environments.
    allowed = ("HOME", "PATH", "CODEX_HOME", "TMPDIR", "LANG", "LC_ALL",
               "SSL_CERT_FILE", "SSL_CERT_DIR")
    result = {key: os.environ[key] for key in allowed if key in os.environ}
    result["RUST_LOG"] = "off"
    return result


def _normalized_usage(value):
    if not isinstance(value, dict):
        return None
    usage = {key: value[key] for key in _USAGE_FIELDS
             if type(value.get(key)) is int and value[key] >= 0}
    if "input_tokens" not in usage or "output_tokens" not in usage:
        return None
    # CLI turn.completed reports reasoning as a breakdown of output; cached
    # input is a subset of input. Neither is added a second time.
    if usage.get("cached_input_tokens", 0) > usage["input_tokens"]:
        return None
    if usage.get("reasoning_output_tokens", 0) > usage["output_tokens"]:
        return None
    usage["total_tokens"] = usage["input_tokens"] + usage["output_tokens"]
    return usage


def _parse_events(stdout):
    """Allow only passive events; fail any tool item, even on a zero exit."""
    usage = None
    final_text = None
    completed = False
    failure = None
    for line in stdout.splitlines():
        try:
            event = json.loads(line)
        except (ValueError, TypeError):
            raise ModelError("invalid_cli_event", usage)
        if not isinstance(event, dict):
            raise ModelError("invalid_cli_event", usage)
        kind = event.get("type")
        if kind == "turn.completed":
            if completed:
                failure = "unexpected_multiple_turns"
            completed = True
            usage = _normalized_usage(event.get("usage"))
        elif kind in ("thread.started", "turn.started"):
            pass
        elif kind in ("item.started", "item.updated", "item.completed"):
            item = event.get("item", {})
            if not isinstance(item, dict) or item.get("type") not in ("agent_message", "reasoning"):
                failure = "unexpected_tool_event"
            elif kind == "item.completed" and item.get("type") == "agent_message":
                final_text = item.get("text")
        elif kind in ("error", "turn.failed"):
            failure = "model_execution_failed"
        else:
            failure = "unexpected_cli_event"
    if failure:
        raise ModelError(failure, usage)
    if not completed or not isinstance(final_text, str):
        raise ModelError("incomplete_model_result", usage)
    try:
        result = json.loads(final_text)
    except ValueError:
        raise ModelError("invalid_model_json", usage)
    if not isinstance(result, dict) or set(result) != {"items"} or not isinstance(result["items"], list):
        raise ModelError("invalid_model_schema", usage)
    for item in result["items"]:
        if not isinstance(item, dict) or set(item) != _ITEM_FIELDS:
            raise ModelError("invalid_model_schema", usage)
        if any(not isinstance(item[key], str) for key in ("article_id", "summary", "relevance")):
            raise ModelError("invalid_model_schema", usage)
        if type(item["insufficient_evidence"]) is not bool:
            raise ModelError("invalid_model_schema", usage)
        if not isinstance(item["evidence_ids"], list) or any(not isinstance(x, str) for x in item["evidence_ids"]):
            raise ModelError("invalid_model_schema", usage)
    return {"items": result["items"], "usage": usage, "usage_known": usage is not None}


class CodexModel:
    def __init__(self, root: Path, model: Optional[str] = None,
                 reasoning: Optional[str] = None):
        self.root = Path(root).resolve(strict=True)
        self.executable = shutil.which("codex")
        if not self.executable:
            raise ModelError("codex_not_installed")
        self.env = _environment()
        codex_home = Path(self.env.get("CODEX_HOME", str(Path.home() / ".codex")))
        defaults = _safe_defaults(codex_home / "config.toml")
        if defaults.get("model_provider", "openai") != "openai":
            raise ModelError("unsupported_model_provider")
        self.model = model or defaults.get("model")
        self.reasoning = reasoning or defaults.get("model_reasoning_effort")
        if not self.model or not self.reasoning:
            raise ModelError("model_and_reasoning_must_be_configured")
        if not re.fullmatch(r"[A-Za-z0-9_.:/-]+", self.model):
            raise ModelError("invalid_model_name")
        if self.reasoning not in ("none", "minimal", "low", "medium", "high", "xhigh", "max", "ultra"):
            raise ModelError("invalid_reasoning_effort")
        self.prompt = self._read_asset("prompts/summarize.md")
        self.schema_text = self._read_asset("prompts/summary.schema.json")
        self.cli_version = self._probe(["--version"]).strip()
        if self.cli_version != SUPPORTED_CLI:
            raise ModelError("cli_version_requires_revalidation")
        self._flags = []
        for feature in DISABLED_FEATURES:
            self._flags += ["-c", "features." + feature + "=false"]
        self._flags += ["-c", 'web_search="disabled"',
                        "-c", "features.skip_host_skill_discovery=true",
                        # This capability-removal feature is experimental. Its
                        # generic startup notice uses the CLI's error item type;
                        # suppress only that documented notice, not real errors.
                        "-c", "suppress_unstable_features_warning=true",
                        "-c", "project_doc_max_bytes=0",
                        "-c", 'approval_policy="never"',
                        "-c", "apps._default.enabled=false",
                        "-c", "agents.enabled=false",
                        "-c", "tools.update_plan.enabled=false",
                        "-c", "tools.experimental_request_user_input.enabled=false",
                        "-c", "model_reasoning_effort=" + json.dumps(self.reasoning)]
        self._check_capabilities()
        try:
            catalog = json.loads(self._probe(["debug", "models", "--bundled"]))
        except ValueError:
            raise ModelError("model_catalog_invalid")
        self.catalog = _restricted_catalog(catalog, self.model)

    def _read_asset(self, relative):
        candidate = self.root / relative
        if not candidate.resolve(strict=True).is_relative_to(self.root):
            raise ModelError("unsafe_asset_path")
        return candidate.read_text(encoding="utf-8")

    def _probe(self, args):
        try:
            result = subprocess.run([self.executable] + args, cwd=str(self.root),
                                    env=self.env, capture_output=True, text=True,
                                    timeout=15, check=False, shell=False)
        except (OSError, subprocess.TimeoutExpired):
            raise ModelError("cli_preflight_failed")
        if result.returncode:
            raise ModelError("cli_preflight_failed")
        return result.stdout

    def _check_capabilities(self):
        states = {}
        for line in self._probe(["features", "list"] + self._flags).splitlines():
            fields = line.split()
            if fields and fields[-1] in ("true", "false"):
                states[fields[0]] = fields[-1] == "true"
        # UnifiedExec selects an implementation, not its availability. The
        # installed CLI forces it on; add_shell_tools returns before registering
        # exec_command/write_stdin when ShellTool=false. Keep the disable request
        # but verify the actual gate. Also force catalog shell_type=disabled.
        # Source: openai/codex, core/src/tools/spec_plan.rs:add_shell_tools.
        if any(states.get(feature) is not False for feature in DISABLED_FEATURES
               if feature != "unified_exec"):
            raise ModelError("tool_disabling_not_verified")
        self.unified_exec_feature = states.get("unified_exec")
        # `mcp list` is configuration inspection, not an MCP connection. Explicit
        # per-server disable avoids relying on empty TOML-map merge semantics.
        try:
            servers = json.loads(self._probe(["mcp", "list", "--json"] + self._flags))
        except ValueError:
            raise ModelError("mcp_inventory_failed")
        if not isinstance(servers, list):
            raise ModelError("mcp_inventory_failed")
        for server in servers:
            name = server.get("name")
            if not isinstance(name, str) or not re.fullmatch(r"[A-Za-z0-9_-]+", name):
                raise ModelError("unsupported_mcp_identifier")
            self._flags += ["-c", "mcp_servers." + name + ".enabled=false"]
            # exec ignores user config; supply an inert valid transport so the
            # explicit disabled server entry remains parseable in that mode.
            transport = server.get("transport", {}).get("type")
            if transport == "stdio":
                self._flags += ["-c", "mcp_servers." + name + '.command="/usr/bin/false"']
            elif transport == "streamable_http":
                self._flags += ["-c", "mcp_servers." + name + '.url="https://disabled.invalid"']
            else:
                raise ModelError("unsupported_mcp_transport")
        try:
            disabled = json.loads(self._probe(["mcp", "list", "--json"] + self._flags))
        except ValueError:
            raise ModelError("mcp_disabling_not_verified")
        if not isinstance(disabled, list) or any(s.get("enabled") is not False for s in disabled):
            raise ModelError("mcp_disabling_not_verified")

    @property
    def identity(self):
        return {"backend": "codex-cli", "model": self.model,
                "reasoning": self.reasoning, "cli_version": self.cli_version,
                "adapter_version": ADAPTER_VERSION,
                "prompt_sha256": hashlib.sha256(self.prompt.encode()).hexdigest(),
                "schema_sha256": hashlib.sha256(self.schema_text.encode()).hexdigest(),
                "sandbox": "read-only", "disabled_features": [x for x in DISABLED_FEATURES if x != "unified_exec"],
                "unified_exec_feature": self.unified_exec_feature,
                "shell_tools_gate": "shell_tool=false and shell_type=disabled",
                "capability_overrides": CAPABILITY_OVERRIDES,
                "catalog_sha256": hashlib.sha256(json.dumps(self.catalog, sort_keys=True).encode()).hexdigest(),
                "mcp_preflight": "all_configured_servers_disabled",
                "provider_token_ceiling": False}

    def build_input(self, payload):
        return self.prompt + json.dumps(payload, ensure_ascii=False, sort_keys=True,
                                        separators=(",", ":")) + "\n"

    def _command(self, scratch):
        schema = scratch / "schema.json"
        schema.write_text(self.schema_text, encoding="utf-8")
        catalog = scratch / "catalog.json"
        catalog.write_text(json.dumps(self.catalog), encoding="utf-8")
        (scratch / ".research-agent-root").touch()
        args = [self.executable, "exec", "--ephemeral", "--ignore-user-config",
                "--strict-config", "--skip-git-repo-check", "--sandbox", "read-only", "--json",
                "--color", "never", "--model", self.model,
                "--output-schema", str(schema), "--cd", str(scratch)] + self._flags
        args += ["-c", 'project_root_markers=[".research-agent-root"]',
                 "-c", "projects." + json.dumps(str(scratch)) + '.trust_level="untrusted"',
                 "-c", "model_catalog_json=" + json.dumps(str(catalog)),
                 "-c", "log_dir=" + json.dumps(str(scratch / "logs")), "-"]
        return args

    def generate(self, payload: dict, timeout: float) -> dict:
        if timeout <= 0:
            raise ModelError("model_timeout")
        work = self.root / "work"
        if work.exists() and (work.is_symlink() or not work.resolve().is_relative_to(self.root)):
            raise ModelError("unsafe_work_path")
        work.mkdir(exist_ok=True)
        with tempfile.TemporaryDirectory(prefix="model-", dir=str(work)) as temp:
            scratch = Path(temp)
            # New marker establishes a project boundary for project config and
            # instructions. Rules remain enabled; no bypass flags are used.
            args = self._command(scratch)
            try:
                process = subprocess.Popen(args, cwd=str(scratch), env=self.env,
                                           stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                                           stderr=subprocess.PIPE, text=True,
                                           shell=False, start_new_session=True)
            except OSError:
                raise ModelError("model_start_failed")
            try:
                stdout, _ = process.communicate(self.build_input(payload), timeout=timeout)
            except subprocess.TimeoutExpired:
                # Terminate all descendants, then reap. The request may already
                # have consumed tokens: never report a timeout as zero usage.
                try:
                    os.killpg(process.pid, signal.SIGKILL)
                except ProcessLookupError:
                    pass
                process.communicate()
                raise ModelError("model_timeout")
            try:
                result = _parse_events(stdout)
            except ModelError:
                raise
            if process.returncode:
                raise ModelError("model_execution_failed", result["usage"])
            return result
