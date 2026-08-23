"""The Index Checker end to end, through its page on the shared server."""

from __future__ import annotations


def test_an_index_can_be_checked_through_the_window(server, get, post_file, make_docx):
    path = make_docx(
        "Adams, John, 12, 11",              # pages out of order
        "Baker, Sarah, 308-310",            # a hyphen, and an unelided range
    )
    payload = post_file(server + "/index/check", "file", path.name,
                        path.read_bytes(), fields={"last_page": "400"})

    assert payload.get("error") is None, payload.get("error")
    assert payload["entries"] == 2
    assert payload["fixes"] >= 1 and payload["flags"] >= 1
    assert "page-order" in payload["counts"]

    status, marked = get(server + "/index/download/" + payload["id"])
    assert status == 200 and marked[:2] == b"PK"    # a real .docx


def test_the_index_download_expires_politely(server, get):
    import urllib.error

    try:
        get(server + "/index/download/nosuchjob")
    except urllib.error.HTTPError as exc:
        assert exc.code == 404 and b"expired" in exc.read()
    else:
        raise AssertionError("a missing result should be a 404")
