"""Alphabetisation, against the examples in the guidelines themselves."""

import pytest

from editools.index.sortkey import (COMMA, END, PAREN, candidate_keys, in_order,
                                main_key, sort_keys)


def ordered(*entries, subentry=False, drop_prepositions=True):
    """True if the entries are in an acceptable order as given."""
    keys = [candidate_keys(e, subentry=subentry,
                           drop_prepositions=drop_prepositions) for e in entries]
    return all(in_order(a, b) for a, b in zip(keys, keys[1:]))


def filed(*entries):
    """As ``ordered``, but through the parser, as the checker itself runs."""
    from editools.index.parser import parse

    return ordered(*[parse(e).term for e in entries])


# -- the guidelines' own worked examples -------------------------------------

def test_letter_by_letter_section_5():
    assert ordered("New, Arthur", "New, James", "newborn", "newcomer", "New Deal")


def test_mc_names_alphabetised_as_spelled_section_6():
    assert ordered("MacNeice, Louis", "Magellan, Ferdinand", "Martin, Henry",
                   "McCarthy, Eugene", "McDuffie, Horatio")


def test_personal_titles_do_not_count_section_7():
    assert ordered("Sarducci, Gilberto", "Sarducci, Fr. Guido",
                   "Sherman, Sen. John", "Sherman, Maj. Gen. William Tecumseh")


def test_articles_move_to_the_end_section_8():
    assert ordered("Midsummer Night's Dream, A, 254–56", "New Yorker, The, 16",
                   "New York Post, 77", "New York Times, The, 28")


# -- the tiebreak ------------------------------------------------------------

def test_given_name_breaks_a_tie_on_the_surname():
    """§5 sorts 'New, Arthur' before 'New, James', so the given name counts."""
    assert not ordered("Miller, Glenn", "Miller, George A.")
    assert ordered("Miller, George A.", "Miller, Glenn")


def test_a_spelled_out_title_is_part_of_the_name():
    """'Lady Bird' is a name; only abbreviated titles are stripped (§7)."""
    assert ordered("Johnson, John B.", "Johnson, Lady Bird")


def test_an_initial_is_not_the_article_a():
    assert main_key("Bell, A. G.") == ("bell", COMMA, "ag", END)


# -- punctuation and accents -------------------------------------------------

@pytest.mark.parametrize("first,second", [
    ("Atlantic Monthly, The", "AT&T"),      # & ignored: "att" after "atlantic"
    ("elocution", "E=mc²"),                 # = ignored: "emc2" after "elocution"
])
def test_all_punctuation_is_ignored(first, second):
    assert ordered(first, second)


# -- symbols that stand for a word -------------------------------------------

def test_a_symbol_is_read_aloud():
    """'A&E' files under "a and e"; the & is a word, not punctuation."""
    assert main_key("A&E") == ("aande", END)
    assert main_key("R&B") == ("randb", END)


def test_a_symbol_read_aloud_files_where_the_index_puts_it():
    """The Leeds cases, and R&D after radio, which the editor confirmed."""
    assert ordered("A&E", "Abramovic, Marina", "Ace, Johnny", "Adelman, Mark",
                   "“Adore” (song)", "AEG")
    assert ordered("Redding, Otis", "Red Hot + Riot (album)",
                   "Red Hot Organization", "Reed, Jimmy")
    assert ordered("radio", "radio stations", "R&B", "R&D", "Reagan")


def test_a_symbol_read_more_than_one_way_offers_both():
    """"+" is "and" or "plus", and both readings are equally right."""
    assert ("redhotplusriot", END) in sort_keys("Red Hot + Riot").house
    assert ("redhotandriot", END) in sort_keys("Red Hot + Riot").house


def test_a_symbol_may_also_be_folded_away():
    """The other convention exists, so it is accepted as a second reading."""
    assert ordered("Atlantic Monthly, The", "AT&T")
    assert sort_keys("AT&T").house[0] == ("atandt", END)
    assert ("att", END) in sort_keys("AT&T").every


def test_a_symbol_entry_filed_at_the_head_of_its_letter_is_wrong():
    """Wrong under both readings: "randb" and "rb" each follow "race"."""
    assert not ordered("R&B", "race relations")
    assert not ordered("Zeta", "A&E")


def test_an_equals_sign_is_not_read_aloud():
    """'E=mc²' files after 'elocution', which reading it aloud would break."""
    assert main_key("E=mc²") == ("emc2", END)
    assert ordered("elocution", "E=mc²")


# -- the order of precedence after a shared word -----------------------------

def test_the_five_tiers_rank_in_order():
    """One word, then a parenthesis, a comma, a number, and more letters."""
    assert ordered("London", "London (England)", "London, Jack",
                   "London 1900", "Londonderry")


def test_a_bare_word_files_before_the_same_word_qualified():
    assert not ordered("London (England)", "London")
    assert not ordered("London, Jack", "London (England)")


def test_a_parenthesis_is_alphabetised_not_discarded():
    """Dropping the bracketed part made 'London (Ontario)' sort as 'London'."""
    assert ordered("London (England)", "London (Ontario)")
    assert not ordered("London (Ontario)", "London (England)")


def test_alphabetising_starts_again_after_each_cut():
    assert ordered("Hoe, Robert", "Hoe, Robert, Jr.")
    assert ordered("Smith, John (the elder)", "Smith, John (the younger)")


def test_a_person_a_place_and_a_thing_sharing_a_name():
    """The guidelines' own worked example of same-name entries."""
    assert ordered("hoe, garden", "Hoe, Robert", "London, England",
                   "London, Jack")
    assert ordered("garden hoe", "hoe. See garden hoe", "Hoe, Carolyn",
                   "Hoe, Robert", "London (England)", "London, Amy",
                   "London, Jack")


def test_a_bracketed_date_tells_two_of_a_name_apart():
    """Brackets hold a qualifier, never page references."""
    assert ordered("Smith, John (1820–1880)", "Smith, John (1900–1970)")
    assert not ordered("Smith, John (1900–1970)", "Smith, John (1820–1880)")


def test_two_entries_that_alphabetise_the_same_are_reported():
    from editools.index.parser import parse
    from editools.index.rules import check_entry_order

    found = check_entry_order(
        [(i, parse(e)) for i, e in enumerate(["Hoe, Robert, 5", "Hoe, Robert, 9"])])
    assert [f.severity for _, f in found] == ["check"]
    assert "needs a qualifier" in found[0][1].message


def test_a_qualifier_settles_it_and_nothing_is_reported():
    from editools.index.parser import parse
    from editools.index.rules import check_entry_order

    entries = ["London (England), 5", "London, Amy, 7", "London, Jack, 9"]
    assert check_entry_order([(i, parse(e)) for i, e in enumerate(entries)]) == []


def test_a_cross_reference_is_not_part_of_the_name():
    """'hoe. See garden hoe' files under 'hoe', not 'hoeseegardenhoe'."""
    from editools.index.parser import parse

    assert parse("hoe. See garden hoe").term == "hoe"
    assert main_key(parse("hoe. See garden hoe").term) == ("hoe", END)


# -- quotation marks and leading brackets ------------------------------------

def test_the_comma_inside_a_closing_quote_is_the_separator():
    """House style tucks it in the quote: '“Purple Rain,” 148'."""
    from editools.index.parser import parse

    assert parse("“Purple Rain,” 148").term == "“Purple Rain,”"
    assert main_key("“Purple Rain,”") == ("purplerain", END)
    assert filed("“Purple Rain,” 148", "Purple Rain (album), 117",
                 "Purple Rain (film), 4", "“Purple Rain” (song), 116",
                 "Purple Rain Tour, 134")


def test_a_comma_inside_a_quoted_phrase_still_is_not():
    from editools.index.parser import parse

    assert parse("“Ucayali, 1871” curare, 37").term == "“Ucayali, 1871” curare"


def test_a_leading_bracket_is_part_of_the_title():
    """There is nothing in front for the bracket to qualify."""
    assert main_key("“(I Wanna) Testify” (song)") == (
        "iwannatestify", PAREN, "song", END)
    assert main_key("(Music from) The Elder (album)") == (
        "musicfromtheelder", PAREN, "album", END)


def test_a_bracket_inside_quotes_belongs_to_the_title():
    assert main_key("“I Got You (I Feel Good)” (song)") == (
        "igotyouifeelgood", PAREN, "song", END)
    assert ordered("“I Got You” (song)", "“I Got You (I Feel Good)” (song)")


def test_one_misfiling_does_not_flag_the_whole_run_after_it():
    """An entry filed too early blocks everything that legitimately follows."""
    from editools.index.parser import parse
    from editools.index.rules import check_entry_order

    entries = ["“I Got You” (song), 29", "“(I Wanna) Testify” (song), 29",
               "“I Know You Got Soul” (song), 270",
               "“I’ll Be in Trouble” (song), 43", "“I Love It Loud” (song), 86"]
    found = check_entry_order([(i, parse(e)) for i, e in enumerate(entries)])
    assert len(found) == 1
    assert found[0][1].message.startswith("'“(I Wanna) Testify” (song)'")


# -- the exceptions the wish list calls out ----------------------------------

def test_a_numeral_may_be_read_more_than_one_way():
    """'911' reads "nine…", so it files among the n's, not before the a's."""
    assert ordered("nightlife", "911/999", "Nobel Prize")


def test_a_numeral_subentry_files_under_its_spelling():
    assert ordered("nickname for", "1956 consent decree for", subentry=True)


def test_initial_prepositions_do_not_count_in_a_subentry():
    assert ordered("area codes created by", "on operators",
                   "as public utility", "in World War I", subentry=True)


def test_a_preposition_may_also_be_counted():
    """Both conventions exist, so a list is judged under whichever it follows."""
    assert ordered("between Boston and New York", "bills for",
                   subentry=True, drop_prepositions=False)
    assert not ordered("at Fordlandia", "Ford and",
                       subentry=True, drop_prepositions=True)


def test_a_leading_article_may_belong_to_the_name():
    assert ordered("Pasteur Institute", "“El Pastor,” 19")
    assert ordered("San Antonio Express (newspaper)", "El Sangay volcano")


def test_an_arabic_article_prefix_files_under_the_next_word():
    assert ordered("Apocalypse Recalled (Maier)", "Al-Aqsa Flood",
                   "al-Aqsa Mosque, Jerusalem")
    assert ordered("Marx, Karl", "al-Masjid al-Aqsa")


# -- how an ambiguous case is reported ---------------------------------------

def test_every_reading_of_a_numeral_is_equally_right_so_nothing_is_said():
    """An index files a numeral as it reads, and 1956 reads more than one way."""
    from editools.index.parser import parse
    from editools.index.rules import check_subentry_order

    assert check_subentry_order(
        parse("monopolies, 5; nickname for, 312; "
              "1956 consent decree for, 391")) == []


def test_an_ambiguous_ordering_says_which_reading_would_save_it():
    from editools.index.parser import parse
    from editools.index.rules import check_entry_order, check_subentry_order

    symbol = check_entry_order(
        [(i, parse(e))
         for i, e in enumerate(["Atlantic Monthly, The, 55", "AT&T, 60"])])
    assert symbol[0][1].severity == "check"
    assert "an ignored symbol" in symbol[0][1].message

    preposition = check_subentry_order(
        parse("x, 5; between Boston and New York, 135; bills for, 397"))
    assert preposition[0].severity == "check"
    assert "initial preposition counts" in preposition[0].message


def test_an_unambiguous_ordering_error_is_an_error():
    from editools.index.parser import parse
    from editools.index.rules import check_subentry_order

    found = check_subentry_order(parse("x, 5; parks, 61; architecture, 64"))
    assert found[0].severity == "error"
    assert "though" not in found[0].message
