"""Run a whole proof through extraction, lookup and the rule engine."""

from __future__ import annotations

import time
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field

from . import extract, rules
from .dictionary import Dictionary
from .model import Break, LineBreakFinding, Verdict, strip_possessive


@dataclass
class AuditResult:
    pdf_path: str
    breaks: list[Break]
    line_breaks: list[LineBreakFinding]
    page_count: int
    unique_words: int
    api_calls: int
    api_errors: list[str] = field(default_factory=list)
    dictionary_source: str = "Merriam-Webster API"
    elapsed: float = 0.0

    @property
    def flagged(self) -> list[Break]:
        return [b for b in self.breaks if b.worst.is_flag]

    @property
    def violations(self) -> list[Break]:
        return [b for b in self.breaks if b.worst is Verdict.VIOLATION]

    @property
    def advisories(self) -> list[Break]:
        return [b for b in self.breaks if b.worst is Verdict.ADVISORY]

    @property
    def needs_check(self) -> list[Break]:
        return [b for b in self.breaks if b.worst in (Verdict.NEEDS_CHECK, Verdict.SUSPECT)]

    @property
    def clean(self) -> list[Break]:
        return [b for b in self.breaks if b.worst in (Verdict.OK, Verdict.NOT_APPLICABLE)]

    @property
    def artifacts(self) -> list[Break]:
        return [b for b in self.breaks if b.kind == "artifact"]

    def counts(self) -> dict[str, int]:
        return {
            "Pages": self.page_count,
            "End-of-line hyphens found": len(self.breaks),
            "Extraction artifacts (no real break)": len(self.artifacts),
            "Real word divisions checked": len(self.breaks) - len(self.artifacts),
            "Unique words looked up": self.unique_words,
            "Violations": len(self.violations),
            "Needs check": len(self.needs_check),
            "Advisories": len(self.advisories),
            "Clean": len(self.clean),
            "Line-break findings (Rule 6)": len(self.line_breaks),
        }


def prefetch(words: list[str], dictionary: Dictionary, workers: int = 6, progress=None) -> None:
    """Warm the dictionary cache for every distinct word, in parallel.

    One book is a few hundred distinct words; done serially over the network
    that is the slow part of the whole run, and done concurrently it is a few
    seconds.  Everything lands in the on-disk cache, so the next book only
    pays for words this one did not contain.
    """
    if dictionary.offline:
        return
    done = 0
    with ThreadPoolExecutor(max_workers=workers) as pool:
        for _ in pool.map(dictionary.lookup, words):
            done += 1
            if progress and done % 25 == 0:
                progress(done, len(words))
    if progress:
        progress(len(words), len(words))


def run(
    pdf_path: str,
    dictionary: Dictionary,
    artifacts: list[str] | None = None,
    progress=None,
) -> AuditResult:
    """Audit *pdf_path* end to end."""
    started = time.time()

    def say(message: str) -> None:
        if progress:
            progress(message)

    say("Reading the PDF…")
    document = extract.load(pdf_path, artifacts)
    say(f"{len(document.pages)} pages, {len(document.breaks)} end-of-line hyphens found.")

    words = sorted({
        strip_possessive(b.word).lower()
        for b in document.breaks
        if b.kind not in ("artifact", "url")
    })
    if not dictionary.offline:
        say(f"Looking up {len(words)} distinct words in Merriam-Webster…")
        prefetch(words, dictionary)
        dictionary.save()

    say("Applying all nine rules to every break…")
    ctx = rules.Context(dictionary=dictionary, tokens=document.tokens)
    for brk in document.breaks:
        rules.evaluate(brk, ctx)
    rules.check_consistency(document.breaks, ctx)

    say("Checking line breaks for initials and numerals…")
    line_breaks = rules.check_line_breaks(document.pages, document.running_heads)

    dictionary.save()
    return AuditResult(
        pdf_path=pdf_path,
        breaks=document.breaks,
        line_breaks=line_breaks,
        page_count=len(document.pages),
        unique_words=len(words),
        api_calls=dictionary.api_calls,
        api_errors=dictionary.api_errors,
        dictionary_source=(
            "TeX en-US patterns (no Merriam-Webster key — Rule 1 unverified)"
            if dictionary.offline else "Merriam-Webster Collegiate API"
        ),
        elapsed=time.time() - started,
    )
