# Hyphenation Checker

Finds bad end-of-line hyphen breaks in a typeset proof and writes a spreadsheet
of what to fix, with page numbers.

Every hyphenated word at the end of a line is checked against **all nine rules**
of the house ruleset, not just the first one that seems relevant. Rule 1 is
checked against Merriam-Webster's own syllable dots, fetched from MW's
dictionary API and cached on disk.

```
$ hyphencheck audit Swans_INT_1P.pdf

Reading the PDF…
224 pages, 431 end-of-line hyphens found.
Looking up 263 distinct words in Merriam-Webster…
Applying all nine rules to every break…

Swans_INT_1P_hyphenation_audit.xlsx
13 violation(s), 10 needing a look, 4 advisory, across 361 word divisions on 224 pages.
  p.16    cross-/legged            Rule 4
  p.88    co-/meth                 Rule 1
  p.119   Eng-/lish                Rule 1
  p.124   butch-/er's              Rule 3
  p.204   fold-/up                 Rule 2
  p.205   cher-/ries               Rule 4
```

## Why this exists

This replaces a manual pass that ran into three problems, all of which are
structural rather than a matter of trying harder:

| Problem | What the tool does |
|---|---|
| Checking a word against Rule 1, finding it fine, and stopping — so `butch-/er's` (Rule 3) and `cher-/ries—or` (Rule 4) slipped through | Every rule is applied to every break, independently. The spreadsheet has a column per rule so you can see it happened. |
| One Merriam-Webster lookup per word, by hand, over hundreds of words | One API request per *distinct* word, run in parallel, cached on disk forever. The second book only pays for words the first did not contain. |
| Different answers on different passes | The same PDF gives the same spreadsheet every time. |

Rules 2, 3, 4, 5 and 8 need no dictionary at all — they are letter counts and
character adjacency, and they are where most real violations turn up.

## Installing

```bash
git clone <this repo>
cd hyphenchecker
python3 -m venv .venv
.venv/bin/pip install -e .
```

Then add a Merriam-Webster key (free, one time — **[SETUP.md](SETUP.md)** walks
through it with no assumed knowledge):

```bash
.venv/bin/hyphencheck setup
```

On a Mac you can skip all of that and double-click **`run-checker.command`**;
on Windows, **`run-checker.bat`**. Either one sets everything up on first run
and opens the drag-and-drop window.

## Using it

**Drag and drop.** `hyphencheck ui` opens a page in your browser. Drop a PDF on
it, wait, download the spreadsheet. Nothing leaves your computer except the
word lookups.

**Command line.**

```bash
hyphencheck audit BOOK.pdf                  # writes BOOK_hyphenation_audit.xlsx
hyphencheck audit BOOK.pdf -o audit.xlsx    # or name it yourself
hyphencheck word cemetery photographer      # where does MW divide this word?
hyphencheck audit BOOK.pdf --offline        # no dictionary; Rules 2-5, 8 still apply
```

## The spreadsheet

| Tab | What is on it |
|---|---|
| **Summary** | Totals, how many breaks each rule flagged, and every flagged item by page |
| **Flagged Items** | Only what needs your attention, sorted by page |
| **All Instances** | Every end-of-line hyphen in the book, with each rule's verdict in columns R1–R9 |
| **Line Breaks (Rule 6)** | Breaks *between* words: split initials, `Elizabeth / II`, `Sammy Davis / Jr.` |
| **Rule Key** | What each column means |

Verdicts are **VIOLATION** (a rule is broken), **NEEDS CHECK** (the tool will not
guess — usually an invented name or a word MW does not carry), **ADVISORY** (the
break is legal but Rule 7 prefers another point, or the book divides the same
word two different ways), and **OK**.

## Words the dictionary cannot settle

Invented names and house-style decisions go in an overrides file, and they
outrank the dictionary. Copy `overrides.example.json` to
`~/.hyphencheck/overrides.json`:

```json
{
  "Marvolene": "Mar·vo·lene",
  "rulepig": "nobreak"
}
```

A word marked `nobreak` may not be divided at all; anything else is read as the
dotted form. Decisions recorded here carry over to the next book.

## What it will not do

It flags; you decide. Specifically:

- **A word Merriam-Webster does not carry gets flagged, not guessed at.** That
  is Rule 6.4's instruction, and it is why invented names come back as NEEDS
  CHECK rather than a confident answer.
- **Proper-noun coverage depends on MW's Collegiate API**, which carries fewer
  biographical and geographical names than the website. Names it does not have
  fall through to Rule 6's morpheme and vowel tests, and are flagged when
  neither settles it.
- **Rule 9 needs the italics to survive extraction.** Foreign-language setting
  is detected from the PDF's font names; if a proof is generated without them,
  foreign words are caught only by their absence from MW.
- **Rule 7 is advisory**, never a violation — it expresses a preference among
  break points Merriam-Webster already allows.
- **Rejoining a compound can be genuinely ambiguous** (`re-cover` / `recover`).
  Where both readings are real words and the book uses both, the row is marked
  NEEDS CHECK rather than decided.

## Running the tests

```bash
.venv/bin/pip install -e ".[dev]"
.venv/bin/python -m pytest
```

The tests build a small proof PDF containing every case in the ruleset —
including the four misses that prompted the "check every rule" instruction —
and run the whole pipeline over it. Merriam-Webster's API is not called from
the test run; the dictionary is primed with recorded responses in the real API's
shape, so the parsing path is exercised rather than stubbed.

## How it works

```
PDF ──▶ extract ──▶ break detection ──▶ dictionary ──▶ nine rules ──▶ .xlsx
        lines,      line-ending          MW API +      each applied   Summary
        folios,     hyphens, em-dash     disk cache    independently  Flagged
        italics     adjacency, URLs      + overrides   to every break All / Rules
```

| File | Responsibility |
|---|---|
| `extract.py` | PDF to lines; printed page numbers, running heads, italics, break detection |
| `dictionary.py` | Merriam-Webster lookups, the on-disk cache, overrides, TeX fallback |
| `rules.py` | The nine rules, plus consistency and the between-words checks |
| `audit.py` | Runs a whole proof: extract, prefetch, evaluate |
| `report.py` | The spreadsheet |
| `webui.py` | The local drag-and-drop window |
