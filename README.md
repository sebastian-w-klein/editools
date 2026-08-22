# Index Checker

Checks a book index against FSG house style. You drop the Word file onto a page
and get the same file back with the problems highlighted, each one explained in
a Word comment, and every mark recorded as a tracked change — so nothing the
checker does can be left in the file by accident.

![The Index Checker page](docs/screenshot.png)

---

## What it checks so far

| Check | Highlight |
|---|---|
| Main entries out of alphabetical order | yellow |
| Subentries out of alphabetical order | green |
| Page numbers listed out of numerical order | blue |
| Page ranges that run backwards (30–20) | pink |

Alphabetising is letter by letter, per §5 of the FSG Indexing Guidelines: it
ignores spaces, punctuation and accents, and everything after an open
parenthesis, comma or colon. Because that makes `New, Arthur` and `New, James`
identical, a second key breaks the tie on the given name, with abbreviated
personal titles ignored as §7 requires.

The remaining rules from the wish list are not built yet.
[`docs/FEASIBILITY.md`](docs/FEASIBILITY.md) covers all 28 and the build order;
[`docs/RULES.md`](docs/RULES.md) records the judgement calls behind the ones
that are done.

## How the marks work

Every mark is a tracked change, so in Word:

* **Reject All** puts the file back exactly as it arrived. This is tested — on
  a 1,243-paragraph index, rejecting every change restored all 1,243
  paragraphs character for character.
* **Accept All** keeps the highlights. You would not normally want that; work
  through the comments and reject as you go.

Each highlight has a comment saying what is wrong, so you never have to work
out why something was flagged.

---

# Setting up

**You only do this once.** After that, checking an index is drag, drop,
download.

## Step 1 — Is Python already there?

**On a Mac:** press `⌘ + Space`, type `Terminal`, press Enter, then type:

```
python3 --version
```

**On Windows:** press Start, type `Command Prompt`, press Enter, then type:

```
python --version
```

If you see something starting with `3.` (3.9 or higher), skip to Step 2.
If you see `command not found` or `not recognized`, install Python from
**https://www.python.org/downloads/** first.

> On Windows, tick **"Add python.exe to PATH"** at the bottom of the installer
> before clicking Install. It is the easiest step to miss and the one that
> breaks everything else.

## Step 2 — Download the tool

On the project's GitHub page, click the green **Code** button, choose
**Download ZIP**, and unzip it somewhere you will remember — Documents is fine.

## Step 3 — Open it

* **On a Mac:** double-click **`run-checker.command`**
* **On Windows:** double-click **`run-checker.bat`**

The first time, it spends a minute setting itself up. Then a page opens in your
browser. Leave the small black window open while you use it — that is the
program itself. Closing it closes the checker.

> **Mac, first time only:** if you get "cannot be opened because it is from an
> unidentified developer", right-click `run-checker.command`, choose **Open**,
> then **Open** again. You only do this once.

## Step 4 — Check an index

Drag the Word file onto the page. You get a list of what was found and a
**Download the marked-up file** button.

Nothing leaves your computer. The page is served by the program running on your
own machine.

---

## For the terminal, if you prefer

```
indexcheck check index.docx          # writes index_checked.docx
indexcheck check index.docx --dry-run   # just report, write nothing
indexcheck rules                     # list the checks and their colours
indexcheck ui                        # open the drag-and-drop page
```

## Running the tests

```
python -m venv .venv
.venv/bin/pip install -e ".[dev]"
.venv/bin/python -m pytest
```
