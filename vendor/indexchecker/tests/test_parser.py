"""Entry structure, per §12, §15 and §16."""

from indexcheck.parser import parse


def test_general_references_then_run_in_subentries():
    entry = parse("New York City, 32–40, 183–89; architecture, 31, 115–16; "
                  "mass transit, 40–45; parks, 54")
    assert entry.term == "New York City"
    assert [r.page for r in entry.general] == [32, 183]
    assert [s.term for s in entry.subentries] == [
        "architecture", "mass transit", "parks"]


def test_a_colon_means_no_general_references():
    entry = parse("New York City: architecture, 31, 115–16; mass transit, 40–45")
    assert entry.colon_form is True
    assert entry.general == []
    assert [s.term for s in entry.subentries] == ["architecture", "mass transit"]


def test_cross_references_are_the_last_subentry():
    entry = parse("art, 290, 457; see also films; literature")
    assert [s.term for s in entry.subentries] == []
    assert [s.text.strip() for s in entry.crossrefs] == ["see also films", "literature"]


def test_a_see_inside_a_subentry_does_not_end_the_list():
    """'lawsuits involving, see patent litigation' is a subentry, and the
    entry carries on with ordinary subentries after it."""
    entry = parse("American Bell Telephone Company, 115, 171; exchanges for, "
                  "123–35; lawsuits involving, see patent litigation; "
                  "predecessors of, 105–106, 110–15")
    assert [s.term for s in entry.subentries] == [
        "exchanges for", "lawsuits involving", "predecessors of"]
    assert entry.crossrefs == []


def test_a_bracketed_see_also_ends_nothing():
    entry = parse("AT&T, 13, 15, 171–72 (see also Bell System); "
                  "area codes created by, 300–301")
    assert entry.term == "AT&T"
    assert [s.term for s in entry.subentries] == ["area codes created by"]


def test_a_dummy_entry_is_all_cross_reference():
    entry = parse("transportation, see mass transit; taxis")
    assert entry.subentries == []
    assert len(entry.crossrefs) == 1


def test_the_illustration_note_is_not_an_entry():
    assert parse("Page numbers in italics refer to illustrations").is_note


def test_a_subentry_may_open_with_a_year():
    """'1956 consent decree for, 391' has one page reference, not two."""
    entry = parse("monopolies, 12; 1956 consent decree for, 391")
    assert [r.page for r in entry.subentries[0].refs] == [391]
