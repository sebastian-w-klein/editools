# FSG Index Checker — feasibility assessment

Assessment of the 28 rules in the Index Checker wish list, against the same
delivery model as the Hyphenation Checker: runs locally, non-technical user
drops a file onto a web page, gets a file back.

**Verdict: yes, all of it is doable.** 27 of the 28 rules are deterministic
operations on text and character formatting. One rule (matching index terms
against the book's own text) is genuinely hard and belongs in a later phase.

> **Status.** Phase 1 is built: the tracked-changes layer, the entry parser and
> the four high-priority rules, validated against three published FSG indexes.
> See [RULES.md](RULES.md) for what it decides and why. The guidelines and
> sample indexes answered several of the open questions below; the answers are
> recorded in RULES.md rather than restated here.

---

## The one real architectural difference from the Hyphenation Checker

The Hyphenation Checker *reads* a PDF and *writes a report*. Nothing goes back
into the source file.

The Index Checker has to **edit the Word file in place and hand it back**, with
every edit recorded as a Track Changes revision. That is the only genuinely new
machinery, and it is the part most worth de-risking first — so it was.

This was spiked first and is now the `docxio` module, covered by
`tests/test_docxio.py`. It applies tracked insertions, tracked deletions,
tracked formatting changes (`w:rPrChange`) and highlights at exact character
ranges in a real `.docx`:

```
--- paragraph 1 ---
 before (reject all): Baltimore, Maryland,  30-20, 45n12, 82 and n, 128
 after  (accept all): Baltimore, Maryland, 30–20, 45n12, 82 and n, 128
 marked             : Baltimore, Maryland, [yellow]30–20[/], 45*n*12, 82 and n, 128
 tracked: 1 ins, 2 del, 1 fmt, 4 hl
```

Reject-all restores the original exactly; accept-all gives the corrected text.
That is the whole contract, and it holds.

### Three non-obvious constraints the spike surfaced

These were found by building it, not by reasoning about it, and they dictate
the shape of the code:

1. **Runs must be walked recursively, and deletion-aware.** Word text is split
   across `<w:r>` runs, and once an edit is made the runs move *inside*
   `<w:ins>` / `<w:del>` wrappers. Text inside `w:del` is no longer part of the
   current document text. A naive scan of direct children silently corrupts
   every offset after the first edit.

2. **Italic detection cannot just test for `<w:i>`.** Word writes an explicit
   `<w:i w:val="0"/>` to mean *not* italic. Testing for presence alone reports
   the entire paragraph as italic. This matters directly — four of the wish-list
   rules turn on whether something already is italic (duplicate page numbers,
   italic commas, roman commas between italic note numbers, non-italic "see").

3. **Edits must be applied in descending character offset**, and at the same
   offset a deletion must precede an insertion. Otherwise each edit invalidates
   the offsets of the ones after it. The spike does this with an edit queue that
   collects all findings first and applies them last — which is the right design
   regardless, because it also keeps the rules independent of one another.

---

## Rule-by-rule

### High priority — all four straightforward

| Rule | Notes |
|---|---|
| Main entries out of alphabetical order | Sort key implemented and tested, see below |
| Subentries out of order, ignoring initial prepositions/conjunctions | Same sort key + a stopword list |
| Page numbers out of numerical order | Needs the number parser (handles `45n12`, `82 and n`) |
| Page ranges out of order (`30–20`) | Trivial once ranges are parsed |

The `sortkey` module implements the letter-by-letter rule from the
guidelines — ignore spaces, hyphens, periods, quotes, and everything after an
open parenthesis, comma, or colon:

```
SORT KEY               ENTRY
adams                  Adams, John, 15
adamsmith              Adam-Smith, Jane, 9
chicago                Chicago (city), 40
postworldwariiera      post-World War II era, 88
```

**One consequence worth raising with your mom.** Because the rule discards
everything after a comma, `Adams, John` and `Adams, Abigail` produce the *same*
sort key. The checker therefore cannot tell that they are in the wrong order,
and will not flag them. That is faithful to the stated rule, and it errs toward
silence rather than false alarms — but if she expects given names to be checked,
that is a deliberate second-level tiebreak we should add on purpose.

### Lower priority — all sixteen doable

Straight pattern work: military titles, punctuation clusters (`,,` `,;` `;;` …),
`post-World`, spaced dashes, tabs, double spaces, entries with no term, page
numbers above the last page of text, elided ranges (`100–9` → `100–109`).

Four of them depend on reading existing character formatting, which constraint 2
above covers: duplicate page numbers unless the second is italic; italic commas
and semicolons; roman commas between italic note numbers; non-italic lowercase
"see".

Curly quotes and hyphen/em dash → en dash are context-sensitive but well-trodden.

### "If possible" — two of three are the easy kind of hard

**Syntax checking** (comma+space between page numbers, semicolon+space before a
subentry, no punctuation before a carriage return, `see also` preceded by
semicolon or open paren, `see` phrases with no page numbers) is best done by
writing a proper parser for the FSG index-entry grammar rather than as a pile of
regexes. That is more work up front and it pays for itself immediately: once an
entry is parsed into `term / subentries / page references`, most of the
high-priority rules fall out of the parse for free, and the syntax rules become
"the parser did not recognise this". The wish list's own note — that the
punctuation-cluster rule is a fallback "if the below rule about checking syntax
is too complicated" — is pointing at exactly this trade.

**Cross-checking `see also` targets** against the rest of the index is a lookup
over the parsed entries. Easy once the parser exists.

**Matching index terms against the book's text** is the genuinely hard one. It
needs a second input file (the typeset proof, as the Hyphenation Checker already
takes), a spell checker, fuzzy matching to find the near-miss in the book, and a
character-level diff to highlight only the letters and hyphens that differ. Every
part is doable and the Hyphenation Checker already does PDF extraction — but it
is the only rule whose output is a judgement call rather than a fact, so it will
need tuning against real books to avoid drowning the user in noise. Phase 3.

---

## Suggested phasing

1. ~~**Foundation + high priority.**~~ **Done.** The docx tracked-changes layer,
   the entry parser, the sort key, page-number parsing, the four high-priority
   rules.
2. **The lower-priority rules.** Mostly additive once the foundation is there;
   each is a small, independently testable rule, exactly like the
   Hyphenation Checker's nine.
3. **Syntax parsing + cross-references.**
4. **Book-text matching.**

---

## Open questions for your mom

1. **Should highlights themselves be tracked changes?** The wish list says all
   changes should be tracked. Strictly, a highlight is a formatting change and
   Word *can* track it — but then she has to accept or reject every flag, which
   is a lot of clicking for something whose only purpose is to catch her eye.
   Recommendation: real edits (dashes, quotes, italics, deletions) are tracked;
   highlights are plain formatting she deletes as she works through them.
2. **One highlight colour, or colour-coded by problem type** with a legend?
   Word offers a fixed palette; the spike shows two colours working.
3. **Would Word comments help?** A highlight says "something is wrong here"; a
   comment can say "page 10 is out of order" or "range 100–9 should be 100–109".
   This is very doable and would likely save her the most time of anything on
   the list. Worth asking whether she'd want it.
4. **Which rules should auto-fix versus only flag?** The wish list mixes both
   ("highlight X" vs "change X to Y"). Getting this split right per rule matters
   more than any individual rule.
5. **We need the FSG Indexing Guidelines**, pp. 1–3. The wish list cites them
   three times for details it does not restate — alphabetizing exceptions,
   the paragraph/run-in format, and elided page ranges.
6. **Last page of text** has to be entered by the user for the "page numbers too
   high" rule — a box on the drop page, same idea as the Merriam-Webster key
   field in the Hyphenation Checker.
7. **Sample indexes to test against.** Two or three real FSG indexes, ideally
   ones already copyedited so we can check the tool finds what a human found.
