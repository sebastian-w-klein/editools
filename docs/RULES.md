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

**Current state: 13 findings across 2,778 entries, and all 13 are genuine.**

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
more than one defensible reading. Picking one and flagging every index that
chose the other would bury the real findings, so an entry offers *candidate*
keys and is accepted if any reading puts it in order.

**Numerals.** An index files numerals as though spelled out, but `911` may be
read "nine one one" or "nine hundred eleven", and `1984` "nineteen
eighty-four". All the readings are offered. This is what lets `911/999` sit
among the n's, and `1956 consent decree for` sit after `nickname for`.

**Leading articles.** §8 moves an article to the end of a title of a work, but
a name keeps it: `"El Pastor"` files under Pastor, and `al-Aqsa Mosque` under
Aqsa. Both the term as written and the term without its article are offered,
including joined Arabic prefixes (`al-`, `el-`, `ad-`…).

**Initial prepositions in subentries.** This one is *not* a per-entry choice —
an index picks a convention and holds to it. Judging each pair under whichever
reading suits it lets an inconsistent list slip through: O'Hara has
`at Fordlandia` before `Ford and`, which is wrong if you ignore "at" and wrong
in a different place if you don't, but reading each pair separately finds
neither. So the whole subentry list is judged under both conventions and the
one it follows more closely is reported. On a tie the house rule wins:
initial prepositions and conjunctions do not count.

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
