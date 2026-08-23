"""Updating in place.

GitHub is never contacted from a test; a fake fetcher serves an archive built
on the spot. That leaves the part worth testing exercised for real — writing
files over a live install without destroying the things that must survive it.
"""

from __future__ import annotations

import io
import json
import zipfile
from pathlib import Path

import pytest

from hyphencheck import update as updater
from hyphencheck.update import Marker, UpdateError

SHA = "a" * 40
NEWER = "b" * 40


def build_archive(files: dict[str, str], sha: str = NEWER) -> bytes:
    """An archive shaped like GitHub's: one top-level folder, then the project."""
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as archive:
        for path, content in files.items():
            archive.writestr(f"hyphenchecker-{sha}/{path}", content)
    return buffer.getvalue()


DEFAULT_FILES = {
    "pyproject.toml": "[project]\nname = 'hyphencheck'\ndependencies = ['pdfplumber']\n",
    "README.md": "# new readme\n",
    "src/hyphencheck/__init__.py": "__version__ = '2.0.0'\n",
    "src/hyphencheck/rules.py": "# new rules\n",
}


@pytest.fixture
def install(tmp_path) -> Path:
    """A project folder that looks like a working install."""
    root = tmp_path / "hyphenchecker"
    (root / "src" / "hyphencheck").mkdir(parents=True)
    (root / "pyproject.toml").write_text(DEFAULT_FILES["pyproject.toml"], encoding="utf-8")
    (root / "README.md").write_text("# old readme\n", encoding="utf-8")
    (root / "src" / "hyphencheck" / "__init__.py").write_text("__version__ = '1.0.0'\n", encoding="utf-8")
    (root / "src" / "hyphencheck" / "rules.py").write_text("# old rules\n", encoding="utf-8")

    # The things that must survive an update.
    (root / ".venv" / "bin").mkdir(parents=True)
    (root / ".venv" / "bin" / "hyphencheck").write_text("#!/bin/sh\n", encoding="utf-8")
    (root / "overrides.json").write_text('{"Marvolene": "Mar*vo*lene"}', encoding="utf-8")

    Marker(sha=SHA, installed=["README.md", "pyproject.toml",
                               "src/hyphencheck/__init__.py",
                               "src/hyphencheck/rules.py"]).write(root)
    return root


def fake_fetch(sha: str = NEWER, files: dict[str, str] | None = None, calls: list | None = None):
    payload = build_archive(files or DEFAULT_FILES, sha)

    def fetch(url: str, headers=None) -> bytes:
        if calls is not None:
            calls.append(url)
        if url.startswith(updater.API):
            return sha.encode()
        return payload

    return fetch


# -- checking ---------------------------------------------------------------

def test_no_update_means_nothing_is_downloaded(install):
    calls: list[str] = []
    result = updater.run(install, fetch=fake_fetch(sha=SHA, calls=calls))
    assert not result.updated and result.message == "Already up to date."
    assert all(url.startswith(updater.API) for url in calls), "an archive was fetched anyway"


def test_a_recent_check_is_not_repeated_over_the_network(install):
    """Several people behind one address must not exhaust GitHub's hourly limit."""
    marker = Marker.read(install)
    marker.last_checked = updater._now()
    marker.last_seen_sha = marker.sha
    marker.write(install)

    calls: list[str] = []
    available, _, _ = updater.check(install, fetch=fake_fetch(calls=calls))
    assert not available and calls == []


def test_a_stale_check_does_go_to_the_network(install):
    marker = Marker.read(install)
    marker.last_checked = "2020-01-01T00:00:00+00:00"
    marker.write(install)
    calls: list[str] = []
    available, _, _ = updater.check(install, fetch=fake_fetch(calls=calls))
    assert available and calls


# -- applying ---------------------------------------------------------------

def test_an_update_replaces_the_source(install):
    result = updater.run(install, fetch=fake_fetch())
    assert result.updated
    assert (install / "src" / "hyphencheck" / "rules.py").read_text() == "# new rules\n"
    assert (install / "README.md").read_text() == "# new readme\n"


def test_the_virtual_environment_is_never_touched(install):
    """Losing .venv would send the user back to reinstalling from scratch."""
    updater.run(install, fetch=fake_fetch())
    assert (install / ".venv" / "bin" / "hyphencheck").is_file()


def test_the_users_own_overrides_survive(install):
    updater.run(install, fetch=fake_fetch())
    assert json.loads((install / "overrides.json").read_text())["Marvolene"] == "Mar*vo*lene"


def test_a_file_dropped_from_the_project_is_removed(install):
    files = dict(DEFAULT_FILES)
    del files["src/hyphencheck/rules.py"]
    updater.run(install, fetch=fake_fetch(files=files))
    assert not (install / "src" / "hyphencheck" / "rules.py").exists()


def test_only_files_a_past_update_installed_are_ever_removed(install):
    """Anything the user put there themselves is safe by construction."""
    stray = install / "my notes.txt"
    stray.write_text("keep me", encoding="utf-8")
    files = {k: v for k, v in DEFAULT_FILES.items() if k != "README.md"}
    updater.run(install, fetch=fake_fetch(files=files))
    assert stray.read_text() == "keep me"
    assert not (install / "README.md").exists()  # this one was ours to remove


def test_the_marker_records_what_was_installed(install):
    updater.run(install, fetch=fake_fetch())
    marker = Marker.read(install)
    assert marker.sha == NEWER
    assert "src/hyphencheck/rules.py" in marker.installed
    assert marker.updated_at


# -- refusing bad input -----------------------------------------------------

def test_an_archive_that_is_not_this_project_is_refused(install):
    files = {"README.md": "# something else entirely\n"}
    with pytest.raises(UpdateError, match="does not look like"):
        updater.run(install, fetch=fake_fetch(files=files))
    assert (install / "src" / "hyphencheck" / "rules.py").read_text() == "# old rules\n"


def test_a_path_climbing_out_of_the_folder_is_refused(install):
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as archive:
        archive.writestr(f"hyphenchecker-{NEWER}/src/hyphencheck/__init__.py", "x = 1\n")
        archive.writestr(f"hyphenchecker-{NEWER}/../../escaped.txt", "pwned\n")
    with pytest.raises(UpdateError, match="unsafe path"):
        updater.apply_archive(install, buffer.getvalue(), [])
    assert not (install.parent.parent / "escaped.txt").exists()


def test_a_corrupt_download_is_refused(install):
    def fetch(url, headers=None):
        return NEWER.encode() if url.startswith(updater.API) else b"not a zip at all"

    with pytest.raises(UpdateError, match="readable archive"):
        updater.run(install, fetch=fetch)


def test_an_unreachable_github_is_explained_not_raised_raw(install):
    def fetch(url, headers=None):
        raise UpdateError("Could not reach GitHub (timed out). Check the internet connection.")

    with pytest.raises(UpdateError, match="Could not reach GitHub"):
        updater.run(install, fetch=fetch)


# -- dependencies -----------------------------------------------------------

def test_unchanged_dependencies_need_no_reinstall(install, monkeypatch):
    monkeypatch.setattr(updater, "reinstall",
                        lambda root: pytest.fail("reinstalled without need"))
    assert updater.run(install, fetch=fake_fetch()).updated


def test_changed_dependencies_trigger_a_reinstall(install, monkeypatch):
    ran: list[Path] = []
    monkeypatch.setattr(updater, "reinstall", lambda root: (ran.append(root), (True, ""))[1])
    files = dict(DEFAULT_FILES)
    files["pyproject.toml"] = "[project]\nname = 'hyphencheck'\ndependencies = ['pdfplumber', 'brand-new']\n"
    result = updater.run(install, fetch=fake_fetch(files=files))
    assert ran == [install] and result.reinstalled


def test_a_failed_reinstall_says_how_to_finish_by_hand(install, monkeypatch):
    monkeypatch.setattr(updater, "reinstall", lambda root: (False, "no network"))
    files = dict(DEFAULT_FILES)
    files["pyproject.toml"] = "[project]\ndependencies = ['something-else']\n"
    result = updater.run(install, fetch=fake_fetch(files=files))
    assert result.updated and "pip install -e ." in result.message


# -- finding the project ----------------------------------------------------

def test_the_project_folder_is_found_from_the_running_code():
    root = updater.project_root()
    assert root is not None
    assert (root / "pyproject.toml").is_file()
