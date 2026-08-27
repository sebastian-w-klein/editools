# Editorial Tools

Two checkers for two jobs, in one download:

| | What it does | What you give it | What you get back |
|---|---|---|---|
| **Index Checker** | Checks a book index against FSG house style | a Word file | the same file, marked up as tracked changes |
| **Hyphenation Checker** | Finds bad end-of-line hyphen breaks in a typeset proof | a PDF proof | a spreadsheet of what to fix, with page numbers |

They used to be two separate downloads with two separate setups. They are now
one, so there is one thing to install, one thing to keep, and **updates arrive
by themselves** — you will never download a zip file again.

You still use them as two tools. Each has its own page and its own colour;
one icon opens both, and you pick the one you want from the page that
appears.

---

# Setting up

**You only do this once**, for both tools together. There are three steps, and
the longest part is waiting for an email from Merriam-Webster in step 4 — and
that one is only needed for the Hyphenation Checker.

## Step 1 — Is Python already there?

It often is, and that saves you a step.

**On a Mac:** press `⌘ + Space`, type `Terminal`, press Enter. A window with a
text prompt opens. Type this and press Enter:

```
python3 --version
```

**On Windows:** press Start, type `Command Prompt`, press Enter, then type:

```
python --version
```

If something like `Python 3.11.5` appears, you already have it — **skip to
Step 2**. Any version starting with `3.` is fine, as long as it is 3.9 or
higher.

If you see `command not found`, `not recognized`, or Windows offers to open the
Microsoft Store, install Python from **https://www.python.org/downloads/**
first.

> **On Windows**, tick **"Add python.exe to PATH"** at the bottom of the
> installer before clicking Install. It is the easiest step to miss and the one
> that breaks everything else.

> **On a Mac**, when the installer finishes a Finder window opens showing the
> Python folder. Find **`Install Certificates.command`** and double-click it. A
> black window appears, prints some text, and finishes. This lets Python talk
> to websites securely — without it the Hyphenation Checker cannot reach
> Merriam-Webster. If the window already closed, the file is at
> `Applications → Python 3.13 → Install Certificates.command` (the number may
> differ).

## Step 2 — Download the tools

On the project's GitHub page, click the green **Code** button, choose
**Download ZIP**, and unzip it somewhere you will remember — Documents is fine.

**This is the last time you download anything.** From here on the tools keep
themselves up to date.

## Step 3 — Open it

Inside the folder there is one icon. Double-click it:

* **On a Mac:** **`Editorial Tools.command`**
* **On Windows:** **`Editorial Tools.bat`**

The first time, it spends a minute setting itself up. Then a page opens in your
browser offering both checkers. Click the one you want. Leave the small black
window open while you use it — that is the program itself. Closing it closes
both checkers.

> **Mac, first time only:** if you get "cannot be opened because it is from an
> unidentified developer", right-click the file, choose **Open**, then **Open**
> again. You only do this once.

There is only ever one thing to start, whichever checker you need, and you can
move between them from the link at the top of each page. If you double-click
the icon again while the tools are already open, it simply brings the page
back up rather than starting a second copy.

The tools keep their Python setup in your own user folder rather than beside
these files, so they work whether you keep this folder on your computer or on a
shared network drive.

## Step 4 — A Merriam-Webster key, for the Hyphenation Checker only

The Index Checker needs nothing else and is ready to use now. The Hyphenation
Checker needs to look words up in Merriam-Webster to check Rule 1, and
Merriam-Webster asks everyone who does that to register. It is free, and each
person needs their own — a key is tied to one account and allows 1,000 lookups
a day, which is a few books' worth.

### Registering

1. Go to **https://dictionaryapi.com/register/index**

2. Fill in the form: your name, email, and a password of your choosing.

3. Where it asks which dictionaries you want, tick **Collegiate® Dictionary**.

   That is the one with the syllable dots in it — the raised dots in
   `cem·e·ter·y` that say where a word may be divided. Those dots are the whole
   reason for the key. If it lets you tick a second one, the Collegiate®
   Thesaurus is a fine choice, but this tool does not use it.

   When it asks what you are building, an honest one-line answer such as
   "checking hyphenation in book proofs" is fine.

4. Submit the form and wait for the confirmation email. Click the link in it.

5. Sign in at **https://dictionaryapi.com** and go to **Your Keys** — under your
   account name at the top of the page. You will see a long line of letters,
   numbers and dashes, something like:

   ```
   a1b2c3d4-5e6f-7890-abcd-ef1234567890
   ```

   That is your key. Copy it.

   **If two keys are listed**, take the one labelled **Collegiate Dictionary**,
   not the Thesaurus one. They are not interchangeable, and the tool will tell
   you if the wrong one gets used.

> **Treat the key like a password.** Don't paste it into emails or chat
> messages. Once entered it lives on your own computer, in a file only your
> account can read. Colleagues should each register their own rather than
> sharing one.

### Entering it

On the Hyphenation Checker page there is a box marked *"Paste your
Merriam-Webster key here."* Paste it in and click **Save**. The tool checks the
key against a real word before saving, so you find out immediately whether it
works:

> Key saved and working (cemetery → cem·e·ter·y).

That is it. You will not be asked again.

> **Already had the old Hyphenation Checker?** Your key, your remembered word
> lookups and your overrides are picked up automatically the first time you
> open the new one. There is nothing to re-enter and nothing to copy across.

---

# Checking an index

1. Double-click **`Editorial Tools`** and choose the **Index Checker**.
2. Drag the Word file onto the page. If you fill in the last page of the book
   first, it will also catch references pointing past the end.
3. You get a list of what was fixed and what was flagged, and a **Download the
   marked-up file** button.

Nothing leaves your computer.

## What it fixes and what it flags

**Fixes, as tracked changes** — only where house style settles the question:

* page ranges elided as §9 wants them (`308–310` → `308–10`)
* hyphens and em dashes between page numbers turned into en dashes
* note markers and their note numbers italicised (§17)
* `see` and `see also` lowercased and italicised (§15)
* straight quotes turned into curly ones
* tabs removed, runs of spaces closed up

**Flags, highlighted and explained in a comment** — where it needs your
judgement:

| Check | Highlight |
|---|---|
| Main entries out of alphabetical order | yellow |
| Subentries out of alphabetical order | green |
| Page numbers out of order, or listed twice | blue |
| Page ranges that run backwards, or run past the end of the book | pink |
| Doubled punctuation, or an entry ending in it | yellow |
| A comma or semicolon that should be roman, not italic | green |
| A personal title spelled out rather than abbreviated | yellow |
| `ff.`, `passim`, spaced dashes, lines with no entry term | pink |
| A `see` or `see also` pointing at an entry that does not exist | pink |
| Punctuation between the parts of an entry (§12, §15, §16) | yellow |

A flag is either an **error** — wrong however you read it — or a **check**,
meaning it breaks the house rule but would be right under another defensible
reading. The comment says which.

Alphabetising is letter by letter, per §5 of the FSG Indexing Guidelines: it
ignores spaces, punctuation and accents, and everything after an open
parenthesis, comma or colon. Because that makes `New, Arthur` and `New, James`
identical, a second key breaks the tie on the given name, with abbreviated
personal titles ignored as §7 requires.

## How the marks work

Every mark is a tracked change, so in Word:

* **Reject All** puts the file back exactly as it arrived — fixes and
  highlights alike. This is checked on every run against all three sample
  indexes, paragraph for paragraph.
* **Accept All** would keep the highlights as well as the fixes, which you do
  not want. Work through the changes one at a time: accept the fixes you agree
  with, and reject each highlight once you have dealt with it.

Every highlight carries a comment saying what is wrong, so you never have to
work out why something was flagged.

[`docs/index/RULES.md`](docs/index/RULES.md) records the judgement calls behind
every rule; [`docs/index/FEASIBILITY.md`](docs/index/FEASIBILITY.md) covers the
whole wish list and what is left.

---

# Checking hyphenation in a proof

1. Double-click **`Editorial Tools`** and choose the **Hyphenation Checker**.
2. Drag the proof PDF onto the page.
3. Wait. A full book takes a minute or two the first time. Later books are
   faster, because every word looked up is remembered.
4. Click **Download the spreadsheet**.

Every hyphenated word at the end of a line is checked against **all nine rules**
of the ruleset — not just the first one that seems to apply. The flagged items
also appear on the page, so you can see what turned up without opening the
file. Nothing leaves your computer except the individual word lookups — the
proof itself never goes anywhere.

## Reading the spreadsheet

| Tab | What is on it |
|---|---|
| **Summary** | Totals, how many breaks each rule flagged, and every flagged item by page |
| **Flagged Items** | Only what needs your attention, sorted by page |
| **Advisories** | Legal breaks worth a glance that usually need no change — kept off the Flagged tab so they don't crowd the real work |
| **All Instances** | Every end-of-line hyphen in the book, with each rule's verdict in columns R1–R9 |
| **Line Breaks (Rule 6)** | Breaks *between* words: split initials, `Elizabeth / II`, `Sammy Davis / Jr.` |
| **Rule Key** | What each column means |

Four verdicts:

- **VIOLATION** — a rule is broken. The Reason column says which and why.
- **NEEDS CHECK** — the tool will not guess. Usually an invented name, or a
  word Merriam-Webster does not carry.
- **ADVISORY** — the break is allowed and breaks no rule. Rule 7 would prefer a
  different point, or the book divides the same word two ways in two places.
  These live on their own tab and can usually be ignored entirely.
- **OK** — nothing wrong with it.

[`docs/hyphen/RULES.md`](docs/hyphen/RULES.md) records the judgement calls
behind every rule.

## Words the dictionary cannot settle

Invented character names and house-style decisions go in an *overrides* file,
and they beat the dictionary. Copy `overrides.example.json` from this folder to
`overrides.json` and edit it:

```json
{
  "Marvolene": "Mar·vo·lene",
  "rulepig": "nobreak"
}
```

Use `·` to mark where a word may divide, or `nobreak` for a word that should
never be divided. Decisions recorded here carry over to every later book, so
each name only has to be settled once.

---

# Updates

**There is nothing to do.** When the tools are improved, the new version
installs itself the next time you open a checker. You do not download anything,
you do not unzip anything, and you are not asked.

It works like this:

* Opening a checker looks — at most once a day — for a newer version.
* If there is one, it is installed before the page opens. This takes a second
  or two.
* The page then says *"An update was installed. Close this window and open the
  checker again to start using it."*
* If the internet is unreachable, or your office network blocks GitHub, nothing
  happens and the checker starts exactly as before. An update is never urgent.

**Your settings are never affected.** Your Merriam-Webster key, your remembered
word lookups and your `overrides.json` all survive an update untouched — the
updater only ever replaces files that came with the tools in the first place.

If you would rather check by hand, `editools update --check` says whether one
is waiting and `editools update` installs it. Doing that also skips the
once-a-day look, which is the only reason a brand-new version can take a day to
arrive on its own.

Opening the tools by double-click keeps Python tucked away in its own folder, so
plain `editools` is not a command your Terminal or PowerShell knows — it answers
*"the term 'editools' is not recognized"*. Say which Python to use and it works
from any folder:

* **Windows**, in PowerShell:

  ```powershell
  & "$env:LOCALAPPDATA\EditorialTools\venv\Scripts\python.exe" -m editools update
  ```

* **macOS**, in Terminal:

  ```bash
  "$HOME/Library/Application Support/EditorialTools/venv/bin/python" -m editools update
  ```

---

# If something goes wrong

**"command not found: python3" / "'python' is not recognized"**
Python is not installed, or on Windows the **"Add python.exe to PATH"** box was
not ticked during installation. Run the installer again, choose **Modify**, and
make sure that box is ticked. Then close your Terminal or Command Prompt window
and open a new one — it only notices new software when it starts.

**"The term 'editools' is not recognized" / "command not found: editools"**
Nothing is broken, and nothing needs reinstalling. Opening the tools by
double-click keeps their Python in a folder of its own, which your Terminal or
PowerShell knows nothing about, so the short `editools …` commands are not
spelled out for it. Two ways past it: double-click **Editorial Tools** as usual
and let it update itself, or type the full path to its Python — the [Updates]
(#updates) section has the line to copy.

**Windows opens the Microsoft Store when you type `python`**
That is Windows offering to install it for you, and it works fine — but the
python.org installer in Step 1 gives you more control. Either is acceptable.

**It stops after "Setting up for the first time"**
You may see something about an environment location having "moved due to
redirects, links or junctions", naming a `\\NYFILE32\...` path. That is an
older version of the tool trying to set itself up on a network drive, which
Windows will not allow. The current version keeps its setup in your user folder
instead and works from a network drive. If you are seeing this, you are running
an old copy — download the current one.

**On a Mac: "SSL: CERTIFICATE_VERIFY_FAILED" when saving your key**
The `Install Certificates.command` step was skipped. Go to
`Applications → Python 3.13` (the number may differ) and double-click
**`Install Certificates.command`**, then try again.

**"That key did not work."**
Most often the Thesaurus key was copied instead of the Collegiate one — go back
to **Your Keys** on dictionaryapi.com and check which is which. It can also
mean the key is brand new; Merriam-Webster sometimes takes a few minutes to
activate one.

**Every word comes back "NEEDS CHECK" or the spreadsheet says "unverified"**
The Hyphenation Checker is running without a key and cannot reach the
dictionary. Paste your key into the box on the page. Rules 2, 3, 4, 5 and 8
still work without one, so the spreadsheet is not worthless — but Rule 1 will
be marked unverified throughout.

**Red or yellow text appears in the black window**
Not everything printed there is an error. Notices about pip having a newer
version, or warnings mentioning `DeprecationWarning`, are harmless and can be
ignored. The messages worth acting on are the ones this section lists.

**The page says "No file was received" or nothing happens when you drop a file**
Check you are on the right page: the Index Checker takes Word files, the
Hyphenation Checker takes PDFs. Then try clicking the drop area to choose the
file from a file browser instead of dragging it.

**It stops partway through a long book**
Merriam-Webster allows 1,000 lookups a day on a free key. A book uses a few
hundred distinct words, so this is only reachable if you check several books in
one day. Everything already looked up is saved, so running it again tomorrow
picks up where it left off rather than starting over.

**A character's invented name keeps getting flagged**
That is deliberate — the dictionary has no entry, so the tool will not guess.
Record your decision once in the overrides file (above) and it is treated as
settled from then on.

**"GitHub would not answer this request"**
Usually too many update checks have come from your office network in the last
hour — GitHub allows a limited number from any one address, and waiting an hour
fixes it. On a work network it can also mean GitHub is blocked outright, in
which case updates have to be installed by hand. Either way, carry on: the
checkers work exactly as before.

**An update finished but said the components could not be installed**
The files were updated but a new dependency could not be fetched. The message
tells you the one command to run in this folder to finish the job. Until then a
checker may not start, so it is worth doing straight away.

**The browser page won't load / "can't connect"**
The black window that starts the tools has been closed. Double-click the icon
again and leave it open.

**"Something else on this computer is already using port 8765"**
Another program has taken the port the tools use. The message tells you the one
command to run to use a different one. This is rare, and nothing to do with
having the tools open twice — opening them twice is handled and harmless.

---

# For the technically inclined

The rest of this is not needed to use the tools.

## From the command line

```bash
# Index Checker
editools index check index.docx                 # writes index_checked.docx
editools index check index.docx --last-page 460 # also catch pages past the end
editools index check index.docx --dry-run       # just report, write nothing
editools index rules                            # list the checks and their colours
editools index ui                               # open its page

# Hyphenation Checker
editools hyphen audit BOOK.pdf                  # writes BOOK_hyphenation_audit.xlsx
editools hyphen audit BOOK.pdf -o audit.xlsx    # or name it yourself
editools hyphen word cemetery photographer      # where does MW divide this word?
editools hyphen audit BOOK.pdf --offline        # no dictionary; Rules 2-5, 8 still apply
editools hyphen setup                           # save and verify your MW key
editools hyphen ui                              # open its page

# Both
editools ui                                     # the page they are both reached from
editools update                                 # install the latest version now
editools update --check                         # is there a newer version?
```

These are the names the commands go by once the environment they live in is the
one you are typing into. After a double-click install it is not, so reach them
the long way round — see [Updates](#updates) for the full path to type.

The old `indexcheck …` and `hyphencheck …` commands still work and mean the
same thing, so nothing written down before the merge has stopped working.

## How it is put together

```
src/editools/
  cli.py        one command, two tools
  config.py     settings, shared: ~/.editools/
  update.py     the self-updater
  webui/        one server, one port; /index/ and /hyphen/
  index/        the Index Checker's parser, rules and Word writer
  hyphen/       the Hyphenation Checker's extractor, rules and dictionary
```

The two rule engines are deliberately not shared. An index entry and an
end-of-line hyphen have nothing in common, and a common abstraction over them
would cost more than it saved.

## Running the tests

```bash
python -m venv .venv
.venv/bin/pip install -e ".[dev]"
.venv/bin/python -m pytest
```
