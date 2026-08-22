"""Page references, against the forms in the guidelines."""

import pytest

from indexcheck.pagerefs import elide, parse, unelide


@pytest.mark.parametrize("start,end,expected", [
    (22, 23, "23"),        # not 22–3
    (143, 147, "47"),      # not 143–7 or 143–147
    (221, 235, "35"),      # not 221–235
    (310, 311, "11"),
    (412, 417, "17"),
    (608, 609, "609"),     # §9 exception: the x00–x09 band takes three digits
    (100, 109, "109"),
])
def test_elision_follows_section_9(start, end, expected):
    assert elide(start, end) == expected


@pytest.mark.parametrize("start,written,expected", [
    (171, "72", 172), (310, "11", 311), (105, "106", 106), (98, "102", 102),
])
def test_un_eliding_a_range(start, written, expected):
    assert unelide(start, written) == expected


def test_plain_references_and_ranges():
    refs = parse("13, 15, 171–72")
    assert [(r.page, r.end) for r in refs] == [(13, None), (15, None), (171, 172)]


def test_footnote_forms_section_17():
    assert parse("82n")[0].note_marker == "n"
    assert parse("82 and n")[0].has_and is True


def test_a_note_list_stops_where_the_italics_stop():
    """'304n1, 305nn1, 7' is note 1 on 304, then notes 1 and 7 on 305 —
    not a single run of note numbers."""
    refs = parse("304n1, 305nn1, 7")
    assert [(r.page, r.note_marker, r.note_numbers) for r in refs] == [
        (304, "n", [1]), (305, "nn", [1, 7])]


def test_a_year_in_brackets_is_not_a_page_number():
    """'market share of (1917), 223' has one reference, not two."""
    assert [r.page for r in parse("market share of (1917), 223")] == [223]


def test_a_cross_reference_in_brackets_is_not_a_page_number():
    assert [r.page for r in parse("171–72 (see also Bell System)")] == [171]
