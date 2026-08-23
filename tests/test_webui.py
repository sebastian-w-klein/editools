"""The local window: two tools behind one server.

Merriam-Webster is never reached from a test, so key verification is stubbed
at the seam the handler actually calls.
"""

from __future__ import annotations

import json
import urllib.error
import urllib.request

import pytest

from editools import config, webui


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


# -- two tools, told apart ---------------------------------------------------

def test_the_front_page_offers_both_tools(server, get):
    status, body = get(server + "/")
    page = body.decode()
    assert status == 200
    assert "Index Checker" in page and "Hyphenation Checker" in page
    assert 'href="/index/"' in page and 'href="/hyphen/"' in page


def test_each_tool_has_its_own_page(server, get):
    index = get(server + "/index/")[1].decode()
    hyphen = get(server + "/hyphen/")[1].decode()
    assert "<title>Index Checker</title>" in index
    assert "<title>Hyphenation Checker</title>" in hyphen
    # Different enough to look like different tools, not one tool twice.
    assert "#7a2e2e" in index and "#2a4f7c" in hyphen
    # And each can be left for the other.
    assert 'href="/"' in index and 'href="/"' in hyphen


def test_a_tool_only_answers_on_its_own_routes(server, get):
    for gone in ("/check", "/audit", "/status", "/index/audit", "/hyphen/check"):
        with pytest.raises(urllib.error.HTTPError) as raised:
            get(server + gone)
        assert raised.value.code == 404


# -- the Merriam-Webster key, which belongs to the Hyphenation Checker -------

def test_the_hyphen_page_offers_somewhere_to_paste_a_key(server, get):
    page = get(server + "/hyphen/")[1].decode()
    assert 'id="keyinput"' in page and "/hyphen/key" in page


def test_status_reports_whether_a_key_is_saved(server, get, monkeypatch):
    monkeypatch.setattr(config, "api_key", lambda *a, **k: "")
    assert get(server + "/hyphen/status")[1] == b'{"has_key": false}'


def test_a_working_key_is_accepted(server, monkeypatch):
    saved = {}

    def fake_verify(key):
        saved["key"] = key
        return True, "Key saved and working (cemetery → cem·e·ter·y)."

    monkeypatch.setattr(config, "verify_and_save", fake_verify)
    status, payload = post_json(server + "/hyphen/key", {"key": "abc-123"})
    assert status == 200 and payload["ok"] is True
    assert saved["key"] == "abc-123"
    assert "cem·e·ter·y" in payload["message"]


def test_a_bad_key_is_reported_not_saved(server, monkeypatch):
    monkeypatch.setattr(
        config, "verify_and_save",
        lambda key: (False, "That key did not work (HTTP 403)."),
    )
    _, payload = post_json(server + "/hyphen/key", {"key": "wrong"})
    assert payload["ok"] is False and "did not work" in payload["message"]


def test_an_unreachable_dictionary_does_not_crash_the_window(server, monkeypatch):
    def explode(key):
        raise ConnectionError("name resolution failed")

    monkeypatch.setattr(config, "verify_and_save", explode)
    _, payload = post_json(server + "/hyphen/key", {"key": "abc"})
    assert payload["ok"] is False and "Could not reach" in payload["message"]


def test_another_site_cannot_overwrite_the_saved_key(server, monkeypatch):
    monkeypatch.setattr(
        config, "verify_and_save",
        lambda key: pytest.fail("a cross-site post reached the key handler"),
    )
    status, payload = post_json(
        server + "/hyphen/key", {"key": "evil"}, origin="http://evil.example"
    )
    assert status == 403 and "another site" in payload["error"]


def test_another_site_cannot_post_a_file_either(server, monkeypatch):
    for route in ("/index/check", "/hyphen/audit"):
        status, payload = post_json(server + route, {}, origin="http://evil.example")
        assert status == 403 and "another site" in payload["error"]


# -- the update notice -------------------------------------------------------

def test_the_window_reports_what_the_update_did(server, get, monkeypatch):
    """The page shows the state settled at startup, not a fresh lookup.

    Whether there is a new version is decided once, while the tools are
    starting, so that dropping a file never waits on GitHub.
    """
    monkeypatch.setitem(webui.server.UPDATE_STATE, "available", True)
    monkeypatch.setitem(webui.server.UPDATE_STATE, "installed", True)
    payload = json.loads(get(server + "/update-status")[1])
    assert payload["available"] is True and payload["installed"] is True


def test_both_pages_show_the_notice(server, get):
    for page in ("/", "/index/", "/hyphen/"):
        assert "/update-status" in get(server + page)[1].decode()
