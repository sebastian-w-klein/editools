"""Fixtures for the shared parts: a real server on a free port."""

from __future__ import annotations

import json
import threading
import urllib.error
import urllib.request
from http.server import ThreadingHTTPServer

import pytest

from editools import webui


@pytest.fixture
def server():
    """A real server on a free port, torn down after the test."""
    httpd = ThreadingHTTPServer(("127.0.0.1", 0), webui.Handler)
    thread = threading.Thread(target=httpd.serve_forever, daemon=True)
    thread.start()
    yield f"http://127.0.0.1:{httpd.server_address[1]}"
    httpd.shutdown()
    httpd.server_close()


@pytest.fixture
def get():
    def fetch(url: str):
        with urllib.request.urlopen(url, timeout=10) as response:
            return response.status, response.read()
    return fetch


@pytest.fixture
def post_file():
    """Post one file as a browser would, and read the JSON back."""
    def send(url: str, field: str, filename: str, data: bytes,
             fields: dict | None = None, timeout: int = 120):
        boundary = "----editools-test"
        body = b""
        for name, value in (fields or {}).items():
            body += (f"--{boundary}\r\n"
                     f'Content-Disposition: form-data; name="{name}"\r\n\r\n'
                     f"{value}\r\n").encode()
        body += (
            f"--{boundary}\r\n"
            f'Content-Disposition: form-data; name="{field}"; filename="{filename}"\r\n'
            f"Content-Type: application/octet-stream\r\n\r\n"
        ).encode() + data + f"\r\n--{boundary}--\r\n".encode()

        request = urllib.request.Request(
            url, data=body, method="POST",
            headers={"Content-Type": f"multipart/form-data; boundary={boundary}"},
        )
        with urllib.request.urlopen(request, timeout=timeout) as response:
            return json.loads(response.read())
    return send
