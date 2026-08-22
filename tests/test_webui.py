"""The local window: serving the page, taking a key, running an audit.

Merriam-Webster is never reached from a test, so key verification is stubbed
at the seam the handler actually calls.
"""

from __future__ import annotations

import json
import threading
import urllib.error
import urllib.request
from http.server import ThreadingHTTPServer

import pytest

from hyphencheck import config, webui


@pytest.fixture
def server():
    """A real server on a free port, torn down after the test."""
    httpd = ThreadingHTTPServer(("127.0.0.1", 0), webui.Handler)
    thread = threading.Thread(target=httpd.serve_forever, daemon=True)
    thread.start()
    yield f"http://127.0.0.1:{httpd.server_address[1]}"
    httpd.shutdown()
    httpd.server_close()


def get(url: str):
    with urllib.request.urlopen(url, timeout=10) as response:
        return response.status, response.read()


def post_json(url: str, payload: dict, origin: str | None = None):
    request = urllib.request.Request(
        url, data=json.dumps(payload).encode(),
        headers={"Content-Type": "application/json"}, method="POST",
    )
    if origin:
        request.add_header("Origin", origin)
    try:
        with urllib.request.urlopen(request, timeout=10) as response:
            return response.status, json.loads(response.read())
    except urllib.error.HTTPError as exc:
        return exc.code, json.loads(exc.read())


def test_the_page_offers_somewhere_to_paste_a_key(server):
    status, body = get(server + "/")
    page = body.decode()
    assert status == 200
    assert 'id="keyinput"' in page and "/key" in page


def test_status_reports_whether_a_key_is_saved(server, monkeypatch):
    monkeypatch.setattr(config, "api_key", lambda *a, **k: "")
    assert get(server + "/status")[1] == b'{"has_key": false}'


def test_a_working_key_is_accepted(server, monkeypatch):
    saved = {}

    def fake_verify(key):
        saved["key"] = key
        return True, "Key saved and working (cemetery → cem·e·ter·y)."

    monkeypatch.setattr(config, "verify_and_save", fake_verify)
    status, payload = post_json(server + "/key", {"key": "abc-123"})
    assert status == 200 and payload["ok"] is True
    assert saved["key"] == "abc-123"
    assert "cem·e·ter·y" in payload["message"]


def test_a_bad_key_is_reported_not_saved(server, monkeypatch):
    monkeypatch.setattr(
        config, "verify_and_save",
        lambda key: (False, "That key did not work (HTTP 403)."),
    )
    _, payload = post_json(server + "/key", {"key": "wrong"})
    assert payload["ok"] is False and "did not work" in payload["message"]


def test_an_unreachable_dictionary_does_not_crash_the_window(server, monkeypatch):
    def explode(key):
        raise ConnectionError("name resolution failed")

    monkeypatch.setattr(config, "verify_and_save", explode)
    _, payload = post_json(server + "/key", {"key": "abc"})
    assert payload["ok"] is False and "Could not reach" in payload["message"]


def test_another_site_cannot_overwrite_the_saved_key(server, monkeypatch):
    monkeypatch.setattr(
        config, "verify_and_save",
        lambda key: pytest.fail("a cross-site post reached the key handler"),
    )
    status, payload = post_json(
        server + "/key", {"key": "evil"}, origin="http://evil.example"
    )
    assert status == 403 and "another site" in payload["error"]


def test_a_proof_can_be_audited_through_the_window(server, proof_pdf, monkeypatch):
    monkeypatch.setattr(config, "api_key", lambda *a, **k: "")
    boundary = "----hyphencheck-test"
    body = (
        f"--{boundary}\r\n"
        f'Content-Disposition: form-data; name="pdf"; filename="proof.pdf"\r\n'
        f"Content-Type: application/pdf\r\n\r\n"
    ).encode() + proof_pdf.read_bytes() + f"\r\n--{boundary}--\r\n".encode()

    request = urllib.request.Request(
        server + "/audit", data=body, method="POST",
        headers={"Content-Type": f"multipart/form-data; boundary={boundary}"},
    )
    with urllib.request.urlopen(request, timeout=120) as response:
        payload = json.loads(response.read())

    assert payload.get("error") is None, payload.get("error")
    assert payload["counts"]["pages"] == 4
    assert payload["counts"]["violations"] >= 5
    assert any(row["display"] == "butch-/er's" for row in payload["flagged"])

    status, spreadsheet = get(server + "/download/" + payload["id"])
    assert status == 200 and spreadsheet[:2] == b"PK"  # a real .xlsx
