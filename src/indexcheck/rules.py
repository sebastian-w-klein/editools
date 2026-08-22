"""The checks themselves.

Each rule takes a parsed entry and yields :class:`Finding` objects describing a
character range and what is wrong with it. Nothing here touches the document —
findings become tracked changes, highlights and comments in :mod:`audit`, which
keeps the rules easy to test and lets them fire in any order.

A finding either *flags* a span for a human to look at or carries a *fix*: a
tracked edit that Word will show as a revision. Fixes are for changes the
guidelines make unambiguous — an en dash between page numbers, italic on a note
marker. Anything needing judgement is flagged instead.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from . import pagerefs
from .pagerefs import EN_DASH, elide
from .parser import Entry
from .sortkey import candidate_keys, in_order

#: Highlight colour per rule, so the marked-up file is readable at a glance.
COLOURS = {
    "entry-order": "yellow",
    "subentry-order": "brightGreen",
    "page-order": "cyan",
    "range-order": "magenta",
    "duplicate-page": "cyan",
    "page-too-high": "magenta",
    "elision": "cyan",
    "no-term": "magenta",
    "punctuation": "yellow",
    "spaced-dash": "yellow",
    "italic-punctuation": "brightGreen",
    "roman-note-comma": "brightGreen",
    "spell-out-title": "yellow",
    "post-world": "yellow",
    "ff-passim": "magenta",
}

#: Ranks that §7 requires to be abbreviated.
SPELLED_OUT_TITLES = [
    "Field Marshal", "Brigadier General", "Lieutenant General",
    "Major General", "Lieutenant Colonel", "General", "Colonel", "Major",
    "Admiral", "Captain", "Lieutenant", "Sergeant", "Airman", "Brigadier",
    "Commander",
]


@dataclass
class Finding:
    rule: str
    start: int
    stop: int
    message: str
    #: "error" — wrong however you read it. "check" — wrong under the house
    #: rule, but another defensible reading would put it right.
    severity: str = "error"
    #: None to flag the span; otherwise the edit to make as a tracked change.
    action: str | None = None        # "delete" | "replace" | "italicise"
    replacement: str = ""
    #: set italic on the replacement text
    italic: bool = False

    @property
    def colour(self) -> str:
        return COLOURS.get(self.rule, "yellow")


# ---------------------------------------------------------------------------
# ordering
# ---------------------------------------------------------------------------

def _order_severity(previous_keys, current_keys) -> str | None:
    """How badly a pair is out of order, judged on the house reading first.

    ``None`` means in order. Otherwise the house reading (the first candidate
    key) puts them the wrong way round, and the severity says whether any other
    reading would have saved it.
    """
    if current_keys[0] >= previous_keys[0]:
        return None
    return "check" if in_order(previous_keys, current_keys) else "error"


def _alternative(severity: str) -> str:
    return ("" if severity == "error" else
            " — though it is right if filed under a spelled-out numeral "
            "or a leading article")


def check_entry_order(entries: list[tuple[int, Entry]]) -> list[tuple[int, Finding]]:
    """Main entries run in alphabetical order, letter by letter (§5).

    Reported against the entry that breaks the run, so a single misfiled entry
    produces one flag rather than two.
    """
    found = []
    previous = None
    for position, entry in entries:
        if entry.is_note or not entry.term:
            continue
        keys = candidate_keys(entry.term)
        if previous is not None:
            severity = _order_severity(previous[0], keys)
            if severity:
                found.append((position, Finding(
                    "entry-order", 0, max(1, entry.term_stop),
                    f"{entry.term!r} should come before {previous[1]!r}"
                    + _alternative(severity),
                    severity=severity,
                )))
                continue
        previous = (keys, entry.term)
    return found


def check_subentry_order(entry: Entry) -> list[Finding]:
    """Subentries run in alphabetical order, letter by letter (§12).

    The house rule is that initial prepositions and conjunctions do not count,
    so 'on operators' files under 'operators'. An index that counts them
    instead is a defensible choice, so those come back as 'check' rather than
    'error'.
    """
    found = []
    subs = entry.subentries
    keys = [candidate_keys(s.term, subentry=True) for s in subs]
    counted = [candidate_keys(s.term, subentry=True, drop_prepositions=False)
               for s in subs]
    for i in range(1, len(subs)):
        if keys[i][0] >= keys[i - 1][0]:
            continue
        if in_order(keys[i - 1], keys[i]):
            severity, aside = "check", _alternative("check")
        elif counted[i][0] >= counted[i - 1][0]:
            severity, aside = "check", (
                " — though it is right if the initial preposition counts")
        else:
            severity, aside = "error", ""
        current, previous = subs[i], subs[i - 1]
        start = current.start + (len(current.text) - len(current.text.lstrip()))
        found.append(Finding(
            "subentry-order", start, start + len(current.term),
            f"subentry {current.term!r} should come before {previous.term!r}"
            + aside,
            severity=severity,
        ))
    return found


# ---------------------------------------------------------------------------
# page numbers
# ---------------------------------------------------------------------------

def _drop_leading_year(refs):
    """Drop a leading reference that is really a year in the entry name.

    "Nuclear Non-Proliferation Treaty, 1968, 322" and '"Ucayali, 1871" curare,
    37' both put a year where a page number would go. A year is recognisable
    because every reference after it is smaller — a real page list that opened
    at 1968 would carry on upwards.
    """
    if len(refs) > 1 and 1000 <= refs[0].page <= 2100:
        if all(r.page < refs[0].page for r in refs[1:]):
            return refs[1:]
    return refs


def _reference_lists(entry: Entry):
    for refs in [entry.general] + [s.refs for s in entry.subentries]:
        yield _drop_leading_year(refs)


def check_page_order(entry: Entry) -> list[Finding]:
    """Page numbers within a reference list must not go backwards.

    Equal numbers are allowed: §11 puts the roman page before the italic one
    when the same page is indexed for text and for an illustration.
    """
    found = []
    for refs in _reference_lists(entry):
        for previous, current in zip(refs, refs[1:]):
            if current.page < previous.page:
                found.append(Finding(
                    "page-order", current.start, current.stop,
                    f"{current.page} comes after {previous.page}; "
                    "page numbers should run in ascending order",
                ))
    return found


def check_range_order(entry: Entry) -> list[Finding]:
    """A page range must not run backwards (30–20)."""
    found = []
    for refs in _reference_lists(entry):
        for ref in refs:
            if ref.is_range and ref.end is not None and ref.end < ref.page:
                found.append(Finding(
                    "range-order", ref.start, ref.stop,
                    f"the range {ref.text} ends before it begins",
                ))
    return found


def check_duplicate_pages(entry: Entry) -> list[Finding]:
    """A page should not be listed twice in one reference list.

    §11 allows the same page twice when the second is an illustration, set in
    italic — 'New York City, 7, 34, 34, 53' — so an italic repeat is fine.
    """
    found = []
    for refs in _reference_lists(entry):
        seen: dict[int, pagerefs.PageRef] = {}
        for ref in refs:
            if ref.is_range or ref.note_marker:
                continue
            earlier = seen.get(ref.page)
            if earlier is not None and not ref.italic:
                found.append(Finding(
                    "duplicate-page", ref.start, ref.stop,
                    f"page {ref.page} is already listed in this entry"
                    " (an illustration reference would be italic)",
                ))
            seen.setdefault(ref.page, ref)
    return found


def check_elision(entry: Entry) -> list[Finding]:
    """Page ranges are elided as §9 requires.

    Two digits minimum (22–23, not 22–3), no more than needed (143–47, not
    143–147), three in the x00–x09 band (608–609).
    """
    found = []
    for refs in _reference_lists(entry):
        for ref in refs:
            if not ref.is_range or ref.end is None or ref.end < ref.page:
                continue
            wanted = elide(ref.page, ref.end)
            if wanted == ref.end_text:
                continue
            stop = ref.stop if not ref.note_marker else ref.note_start
            found.append(Finding(
                "elision", stop - len(ref.end_text), stop,
                f"§9 writes this range as {ref.page}{EN_DASH}{wanted}",
                action="replace", replacement=wanted,
            ))
    return found


def check_page_too_high(entry: Entry, last_page: int | None) -> list[Finding]:
    """No page reference may point past the end of the book."""
    if not last_page:
        return []
    found = []
    for refs in _reference_lists(entry):
        for ref in refs:
            highest = max(ref.page, ref.end or 0)
            if highest > last_page:
                found.append(Finding(
                    "page-too-high", ref.start, ref.stop,
                    f"page {highest} is past the last page of the book "
                    f"({last_page})",
                ))
    return found


# ---------------------------------------------------------------------------
# notes, per §17
# ---------------------------------------------------------------------------

def check_note_italics(entry: Entry) -> list[Finding]:
    """A note marker and its note numbers are italic (§17).

    §17 sets both: 82n, 82 and n, 304n1, 305nn1, 7. The page number itself
    stays roman.
    """
    found = []
    for refs in _reference_lists(entry):
        for ref in refs:
            if not ref.note_marker:
                continue
            start, stop = ref.note_start, ref.note_stop
            if all(entry.italics[start:stop]):
                continue
            found.append(Finding(
                "note-italics", start, stop,
                f"§17 sets {entry.text[start:stop]!r} in italic",
                action="italicise",
            ))
    return found


def check_roman_note_comma(entry: Entry) -> list[Finding]:
    """The comma between italic note numbers is italic too (§17: 305nn1, 7)."""
    found = []
    for refs in _reference_lists(entry):
        for ref in refs:
            if len(ref.note_numbers) < 2:
                continue
            for m in re.finditer(",", entry.text[ref.note_start:ref.note_stop]):
                at = ref.note_start + m.start()
                if not entry.italics[at]:
                    found.append(Finding(
                        "roman-note-comma", at, at + 1,
                        "§17 sets the comma between note numbers in italic",
                    ))
    return found


# ---------------------------------------------------------------------------
# punctuation and spacing
# ---------------------------------------------------------------------------

_STRAIGHT_OPEN = re.compile(r"(?<![\w,.;:!?)\]])['\"]")

def check_quotes(entry: Entry) -> list[Finding]:
    """Straight quotes become curly ones."""
    found = []
    for m in re.finditer(r"['\"]", entry.text):
        straight = m.group(0)
        opening = bool(_STRAIGHT_OPEN.match(entry.text, m.start()))
        if straight == '"':
            curly = "“" if opening else "”"
        else:
            curly = "‘" if opening else "’"
        found.append(Finding(
            "quotes", m.start(), m.end(),
            f"straight quote becomes {curly}",
            action="replace", replacement=curly,
        ))
    return found


def check_number_dashes(entry: Entry) -> list[Finding]:
    """A dash between two numbers is an en dash, with no spaces (§9)."""
    found = []
    for m in re.finditer(r"(?<=\d)(\s*[-‐‑‒—]\s*)(?=\d)",
                         entry.text):
        found.append(Finding(
            "number-dash", m.start(1), m.end(1),
            "a page range takes an en dash with no spaces (§9)",
            action="replace", replacement=EN_DASH,
        ))
    # an en dash that is right, but padded with spaces
    for m in re.finditer(r"(?<=\d)(\s+–\s*|\s*–\s+)(?=\d)", entry.text):
        found.append(Finding(
            "number-dash", m.start(1), m.end(1),
            "a page range takes an en dash with no spaces (§9)",
            action="replace", replacement=EN_DASH,
        ))
    return found


def check_spaced_dash(entry: Entry) -> list[Finding]:
    """A dash with a space on either side, outside a page range."""
    found = []
    for m in re.finditer(r"(?<!\d)[-‐-―]\s|\s[-‐-―](?!\d)",
                         entry.text):
        found.append(Finding(
            "spaced-dash", m.start(), m.end(),
            "a dash with a space beside it",
        ))
    return found


def check_whitespace(entry: Entry) -> list[Finding]:
    """Tabs go; runs of spaces collapse to one."""
    found = []
    for m in re.finditer(r"\t+", entry.text):
        found.append(Finding("whitespace", m.start(), m.end(),
                             "tab removed", action="delete"))
    for m in re.finditer(r"  +", entry.text):
        found.append(Finding("whitespace", m.start(), m.end() - 1,
                             "extra space removed", action="delete"))
    return found


_CLUSTER = re.compile(r"[,;.]\s*[,;]|[,;]\s*\.")

#: Abbreviations whose full stop is followed by a comma quite properly —
#: "Adam, A. O., 315" and "Benjamin, Park, Jr., 176" are not doubled
#: punctuation.
_ABBREVIATIONS = {"jr", "sr", "mr", "mrs", "ms", "dr", "st", "co", "inc",
                  "ltd", "no", "vol", "ed", "trans", "et al"}


def _ends_an_abbreviation(text: str, dot: int) -> bool:
    """True if the full stop at ``dot`` closes an initial or abbreviation."""
    word = re.search(r"([A-Za-z]+)\.$", text[:dot + 1])
    if not word:
        return False
    return len(word.group(1)) == 1 or word.group(1).lower() in _ABBREVIATIONS


def check_punctuation_clusters(entry: Entry) -> list[Finding]:
    """Doubled or mismatched punctuation, and punctuation at the end."""
    found = []
    for m in _CLUSTER.finditer(entry.text):
        if m.group(0)[0] == "." and _ends_an_abbreviation(entry.text, m.start()):
            continue
        found.append(Finding(
            "punctuation", m.start(), m.end(),
            f"{m.group(0)!r} — doubled punctuation",
        ))
    trailing = re.search(r"[,;:.]\s*$", entry.text)
    if trailing and not (entry.text[trailing.start()] == "."
                         and _ends_an_abbreviation(entry.text, trailing.start())):
        found.append(Finding(
            "punctuation", trailing.start(), trailing.start() + 1,
            "an entry should not end with punctuation",
        ))
    return found


def check_italic_punctuation(entry: Entry) -> list[Finding]:
    """The comma before page numbers is roman, even after an italic entry.

    §3 says so outright and §8 repeats it for titles of works. The same goes
    for the semicolons that separate subentries.
    """
    found = []
    spans = [(entry.term_stop, "the comma after an entry")]
    for ref in entry.general:
        spans.append((ref.stop, "the comma between page numbers"))
    for segment in entry.subentries + entry.crossrefs:
        spans.append((segment.start - 1, "the semicolon between entries"))
        for ref in segment.refs:
            spans.append((ref.stop, "the comma between page numbers"))

    seen = set()
    for at, what in spans:
        if at < 0 or at >= len(entry.text) - 1:
            continue
        m = re.match(r"\s*([,;])", entry.text[at:])
        if not m:
            continue
        position = at + m.start(1)
        if position in seen or not entry.italics[position]:
            continue
        seen.add(position)
        found.append(Finding(
            "italic-punctuation", position, position + 1,
            f"{what} should be roman, not italic (§3)",
        ))
    return found


# ---------------------------------------------------------------------------
# cross-references and wording
# ---------------------------------------------------------------------------

_SEE = re.compile(r"(?:(?<=[,;(])|^)(\s*)(see\s+also|see)\b", re.IGNORECASE)

def check_see_style(entry: Entry) -> list[Finding]:
    """'see' and 'see also' are lowercase and italic (§15, §16)."""
    found = []
    for m in _SEE.finditer(entry.text):
        start, stop = m.start(2), m.end(2)
        word = m.group(2)
        if word != word.lower():
            # lowercase and italic in one edit — they are the same span, so
            # they cannot be two findings
            found.append(Finding(
                "see-style", start, stop,
                f"{word!r} is lowercase and italic in an index (§15)",
                action="replace", replacement=word.lower(), italic=True,
            ))
        elif not all(entry.italics[start:stop]):
            found.append(Finding(
                "see-style", start, stop,
                f"{word!r} is set in italic (§15)",
                action="italicise",
            ))
    return found


def check_spelled_out_titles(entry: Entry) -> list[Finding]:
    """§7 wants personal titles abbreviated.

    Only where the rank actually titles a person — after the comma that
    follows a surname, as in "Sherman, Major General William Tecumseh". The
    same words open plenty of entries that are not titles at all:
    "General Electric", "Major, Randolph", "Major and, 114".
    """
    found = []
    pattern = "|".join(sorted(SPELLED_OUT_TITLES, key=len, reverse=True))
    for m in re.finditer(rf",\s+({pattern})\s+[A-Z]", entry.text):
        found.append(Finding(
            "spell-out-title", m.start(1), m.end(1),
            f"§7 abbreviates personal titles — {m.group(1)!r}",
        ))
    return found


def check_post_world(entry: Entry) -> list[Finding]:
    """'post-World' — the hyphen is worth a second look."""
    return [Finding("post-world", m.start(), m.end(),
                    "check the hyphen in 'post-World'")
            for m in re.finditer(r"post(-)World", entry.text)]


def check_ff_passim(entry: Entry) -> list[Finding]:
    """§9: do not use ff. or passim."""
    return [Finding("ff-passim", m.start(), m.end(),
                    f"§9 does not use {m.group(0)!r}")
            for m in re.finditer(r"(?<![A-Za-z])ff\.|\bpassim\b", entry.text)]


def check_has_term(entry: Entry) -> list[Finding]:
    """A paragraph that is page numbers alone — usually a stray turnover line.

    Numeric entries are real ("911/999, 4, 5"), so this only fires when the
    whole paragraph is digits, commas, spaces and dashes with nothing else.
    """
    if re.fullmatch(r"[\d,;\s\u2013\u2014-]+", entry.text.strip() or "x"):
        return [Finding("no-term", 0, min(len(entry.text), 40),
                        "this paragraph is page numbers with no entry term")]
    return []


#: Rules that look at one entry on its own.
PER_ENTRY = [
    check_page_order, check_range_order, check_subentry_order,
    check_duplicate_pages, check_elision, check_note_italics,
    check_roman_note_comma, check_quotes, check_number_dashes,
    check_spaced_dash, check_whitespace, check_punctuation_clusters,
    check_italic_punctuation, check_see_style, check_spelled_out_titles,
    check_post_world, check_ff_passim, check_has_term,
]
