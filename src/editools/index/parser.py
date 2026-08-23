"""Parsing an index entry in FSG's paragraph form (§12, §15, §16).

An entry is one Word paragraph::

    AT&T, 13, 15, 171–72 (see also Bell System); area codes created by,
    300–301; engineering department of, see Bell Labs; ...

The main term is followed by its general page references, then subentries run
in and separated by semicolons (§12). Cross-references are the last "subentry"
(§15), so once a segment *begins* with "see" or "see also" everything after it
is another cross-reference target rather than a new subentry.

That last distinction matters: ``lawsuits involving, see patent litigation``
is a subentry whose value happens to be a cross-reference, and the entry
carries on with ordinary subentries afterwards. Only a segment that *starts*
with the cross-reference closes the list. A ``(see also ...)`` inside
parentheses is scoped to those parentheses and closes nothing.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

from . import pagerefs
from .pagerefs import PageRef

#: The note at the top of an index, not an entry (§11).
ILLUSTRATION_NOTE = re.compile(r"^\s*page numbers in\b.*\brefer to\b", re.IGNORECASE)

_SEE_START = re.compile(r"^\s*\(?\s*see(\s+also)?\b", re.IGNORECASE)
_SEE_ANY = re.compile(r"\bsee(\s+also)?\b", re.IGNORECASE)


@dataclass
class Segment:
    """One semicolon-delimited piece of an entry."""

    text: str
    start: int                       # offset within the paragraph
    refs: list[PageRef] = field(default_factory=list)
    is_crossref: bool = False        # segment begins with "see"/"see also"
    term: str = ""                   # the part before the page references

    @property
    def stop(self) -> int:
        return self.start + len(self.text)


@dataclass
class Entry:
    """A parsed index entry."""

    text: str
    italics: list[bool]
    term: str = ""
    term_stop: int = 0               # where the main term ends
    general: list[PageRef] = field(default_factory=list)
    subentries: list[Segment] = field(default_factory=list)
    crossrefs: list[Segment] = field(default_factory=list)
    colon_form: bool = False         # "Term: sub, refs" — no general refs (§12)
    is_note: bool = False            # the illustration note, not an entry
    head: "Segment | None" = None    # the main term and its general references


def _split_segments(text: str) -> list[tuple[str, int]]:
    """Split on semicolons that are not inside parentheses."""
    out, depth, start = [], 0, 0
    for i, ch in enumerate(text):
        if ch == "(":
            depth += 1
        elif ch == ")":
            depth = max(0, depth - 1)
        elif ch == ";" and depth == 0:
            out.append((text[start:i], start))
            start = i + 1
    out.append((text[start:], start))
    return out


def _find_top_level(text: str, pattern: str) -> int:
    """Offset of the first match outside parentheses, or -1.

    A colon or semicolon inside brackets belongs to a cross-reference —
    "lawsuits involving (see monopolies: lawsuits against; patent litigation)"
    is one segment, not a colon-form entry with subentries.
    """
    depth = 0
    for m in re.finditer(r"[()]|" + pattern, text):
        token = m.group(0)
        if token == "(":
            depth += 1
        elif token == ")":
            depth = max(0, depth - 1)
        elif depth == 0:
            return m.start()
    return -1


def _mask_quoted(text: str) -> str:
    """Blank out quoted spans, keeping offsets.

    A title in quotes can hold a comma and a year — '"Ucayali, 1871" curare,
    37' — and reading that comma as the boundary between the term and its
    page references turns 1871 into a page number.

    The comma that sits *immediately* before the closing quote is the
    exception: house style tucks the separator inside the quotation mark, so
    the comma in '"Purple Rain," 148' is the boundary rather than part of the
    title. Left masked, the term reads '"Purple Rain," 148' and folds to
    "purplerain148", which files after every other Purple Rain entry.
    """
    out, quote = [], None
    for ch in text:
        if quote is None and ch in "\u201c\"":
            quote = "\u201d" if ch == "\u201c" else "\""
            out.append(ch)
        elif quote is not None and ch == quote:
            quote = None
            if out and text[len(out) - 1] == ",":
                out[-1] = ","
            out.append(ch)
        else:
            out.append(" " if quote else ch)
    return "".join(out)


def _term_of(segment: str) -> str:
    """The term part of a segment — everything before its page references.

    A cross-reference ends the term as surely as a page number does, and it is
    not always a comma that introduces it: a dummy entry may be written
    "hoe. See garden hoe". Left in, the whole clause folds into the sort key
    and the entry files under "hoeseegardenhoe", well past every real h.
    """
    m = re.search(r"[,.]\s*(?=\(?see\b)|,(?P<quote>[\u201d\u2019\"']*)\s*(?=\d)",
                  _mask_quoted(segment), re.IGNORECASE)
    if not m:
        return segment.strip()
    # keep a closing quote on the term, so it reads '"Purple Rain,"' rather
    # than being cut off mid-title at the comma
    stop = m.end("quote") if m.group("quote") else m.start()
    return segment[:stop].strip()


def parse(text: str, italics: list[bool] | None = None) -> Entry:
    """Parse one paragraph into an Entry."""
    italics = italics or [False] * len(text)
    entry = Entry(text=text, italics=italics)

    if ILLUSTRATION_NOTE.match(text):
        entry.is_note = True
        return entry

    body, offset = text, 0

    # "New York City: architecture, ..." — a colon means no general references
    # and everything after it is a subentry (§12).
    colon = _find_top_level(body, r":\s")
    first_semi = _find_top_level(body, r";")
    first_comma = _find_top_level(body, r",")
    if colon != -1 and (first_semi == -1 or colon < first_semi) \
            and (first_comma == -1 or colon < first_comma):
        entry.colon_form = True
        entry.term = body[:colon].strip()
        entry.term_stop = colon
        offset = colon + 2
        body = body[offset:]

    segments: list[Segment] = []
    seen_crossref = False
    for raw, rel in _split_segments(body):
        start = rel + offset
        seg = Segment(text=raw, start=start)
        seg.term = _term_of(raw)
        # Parse references from after the term only. A subentry may open with a
        # year — "1956 consent decree for, 391" — and reading that as a page
        # number drops a four-digit entry into the middle of the list.
        head = len(raw) - len(raw.lstrip()) + len(seg.term)
        seg.refs = pagerefs.parse(raw[head:], italics, offset=start + head)
        # Once a segment opens with "see"/"see also", the rest are targets (§15).
        if seen_crossref or _SEE_START.match(raw):
            seg.is_crossref = True
            seen_crossref = True
        segments.append(seg)

    if not entry.colon_form and segments:
        head = segments.pop(0)
        entry.head = head
        entry.term = head.term
        entry.term_stop = head.start + len(head.term)
        entry.general = head.refs
        # "transportation, see mass transit" — a dummy entry (§16). Its own
        # cross-reference makes every following segment a target too.
        if _SEE_ANY.search(head.text) and not head.refs:
            seen_crossref = True
            for seg in segments:
                seg.is_crossref = True

    entry.subentries = [s for s in segments if not s.is_crossref]
    entry.crossrefs = [s for s in segments if s.is_crossref]
    return entry


# ---------------------------------------------------------------------------
# cross-reference targets
# ---------------------------------------------------------------------------

_SEE_WORD = re.compile(r"\bsee(\s+also)?\b", re.IGNORECASE)


@dataclass
class Target:
    """One thing a cross-reference points at."""

    text: str                        # as written, trimmed
    start: int                       # offset within the paragraph
    stop: int
    also: bool = False               # "see also" rather than "see"
    italic: bool = False             # a whole category, not an entry (§15)

    @property
    def entry_name(self) -> str:
        """The main entry a target names, dropping any ': subentry' (§16)."""
        return self.text.split(":")[0].strip()


def _split_top_level(text: str, start: int) -> list[tuple[str, int]]:
    """Split on semicolons outside parentheses, keeping offsets."""
    out, depth, at = [], 0, 0
    for i, ch in enumerate(text):
        if ch == "(":
            depth += 1
        elif ch == ")":
            depth = max(0, depth - 1)
        elif ch == ";" and depth == 0:
            out.append((text[at:i], start + at))
            at = i + 1
    out.append((text[at:], start + at))
    return out


def _trim(text: str, start: int) -> tuple[str, int, int]:
    """Strip surrounding space and brackets, keeping offsets straight."""
    lead = len(text) - len(text.lstrip(" ("))
    trimmed = text.strip(" ()").rstrip(".,;")
    return trimmed, start + lead, start + lead + len(trimmed)


def crossref_targets(entry: Entry) -> list[Target]:
    """Every entry a cross-reference in this paragraph points at.

    Three shapes, and the scope of a target depends on which one it is:

    * the trailing run of cross-references, where §15 continues the list of
      targets across semicolons to the end of the paragraph;
    * a ``see`` inside a subentry, which ends at that subentry's semicolon —
      "engineering department of, see Bell Labs; etiquette encouraged by, 137"
      points at one entry, not two;
    * a parenthetical ``(see also ...)``, scoped to its brackets.
    """
    targets: list[Target] = []

    def add(text: str, start: int, also: bool):
        trimmed, begin, end = _trim(text, start)
        if not trimmed:
            return
        targets.append(Target(
            trimmed, begin, end, also=also,
            italic=bool(entry.italics[begin:end]) and all(entry.italics[begin:end]),
        ))

    # 1. the trailing cross-reference run (§15)
    if entry.crossrefs:
        first = entry.crossrefs[0]
        m = _SEE_WORD.search(first.text)
        also = bool(m and m.group(1))
        rest = entry.crossrefs
        if m:
            add(first.text[m.end():], first.start + m.end(), also)
            rest = entry.crossrefs[1:]
        # otherwise the "see" sits in the head — a dummy entry (§16) — and
        # every trailing segment is one of its targets
        for segment in rest:
            add(segment.text, segment.start, also)

    # 2. a "see" inside the head or a subentry, and any parenthetical
    for segment in ([entry.head] if entry.head else []) + entry.subentries:
        for m in _SEE_WORD.finditer(segment.text):
            also = bool(m.group(1))
            rest, at = segment.text[m.end():], segment.start + m.end()
            # a parenthetical closes at its bracket; otherwise the segment ends it
            depth = segment.text[:m.start()].count("(") - segment.text[:m.start()].count(")")
            if depth > 0:
                close = rest.find(")")
                if close != -1:
                    rest = rest[:close]
            for piece, start in _split_top_level(rest, at):
                add(piece, start, also)

    return targets
