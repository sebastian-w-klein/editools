"""Extraction has to survive real typesetting before any rule can help."""

from __future__ import annotations

from editools.hyphen import extract
from editools.hyphen.textutil import split_leading_word, split_trailing_word


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


# -- words divided across a page turn ----------------------------------------

def test_a_word_divided_across_a_page_turn_is_rejoined(page_turn_pdf):
    """The continuation is on the next page's first body line, not its head."""
    document = extract.load(str(page_turn_pdf))
    words = {brk.word for brk in document.breaks}
    assert "considered" in words
    assert "afternoon" in words


def test_a_page_turn_break_is_reported_on_the_page_it_starts(page_turn_pdf):
    document = extract.load(str(page_turn_pdf))
    by_word = {brk.word: brk for brk in document.breaks}
    assert by_word["considered"].book_page == "40"   # the hyphen is on p.40
    assert by_word["afternoon"].book_page == "43"
    assert all(by_word[w].crosses_page for w in ("considered", "afternoon"))


def test_running_heads_are_found_by_position_when_they_never_repeat(page_turn_pdf):
    """Chapter-named heads appear on too few pages to be caught by counting.

    Each head is on 2 of 6 pages here. Position in the margin identifies them
    anyway — otherwise the head becomes the continuation of the broken word.
    """
    document = extract.load(str(page_turn_pdf))
    assert not document.running_heads, "this proof has no head repeating often enough"
    for page in document.pages:
        assert len(document.furniture.marks(page.number)) >= 2  # head and folio


def test_no_head_or_folio_is_ever_treated_as_part_of_a_word(page_turn_pdf):
    document = extract.load(str(page_turn_pdf))
    for brk in document.breaks:
        assert "ONE" not in brk.word and "TWO" not in brk.word
        assert "THREE" not in brk.word
        assert not any(ch.isdigit() for ch in brk.word)


def test_an_unreadable_page_turn_is_flagged_rather_than_invented(mw):
    """If the continuation still reads as furniture, say so — do not guess.

    A join that produced "considONE" would otherwise be checked as a word and
    reported as a confident violation of a rule, against a word nobody set.
    """
    from editools.hyphen import rules
    from editools.hyphen.model import Break, Verdict

    brk = Break(
        pdf_page=41, book_page="40", line_index=30, left="consid", right="ONE",
        hyphen_char="-", line_text="…consid-", next_line_text="ONE: The Garden",
        kind="furniture", crosses_page=True,
    )
    rules.evaluate(brk, rules.Context(dictionary=mw, tokens={}))
    assert brk.worst is not Verdict.VIOLATION
    assert "running head or folio" in " ".join(brk.notes)
