import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import Mock, patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "code"))
from model import (CodexModel, ModelError, DISABLED_FEATURES, SUPPORTED_CLI,
                   _environment, _normalized_usage, _parse_events, _safe_defaults,
                   _restricted_catalog, CAPABILITY_OVERRIDES)


ITEM = {"article_id": "article-1", "summary": "Evidence-backed summary.",
        "relevance": "Interpretation: Useful for evaluation.",
        "evidence_ids": ["p1"], "insufficient_evidence": False}


def events(item=None, usage=None, extra=None):
    stream = [{"type": "thread.started", "thread_id": "private-value"},
              {"type": "turn.started"}]
    stream.extend(extra or [])
    stream += [{"type": "item.completed", "item": {"type": "agent_message",
                "text": json.dumps({"items": [item or ITEM]})}},
               {"type": "turn.completed", "usage": usage}]
    return "\n".join(json.dumps(x) for x in stream)


class EventTests(unittest.TestCase):
    def test_usage_never_double_counts_cached_or_reasoning(self):
        usage = {"input_tokens": 100, "cached_input_tokens": 80,
                 "output_tokens": 30, "reasoning_output_tokens": 20,
                 "secret": "must not leak"}
        result = _parse_events(events(usage=usage))
        self.assertEqual(result["usage"]["total_tokens"], 130)
        self.assertNotIn("secret", result["usage"])
        self.assertTrue(result["usage_known"])

    def test_missing_usage_is_unknown(self):
        result = _parse_events(events())
        self.assertIsNone(result["usage"])
        self.assertFalse(result["usage_known"])

    def test_bad_usage_is_unknown(self):
        for bad in ({"input_tokens": True, "output_tokens": 3},
                    {"input_tokens": -1, "output_tokens": 3},
                    {"input_tokens": 1, "output_tokens": 3, "cached_input_tokens": 2},
                    {"input_tokens": 1, "output_tokens": 3, "reasoning_output_tokens": 4}):
            self.assertIsNone(_normalized_usage(bad))

    def test_tool_event_fails_and_preserves_available_usage(self):
        for kind in ("command_execution", "file_change", "mcp_tool_call", "web_search", "new_tool"):
            with self.assertRaises(ModelError) as error:
                _parse_events(events(usage={"input_tokens": 10, "output_tokens": 5},
                                     extra=[{"type": "item.started", "item": {"type": kind}}]))
            self.assertEqual(error.exception.code, "unexpected_tool_event")
            self.assertEqual(error.exception.usage["total_tokens"], 15)

    def test_extra_model_fields_are_rejected(self):
        item = dict(ITEM, fabricated_url="https://fake.invalid")
        with self.assertRaises(ModelError) as error:
            _parse_events(events(item))
        self.assertEqual(error.exception.code, "invalid_model_schema")

    def test_unknown_event_and_failure_text_are_not_returned(self):
        secret = "SUPER_SECRET"
        with self.assertRaises(ModelError) as error:
            _parse_events(events(extra=[{"type": "error", "message": secret}]))
        self.assertNotIn(secret, str(error.exception))


class ConfigurationTests(unittest.TestCase):
    def test_only_safe_defaults_are_extracted(self):
        with tempfile.TemporaryDirectory() as temp:
            p = Path(temp) / "config.toml"
            p.write_text('model="configured-model"\nmodel_reasoning_effort="high"\n'
                         'api_key="SECRET"\n[mcp_servers.test]\nmodel="ignore"\n'
                         '[models.new_thread]\nmodel="new-default"\n')
            self.assertEqual(_safe_defaults(p),
                             {"model": "new-default", "model_reasoning_effort": "high"})

    def test_environment_excludes_api_keys_and_parent_identity(self):
        with patch.dict(os.environ, {"OPENAI_API_KEY": "secret", "CODEX_THREAD_ID": "parent"}):
            env = _environment()
        self.assertNotIn("OPENAI_API_KEY", env)
        self.assertNotIn("CODEX_THREAD_ID", env)

    def test_enabled_shell_tool_fails_before_generation(self):
        instance = CodexModel.__new__(CodexModel)
        instance._flags = []
        features = "\n".join(f + " stable " + ("true" if f == "shell_tool" else "false")
                             for f in DISABLED_FEATURES)
        with patch.object(instance, "_probe", return_value=features):
            with self.assertRaises(ModelError) as error:
                instance._check_capabilities()
        self.assertEqual(error.exception.code, "tool_disabling_not_verified")

    def test_catalog_preserves_identity_and_instructions_but_removes_tools(self):
        original = {"slug": "selected", "base_instructions": "Safety instructions.",
                    "default_reasoning_level": "high", "apply_patch_tool_type": "freeform",
                    "experimental_supported_tools": ["clock"], "shell_type": "unified_exec"}
        updated = _restricted_catalog({"models": [original]}, "selected")["models"][0]
        for key, value in original.items():
            if key not in CAPABILITY_OVERRIDES:
                self.assertEqual(updated[key], value)
        self.assertIsNone(updated["apply_patch_tool_type"])
        self.assertEqual(updated["shell_type"], "disabled")
        self.assertEqual(updated["experimental_supported_tools"], [])

    def test_mcp_servers_are_disabled_individually_and_rechecked(self):
        instance = CodexModel.__new__(CodexModel)
        instance._flags = []
        features = "\n".join(f + " stable " + ("true" if f == "unified_exec" else "false")
                             for f in DISABLED_FEATURES)
        with patch.object(instance, "_probe", side_effect=[features,
                          '[{"name":"example","enabled":true,"transport":{"type":"stdio"}}]',
                          '[{"name":"example","enabled":false}]']):
            instance._check_capabilities()
        self.assertIn("mcp_servers.example.enabled=false", instance._flags)


class SubprocessTests(unittest.TestCase):
    def make_adapter(self, root):
        # No CLI/model calls in tests; constructor preflight tested separately.
        m = CodexModel.__new__(CodexModel)
        m.root = Path(root)
        m.executable = "/usr/bin/fake-codex"
        m.env = {"PATH": "/usr/bin"}
        m.model = "configured-model"
        m.reasoning = "high"
        m.prompt = "Summarize evidence only.\n"
        m.schema_text = '{"type":"object"}'
        m.catalog = {"models": [{"slug": "configured-model"}]}
        m._flags = ["-c", "features.shell_tool=false"]
        return m

    def test_exact_input_is_passed_on_stdin_without_shell(self):
        with tempfile.TemporaryDirectory() as temp:
            m = self.make_adapter(temp)
            process = Mock(returncode=0)
            process.communicate.return_value = (events(), "private stderr")
            payload = {"articles": [], "text": "$(touch nope)"}
            with patch("model.subprocess.Popen", return_value=process) as popen:
                m.generate(payload, 10)
            process.communicate.assert_called_once_with(m.build_input(payload), timeout=10)
            self.assertFalse(popen.call_args.kwargs["shell"])
            self.assertTrue(popen.call_args.kwargs["start_new_session"])
            args = popen.call_args.args[0]
            self.assertIn("--ignore-user-config", args)
            self.assertIn("--ephemeral", args)
            self.assertIn("read-only", args)
            self.assertNotIn("--ignore-rules", args)
            self.assertFalse(any("bypass" in arg for arg in args))
            self.assertFalse(any(Path(temp, "work").iterdir()))

    def test_timeout_kills_process_group_reaps_and_marks_unknown(self):
        with tempfile.TemporaryDirectory() as temp:
            m = self.make_adapter(temp)
            process = Mock(pid=1234)
            process.communicate.side_effect = [subprocess.TimeoutExpired("codex", 1), ("", "")]
            with patch("model.subprocess.Popen", return_value=process), patch("model.os.killpg") as kill:
                with self.assertRaises(ModelError) as error:
                    m.generate({"articles": []}, 1)
            kill.assert_called_once_with(1234, signal.SIGKILL)
            self.assertEqual(process.communicate.call_count, 2)
            self.assertEqual(error.exception.code, "model_timeout")
            self.assertFalse(error.exception.usage_known)

    def test_escaping_work_symlink_is_rejected_before_process(self):
        with tempfile.TemporaryDirectory() as temp, tempfile.TemporaryDirectory() as outside:
            Path(temp, "work").symlink_to(outside, target_is_directory=True)
            with patch("model.subprocess.Popen") as popen:
                with self.assertRaises(ModelError) as error:
                    self.make_adapter(temp).generate({"articles": []}, 1)
            self.assertEqual(error.exception.code, "unsafe_work_path")
            popen.assert_not_called()


if __name__ == "__main__":
    unittest.main()
