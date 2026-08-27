# How each rule is implemented

A map from the ruleset document to the code, including the judgement calls.
All of it lives in `src/hyphencheck/rules.py` unless noted.

Every rule runs against every break. A rule that does not apply returns `n/a`
with its reason, rather than being skipped — so the `All Instances` tab shows
positively that each rule was considered.

---

### Rule 1 — General English words

The break index (the number of characters before the hyphen) must be one of the
division points in Merriam-Webster's dotted headword. MW's API returns these as
asterisks in the `hw` field (`cem*e*ter*y`), so this is a set-membership test
against real data, not an estimate of where syllables fall.

Division points are harvested from the headword, from inflected forms (`ins` —
this is where `cher*ries` lives), from variants (`vrs`), and from undefined
run-ons (`uros`).

Three outcomes beyond pass/fail:

- **MW's entry has no dots at all** (`cometh`) — then no break is legal, and
  any break is a violation.
- **MW has no entry** — `NEEDS CHECK`. The word is not guessed at.
- **No API key** — TeX's en-US hyphenation patterns stand in, and a mismatch is
  reported as `SUSPECT` ("confirm against MW"), never as a Rule 1 violation.
  TeX has no vocabulary, so when MW *was* asked and had no entry, TeX is not
  consulted at all — otherwise an invented name would be quietly waved through.

Rule 1 stands down for URLs (Rule 8 says so) and for a break at a compound's
own hyphen (that is Rule 5's business, not a syllable division).

### Rule 2 — Letter minimums

Alphabetic characters only, on each side. Punctuation and digits do not count.
Applies to compounds broken at their own hyphen too — Rule 5 says where a
compound may break, not whether the minimums are waived. This is what catches
`fold-/up`.

### Rule 3 — Possessives

Fires only on a possessive. The trailing `'s` is stripped and the remaining
letters counted, so `fa-ther's` passes (`ther`, 4) and `moth-er's` fails (`er`,
2). Also checks the ruleset's second clause: if the base word has no break
point that clears Rule 2 on its own, it cannot be broken with the possessive
attached either.

This is checked independently of Rule 1 — `butch-/er's` is a correct MW
division *and* a Rule 3 violation.

### Rule 4 — Em dash adjacency

Looks at the character set tight against the word on either side, taken from
the extracted line. Both a real em dash (`—`) and the typewriter `--` count.
The extractor keeps this context deliberately: for `cher-/ries—or`, the dash
arrives attached to the fragment on the *next* line, and for
`encroachment—power-/ful` it is attached to the fragment on the current one,
so both sides are captured (`extract.py`, via `split_trailing_word` /
`split_leading_word`).

### Rule 5 — Already-hyphenated compounds

Whether the break sits at a compound's own hyphen is settled before Rule 1
runs, because the answer decides whether Rule 1 applies at all. Three sources,
most reliable first:

1. A hyphen inside either fragment settles it outright — the word is a compound
   and the break is *not* at its hyphen, which is a violation
   (`pov-/erty-stricken`).
2. The book's own text: if `cross-legged` is set intact somewhere else in the
   same proof, that is the intended form.
3. Merriam-Webster: a hyphenated headword means a compound.

Where the closed form is a real word *and* the book also uses the hyphenated
form, the row is marked `NEEDS CHECK` rather than decided — `re-cover` and
`recover` are different words and no amount of string handling can tell which
was set.

### Rule 6 — Proper nouns

Applied in the ruleset's own order, stopping at the first that answers:

1. In MW → Rule 1 governs.
2. Ends in a recognizable morpheme (`-worth`, `-ville`, `-son`, `-berg`, and
   about thirty more) → the boundary in front of it is a **seam**, not merely a
   no-split zone.
3. Otherwise, a break after a vowel is accepted — but only where TeX's en-US
   patterns do not contradict it.
4. Otherwise flagged, per the rule's own instruction not to guess.

**Step 2, both sides of the seam.** Leaving the morpheme whole is not enough.
`Word-/sworth` does not split `-worth` and is still wrong: the linking s belongs
to `Words`, and carried over it makes a second element nobody set. So a break
short of the seam has to answer to the element in front of it, which — unlike
the name as a whole — is often an ordinary word MW carries:

- **MW knows the element** → the break must be one of *its* division points.
  `but·ter` licenses `But-/terfield` and rejects `Butt-/erfield`; `words` is
  dotted nowhere, so `Words-/worth` is the only place Wordsworth divides.
- **MW does not know it** → the letters the break would carry over must be able
  to form a syllable, which means containing a vowel. `Farn-/sworth` and
  `Islin-/gton` strand a bare consonant on the morpheme and are violations;
  `Isl-/ington` carries `ing` and is left alone.

This is what caught `Word-/sworth`, where the old one-sided test passed the
break and the correct `Words-/worth` read identically in the report.

**Step 3, a guess is not a pass.** `Sha-/ron` follows a vowel exactly as
`Ma-/rina` does, and one of the two is wrong; the last letter of the fragment
cannot tell them apart. So where TeX has division points for the name and the
break is not among them — or, as with `Sharon`, where TeX finds nowhere to
divide it at all — the row goes to a human as `NEEDS CHECK` rather than passing.

TeX never *licenses* a break here and never produces a violation: it omits
legitimate points as readily as it withholds bad ones, so absence of agreement
is worth a look and nothing more. This is the one place TeX is consulted after
MW has been asked and had no entry (`Dictionary.tex_positions`); Rule 1 still
may not see it, because a Rule 1 verdict would then rest on a guess, which is
exactly what that rule forbids.

The initials, numerals and `Jr./Sr.` provisions are breaks *between* words, not
hyphen breaks, so they are collected by a separate scan
(`check_line_breaks`) and reported on their own tab.

### Rule 7 — Prefixes and suffixes

Advisory only, and never overrides MW: it fires only when MW allows more than
one division point and the break is not at the morpheme boundary. So
`displea-/sure` earns an advisory pointing at `dis-pleasure`, and a preferred
point that would fail Rule 2 is not suggested.

### Rule 8 — URLs

A URL, bare domain or email address is detected from the two fragments joined
together. Any hyphen at a line break inside one is a violation — the ruleset
forbids both adding one and letting the address's own hyphen fall there — and
the finding names the legal break points from the rule's list (before `/`, `.`,
`,`, `:`, `-`, `~`, `_`, `?`, `#`, `%`, `@`; before or after `=` and `&`).

Rules 1–7 return `n/a` for URLs, as the rule directs.

### Rule 9 — Non-English words

A word with its own MW entry is Rule 1's business, assimilated or not, so
Rule 9 stands down for it. Otherwise it fires on evidence of foreign-language
*setting*: italics (read from the PDF's font names) or non-English diacritics.

A missing MW entry on its own is Rule 1's finding, not Rule 9's — otherwise
every ordinary coinage and closed compound would be double-reported as a
foreign word.

---

### Consistency (not a numbered rule)

The same word divided at two different points in one book is flagged on every
instance, with the pages listed. Both points can be legal and it is still an
error in the proof. This is what `Mar-/volene` versus `Marvol-/ene` is.

### Words divided across a page turn

A word broken on a page's last line continues on the *next page's first line of
body text* — not on its running head or folio. Getting that wrong does not
merely lose a break: it joins two unrelated fragments into a word nobody set
(`consid-` + `ONE: The Garden` → `considONE`) and then reports that word as a
confident rule violation.

So page furniture is identified before any break is read, by four independent
signals, any one of which is enough:

1. **Position.** A running head and a folio hold the same height on every page.
   Short lines that recur in the top or bottom margin band across at least a
   third of the pages are furniture, whatever they say. This is the signal that
   survives a running head naming the chapter, which never repeats often enough
   to be found by counting text.
2. **Geometry.** Furniture is separated from the text block by much more than a
   line's leading. Short lines set apart by more than 1.8× the usual leading are
   peeled off each end of the page. The leading is estimated from the *most
   common* gap rather than the median, because each page's margins contribute a
   couple of very large gaps that drag a median upward.
3. **Repeated text.** Short lines appearing at a page edge three or more times.
4. **The export slug.** InDesign stamps the file name, the spread number and
   the export date and time across the foot of every page of a proof
   (`042-154238_ch01_1P.indd 29    08/07/26 7:27 PM`). A literal file name is
   as certain a mark of furniture as there is, and it is needed as its own
   signal because the first three all look for a *short* line: the slug runs
   most of the measure and slips past every one of them. It is matched against
   the line as extracted, before the artifact patterns below trim it, and
   against a form with runs of repeated characters collapsed — some pages of a
   proof decode the same slug with every glyph doubled
   (`004422--115544223388__cchh0011__11PP..iinnddd`), which is where
   `bath-/cchh` and a "`PPMM`" flagged as a broken name both came from.

If a break still crosses a page turn into something that reads as furniture —
all capitals, or containing digits — the row is reported as unreadable, with a
note asking for that page turn to be checked by eye. Refusing to answer is the
right outcome there; inventing a word and citing a rule against it is not.

### Extraction artifacts

A soft hyphen fused onto an em dash by the PDF text layer (`patrons—-`) divides
no word. These are detected, excluded from the violation counts, and still
listed so the numbers reconcile.
