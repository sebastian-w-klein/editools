"""Settings shared by both checkers, so a key is entered once and forgotten."""

from __future__ import annotations

import json
import os
import shutil
from pathlib import Path

HOME = Path(os.environ.get("EDITOOLS_HOME", Path.home() / ".editools"))
CONFIG_PATH = HOME / "config.json"
CACHE_PATH = HOME / "mw-cache.json"
OVERRIDES_PATH = HOME / "overrides.json"

#: Where the Hyphenation Checker kept these before the two tools were merged.
LEGACY_HOME = Path(os.environ.get("HYPHENCHECK_HOME",
                                  Path.home() / ".hyphencheck"))


def load() -> dict:
    try:
        with open(CONFIG_PATH, encoding="utf-8") as handle:
            data = json.load(handle)
        return data if isinstance(data, dict) else {}
    except (OSError, ValueError):
        return {}


def save(data: dict) -> Path:
    HOME.mkdir(parents=True, exist_ok=True)
    with open(CONFIG_PATH, "w", encoding="utf-8") as handle:
        json.dump(data, handle, indent=2)
    try:
        CONFIG_PATH.chmod(0o600)  # the key is a credential
    except OSError:
        pass
    return CONFIG_PATH


def api_key(explicit: str | None = None) -> str:
    """The Merriam-Webster key, from the flag, the environment, or the config file."""
    return explicit or os.environ.get("MW_DICTIONARY_KEY") or load().get("mw_key", "")


def verify_and_save(key: str) -> tuple[bool, str]:
    """Check a Merriam-Webster key actually works, then store it.

    Verifying before saving turns the commonest setup mistake — copying the
    Thesaurus key instead of the Collegiate one — into a clear message at the
    moment it happens, rather than a spreadsheet full of unverified rows later.
    """
    from .dictionary import Dictionary

    key = key.strip()
    if not key:
        return False, "No key was entered."

    dictionary = Dictionary(api_key=key, cache_path=CACHE_PATH)
    check = dictionary.lookup("cemetery")
    if check.source != "mw":
        detail = dictionary.api_errors[0] if dictionary.api_errors else "no entry came back"
        return False, (
            f"That key did not work ({detail}). Check you copied the Collegiate "
            f"Dictionary key rather than the Thesaurus one — they are not "
            f"interchangeable. A brand-new key can also take a few minutes to start working."
        )

    settings = load()
    settings["mw_key"] = key
    save(settings)
    dictionary.save()
    return True, f"Key saved and working (cemetery \u2192 {check.display})."


def load_overrides(path: str | Path | None = None) -> dict[str, str]:
    """Words the proofreader has ruled on herself.

    Maps a word to its dotted form (``"Mar*vo*lene"`` or ``"Mar·vo·lene"``) or
    to ``"nobreak"`` when the word may not be divided at all.  Invented names
    and house-style decisions live here, and they outrank the dictionary.
    """
    candidates = [Path(path)] if path else [OVERRIDES_PATH, Path("overrides.json")]
    for candidate in candidates:
        try:
            with open(candidate, encoding="utf-8") as handle:
                data = json.load(handle)
            if isinstance(data, dict):
                return {str(k): str(v) for k, v in data.items()}
        except (OSError, ValueError):
            continue
    return {}


def adopt_legacy() -> bool:
    """Move a pre-merge ``~/.hyphencheck`` across, once.

    The Merriam-Webster key takes twenty minutes to get hold of, most of it
    spent waiting for an email, and the lookup cache is a book's worth of
    requests already paid for. Losing either to a rename would be a poor way
    to find out the tools had been merged, so both are carried over the first
    time the new home is wanted. The old folder is copied, not moved: an
    install of the old checker that is still on the machine goes on working.
    """
    if HOME.exists() or not LEGACY_HOME.is_dir():
        return False
    try:
        HOME.mkdir(parents=True, exist_ok=True)
        for name in ("config.json", "mw-cache.json", "overrides.json"):
            source = LEGACY_HOME / name
            if source.is_file():
                shutil.copy2(source, HOME / name)
        try:
            (HOME / "config.json").chmod(0o600)
        except OSError:
            pass
        return True
    except OSError:
        return False
