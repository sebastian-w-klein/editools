"""Turn a typeset proof PDF into the list of end-of-line hyphen breaks.

The job here is only detection — deciding whether a break is *allowed* is the
rule engine's problem.  What this module has to get right is:

* which physical line ends in a word-division hyphen (and not an em dash),
* which printed page number that line sits on,
* what characters sit tight against the word on either side (for Rule 4),
* whether the word is set in italic (for Rule 9).
"""

from __future__ import annotations

import re
from collections import Counter
from dataclasses import dataclass, field
from statistics import median

import pdfplumber

from .model import Break
from .textutil import (
    HYPHENS,
    ends_with_em_dash,
    leading_em_dash,
    looks_like_url,
    split_leading_word,
    split_trailing_word,
    trailing_em_dash,
)

#: Junk that InDesign proofs leave in the extracted text stream.  These are
#: stripped from the end of every line before any hyphen test, because a fused
#: footer marker can otherwise hide (or invent) a line-ending hyphen.
DEFAULT_ARTIFACTS = [
    r"\s*[-+]?\d+[—–]\s*$",       # baseline/folio markers such as "-1—" or "0—"
    r"\s*\.indd\s+\d+\s*$",       # ".indd 204"
    r"\s*\d+/\d+/\d+\s+\d+:\d+\s*(?:AM|PM)?\s*$",  # export timestamps
]

#: The slug InDesign stamps across the foot of an exported proof — the
#: ``.indd`` file name, the spread number, and the export date and time:
#:
#:     042-154238_ch01_1P.indd 29                08/07/26 7:27 PM
#:
#: It sits below the folio on nearly every page and is no part of the typeset
#: book.  A literal file name is about as certain a mark of furniture as there
#: is, which matters because this line is *long* — it runs most of the measure
#: — and so escapes the geometry and position signals, both of which look for
#: a short line in the margin.
EXPORT_FOOTER = re.compile(
    r"^[\w.\-:/\\ ]*?\.ind+\b"                   # 042-154238_ch01_1P.indd
    r"(?:\s+\d+)?"                                # the spread number
    r"(?:\s+\d{1,2}/\d{1,2}/\d{2,4})?"            # 08/07/26
    r"(?:\s+\d{1,2}:\d{2}(?:\s*[AP]\.?M\.?)?)?"   # 7:27 PM
    r"\s*$",
    re.IGNORECASE,
)

#: The other half of the slug, when extraction breaks it into two lines: a
#: line that is nothing but the export date and time.  The artifact patterns
#: above already strip this from the end of any line — it only survives on its
#: own when the doubling puts it beyond their reach.
EXPORT_TIMESTAMP = re.compile(
    r"^\d{1,2}/\d{1,2}/\d{2,4}"
    r"(?:\s+\d{1,2}:\d{2}(?:\s*[AP]\.?M\.?)?)?\s*$",
    re.IGNORECASE,
)

DOUBLED = re.compile(r"(.)\1+")


def _squeeze(text: str) -> str:
    """Collapse every run of a repeated character to one.

    Some pages of a proof decode the footer with each glyph doubled —
    ``004422--115544223388__cchh0011__11PP..iinnddd`` for the same text that
    reads cleanly elsewhere in the file — so the pattern above cannot see it.
    Squeezing hands it back a readable ``042-154238_ch01_1P.ind``.  It is
    lossy (real double letters go too), which is why it is only ever used to
    *recognise* a line, never to rewrite one.
    """
    return DOUBLED.sub(r"\1", text)


def is_export_footer(text: str) -> bool:
    """True if *text* is an InDesign export slug rather than a line of the book."""
    text = text.strip()
    if not text:
        return False
    return any(
        pattern.match(form)
        for pattern in (EXPORT_FOOTER, EXPORT_TIMESTAMP)
        for form in (text, _squeeze(text))
    )


FOLIO = re.compile(r"^\s*(\d{1,4}|[ivxlcdm]{1,8}|[IVXLCDM]{1,8})\s*$")

ITALIC_FONT = re.compile(r"italic|oblique|-it\b|it$", re.IGNORECASE)

#: Word gap as a fraction of font size. A space in most book faces is about a
#: quarter of the point size, so anything wider than this is a real space.
WORD_GAP_RATIO = 0.12


@dataclass
class Line:
    pdf_page: int
    index: int
    text: str
    top: float = 0.0
    bottom: float = 0.0
    chars: list = field(default_factory=list, repr=False)
    #: The line as extracted, before the artifact patterns trimmed it.  A
    #: footer is recognised by its file name and timestamp, and stripping
    #: those is exactly what takes the evidence away.
    raw: str = ""


@dataclass
class Page:
    number: int          # physical, 1-based
    folio: str           # printed page number as it appears on the page
    lines: list[Line]
    height: float = 0.0


@dataclass
class Document:
    pages: list[Page]
    breaks: list[Break]
    tokens: Counter      # every whole-word token in the book, for compound checks
    furniture: "Furniture"

    @property
    def running_heads(self) -> set[str]:
        return self.furniture.running_heads

    def token_appears(self, text: str) -> int:
        """How many times *text* appears in the book as a complete token."""
        return self.tokens.get(text.lower(), 0)


def _normalize(text: str) -> str:
    """Collapse a line to a form suitable for running-head detection."""
    return re.sub(r"[\d\s]+", " ", text).strip().lower()


def _strip_artifacts(text: str, patterns: list[re.Pattern]) -> str:
    previous = None
    while previous != text:
        previous = text
        for pattern in patterns:
            text = pattern.sub("", text)
    return text.rstrip()


def _is_italic(chars: list, count: int) -> bool:
    """True if the last *count* characters are predominantly italic."""
    if not chars:
        return False
    tail = chars[-count:] if count and count <= len(chars) else chars
    italic = sum(1 for c in tail if ITALIC_FONT.search(str(c.get("fontname", ""))))
    return italic > len(tail) / 2


def _extract_lines(page) -> list[dict]:
    """Pull a page's lines, sizing the word gap to the type rather than fixing it.

    pdfplumber's default 3pt word gap is wider than a space in book-sized
    type, which silently runs whole lines together into one token — and a
    hyphen audit that cannot see word boundaries is worthless.  Scaling the
    tolerance to the actual font size keeps the words apart at any size.
    """
    for kwargs in (
        {"x_tolerance_ratio": WORD_GAP_RATIO, "y_tolerance": 3},
        {"x_tolerance": 1.2},
        {},
    ):
        try:
            lines = page.extract_text_lines(strip=True, return_chars=True, **kwargs)
        except (TypeError, ValueError):
            continue
        except Exception:
            return []
        if lines:
            return lines
    return []


def read_pages(pdf_path: str, artifacts: list[str] | None = None) -> list[Page]:
    """Extract every page of *pdf_path* as cleaned, ordered lines."""
    patterns = [re.compile(p) for p in (artifacts if artifacts is not None else DEFAULT_ARTIFACTS)]
    pages: list[Page] = []
    with pdfplumber.open(pdf_path) as pdf:
        for page_number, page in enumerate(pdf.pages, start=1):
            raw_lines = _extract_lines(page)
            lines: list[Line] = []
            for index, raw in enumerate(raw_lines):
                text = _strip_artifacts(raw.get("text", ""), patterns)
                if not text.strip():
                    continue
                lines.append(Line(
                    pdf_page=page_number,
                    index=index,
                    text=text,
                    raw=raw.get("text", ""),
                    top=float(raw.get("top", 0.0) or 0.0),
                    bottom=float(raw.get("bottom", 0.0) or 0.0),
                    chars=raw.get("chars", []),
                ))
            pages.append(Page(page_number, "", lines, float(page.height or 0.0)))
    return pages


#: A margin gap this many times the line leading marks the end of the text block.
MARGIN_GAP = 1.8

#: Furniture is short; body lines run most of the measure.
SHORT_LINE = 0.6

#: How many furniture lines may sit at each end of a page (head + folio, say).
MAX_FURNITURE_PER_EDGE = 2


@dataclass
class Furniture:
    """The lines on each page that are not body text.

    Running heads, folios, export slugs and proof markers have to be
    identified before any break can be read, because a word divided across a
    page boundary continues on the *next page's first body line* — and if a
    running head is mistaken for that line, the two halves get joined into a
    word nobody set.
    """

    by_page: dict[int, set[int]] = field(default_factory=dict)
    running_heads: set[str] = field(default_factory=set)

    def marks(self, page_number: int) -> set[int]:
        return self.by_page.get(page_number, set())


def _typical_leading(pages: list[Page]) -> float:
    """The usual baseline-to-baseline distance in the body text.

    The *most common* gap rather than the median: a page's margins contribute
    a couple of very large gaps each, which drag a median upward far enough to
    stop the margins being recognised as margins.
    """
    gaps: Counter[int] = Counter()
    for page in pages:
        tops = [line.top for line in page.lines]
        for a, b in zip(tops, tops[1:]):
            if b > a:
                gaps[round(b - a)] += 1
    if not gaps:
        return 0.0
    most = max(gaps.values())
    return float(min(gap for gap, count in gaps.items() if count == most))


def _typical_measure(pages: list[Page]) -> float:
    """The usual length of a body line, in characters."""
    lengths = [len(line.text) for page in pages for line in page.lines]
    return median(lengths) if lengths else 0.0


def _geometric_furniture(lines: list[Line], leading: float, measure: float) -> set[int]:
    """Peel short, set-apart lines off the top and bottom of one page.

    A running head or folio sits in the margin, separated from the text block
    by much more than a line's leading. That is true whatever the head happens
    to say, so it catches per-chapter running heads and one-off proof marks
    that no amount of counting repeated text would find.
    """
    marks: set[int] = set()
    if len(lines) < 4 or leading <= 0:
        return marks
    threshold = leading * MARGIN_GAP
    short = measure * SHORT_LINE

    top = 0
    for _ in range(MAX_FURNITURE_PER_EDGE):
        if top + 1 >= len(lines):
            break
        if lines[top + 1].top - lines[top].top > threshold and len(lines[top].text) <= short:
            marks.add(top)
            top += 1
        else:
            break

    bottom = len(lines) - 1
    for _ in range(MAX_FURNITURE_PER_EDGE):
        if bottom - 1 <= top:
            break
        if lines[bottom].top - lines[bottom - 1].top > threshold and len(lines[bottom].text) <= short:
            marks.add(bottom)
            bottom -= 1
        else:
            break
    return marks


#: Only the outer bands of a page can hold furniture.
TOP_MARGIN = 0.15
BOTTOM_MARGIN = 0.80


def _positional_furniture(pages: list[Page], measure: float) -> dict[int, set[int]]:
    """Short lines that sit at the same height in the margin on many pages.

    A running head and a folio hold their position from page to page, which
    identifies them no matter what they say — the signal that survives when a
    head names the chapter and so never repeats often enough to be counted.
    Only the top and bottom bands of the page are considered, so a short line
    of body text cannot be caught by this.
    """
    short = measure * SHORT_LINE
    bands: Counter[int] = Counter()
    for page in pages:
        if not page.height:
            continue
        seen: set[int] = set()
        for line in page.lines:
            in_margin = (line.top < page.height * TOP_MARGIN
                         or line.top > page.height * BOTTOM_MARGIN)
            if in_margin and len(line.text) <= short:
                band = round(line.top / 3)
                if band not in seen:
                    seen.add(band)
                    bands[band] += 1

    minimum = max(3, len(pages) * 0.3)
    furniture_bands = {band for band, count in bands.items() if count >= minimum}

    marks: dict[int, set[int]] = {}
    for page in pages:
        found = set()
        if page.height:
            for index, line in enumerate(page.lines):
                if round(line.top / 3) in furniture_bands and len(line.text) <= short:
                    found.add(index)
        marks[page.number] = found
    return marks


def find_running_heads(pages: list[Page], minimum: int = 3) -> set[str]:
    """Short text repeating at the top or bottom edge of several pages.

    A second opinion alongside the geometry, for proofs whose margins are not
    cleanly separated. Only edge lines are considered and only short ones, so
    a repeated line of dialogue is not mistaken for a running head.
    """
    counts: Counter[str] = Counter()
    for page in pages:
        for line in page.lines[:1] + page.lines[-1:]:
            key = _normalize(line.text)
            if key and len(line.text) <= 60:
                counts[key] += 1
    return {text for text, count in counts.items() if count >= minimum}


def find_furniture(pages: list[Page]) -> Furniture:
    """Everything on each page that is not body text."""
    leading = _typical_leading(pages)
    measure = _typical_measure(pages)
    running_heads = find_running_heads(pages)

    positional = _positional_furniture(pages, measure)

    by_page: dict[int, set[int]] = {}
    for page in pages:
        marks = _geometric_furniture(page.lines, leading, measure)
        marks |= positional.get(page.number, set())
        for index, line in enumerate(page.lines):
            if (FOLIO.match(line.text)
                    or _normalize(line.text) in running_heads
                    or is_export_footer(line.raw or line.text)):
                marks.add(index)
        by_page[page.number] = marks
    return Furniture(by_page=by_page, running_heads=running_heads)


def assign_folios(pages: list[Page], running_heads: set[str]) -> None:
    """Record each page's printed page number, read off the page itself.

    Falling back to the physical PDF index would be wrong for any book with
    front matter, and the folio is what the proofreader actually needs in
    order to find a flagged line in the proof.
    """
    for page in pages:
        folio = ""
        candidates = page.lines[:2] + page.lines[-2:]
        for line in candidates:
            match = FOLIO.match(line.text)
            if match:
                folio = match.group(1)
                break
        if not folio:
            # Some designs set the folio tight against the running head.
            for line in candidates:
                if _normalize(line.text) in running_heads:
                    numbers = re.findall(r"\b\d{1,4}\b", line.text)
                    if numbers:
                        folio = numbers[0]
                        break
        page.folio = folio


def _content_lines(page: Page, furniture: "Furniture") -> list[Line]:
    """Just the body text of one page, in reading order."""
    marks = furniture.marks(page.number)
    return [line for index, line in enumerate(page.lines) if index not in marks]


#: A continuation fragment that looks like this is not the rest of a word.
def _looks_like_furniture(fragment: str) -> bool:
    if any(ch.isdigit() for ch in fragment):
        return True
    letters = [ch for ch in fragment if ch.isalpha()]
    return len(letters) > 1 and all(ch.isupper() for ch in letters)


def find_breaks(pages: list[Page], furniture: "Furniture") -> list[Break]:
    """Locate every line that ends in a word-division hyphen."""
    breaks: list[Break] = []
    # Flatten to a single stream so a break on the last line of a page is
    # joined to the first line of the next page.
    stream: list[tuple[Page, Line]] = []
    for page in pages:
        for line in _content_lines(page, furniture):
            stream.append((page, line))

    for position, (page, line) in enumerate(stream[:-1]):
        text = line.text.rstrip()
        if not text or text[-1] not in HYPHENS:
            continue

        tail_token = text.split()[-1]
        stripped = tail_token[:-1]
        if not stripped:
            continue  # a hyphen standing alone is not a word division

        next_page, next_line = stream[position + 1]
        next_text = next_line.text.lstrip()
        if not next_text:
            continue
        next_token = next_text.split()[0]

        prefix, left, _ = split_trailing_word(stripped)
        suffix_prefix, right, suffix = split_leading_word(next_token)

        # An em dash immediately before the trailing hyphen means the extractor
        # merged a soft hyphen onto a dash: no word is actually divided here.
        crosses_page = next_page.number != page.number

        if ends_with_em_dash(stripped) or not left or not right:
            kind = "artifact"
        elif crosses_page and _looks_like_furniture(right):
            # The word continues on the next page, but what follows is a
            # running head or folio rather than the rest of the word. Better to
            # say so than to invent a word and report it as a violation.
            kind = "furniture"
        elif (
            looks_like_url(stripped)
            or looks_like_url(stripped + next_token)   # "example." + "com"
            or looks_like_url(tail_token + next_token)
        ):
            kind = "url"
        else:
            kind = "syllable"

        if kind == "url":
            # For a URL keep the raw tokens; the pieces are not "words".
            left, right = stripped, next_token
            prefix = suffix = suffix_prefix = ""

        breaks.append(
            Break(
                pdf_page=page.number,
                book_page=page.folio,
                line_index=line.index,
                left=left,
                right=right,
                hyphen_char=text[-1],
                line_text=line.text,
                next_line_text=next_line.text,
                char_before=prefix,
                char_after=(suffix_prefix + suffix)[:8],
                trailing_punct=suffix,
                italic=_is_italic(line.chars, len(left) + 1),
                kind=kind,
                crosses_page=crosses_page,
            )
        )
    return breaks


TOKEN = re.compile(r"[A-Za-zÀ-ɏ][A-Za-zÀ-ɏ'’-]*")


def index_tokens(pages: list[Page], furniture: "Furniture") -> Counter:
    """Count every whole word in the book.

    Used to settle whether ``cross-/legged`` rejoins as ``cross-legged`` or
    ``crosslegged``: if the hyphenated form is set intact elsewhere in the
    same book, that is the answer.
    """
    counts: Counter[str] = Counter()
    for page in pages:
        for line in _content_lines(page, furniture):
            for token in TOKEN.findall(line.text):
                counts[token.lower()] += 1
    return counts


def load(pdf_path: str, artifacts: list[str] | None = None) -> Document:
    """Read *pdf_path* and return everything the rule engine needs."""
    pages = read_pages(pdf_path, artifacts)
    furniture = find_furniture(pages)
    assign_folios(pages, furniture.running_heads)
    breaks = find_breaks(pages, furniture)
    tokens = index_tokens(pages, furniture)
    return Document(pages=pages, breaks=breaks, tokens=tokens, furniture=furniture)
