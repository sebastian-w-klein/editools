"""The overrides file is hand-edited, so it has to say when it cannot be read.

Every name a proofreader has ever settled lives in this one file. Handing back
an empty set because a word processor curled a quotation mark loses all of it,
and a proof checked without it looks exactly like a proof checked with it —
which is why silence here is worse than the error.
"""

from __future__ import annotations

import pytest

from editools import config

GOOD = '{\n  "Marvolene": "Mar·vo·lene",\n  "rulepig": "nobreak"\n}\n'


@pytest.fixture
def overrides(tmp_path):
    def write(text: str):
        path = tmp_path / "overrides.json"
        path.write_text(text, encoding="utf-8")
        return path
    return write


def test_a_good_file_is_read_and_says_nothing(overrides):
    result = config.read_overrides(overrides(GOOD))
    assert result.words == {"Marvolene": "Mar·vo·lene", "rulepig": "nobreak"}
    assert result.problem == ""


def test_no_file_at_all_is_not_a_problem(tmp_path):
    """Most books need no overrides; that is not something to warn about."""
    result = config.read_overrides(tmp_path / "nothing-here.json")
    assert result.words == {} and result.problem == ""


def test_curled_quotation_marks_are_named_as_the_cause(overrides):
    """What TextEdit does to this file unless it is in plain-text mode."""
    result = config.read_overrides(overrides('{“Marvolene”: “Mar·vo·lene”}'))
    assert result.words == {}
    assert "curly" in result.problem
    assert "Make Plain Text" in result.problem
    assert "line 1" in result.problem


def test_a_comma_after_the_last_entry_is_named_as_the_cause(overrides):
    result = config.read_overrides(overrides('{\n  "Marvolene": "Mar·vo·lene",\n}\n'))
    assert result.words == {}
    assert "comma after the last entry" in result.problem


def test_an_unexplained_error_still_reports_the_file_and_line(overrides):
    result = config.read_overrides(overrides('{\n  "Marvolene" "Mar·vo·lene"\n}\n'))
    assert result.words == {}
    assert "overrides.json" in result.problem and "line 2" in result.problem


def test_a_file_that_is_not_a_list_of_words_is_refused(overrides):
    result = config.read_overrides(overrides('["Marvolene"]'))
    assert result.words == {}
    assert "list of words" in result.problem


def test_a_file_that_is_not_plain_text_is_refused(tmp_path):
    path = tmp_path / "overrides.json"
    path.write_bytes(b"\xff\xfe{\x00}\x00")       # saved in the wrong encoding
    result = config.read_overrides(path)
    assert result.words == {}
    assert "plain text" in result.problem


def test_every_problem_says_the_words_went_unused(overrides):
    """The consequence is the part that matters, so every message carries it."""
    for text in ('{“a”: “b”}', '{"a": "b",}', '["a"]', '{"a" "b"}'):
        problem = config.read_overrides(overrides(text)).problem
        assert "were used" in problem or "was used" in problem, text


def test_the_plain_loader_still_returns_just_the_words(overrides):
    """Nothing that only wants the words had to change."""
    assert config.load_overrides(overrides(GOOD))["rulepig"] == "nobreak"
    assert config.load_overrides(overrides('{“a”: “b”}')) == {}
