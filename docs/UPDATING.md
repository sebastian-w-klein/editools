# How updating works

The tool updates itself in place rather than being downloaded and unzipped
again. This note records why it works the way it does.

## Checking is the cheap part; downloading is not worth optimising

The obvious design is to fetch only the files that changed. Measured against a
real update — the page-turn fix, which touched 14 files — that would have been
**141 KB** fetched file by file, against **77 KB** for the entire project as a
compressed archive. Raw files come down uncompressed and the archive does not,
so the "incremental" approach moves nearly twice the bytes, needs a request per
file, and has to follow renames and deletions.

So there is no differ. The saving that matters is not downloading *at all* when
nothing has changed, and that costs one small request: GitHub will return just
the branch's commit hash, given `Accept: application/vnd.github.sha`. If it
matches what is recorded locally, the update stops there.

The archive is then fetched pinned to that exact hash rather than to the branch,
so the version checked and the version installed cannot disagree, even if
someone pushes in between.

## What must survive an update

Two things live inside the project folder and are not part of the project:

- **`.venv`** — the Python environment. Losing it means reinstalling from
  scratch, which for the intended user means going back to the README.
- **`overrides.json`** — the proofreader's own decisions about words the
  dictionary cannot settle, accumulated over every book.

Neither is in the archive, so the rule that protects them is a structural one
rather than a list of special cases: **the updater only ever deletes a file
that a previous update installed.** It records a manifest of what it wrote, and
on the next update removes only the entries that have since disappeared from
the project. Anything the user put in the folder was never in a manifest and so
can never be chosen for deletion. `.venv` and `overrides.json` are also named
explicitly in `PROTECTED`, as a second line.

## Failure modes it is built against

- **A partial download.** Files are extracted to a temporary folder first and
  only copied into place once the whole archive has been read. A truncated or
  corrupt download leaves the install untouched.
- **The wrong archive.** An archive that does not contain
  `src/hyphencheck/__init__.py` is refused before anything is written.
- **A path escaping the folder.** Archive entries naming `..` are rejected.
  GitHub would never send one, but this code writes files, so it checks rather
  than trusts.
- **Changed dependencies.** An editable install points the environment at the
  source folder, so replacing source files is the whole update — nothing needs
  reinstalling unless `pyproject.toml` itself changed. When it has, the
  installer is re-run, and if that fails the message names the one command
  needed to finish by hand.
- **GitHub's rate limit.** Anonymous requests are limited per address, and
  several colleagues in one office share an address. A "no update" answer is
  therefore cached for a day, so the window's automatic check costs nothing
  most of the time. A refusal is reported as "try again later", not as a fault.
- **No internet.** The window's update check fails silently. Someone checking a
  proof should not be interrupted because GitHub was unreachable.
