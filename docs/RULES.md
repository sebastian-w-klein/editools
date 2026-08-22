# What the checker decides, and why

The four rules built so far are simple to state and fiddly to get right. This
records the judgement calls, because most of them were forced by real indexes
rather than by the guidelines.

Validated against three published FSG indexes — Gleick, *The Telephone*;
O'Hara, *The Flying Death*; Klein and Taylor, *End Times Fascism* — 2,778
entries in all. These are final files sent to the compositor, so almost
everything in them is right, which makes them a good test: nearly every flag
should be a real miss, and a checker that cries wolf on copyedited work is
useless.

**Current state: 10 fixes made, 14 errors and 13 ambiguous cases flagged,
across 2,778 entries.** Rejecting every change restores all three files
paragraph for paragraph, which is checked on each run.

---

## Alphabetising

### The primary key ignores all punctuation, not just the listed characters

§5 says to ignore "spaces, hyphens, periods, single and double quote marks".
Taken literally, `AT&T` folds to `at&t` and files *before* `Atlantic Monthly`,
because `&` sorts below `l`. The published index puts Atlantic Monthly first,
which is what you get by dropping the ampersand entirely: `att`. `E=mc²`
settles it the same way — it appears after `elocution`, which only works if the
`=` is dropped. So §5's list is illustrative and the rule is "ignore all
punctuation".

### A tiebreak on the given name

Because the key drops everything after a comma, `New, Arthur` and `New, James`
reduce to the same string. §5's own example nonetheless sorts Arthur before
James, so a second key compares the given name. Without it the checker cannot
see that `Miller, Glenn` before `Miller, George A.` is wrong — which it is, in
a published index.

### Only *abbreviated* personal titles are stripped

§7 says personal titles do not count, and requires them to be abbreviated.
Stripping spelled-out titles as well breaks real names: `Johnson, Lady Bird`
would file under "Bird" and sort before `Johnson, John B.` So a title is only
ignored when it is abbreviated — and never when it is a single initial, since
`A.` is an initial, not the article "a". That one mattered: without it,
`A. G. Bell's independence from` filed under "G".

### Letters with a stroke need their own mapping

`Ø` does not decompose under Unicode NFKD — the stroke is part of the glyph,
not a combining mark — so stripping non-letters turned `Ørsted` into `rsted`.
That sorted after every other entry and made the checker flag all 129 entries
that followed it. Letters like `ø ł đ æ œ ß þ` are mapped explicitly.

---

## Where there is no single right answer

Three of the alphabetising exceptions the wish list mentions genuinely have
more than one defensible reading. These are all *reported*, since the house
rule is the house rule — but a finding that only the house reading condemns is
marked **check** rather than **error**, and its comment says which other
reading would have saved it. Nothing is silently swallowed.

**Numerals.** An index files numerals as though spelled out, but `911` may be
read "nine one one" or "nine hundred eleven", and `1984` "nineteen
eighty-four". All the readings are offered. This is what lets `911/999` sit
among the n's, and `1956 consent decree for` sit after `nickname for`.

**Leading articles.** §8 moves an article to the end of a title of a work, but
a name keeps it: `"El Pastor"` files under Pastor, and `al-Aqsa Mosque` under
Aqsa. Both the term as written and the term without its article are offered,
including joined Arabic prefixes (`al-`, `el-`, `ad-`…).

**Initial prepositions in subentries.** The house rule — the one the wish list
states — is that they do not count, so that is what is reported against.
Counting them is a real convention too, so where that reading would put the
pair right, the finding says so and drops to **check**.

---

## Page numbers

### A year is not a page number

Three separate patterns put a four-digit year where a page number would go:
a bracketed qualifier (`market share of (1917), 223`), a year in the entry
name (`Nuclear Non-Proliferation Treaty, 1968, 322`), and one inside quotes
(`"Ucayali, 1871" curare, 37`). Bracketed spans are ignored outright;
references are parsed only from *after* the entry's term; and a leading
reference between 1000 and 2100 is dropped when every reference after it is
smaller, since a real page list starting at 1968 would carry on upwards.

### Equal page numbers are allowed

§11 puts the roman page before the italic one when the same page is indexed
for text and for an illustration — `New York City, 7, 34, 34, 53` — so the
check is that numbers never go *backwards*, not that they always increase.

### Note numbers stop where the italics stop

`304n1, 305nn1, 7` is note 1 on page 304, then notes 1 and 7 on page 305 — not
a single run of note numbers. Nothing in the text distinguishes the two
readings; what does is that §17 sets the note numbers in italic, so the list
runs exactly as far as the italics do.

### Elision follows §9 exactly

Two digits minimum (`22–23`, not `22–3`), no more than needed (`143–47`, not
`143–147`), and three in the x00–x09 band (`608–609`).

---

## Things worth deciding before the next batch of rules

1. **The wish list and §17 disagree about note numbers.** The wish list asks to
   italicise "n" and "nn" *"but not the number itself (e.g. 429nn)"*, while §17
   sets the number in italic too: `304n1`, `305nn1, 7`. The published indexes
   follow §17. Worth confirming which to implement before automating it.
2. **Sub-subentries and indented style.** All three sample indexes are in
   paragraph form with no indented subentries, so the parser assumes it. §12
   and §13 allow indented style, which would need separate handling if it ever
   turns up.
3. **The last page of the book** has to be entered by hand for the
   "page numbers too high" rule. It needs a box on the page.

---

## Phase two

Eighteen more rules. They split into two kinds, and the split matters more than
any individual rule: a **fix** is a tracked edit Word shows as a revision, and
is only used where the guidelines settle the question outright. Anything
needing judgement is **flagged** with a highlight and a comment instead.

| Fixed for you | Flagged for you |
|---|---|
| Elision corrected to §9 (`308–310` → `308–10`) | Page listed twice in one entry, unless the repeat is italic (§11) |
| Hyphens and em dashes between page numbers → en dash | Page reference past the last page of the book |
| Note markers and note numbers italicised (§17) | Roman comma between italic note numbers (§17) |
| `see` / `see also` lowercased and italicised (§15) | Doubled punctuation, and punctuation ending an entry |
| Straight quotes → curly | A dash with a space beside it |
| Tabs removed, runs of spaces collapsed | A comma or semicolon that should be roman, not italic (§3, §8) |
| | A personal title spelled out rather than abbreviated (§7) |
| | `ff.` or `passim`, which §9 forbids |
| | A paragraph that is page numbers with no entry term |
| | The hyphen in `post-World` |

### Where §17 and the wish list disagree

The wish list asks to italicise `n`/`nn` *"but not the number itself"*. §17 sets
the number in italic too — `304n1`, `305nn1, 7` — and all three published
indexes follow §17. The guidelines win: the marker and its note numbers are
italicised together, and the page number stays roman.

### What the real indexes forced

Four rules were wrong on first contact with a published index, in ways worth
recording because each looked right in isolation.

**The §9 three-digit exception applies only when both ends stay in the band.**
`608–609` takes three digits because 608 and 609 are both in the 600–609 band.
`108–10` takes two, because 110 has left it. All three indexes are consistent
about this, and reading §9's exception as "start is in the band" flagged 13
correct ranges in Gleick alone.

**A full stop before a comma is usually an abbreviation.** `Adam, A. O., 315`
and `Benjamin, Park, Jr., 176` are not doubled punctuation, and neither is an
entry ending `Merck and Co.` The wish list lists `.,` as a fault; in practice it
is one only when the full stop does not close an initial or an abbreviation.
Without that exception this rule alone produced 125 false positives.

**A rank word is only a title when it titles someone.** `General Electric` is a
company, `Major, Randolph` a surname, and `Major and, 114` a subentry about
him. §7 only bites where the rank sits in the given-name position after a
surname — `Sherman, Major General William Tecumseh`.

**A line of page numbers is not the same as a numeric entry.** `911/999, 4, 5`
is a real entry with no letters in its term. The rule fires only when the whole
paragraph is digits, commas, spaces and dashes.

### Overlapping edits

Two rules can land on the same characters — an elision fix and a dash fix
inside one range. Applying both would corrupt the text, so the first edit wins
and the second is dropped; flags are unaffected, since they only add a
highlight.

---

## Phase three: cross-references and syntax

### Where a cross-reference points

§15 makes cross-references the last "subentry", separated by semicolons, which
means a `see` has a different reach depending on where it sits:

* a trailing run continues across semicolons to the end of the paragraph —
  `art, 290; see also films; literature` names two entries;
* a `see` inside a subentry stops at that subentry's semicolon —
  `engineering department of, see Bell Labs; etiquette encouraged by, 137`
  names one entry, not two;
* a bracketed `(see also …)` is scoped to its brackets.

Getting this wrong in either direction is silent: too greedy and half the
index becomes a cross-reference target, too narrow and most references go
unchecked.

Every target is then looked up among the entries. Four things had to be
allowed for before this stopped crying wolf on published work, and each is a
real convention rather than a special case:

* **A reference may name an entry in short.** `see Western Electric` points at
  `Western Electric Manufacturing Company`, and `see also long-distance` at
  `long-distance telephony`. Entries are registered under every word-boundary
  prefix of their name.
* **A slash joins two names for one entry.** `British Empire/United Kingdom`
  answers to either half.
* **`see under radio` means the entry `radio`.**
* **An italic target is a whole category, not an entry.** §15 puts it last and
  in italic — `see also individual neighborhoods` — and by design no such entry
  exists, so italic targets are skipped.

### Syntax

The six sub-rules are checked by measuring the *gaps* between the parts the
parser has already identified: a comma and a space between page numbers and
before them, a semicolon and a space before a subentry, a semicolon or open
bracket before `see also`, and no page numbers on an entry that is only a
cross-reference.

One allowance is needed: §15 lets a bracketed cross-reference sit in the gap
before a subentry — `171–72 (see also Bell System); area codes created by` —
so the punctuation is judged with any bracketed aside taken out. Without that,
every parenthetical cross-reference in Gleick was flagged.

This rule turns out to diagnose better than the ordering rules do. The missing
semicolon in Gleick's `Communications Act of, 402 Centennial Exhibition and,
85` shows up here as what it actually is, where the page-order rule could only
report that 85 came after 402. It also found `294,341` — a comma with no space
after it, which nothing else was looking for.

### The one it cannot tell apart

`Models 102, 300, and 302, 309–10` is flagged as a bad gap between page
numbers. The model numbers in the entry's own name are indistinguishable from
page references, so the checker reads `, and ` as punctuation between two page
numbers. One instance in 2,778 entries, and it is arguably worth an eye
anyway; worth knowing about rather than worth suppressing.
