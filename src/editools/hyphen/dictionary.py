"""Where a word's legal break points come from.

Rule 1 says break points must match Merriam-Webster's own dotted entry, so
that is the primary source: MW's Dictionary API returns the headword with its
division points already marked (``cem*e*ter*y``), which is exactly the data
the rule asks for — no guessing at syllables.

Every response is cached on disk, so a re-run of the same book costs no API
calls at all, and the second book only pays for words the first one did not
contain.

Two lower-authority sources back it up:

* an *overrides* file, where the proofreader records decisions the dictionary
  cannot make for her (invented character names, house style);
* TeX's en-US hyphenation patterns, used only when there is no API key, and
  never reported as a Rule 1 violation — only as something to look at.
"""

from __future__ import annotations

import json
import os
import re
import threading
import time
import urllib.parse
from dataclasses import dataclass, field
from pathlib import Path

import requests

from .model import strip_possessive

API_ROOT = "https://www.dictionaryapi.com/api/v3/references"
DEFAULT_REFS = ("collegiate",)
DEFAULT_CACHE = Path.home() / ".hyphencheck" / "mw-cache.json"

#: MW marks division points with an asterisk in the headword field.
MW_DOT = "*"

#: How the dotted form is shown back to the user, matching MW's own display.
DISPLAY_DOT = "·"


@dataclass
class Syllabification:
    """What we know about where *word* may be divided."""

    word: str
    found: bool = False
    positions: set[int] = field(default_factory=set)
    dotted: str = ""
    source: str = "none"          # mw | override | tex | none
    hyphenated_compound: bool = False
    consulted: bool = False       # Merriam-Webster was actually asked about this word
    note: str = ""

    @property
    def authoritative(self) -> bool:
        """True when the source is one Rule 1 accepts as governing."""
        return self.source in ("mw", "override")

    @property
    def display(self) -> str:
        return self.dotted.replace(MW_DOT, DISPLAY_DOT) if self.dotted else ""


def positions_from_dotted(dotted: str) -> set[int]:
    """Character offsets of the division points in a dotted headword."""
    positions: set[int] = set()
    offset = 0
    for chunk in dotted.split(MW_DOT)[:-1]:
        offset += len(chunk)
        positions.add(offset)
    return positions


def plain(dotted: str) -> str:
    return dotted.replace(MW_DOT, "")


class Dictionary:
    """Looks up division points, cheapest source first."""

    def __init__(
        self,
        api_key: str | None = None,
        cache_path: str | Path | None = None,
        refs: tuple[str, ...] = DEFAULT_REFS,
        overrides: dict[str, str] | None = None,
        offline: bool = False,
        timeout: float = 15.0,
    ) -> None:
        self.api_key = api_key or os.environ.get("MW_DICTIONARY_KEY") or ""
        self.refs = refs
        self.offline = offline or not self.api_key
        self.timeout = timeout
        self.overrides = {k.lower(): v for k, v in (overrides or {}).items()}
        self.cache_path = Path(cache_path) if cache_path else DEFAULT_CACHE
        self._cache: dict[str, object] = _load_cache(self.cache_path)
        self._dirty = False
        self._lock = threading.Lock()
        self._local = threading.local()
        self._tex = None
        self.api_calls = 0
        self.api_errors: list[str] = []
        self._memo: dict[str, Syllabification] = {}

    # -- public ---------------------------------------------------------

    def lookup(self, word: str) -> Syllabification:
        """Division points for *word*, including possessive and plural forms."""
        key = word.lower()
        cached = self._memo.get(key)
        if cached is not None:
            return cached
        result = self._lookup_uncached(word)
        self._memo[key] = result
        return result

    @property
    def session(self) -> requests.Session:
        """One session per thread — prefetch fans out across several."""
        session = getattr(self._local, "session", None)
        if session is None:
            session = requests.Session()
            self._local.session = session
        return session

    def save(self) -> None:
        if self._dirty:
            _save_cache(self.cache_path, self._cache)
            self._dirty = False

    # -- resolution order -----------------------------------------------

    def _lookup_uncached(self, word: str) -> Syllabification:
        key = word.lower()

        override = self.overrides.get(key)
        if override is not None:
            return _from_override(word, override)

        forms = self._mw_forms(key)
        consulted = forms is not None
        if forms:
            hit = self._match(word, forms)
            if hit:
                return hit

        # A regular "+s" plural or possessive keeps the stem's division points:
        # the s simply joins the final syllable.
        base = strip_possessive(word)
        if base.lower() != key:
            stem = self.lookup(base)
            if stem.found:
                return Syllabification(
                    word=word,
                    found=True,
                    positions=set(stem.positions),
                    dotted=stem.dotted,
                    source=stem.source,
                    hyphenated_compound=stem.hyphenated_compound,
                    consulted=stem.consulted,
                    note=f"from MW entry for “{base}”",
                )
        if key.endswith("s") and not key.endswith(("ss", "us", "is")):
            singular = word[:-1]
            stem_forms = self._mw_forms(singular.lower())
            consulted = consulted or stem_forms is not None
            if stem_forms:
                stem = self._match(singular, stem_forms)
                if stem and stem.found and not stem.hyphenated_compound:
                    return Syllabification(
                        word=word,
                        found=True,
                        positions=set(stem.positions),
                        dotted=stem.dotted + "s",
                        source=stem.source,
                        consulted=stem.consulted,
                        note=f"regular plural of “{singular}”; stem division points apply",
                    )

        return self._tex_fallback(word, consulted)

    def _match(self, word: str, forms: dict[str, str]) -> Syllabification | None:
        dotted = forms.get(word.lower())
        if dotted is None:
            return None
        return Syllabification(
            word=word,
            found=True,
            positions=positions_from_dotted(dotted),
            dotted=dotted,
            source="mw",
            hyphenated_compound="-" in plain(dotted),
            consulted=True,
        )

    def _tex_fallback(self, word: str, consulted: bool = False) -> Syllabification:
        """TeX patterns, used only where Merriam-Webster has not spoken.

        If MW *was* asked and had no entry, TeX must not paper over that: the
        word is an invented name or foreign, and guessing at its syllables is
        exactly what Rule 1 forbids.
        """
        if consulted:
            return Syllabification(word=word, found=False, source="none", consulted=True)
        positions = self._tex_positions(word)
        if positions is None:
            return Syllabification(word=word, found=False, source="none")
        return Syllabification(
            word=word,
            found=False,
            positions=positions,
            dotted=_insert_dots(word, positions),
            source="tex",
            note="not confirmed against Merriam-Webster",
        )

    def _tex_positions(self, word: str) -> set[int] | None:
        if self._tex is None:
            try:
                import pyphen

                self._tex = pyphen.Pyphen(lang="en_US")
            except Exception:
                self._tex = False
        if not self._tex:
            return None
        try:
            return set(self._tex.positions(word))
        except Exception:
            return None

    # -- Merriam-Webster -------------------------------------------------

    def _mw_forms(self, word: str) -> dict[str, str] | None:
        """All dotted forms MW knows for *word*, or None if MW was not consulted."""
        entries = self._mw_entries(word)
        if entries is None:
            return None
        return collect_dotted_forms(entries)

    def _mw_entries(self, word: str) -> list | None:
        collected: list = []
        consulted = False
        for ref in self.refs:
            cache_key = f"{ref}:{word}"
            if cache_key in self._cache:
                consulted = True
                cached = self._cache[cache_key]
                if isinstance(cached, list):
                    collected.extend(cached)
                continue
            if self.offline:
                continue
            payload = self._fetch(ref, word)
            if payload is None:
                continue
            consulted = True
            with self._lock:
                self._cache[cache_key] = payload
                self._dirty = True
            collected.extend(payload)
        return collected if consulted else None

    def _fetch(self, ref: str, word: str) -> list | None:
        url = f"{API_ROOT}/{ref}/json/{urllib.parse.quote(word)}"
        for attempt in range(3):
            try:
                response = self.session.get(
                    url, params={"key": self.api_key}, timeout=self.timeout
                )
                with self._lock:
                    self.api_calls += 1
                if response.status_code == 200:
                    return response.json()
                if response.status_code in (429, 500, 502, 503):
                    time.sleep(2**attempt)
                    continue
                self.api_errors.append(f"{word}: HTTP {response.status_code}")
                return None
            except requests.RequestException as exc:
                if attempt == 2:
                    self.api_errors.append(f"{word}: {type(exc).__name__}")
                    return None
                time.sleep(2**attempt)
        return None


def collect_dotted_forms(entries: list) -> dict[str, str]:
    """Harvest every dotted form from a set of MW API entries.

    MW puts division points on the headword (``hwi.hw``), on inflected forms
    (``ins[].if`` — this is where ``cher*ries`` lives), on variants
    (``vrs[].va``) and on undefined run-ons (``uros[].ure``).  All of them are
    legitimate answers to "where may this word be divided".
    """
    forms: dict[str, str] = {}

    def add(dotted: object) -> None:
        if not isinstance(dotted, str):
            return
        dotted = re.sub(r"[\[\]{}()]", "", dotted).strip()
        if not dotted or " " in dotted:
            return
        key = plain(dotted).lower()
        if key and key not in forms:
            forms[key] = dotted

    for entry in entries:
        if not isinstance(entry, dict):
            continue  # a bare string is MW's "did you mean" suggestion
        add(entry.get("hwi", {}).get("hw"))
        for inflection in entry.get("ins", []) or []:
            add(inflection.get("if"))
        for variant in entry.get("vrs", []) or []:
            add(variant.get("va"))
        for run_on in entry.get("uros", []) or []:
            add(run_on.get("ure"))
            for inflection in run_on.get("ins", []) or []:
                add(inflection.get("if"))
    return forms


def _insert_dots(word: str, positions: set[int]) -> str:
    out = []
    for index, ch in enumerate(word):
        if index in positions and index:
            out.append(MW_DOT)
        out.append(ch)
    return "".join(out)


def _from_override(word: str, value: str) -> Syllabification:
    if value.strip().lower() in ("nobreak", "none", "-"):
        return Syllabification(
            word=word, found=True, positions=set(), dotted=word, source="override",
            consulted=True, note="marked unbreakable in the overrides file",
        )
    dotted = value.replace(DISPLAY_DOT, MW_DOT).replace("·", MW_DOT)
    return Syllabification(
        word=word,
        found=True,
        positions=positions_from_dotted(dotted),
        dotted=dotted,
        source="override",
        hyphenated_compound="-" in plain(dotted),
        consulted=True,
        note="from the overrides file",
    )


def _load_cache(path: Path) -> dict:
    try:
        with open(path, encoding="utf-8") as handle:
            data = json.load(handle)
        return data if isinstance(data, dict) else {}
    except (OSError, ValueError):
        return {}


def _save_cache(path: Path, cache: dict) -> None:
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        tmp = path.with_suffix(path.suffix + ".tmp")
        with open(tmp, "w", encoding="utf-8") as handle:
            json.dump(cache, handle)
        tmp.replace(path)
    except OSError:
        pass
