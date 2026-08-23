"""Parsing Merriam-Webster's JSON, and the cache that makes it cheap."""

from __future__ import annotations

import json

from editools.hyphen.dictionary import Dictionary, collect_dotted_forms, positions_from_dotted
from hyphen.conftest import build_cache


def test_division_points_come_from_the_asterisks():
    assert positions_from_dotted("cem*e*ter*y") == {3, 4, 7}
    assert positions_from_dotted("cometh") == set()


def test_dotted_forms_are_harvested_from_every_field():
    """Headword, inflections, variants and run-ons all carry division points."""
    forms = collect_dotted_forms([
        {
            "hwi": {"hw": "cher*ry"},
            "ins": [{"if": "cher*ries"}],
            "vrs": [{"va": "che*rie"}],
            "uros": [{"ure": "cher*ry*like"}],
        },
        "cherryish",  # MW's "did you mean" strings must be ignored
    ])
    assert forms["cherry"] == "cher*ry"
    assert forms["cherries"] == "cher*ries"
    assert forms["cherrylike"] == "cher*ry*like"


def test_an_inflected_form_resolves_through_the_base_entry(mw):
    assert mw.lookup("cherries").positions == positions_from_dotted("cher*ries")


def test_a_possessive_resolves_through_the_base_word(mw):
    possessive = mw.lookup("butcher's")
    assert possessive.found and possessive.positions == {5}


def test_a_regular_plural_keeps_the_stems_division_points(mw):
    plural = mw.lookup("butchers")
    assert plural.found and 5 in plural.positions


def test_a_hyphenated_headword_is_recognised_as_a_compound(mw):
    assert mw.lookup("cross-legged").hyphenated_compound


def test_a_word_mw_does_not_carry_is_reported_as_absent(mw):
    """And is not quietly filled in from TeX, which knows no vocabulary."""
    result = mw.lookup("Marvolene")
    assert not result.found and result.consulted and result.source == "none"


def test_tex_is_used_only_when_mw_was_never_consulted(tmp_path):
    offline = Dictionary(api_key="", cache_path=tmp_path / "empty.json", offline=True)
    result = offline.lookup("photographer")
    assert result.source == "tex" and not result.consulted


def test_overrides_outrank_the_dictionary(tmp_path):
    dictionary = Dictionary(
        api_key="", cache_path=tmp_path / "c.json", offline=True,
        overrides={"Marvolene": "Mar*vo*lene"},
    )
    result = dictionary.lookup("Marvolene")
    assert result.source == "override" and result.positions == {3, 5}


def test_an_override_can_forbid_breaking_a_word(tmp_path):
    dictionary = Dictionary(
        api_key="", cache_path=tmp_path / "c.json", offline=True,
        overrides={"rulepig": "nobreak"},
    )
    assert dictionary.lookup("rulepig").positions == set()


def test_the_cache_survives_a_round_trip(tmp_path):
    path = tmp_path / "mw-cache.json"
    path.write_text(json.dumps(build_cache()), encoding="utf-8")
    first = Dictionary(api_key="", cache_path=path, offline=True)
    assert first.lookup("cemetery").display == "cem·e·ter·y"
    first.save()
    second = Dictionary(api_key="", cache_path=path, offline=True)
    assert second.lookup("cemetery").found
    assert second.api_calls == 0
