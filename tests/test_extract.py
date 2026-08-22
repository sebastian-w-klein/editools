"""Extraction has to survive real typesetting before any rule can help."""

from __future__ import annotations

from hyphencheck import extract
from hyphencheck.textutil import split_leading_word, split_trailing_word


def test_words_are_not_run_together(proof_pdf):
    """pdfplumber's default word gap is wider than a space in book type."""
    document = extract.load(str(proof_pdf))
    text = " ".join(line.text for page in document.pages for line in page.lines)
    assert "It was a cold morning" in text


def test_printed_page_numbers_are_read_off_the_page(proof_pdf):
    document = extract.load(str(proof_pdf))
    assert [page.folio for page in document.pages] == ["1", "2", "3", "4"]


def test_running_heads_are_detected_and_ignored(proof_pdf):
    document = extract.load(str(proof_pdf))
    assert "s wa n s" in document.running_heads
    assert all("WA N S" not in brk.line_text for brk in document.breaks)


def test_every_break_in_the_proof_is_found(proof_pdf):
    document = extract.load(str(proof_pdf))
    found = {brk.display for brk in document.breaks}
    for expected in [
        "butch-/er's", "cher-/ries", "cross-/legged", "fold-/up",
        "photo-/grapher", "Ply-/mouth", "Eng-/lish", "co-/meth",
        "Mar-/volene", "Marvol-/ene", "dis-/pleasure", "displea-/sure",
        "poverty-/stricken", "pov-/erty-stricken", "power-/ful",
        "dépay-/sement", "Wordswor-/th",
    ]:
        assert expected in found, f"missed {expected}"


def test_em_dash_adjacency_is_captured_on_both_sides(proof_pdf):
    document = extract.load(str(proof_pdf))
    by_display = {brk.display: brk for brk in document.breaks}
    assert by_display["cher-/ries"].char_after.startswith("—")
    assert by_display["power-/ful"].char_before.endswith("—")


def test_a_soft_hyphen_fused_to_an_em_dash_is_not_a_word_division(proof_pdf):
    document = extract.load(str(proof_pdf))
    artifacts = [brk for brk in document.breaks if brk.kind == "artifact"]
    assert [brk.left for brk in artifacts] == ["patrons"]


def test_urls_are_recognised(proof_pdf):
    document = extract.load(str(proof_pdf))
    urls = [brk for brk in document.breaks if brk.kind == "url"]
    assert [brk.display for brk in urls] == ["www.exam-/ple.com"]


def test_italic_setting_is_detected(proof_pdf):
    document = extract.load(str(proof_pdf))
    by_display = {brk.display: brk for brk in document.breaks}
    assert by_display["dépay-/sement"].italic
    assert not by_display["butch-/er's"].italic


def test_the_book_is_indexed_for_compound_checks(proof_pdf):
    document = extract.load(str(proof_pdf))
    assert document.token_appears("morning") == 1


def test_trailing_word_keeps_an_em_dash_in_the_prefix():
    assert split_trailing_word("encroachment—power") == ("encroachment—", "power", "")


def test_leading_word_keeps_an_em_dash_in_the_suffix():
    assert split_leading_word("ries—or") == ("", "ries", "—or")


def test_possessives_survive_tokenisation():
    assert split_leading_word("er's,") == ("", "er's", ",")
