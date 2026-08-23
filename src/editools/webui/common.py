"""The parts of the local web server both checkers share.

Each checker keeps its own page, its own colour and its own name, because to
the person using them they are two different tools. What they have no reason
to disagree about — how an upload is unpacked, how a reply is sent, which
requests are refused — lives here and is written once.
"""

from __future__ import annotations

import http.server
import json
import tempfile
from email.parser import BytesParser
from email.policy import default as default_policy
from pathlib import Path
from urllib.parse import unquote

#: Uploads and results, thrown away when the server stops.
WORKDIR = Path(tempfile.gettempdir()) / "editools-ui"

#: Finished files by job id, for the download link the page shows afterwards.
RESULTS: dict[str, Path] = {}


def parse_upload(headers, body: bytes):
    """Pull the uploaded file, and any form fields, out of a multipart body.

    Returns ``(filename, data, fields)``, or None if there was no file. The
    Index Checker sends a field alongside the file and the Hyphenation Checker
    does not, so fields come back either way and the caller ignores what it
    does not want.
    """
    content_type = headers.get("Content-Type", "")
    if "multipart/form-data" not in content_type:
        return None
    raw = (b"Content-Type: " + content_type.encode()
           + b"\r\nMIME-Version: 1.0\r\n\r\n" + body)
    message = BytesParser(policy=default_policy).parsebytes(raw)
    upload, fields = None, {}
    for part in message.iter_parts():
        filename = part.get_filename()
        if filename:
            upload = (unquote(filename), part.get_payload(decode=True))
        else:
            name = part.get_param("name", header="content-disposition")
            if name:
                fields[name] = part.get_payload(decode=True).decode(
                    "utf-8", "replace").strip()
    return (upload[0], upload[1], fields) if upload else None


class BaseHandler(http.server.BaseHTTPRequestHandler):
    """Replies, and the one check worth making on a localhost server."""

    server_version = "editools"

    def log_message(self, fmt, *args):        # quieter than the default
        pass

    def send_bytes(self, code, body, content_type, extra=None):
        self.send_response(code)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        for key, value in (extra or {}).items():
            self.send_header(key, value)
        self.end_headers()
        self.wfile.write(body)

    def send_html(self, page: str):
        self.send_bytes(200, page.encode(), "text/html; charset=utf-8")

    def send_json(self, code, payload):
        self.send_bytes(code, json.dumps(payload).encode(), "application/json")

    def send_result(self, key: str, content_type: str, expired: str):
        """Hand back a finished file, or say plainly that it has gone."""
        path = RESULTS.get(unquote(key))
        if not path or not path.exists():
            self.send_json(404, {"error": expired})
            return
        self.send_bytes(
            200, path.read_bytes(), content_type,
            {"Content-Disposition": f'attachment; filename="{path.name}"'},
        )

    def from_this_machine(self) -> bool:
        """Reject posts from a page on some other site.

        The server listens on localhost, but any web page the user happens to
        have open can still post to localhost. Nothing here is dangerous, but
        a stray request should not be able to overwrite a saved key.
        """
        origin = self.headers.get("Origin")
        if origin is None:
            return True  # not a cross-site request
        return origin in (f"http://{self.headers.get('Host', '')}",
                          "http://localhost", "http://127.0.0.1")

    def read_body(self) -> bytes:
        return self.rfile.read(int(self.headers.get("Content-Length", 0)))


def new_job() -> tuple[str, Path]:
    """A fresh id and an empty folder to work in."""
    import uuid

    WORKDIR.mkdir(parents=True, exist_ok=True)
    job = uuid.uuid4().hex
    folder = WORKDIR / job
    folder.mkdir()
    return job, folder
