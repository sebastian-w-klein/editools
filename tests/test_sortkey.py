"""Alphabetisation, against the examples in the guidelines themselves."""

import pytest

from indexcheck.sortkey import candidate_keys, in_order, main_key


def ordered(*entries, subentry=False, drop_prepositions=True):
    """True if the entries are in an acceptable order as given."""
    keys = [candidate_keys(e, subentry=subentry,
                           drop_prepositions=drop_prepositions) for e in entries]
    return all(in_order(a, b) for a, b in zip(keys, keys[1:]))


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
    assert main_key("Bell, A. G.")[1] == "ag"


# -- punctuation and accents -------------------------------------------------

@pytest.mark.parametrize("first,second", [
    ("Atlantic Monthly, The", "AT&T"),      # & ignored: "att" after "atlantic"
    ("elocution", "E=mc²"),                 # = ignored: "emc2" after "elocution"
])
def test_all_punctuation_is_ignored(first, second):
    assert ordered(first, second)


def test_stroked_letters_fold_to_their_base_letter():
    """Ø does not decompose under NFKD; without help it folds to 'rsted'."""
    assert main_key("Ørsted, Hans Christian")[0] == "orsted"
    assert ordered("Ørsted, Hans Christian", "Orton, William", "oscilloscopes")


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
