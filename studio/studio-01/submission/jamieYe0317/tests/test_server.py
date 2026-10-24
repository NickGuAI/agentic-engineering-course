"""Local UI boundaries and job lifecycle, using fixtures and fake runners only."""

import concurrent.futures
from datetime import datetime, timezone
import http.client
import json
from pathlib import Path
import sys
import tempfile
import threading
import time
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "code"))
from server import ApiError, ResearchApp, create_server


class AppFixture(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        (self.root / "policy.json").write_text((ROOT / "policy.json").read_text())
        (self.root / "web").mkdir()
        for name, value in (("index.html", "<!doctype html><title>Fixture</title>"),
                            ("app.js", "/* fixture script */"),
                            ("style.css", "/* fixture style */")):
            (self.root / "web" / name).write_text(value)
        (self.root / "outputs").mkdir()
        (self.root / "work").mkdir()
        self.app = ResearchApp(self.root, runner=self.successful_runner)
        self.addCleanup(self.app.join_worker)

    @staticmethod
    def successful_runner(kind, days, max_items, run_id):
        return {"status": "complete", "run_id": run_id}

    def make_run(self, run_id="fixture-run"):
        directory = self.root / "outputs" / run_id
        directory.mkdir()
        for name, value in {
            "status": {"run_id": run_id, "mode": "synthetic_fixture", "status": "partial", "warnings": []},
            "manifest": {"run_id": run_id, "as_of": "2026-09-18T16:00:00+00:00",
                         "mode": "synthetic_fixture", "selected_articles": [], "sources": []},
            "usage": {"cache_hits": 0, "counters": {"model_calls": 0}},
            "verification": {"passed": False, "failures": ["fixture_only"]},
        }.items():
            (directory / (name + ".json")).write_text(json.dumps(value))
        return directory

    def assert_api_error(self, expected_status, function, *args):
        with self.assertRaises(ApiError) as caught:
            function(*args)
        self.assertEqual(caught.exception.status, expected_status)
        self.assertIsInstance(caught.exception.code, str)

    def wait_for_job(self, app, job_id):
        deadline = time.monotonic() + 2
        while time.monotonic() < deadline:
            result = app.get_job(job_id)
            if result["status"] != "running":
                return result
            threading.Event().wait(timeout=0.005)
        self.fail("fixture job did not finish")


class ResearchAppTests(AppFixture):
    def test_live_complete_partial_and_empty_are_successful_jobs(self):
        for outcome in ("complete", "partial", "empty"):
            calls = []
            def runner(kind, days, max_items, run_id):
                calls.append((kind, days, max_items, run_id))
                return {"status": outcome, "run_id": run_id}
            app = ResearchApp(self.root, runner=runner)
            job = app.start_job({"kind": "live", "days": 3, "max_items": 2})
            app.join_worker()
            finished = app.get_job(job["id"])
            with self.subTest(outcome=outcome):
                self.assertEqual(finished["status"], "complete")
                self.assertEqual(calls[0][:3], ("live", 3, 2))
                self.assertEqual(finished["run_id"], calls[0][3])

    def test_blocked_and_crashed_runner_release_slot_and_report_failure(self):
        calls = []
        def runner(kind, days, max_items, run_id):
            calls.append(run_id)
            if len(calls) == 1:
                return {"status": "blocked", "run_id": run_id}
            if len(calls) == 2:
                raise RuntimeError("fixture runner error")
            return {"status": "complete", "run_id": run_id}
        app = ResearchApp(self.root, runner=runner)
        self.addCleanup(app.join_worker)
        for expected in ("failed", "failed", "complete"):
            job = app.start_job({"kind": "live", "days": 7, "max_items": 5})
            self.assertEqual(self.wait_for_job(app, job["id"])["status"], expected)

    def test_demo_prefers_compact_run_and_keeps_all_run_ids(self):
        run_ids = {"full": "fixture-full", "compact": "fixture-compact", "failure": "fixture-failure"}
        app = ResearchApp(self.root, runner=lambda *args: {"run_ids": run_ids, "mode": "synthetic_fixture"})
        job = app.start_job({"kind": "demo", "days": 7, "max_items": 5})
        app.join_worker()
        result = app.get_job(job["id"])
        self.assertEqual(result["status"], "complete")
        self.assertEqual(result["run_id"], run_ids["compact"])
        self.assertCountEqual(result["run_ids"], run_ids.values())

    def test_job_input_schema_and_bounds_reject_before_runner(self):
        calls = []
        app = ResearchApp(self.root, runner=lambda *args: calls.append(args))
        invalid = [
            {}, [], None,
            {"kind": "shell"}, {"kind": ["live"]},
            {"kind": "live", "command": "anything"},
            {"kind": "live", "run_id": "../work"},
            {"kind": "live", "days": 0}, {"kind": "live", "days": 8},
            {"kind": "live", "days": True}, {"kind": "live", "days": "7"},
            {"kind": "live", "max_items": 0}, {"kind": "live", "max_items": 6},
            {"kind": "live", "max_items": False}, {"kind": "live", "max_items": "5"},
        ]
        for payload in invalid:
            with self.subTest(payload=payload):
                self.assert_api_error(400, app.start_job, payload)
        self.assertEqual(calls, [])

    def test_concurrent_submissions_launch_exactly_one_runner(self):
        entered, release = threading.Event(), threading.Event()
        calls = []
        def runner(kind, days, max_items, run_id):
            calls.append(run_id)
            entered.set()
            release.wait(timeout=3)
            return {"status": "partial", "run_id": run_id}
        app = ResearchApp(self.root, runner=runner)
        def submit(unused):
            try:
                return app.start_job({"kind": "live", "days": 7, "max_items": 5})
            except ApiError as exc:
                return exc.status
        try:
            with concurrent.futures.ThreadPoolExecutor(max_workers=8) as pool:
                results = list(pool.map(submit, range(8)))
            self.assertTrue(entered.wait(timeout=1))
            self.assertEqual(sum(isinstance(result, dict) for result in results), 1)
            self.assertEqual(results.count(409), 7)
            self.assertEqual(len(calls), 1)
        finally:
            release.set()
            app.join_worker()

    def test_join_worker_drains_active_job(self):
        entered, release, drained = threading.Event(), threading.Event(), threading.Event()
        def runner(kind, days, max_items, run_id):
            entered.set()
            release.wait(timeout=3)
            return {"status": "complete", "run_id": run_id}
        app = ResearchApp(self.root, runner=runner)
        job = app.start_job({"kind": "live", "days": 7, "max_items": 5})
        self.assertTrue(entered.wait(timeout=1))
        def drain():
            app.join_worker()
            drained.set()
        waiter = threading.Thread(target=drain)
        waiter.start()
        try:
            self.assertFalse(drained.wait(timeout=0.03))
        finally:
            release.set()
            waiter.join(timeout=2)
        self.assertTrue(drained.is_set())
        self.assertEqual(app.get_job(job["id"])["status"], "complete")

    def test_state_ignores_unfinished_runs_and_unknown_jobs_are_not_found(self):
        (self.root / "outputs" / "unfinished").mkdir()
        state = self.app.state()
        self.assertIsInstance(state["csrf_token"], str)
        self.assertIsInstance(state["runs"], list)
        self.assertFalse(state["running"])
        self.assert_api_error(404, self.app.get_job, "does-not-exist")

    def test_run_paths_and_same_root_symlinks_cannot_expose_work(self):
        directory = self.make_run()
        self.assertIsInstance(self.app.run_detail("fixture-run"), dict)
        for run_id in ("../work", "/tmp", "..", "x/y", "x%2Fy"):
            with self.subTest(run_id=run_id):
                self.assert_api_error(404, self.app.run_detail, run_id)
        secret = self.root / "work" / "secret.json"
        secret.write_text('{"private": "fixture-secret"}')
        (directory / "manifest.json").unlink()
        (directory / "manifest.json").symlink_to(secret)
        self.assert_api_error(404, self.app.run_detail, "fixture-run")
        (self.root / "outputs" / "work-alias").symlink_to(self.root / "work", target_is_directory=True)
        self.assert_api_error(404, self.app.run_detail, "work-alias")

    def test_tampered_saved_digest_is_withheld_and_marked_blocked(self):
        from experiments import FixtureModel, fixture_collection
        from run import research

        (self.root / "prompts").mkdir()
        for name in ("summarize.md", "summary.schema.json"):
            (self.root / "prompts" / name).write_text((ROOT / "prompts" / name).read_text())
        for filename in ("digest.md", "digest.json"):
            with self.subTest(tampered_file=filename):
                run_id = "tampered-" + filename.replace(".", "-")
                report = research(
                    self.root, self.app.policy, datetime(2026, 9, 18, 16, tzinfo=timezone.utc),
                    FixtureModel(self.root), run_id=run_id, collection=fixture_collection(),
                    mode="synthetic_fixture", use_cache=False)
                self.assertEqual(report["status"], "complete")
                original = self.app.run_detail(run_id)
                self.assertTrue(original["verification"]["passed"])
                self.assertIsNotNone(original["digest"])

                directory = self.root / "outputs" / run_id
                saved_status = (directory / "status.json").read_bytes()
                saved_check = (directory / "verification.json").read_bytes()
                target = directory / filename
                if filename.endswith(".json"):
                    digest = json.loads(target.read_text())
                    # Keep the summary structurally valid: the original artifact
                    # hash must still invalidate this changed factual content.
                    digest["items"][0]["summary"] = "Changed " + digest["items"][0]["summary"]
                    target.write_text(json.dumps(digest))
                else:
                    target.write_text(target.read_text() + "\nChanged after verification.\n")

                current = self.app.run_detail(run_id)
                self.assertFalse(current["verification"]["passed"])
                self.assertIsNone(current["digest"])
                self.assertEqual(current["status"]["status"], "blocked")
                self.assertTrue(any("withheld" in warning for warning in current["status"]["warnings"]))
                listed = next(row for row in self.app.state()["runs"] if row["run_id"] == run_id)
                self.assertEqual(listed["status"], "blocked")
                self.assertEqual(listed["items"], 0)
                # Viewing corrupt artifacts changes neither saved evidence nor
                # its historical outcome; only the current UI result changes.
                self.assertEqual((directory / "status.json").read_bytes(), saved_status)
                self.assertEqual((directory / "verification.json").read_bytes(), saved_check)


class ServerHTTPTests(AppFixture):
    def setUp(self):
        super().setUp()
        self.server = create_server(self.app, port=0)
        self.thread = threading.Thread(target=self.server.serve_forever, kwargs={"poll_interval": 0.01}, daemon=True)
        self.thread.start()
        self.addCleanup(self.close_server)
        self.host = "127.0.0.1:%d" % self.server.server_port

    def close_server(self):
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(timeout=2)

    def request(self, method, path, body=None, headers=None):
        connection = http.client.HTTPConnection("127.0.0.1", self.server.server_port, timeout=2)
        try:
            connection.request(method, path, body=body, headers=headers or {})
            response = connection.getresponse()
            return response.status, dict(response.getheaders()), response.read()
        finally:
            connection.close()

    def post_headers(self, **changes):
        result = {"Host": self.host, "Origin": "http://" + self.host,
                  "X-CSRF-Token": self.app.csrf_token, "Content-Type": "application/json"}
        result.update(changes)
        return result

    def test_bound_to_loopback_and_fixed_static_routes_only(self):
        self.assertEqual(self.server.server_address[0], "127.0.0.1")
        for route in ("/", "/app.js", "/style.css"):
            with self.subTest(route=route):
                self.assertEqual(self.request("GET", route)[0], 200)
        for route in ("/work/secret.json", "/code/model.py", "/.git/config", "/auth.json", "/outputs/"):
            with self.subTest(route=route):
                self.assertEqual(self.request("GET", route)[0], 404)

    def test_state_token_and_foreign_host_boundary(self):
        status, headers, data = self.request("GET", "/api/state")
        self.assertEqual(status, 200)
        self.assertEqual(json.loads(data)["csrf_token"], self.app.csrf_token)
        self.assertNotEqual(headers.get("Access-Control-Allow-Origin"), "*")
        self.assertEqual(self.request("GET", "/api/state", headers={"Host": "attacker.example"})[0], 403)
        self.assertEqual(self.request("GET", "/api/state", headers={"Host": "127.0.0.1:1"})[0], 403)

    def test_post_requires_matching_origin_and_csrf_token(self):
        payload = json.dumps({"kind": "live", "days": 7, "max_items": 5})
        bad_headers = [
            self.post_headers(Origin="https://attacker.example"),
            self.post_headers(Origin="null"),
            self.post_headers(Origin="http://localhost:%d" % self.server.server_port),
            self.post_headers(**{"X-CSRF-Token": "wrong"}),
            self.post_headers(Host="attacker.example"),
        ]
        missing_origin = self.post_headers()
        del missing_origin["Origin"]
        bad_headers.append(missing_origin)
        missing_token = self.post_headers()
        del missing_token["X-CSRF-Token"]
        bad_headers.append(missing_token)
        for headers in bad_headers:
            with self.subTest(headers=headers):
                self.assertEqual(self.request("POST", "/api/jobs", payload, headers)[0], 403)

    def test_post_rejects_malformed_oversized_or_unsupported_input(self):
        for body, expected in (("{", 400), ("x" * 4097, 413),
                               (json.dumps({"kind": "live", "path": "../work"}), 400),
                               (json.dumps({"kind": "live", "days": 8}), 400)):
            with self.subTest(expected=expected, length=len(body)):
                self.assertEqual(self.request("POST", "/api/jobs", body, self.post_headers())[0], expected)
        status = self.request("POST", "/api/jobs", '{}',
                              self.post_headers(**{"Content-Type": "text/plain"}))[0]
        self.assertIn(status, (400, 415))

    def test_valid_localhost_origin_can_start_and_poll_job(self):
        local = "localhost:%d" % self.server.server_port
        status, headers, data = self.request(
            "POST", "/api/jobs", json.dumps({"kind": "live", "days": 7, "max_items": 5}),
            self.post_headers(Host=local, Origin="http://" + local))
        self.assertIn(status, (200, 202))
        job = json.loads(data)["job"]
        self.app.join_worker()
        status, _, data = self.request("GET", "/api/jobs/" + job["id"])
        self.assertEqual(status, 200)
        self.assertEqual(json.loads(data)["job"]["status"], "complete")
        self.assertEqual(self.request("GET", "/api/jobs/missing")[0], 404)

    def test_routes_reject_traversal_and_static_symlink(self):
        secret = self.root / "work" / "secret.txt"
        secret.write_text("fixture-private-data")
        (self.root / "web" / "app.js").unlink()
        (self.root / "web" / "app.js").symlink_to(secret)
        for route in ("/app.js", "/api/runs/..%2Fwork", "/api/runs/../work", "/../work/secret.txt"):
            with self.subTest(route=route):
                status, _, data = self.request("GET", route)
                self.assertEqual(status, 404)
                self.assertNotIn(b"fixture-private-data", data)


if __name__ == "__main__":
    unittest.main()
