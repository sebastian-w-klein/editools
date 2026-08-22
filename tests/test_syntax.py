"""The syntax rules, per §12, §15 and §16."""

import pytest

from indexcheck.parser import parse
from indexcheck.rules import check_syntax


def syntax(text):
    return [f.message for f in check_syntax(parse(text))]


def test_a_well_formed_entry_is_quiet():
    assert syntax("New York City, 32–40, 183–89; architecture, 31, 115–16; "
                  "mass transit, 40–45") == []


def test_a_missing_space_after_a_comma():
    assert syntax("Adams, 273, 276, 294,341") == [
        "the gap between page numbers takes ', ', not ','"]


def test_a_missing_semicolon_before_a_subentry():
    """'Communications Act of, 402 Centennial Exhibition and, 85' has run two
    subentries together."""
    assert syntax("Congress, 12; Communications Act of, 402 "
                  "Centennial Exhibition and, 85")


def test_a_bracketed_cross_reference_may_sit_before_a_subentry():
    """§15 allows '171–72 (see also Bell System); area codes created by'."""
    assert syntax("AT&T, 13, 15, 171–72 (see also Bell System); "
                  "area codes created by, 300–301") == []


def test_see_also_needs_a_semicolon_or_bracket_before_it():
    assert syntax("art, 290, 457, see also films")
    assert syntax("art, 290, 457; see also films") == []
    assert syntax("AT&T, 13 (see also Bell System)") == []


def test_a_cross_reference_entry_carries_no_page_numbers():
    """§16: a dummy entry is only a cross-reference."""
    assert syntax("transportation, 15, see mass transit")
    assert syntax("transportation, see mass transit") == []


def test_a_see_in_a_subentry_does_not_trip_the_page_number_rule():
    assert syntax("American Bell Telephone Company, 115, 171; "
                  "lawsuits involving, see patent litigation") == []
