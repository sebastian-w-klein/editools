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


def _term_of(segment: str) -> str:
    """The term part of a segment — everything before its page references."""
    m = re.search(r",\s*(?=\d|\(?see\b)", segment, re.IGNORECASE)
    return (segment[: m.start()] if m else segment).strip()


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
    colon = re.search(r":\s", body)
    first_semi = body.find(";")
    first_comma = body.find(",")
    if colon and (first_semi == -1 or colon.start() < first_semi) \
            and (first_comma == -1 or colon.start() < first_comma):
        entry.colon_form = True
        entry.term = body[: colon.start()].strip()
        entry.term_stop = colon.start()
        offset = colon.end()
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
