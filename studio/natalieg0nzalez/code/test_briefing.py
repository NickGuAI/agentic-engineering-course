import contextlib
import datetime as dt
import io
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

import briefing


class SendModesTest(unittest.TestCase):
    def run_mode(self, mode, out, sendmail, recipient="test@example.com"):
        errors = io.StringIO()
        with patch.object(briefing, "OUT", out), \
             patch.object(briefing, "briefing", return_value=("# Preview", "<h1>Preview</h1>", [])), \
             patch.object(briefing.subprocess, "run", side_effect=sendmail), \
             patch.object(sys, "argv", ["briefing.py", mode]), \
             patch.dict(os.environ, {"BRIEFING_TO": recipient} if recipient is not None else {}, clear=True), \
             contextlib.redirect_stdout(io.StringIO()), \
             contextlib.redirect_stderr(errors):
            briefing.main()
        return errors.getvalue()

    def test_test_send_bypasses_and_preserves_marker(self):
        with tempfile.TemporaryDirectory(dir=briefing.OUT) as folder:
            out = Path(folder)
            day = dt.datetime.now(briefing.TZ).date().isoformat()
            marker = out / f"sent-{day}.txt"
            marker.write_text("existing daily submission\n")
            calls = []

            def sendmail(args, **kwargs):
                calls.append((args, kwargs))
                return type("Result", (), {"returncode": 0, "stderr": ""})()

            self.run_mode("--test-send", out, sendmail)
            self.assertEqual(len(calls), 1)
            self.assertEqual(marker.read_text(), "existing daily submission\n")
            self.assertIn("Subject: [TEST]", calls[0][1]["input"])
            self.assertIn("text/html", calls[0][1]["input"])
            self.assertIn("test email: submitted", (out / f"test-send-{day}.log").read_text())

    def test_normal_send_still_skips_existing_marker(self):
        with tempfile.TemporaryDirectory(dir=briefing.OUT) as folder:
            out = Path(folder)
            day = dt.datetime.now(briefing.TZ).date().isoformat()
            marker = out / f"sent-{day}.txt"
            marker.write_text("existing daily submission\n")

            def unexpected_send(*args, **kwargs):
                self.fail("normal send called sendmail despite an existing marker")

            self.run_mode("--send", out, unexpected_send)
            self.assertEqual(marker.read_text(), "existing daily submission\n")
            self.assertIn("already submitted today; skipped", (out / f"run-{day}.log").read_text())

    def test_test_send_requires_recipient_without_traceback(self):
        with tempfile.TemporaryDirectory(dir=briefing.OUT) as folder:
            out = Path(folder)

            def unexpected_send(*args, **kwargs):
                self.fail("sendmail called without a recipient")

            with self.assertRaises(SystemExit) as stopped:
                self.run_mode("--test-send", out, unexpected_send, recipient=None)
            self.assertEqual(stopped.exception.code, 2)


if __name__ == "__main__":
    unittest.main()
