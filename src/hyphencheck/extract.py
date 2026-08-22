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
    chars: list = field(default_factory=list, repr=False)


@dataclass
class Page:
    number: int          # physical, 1-based
    folio: str           # printed page number as it appears on the page
    lines: list[Line]


@dataclass
class Document:
    pages: list[Page]
    breaks: list[Break]
    tokens: Counter      # every whole-word token in the book, for compound checks
    running_heads: set[str]

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
                lines.append(Line(page_number, index, text, raw.get("chars", [])))
            pages.append(Page(page_number, "", lines))
    return pages


def find_running_heads(pages: list[Page], threshold: float = 0.15) -> set[str]:
    """Text that repeats at the top or bottom of many pages is furniture."""
    counts: Counter[str] = Counter()
    for page in pages:
        edge_lines = page.lines[:1] + page.lines[-1:]
        for line in edge_lines:
            key = _normalize(line.text)
            if key:
                counts[key] += 1
    minimum = max(3, int(len(pages) * threshold))
    return {text for text, count in counts.items() if count >= minimum}


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


def _content_lines(page: Page, running_heads: set[str]) -> list[Line]:
    keep = []
    for line in page.lines:
        if _normalize(line.text) in running_heads:
            continue
        if FOLIO.match(line.text):
            continue
        keep.append(line)
    return keep


def find_breaks(pages: list[Page], running_heads: set[str]) -> list[Break]:
    """Locate every line that ends in a word-division hyphen."""
    breaks: list[Break] = []
    # Flatten to a single stream so a break on the last line of a page is
    # joined to the first line of the next page.
    stream: list[tuple[Page, Line]] = []
    for page in pages:
        for line in _content_lines(page, running_heads):
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
        if ends_with_em_dash(stripped) or not left or not right:
            kind = "artifact"
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
            )
        )
    return breaks


TOKEN = re.compile(r"[A-Za-zÀ-ɏ][A-Za-zÀ-ɏ'’-]*")


def index_tokens(pages: list[Page], running_heads: set[str]) -> Counter:
    """Count every whole word in the book.

    Used to settle whether ``cross-/legged`` rejoins as ``cross-legged`` or
    ``crosslegged``: if the hyphenated form is set intact elsewhere in the
    same book, that is the answer.
    """
    counts: Counter[str] = Counter()
    for page in pages:
        for line in _content_lines(page, running_heads):
            for token in TOKEN.findall(line.text):
                counts[token.lower()] += 1
    return counts


def load(pdf_path: str, artifacts: list[str] | None = None) -> Document:
    """Read *pdf_path* and return everything the rule engine needs."""
    pages = read_pages(pdf_path, artifacts)
    running_heads = find_running_heads(pages)
    assign_folios(pages, running_heads)
    breaks = find_breaks(pages, running_heads)
    tokens = index_tokens(pages, running_heads)
    return Document(pages=pages, breaks=breaks, tokens=tokens, running_heads=running_heads)
