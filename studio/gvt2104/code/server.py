"""Self-contained HTTP server for the Agent News Digest.

Serves the static webpage and a small JSON API. Pure stdlib -- run with:

    python3 code/server.py            # then open http://localhost:8000

Endpoints:
    GET  /                 -> the webpage
    GET  /api/articles     -> ranked articles + learned weights (served from cache)
    POST /api/refresh      -> re-fetch all sources, then return ranked articles
    POST /api/rate         -> {id, rating, note} -> persist + return re-ranked list
    GET  /api/health       -> liveness probe
"""

from __future__ import annotations

import errno
import json
import os
import sys
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import fetcher  # noqa: E402
import ranking  # noqa: E402
import storage  # noqa: E402

STATIC_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "static")
CONTENT_TYPES = {
    ".html": "text/html; charset=utf-8",
    ".css": "text/css; charset=utf-8",
    ".js": "application/javascript; charset=utf-8",
    ".json": "application/json; charset=utf-8",
    ".svg": "image/svg+xml",
}


def _ranked_payload(fetch_result: dict) -> dict:
    ratings = storage.load_ratings()
    ranked = ranking.rank(fetch_result["articles"], ratings)
    weights = ranking.learned_weights(ratings)
    return {
        "articles": ranked,
        "weights": dict(sorted(weights.items(), key=lambda kv: kv[1], reverse=True)),
        "status": fetch_result.get("status", {}),
        "used_fallback": fetch_result.get("used_fallback", False),
        "count": len(ranked),
    }


class Handler(BaseHTTPRequestHandler):
    server_version = "AgentNewsDigest/1.0"

    # -- helpers -----------------------------------------------------------
    def _send_json(self, obj, status: int = 200) -> None:
        body = json.dumps(obj).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _send_file(self, path: str) -> None:
        if not os.path.isfile(path):
            self.send_error(404, "Not found")
            return
        ext = os.path.splitext(path)[1]
        with open(path, "rb") as fh:
            body = fh.read()
        self.send_response(200)
        self.send_header("Content-Type", CONTENT_TYPES.get(ext, "application/octet-stream"))
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _read_body(self) -> dict:
        length = int(self.headers.get("Content-Length", 0) or 0)
        if not length:
            return {}
        try:
            return json.loads(self.rfile.read(length).decode("utf-8"))
        except (ValueError, UnicodeDecodeError):
            return {}

    # -- routes ------------------------------------------------------------
    def do_GET(self) -> None:
        route = self.path.split("?", 1)[0]
        if route == "/api/health":
            self._send_json({"ok": True})
        elif route == "/api/articles":
            self._send_json(_ranked_payload(fetcher.get_articles(refresh=False)))
        elif route in ("/", "/index.html"):
            self._send_file(os.path.join(STATIC_DIR, "index.html"))
        else:
            # serve static assets, guarding against path traversal
            safe = os.path.normpath(route).lstrip("/\\")
            target = os.path.join(STATIC_DIR, safe)
            if os.path.commonpath([STATIC_DIR, os.path.abspath(target)]) != STATIC_DIR:
                self.send_error(403, "Forbidden")
                return
            self._send_file(target)

    def do_POST(self) -> None:
        route = self.path.split("?", 1)[0]
        if route == "/api/refresh":
            self._send_json(_ranked_payload(fetcher.get_articles(refresh=True)))
        elif route == "/api/rate":
            self._handle_rate()
        else:
            self.send_error(404, "Not found")

    def _handle_rate(self) -> None:
        data = self._read_body()
        article_id = data.get("id")
        if not article_id:
            self._send_json({"error": "missing article id"}, status=400)
            return
        try:
            rating = int(data.get("rating", 0))
        except (TypeError, ValueError):
            rating = 0
        rating = max(-1, min(1, rating))  # clamp to {-1, 0, 1}
        note = str(data.get("note", ""))
        tags = data.get("tags") or []
        title = str(data.get("title", ""))
        storage.save_rating(article_id, rating, note, tags, title)
        # return the freshly re-ranked list (served from cache, no re-fetch)
        self._send_json(_ranked_payload(fetcher.get_articles(refresh=False)))

    def log_message(self, fmt, *args):  # quieter, single-line logs
        sys.stderr.write("%s - %s\n" % (self.address_string(), fmt % args))


def _serve(host: str, port: int, max_tries: int = 20) -> ThreadingHTTPServer:
    """Bind to ``port``; if it's in use, fall forward to the next free port.

    If PORT was set explicitly, honor it exactly and don't hunt for another.
    """
    explicit = "PORT" in os.environ
    for candidate in range(port, port + max_tries):
        try:
            return ThreadingHTTPServer((host, candidate), Handler)
        except OSError as exc:
            if errno.EADDRINUSE not in (exc.errno,) or explicit:
                raise
            print(f"Port {candidate} is in use, trying {candidate + 1}…")
    raise SystemExit(f"No free port found in range {port}-{port + max_tries - 1}.")


def main() -> None:
    host = os.environ.get("HOST", "127.0.0.1")
    port = int(os.environ.get("PORT", "8765"))
    httpd = _serve(host, port)
    bound_port = httpd.server_address[1]
    print(f"Agent News Digest running at http://{host}:{bound_port}  (Ctrl-C to stop)")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nShutting down.")
        httpd.shutdown()


if __name__ == "__main__":
    main()
