"""Parsing page references, per FSG Indexing Guidelines §9, §11 and §17.

A reference is one of:

* a plain page number             ``15``
* a range                         ``171–72``  (elided per §9)
* a footnote                      ``82n``     (§17)
* an endnote with note numbers    ``304n1``, ``305nn1, 7``
* text plus footnote              ``82 and n``

Italic numbers point at illustrations (§11) and italic note numbers belong to
the note form, so the parser is told which characters are italic and carries
that through — several rules turn on it.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

EN_DASH = "–"
DASHES = "-‐‑‒–—"

# One reference: page, optional range, optional note marker and note numbers.
_REF = re.compile(
    r"(?P<page>\d+)"
    r"(?:\s*(?P<dash>[" + DASHES + r"])\s*(?P<end>\d+))?"
    r"(?:\s*(?P<and>and)\s+)?"
    r"(?P<n>n{1,2})?"
    r"(?P<notes>\d+)?",
    re.IGNORECASE,
)

# Continuation of an "nn" note list: ", 7" in ``305nn1, 7``.
_MORE_NOTES = re.compile(r"\s*,\s*(\d+)")


@dataclass
class PageRef:
    """A single page reference within an entry."""

    page: int
    end: int | None = None          # resolved end of a range, un-elided
    end_text: str = ""              # the second number exactly as written
    dash: str = ""                  # the dash character actually used
    note_marker: str = ""           # "n", "nn" or ""
    note_numbers: list[int] = field(default_factory=list)
    has_and: bool = False           # the "82 and n" form
    italic: bool = False            # illustration reference (§11)
    start: int = 0                  # character offsets within the paragraph
    stop: int = 0
    text: str = ""

    @property
    def is_range(self) -> bool:
        return self.end is not None


def unelide(start: int, end_text: str) -> int:
    """Expand an elided range end: (171, '72') -> 172, (310, '11') -> 311."""
    if not end_text:
        return start
    head = str(start)
    if len(end_text) >= len(head):
        return int(end_text)
    return int(head[: len(head) - len(end_text)] + end_text)


def elide(start: int, end: int) -> str:
    """The second number of a range as §9 wants it written.

    Two digits minimum (22–23, not 22–3); no more digits than needed
    (143–47, not 143–147); three digits in the x00–x09 band (608–609).
    """
    head, tail = str(start), str(end)
    if len(head) != len(tail):
        return tail
    if start % 100 <= 9:                     # §9 exception: 100–109, 608–609
        return tail
    shared = 0
    while shared < len(head) - 1 and head[shared] == tail[shared]:
        shared += 1
    return tail[min(shared, len(tail) - 2):]


def _mask_parentheses(text: str) -> str:
    """Blank out parenthesised spans.

    What is in brackets is a qualifier, not a reference: a disambiguating year
    in "market share of (1917), 223", or a cross-reference in
    "171-72 (see also Bell System)". Reading either as a page number puts a
    four-digit "page" in the middle of the list.
    """
    out, depth = [], 0
    for ch in text:
        if ch == "(":
            depth += 1
        out.append(" " if depth else ch)
        if ch == ")":
            depth = max(0, depth - 1)
    return "".join(out)


def parse(text: str, italics: list[bool] | None = None, offset: int = 0) -> list[PageRef]:
    """Pull every page reference out of a stretch of text."""
    text = _mask_parentheses(text)
    refs: list[PageRef] = []
    pos = 0
    while True:
        m = _REF.search(text, pos)
        if not m:
            break
        page = int(m.group("page"))
        end_text = m.group("end") or ""
        notes = [int(m.group("notes"))] if m.group("notes") else []
        stop_at = m.end()
        # ``nn`` takes a list of note numbers (§17: 305nn1, 7). The list runs
        # only as far as the italics do — that is what separates "305nn1, 7"
        # from "304n1, 305...", where the next page number is roman.
        if m.group("n") and m.group("n").lower() == "nn" and notes:
            while True:
                more = _MORE_NOTES.match(text, stop_at)
                if not more:
                    break
                if italics is not None:
                    span = italics[more.start(1) + offset : more.end(1) + offset]
                    if not (span and all(span)):
                        break
                notes.append(int(more.group(1)))
                stop_at = more.end()
        start, stop = m.start() + offset, stop_at + offset
        ital = False
        if italics:
            span = italics[m.start() + offset : m.start() + offset + len(m.group("page"))]
            ital = bool(span) and all(span)
        refs.append(
            PageRef(
                page=page,
                end=unelide(page, end_text) if end_text else None,
                end_text=end_text,
                dash=m.group("dash") or "",
                note_marker=(m.group("n") or "").lower(),
                note_numbers=notes,
                has_and=bool(m.group("and")),
                italic=ital,
                start=start,
                stop=stop,
                text=text[m.start():stop_at],
            )
        )
        pos = stop_at          # skip text an "nn" list already consumed
    return refs
