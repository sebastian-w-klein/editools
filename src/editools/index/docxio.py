"""Reading and editing a Word index with Track Changes on.

Everything the checker does to a document goes through here. Three constraints
shape this module, all of them found by trying it rather than by reading the
spec:

1. Runs must be walked recursively and deletion-aware. Word splits text across
   ``<w:r>`` runs, and an edit moves runs *inside* ``<w:ins>`` / ``<w:del>``
   wrappers. Text inside ``w:del`` is no longer part of the current text, so a
   scan of direct children corrupts every offset after the first edit.

2. Italic cannot be tested by the presence of ``<w:i>``. Word writes an
   explicit ``<w:i w:val="0"/>`` to mean *not* italic, so presence alone reports
   whole paragraphs as italic. Several rules turn on real italics.

3. Edits must be applied in descending character offset, and at the same offset
   a deletion must precede an insertion — otherwise each edit invalidates the
   offsets of the ones after it. :class:`EditQueue` enforces both.
"""

from __future__ import annotations

import copy
import datetime as _dt
from dataclasses import dataclass

from docx.oxml.ns import qn
from docx.text.run import Run
from lxml import etree

W = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"
AUTHOR = "Index Checker"
INITIALS = "IC"


def _stamp() -> str:
    return _dt.datetime.now(_dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


class _Ids:
    """Revision ids, unique within a document."""

    def __init__(self, start: int = 9000):
        self.n = start

    def next(self) -> str:
        self.n += 1
        return str(self.n)


def el(tag: str, **attrs) -> etree._Element:
    node = etree.Element(qn(tag))
    for key, value in attrs.items():
        node.set(qn(key.replace("_", ":")), value)
    return node


def toggle_on(rPr, tag: str) -> bool:
    """True when a toggle property is genuinely on (an absent w:val means on)."""
    if rPr is None:
        return False
    node = rPr.find(W + tag)
    if node is None:
        return False
    return node.get(qn("w:val")) not in ("0", "false", "off")


def live_runs(p) -> list:
    """Runs contributing to the paragraph's current text (skipping deletions)."""
    return [
        r for r in p.iter(W + "r")
        if not any(a.tag == W + "del" for a in r.iterancestors())
    ]


def read(p) -> tuple[str, list[bool]]:
    """The paragraph's current text, and whether each character is italic."""
    chunks, italics = [], []
    for run in live_runs(p):
        node = run.find(W + "t")
        if node is None or not node.text:
            continue
        on = toggle_on(run.find(W + "rPr"), "i")
        chunks.append(node.text)
        italics.extend([on] * len(node.text))
    return "".join(chunks), italics


def _split(run, at: int):
    """Split a run's text at ``at``; return the new trailing run, or None."""
    node = run.find(W + "t")
    text = node.text or ""
    if at <= 0 or at >= len(text):
        return None
    tail = copy.deepcopy(run)
    node.text = text[:at]
    node.set(qn("xml:space"), "preserve")
    tail_node = tail.find(W + "t")
    tail_node.text = text[at:]
    tail_node.set(qn("xml:space"), "preserve")
    run.addnext(tail)
    return tail


def isolate(p, start: int, stop: int) -> list:
    """Runs covering exactly characters [start, stop) of the current text."""
    pos, targets = 0, []
    for run in live_runs(p):
        node = run.find(W + "t")
        if node is None or not node.text:
            continue
        length = len(node.text)
        r_start, r_stop = pos, pos + length
        pos = r_stop
        if r_stop <= start or r_start >= stop:
            continue
        current = run
        if r_start < start:
            tail = _split(current, start - r_start)
            if tail is not None:
                current = tail
            r_start = start
        node = current.find(W + "t")
        if r_start + len(node.text or "") > stop:
            _split(current, stop - r_start)
        targets.append(current)
    return targets


@dataclass
class Edit:
    """One pending change to a paragraph."""

    at: int
    kind: str            # "highlight" | "italic" | "delete" | "insert" | "comment"
    stop: int = 0
    text: str = ""
    colour: str = "yellow"
    note: str = ""


class EditQueue:
    """Collects edits for one paragraph and applies them safely.

    Rules are free to report findings in any order; the queue sorts them so
    later offsets are edited first and a deletion always precedes an insertion
    at the same offset.
    """

    #: formatting first, then text edits, deletions before insertions
    ORDER = {"comment": 0, "highlight": 1, "italic": 2, "delete": 3, "insert": 4}

    def __init__(self, document, paragraph, ids: _Ids):
        self.document = document
        self.p = paragraph
        self.ids = ids
        self.edits: list[Edit] = []

    def highlight(self, start, stop, colour="yellow", note=""):
        self.edits.append(Edit(start, "highlight", stop=stop, colour=colour))
        if note:
            self.comment(start, stop, note)

    def italicise(self, start, stop):
        self.edits.append(Edit(start, "italic", stop=stop))

    def delete(self, start, stop):
        self.edits.append(Edit(start, "delete", stop=stop))

    def insert(self, at, text, italic=False):
        self.edits.append(Edit(at, "insert", text=text, colour="i" if italic else ""))

    def comment(self, start, stop, note):
        self.edits.append(Edit(start, "comment", stop=stop, note=note))

    def apply(self) -> int:
        for edit in sorted(self.edits, key=lambda e: (-e.at, self.ORDER[e.kind])):
            getattr(self, "_" + edit.kind)(edit)
        return len(self.edits)

    # -- individual operations ------------------------------------------------

    def _highlight(self, edit: Edit):
        """Highlight as a tracked formatting change, so rejecting removes it."""
        for run in isolate(self.p, edit.at, edit.stop):
            rPr = run.find(W + "rPr")
            before = copy.deepcopy(rPr) if rPr is not None else None
            if rPr is None:
                rPr = el("w:rPr")
                run.insert(0, rPr)
            for old in rPr.findall(W + "highlight"):
                rPr.remove(old)
            rPr.append(el("w:highlight", w_val=edit.colour))
            self._record_format_change(rPr, before)

    def _italic(self, edit: Edit):
        for run in isolate(self.p, edit.at, edit.stop):
            rPr = run.find(W + "rPr")
            before = copy.deepcopy(rPr) if rPr is not None else None
            if rPr is None:
                rPr = el("w:rPr")
                run.insert(0, rPr)
            for old in rPr.findall(W + "i"):
                rPr.remove(old)
            rPr.insert(0, el("w:i"))
            self._record_format_change(rPr, before)

    def _record_format_change(self, rPr, before):
        """Attach a w:rPrChange holding the run's previous properties."""
        for old in rPr.findall(W + "rPrChange"):
            return  # already tracked by an earlier edit in this pass
        change = el("w:rPrChange", w_id=self.ids.next(),
                    w_author=AUTHOR, w_date=_stamp())
        inner = el("w:rPr")
        if before is not None:
            for child in before:
                if child.tag != W + "rPrChange":
                    inner.append(copy.deepcopy(child))
        change.append(inner)
        rPr.append(change)

    def _delete(self, edit: Edit):
        targets = isolate(self.p, edit.at, edit.stop)
        if not targets:
            return
        wrapper = el("w:del", w_id=self.ids.next(), w_author=AUTHOR, w_date=_stamp())
        targets[0].addprevious(wrapper)
        for run in targets:
            node = run.find(W + "t")
            deleted = el("w:delText")
            deleted.text = node.text
            deleted.set(qn("xml:space"), "preserve")
            run.remove(node)
            run.append(deleted)
            wrapper.append(run)

    def _insert(self, edit: Edit):
        wrapper = el("w:ins", w_id=self.ids.next(), w_author=AUTHOR, w_date=_stamp())
        run = el("w:r")
        if edit.colour == "i":
            rPr = el("w:rPr")
            rPr.append(el("w:i"))
            run.append(rPr)
        node = el("w:t")
        node.text = edit.text
        node.set(qn("xml:space"), "preserve")
        run.append(node)
        wrapper.append(run)
        targets = isolate(self.p, edit.at, edit.at + 1)
        if targets:
            targets[0].addprevious(wrapper)
        else:
            live = live_runs(self.p)
            if live:
                live[-1].addnext(wrapper)
            else:
                self.p.append(wrapper)

    def _comment(self, edit: Edit):
        targets = isolate(self.p, edit.at, edit.stop)
        if not targets:
            return
        runs = [Run(t, self.p) for t in targets]
        self.document.add_comment(runs, edit.note, author=AUTHOR, initials=INITIALS)
