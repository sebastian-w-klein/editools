# Setting up, start to finish

You need to do this once. After that, checking a book is drag, drop, download.

There are two parts: installing the program, and getting a free key from
Merriam-Webster so the program can look words up in the dictionary.

---

## Part 1 — Get the free Merriam-Webster key

A "key" here is just a long password that tells Merriam-Webster the requests
are coming from you. It is free and takes about five minutes, most of which is
waiting for an email.

1. Go to **https://dictionaryapi.com/register/index**

2. Fill in the form: your name, email, and a password.

3. Where it asks which dictionaries you want, tick
   **Collegiate® Dictionary**.

   That is the one that has the syllable dots in it — the raised dots in
   `cem·e·ter·y` that say where a word may be divided. This is the whole reason
   for the key. If it lets you tick a second, **Collegiate® Thesaurus** is a
   fine choice, but it is not used here.

   When it asks what you are building, an honest one-line answer such as
   "checking hyphenation in book proofs" is fine.

4. Submit the form and wait for the confirmation email. Click the link in it.

5. Sign in at **https://dictionaryapi.com** and go to **Your Keys** (it is
   under your account name at the top). You will see a long line of letters,
   numbers and dashes, something like:

   ```
   a1b2c3d4-5e6f-7890-abcd-ef1234567890
   ```

   That is your key. Copy it.

   If two keys are listed, take the one labelled **Collegiate Dictionary**, not
   the Thesaurus one — they are not interchangeable, and the program will tell
   you if the wrong one gets used.

**Treat the key like a password.** Don't paste it into emails or chats. It
lives on your own computer once you've entered it below, and nothing needs it
again.

---

## Part 2 — Install the program

### On a Mac

1. Open the `hyphenchecker` folder.
2. Double-click **`run-checker.command`**.

   The first time, a black window appears and says it is setting things up.
   That takes a minute. It only happens once.

   If macOS says it cannot open the file because it is from an unidentified
   developer: right-click the file, choose **Open**, then **Open** again in the
   box that appears.

3. Your browser opens with the Hyphenation Checker.

### On Windows

1. Open the `hyphenchecker` folder.
2. Double-click **`run-checker.bat`**.
3. Your browser opens with the Hyphenation Checker.

### Telling it your key

The page will say *"No Merriam-Webster key saved."* To fix that, open the
black window that appeared and type:

```
hyphencheck setup
```

Paste your key when it asks, and press Enter. It checks the key works by
looking up one word, and tells you either way:

```
Key verified (cemetery → cem·e·ter·y) and saved to /Users/you/.hyphencheck/config.json.
```

That is it. You will not be asked again.

---

## Checking a book

1. Double-click `run-checker.command` (Mac) or `run-checker.bat` (Windows).
2. Drag the proof PDF onto the page.
3. Wait. A full book takes a minute or two the first time, and is much faster
   afterwards, because every word looked up is remembered.
4. Click **Download the spreadsheet**.

The flagged items also appear on the page, so you can see what turned up
without opening the file.

---

## If something goes wrong

**"That key did not work."**
Most often the Thesaurus key was copied instead of the Collegiate one. Go back
to **Your Keys** on dictionaryapi.com and check which is which. It can also
mean the key is brand new — Merriam-Webster sometimes takes a few minutes to
activate one.

**Every word comes back "NEEDS CHECK."**
The program is running without a key and cannot reach the dictionary. Run
`hyphencheck setup`. Rules 2, 3, 4, 5 and 8 still work without one, so the
spreadsheet is not worthless — but Rule 1 will be marked unverified throughout.

**"No such file."**
The PDF path has a typo, or the file has moved. Dragging the file onto the page
avoids this entirely.

**It stops partway through a long book.**
Merriam-Webster allows 1,000 lookups a day on a free key. A book uses a few
hundred distinct words, so this is only reachable if you check several books in
one day. Everything already looked up is cached, so running it again tomorrow
picks up where it left off rather than starting over.

**A character's invented name keeps getting flagged.**
That is deliberate — the dictionary has no entry, so the program will not guess.
Once you decide where it should divide, record it once in
`~/.hyphencheck/overrides.json` and it will be treated as settled from then on,
in this book and every later one:

```json
{
  "Marvolene": "Mar·vo·lene",
  "rulepig": "nobreak"
}
```

Use `nobreak` for a word that should never be divided.
