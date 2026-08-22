"""Test fixtures, including a Merriam-Webster stand-in.

Merriam-Webster's API cannot be called from a test run, so the dictionary is
primed with cache entries shaped exactly like real API responses — the
headword with asterisk division points, inflected forms under ``ins``, and
MW's bare-string "did you mean" list for words it does not carry.  That
exercises the real parsing path rather than stubbing it out.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from hyphencheck.dictionary import Dictionary  # noqa: E402

#: word -> dotted headword, as MW returns it.  A value of None means MW has no
#: entry and answers with suggestions instead.
MW_ENTRIES: dict[str, str | None] = {
    "butcher": "butch*er",
    "cherry": "cher*ry",
    "cross-legged": "cross-legged",
    "crosslegged": None,
    "foldup": None,
    "fold-up": None,
    "photographer": "pho*tog*ra*pher",
    "plymouth": "Plym*outh",
    "english": "En*glish",
    "cometh": "cometh",           # a real entry carrying no division point
    "displeasure": "dis*plea*sure",
    "poverty-stricken": "pov*er*ty-strick*en",
    "povertystricken": None,
    "wordsworth": None,
    "wordswor": None,
    "marvolene": None,
    "dépaysement": None,
    "father": "fa*ther",
    "mother": "moth*er",
    "plato": "Pla*to",
    "homer": "Ho*mer",
    "reinforce": "re*in*force",
    "cemetery": "cem*e*ter*y",
    "co-op": "co-op",
    "power": "pow*er",
    "powerful": "pow*er*ful",
    "encroachment": "en*croach*ment",
    "example": "ex*am*ple",
    "stricken": "strick*en",
    "legged": "leg*ged",
    "sement": None,
    "ene": None,
}

#: Inflected forms MW lists under ``ins`` on the base entry.
MW_INFLECTIONS: dict[str, list[str]] = {
    "cherry": ["cher*ries"],
    "butcher": ["butch*ers"],
}


def _response(word: str) -> list:
    dotted = MW_ENTRIES.get(word.lower(), "MISSING")
    if dotted == "MISSING" or dotted is None:
        # MW answers an unknown word with a list of plain strings.
        return [f"{word}s", f"{word}ed"]
    entry = {
        "meta": {"id": word, "stems": [word.replace("*", "")]},
        "hwi": {"hw": dotted},
        "fl": "noun",
    }
    inflections = MW_INFLECTIONS.get(word.lower())
    if inflections:
        entry["ins"] = [{"if": form} for form in inflections]
    return [entry]


def build_cache() -> dict:
    cache = {}
    for word in MW_ENTRIES:
        cache[f"collegiate:{word}"] = _response(word)
    # Inflected forms resolve through the base entry, exactly as MW does.
    for base, forms in MW_INFLECTIONS.items():
        for form in forms:
            cache[f"collegiate:{form.replace('*', '')}"] = _response(base)
    return cache


@pytest.fixture
def mw(tmp_path) -> Dictionary:
    """A Dictionary backed by recorded MW responses, with no network access."""
    cache_path = tmp_path / "mw-cache.json"
    cache_path.write_text(json.dumps(build_cache()), encoding="utf-8")
    dictionary = Dictionary(api_key="", cache_path=cache_path, offline=True)
    return dictionary


@pytest.fixture
def proof_pdf(tmp_path) -> Path:
    from make_fixture import build

    return build(tmp_path / "sample_proof.pdf")


sys.path.insert(0, str(Path(__file__).resolve().parent))
