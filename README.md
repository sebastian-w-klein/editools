# Index Checker

Checks a book index against FSG house style and hands back the Word file with
the problems highlighted and the fixes made as tracked changes.

Not built yet. `docs/FEASIBILITY.md` assesses the 28 rules on the wish list and
proposes a build order; `spikes/` contains the working proofs behind that
assessment.

## Spikes

Run them with `python-docx` and `lxml` installed:

```
python -m venv .venv
.venv/bin/pip install python-docx lxml
.venv/bin/python spikes/tracked_changes_spike.py   # writes checked2.docx
.venv/bin/python spikes/verify_spike.py            # shows accept-all / reject-all
.venv/bin/python spikes/sortkey_spike.py           # letter-by-letter alphabetising
```

`tracked_changes_spike.py` proves the core mechanism: tracked insertions,
deletions and formatting changes plus highlights, applied at exact character
ranges in a real `.docx`. `verify_spike.py` confirms that accepting all changes
yields the corrected text and rejecting them restores the original.
