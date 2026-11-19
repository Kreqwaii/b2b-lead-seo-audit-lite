#!/usr/bin/env python3
"""
B2B Lead & SEO Audit CLI (Lite) — 100% Python 3.9+ stdlib, zero external dependencies.

Audits a single URL for HTTP status, response time, HTTPS, <title>, <meta name="description">,
<meta name="viewport">, footer copyright year, and extracts valid contact email addresses.
"""

from __future__ import annotations

import argparse
from html.parser import HTMLParser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import re
import ssl
import sys
import threading
import time
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urlparse
from urllib.request import Request, urlopen

USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/124.0.0.0 Safari/537.36"
)

EMAIL_RE = re.compile(r"[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,24}")
COPYRIGHT_RE = re.compile(
    r"(?:©|&copy;|copyright)\s*(?:\d{4}\s*[-–—]\s*)?(20\d{2}|19\d{2})",
    re.IGNORECASE,
)

IGNORED_EMAIL_EXTENSIONS = (
    ".png",
    ".jpg",
    ".jpeg",
    ".gif",
    ".svg",
    ".webp",
    ".ico",
    ".css",
    ".js",
    ".woff",
    ".woff2",
    ".ttf",
    ".pdf",
    ".mp4",
)

IGNORED_EMAIL_DOMAINS = {
    "example.com",
    "example.org",
    "example.net",
    "test.com",
    "domain.com",
    "yourdomain.com",
    "email.com",
    "sentry.io",
    "wixpress.com",
    "placeholder.com",
}


class _SEOHTMLParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.in_title = False
        self.title_parts: list[str] = []
        self.meta_description: str | None = None
        self.has_viewport = False
        self.mailto_emails: list[str] = []
        self.text_parts: list[str] = []
        self._skip_text = False

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        tag_l = tag.lower()
        attr_map = {k.lower(): (v or "") for k, v in attrs}

        if tag_l == "title":
            self.in_title = True
        elif tag_l in ("script", "style", "noscript"):
            self._skip_text = True
        elif tag_l == "meta":
            name = attr_map.get("name", "").strip().lower()
            if name == "description" and self.meta_description is None:
                content = attr_map.get("content", "").strip()
                if content:
                    self.meta_description = content
            elif name == "viewport":
                if attr_map.get("content", "").strip():
                    self.has_viewport = True
        elif tag_l == "a":
            href = attr_map.get("href", "").strip()
            if href.lower().startswith("mailto:"):
                raw_email = href[7:].split("?", 1)[0].strip()
                if raw_email:
                    self.mailto_emails.append(raw_email)

    def handle_endtag(self, tag: str) -> None:
        tag_l = tag.lower()
        if tag_l == "title":
            self.in_title = False
        elif tag_l in ("script", "style", "noscript"):
            self._skip_text = False

    def handle_data(self, data: str) -> None:
        if self.in_title:
            self.title_parts.append(data)
        if not self._skip_text:
            self.text_parts.append(data)


def normalize_url(raw_url: str) -> str:
    url = raw_url.strip()
    if not url:
        raise ValueError("URL cannot be empty")
    if not url.startswith(("http://", "https://")):
        url = "https://" + url
    parsed = urlparse(url)
    if not parsed.netloc:
        raise ValueError(f"Invalid URL: {raw_url}")
    return url


def is_valid_business_email(email: str) -> bool:
    candidate = email.strip().lower().strip(".,;:!?\"'<>()[]{}")
    if "@" not in candidate:
        return False
    local, _, domain = candidate.partition("@")
    if not local or not domain or "." not in domain:
        return False
    if any(candidate.endswith(ext) for ext in IGNORED_EMAIL_EXTENSIONS):
        return False
    if domain in IGNORED_EMAIL_DOMAINS:
        return False
    if any(domain.endswith("." + d) for d in IGNORED_EMAIL_DOMAINS):
        return False
    if ".." in candidate or local.startswith(".") or local.endswith("."):
        return False
    return True


def extract_emails(html_text: str, mailto_emails: list[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for raw in [*mailto_emails, *EMAIL_RE.findall(html_text)]:
        cleaned = raw.strip().lower().strip(".,;:!?\"'<>()[]{}")
        if cleaned not in seen and is_valid_business_email(cleaned):
            seen.add(cleaned)
            result.append(cleaned)
    return result


def extract_copyright_year(text: str) -> int | None:
    matches = COPYRIGHT_RE.findall(text)
    if not matches:
        return None
    years = [int(y) for y in matches if 1990 <= int(y) <= 2100]
    return max(years) if years else None


def audit_url(raw_url: str, timeout: float = 10.0, insecure: bool = False) -> dict[str, Any]:
    url = normalize_url(raw_url)
    req = Request(
        url,
        headers={
            "User-Agent": USER_AGENT,
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.9",
        },
    )

    ssl_ctx = ssl._create_unverified_context() if insecure else ssl.create_default_context()
    start = time.perf_counter()
    status_code: int | None = None
    final_url = url
    html_bytes = b""
    error_msg: str | None = None

    try:
        with urlopen(req, timeout=timeout, context=ssl_ctx) as resp:
            status_code = getattr(resp, "status", None) or resp.getcode()
            final_url = resp.geturl() or url
            html_bytes = resp.read(2 * 1024 * 1024)
    except HTTPError as exc:
        status_code = exc.code
        final_url = exc.geturl() or url
        html_bytes = exc.read(512 * 1024) if exc.fp else b""
        error_msg = f"HTTP {exc.code}: {exc.reason}"
    except URLError as exc:
        error_msg = f"URL Error: {exc.reason}"
    except Exception as exc:  # pragma: no cover
        error_msg = f"Request failed: {exc}"

    elapsed_ms = round((time.perf_counter() - start) * 1000, 1)
    parsed_final = urlparse(final_url)
    is_https = parsed_final.scheme.lower() == "https"

    html_text = html_bytes.decode("utf-8", errors="replace")
    parser = _SEOHTMLParser()
    if html_text:
        parser.feed(html_text)
        parser.close()

    title = " ".join("".join(parser.title_parts).split()) or None
    visible_text = " ".join(parser.text_parts)
    copyright_year = extract_copyright_year(html_text) or extract_copyright_year(visible_text)
    emails = extract_emails(html_text, parser.mailto_emails)

    return {
        "url": url,
        "final_url": final_url,
        "status_code": status_code,
        "response_time_ms": elapsed_ms,
        "https": is_https,
        "title": title,
        "has_title": bool(title),
        "meta_description": parser.meta_description,
        "has_meta_description": bool(parser.meta_description),
        "has_viewport": parser.has_viewport,
        "copyright_year": copyright_year,
        "emails": emails,
        "error": error_msg,
    }


def format_table(result: dict[str, Any]) -> str:
    rows = [
        ("Target URL", result["url"]),
        ("Final URL", result["final_url"]),
        ("HTTP Status", str(result["status_code"]) if result["status_code"] is not None else "N/A"),
        ("Response Time", f"{result['response_time_ms']} ms"),
        ("HTTPS", "Yes" if result["https"] else "No"),
        ("Title", result["title"] or "(missing)"),
        ("Meta Description", result["meta_description"] or "(missing)"),
        ("Viewport Meta", "Yes" if result["has_viewport"] else "No"),
        ("Copyright Year", str(result["copyright_year"]) if result["copyright_year"] else "(not found)"),
        ("Emails Found", ", ".join(result["emails"]) if result["emails"] else "(none)"),
    ]
    if result.get("error"):
        rows.append(("Error", result["error"]))

    key_width = max(len(k) for k, _ in rows)
    lines = [f"{k:<{key_width}} | {v}" for k, v in rows]
    sep = "-" * key_width + "-+-" + "-" * 40
    return "\n".join([lines[0], sep, *lines[1:]])


def run_self_test() -> int:
    sample_html = """<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <title>Apex Dental Studio | Cosmetic Dentistry</title>
  <meta name="description" content="Trusted family and cosmetic dentistry in Austin, TX.">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
</head>
<body>
  <h1>Welcome to Apex Dental</h1>
  <p>Contact us: <a href="mailto:hello@apexdental.io?subject=Booking">hello@apexdental.io</a></p>
  <p>Support: care@apexdental.io</p>
  <img src="hero@2x.png" alt="logo">
  <p>Ignore placeholder: test@example.com and icon@2x.svg</p>
  <footer>&copy; 2021-2025 Apex Dental Studio. All rights reserved.</footer>
</body>
</html>"""

    class _Handler(BaseHTTPRequestHandler):
        def do_GET(self) -> None:  # noqa: N802
            body = sample_html.encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def log_message(self, format: str, *args: object) -> None:
            return

    server = ThreadingHTTPServer(("127.0.0.1", 0), _Handler)
    port = server.server_address[1]
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()

    try:
        res = audit_url(f"http://127.0.0.1:{port}/", timeout=5.0)
        checks = [
            ("status_code == 200", res["status_code"] == 200),
            ("https is False on local http", res["https"] is False),
            ("has_title is True", res["has_title"] is True),
            ("has_meta_description is True", res["has_meta_description"] is True),
            ("has_viewport is True", res["has_viewport"] is True),
            ("copyright_year == 2025", res["copyright_year"] == 2025),
            (
                "valid business emails extracted",
                res["emails"] == ["hello@apexdental.io", "care@apexdental.io"],
            ),
            ("no error", res["error"] is None),
        ]
        passed = sum(1 for _, ok in checks if ok)
        total = len(checks)
        for name, ok in checks:
            print(f"[{'PASS' if ok else 'FAIL'}] {name}")
        print(f"{passed}/{total} CHECKS PASSED")
        return 0 if passed == total else 1
    finally:
        server.shutdown()
        server.server_close()


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="audit_url.py",
        description="Lite Single-URL B2B Lead & SEO Audit CLI (100% Python stdlib).",
    )
    parser.add_argument("url", nargs="?", help="Target website URL to audit (e.g. https://example.org)")
    parser.add_argument(
        "--format",
        choices=("table", "json"),
        default="table",
        help="Output format (default: table)",
    )
    parser.add_argument(
        "--timeout",
        type=float,
        default=10.0,
        help="HTTP request timeout in seconds (default: 10.0)",
    )
    parser.add_argument(
        "--insecure",
        action="store_true",
        help="Disable SSL certificate verification",
    )
    parser.add_argument(
        "--self-test",
        action="store_true",
        help="Run built-in self-test against a local ThreadingHTTPServer",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.self_test:
        return run_self_test()

    if not args.url:
        parser.print_help()
        return 2

    try:
        result = audit_url(args.url, timeout=args.timeout, insecure=args.insecure)
    except ValueError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 2

    if args.format == "json":
        print(json.dumps(result, indent=2, ensure_ascii=False))
    else:
        print(format_table(result))

    return 0 if result["status_code"] is not None and result["status_code"] < 400 else 1


if __name__ == "__main__":
    raise SystemExit(main())
