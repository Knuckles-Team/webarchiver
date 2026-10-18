"""Local fixture web server: tests never reach the live internet."""

from __future__ import annotations

import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import pytest

FIXTURES = Path(__file__).parent / "fixtures"

ROUTES: dict[str, tuple[int, str, bytes, dict[str, str]]] = {
    "/robots.txt": (
        200,
        "text/plain",
        b"User-agent: *\nDisallow: /private/\n",
        {},
    ),
    "/article": (
        200,
        "text/html; charset=utf-8",
        (FIXTURES / "article.html").read_bytes(),
        {},
    ),
    "/moved": (301, "text/plain", b"", {"Location": "/article"}),
    "/private/secret": (200, "text/html", b"<p>secret</p>", {}),
    "/image.png": (200, "image/png", b"\x89PNG\r\n", {}),
    "/huge": (200, "text/html", b"<p>" + b"x" * 4096 + b"</p>", {}),
    "/empty": (200, "text/html", b"<html><body></body></html>", {}),
    "/gone": (404, "text/html", b"<p>missing</p>", {}),
}


class _Handler(BaseHTTPRequestHandler):
    def do_GET(self) -> None:  # noqa: N802 - stdlib handler name
        status, ctype, body, headers = ROUTES.get(
            self.path, (404, "text/plain", b"not found", {})
        )
        self.send_response(status)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        for name, value in headers.items():
            self.send_header(name, value)
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, *args: object) -> None:
        return


@pytest.fixture(scope="session")
def site() -> str:
    server = ThreadingHTTPServer(("127.0.0.1", 0), _Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    yield f"http://127.0.0.1:{server.server_address[1]}"
    server.shutdown()
