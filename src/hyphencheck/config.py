"""Small persistent settings file, so the API key is entered once and forgotten."""

from __future__ import annotations

import json
import os
from pathlib import Path

HOME = Path(os.environ.get("HYPHENCHECK_HOME", Path.home() / ".hyphencheck"))
CONFIG_PATH = HOME / "config.json"
CACHE_PATH = HOME / "mw-cache.json"
OVERRIDES_PATH = HOME / "overrides.json"


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
