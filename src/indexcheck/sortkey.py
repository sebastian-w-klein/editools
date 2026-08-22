"""Letter-by-letter alphabetisation, per FSG Indexing Guidelines §5–§8.

The primary key ignores punctuation and spaces and drops everything after an
open parenthesis, a comma, or a colon. That last part means ``New, Arthur`` and
``New, James`` reduce to the same primary key, which is why §5's own example
sorts them before ``newborn`` — so a secondary key breaks the tie on the given
name, with personal titles stripped as §7 requires.

Several of the exceptions the wish list mentions have no single right answer:
a numeral may be read aloud more than one way, an initial preposition may or
may not be counted, and a leading article may be part of a name. Rather than
pick one reading and flag every index that chose the other, an entry offers
*candidate* keys and the ordering check accepts it if any reading puts it in
order. That keeps the checker quiet on the many defensible choices and still
catches an entry that is wrong under all of them.
"""

from __future__ import annotations

import re
import unicodedata

#: Abbreviated personal titles — civil, ecclesiastical, military (§7).
#: These do not count in alphabetisation.
PERSONAL_TITLES = {
    "abp", "adm", "amb", "bp", "brig", "capt", "card", "cdr", "cmdr", "col",
    "cpl", "dr", "ens", "fr", "gen", "gov", "judge", "justice", "lt", "maj",
    "msgr", "pfc", "pres", "prof", "pvt", "rep", "rev", "sen", "sgt", "sr",
    "st", "mlle", "mme", "mr", "mrs", "ms",
}

#: Initial prepositions and conjunctions ignored when sorting subentries.
SUBENTRY_STOPWORDS = {
    "a", "about", "after", "against", "among", "an", "and", "as", "at",
    "before", "between", "but", "by", "during", "for", "from", "in", "into",
    "nor", "of", "on", "or", "over", "the", "through", "to", "toward",
    "towards", "under", "upon", "with", "within", "without",
}

#: Definite and indefinite articles that may open a name rather than title it.
#: §8 moves an article to the end of a title of a work, but a name like
#: "El Pastor" or "al-Masjid al-Aqsa" keeps it and files under the next word.
ARTICLES = {
    "the", "a", "an", "el", "la", "le", "les", "los", "las", "il", "lo",
    "der", "die", "das", "den", "het", "de", "un", "una", "une", "uno", "al",
}

#: Arabic article prefixes, written joined to the word: "al-Aqsa" files under
#: Aqsa, "al-Masjid al-Aqsa" under Masjid.
ARTICLE_PREFIXES = ("al-", "el-", "ad-", "as-", "az-", "ash-", "ar-")

# Characters ignored by letter-by-letter alphabetisation. §5 names spaces,
# hyphens, periods and quote marks; the published indexes show the rule is
# really "ignore all punctuation" — AT&T files under "att", before "Atlantic
# Monthly", and E=mc² files under "emc2", after "elocution".
_IGNORED = re.compile(r"[^0-9a-z]")

# A segment that is page references rather than part of the term.
_PAGEREF = re.compile(r"^\s*(see\b|\d|[ivxlcdm]+\s*$)", re.IGNORECASE)

#: Letters that carry their mark inside the glyph, so NFKD leaves them whole.
#: Without these, "Ørsted" folds to "rsted" and files after every other entry.
_SPECIAL_LETTERS = {
    "ø": "o", "đ": "d", "ð": "d", "ł": "l", "ħ": "h", "ı": "i", "ŋ": "n",
    "þ": "th", "æ": "ae", "œ": "oe", "ß": "ss",
}

_ONES = ["zero", "one", "two", "three", "four", "five", "six", "seven",
         "eight", "nine", "ten", "eleven", "twelve", "thirteen", "fourteen",
         "fifteen", "sixteen", "seventeen", "eighteen", "nineteen"]
_TENS = ["", "", "twenty", "thirty", "forty", "fifty", "sixty", "seventy",
         "eighty", "ninety"]


def _fold(text: str) -> str:
    """Strip accents, drop punctuation and spaces, lowercase.

    Accented letters alphabetise as their unaccented equivalents.
    """
    text = text.lower()
    text = "".join(_SPECIAL_LETTERS.get(c, c) for c in text)
    text = unicodedata.normalize("NFKD", text)
    text = "".join(c for c in text if not unicodedata.combining(c))
    return _IGNORED.sub("", text)


def _is_initial(word: str) -> bool:
    """True for 'A.' or 'G.' — an initial, not the article 'a'."""
    return len(word) == 2 and word.endswith(".") and word[0].isalpha()


def _strip_titles(text: str) -> str:
    """Drop leading personal titles: 'Fr. Guido' -> 'Guido' (§7).

    Only *abbreviated* titles are stripped, which §7 requires them to be.
    Spelling one out is nearly always part of a name rather than a title —
    'Johnson, Lady Bird' files under Bird only if you wrongly read 'Lady' as
    a title, which would sort her before 'Johnson, John B.'
    """
    words = text.split()
    while len(words) > 1:
        head = words[0]
        if (head.endswith(".") and not _is_initial(head)
                and head.rstrip(".").lower() in PERSONAL_TITLES):
            words.pop(0)
        else:
            break
    return " ".join(words)


def _bare(word: str) -> str:
    """A word with surrounding punctuation and quote marks removed."""
    return word.strip(".,;:'\u2018\u2019\"\u201c\u201d()[]").lower()


def _drop_leading(text: str, vocabulary: set[str]) -> str:
    """Drop leading words that appear in ``vocabulary``, keeping the last."""
    words = text.split()
    while len(words) > 1:
        head = words[0]
        if _is_initial(head):
            break
        if _bare(head) in vocabulary:
            words.pop(0)
        else:
            break
    return " ".join(words) if words else text


def _drop_article_prefix(text: str) -> str:
    """Strip a joined Arabic article: 'al-Aqsa Flood' -> 'Aqsa Flood'."""
    stripped = text.lstrip("\u201c\u2018\"'")
    lowered = stripped.lower()
    for prefix in ARTICLE_PREFIXES:
        if lowered.startswith(prefix) and len(stripped) > len(prefix):
            return stripped[len(prefix):]
    return text


def strip_leading_stopwords(text: str) -> str:
    """Drop initial prepositions/conjunctions from a subentry term."""
    return _drop_leading(text, SUBENTRY_STOPWORDS)


def _spell(n: int) -> str:
    """Spell a number the way an index would read it aloud."""
    if n < 20:
        return _ONES[n]
    if n < 100:
        return _TENS[n // 10] + (_ONES[n % 10] if n % 10 else "")
    if n < 1000:
        return _ONES[n // 100] + "hundred" + (_spell(n % 100) if n % 100 else "")
    return _spell(n // 1000) + "thousand" + (_spell(n % 1000) if n % 1000 else "")


def _numeral_readings(term: str) -> list[str]:
    """Every way a numeral-initial term might be read aloud.

    '911' may be "nine one one" or "nine hundred eleven", and '1984'
    "nineteen eighty-four". An index files numerals as though spelled out, so
    offer all of them rather than guess.
    """
    m = re.match(r"\s*(\d+)", term)
    if not m:
        return []
    digits, rest = m.group(1), term[m.end():]
    out = ["".join(_spell(int(d)) for d in digits), _spell(int(digits))]
    if len(digits) == 4:
        out.append(_spell(int(digits[:2])) + _spell(int(digits[2:])))
    return [o + rest for o in out]


def split_term(entry: str) -> tuple[str, str]:
    """Split an entry into its sorting term and its tiebreak segment.

    The term is everything up to the first open parenthesis, comma or colon.
    The tiebreak is the following comma-delimited segment when that segment is
    part of the name rather than page references.
    """
    head = re.split(r"[(:]", entry, maxsplit=1)[0]
    parts = head.split(",")
    term = parts[0].strip()
    tiebreak = ""
    if len(parts) > 1:
        candidate = parts[1].strip()
        if candidate and not _PAGEREF.match(candidate):
            tiebreak = candidate
    return term, tiebreak


def candidate_keys(entry: str, subentry: bool = False,
                   drop_prepositions: bool = True) -> list[tuple[str, str]]:
    """Every sort key the entry could legitimately have.

    The readings offered are: the term as written; with a leading article
    dropped; and, for a numeral-initial term, each way of reading the numeral
    aloud. Whether initial prepositions count is not a per-entry choice — an
    index picks one convention and holds to it — so it is passed in by the
    caller, which decides per entry list.
    """
    term, tiebreak = split_term(entry)
    tie = _fold(_strip_titles(tiebreak))

    readings = [term]
    for candidate in (_drop_leading(term, ARTICLES), _drop_article_prefix(term)):
        if candidate != term and candidate not in readings:
            readings.append(candidate)
    if subentry and drop_prepositions:
        readings = [strip_leading_stopwords(r) for r in readings]
    for reading in list(readings):
        readings.extend(_numeral_readings(reading))

    seen, keys = set(), []
    for reading in readings:
        key = (_fold(reading), tie)
        if key[0] and key not in seen:
            seen.add(key)
            keys.append(key)
    return keys or [(_fold(term), tie)]


def in_order(previous: list[tuple[str, str]],
             current: list[tuple[str, str]]) -> bool:
    """True if the pair reads as correctly ordered under some pair of keys."""
    return any(c >= p for c in current for p in previous)


def main_key(entry: str) -> tuple[str, str]:
    """The primary sort key for a main entry."""
    return candidate_keys(entry)[0]


def sub_key(subentry: str) -> tuple[str, str]:
    """The primary sort key for a subentry."""
    term, tiebreak = split_term(subentry)
    return (_fold(strip_leading_stopwords(term)), _fold(_strip_titles(tiebreak)))
