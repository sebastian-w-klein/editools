"""The nine rules, applied independently to every break.

The one thing this module must never do is stop early.  Clearing a word under
Rule 1 does not exempt it from Rules 2, 3, 4 or 9 — that shortcut is what let
``butch-/er's`` (Rule 3) and ``cher-/ries—or`` (Rule 4) through a manual pass.
So :func:`evaluate` runs every rule against every break and records a verdict
for each, including the ones that come back "not applicable".

The only exceptions are the ones the ruleset itself states: Rule 8 says URLs
are governed solely by Rule 8, and a break that falls at a compound's own
hyphen is Rule 5's business rather than Rule 1's.
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass

from .dictionary import Dictionary, Syllabification
from .model import (
    CONSISTENCY_RULE,
    Break,
    Finding,
    LineBreakFinding,
    Verdict,
    letter_count,
    strip_possessive,
)
from .textutil import (
    ends_in_vowel,
    is_initial,
    is_roman_numeral,
    leading_em_dash,
    trailing_em_dash,
)

MIN_BEFORE = 2
MIN_AFTER = 3

#: Rule 6.2 — independent English morphemes that end a name and must not be split.
NAME_MORPHEMES = (
    "worth", "ville", "son", "berg", "burg", "bury", "borough", "brook",
    "field", "ford", "hall", "ham", "haven", "hill", "house", "land",
    "man", "mont", "moor", "more", "mouth", "port", "ridge", "shire",
    "smith", "stead", "stone", "ton", "town", "wick", "wood", "well",
)

#: Rule 7 — morpheme boundaries preferred when MW allows more than one point.
PREFIXES = (
    "counter", "trans", "under", "inter", "super", "trans", "trans",
    "anti", "auto", "over", "post", "self", "semi", "sub", "dis", "mis",
    "non", "out", "pre", "pro", "com", "con", "for", "fore", "hyper",
    "il", "im", "in", "ir", "re", "un", "up", "de", "co", "ex", "bi",
)
SUFFIXES = (
    "giving", "ability", "ization", "ational", "ment", "ness", "less",
    "ship", "hood", "ward", "wise", "some", "like", "able", "ible",
    "ance", "ence", "tion", "sion", "ious", "eous", "ous", "ful", "ist",
    "ism", "ity", "ive", "ize", "ise", "ing", "est", "dom", "ery", "ary",
    "ly", "er", "ed", "al",
)

DIACRITICS = set("àáâãäåæçèéêëìíîïñòóôõöøùúûüýÿÀÁÂÃÄÅÆÇÈÉÊËÌÍÎÏÑÒÓÔÕÖØÙÚÛÜÝß")

#: Rule 8 — characters a URL may be broken *before*.
URL_BREAK_BEFORE = "/.,:-~_?#%@"
#: Rule 8 — characters a URL may be broken before *or* after.
URL_BREAK_EITHER = "=&"


@dataclass
class Context:
    """Everything a rule may consult beyond the break itself."""

    dictionary: Dictionary
    tokens: dict            # every whole token in the book, lowercased -> count
    min_before: int = MIN_BEFORE
    min_after: int = MIN_AFTER

    def token_count(self, text: str) -> int:
        return self.tokens.get(text.lower(), 0)


# --------------------------------------------------------------------------
# shared analysis
# --------------------------------------------------------------------------

NOT_COMPOUND = "not_compound"
AT_HYPHEN = "at_hyphen"
INSIDE_COMPONENT = "inside_component"
AMBIGUOUS = "ambiguous"


@dataclass
class Analysis:
    """Facts about a break that more than one rule needs."""

    compound_state: str
    syllabification: Syllabification
    hyphenated_form: str


def analyze_break(brk: Break, ctx: Context) -> Analysis:
    """Work out whether the break sits at a compound's own hyphen.

    This has to be settled before Rule 1 runs, because a compound broken at
    its hyphen is not a syllable division at all.  Three sources answer it,
    in order of reliability: the fragments themselves (a hyphen inside one of
    them settles it outright), the book's own text (if ``cross-legged`` is set
    intact on another page, that is the intended form), then MW.
    """
    hyphenated = f"{brk.left}-{brk.right}"
    base = strip_possessive(brk.word)

    if "-" in brk.left or "-" in brk.right:
        return Analysis(INSIDE_COMPONENT, ctx.dictionary.lookup(base), hyphenated)

    closed = ctx.dictionary.lookup(base)
    in_book = ctx.token_count(hyphenated) or ctx.token_count(strip_possessive(hyphenated))

    if closed.found and closed.source in ("mw", "override"):
        if in_book:
            return Analysis(AMBIGUOUS, closed, hyphenated)
        return Analysis(NOT_COMPOUND, closed, hyphenated)

    if in_book:
        return Analysis(AT_HYPHEN, closed, hyphenated)

    compound = ctx.dictionary.lookup(strip_possessive(hyphenated))
    if compound.found and compound.hyphenated_compound:
        return Analysis(AT_HYPHEN, compound, hyphenated)

    return Analysis(NOT_COMPOUND, closed, hyphenated)


# --------------------------------------------------------------------------
# the rules
# --------------------------------------------------------------------------


def rule_1(brk: Break, ctx: Context, info: Analysis) -> Finding:
    """General English words — the break must land on an MW division point."""
    if brk.kind == "url":
        return Finding(1, Verdict.NOT_APPLICABLE, "URLs are governed solely by Rule 8")
    if info.compound_state == AT_HYPHEN:
        return Finding(1, Verdict.NOT_APPLICABLE, "break falls at the compound's own hyphen (Rule 5)")
    if info.compound_state == INSIDE_COMPONENT:
        return Finding(1, Verdict.NOT_APPLICABLE, "compound word — Rule 5 governs the break point")

    syl = info.syllabification
    index = brk.break_index

    if syl.source in ("mw", "override"):
        source = "MW" if syl.source == "mw" else "overrides file"
        if not syl.positions:
            return Finding(
                1, Verdict.VIOLATION,
                f"{source} shows no division point in “{syl.word}” — the word may not be broken",
            )
        if index in syl.positions:
            return Finding(1, Verdict.OK, f"matches {source} ({syl.display})")
        return Finding(
            1, Verdict.VIOLATION,
            f"{source} shows {syl.display}; the break after “{brk.left}” is not a marked point",
        )

    if syl.source == "tex":
        if index in syl.positions:
            return Finding(
                1, Verdict.OK,
                f"matches TeX en-US patterns ({syl.display}) — not confirmed against MW",
            )
        return Finding(
            1, Verdict.SUSPECT,
            f"TeX en-US patterns suggest {syl.display}; the break after “{brk.left}” "
            f"does not match — confirm against MW",
        )

    if syl.consulted:
        return Finding(
            1, Verdict.NEEDS_CHECK,
            f"“{syl.word}” has no Merriam-Webster entry, so there is no marked division "
            f"point to check the break against — decide this one by hand",
        )
    return Finding(
        1, Verdict.NEEDS_CHECK,
        f"“{syl.word}” was not looked up (no Merriam-Webster key) and TeX has no pattern for it",
    )


def rule_2(brk: Break, ctx: Context, info: Analysis) -> Finding:
    """At least two letters before the hyphen and three after it."""
    if brk.kind == "url":
        return Finding(2, Verdict.NOT_APPLICABLE, "URLs are governed solely by Rule 8")

    before = letter_count(brk.left)
    after = letter_count(brk.right)
    problems = []
    if before < ctx.min_before:
        problems.append(f"only {before} letter(s) before the hyphen (minimum {ctx.min_before})")
    if after < ctx.min_after:
        problems.append(f"only {after} letter(s) after the hyphen (minimum {ctx.min_after})")

    if problems:
        message = "; ".join(problems)
        if info.compound_state == AT_HYPHEN:
            message += " — the minimums still apply at a compound's own hyphen, so the word may not be broken"
        return Finding(2, Verdict.VIOLATION, message)
    return Finding(2, Verdict.OK, f"{before} before / {after} after")


def rule_3(brk: Break, ctx: Context, info: Analysis) -> Finding:
    """A possessive 's does not count toward the three-letter minimum."""
    if brk.kind == "url":
        return Finding(3, Verdict.NOT_APPLICABLE, "URLs are governed solely by Rule 8")
    if not brk.is_possessive:
        return Finding(3, Verdict.NOT_APPLICABLE, "not a possessive")

    bare = letter_count(strip_possessive(brk.right))
    if bare < ctx.min_after:
        return Finding(
            3, Verdict.VIOLATION,
            f"discounting the possessive, only {bare} letter(s) follow the hyphen "
            f"(“{strip_possessive(brk.right)}”) — minimum {ctx.min_after}",
        )

    # "If a word cannot be broken without the possessive, it cannot be broken
    # with it attached either."
    syl = info.syllabification
    if syl.source in ("mw", "override"):
        base = strip_possessive(brk.word)
        usable = [
            p for p in syl.positions
            if letter_count(base[:p]) >= ctx.min_before and letter_count(base[p:]) >= ctx.min_after
        ]
        if not usable:
            return Finding(
                3, Verdict.VIOLATION,
                f"“{base}” has no break point that clears Rule 2 on its own, so it "
                f"may not be broken with the possessive attached either",
            )
    return Finding(3, Verdict.OK, f"{bare} letter(s) after the hyphen discounting the possessive")


def rule_4(brk: Break, ctx: Context, info: Analysis) -> Finding:
    """A word set tight against an em dash may not be broken at end of line."""
    if brk.kind == "url":
        return Finding(4, Verdict.NOT_APPLICABLE, "URLs are governed solely by Rule 8")

    before = leading_em_dash(brk.char_before)
    after = trailing_em_dash(brk.char_after)
    if before or after:
        side = "before" if before else "after"
        return Finding(
            4, Verdict.VIOLATION,
            f"set with no space against an em dash ({side} the word) and hyphenated "
            f"at end of line",
        )
    return Finding(4, Verdict.OK, "no em dash set tight against the word")


def rule_5(brk: Break, ctx: Context, info: Analysis) -> Finding:
    """A hyphenated compound may be broken only at one of its own hyphens."""
    if brk.kind == "url":
        return Finding(5, Verdict.NOT_APPLICABLE, "URLs are governed solely by Rule 8")

    state = info.compound_state
    if state == INSIDE_COMPONENT:
        return Finding(
            5, Verdict.VIOLATION,
            f"“{info.hyphenated_form}” already contains a hyphen; it may be broken only "
            f"at an existing hyphen, not at a syllable point inside a component",
        )
    if state == AT_HYPHEN:
        return Finding(5, Verdict.OK, "break falls at the compound's own hyphen")
    if state == AMBIGUOUS:
        return Finding(
            5, Verdict.NEEDS_CHECK,
            f"could rejoin as “{brk.word}” or as “{info.hyphenated_form}” — both appear "
            f"valid; confirm which form is set",
        )
    return Finding(5, Verdict.NOT_APPLICABLE, "not a hyphenated compound")


def rule_6(brk: Break, ctx: Context, info: Analysis) -> Finding:
    """Proper nouns: MW first, then a recognizable morpheme, then a vowel."""
    if brk.kind == "url":
        return Finding(6, Verdict.NOT_APPLICABLE, "URLs are governed solely by Rule 8")
    if not brk.left[:1].isupper():
        return Finding(6, Verdict.NOT_APPLICABLE, "not a proper-noun candidate")

    syl = info.syllabification
    if syl.source in ("mw", "override"):
        return Finding(6, Verdict.OK, f"listed in MW ({syl.display}) — Rule 1 governs the break")

    base = strip_possessive(brk.word).lower()
    for morpheme in NAME_MORPHEMES:
        if base.endswith(morpheme) and len(base) > len(morpheme) + 1:
            start = len(base) - len(morpheme)
            if start < brk.break_index < len(base):
                return Finding(
                    6, Verdict.VIOLATION,
                    f"splits the morpheme “-{morpheme}”; break at “{brk.word[:start]}-"
                    f"{brk.word[start:]}” instead",
                )
            return Finding(6, Verdict.OK, f"no MW entry; break does not split “-{morpheme}”")

    if ends_in_vowel(brk.left):
        return Finding(
            6, Verdict.OK,
            "no MW entry and no recognizable morpheme; the break follows a vowel (Rule 6.3)",
        )
    return Finding(
        6, Verdict.NEEDS_CHECK,
        "no MW entry, no recognizable morpheme, and the break does not follow a vowel — "
        "flag rather than guess (Rule 6.4)",
    )


def rule_7(brk: Break, ctx: Context, info: Analysis) -> Finding:
    """Prefer the morpheme boundary when MW allows more than one break point."""
    if brk.kind == "url":
        return Finding(7, Verdict.NOT_APPLICABLE, "URLs are governed solely by Rule 8")
    syl = info.syllabification
    if syl.source not in ("mw", "override") or len(syl.positions) < 2:
        return Finding(7, Verdict.NOT_APPLICABLE, "no alternative MW break point to prefer")

    base = strip_possessive(brk.word)
    lowered = base.lower()
    preferred = None
    for prefix in PREFIXES:
        if lowered.startswith(prefix) and len(prefix) in syl.positions:
            preferred = len(prefix)
            break
    if preferred is None:
        for suffix in SUFFIXES:
            if lowered.endswith(suffix) and len(base) - len(suffix) in syl.positions:
                preferred = len(base) - len(suffix)
                break

    if preferred is None or preferred == brk.break_index:
        return Finding(7, Verdict.OK, "break is at the natural morpheme boundary or none applies")
    if (
        letter_count(base[:preferred]) < ctx.min_before
        or letter_count(base[preferred:]) < ctx.min_after
    ):
        return Finding(7, Verdict.OK, "the morpheme boundary would fail Rule 2, so this break stands")
    return Finding(
        7, Verdict.ADVISORY,
        f"MW also allows “{base[:preferred]}-{base[preferred:]}”, the morpheme boundary, "
        f"which Rule 7 prefers over “{brk.left}-{brk.right}”",
    )


def rule_8(brk: Break, ctx: Context, info: Analysis) -> Finding:
    """URLs: never a hyphen at the break, and only at the listed characters."""
    if brk.kind != "url":
        return Finding(8, Verdict.NOT_APPLICABLE, "not a URL, domain or email address")

    joined = f"{brk.left}-{brk.right}"
    owns_hyphen = bool(ctx.token_count(joined))
    if owns_hyphen:
        detail = "a hyphen belonging to the address has been left at the end of the line"
    else:
        detail = "a hyphen has been added to break the address"
    suggestion = _url_break_suggestion(brk.left + brk.right)
    return Finding(8, Verdict.VIOLATION, f"{detail}; Rule 8 forbids both. {suggestion}")


def _url_break_suggestion(url: str) -> str:
    points = []
    for index, ch in enumerate(url):
        if index == 0:
            continue
        if ch in URL_BREAK_BEFORE or ch in URL_BREAK_EITHER:
            points.append(f"{url[:index]} / {url[index:]}")
    if url.startswith(("http://", "https://")):
        cut = url.index("//") + 2
        points.insert(0, f"{url[:cut]} / {url[cut:]}")
    if not points:
        return "No listed break character is available in this address."
    return "Break instead at: " + "; ".join(points[:3]) + (" …" if len(points) > 3 else "")


def rule_9(brk: Break, ctx: Context, info: Analysis) -> Finding:
    """Flag foreign-language words that have no MW entry."""
    if brk.kind == "url":
        return Finding(9, Verdict.NOT_APPLICABLE, "URLs are governed solely by Rule 8")

    syl = info.syllabification
    if syl.source in ("mw", "override"):
        return Finding(
            9, Verdict.NOT_APPLICABLE,
            "has a Merriam-Webster entry, so Rule 1 governs it",
        )

    has_diacritics = any(ch in DIACRITICS for ch in brk.word)
    if brk.italic:
        return Finding(
            9, Verdict.NEEDS_CHECK,
            "set in italic and not found in Merriam-Webster — check whether this is "
            "foreign-language text, which Rule 9 says to flag",
        )
    if has_diacritics:
        return Finding(
            9, Verdict.NEEDS_CHECK,
            "carries non-English diacritics and has no MW entry — flag per Rule 9",
        )
    if brk.left[:1].isupper():
        return Finding(9, Verdict.NOT_APPLICABLE, "proper noun — Rule 6 governs")

    # Rule 9 is about words *set as* foreign-language text.  A missing MW
    # entry on its own is Rule 1's finding, and repeating it here would just
    # double-count ordinary compounds and coinages as foreign words.
    return Finding(
        9, Verdict.NOT_APPLICABLE,
        "not set as foreign-language text (no italic, no diacritics)",
    )


ALL_RULES = (rule_1, rule_2, rule_3, rule_4, rule_5, rule_6, rule_7, rule_8, rule_9)


def evaluate(brk: Break, ctx: Context) -> Break:
    """Run every rule against *brk* and attach the findings."""
    if brk.kind == "furniture":
        brk.notes.append(
            f"the word continues on the next page, but the text after the break "
            f"(“{brk.right}”) reads as a running head or folio rather than the rest "
            f"of the word — check this page turn by eye"
        )
        brk.findings = [
            Finding(n, Verdict.NOT_APPLICABLE, "could not read the continuation of this word")
            for n in range(1, 10)
        ]
        return brk

    if brk.kind == "artifact":
        brk.notes.append(
            "extraction artifact: a soft hyphen fused onto an em dash — no word is divided here"
        )
        brk.findings = [
            Finding(n, Verdict.NOT_APPLICABLE, "no word is divided at this line ending")
            for n in range(1, 10)
        ]
        return brk

    info = analyze_break(brk, ctx)
    brk.findings = [rule(brk, ctx, info) for rule in ALL_RULES]
    if info.compound_state == AT_HYPHEN and brk.kind == "syllable":
        brk.kind = "compound"
    if info.syllabification.note:
        brk.notes.append(info.syllabification.note)
    return brk


def check_consistency(breaks: list[Break], ctx: Context) -> None:
    """Flag a word the book divides in more than one place.

    Both points can be legal and it is still an error in the proof: the same
    word should break the same way throughout.
    """
    by_word: dict[str, list[Break]] = defaultdict(list)
    for brk in breaks:
        if brk.kind in ("artifact", "url", "furniture"):
            continue
        by_word[brk.word.lower()].append(brk)

    for word, group in by_word.items():
        points = {b.break_index for b in group}
        if len(points) < 2:
            continue
        shown = sorted({b.display for b in group})
        pages = sorted({b.book_page or str(b.pdf_page) for b in group})
        in_mw = any(
            (b.finding_for(1) or Finding(1, Verdict.OK)).verdict is Verdict.OK
            and ctx.dictionary.lookup(strip_possessive(b.word)).source in ("mw", "override")
            for b in group
        )
        verdict = Verdict.ADVISORY if in_mw else Verdict.NEEDS_CHECK
        message = (
            f"“{word}” is divided {len(points)} different ways in this book "
            f"({', '.join(shown)}) on pages {', '.join(pages)} — make them consistent"
        )
        for brk in group:
            brk.findings.append(Finding(CONSISTENCY_RULE, verdict, message))


# --------------------------------------------------------------------------
# Rule 6, second half: breaks *between* words
# --------------------------------------------------------------------------

GENERATIONAL = ("Jr.", "Jr", "Sr.", "Sr", "II", "III", "IV", "V", "VI", "VII", "VIII", "IX", "X")


def check_line_breaks(pages, furniture) -> list[LineBreakFinding]:
    """Rule 6's initials, numerals and Jr./Sr. provisions.

    These are not hyphen breaks at all — they are places a line divides
    between two words — so they are collected separately and reported on
    their own tab.
    """
    from .extract import _content_lines  # local import: same package

    findings: list[LineBreakFinding] = []
    stream = []
    for page in pages:
        for line in _content_lines(page, furniture):
            stream.append((page, line))

    for position, (page, line) in enumerate(stream[:-1]):
        tokens = line.text.split()
        next_tokens = stream[position + 1][1].text.split()
        if not tokens or not next_tokens:
            continue
        last, first = tokens[-1], next_tokens[0]
        if last.endswith("-"):
            continue  # a hyphen break, handled by the rules above

        clean_first = first.strip("“”\"'(),;:")

        if is_initial(last) and is_initial(first):
            findings.append(LineBreakFinding(
                page.number, page.folio, line.index, last, first, Verdict.VIOLATION,
                "initials must not be split from one another — the whole group moves together",
            ))
            continue

        if clean_first in GENERATIONAL or (is_roman_numeral(clean_first) and len(clean_first) <= 5):
            if last[:1].isupper():
                findings.append(LineBreakFinding(
                    page.number, page.folio, line.index, last, first, Verdict.VIOLATION,
                    f"avoid a break between a name and “{clean_first}” — keep them on one line, "
                    f"or divide within the name instead",
                ))
                continue

        if clean_first.rstrip(".,").isdigit() and last[:1].isupper() and len(last) > 1:
            findings.append(LineBreakFinding(
                page.number, page.folio, line.index, last, first, Verdict.NEEDS_CHECK,
                f"a numeral opens the line after “{last}” — if it belongs to the name, "
                f"Rule 6 says not to break here",
            ))
            continue

        if is_initial(first) and last[:1].isupper() and not is_initial(last):
            findings.append(LineBreakFinding(
                page.number, page.folio, line.index, last, first, Verdict.ADVISORY,
                f"keep the middle initial with the first name where possible "
                f"(“{last} {first}/…”)",
            ))
    return findings
