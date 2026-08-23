"""The phase-two rules, each shown finding the fault it is meant to find."""

import pytest

from editools.index import rules
from editools.index.parser import parse


def check(rule, text, italics=None):
    """Run one rule over one entry."""
    mask = [False] * len(text)
    for start, stop in (italics or []):
        mask[start:stop] = [True] * (stop - start)
    return rule(parse(text, mask))


def italic_span(text, needle):
    at = text.index(needle)
    return (at, at + len(needle))


# -- notes, §17 --------------------------------------------------------------

def test_a_roman_note_marker_is_italicised():
    found = check(rules.check_note_italics, "McDuffie, 15, 82n, 128")
    assert [f.action for f in found] == ["italicise"]
    assert found[0].stop - found[0].start == 1        # just the "n"


def test_the_note_number_is_italicised_too():
    """§17 sets both: 304n1, 305nn1, 7 — the wish list says otherwise."""
    text = "McDuffie, 304n1"
    found = check(rules.check_note_italics, text)
    assert text[found[0].start:found[0].stop] == "n1"


def test_an_italic_note_marker_is_left_alone():
    text = "McDuffie, 15, 82n, 128"
    assert check(rules.check_note_italics, text,
                 [italic_span(text, "n,")[0:1] + (text.index("n,") + 1,)]) == []


def test_the_and_n_form():
    text = "McDuffie, 15, 82 and n, 128"
    found = check(rules.check_note_italics, text)
    assert text[found[0].start:found[0].stop] == "n"


def test_a_roman_comma_between_note_numbers_is_flagged():
    """§17 sets '305nn1, 7' entirely in italic, comma included."""
    text = "McDuffie, 305nn1, 7"
    at = text.index("nn")
    # "nn1" and "7" italic, but the comma between them left roman
    found = check(rules.check_roman_note_comma, text,
                  [(at, at + 3), (len(text) - 1, len(text))])
    assert len(found) == 1
    assert text[found[0].start] == ","


# -- cross-references, §15 and §16 -------------------------------------------

def test_capitalised_see_also_is_lowercased():
    found = check(rules.check_see_style, "art, 290; See also films")
    assert (found[0].action, found[0].replacement) == ("replace", "see also")


def test_roman_see_also_is_italicised():
    found = check(rules.check_see_style, "art, 290; see also films")
    assert found[0].action == "italicise"


def test_an_italic_see_also_is_left_alone():
    text = "art, 290; see also films"
    assert check(rules.check_see_style, text,
                 [italic_span(text, "see also")]) == []


def test_see_is_not_matched_inside_a_word():
    assert check(rules.check_see_style, "seeds, 12; seeing, 14") == []


# -- punctuation and spacing -------------------------------------------------

def test_straight_quotes_become_curly():
    found = check(rules.check_quotes, 'the "Ucayali" curare, 37')
    assert [f.replacement for f in found] == ["“", "”"]


def test_a_hyphen_between_page_numbers_becomes_an_en_dash():
    found = check(rules.check_number_dashes, "Baltimore, 30-45")
    assert (found[0].action, found[0].replacement) == ("replace", "–")


def test_a_padded_en_dash_is_closed_up():
    found = check(rules.check_number_dashes, "Baltimore, 30 – 45")
    assert found[0].replacement == "–"


def test_a_spaced_dash_outside_a_range_is_flagged():
    assert len(check(rules.check_spaced_dash, "post- World War, 12")) == 1


def test_tabs_and_double_spaces_go():
    found = check(rules.check_whitespace, "Adams,\tJohn,  15")
    assert [f.action for f in found] == ["delete", "delete"]


@pytest.mark.parametrize("text", ["Adams,, 15", "Adams,; 15", "Adams; ; 15"])
def test_doubled_punctuation_is_flagged(text):
    assert check(rules.check_punctuation_clusters, text)


@pytest.mark.parametrize("text", ["Adam, A. O., 315", "Benjamin, Park, Jr., 176"])
def test_an_abbreviation_before_a_comma_is_not_doubled_punctuation(text):
    assert check(rules.check_punctuation_clusters, text) == []


def test_an_entry_ending_in_an_abbreviation_is_fine():
    assert check(rules.check_punctuation_clusters,
                 "makers, see Eli Lilly; Merck and Co.") == []


def test_an_entry_ending_in_a_comma_is_flagged():
    assert check(rules.check_punctuation_clusters, "Adams, John, 15,")


def test_the_comma_before_page_numbers_must_be_roman():
    """§3: roman even after an italic entry."""
    text = "New Yorker, The, 16, 29"
    at = text.index(", 16")
    assert len(check(rules.check_italic_punctuation, text, [(at, at + 1)])) == 1


# -- page numbers ------------------------------------------------------------

def test_a_repeated_page_is_flagged():
    assert len(check(rules.check_duplicate_pages, "Adams, 9, 9, 75")) == 1


def test_an_italic_repeat_is_an_illustration():
    """§11: 'New York City, 7, 34, 34, 53' — the second 34 is a picture."""
    text = "New York City, 7, 34, 34, 53"
    at = text.rindex("34")
    assert check(rules.check_duplicate_pages, text, [(at, at + 2)]) == []


@pytest.mark.parametrize("written,wanted", [
    ("100–9", "109"), ("123–4", "24"), ("20–9", "29"), ("308–310", "10"),
])
def test_bad_elision_is_corrected(written, wanted):
    found = check(rules.check_elision, f"Adams, {written}")
    assert (found[0].action, found[0].replacement) == ("replace", wanted)


@pytest.mark.parametrize("written", ["22–23", "143–47", "608–609", "108–109",
                                     "108–10", "105–106"])
def test_correct_elision_is_left_alone(written):
    assert check(rules.check_elision, f"Adams, {written}") == []


def test_a_page_past_the_end_of_the_book():
    entry = parse("Adams, 15, 402")
    assert len(rules.check_page_too_high(entry, last_page=390)) == 1
    assert rules.check_page_too_high(entry, last_page=None) == []


# -- wording -----------------------------------------------------------------

def test_a_spelled_out_rank_is_flagged():
    found = check(rules.check_spelled_out_titles,
                  "Sherman, Major General William Tecumseh, 15")
    assert [f.start for f in found]


@pytest.mark.parametrize("text", [
    "General Electric (GE), 227",      # a company
    "Major, Randolph, 40",             # a surname
    "curare, 12; Major and, 114",      # a surname in a subentry
])
def test_rank_words_that_are_not_titles_are_left_alone(text):
    assert check(rules.check_spelled_out_titles, text) == []


def test_ff_and_passim_are_flagged():
    assert len(check(rules.check_ff_passim, "Adams, 15ff., 20 passim")) == 2


def test_a_line_of_page_numbers_alone():
    assert check(rules.check_has_term, "394–95, 402")


def test_a_numeric_entry_is_a_real_entry():
    assert check(rules.check_has_term, "911/999, 4, 5, 394–95") == []


def test_a_capitalised_see_also_is_lowercased_and_italicised_at_once():
    """Both changes touch the same span, so they must be one edit."""
    found = check(rules.check_see_style, "art, 290; See also films")
    assert len(found) == 1
    assert (found[0].replacement, found[0].italic) == ("see also", True)
