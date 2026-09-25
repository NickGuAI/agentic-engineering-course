#!/usr/bin/env python3
"""Small course-supplied wrapper for Tavily's Search and Extract REST APIs.

This is not Tavily's official CLI or SDK. It uses only the Python standard
library so students can run it with Python 3.9 or newer and no installation.
The API key is read from TAVILY_API_KEY and is never included in output.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from typing import Any, Dict, Optional, Sequence, TextIO
from urllib.error import HTTPError, URLError
from urllib.parse import urlsplit
from urllib.request import Request, urlopen


API_BASE = "https://api.tavily.com"
TIMEOUT_SECONDS = 30
MAX_RESPONSE_BYTES = 2_000_000
MAX_ERROR_CHARS = 1_000
MAX_SEARCH_CONTENT_CHARS = 1_200
MAX_EXTRACT_CONTENT_CHARS = 8_000


def _scrub_value(value: Any, api_key: str) -> Any:
    if isinstance(value, str) and api_key:
        return value.replace(api_key, "[redacted]")
    if isinstance(value, list):
        return [_scrub_value(item, api_key) for item in value]
    if isinstance(value, dict):
        return {key: _scrub_value(item, api_key) for key, item in value.items()}
    return value


def _write_json(data: Dict[str, Any], stream: TextIO) -> None:
    api_key = os.environ.get("TAVILY_API_KEY", "").strip()
    json.dump(_scrub_value(data, api_key), stream, ensure_ascii=False, indent=2)
    stream.write("\n")


def _bounded_text(value: Any, limit: int) -> tuple[str, bool]:
    text = value if isinstance(value, str) else ""
    if len(text) <= limit:
        return text, False
    return text[:limit], True


def _safe_error_text(value: Any, api_key: str, limit: int = MAX_ERROR_CHARS) -> str:
    """Bound untrusted API error text and scrub any accidental key echo."""
    if not isinstance(value, str):
        value = "Tavily returned an error response."
    value = value.replace(api_key, "[redacted]") if api_key else value
    value = re.sub(r"(?i)(bearer\s+)[^\s,;]+", r"\1[redacted]", value)
    value = re.sub(r"(?i)(api[_ -]?key\s*[:=]\s*)[^\s,;]+", r"\1[redacted]", value)
    if len(value) > limit:
        value = value[:limit] + "…"
    return value


def _api_error_message(body: bytes, api_key: str) -> str:
    text = body.decode("utf-8", errors="replace")
    try:
        parsed = json.loads(text)
    except json.JSONDecodeError:
        parsed = None

    if isinstance(parsed, dict):
        detail = parsed.get("detail")
        if isinstance(detail, dict) and isinstance(detail.get("error"), str):
            text = detail["error"]
        elif isinstance(parsed.get("error"), str):
            text = parsed["error"]
        else:
            text = "Tavily returned an error response."
    elif not text.strip():
        text = "Tavily returned an empty error response."
    return _safe_error_text(text, api_key)


def _emit_error(
    error_type: str,
    message: str,
    *,
    http_status: Optional[int] = None,
    stream: Optional[TextIO] = None,
) -> int:
    _write_json(
        {
            "ok": False,
            "status": "error",
            "http_status": http_status,
            "error": {"type": error_type, "message": message},
        },
        stream if stream is not None else sys.stderr,
    )
    return 2


def _post(endpoint: str, payload: Dict[str, Any], api_key: str) -> tuple[int, Dict[str, Any]]:
    request = Request(
        f"{API_BASE}/{endpoint}",
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
            "Accept": "application/json",
        },
        method="POST",
    )
    try:
        with urlopen(request, timeout=TIMEOUT_SECONDS) as response:
            raw_status = getattr(response, "status", None)
            http_status = int(raw_status if raw_status is not None else response.getcode())
            body = response.read(MAX_RESPONSE_BYTES + 1)
    except HTTPError as exc:
        body = exc.read(MAX_RESPONSE_BYTES + 1)
        raise _TavilyRequestError(
            "http_error", _api_error_message(body, api_key), int(exc.code)
        ) from None
    except (URLError, TimeoutError, OSError) as exc:
        reason = getattr(exc, "reason", None)
        description = str(reason) if reason is not None else "The request could not be completed."
        raise _TavilyRequestError(
            "network_error", _safe_error_text(description, api_key)
        ) from None

    if len(body) > MAX_RESPONSE_BYTES:
        raise _TavilyRequestError(
            "response_too_large",
            f"Tavily response exceeded the {MAX_RESPONSE_BYTES}-byte safety limit.",
            http_status,
        )
    try:
        data = json.loads(body.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError):
        raise _TavilyRequestError(
            "invalid_response", "Tavily returned invalid JSON.", http_status
        ) from None
    if not isinstance(data, dict):
        raise _TavilyRequestError(
            "invalid_response", "Tavily returned JSON with an unexpected shape.", http_status
        )
    return http_status, data


class _TavilyRequestError(Exception):
    def __init__(self, error_type: str, message: str, http_status: Optional[int] = None):
        super().__init__(message)
        self.error_type = error_type
        self.message = message
        self.http_status = http_status


def _valid_web_url(url: str) -> bool:
    try:
        parsed = urlsplit(url)
        return parsed.scheme in {"http", "https"} and bool(parsed.hostname) and not parsed.username and not parsed.password
    except ValueError:
        return False


def _search(query: str, max_results: int, api_key: str, output: TextIO) -> int:
    http_status, response = _post(
        "search",
        {"query": query, "search_depth": "basic", "max_results": max_results},
        api_key,
    )
    api_results = response.get("results")
    if not isinstance(api_results, list):
        raise _TavilyRequestError(
            "invalid_response", "Tavily search response did not contain a results list.", http_status
        )

    results = []
    for result in api_results[:max_results]:
        if not isinstance(result, dict):
            continue
        content, truncated = _bounded_text(result.get("content"), MAX_SEARCH_CONTENT_CHARS)
        normalized = {
            "title": result.get("title") if isinstance(result.get("title"), str) else "",
            "url": result.get("url") if isinstance(result.get("url"), str) else "",
            "content": content,
            "content_truncated": truncated,
        }
        if isinstance(result.get("score"), (int, float)):
            normalized["score"] = result["score"]
        results.append(normalized)

    usage = response.get("usage")
    result: Dict[str, Any] = {
        "ok": True,
        "status": "success",
        "http_status": http_status,
        "query": response.get("query") if isinstance(response.get("query"), str) else query,
        "result_count": len(results),
        "results": results,
    }
    if isinstance(response.get("request_id"), str):
        result["request_id"] = response["request_id"]
    if response.get("response_time") is not None:
        result["response_time"] = response["response_time"]
    if isinstance(usage, dict) and usage.get("credits") is not None:
        result["credits_used"] = usage["credits"]
    _write_json(result, output)
    return 0


def _extract(url: str, api_key: str, output: TextIO) -> int:
    http_status, response = _post(
        "extract",
        {"urls": url, "format": "markdown", "extract_depth": "basic"},
        api_key,
    )
    api_results = response.get("results", [])
    failed_results = response.get("failed_results", [])
    if not isinstance(api_results, list) or not isinstance(failed_results, list):
        raise _TavilyRequestError(
            "invalid_response", "Tavily extract response had an unexpected results shape.", http_status
        )

    results = []
    for item in api_results[:1]:
        if not isinstance(item, dict):
            continue
        content, truncated = _bounded_text(item.get("raw_content"), MAX_EXTRACT_CONTENT_CHARS)
        results.append(
            {
                "url": item.get("url") if isinstance(item.get("url"), str) else url,
                "content": content,
                "content_truncated": truncated,
            }
        )

    failures = []
    for item in failed_results[:1]:
        if not isinstance(item, dict):
            continue
        failures.append(
            {
                "url": item.get("url") if isinstance(item.get("url"), str) else url,
                "error": _safe_error_text(item.get("error"), api_key, limit=500),
            }
        )

    status = "success" if results and not failures else "partial" if results and failures else "error"
    result = {
        "ok": status != "error",
        "status": status,
        "http_status": http_status,
        "result_count": len(results),
        "results": results,
        "failed_results": failures,
    }
    if isinstance(response.get("request_id"), str):
        result["request_id"] = response["request_id"]
    if response.get("response_time") is not None:
        result["response_time"] = response["response_time"]
    if status == "error":
        result["error"] = {"type": "no_extracted_content", "message": "Tavily did not extract content from the URL."}
    _write_json(result, output)
    return 0 if status != "error" else 1


class _JsonArgumentParser(argparse.ArgumentParser):
    def error(self, message: str) -> None:
        _emit_error("invalid_arguments", message)
        raise SystemExit(2)


def _build_parser() -> argparse.ArgumentParser:
    parser = _JsonArgumentParser(
        description="Course-supplied wrapper for Tavily Search and Extract (not an official Tavily CLI)."
    )
    subparsers = parser.add_subparsers(dest="command", required=True, parser_class=_JsonArgumentParser)

    search_parser = subparsers.add_parser("search", help="Search the web with Tavily.")
    search_parser.add_argument("query", nargs="+", help="Words that describe the research question.")
    search_parser.add_argument(
        "--max-results", type=int, default=3, choices=range(1, 6), metavar="1..5",
        help="Maximum results to return (default: 3; range: 1..5).",
    )

    extract_parser = subparsers.add_parser("extract", help="Extract one public web page with Tavily.")
    extract_parser.add_argument("url", help="A public HTTP or HTTPS page URL.")
    return parser


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)
    api_key = os.environ.get("TAVILY_API_KEY", "").strip()
    if not api_key:
        return _emit_error(
            "missing_api_key", "Set TAVILY_API_KEY in the environment before using this wrapper."
        )

    try:
        if args.command == "search":
            query = " ".join(args.query).strip()
            if not query:
                return _emit_error("invalid_arguments", "Search query must not be empty.")
            return _search(query, args.max_results, api_key, sys.stdout)
        if args.command == "extract":
            if not _valid_web_url(args.url):
                return _emit_error("invalid_url", "Use one public URL beginning with http:// or https://.")
            return _extract(args.url, api_key, sys.stdout)
        return _emit_error("unsupported_command", "Only search and extract are supported.")
    except _TavilyRequestError as exc:
        return _emit_error(exc.error_type, exc.message, http_status=exc.http_status)
    except Exception:
        # Do not echo exception reprs, which can contain request details.
        return _emit_error("unexpected_error", "The Tavily request could not be completed safely.")


if __name__ == "__main__":
    raise SystemExit(main())
