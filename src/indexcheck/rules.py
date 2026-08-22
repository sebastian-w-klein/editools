"""The checks themselves.

Each rule takes a parsed entry and yields :class:`Finding` objects describing a
character range and what is wrong with it. Nothing here touches the document —
findings are turned into tracked changes and comments by :mod:`audit`, which
keeps the rules easy to test and lets them fire in any order.
"""

from __future__ import annotations

from dataclasses import dataclass

from . import pagerefs
from .parser import Entry
from .sortkey import candidate_keys, in_order

#: Highlight colour per rule, so the marked-up file is readable at a glance.
COLOURS = {
    "entry-order": "yellow",
    "subentry-order": "brightGreen",
    "page-order": "cyan",
    "range-order": "magenta",
}


@dataclass
class Finding:
    rule: str
    start: int
    stop: int
    message: str

    @property
    def colour(self) -> str:
        return COLOURS.get(self.rule, "yellow")


def _drop_leading_year(refs):
    """Drop a leading reference that is really a year in the entry name.

    "Nuclear Non-Proliferation Treaty, 1968, 322" and "Ucayali, 1871" curare,
    37" both put a year where a page number would go. A year is recognisable
    because every reference after it is smaller — a real page list that opened
    at 1968 would carry on upwards.
    """
    if len(refs) > 1 and 1000 <= refs[0].page <= 2100:
        if all(r.page < refs[0].page for r in refs[1:]):
            return refs[1:]
    return refs


def check_page_order(entry: Entry) -> list[Finding]:
    """Page numbers within a reference list must not go backwards.

    Equal numbers are allowed: §11 puts the roman page before the italic one
    when the same page is indexed for text and for an illustration.
    """
    found = []
    groups = [entry.general] + [s.refs for s in entry.subentries]
    for refs in groups:
        refs = _drop_leading_year(refs)
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
    groups = [entry.general] + [s.refs for s in entry.subentries]
    for refs in groups:
        for ref in refs:
            if ref.is_range and ref.end is not None and ref.end < ref.page:
                found.append(Finding(
                    "range-order", ref.start, ref.stop,
                    f"the range {ref.text} ends before it begins",
                ))
    return found


def check_subentry_order(entry: Entry) -> list[Finding]:
    """Subentries run in alphabetical order, letter by letter (§12).

    Initial prepositions and conjunctions do not count, so 'on operators'
    files under 'operators'.
    """
    subs = entry.subentries
    if len(subs) < 2:
        return []

    def violations(drop_prepositions: bool) -> list[Finding]:
        keys = [candidate_keys(s.term, subentry=True,
                               drop_prepositions=drop_prepositions) for s in subs]
        out = []
        for i in range(1, len(subs)):
            if not in_order(keys[i - 1], keys[i]):
                current, previous = subs[i], subs[i - 1]
                start = current.start + (len(current.text) - len(current.text.lstrip()))
                out.append(Finding(
                    "subentry-order", start, start + len(current.term),
                    f"subentry {current.term!r} should come before "
                    f"{previous.term!r}",
                ))
        return out

    # Whether initial prepositions count is a convention the index chooses,
    # not something to decide pair by pair — reading one pair each way lets an
    # inconsistent list slip through. Judge the whole list under both
    # conventions and report the one it follows more closely. On a tie the
    # house rule wins: initial prepositions and conjunctions do not count.
    return min(violations(True), violations(False), key=len)


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
        if previous is not None and not in_order(previous[0], keys):
            found.append((position, Finding(
                "entry-order", 0, max(1, entry.term_stop),
                f"{entry.term!r} should come before {previous[1]!r}",
            )))
        else:
            previous = (keys, entry.term)
    return found


#: Rules that look at one entry on its own.
PER_ENTRY = [check_page_order, check_range_order, check_subentry_order]
