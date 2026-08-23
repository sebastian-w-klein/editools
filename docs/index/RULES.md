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

A fourth index — Leeds, *It's Got to Be Funky*, 1,098 entries — was added
later, and every alphabetising rule below the first heading was forced by it.
It now reports **9 errors and 1 query**, all ten confirmed by hand; the build
before it reported 29, of which 21 were the checker's fault and one — the
misfiled `R&B` — it had fitted a rule around rather than caught.

---

## Alphabetising

### The key is a sequence of segments, not one string

Alphabetising runs up to the first parenthesis or comma and starts again after
it, so where two entries open with the same word it is what *follows* that word
that decides the order:

| | |
|---|---|
| the word on its own | `London` |
| the word, then a parenthesis | `London (England)` |
| the word, then a comma | `London, Jack` |
| the word, then a number | `London 1900` |
| the word, then more letters | `Londonderry` |

A key is therefore alternating segments and separators —
`("london", COMMA, "jack", END)` — with `END` ranking below both punctuation
marks, which is what puts the bare word first. The last two tiers need no rank:
with spaces ignored the digits and letters simply continue the segment, and a
digit already sorts below a letter.

Before this, everything after the first parenthesis or comma was thrown away
except a single tiebreak string. `London` and `London (England)` reduced to the
same key, so `London (Ontario)` filed before `London (England)` without
complaint, and a bare `London` could sit anywhere among the `London,` entries.

### A bracketed date is a qualifier, not a page reference

The term ends at the first comma-separated piece that reads as page references.
Applying that test inside brackets too was wrong: `Smith, John (1820–1880)` and
`Smith, John (1900–1970)` both lost their dates and collapsed onto one key.
Page references are never bracketed in this style, so only a comma piece is
tested.

### The comma inside a closing quote is the separator

House style tucks the comma that divides a term from its page references
inside the quotation mark: `“Purple Rain,” 148`. Masking quoted spans — which
is what stops `“Ucayali, 1871” curare` losing its year — hid that comma too,
so the term read `“Purple Rain,” 148` and folded to `purplerain148`, filing
after every other Purple Rain entry and flagging three correct ones. The comma
*immediately* before a closing quote is exposed again; one in the middle of a
quoted phrase stays masked. The syntax rule then expects only a space in the
gap, since the term already carries its comma.

### A bracket with nothing in front of it is not a qualifier

`“(I Wanna) Testify”` and `(Music from) The Elder` open with a parenthesis, so
cutting the term there left an empty first segment that sorted before every
entry in the index. There is nothing for such a bracket to qualify: it is part
of the title, and the term files under `iwannatestify`.

### One misfiling should not flag the whole run after it

An entry filed too early sits above everything that legitimately follows, and
blaming the followers turns one misfiling into a wall. `“(I Wanna) Testify”`,
landing among the "I Got" entries, drew fourteen flags against entries that
were all correctly placed. When the entry after next fits where the intruder
sits, the intruder is reported instead and the run carries on from the
follower.

### A cross-reference is not part of the name

A dummy entry may be written `hoe. See garden hoe`, with a full stop rather than
the comma the term parser looked for. The whole clause then folded into the key
and the entry filed under `hoeseegardenhoe`, past every real h. A full stop
introduces a cross-reference as readily as a comma does.

### Two entries that alphabetise the same are reported

When a person, a place and a thing share a name they file in normal
alphabetical order — but if their keys are *identical*, sorting cannot say
which comes first and the guidelines' remedy is to tell them apart by hand,
`London (England)` against `London, Amy`. The pair is flagged as **check**,
since it needs an editor's eye rather than a rule.

### The primary key ignores all punctuation, not just the listed characters

§5 says to ignore "spaces, hyphens, periods, single and double quote marks".
Taken literally, `E=mc²` folds to `e=mc2` and files before `elocution`, because
`=` sorts below any letter. The published index puts it *after* elocution,
which only works if the `=` is dropped. So §5's list is illustrative and the
rule is "ignore all punctuation".

### A symbol that stands for a word is read aloud

Folding `&` away with the rest of the punctuation put `A&E` under `ae`, between
Adore and AEG, and reported seven correct entries as misfiled. A symbol is a
word, not a punctuation mark, and an index files it as it is read: `A&E` goes
under `a and e`, before Abramovic.

`R&B` is what settles *how* to read it, and it took the editor to settle it,
because the index itself is wrong there. Leeds files `R&B` at the head of the
R's, before `race relations`. Nothing legitimate puts it there — read aloud it
is `randb` and folded away it is `rb`, and both follow `race` — so it looked
like evidence for a third rule, that a symbol ends its segment the way a
parenthesis does, giving `("r", …)`. That reading fits all three of the index's
symbol entries, which is exactly why it is a trap: it fits by reproducing the
mistake. The house rule is `R&D` after `radio`, so the symbol is read aloud and
the entry is misfiled. It is now reported.

| | folded away | ends the segment | **read aloud** |
|---|---|---|---|
| `A&E` before `Abramovic` | ✗ | ✓ | ✓ |
| `Red Hot + Riot` before `Red Hot Organization` | ✗ | ✓ | ✓ |
| `radio stations` before `R&B` (subentry) | ✓ | ✗ | ✓ |
| `R&B` before `race relations` | ✗ | ✓ | ✗ — and it should be |

A symbol that reads more than one way offers both, as a numeral does: `+` is
"and" or "plus", and `Red Hot + Riot` is right under either. The reading
applies to a whole key rather than one segment, since an index reads its
symbols aloud everywhere or nowhere.

Folding the symbol away is a real convention too — it is what puts `Atlantic
Monthly` before `AT&T` in the earlier corpus — so it is kept as a second
reading and an ordering that needs it comes back as **check**. That is not what
saves a misfiling like `R&B`, which is wrong under both readings.

`&`, `+`, `%` and `@` are read aloud. `=` is not: `E=mc²` files after
`elocution`, which reading it aloud would break. Nor is `$`, where the word is
spoken after the number it precedes.

### The comma inside a closing quote is the separator

House style tucks the comma that divides a term from its page references
inside the quotation mark: `“Purple Rain,” 148`. Masking quoted spans — which
is what stops `“Ucayali, 1871” curare` losing its year — hid that comma too,
so the term read `“Purple Rain,” 148` and folded to `purplerain148`, filing
after every other Purple Rain entry and flagging three correct ones. The comma
*immediately* before a closing quote is exposed again; one in the middle of a
quoted phrase stays masked. The syntax rule then expects only a space in the
gap, since the term already carries its comma.

### A bracket with nothing in front of it is not a qualifier

`“(I Wanna) Testify”` and `(Music from) The Elder` open with a parenthesis, so
cutting the term there left an empty first segment that sorted before every
entry in the index. There is nothing for such a bracket to qualify: it is part
of the title, and the term files under `iwannatestify`.

### One misfiling should not flag the whole run after it

An entry filed too early sits above everything that legitimately follows, and
blaming the followers turns one misfiling into a wall. `“(I Wanna) Testify”`,
landing among the "I Got" entries, drew fourteen flags against entries that
were all correctly placed. When the entry after next fits where the intruder
sits, the intruder is reported instead and the run carries on from the
follower.

### A cross-reference is not part of the name

A dummy entry may be written `hoe. See garden hoe`, with a full stop rather than
the comma the term parser looked for. The whole clause then folded into the key
and the entry filed under `hoeseegardenhoe`, past every real h. A full stop
introduces a cross-reference as readily as a comma does.

### Two entries that alphabetise the same are reported

When a person, a place and a thing share a name they file in normal
alphabetical order — but if their keys are *identical*, sorting cannot say
which comes first and the guidelines' remedy is to tell them apart by hand,
`London (England)` against `London, Amy`. The pair is flagged as **check**,
since it needs an editor's eye rather than a rule.

### The primary key ignores all punctuation, not just the listed characters

§5 says to ignore "spaces, hyphens, periods, single and double quote marks".
Taken literally, `E=mc²` folds to `e=mc2` and files before `elocution`, because
`=` sorts below any letter. The published index puts it *after* elocution,
which only works if the `=` is dropped. So §5's list is illustrative and the
rule is "ignore all punctuation".

### A symbol that stands for a word ends the segment it is in

Folding `&` away with the rest of the punctuation put `A&E` under `ae`, between
Adore and AEG, and reported seven correct entries as misfiled. A symbol is read
aloud, so it is a word rather than a punctuation mark — but *reading it aloud
into the fold* is not what an index does either. The Leeds index settles it
with three cases, and only one treatment fits all three:

| | ignored | read aloud | ends the segment |
|---|---|---|---|
| `A&E` before `Abramovic` | ✗ | ✓ | ✓ |
| `R&B` before `race relations` | ✗ | ✗ | ✓ |
| `Red Hot + Riot` before `Red Hot Organization` | ✗ | ✓ | ✓ |

`R&B` is the one that decides it: read aloud it folds to `randb`, which files
*after* `race relations`, yet the index puts it at the head of the R's. What
files it there is the symbol ending the segment — the key becomes
`("r", SYMBOL, "b")`, and `r` sorts before `race` for the same reason a bare
`London` sorts before `London (England)`. Reading the symbol aloud is right in
spirit: it makes the symbol a word, and a word boundary is what the precedence
rule ranks on.

Ignoring the symbol is a real convention too — it is what puts `Atlantic
Monthly` before `AT&T` in the earlier corpus — so it is kept as a second
reading and an ordering that needs it comes back as **check**.

`SYMBOL` ranks after `COMMA`, on the grounds that a symbol stands for a word
and the guidelines put "word followed by letters" last. No index seen so far
has two entries that turn on it.

Only `&` and `+` are treated this way, both attested. `%`, `$`, `@` and `=` are
still folded away: `E=mc²` files after `elocution`, which ending the segment at
the `=` would break.

### The given name is a segment, not a run-on

`New, Arthur` and `New, James` share a first segment, and §5 sorts them before
`newborn` — which only works if the given name is compared as a segment of its
own rather than run together with the surname. It is what catches `Miller,
Glenn` before `Miller, George A.` — wrong, and in a published index. The same
segmenting continues past the second cut, so `Hoe, Robert` files before
`Hoe, Robert, Jr.`

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

Every one of those readings is as good as the others, so a numeral is *not*
reported: it is a house key, not an alternative. Leeds files `8 (album)` under
eight, `55 Grand` under fifty-five and `1999 Tour` under nineteen ninety-nine,
all correctly, and the earlier build queried all five. The digits-as-written
fold stays a reading too, which is what keeps the guidelines' "word followed by
a number" tier working for `London 1900` against `Londonderry` — there the
digits follow a word rather than opening the entry, so no spelling applies.

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
