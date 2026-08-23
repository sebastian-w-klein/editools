"""Every case in the ruleset, plus the misses that prompted it."""

from __future__ import annotations

import pytest

from editools.hyphen import rules
from editools.hyphen.model import Break, Verdict


def make_break(left: str, right: str, *, before: str = "", after: str = "",
               italic: bool = False, kind: str = "syllable", page: str = "1") -> Break:
    return Break(
        pdf_page=int(page), book_page=page, line_index=0,
        left=left, right=right, hyphen_char="-",
        line_text=f"…{left}-", next_line_text=f"{right}…",
        char_before=before, char_after=after, italic=italic, kind=kind,
    )


def check(brk: Break, mw, tokens=None) -> Break:
    ctx = rules.Context(dictionary=mw, tokens=tokens or {})
    return rules.evaluate(brk, ctx)


def verdict(brk: Break, rule) -> Verdict:
    finding = brk.finding_for(rule)
    assert finding is not None, f"Rule {rule} produced no finding"
    return finding.verdict


# -- the standing instruction ------------------------------------------------

def test_every_rule_is_evaluated_for_every_break(mw):
    """Clearing one rule must never stop the others from running."""
    brk = check(make_break("butch", "er's"), mw)
    assert [f.rule for f in brk.findings] == list(range(1, 10))
    assert verdict(brk, 1) is Verdict.OK        # MW's butch·er — Rule 1 passes
    assert verdict(brk, 3) is Verdict.VIOLATION  # …and Rule 3 still catches it


# -- Rule 1 ------------------------------------------------------------------

def test_rule_1_accepts_a_marked_division_point(mw):
    assert verdict(check(make_break("cem", "etery"), mw), 1) is Verdict.OK


def test_rule_1_rejects_a_break_off_the_marked_point(mw):
    """MW gives pho·tog·ra·pher, so photo-/grapher is wrong."""
    brk = check(make_break("photo", "grapher"), mw)
    assert verdict(brk, 1) is Verdict.VIOLATION
    assert "pho·tog·ra·pher" in brk.finding_for(1).message


def test_rule_1_catches_english(mw):
    """MW's dot is En·glish, not Eng·lish — a real miss from the manual pass."""
    assert verdict(check(make_break("Eng", "lish"), mw), 1) is Verdict.VIOLATION
    assert verdict(check(make_break("En", "glish"), mw), 1) is Verdict.OK


def test_rule_1_rejects_any_break_when_mw_shows_no_division_point(mw):
    """MW carries cometh whole, so co-/meth divides nothing real."""
    brk = check(make_break("co", "meth"), mw)
    assert verdict(brk, 1) is Verdict.VIOLATION
    assert "no division point" in brk.finding_for(1).message


def test_rule_1_uses_mw_inflected_forms(mw):
    """cher·ries comes from the ins block on the cherry entry."""
    assert verdict(check(make_break("cher", "ries"), mw), 1) is Verdict.OK


def test_rule_1_reports_missing_entries_rather_than_guessing(mw):
    assert verdict(check(make_break("Mar", "volene"), mw), 1) is Verdict.NEEDS_CHECK


# -- Rule 2 ------------------------------------------------------------------

@pytest.mark.parametrize(
    "left,right,expected",
    [
        ("fold", "up", Verdict.VIOLATION),    # 2 letters after
        ("Wordswor", "th", Verdict.VIOLATION),
        ("co", "op", Verdict.VIOLATION),
        ("butch", "er's", Verdict.OK),        # 3 counting the possessive s
        ("fa", "ther's", Verdict.OK),
    ],
)
def test_rule_2_letter_minimums(mw, left, right, expected):
    assert verdict(check(make_break(left, right), mw), 2) is expected


def test_rule_2_still_applies_at_a_compounds_own_hyphen(mw):
    """Rule 5 says where a compound may break; it does not waive the minimums."""
    brk = check(make_break("fold", "up"), mw)
    assert verdict(brk, 2) is Verdict.VIOLATION
    assert "only 2 letter(s) after" in brk.finding_for(2).message


# -- Rule 3 ------------------------------------------------------------------

def test_rule_3_discounts_the_possessive(mw):
    """butch-/er's leaves only "er" once the 's is set aside."""
    brk = check(make_break("butch", "er's"), mw)
    assert verdict(brk, 3) is Verdict.VIOLATION
    assert "only 2 letter(s)" in brk.finding_for(3).message


@pytest.mark.parametrize(
    "left,right,expected",
    [
        ("fa", "ther's", Verdict.OK),          # the ruleset's own correct example
        ("Ho", "mer's", Verdict.OK),
        ("moth", "er's", Verdict.VIOLATION),   # the ruleset's own incorrect example
        ("Pla", "to's", Verdict.VIOLATION),
    ],
)
def test_rule_3_worked_examples(mw, left, right, expected):
    assert verdict(check(make_break(left, right), mw), 3) is expected


def test_rule_3_is_not_applicable_without_a_possessive(mw):
    assert verdict(check(make_break("cem", "etery"), mw), 3) is Verdict.NOT_APPLICABLE


# -- Rule 4 ------------------------------------------------------------------

def test_rule_4_catches_an_em_dash_after_the_word(mw):
    """cher-/ries—or: legal under Rule 1 and still a Rule 4 violation."""
    brk = check(make_break("cher", "ries", after="—or"), mw)
    assert verdict(brk, 1) is Verdict.OK
    assert verdict(brk, 4) is Verdict.VIOLATION


def test_rule_4_catches_an_em_dash_before_the_word(mw):
    brk = check(make_break("power", "ful", before="encroachment—"), mw)
    assert verdict(brk, 4) is Verdict.VIOLATION


def test_rule_4_ignores_a_dash_with_a_space(mw):
    assert verdict(check(make_break("cher", "ries", after=", or"), mw), 4) is Verdict.OK


# -- Rule 5 ------------------------------------------------------------------

def test_rule_5_allows_a_break_at_the_compounds_own_hyphen(mw):
    brk = check(make_break("cross", "legged"), mw)
    assert verdict(brk, 5) is Verdict.OK
    assert verdict(brk, 1) is Verdict.NOT_APPLICABLE


def test_rule_5_rejects_a_syllable_break_inside_a_component(mw):
    """pov-/erty-stricken splits a component instead of using the hyphen."""
    brk = check(make_break("pov", "erty-stricken"), mw)
    assert verdict(brk, 5) is Verdict.VIOLATION


def test_rule_5_accepts_the_rulesets_own_example(mw):
    assert verdict(check(make_break("poverty", "stricken"), mw), 5) is Verdict.OK


def test_rule_5_uses_the_book_itself_to_settle_a_compound(mw):
    """If the hyphenated form is set intact elsewhere, that is the intended form."""
    brk = check(make_break("cross", "legged"), mw, tokens={"cross-legged": 4})
    assert verdict(brk, 5) is Verdict.OK


# -- Rule 6 ------------------------------------------------------------------

def test_rule_6_defers_to_mw_when_the_name_is_listed(mw):
    brk = check(make_break("Ply", "mouth"), mw)
    assert verdict(brk, 6) is Verdict.OK          # 6.1: MW is listed…
    assert verdict(brk, 1) is Verdict.VIOLATION   # …and MW says Plym·outh


def test_rule_6_will_not_split_a_recognizable_morpheme(mw):
    brk = check(make_break("Wordswor", "th"), mw)
    assert verdict(brk, 6) is Verdict.VIOLATION
    assert "-worth" in brk.finding_for(6).message


def test_rule_6_accepts_a_break_at_the_morpheme_boundary(mw):
    assert verdict(check(make_break("Words", "worth"), mw), 6) is Verdict.OK


def test_rule_6_flags_rather_than_guesses(mw):
    """No entry, no morpheme, no vowel — Rule 6.4 says flag it."""
    assert verdict(check(make_break("Marvol", "ene"), mw), 6) is Verdict.NEEDS_CHECK


def test_rule_6_allows_a_break_after_a_vowel(mw):
    assert verdict(check(make_break("Marvo", "lene"), mw), 6) is Verdict.OK


# -- Rule 7 ------------------------------------------------------------------

def test_rule_7_prefers_the_morpheme_boundary(mw):
    """MW allows dis·plea·sure both ways; Rule 7 prefers dis-pleasure."""
    brk = check(make_break("displea", "sure"), mw)
    assert verdict(brk, 1) is Verdict.OK
    assert verdict(brk, 7) is Verdict.ADVISORY
    assert "dis-pleasure" in brk.finding_for(7).message


def test_rule_7_is_content_with_the_morpheme_boundary(mw):
    assert verdict(check(make_break("dis", "pleasure"), mw), 7) is Verdict.OK


def test_rule_7_never_overrides_mw(mw):
    """re-inforce is preferred, but only among points MW actually allows."""
    assert verdict(check(make_break("re", "inforce"), mw), 1) is Verdict.OK
    assert verdict(check(make_break("rein", "force"), mw), 7) is Verdict.ADVISORY


# -- Rule 8 ------------------------------------------------------------------

def test_rule_8_forbids_a_hyphen_in_a_url(mw):
    brk = check(make_break("www.exam", "ple.com", kind="url"), mw)
    assert verdict(brk, 8) is Verdict.VIOLATION
    assert "www.example / .com" in brk.finding_for(8).message


def test_rule_8_displaces_rules_1_to_7(mw):
    """The ruleset says URL breaks are governed solely by Rule 8."""
    brk = check(make_break("www.exam", "ple.com", kind="url"), mw)
    for rule in (1, 2, 3, 4, 5, 6, 7):
        assert verdict(brk, rule) is Verdict.NOT_APPLICABLE


# -- Rule 9 ------------------------------------------------------------------

def test_rule_9_flags_italic_words_absent_from_mw(mw):
    brk = check(make_break("dépay", "sement", italic=True), mw)
    assert verdict(brk, 9) is Verdict.NEEDS_CHECK


def test_rule_9_leaves_assimilated_words_to_rule_1(mw):
    """A word with its own MW entry is Rule 1's business, italic or not."""
    brk = check(make_break("cem", "etery", italic=True), mw)
    assert verdict(brk, 9) is Verdict.NOT_APPLICABLE


# -- consistency -------------------------------------------------------------

def test_consistency_flags_one_word_divided_two_ways(mw):
    ctx = rules.Context(dictionary=mw, tokens={})
    breaks = [make_break("Mar", "volene", page="41"), make_break("Marvol", "ene", page="88")]
    for brk in breaks:
        rules.evaluate(brk, ctx)
    rules.check_consistency(breaks, ctx)
    for brk in breaks:
        finding = brk.finding_for("Consistency")
        assert finding is not None and finding.verdict.is_flag


def test_consistency_is_quiet_when_a_word_breaks_the_same_way_twice(mw):
    ctx = rules.Context(dictionary=mw, tokens={})
    breaks = [make_break("cem", "etery"), make_break("cem", "etery")]
    for brk in breaks:
        rules.evaluate(brk, ctx)
    rules.check_consistency(breaks, ctx)
    assert all(brk.finding_for("Consistency") is None for brk in breaks)


# -- artifacts ---------------------------------------------------------------

def test_extraction_artifacts_are_not_reported_as_violations(mw):
    brk = check(make_break("patrons", "and", kind="artifact"), mw)
    assert not brk.worst.is_flag
