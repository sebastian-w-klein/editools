"""The Hyphenation Checker end to end, through its page on the shared server."""

from __future__ import annotations

from editools import config


def test_a_proof_can_be_audited_through_the_window(server, get, post_file,
                                                   proof_pdf, monkeypatch):
    monkeypatch.setattr(config, "api_key", lambda *a, **k: "")
    payload = post_file(server + "/hyphen/audit", "pdf", "proof.pdf",
                        proof_pdf.read_bytes())

    assert payload.get("error") is None, payload.get("error")
    assert payload["counts"]["pages"] == 4
    assert payload["counts"]["violations"] >= 5
    assert any(row["display"] == "butch-/er's" for row in payload["flagged"])

    status, spreadsheet = get(server + "/hyphen/download/" + payload["id"])
    assert status == 200 and spreadsheet[:2] == b"PK"   # a real .xlsx
