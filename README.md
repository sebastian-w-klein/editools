# Hyphenation Checker

Finds bad end-of-line hyphen breaks in a typeset proof and gives you a
spreadsheet of what to fix, with page numbers.

Every hyphenated word at the end of a line is checked against **all nine rules**
of the ruleset — not just the first one that seems to apply. Rule 1 is checked
against Merriam-Webster's own syllable dots, looked up in MW's dictionary
service and remembered on your computer so it only happens once per word.

---

# Setting up

**You only do this once.** It takes about twenty minutes, most of which is
waiting for an email from Merriam-Webster. After that, checking a book is drag,
drop, download.

There are four steps:

1. Install Python (the language the tool is written in)
2. Download the tool
3. Install the tool
4. Get a free Merriam-Webster key and paste it in

If you get stuck at any point, jump to [If something goes
wrong](#if-something-goes-wrong) at the bottom — the common problems are all
listed there.

---

## Before you start: is Python already there?

It often is, and that saves you a step.

**On a Mac:** press `⌘ + Space`, type `Terminal`, press Enter. A window with a
text prompt opens. Type this and press Enter:

```
python3 --version
```

**On Windows:** press the Start button, type `Command Prompt`, press Enter.
Type this and press Enter:

```
python --version
```

If something like `Python 3.11.5` appears, you already have it — **skip to
Step 2**. Any version that starts with `3.` is fine, as long as it is 3.9 or
higher.

If you instead see `command not found`, `not recognized`, or Windows offers to
open the Microsoft Store, carry on with Step 1.

> Keep this Terminal or Command Prompt window open. You will need it again in
> Step 3.

---

## Step 1 — Install Python

### On a Mac

1. Go to **https://www.python.org/downloads/**
2. Click the big yellow **Download Python 3.x** button. It knows you are on a
   Mac and gives you the right file.
3. Open the downloaded file (it ends in `.pkg`) and click through the
   installer: Continue, Continue, Agree, Install. Enter your computer password
   if it asks.
4. **Do not skip this.** When the installer finishes, a Finder window opens
   showing the Python folder. Find the file called **`Install
   Certificates.command`** and double-click it. A black window appears, prints
   some text, and finishes.

   This step lets Python talk to websites securely. Without it, the tool cannot
   reach Merriam-Webster and every word comes back unverified. If the Finder
   window already closed, you can find the file at
   `Applications → Python 3.13 → Install Certificates.command` (the number may
   differ).

### On Windows

1. Go to **https://www.python.org/downloads/**
2. Click the big yellow **Download Python 3.x** button.
3. Open the downloaded file. The installer window appears.
4. **Before clicking anything else**, tick the box at the bottom that says
   **"Add python.exe to PATH"**.

   This is the single most important click in the whole setup. If you miss it,
   your computer will not know where Python is and Step 3 will fail. If you
   have already installed without ticking it, just run the installer again and
   choose **Modify**.

5. Click **Install Now** and wait. Click **Close** when it finishes.

### Check it worked

**Close your Terminal or Command Prompt window and open a new one** — it only
notices new software when it starts up. Then type the check from the section
above (`python3 --version` on a Mac, `python --version` on Windows). You should
now see a version number.

---

## Step 2 — Download the tool

1. Go to the project's page on GitHub.
2. Click the green **Code** button.
3. Choose **Download ZIP**.
4. Find the downloaded ZIP in your Downloads folder and unzip it: double-click
   on a Mac, or right-click → **Extract All** on Windows.
5. Move the unzipped `hyphenchecker` folder somewhere sensible — your Documents
   folder is fine. Just remember where you put it.

---

## Step 3 — Install the tool

This part uses the Terminal (Mac) or Command Prompt (Windows) window. You will
type two commands. If you have never used it before: it is just a place to type
instructions instead of clicking them, and nothing here can break anything.

**First, point the window at the folder.** Type `cd` followed by a space — then
**drag the `hyphenchecker` folder from Finder or File Explorer into the window
and let go**. It fills in the location for you. Press Enter.

```
cd /Users/yourname/Documents/hyphenchecker
```

**Then install it.** Copy this line exactly, paste it in, and press Enter:

**On a Mac** — type the first line, press Enter, wait for it to finish, then
type the second:
```
python3 -m venv .venv
```
```
.venv/bin/pip install -e .
```

**On Windows:**
```
python -m venv .venv
```
```
.venv\Scripts\pip install -e .
```

This downloads the handful of components the tool needs and puts them in their
own folder, tucked inside the project, so nothing else on your computer is
touched. It takes a minute or two and prints a lot of text.

You will know it worked when you see a line starting **`Successfully
installed`** followed by a list of names and version numbers.

> You may then see a note saying *"A new release of pip is available."* That is
> normal and has nothing to do with this tool. Ignore it.

**Now start it:**

**On a Mac:**
```
.venv/bin/hyphencheck ui
```

**On Windows:**
```
.venv\Scripts\hyphencheck ui
```

Your browser opens with the Hyphenation Checker. Leave the black window open
while you use it — closing it stops the tool.

> **From now on**, starting the tool is just: double-click
> **`run-checker.command`** (Mac) or **`run-checker.bat`** (Windows) in the
> `hyphenchecker` folder. You never need to type any of this again.
>
> On a Mac the first time, macOS may refuse to open it because it is from an
> unidentified developer. Right-click the file, choose **Open**, then **Open**
> again in the box that appears. It only asks once.

---

## Step 4 — Get your Merriam-Webster key

The tool needs to look words up in Merriam-Webster to check Rule 1, and
Merriam-Webster asks everyone who does that to register. It is free, and each
person needs their own — a key is tied to one account and allows 1,000 lookups
a day, which is a few books' worth.

You will see a note at the top of the Hyphenation Checker page saying no key is
saved. Here is how to get one.

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

5. Sign in at **https://dictionaryapi.com** and go to **Your Keys** — it is
   under your account name at the top of the page. You will see a long line of
   letters, numbers and dashes, something like:

   ```
   a1b2c3d4-5e6f-7890-abcd-ef1234567890
   ```

   That is your key. Copy it.

   **If two keys are listed**, take the one labelled **Collegiate Dictionary**,
   not the Thesaurus one. They are not interchangeable, and the tool will tell
   you if the wrong one gets used.

> **Treat the key like a password.** Don't paste it into emails or chat
> messages. Once you have entered it below it lives on your own computer, in a
> file only your account can read, and nothing needs it again. Colleagues should
> each register their own rather than sharing one.

### Entering the key

**The easy way — in the app window.** On the Hyphenation Checker page there is
a box marked *"Paste your Merriam-Webster key here."* Paste it in and click
**Save**. The tool checks the key against a real word before saving it, so you
find out immediately whether it works:

> Key saved and working (cemetery → cem·e·ter·y).

That is it. You will not be asked again, and the note at the top of the page
changes to say the key is saved.

**The other way — running the setup command.** If you would rather do it in the
window you used in Step 3, make sure you are still in the `hyphenchecker`
folder and type:

**On a Mac:**
```
.venv/bin/hyphencheck setup
```

**On Windows:**
```
.venv\Scripts\hyphencheck setup
```

It asks for the key, you paste it and press Enter, and it does the same check:

```
Merriam-Webster Collegiate Dictionary API key
(free from https://dictionaryapi.com/register/index — see the README)
Key: a1b2c3d4-5e6f-7890-abcd-ef1234567890
Key saved and working (cemetery → cem·e·ter·y).
Saved to /Users/yourname/.hyphencheck/config.json. You will not be asked again.
```

Both routes save to the same place. Use whichever you prefer.

---

# Checking a book

1. Double-click **`run-checker.command`** (Mac) or **`run-checker.bat`**
   (Windows).
2. Drag the proof PDF onto the page.
3. Wait. A full book takes a minute or two the first time. Later books are
   faster, because every word looked up is remembered.
4. Click **Download the spreadsheet**.

The flagged items also appear on the page, so you can see what turned up
without opening the file. Nothing leaves your computer except the individual
word lookups — the proof itself never goes anywhere.

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

The `All Instances` tab has a column for every rule so you can see at a glance
that each one was applied to each word — including the rules that turned out
not to apply.

## Words the dictionary cannot settle

Invented character names and house-style decisions go in an *overrides* file,
and they beat the dictionary. Copy the `overrides.example.json` file from the
project folder to `overrides.json` and edit it:

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

# If something goes wrong

**"command not found: python3" / "'python' is not recognized"**
Python is not installed, or on Windows the **"Add python.exe to PATH"** box was
not ticked during installation. Run the installer again, choose **Modify**, and
make sure that box is ticked. Then close your Terminal or Command Prompt window
and open a new one — it only notices new software when it starts.

**Windows opens the Microsoft Store when you type `python`**
That is Windows offering to install it for you, and it works fine — but the
python.org installer in Step 1 gives you more control. Either is acceptable.

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
The tool is running without a key and cannot reach the dictionary. Paste your
key into the box on the page. Rules 2, 3, 4, 5 and 8 still work without one, so
the spreadsheet is not worthless — but Rule 1 will be marked unverified
throughout.

**Red or yellow text appears in the black window**
Not everything printed there is an error. Notices about pip having a newer
version, or warnings mentioning `DeprecationWarning`, are harmless and can be
ignored. The messages worth acting on are the ones this section lists.

**The page says "No file was received" or nothing happens when you drop a PDF**
Make sure the file really is a PDF, and try clicking the drop area to choose it
from a file browser instead of dragging.

**It stops partway through a long book**
Merriam-Webster allows 1,000 lookups a day on a free key. A book uses a few
hundred distinct words, so this is only reachable if you check several books in
one day. Everything already looked up is saved, so running it again tomorrow
picks up where it left off rather than starting over.

**A character's invented name keeps getting flagged**
That is deliberate — the dictionary has no entry, so the tool will not guess.
Record your decision once in the overrides file (above) and it is treated as
settled from then on.

**The browser page won't load / "can't connect"**
The black window that starts the tool has been closed. Double-click
`run-checker.command` or `run-checker.bat` again and leave it open.

---

# For the technically inclined

The rest of this is not needed to use the tool.

## From the command line

```bash
hyphencheck audit BOOK.pdf                  # writes BOOK_hyphenation_audit.xlsx
hyphencheck audit BOOK.pdf -o audit.xlsx    # or name it yourself
hyphencheck word cemetery photographer      # where does MW divide this word?
hyphencheck audit BOOK.pdf --offline        # no dictionary; Rules 2-5, 8 still apply
hyphencheck ui                              # the drag-and-drop window
hyphencheck setup                           # save and verify your MW key
```

## Why this exists

It replaces a manual pass that ran into three problems, all structural rather
than a matter of trying harder:

| Problem | What the tool does |
|---|---|
| Checking a word under Rule 1, finding it fine, and stopping — so `butch-/er's` (Rule 3) and `cher-/ries—or` (Rule 4) slipped through, both being *correct* MW divisions that break a different rule | Every rule is applied to every break, independently. The spreadsheet has a column per rule so you can see it happened. |
| One Merriam-Webster lookup per word, by hand, over hundreds of words | One request per *distinct* word, run in parallel, cached on disk forever. The second book only pays for words the first did not contain. |
| Different answers on different passes | The same PDF gives the same spreadsheet every time. |

Rules 2, 3, 4, 5 and 8 need no dictionary at all — they are letter counts and
character adjacency, and they are where most real violations turn up.

## What it will not do

It flags; you decide. Specifically:

- **A word Merriam-Webster does not carry gets flagged, not guessed at.** That
  is Rule 6.4's instruction, and it is why invented names come back as NEEDS
  CHECK rather than a confident answer.
- **Proper-noun coverage depends on MW's Collegiate service**, which carries
  fewer biographical and geographical names than the website. Names it does not
  have fall through to Rule 6's morpheme and vowel tests, and are flagged when
  neither settles it.
- **Rule 9 needs the italics to survive extraction.** Foreign-language setting
  is detected from the PDF's font names; if a proof is generated without them,
  foreign words are caught only by their absence from MW.
- **Rule 7 is advisory**, never a violation — it expresses a preference among
  break points Merriam-Webster already allows.
- **Rejoining a compound can be genuinely ambiguous** (`re-cover` / `recover`).
  Where both readings are real words and the book uses both, the row is marked
  NEEDS CHECK rather than decided.
- **A word divided across a page turn** is rejoined with the first line of body
  text overleaf, skipping the running head and folio. On the rare proof where
  the continuation still cannot be read confidently, the row says so and asks
  you to check that page turn by eye, rather than inventing a word and
  reporting it as a violation.

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

[`docs/RULES.md`](docs/RULES.md) maps each rule in the ruleset to its
implementation, including the judgement calls.

## Running the tests

```bash
.venv/bin/pip install -e ".[dev]"
.venv/bin/python -m pytest
```

The tests build a small proof PDF containing every case in the ruleset —
including the four misses that prompted the "check every rule" instruction —
and run the whole pipeline over it. Merriam-Webster is not called from the test
run; the dictionary is primed with recorded responses in the real service's
shape, so the parsing path is exercised rather than stubbed.
