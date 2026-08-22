"""Core data types shared by the extractor, the rule engine and the report."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum


class Verdict(str, Enum):
    """Outcome of applying one rule to one break."""

    OK = "OK"
    VIOLATION = "VIOLATION"
    SUSPECT = "SUSPECT"          # strong evidence of a problem, but not from MW itself
    NEEDS_CHECK = "NEEDS CHECK"  # a human has to decide
    ADVISORY = "ADVISORY"        # legal break, but a better one exists
    NOT_APPLICABLE = "n/a"

    @property
    def is_flag(self) -> bool:
        return self in (Verdict.VIOLATION, Verdict.SUSPECT, Verdict.NEEDS_CHECK)


#: Rule numbers in the order they appear in the ruleset document.
RULE_TITLES = {
    1: "General English words (MW syllable dots)",
    2: "Minimum letters before and after the hyphen",
    3: "Possessives",
    4: "Words set against an em dash",
    5: "Already-hyphenated (compound) words",
    6: "Proper nouns, names, and titles",
    7: "Compounds, prefixes, and suffixes",
    8: "URLs",
    9: "Non-English words not in MW",
}

#: Not part of the numbered ruleset, but a real finding class the audit produces.
CONSISTENCY_RULE = "Consistency"


@dataclass
class Finding:
    """One rule's verdict on one break."""

    rule: int | str
    verdict: Verdict
    message: str = ""

    @property
    def label(self) -> str:
        return f"Rule {self.rule}" if isinstance(self.rule, int) else str(self.rule)


@dataclass
class Break:
    """A single end-of-line hyphenated word found in the proof.

    ``left`` is the fragment before the line-ending hyphen, ``right`` the
    fragment that continues on the following line.  ``word`` is the two
    joined back together with no hyphen, which is the form looked up in
    Merriam-Webster.
    """

    pdf_page: int                 # 1-based physical page of the PDF file
    book_page: str                # printed folio, e.g. "204" or "" if none found
    line_index: int               # line number within the page
    left: str
    right: str
    hyphen_char: str              # the actual character that ended the line
    line_text: str
    next_line_text: str
    char_before: str = ""         # character immediately preceding ``left``, "" if space/start
    char_after: str = ""          # character immediately following ``right``, "" if space/end
    trailing_punct: str = ""      # punctuation attached after ``right``
    italic: bool = False          # the broken word is set in an italic face
    kind: str = "syllable"        # syllable | compound | url | artifact
    findings: list[Finding] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)

    # -- derived forms -------------------------------------------------

    @property
    def word(self) -> str:
        """The word as it would be set unbroken (no line-break hyphen)."""
        return self.left + self.right

    @property
    def display(self) -> str:
        """How the break appears in the proof, e.g. ``butch-/er's``."""
        return f"{self.left}-/{self.right}"

    @property
    def base(self) -> str:
        """The word with any possessive ending removed."""
        return strip_possessive(self.word)

    @property
    def is_possessive(self) -> bool:
        return self.word != self.base

    @property
    def break_index(self) -> int:
        """Number of characters of :attr:`word` that sit before the hyphen."""
        return len(self.left)

    # -- verdict roll-up -----------------------------------------------

    @property
    def worst(self) -> Verdict:
        order = [
            Verdict.VIOLATION,
            Verdict.SUSPECT,
            Verdict.NEEDS_CHECK,
            Verdict.ADVISORY,
            Verdict.OK,
            Verdict.NOT_APPLICABLE,
        ]
        for verdict in order:
            if any(f.verdict is verdict for f in self.findings):
                return verdict
        return Verdict.OK

    def finding_for(self, rule: int | str) -> Finding | None:
        for f in self.findings:
            if f.rule == rule:
                return f
        return None

    @property
    def _reportable(self) -> list[Finding]:
        """Findings worth printing: anything flagged, plus advisories.

        Advisories are carried too because they appear on the Flagged Items
        tab, and a row there with no stated reason is useless.
        """
        return [f for f in self.findings if f.verdict.is_flag or f.verdict is Verdict.ADVISORY]

    @property
    def flagged_rules(self) -> str:
        return ", ".join(f.label for f in self._reportable)

    @property
    def reason(self) -> str:
        return " | ".join(f"{f.label}: {f.message}" for f in self._reportable if f.message)


@dataclass
class LineBreakFinding:
    """A bad break *between* words (initials, numerals, Jr./Sr.) — Rule 6."""

    pdf_page: int
    book_page: str
    line_index: int
    tail: str        # the end of the line that breaks
    head: str        # the start of the next line
    verdict: Verdict
    message: str


APOSTROPHES = "'’ʼ"


def strip_possessive(word: str) -> str:
    """Remove a trailing possessive ``'s`` (or bare ``s'``) from *word*."""
    if len(word) > 2 and word[-1] in "sS" and word[-2] in APOSTROPHES:
        return word[:-2]
    if len(word) > 1 and word[-1] in APOSTROPHES:
        return word[:-1]
    return word


def letter_count(text: str) -> int:
    """Letters only — punctuation and digits do not count toward Rule 2."""
    return sum(1 for ch in text if ch.isalpha())
