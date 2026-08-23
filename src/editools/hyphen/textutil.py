"""Character-level helpers: hyphens, dashes and token splitting."""

from __future__ import annotations

import re

#: Characters a typesetter (or a PDF extractor) may leave at end of line as a
#: word-division hyphen.
HYPHENS = "-‐‑­"

#: Dashes that are *not* word-division hyphens.
EM_DASHES = "—―"
EN_DASH = "–"
ALL_DASHES = EM_DASHES + EN_DASH

WORD_CHARS = re.compile(r"[A-Za-zÀ-ɏ'’ʼ-]")

#: A run that reads as an em dash in extracted text (real em dash, or the
#: typewriter "--" convention some extractors produce).
EM_DASH_RUN = re.compile(r"[—―]|--")


def is_hyphen(ch: str) -> bool:
    return ch in HYPHENS


def is_em_dash_at(text: str, index: int) -> bool:
    """True if an em dash starts at *index* in *text*."""
    if index < 0 or index >= len(text):
        return False
    if text[index] in EM_DASHES:
        return True
    return text.startswith("--", index)


def ends_with_em_dash(text: str) -> bool:
    stripped = text.rstrip()
    if not stripped:
        return False
    return stripped[-1] in EM_DASHES or stripped.endswith("--")


def split_leading_word(token: str) -> tuple[str, str, str]:
    """Split *token* into ``(prefix, word, suffix)`` around its **first** word.

    The *word* is the run of letters (plus internal apostrophes and hyphens);
    *prefix* and *suffix* hold whatever punctuation is set tight against it.
    Quotation marks, brackets, dashes and terminal punctuation all end up in
    the prefix or suffix, which is what Rule 4 inspects for em-dash adjacency.

        >>> split_leading_word('“encroach')
        ('“', 'encroach', '')
        >>> split_leading_word('ries—or')
        ('', 'ries', '—or')
    """
    match = re.search(r"[A-Za-zÀ-ɏ]", token)
    if not match:
        return token, "", ""
    start = match.start()
    # Walk forward over letters, plus apostrophes/hyphens that have a letter on
    # both sides (so "er's" stays whole but "ries—or" splits at the dash).
    i = start
    while i < len(token):
        ch = token[i]
        if WORD_CHARS.fullmatch(ch) and ch not in "-'’ʼ":
            i += 1
        elif ch in "-'’ʼ" and i + 1 < len(token) and token[i + 1].isalpha():
            i += 1
        else:
            break
    return token[:start], token[start:i], token[i:]


def split_trailing_word(token: str) -> tuple[str, str, str]:
    """Split *token* around its **last** word.

    The fragment before a line-ending hyphen is the tail of its token, so
    ``encroachment—power`` has to yield ``power`` with the em dash left in the
    prefix, where Rule 4 can see it.

        >>> split_trailing_word('encroachment—power')
        ('encroachment—', 'power', '')
        >>> split_trailing_word('“encroach')
        ('“', 'encroach', '')
    """
    end = len(token)
    while end > 0 and not token[end - 1].isalpha():
        end -= 1
    if end == 0:
        return token, "", ""
    start = end
    while start > 0:
        ch = token[start - 1]
        if ch.isalpha():
            start -= 1
        elif ch in "-'’ʼ" and start - 1 > 0 and token[start - 2].isalpha():
            start -= 1
        else:
            break
    return token[:start], token[start:end], token[end:]


def leading_em_dash(prefix: str) -> bool:
    """True if *prefix* ends in an em dash set tight against the word."""
    return bool(prefix) and (prefix[-1] in EM_DASHES or prefix.endswith("--"))


def trailing_em_dash(suffix: str) -> bool:
    """True if *suffix* begins with an em dash set tight against the word."""
    return bool(suffix) and (suffix[0] in EM_DASHES or suffix.startswith("--"))


URL_HINT = re.compile(
    r"(https?://|www\.|ftp://|mailto:)"
    r"|[A-Za-z0-9_\-]+@[A-Za-z0-9_\-]+\."
    r"|[A-Za-z0-9_\-]+\.(com|org|net|edu|gov|io|co|uk|de|fr|info|me|us)\b",
    re.IGNORECASE,
)


def looks_like_url(text: str) -> bool:
    return bool(URL_HINT.search(text))


VOWELS = set("aeiouyAEIOUY")


def ends_in_vowel(text: str) -> bool:
    letters = [c for c in text if c.isalpha()]
    return bool(letters) and letters[-1] in VOWELS


def has_vowel(text: str) -> bool:
    """True if *text* holds a vowel — that is, whether it could form a syllable."""
    return any(ch in VOWELS for ch in text)


ROMAN = re.compile(r"^(?:M{0,4}(?:CM|CD|D?C{0,3})(?:XC|XL|L?X{0,3})(?:IX|IV|V?I{0,3}))$")


def is_roman_numeral(token: str) -> bool:
    token = token.strip(".,;:)”\"'")
    return bool(token) and token.isupper() and bool(ROMAN.fullmatch(token))


INITIAL = re.compile(r"^[A-Z]\.$")


def is_initial(token: str) -> bool:
    return bool(INITIAL.fullmatch(token.strip("“”\"'()")))
