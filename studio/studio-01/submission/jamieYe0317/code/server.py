#!/usr/bin/env python3
"""Loopback-only browser interface for the bounded research harness."""
import argparse
import copy
from datetime import datetime, timezone
import hashlib
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
from pathlib import Path
import secrets
import signal
import threading
import uuid

from evidence import fingerprint
from run import ROOT, TEAM, load_policy, research, safe_error, safe_id
from verify import render, verify_digest


class ApiError(Exception):
    def __init__(self, status, code):
        self.status, self.code = status, code
        super().__init__(code)


def now():
    return datetime.now(timezone.utc).isoformat()


def public_fields(value, names):
    return {name: value[name] for name in names if name in value}


class ResearchApp:
    def __init__(self, root, runner=None):
        self.root = Path(root).resolve()
        self.policy = load_policy(self.root)
        self.csrf_token = secrets.token_urlsafe(32)
        self.lock = threading.Lock()
        self.jobs = {}
        self.active = None
        self.worker = None
        self.closing = False
        self.runner = runner or self._run

    def read_file(self, *parts):
        # Every component must be a real directory/file, even when a symlink
        # would resolve elsewhere inside the submission (such as work/).
        path = self.root
        for part in parts:
            if not part or part in (".", "..") or "/" in part or "\\" in part:
                raise ApiError(404, "not_found")
            path = path / part
            if path.is_symlink():
                raise ApiError(404, "not_found")
        try:
            if not path.is_file() or path.stat().st_size > 4 * 1024 * 1024:
                raise ApiError(404, "not_found")
            return path.read_bytes()
        except OSError:
            raise ApiError(404, "not_found") from None

    def _json(self, run_id, name, optional=False):
        try:
            value = json.loads(self.read_file("outputs", run_id, name))
            if not isinstance(value, dict):
                raise ValueError()
            return value
        except ApiError:
            path = self.root / "outputs" / run_id / name
            if optional and not path.exists() and not path.is_symlink():
                return None
            raise
        except (ValueError, UnicodeError):
            raise ApiError(404, "artifact_unavailable") from None

    def run_detail(self, run_id):
        try:
            safe_id(run_id)
        except (ValueError, TypeError):
            raise ApiError(404, "not_found") from None
        status = self._json(run_id, "status.json")
        manifest = self._json(run_id, "manifest.json")
        usage = self._json(run_id, "usage.json")
        verification = self._json(run_id, "verification.json")
        digest = self._json(run_id, "digest.json", optional=True)
        # Refresh checks in memory; viewing a run never changes its artifacts.
        if digest is not None:
            try:
                checked = verify_digest(digest, manifest, manifest["policy"])
                markdown = self.read_file("outputs", run_id, "digest.md").decode("utf-8")
                if (fingerprint(digest) != verification.get("digest_hash") or
                        fingerprint(manifest) != verification.get("manifest_hash") or
                        hashlib.sha256(markdown.encode()).hexdigest() != verification.get("markdown_sha256") or
                        render(digest) != markdown):
                    checked["failures"].append("artifact_changed_since_check")
                checked["passed"] = not checked["failures"]
                verification = checked
            except (KeyError, TypeError, ValueError, UnicodeError, ApiError):
                verification = {"passed": False, "failures": ["artifact_unavailable_or_invalid"]}
        elif status.get("status") != "blocked":
            verification = {"passed": False, "failures": ["digest_missing"]}
        verification["human_review"] = "pending"
        if verification.get("passed") is not True:
            # A saved success label is not authority after its files change.
            digest = None
            if status.get("status") != "blocked":
                status = dict(status, status="blocked", warnings=list(status.get("warnings", [])) +
                              ["Saved artifact verification failed; the digest is withheld."])
        # Do not send filesystem paths, local configuration or model catalogs.
        return {
            "status": public_fields(status, ("run_id", "mode", "status", "warnings", "human_acceptance")),
            "digest": digest,
            "manifest": public_fields(manifest, ("run_id", "mode", "as_of", "sources", "coverage_limited", "coverage_reasons", "exclusions", "source_failure_policy")),
            "usage": dict(public_fields(usage, ("usage_kind", "application_count_method", "application_counts_exact", "provider_usage", "counters", "cache_hits", "hard_total_token_cap")),
                          model=public_fields(usage.get("model", {}), ("backend", "model", "reasoning"))),
            "verification": verification,
        }

    def state(self):
        rows = []
        directory = self.root / "outputs"
        if directory.is_dir() and not directory.is_symlink():
            # Newly created directories may not have final status yet.
            for path in directory.iterdir():
                if not path.is_dir() or path.is_symlink():
                    continue
                try:
                    detail = self.run_detail(path.name)
                    status, manifest, usage = (detail[k] for k in ("status", "manifest", "usage"))
                    counters = usage.get("counters", {})
                    rows.append({"run_id": path.name, "mode": status.get("mode", "unknown"),
                                 "status": status.get("status", "blocked"), "as_of": manifest.get("as_of"),
                                 "items": len((detail["digest"] or {}).get("items", [])),
                                 "model_calls": counters.get("model_calls", 0),
                                 "input_tokens_estimated": counters.get("application_input_tokens", 0),
                                 "provider_tokens": counters.get("observed_total_tokens"),
                                 "cache_hits": usage.get("cache_hits", 0), "warnings": status.get("warnings", []),
                                 "_saved": path.stat().st_mtime})
                except (ApiError, OSError, ValueError, TypeError, KeyError):
                    continue
        rows.sort(key=lambda row: row["_saved"], reverse=True)
        for row in rows:
            row.pop("_saved")
        with self.lock:
            running = copy.deepcopy(self.jobs.get(self.active))
        return {"csrf_token": self.csrf_token, "running": running, "runs": rows,
                "policy": {"days": self.policy["days"], "max_items": self.policy["max_items"],
                           "model_reasoning": self.policy.get("summary_reasoning", "low")}}

    def start_job(self, payload):
        if not isinstance(payload, dict) or set(payload) - {"kind", "days", "max_items"}:
            raise ApiError(400, "invalid_job")
        kind = payload.get("kind")
        days, max_items = payload.get("days", self.policy["days"]), payload.get("max_items", self.policy["max_items"])
        if (kind not in ("live", "demo") or type(days) is not int or not 1 <= days <= 7 or
                type(max_items) is not int or not 1 <= max_items <= 5):
            raise ApiError(400, "invalid_job")
        with self.lock:
            if self.closing:
                raise ApiError(503, "server_stopping")
            if self.active is not None:
                raise ApiError(409, "job_already_running")
            job_id = uuid.uuid4().hex
            run_id = "web-" + datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ") + "-" + job_id[:8]
            job = {"id": job_id, "kind": kind, "status": "running", "started_at": now(),
                   "run_id": run_id if kind == "live" else None, "run_ids": []}
            self.jobs[job_id] = job
            self.active = job_id
            self.worker = threading.Thread(target=self._finish, args=(job_id, kind, days, max_items, run_id), daemon=False)
            try:
                self.worker.start()
            except Exception:
                self.active, self.worker = None, None
                job.update(status="failed", error="worker_start_failed", finished_at=now())
                raise ApiError(500, "worker_start_failed") from None
            return copy.deepcopy(job)

    def _run(self, kind, days, max_items, run_id):
        if kind == "demo":
            from experiments import demonstration
            return demonstration(self.root)
        from model import CodexModel
        policy = copy.deepcopy(self.policy)
        policy.update(days=days, max_items=max_items)
        model = CodexModel(self.root, reasoning=policy.get("summary_reasoning", "low"))
        return research(self.root, policy, datetime.now(timezone.utc), model, run_id=run_id,
                        source_failure_policy=policy.get("source_failure_policy", "partial"))

    def _finish(self, job_id, kind, days, max_items, run_id):
        try:
            report = self.runner(kind, days, max_items, run_id)
            if kind == "demo":
                ids = report["run_ids"]
                result = {"status": "complete", "run_ids": list(ids.values()), "run_id": ids["compact"]}
            elif report.get("status") in ("complete", "partial", "empty"):
                result = {"status": "complete", "run_id": report["run_id"]}
            else:
                result = {"status": "failed", "error": "research_blocked", "run_id": report.get("run_id", run_id)}
        except Exception as exc:
            result = {"status": "failed", "error": safe_error(exc)}
        with self.lock:
            self.jobs[job_id].update(result, finished_at=now())
            self.active = None

    def get_job(self, job_id):
        with self.lock:
            if job_id not in self.jobs:
                raise ApiError(404, "job_not_found")
            return copy.deepcopy(self.jobs[job_id])

    def join_worker(self):
        with self.lock:
            self.closing = True
            worker = self.worker
        if worker is not None:
            worker.join()


class ResearchHandler(BaseHTTPRequestHandler):
    server_version = "ResearchDesk/1.0"
    sys_version = ""

    def setup(self):
        super().setup()
        self.connection.settimeout(10)

    def log_message(self, fmt, *args):
        pass  # Avoid saving request bodies, queries or tokens.

    def _check_origin(self, write=False):
        hosts = ("127.0.0.1:%d" % self.server.server_port, "localhost:%d" % self.server.server_port)
        host = self.headers.get("Host")
        if len(self.headers.get_all("Host", [])) != 1 or host not in hosts:
            raise ApiError(403, "host_not_allowed")
        origin = self.headers.get("Origin")
        if (write or origin is not None) and origin != "http://" + host:
            raise ApiError(403, "origin_not_allowed")
        if write and not secrets.compare_digest(self.headers.get("X-CSRF-Token", ""), self.server.app.csrf_token):
            raise ApiError(403, "invalid_token")

    def _send(self, status, body, content_type="application/json; charset=utf-8"):
        if not isinstance(body, bytes):
            body = json.dumps(body, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Referrer-Policy", "no-referrer")
        self.send_header("Content-Security-Policy", "default-src 'self'; script-src 'self'; style-src 'self'; connect-src 'self'; img-src 'self'; object-src 'none'; frame-ancestors 'none'; base-uri 'none'; form-action 'self'")
        self.end_headers()
        self.wfile.write(body)

    def _handle(self, write=False):
        try:
            self._check_origin(write)
            if any(char in self.path for char in ("%", "?", "#", "\\")):
                raise ApiError(404, "not_found")
            app = self.server.app
            if write:
                if self.path != "/api/jobs":
                    raise ApiError(404, "not_found")
                if (self.headers.get_content_type() != "application/json" or self.headers.get("Transfer-Encoding") or
                        len(self.headers.get_all("Content-Length", [])) != 1):
                    raise ApiError(400, "invalid_body")
                try:
                    size = int(self.headers["Content-Length"])
                except (ValueError, TypeError):
                    raise ApiError(400, "invalid_body") from None
                if size > 4096:
                    raise ApiError(413, "body_too_large")
                if size <= 0:
                    raise ApiError(400, "invalid_body")
                try:
                    payload = json.loads(self.rfile.read(size))
                except (ValueError, UnicodeError):
                    raise ApiError(400, "invalid_json") from None
                self._send(202, {"job": app.start_job(payload)})
            elif self.path == "/api/state":
                self._send(200, app.state())
            elif self.path.startswith("/api/jobs/"):
                self._send(200, {"job": app.get_job(self.path[len("/api/jobs/"):])})
            elif self.path.startswith("/api/runs/"):
                self._send(200, app.run_detail(self.path[len("/api/runs/"):]))
            else:
                static = {"/": ("index.html", "text/html; charset=utf-8"),
                          "/app.js": ("app.js", "application/javascript; charset=utf-8"),
                          "/style.css": ("style.css", "text/css; charset=utf-8")}
                if self.path not in static:
                    raise ApiError(404, "not_found")
                name, mime = static[self.path]
                self._send(200, app.read_file("web", name), mime)
        except ApiError as exc:
            self._send(exc.status, {"error": exc.code})
        except (BrokenPipeError, ConnectionResetError, TimeoutError):
            pass
        except Exception:
            self._send(500, {"error": "request_failed"})

    def do_GET(self):
        self._handle()

    def do_POST(self):
        self._handle(write=True)


def create_server(app, port=0):
    server = ThreadingHTTPServer(("127.0.0.1", port), ResearchHandler)
    server.app = app
    return server


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--team", required=True, choices=[TEAM])
    parser.add_argument("--port", type=int, default=8765)
    args = parser.parse_args()
    if not 1 <= args.port <= 65535:
        parser.error("--port must be between 1 and 65535")
    app = ResearchApp(ROOT)
    try:
        server = create_server(app, args.port)
    except OSError:
        parser.exit(1, "Cannot bind local port; try another --port.\n")
    def stop(signum, frame):
        raise KeyboardInterrupt()
    signal.signal(signal.SIGTERM, stop)
    print("Research Desk: http://127.0.0.1:%d (Ctrl+C to stop)" % server.server_port, flush=True)
    try:
        server.serve_forever(poll_interval=0.2)
    except KeyboardInterrupt:
        print("Closing local server; allowing any active bounded run to finish.", flush=True)
    finally:
        # The model owns a child process group. Drain its timeout/cleanup path
        # rather than killing an outer process and leaving a model orphaned.
        signal.signal(signal.SIGINT, signal.SIG_IGN)
        signal.signal(signal.SIGTERM, signal.SIG_IGN)
        with app.lock:
            app.closing = True
        server.server_close()
        app.join_worker()


if __name__ == "__main__":
    main()
