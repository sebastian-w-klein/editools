"""Letter-by-letter alphabetisation, per FSG Indexing Guidelines §5–§8.

Alphabetising runs up to the first parenthesis or comma, and starts again after
it. Spaces and every other punctuation mark are ignored. Where two entries open
with the same word, what follows that word decides the order, in this sequence:

    the word on its own            London
    the word, then a parenthesis   London (England)
    the word, then a comma         London, Jack
    the word, then a number        London 1900
    the word, then more letters    Londonderry

So a key is not one string but alternating segments and separators —
``("london", COMMA, "jack", END)`` — with ``END`` ranking below both
punctuation marks, which is what puts the bare word first. The last two tiers
need no rank of their own: with spaces ignored the digits and letters simply
continue the segment, and a digit already sorts below a letter.

That structure is also the tiebreak §5 needs. ``New, Arthur`` and ``New, James``
share a first segment, and §5 sorts them before ``newborn``, which only works
if the given name is compared as a segment of its own rather than run together
with the surname. Personal titles are stripped from those later segments as §7
requires.

Several of the exceptions have no single right answer: a numeral may be read
aloud more than one way, an ampersand may be read aloud or ignored, an initial
preposition may or may not be counted, and a leading article may be part of a
name. Rather than
pick one reading and flag every index that chose the other, an entry offers
*candidate* keys and the ordering check accepts it if any reading puts it in
order. That keeps the checker quiet on the many defensible choices and still
catches an entry that is wrong under all of them.
"""

from __future__ import annotations

import re
import unicodedata
from typing import NamedTuple

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

# A segment that is page references or a cross-reference rather than part of
# the term. Neither counts for sorting.
_PAGEREF = re.compile(r"^\s*(see\b|\d|[ivxlcdm]+\s*$)", re.IGNORECASE)

# A cross-reference introduced by a full stop instead of a comma, as a dummy
# entry may be written: "hoe. See garden hoe".
_TRAILING_SEE = re.compile(r"\.\s+(?=see\b)", re.IGNORECASE)

# An ampersand is a word, not a punctuation mark: it is read aloud, so an index
# may file it as "and". "A&E" then lands under "aande", before "Abramovic",
# rather than under "ae", between "Adore" and "AEG". Dropping it is a real
# convention too, so both readings are offered.
_AMPERSAND = "&"

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
    m = re.match(r"[\s“”‘’\"']*(\d+)", term)
    if not m:
        return []
    digits, rest = m.group(1), term[m.end():]
    out = ["".join(_spell(int(d)) for d in digits), _spell(int(digits))]
    if len(digits) == 4:
        out.append(_spell(int(digits[:2])) + _spell(int(digits[2:])))
    return [o + rest for o in out]


#: What follows a segment, in the order the tiers rank. ``END`` is also what
#: terminates every key, so ``London`` sorts before ``London (England)`` and
#: ``London, Jack`` — the bare word first.
END, PAREN, COMMA = 0, 1, 2

#: A sort key: folded segments at the even positions, ranks at the odd ones.
#: The alternation is what makes two keys comparable however long they are.
SortKey = tuple

#: Symbols that stand for a word rather than punctuate one, and how they read
#: aloud. An index files them as they are read, so "A&E" goes under "a and e",
#: before Abramovic, and "R&B" under "r and b", after radio. A symbol with more
#: than one reading offers both, as a numeral does.
#:
#: "=" is deliberately absent: "E=mc²" files after "elocution", which reading
#: the "=" aloud would break. "$" is too, because the word is spoken after the
#: number it precedes.
SPOKEN = {"&": ("and",), "+": ("and", "plus"), "%": ("percent",), "@": ("at",)}

_QUOTES = {"“": "”", '"': '"'}


def _cut(term: str) -> list[tuple[int, str]]:
    """Cut a term at each parenthesis and comma.

    Alphabetising stops at the first of those and starts again after it, so
    each piece comes back paired with the rank of what introduced it. Three
    things do *not* cut:

    * punctuation inside quotation marks, which belongs to the quoted title —
      the comma in ``“Purple Rain,” 148`` is the house style for closing a
      song title, not the boundary of a name;
    * a closing bracket, which introduces nothing and only puts the scan back
      at the top level, where the next comma can cut again;
    * a bracket with nothing in front of it, since there is nothing for it to
      qualify — ``“(I Wanna) Testify”`` is a title that happens to open with a
      parenthesis, and files under "iwannatestify".
    """
    pieces: list[tuple[int, str]] = []
    current: list[str] = []
    rank, depth, closing = END, 0, None

    def cut(at: int):
        nonlocal current, rank
        pieces.append((rank, "".join(current)))
        current, rank = [], at

    for ch in term:
        if closing is not None:
            current.append(ch)
            if ch == closing:
                closing = None
        elif ch in _QUOTES:
            closing = _QUOTES[ch]
            current.append(ch)
        elif ch == "(" and depth == 0 and _fold("".join(current)):
            cut(PAREN)
            depth = 1
        elif ch == ")" and depth == 1:
            depth = 0
        elif ch == "," and depth == 0:
            cut(COMMA)
        else:
            current.append(ch)
    pieces.append((rank, "".join(current)))
    return pieces


def term_segments(entry: str) -> list[tuple[int, str]]:
    """The pieces of an entry that count for sorting, page references dropped.

    Cutting at every comma would otherwise pull the page references into the
    key, since they are comma-separated too. The first comma piece that reads
    as references ends the term, and so does everything after it.

    Only a comma piece is tested that way. What is in brackets is a qualifier,
    never page references, and a bracketed date is exactly the thing that
    tells two entries of the same name apart — read as references,
    'Smith, John (1820–1880)' and 'Smith, John (1900–1970)' would collapse
    onto one key.
    """
    pieces = _cut(entry)
    head = _TRAILING_SEE.split(pieces[0][1], maxsplit=1)[0]
    kept = [(pieces[0][0], head.strip())]
    for rank, text in pieces[1:]:
        text = text.strip()
        if not text or (rank == COMMA and _PAGEREF.match(text)):
            break
        kept.append((rank, text))
    return kept


def _key(head: str, rest: list[tuple[int, str]],
         spoken: dict[str, str] | None = None) -> SortKey:
    """Build a key from a reading of the first segment and the rest as written.

    Personal titles are stripped from the later segments, where §7 puts them —
    'Sarducci, Fr. Guido' files under Guido, not Fr.

    ``spoken`` maps each symbol to the word it is read as, or is None to fold
    it away. It applies to the whole key rather than one segment, because it is
    a house convention: an index reads its symbols aloud everywhere or nowhere.
    """
    def fold(text: str) -> str:
        for symbol, word in (spoken or {}).items():
            text = text.replace(symbol, f" {word} ")
        return _fold(text)

    key: list = [fold(head)]
    for rank, text in rest:
        key += [rank, fold(_strip_titles(text))]
    key.append(END)
    return tuple(key)


def _spoken_choices(entry: str) -> list[dict[str, str]]:
    """Every way of reading this entry's symbols aloud.

    Empty when it has none. A symbol that reads more than one way — "+" is
    "and" or "plus" — gives a choice per reading, all of them equally right,
    exactly as a numeral does.
    """
    choices: list[dict[str, str]] = [{}]
    for symbol, words in SPOKEN.items():
        if symbol not in entry:
            continue
        choices = [dict(choice, **{symbol: word})
                   for choice in choices for word in words]
    return [] if choices == [{}] else choices


class Keys(NamedTuple):
    """The keys an entry may sort under, split by how sure each reading is.

    ``house`` holds the readings that are all equally correct, so an ordering
    that works under any of them is right and says nothing. A numeral belongs
    here: an index files it as it is read aloud, and ``1999`` reads more than
    one way, but every way of reading it is as good as the others.

    ``every`` adds the readings a different house would take — a leading
    article kept rather than moved, a symbol ignored rather than read as a
    word. An ordering that needs one of those is reported as **check**, with
    the reading that would save it named.
    """

    house: tuple[SortKey, ...]
    every: tuple[SortKey, ...]


def sort_keys(entry: str, subentry: bool = False,
              drop_prepositions: bool = True) -> Keys:
    """Every sort key the entry could legitimately have.

    Only the first segment has more than one reading, since that is the one an
    article or a numeral can open. Whether initial prepositions count is not a
    per-entry choice — an index picks one convention and holds to it — so it
    is passed in by the caller, which decides per entry list.
    """
    segments = term_segments(entry)
    head, rest = segments[0][1], segments[1:]
    if subentry and drop_prepositions:
        head = strip_leading_stopwords(head)

    # readings of the first segment: as written and however its numeral reads,
    # against a leading article that may or may not belong to the name
    settled = [head] + _numeral_readings(head)
    arguable = []
    for reading in (_drop_leading(head, ARTICLES), _drop_article_prefix(head)):
        if reading != head:
            arguable += [reading] + _numeral_readings(reading)

    # readings of its symbols: aloud, which is the house rule, or folded away
    spoken = _spoken_choices(entry)
    house_voices = spoken or [None]
    other_voices = [None] if spoken else []

    house: list[SortKey] = []
    every: list[SortKey] = []

    def add(readings, voices, settled_key: bool):
        for voice in voices:
            for reading in readings:
                key = _key(reading, rest, voice)
                if not key[0] or key in every:
                    continue
                if settled_key:
                    house.append(key)
                every.append(key)

    add(settled, house_voices, True)
    add(settled, other_voices, False)
    add(arguable, house_voices + other_voices, False)

    if not house:
        house = [_key(head, rest)]
    return Keys(tuple(house), tuple(every or house))


def candidate_keys(entry: str, subentry: bool = False,
                   drop_prepositions: bool = True) -> list[SortKey]:
    """Every reading of the entry, house and arguable alike."""
    return list(sort_keys(entry, subentry, drop_prepositions).every)


def in_order(previous, current) -> bool:
    """True if the pair reads as correctly ordered under some pair of keys."""
    return any(c >= p for c in current for p in previous)


def main_key(entry: str) -> SortKey:
    """The primary sort key for a main entry."""
    return sort_keys(entry).house[0]


def sub_key(subentry: str) -> SortKey:
    """The primary sort key for a subentry."""
    return sort_keys(subentry, subentry=True).house[0]


def alternative_readings(entry: str) -> list[str]:
    """Names for the readings this entry has beyond the house ones.

    A finding that only the house reading condemns says which other reading
    would have saved it, and naming a reading the entry cannot have — a symbol
    in a term with no symbol — is worse than saying nothing.
    """
    head = term_segments(entry)[0][1]
    names = []
    if (_drop_leading(head, ARTICLES) != head
            or _drop_article_prefix(head) != head):
        names.append("a leading article")
    if _spoken_choices(entry):
        names.append("an ignored symbol")
    return names


def name_candidates(entry: str) -> list[str]:
    """Every folded form the entry answers to when looked up by name.

    A cross-reference names an entry, not a sort position, so only the first
    segment is wanted: 'see London' should find 'London, Jack'.
    """
    out = []
    for key in sort_keys(entry).every:
        if key[0] not in out:
            out.append(key[0])
    return out
