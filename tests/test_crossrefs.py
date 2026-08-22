"""Cross-reference targets, per §15 and §16."""

import pytest

from indexcheck.parser import crossref_targets, parse
from indexcheck.rules import check_crossref_targets


def targets(text):
    return [t.text for t in crossref_targets(parse(text))]


def dangling(*entries):
    document = [(i, parse(t)) for i, t in enumerate(entries)]
    return [f.message for _, f in check_crossref_targets(document)]


# -- finding the targets -----------------------------------------------------

def test_a_trailing_run_of_targets_continues_past_semicolons():
    """§15 treats cross-references as the last subentry, separated by ';'."""
    assert targets("art, 290, 457; see also films; literature") == [
        "films", "literature"]


def test_a_see_inside_a_subentry_stops_at_that_subentry():
    """'engineering department of, see Bell Labs; etiquette encouraged by,
    137' points at one entry, not two."""
    assert targets("AT&T, 13; engineering department of, see Bell Labs; "
                   "etiquette encouraged by, 137") == ["Bell Labs"]


def test_a_bracketed_cross_reference_is_scoped_to_its_brackets():
    assert targets("AT&T, 13, 15 (see also Bell System); "
                   "area codes created by, 300–301") == ["Bell System"]


def test_a_dummy_entry_keeps_every_target():
    """§16: 'transportation, see mass transit; taxis' points at both."""
    assert sorted(targets("transportation, see mass transit; taxis")) == [
        "mass transit", "taxis"]


def test_a_bracketed_reference_to_a_subentry():
    """A colon inside brackets is part of the reference, not a colon form."""
    assert targets("lawsuits involving (see monopolies: lawsuits against; "
                   "patent litigation), 12") == [
        "monopolies: lawsuits against", "patent litigation"]


def test_only_the_main_entry_of_a_subentry_reference_is_checked():
    target, = crossref_targets(parse("x, 1; see also New York City: mass transit"))
    assert target.entry_name == "New York City"


# -- checking they exist -----------------------------------------------------

def test_a_target_with_no_entry_is_flagged():
    assert dangling("art, 290; see also cinema", "films, 12") == [
        "nothing in the index is filed under 'cinema'"]


def test_a_target_that_exists_is_not_flagged():
    assert dangling("art, 290; see also films", "films, 12") == []


def test_a_shortened_target_finds_its_entry():
    """'see also long-distance' for 'long-distance telephony'."""
    assert dangling("trunk lines, 130; see also long-distance",
                    "long-distance telephony, 95") == []


def test_either_half_of_a_slash_entry_answers():
    assert dangling("United Kingdom, see British Empire",
                    "British Empire/United Kingdom, 202") == []


def test_see_under_points_at_the_plain_entry():
    assert dangling("telephones, 5; radio and, see under radio",
                    "radio, 279–81") == []


def test_an_italic_target_is_a_whole_category():
    """§15 puts a category last and in italic; no such entry exists."""
    text = "New York City, 44; see also individual neighborhoods"
    at = text.index("individual")
    mask = [False] * len(text)
    mask[at:] = [True] * (len(text) - at)
    document = [(0, parse(text, mask))]
    assert check_crossref_targets(document) == []
