"""Updating the tool in place, without the download-and-unzip dance.

The expensive part of an update is not the download — the whole project is
under 80 KB compressed. It is knowing whether there is anything to download at
all, and that costs one small request. When the answer is "no", which it
usually is, nothing else happens.

Fetching only the changed files was considered and rejected: raw files come
down uncompressed, so the last real update would have been 141 KB fetched
file-by-file against 77 KB for the whole compressed archive, at the cost of an
extra request per file and code to follow renames. Replacing everything is
both smaller and simpler.

Nothing in the project folder that belongs to the user may be lost: the
proofreader's own `overrides.json`, and a virtual environment if one was made
beside the project rather than in the home folder. None of it is in the
archive, so the rule is simple — copy files in, and only ever delete something
this updater itself installed last time.

This runs by itself when a checker starts, so in normal use nobody ever asks
for an update or downloads anything: the version on the desk is the version in
the repository, a day later at worst.
"""

from __future__ import annotations

import io
import json
import os
import shutil
import subprocess
import sys
import tempfile
import urllib.error
import urllib.request
import zipfile
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from pathlib import Path

REPO = "sebastian-w-klein/editools"
BRANCH = "main"
API = "https://api.github.com"
CODELOAD = "https://codeload.github.com"

MARKER_NAME = ".editools-update.json"

#: Never remove these, whatever a manifest says.
PROTECTED = {".venv", "venv", "overrides.json", "installed-from.txt",
             MARKER_NAME, ".git"}

#: How long a "no update available" answer stays good, so that several people
#: behind one office address do not exhaust the hourly limit for anonymous
#: requests to GitHub.
CHECK_INTERVAL = timedelta(days=1)

TIMEOUT = 30


class UpdateError(RuntimeError):
    """Something went wrong that the user needs to be told about plainly."""


@dataclass
class Marker:
    """What the last update installed, and when we last looked for a new one."""

    sha: str = ""
    installed: list[str] = field(default_factory=list)
    updated_at: str = ""
    last_checked: str = ""
    last_seen_sha: str = ""

    @classmethod
    def read(cls, root: Path) -> "Marker":
        try:
            with open(root / MARKER_NAME, encoding="utf-8") as handle:
                data = json.load(handle)
            return cls(
                sha=str(data.get("sha", "")),
                installed=[str(p) for p in data.get("installed", [])],
                updated_at=str(data.get("updated_at", "")),
                last_checked=str(data.get("last_checked", "")),
                last_seen_sha=str(data.get("last_seen_sha", "")),
            )
        except (OSError, ValueError):
            return cls()

    def write(self, root: Path) -> None:
        payload = {
            "sha": self.sha,
            "installed": sorted(self.installed),
            "updated_at": self.updated_at,
            "last_checked": self.last_checked,
            "last_seen_sha": self.last_seen_sha,
        }
        try:
            with open(root / MARKER_NAME, "w", encoding="utf-8") as handle:
                json.dump(payload, handle, indent=2)
        except OSError as exc:
            raise UpdateError(f"Could not record the update: {exc}") from exc

    def checked_recently(self) -> bool:
        if not self.last_checked:
            return False
        try:
            when = datetime.fromisoformat(self.last_checked)
        except ValueError:
            return False
        if when.tzinfo is None:
            when = when.replace(tzinfo=timezone.utc)
        return datetime.now(timezone.utc) - when < CHECK_INTERVAL


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def project_root() -> Path | None:
    """The folder holding the project, or None if this is not an editable install.

    An editable install points the environment at the source folder, so
    replacing files there is the whole update. A normal install copies the
    package into the environment instead, and cannot update itself this way.
    """
    here = Path(__file__).resolve()
    for candidate in here.parents[:4]:
        if (candidate / "pyproject.toml").is_file() and (candidate / "src" / "editools").is_dir():
            return candidate
    return None


# -- talking to GitHub ------------------------------------------------------


def _get(url: str, headers: dict[str, str] | None = None) -> bytes:
    request = urllib.request.Request(url, headers=headers or {})
    try:
        with urllib.request.urlopen(request, timeout=TIMEOUT) as response:
            return response.read()
    except urllib.error.HTTPError as exc:
        if exc.code in (403, 429):
            raise UpdateError(
                "GitHub would not answer this request. That is usually because too "
                "many update checks have come from this network in the last hour — "
                "waiting an hour fixes it. On a work network it can also mean GitHub "
                "is blocked, in which case updates have to be installed by hand.\n"
                "Either way the checker itself carries on working as before."
            ) from exc
        raise UpdateError(f"GitHub returned an error ({exc.code}) for {url}") from exc
    except urllib.error.URLError as exc:
        raise UpdateError(
            f"Could not reach GitHub ({exc.reason}). Check the internet connection."
        ) from exc


def latest_sha(fetch=_get) -> str:
    """The newest commit on the release branch.

    Asked for as plain text rather than the full commit record, which keeps the
    request that runs on every check down to a few dozen bytes.
    """
    url = f"{API}/repos/{REPO}/commits/{BRANCH}"
    body = fetch(url, {"Accept": "application/vnd.github.sha"})
    text = body.decode("utf-8", "replace").strip()
    if len(text) == 40 and all(c in "0123456789abcdef" for c in text.lower()):
        return text.lower()
    try:  # an older API, or a proxy that ignored the Accept header
        return str(json.loads(text)["sha"]).lower()
    except (ValueError, KeyError, TypeError) as exc:
        raise UpdateError("GitHub's reply was not in a form this could read.") from exc


def download(sha: str, fetch=_get) -> bytes:
    """The project at exactly *sha*, as a zip archive."""
    return fetch(f"{CODELOAD}/{REPO}/zip/{sha}", None)


# -- applying it ------------------------------------------------------------


def _safe_members(archive: zipfile.ZipFile) -> list[tuple[str, str]]:
    """Archive entries as ``(member, relative path)``, rejecting anything odd.

    An archive can name a path that climbs out of the folder it is extracted
    into. GitHub would never send one, but this code writes files, so it checks
    rather than trusts.
    """
    members: list[tuple[str, str]] = []
    for name in archive.namelist():
        if name.endswith("/"):
            continue
        parts = name.split("/")
        relative = "/".join(parts[1:])  # drop the archive's top-level folder
        if not relative:
            continue
        if any(part in ("..", "") or os.path.isabs(part) for part in parts):
            raise UpdateError(f"The archive contains an unsafe path: {name}")
        if Path(relative).is_absolute() or ".." in Path(relative).parts:
            raise UpdateError(f"The archive contains an unsafe path: {name}")
        members.append((name, relative))
    return members


def _is_protected(relative: str) -> bool:
    return Path(relative).parts[0] in PROTECTED if Path(relative).parts else True


def apply_archive(root: Path, data: bytes, previous: list[str]) -> tuple[list[str], bool]:
    """Write the archive over *root*, returning what it installed.

    Also reports whether ``pyproject.toml`` changed, which is the only reason
    an editable install needs anything reinstalling — source changes take
    effect on their own.
    """
    try:
        archive = zipfile.ZipFile(io.BytesIO(data))
    except zipfile.BadZipFile as exc:
        raise UpdateError("The download was not a readable archive.") from exc

    members = _safe_members(archive)
    if not any(relative == "src/editools/__init__.py" for _, relative in members):
        raise UpdateError(
            "The download does not look like the editorial tools; nothing was changed."
        )

    pyproject_before = (root / "pyproject.toml").read_bytes() if (root / "pyproject.toml").is_file() else b""

    staged = Path(tempfile.mkdtemp(prefix="editools-update-"))
    installed: list[str] = []
    try:
        for name, relative in members:
            if _is_protected(relative):
                continue
            target = staged / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            with archive.open(name) as source, open(target, "wb") as sink:
                shutil.copyfileobj(source, sink)
            installed.append(relative)

        # Everything extracted cleanly, so now put it in place.
        for relative in installed:
            destination = root / relative
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(staged / relative, destination)
    finally:
        shutil.rmtree(staged, ignore_errors=True)

    _remove_stale(root, previous, set(installed))

    pyproject_after = (root / "pyproject.toml").read_bytes() if (root / "pyproject.toml").is_file() else b""
    return installed, pyproject_before != pyproject_after


def _remove_stale(root: Path, previous: list[str], current: set[str]) -> None:
    """Delete files a past update installed that this one no longer ships.

    Nothing outside that list is ever touched, so the virtual environment, the
    overrides file, and anything else of the user's own is safe by
    construction — none of it was installed by an update.
    """
    for relative in previous:
        if relative in current or _is_protected(relative):
            continue
        target = root / relative
        try:
            if target.is_file():
                target.unlink()
                parent = target.parent
                while parent != root and not any(parent.iterdir()):
                    parent.rmdir()
                    parent = parent.parent
        except OSError:
            pass  # a file we cannot remove is not worth failing the update over


def reinstall(root: Path) -> tuple[bool, str]:
    """Re-run the install, for when the dependencies have changed."""
    try:
        finished = subprocess.run(
            [sys.executable, "-m", "pip", "install", "-e", str(root)],
            capture_output=True, text=True, timeout=600,
        )
    except (OSError, subprocess.SubprocessError) as exc:
        return False, f"Could not run the installer: {exc}"
    if finished.returncode != 0:
        tail = (finished.stderr or finished.stdout or "").strip().splitlines()
        return False, "\n".join(tail[-5:]) or "the installer reported a problem"
    return True, ""


# -- the whole job ----------------------------------------------------------


@dataclass
class Result:
    updated: bool
    message: str
    sha: str = ""
    changed: int = 0
    reinstalled: bool = False


def check(root: Path, force: bool = False, fetch=_get) -> tuple[bool, str, Marker]:
    """Is there a newer version? Answers from memory if asked recently."""
    marker = Marker.read(root)
    if not force and marker.sha and marker.checked_recently():
        available = bool(marker.last_seen_sha) and marker.last_seen_sha != marker.sha
        return available, marker.last_seen_sha or marker.sha, marker

    newest = latest_sha(fetch)
    marker.last_checked = _now()
    marker.last_seen_sha = newest
    try:
        marker.write(root)
    except UpdateError:
        pass  # a folder we cannot write to is the update's problem, not the check's
    return newest != marker.sha, newest, marker


def run(root: Path | None = None, force: bool = False, fetch=_get) -> Result:
    """Check for a new version and install it if there is one."""
    root = root or project_root()
    if root is None:
        return Result(False, (
            "This copy cannot update itself, because it was not installed from a "
            "project folder. Download the latest version from GitHub instead."
        ))

    available, newest, marker = check(root, force=True, fetch=fetch)
    if not available and not force:
        return Result(False, "Already up to date.", sha=newest)

    data = download(newest, fetch)
    installed, deps_changed = apply_archive(root, data, marker.installed)

    reinstalled = False
    if deps_changed:
        ok, detail = reinstall(root)
        reinstalled = ok
        if not ok:
            return Result(True, (
                f"Updated the files, but the components it needs could not be "
                f"installed:\n{detail}\n\n"
                f"Run this in the project folder to finish:\n"
                f"  {sys.executable} -m pip install -e ."
            ), sha=newest, changed=len(installed))

    marker.sha = newest
    marker.installed = installed
    marker.updated_at = _now()
    marker.last_checked = _now()
    marker.last_seen_sha = newest
    marker.write(root)

    note = " Components were updated too." if reinstalled else ""
    return Result(
        True,
        f"Updated to {newest[:7]} ({len(installed)} files).{note}\n"
        f"Close the checker window and start it again to use the new version.",
        sha=newest, changed=len(installed), reinstalled=reinstalled,
    )


def auto(root: Path | None = None, fetch=_get) -> dict:
    """Update on the quiet, as part of starting up.

    Called by the launchers before the checker itself starts, so that the
    version somebody uses is the current one without them ever being asked.
    It answers from the once-a-day cached check, so the usual cost is nothing
    at all, and it never fails loudly: a laptop on a train, an office that
    blocks GitHub, a folder that cannot be written to — none of those are a
    reason to stop somebody checking a proof.

    Returns what the page should say about it, if anything.
    """
    state = {"available": False, "installed": False, "latest": ""}
    try:
        root = root or project_root()
        if root is None:
            return state

        available, newest, _ = check(root, fetch=fetch)
        state["latest"] = newest[:7]
        if not available:
            return state

        result = run(root, fetch=fetch)
        state["available"] = True
        state["installed"] = bool(result.updated)
        state["message"] = result.message
    except UpdateError:
        pass          # said plainly by `editools update`, not by a launcher
    except Exception:
        pass          # nothing here is worth failing a launch over
    return state
