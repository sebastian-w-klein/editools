"""One command for both checkers.

``editools index …`` and ``editools hyphen …`` do what ``indexcheck`` and
``hyphencheck`` used to do, and both of those names still work: they are kept
as their own commands so that nothing anybody has written down stops working.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from . import config, update as updater


# -- Index Checker ----------------------------------------------------------


def cmd_index_check(args) -> int:
    from .index import audit

    result = audit.run(args.index, out_path=args.out, mark=not args.dry_run,
                       last_page=args.last_page)
    counts = result.counts()
    print(f"{result.entries} entries read from {Path(args.index).name}")
    if not result.findings:
        print("Nothing to flag.")
    else:
        print(f"{result.fixes} fix(es) made, {result.flags} thing(s) flagged:")
        for rule in sorted(counts):
            print(f"  {counts[rule]:>4}  {rule}")
    if not args.dry_run:
        print(f"\nMarked-up copy: {result.path}")
    return 0


def cmd_index_rules(_args) -> int:
    """Show what gets fixed and what gets flagged."""
    from .index import rules as _rules

    fixes = ["elision", "number-dash", "note-italics", "see-style",
             "quotes", "whitespace"]
    print("Fixed for you, as tracked changes:")
    for rule in fixes:
        print(f"  {rule}")
    print("\nFlagged for you, highlighted and explained in a comment:")
    for rule in sorted(set(_rules.COLOURS) - set(fixes)):
        print(f"  {rule:<20} {_rules.COLOURS[rule]}")
    return 0


# -- Hyphenation Checker ----------------------------------------------------


def _dictionary(args):
    from .hyphen.dictionary import Dictionary

    key = config.api_key(getattr(args, "key", None))
    return Dictionary(
        api_key=key,
        cache_path=getattr(args, "cache", None) or config.CACHE_PATH,
        overrides=config.load_overrides(getattr(args, "overrides", None)),
        offline=getattr(args, "offline", False) or not key,
    )


def cmd_hyphen_audit(args) -> int:
    from .hyphen import audit, report

    pdf_path = Path(args.pdf)
    if not pdf_path.exists():
        print(f"No such file: {pdf_path}", file=sys.stderr)
        return 2

    output = Path(args.output) if args.output else pdf_path.with_name(
        pdf_path.stem + "_hyphenation_audit.xlsx"
    )
    dictionary = _dictionary(args)
    if dictionary.offline and not args.offline:
        print(
            "No Merriam-Webster key found, so Rule 1 will fall back to TeX patterns "
            "and be reported as unverified.\nRun `editools hyphen setup` to add a key.\n",
            file=sys.stderr,
        )

    def progress(message):
        if not args.quiet:
            print(message, file=sys.stderr)

    result = audit.run(str(pdf_path), dictionary, progress=progress)
    path = report.write(result, output)

    counts = result.counts()
    print(f"\n{path}")
    print(
        f"{counts['Violations']} violation(s), {counts['Needs check']} needing a look, "
        f"{counts['Advisories']} advisory, across {counts['Real word divisions checked']} "
        f"word divisions on {counts['Pages']} pages."
    )
    if result.api_errors and not args.quiet:
        print(f"{len(result.api_errors)} lookup(s) failed: "
              f"{', '.join(result.api_errors[:5])}", file=sys.stderr)
    for brk in sorted(result.violations,
                      key=lambda b: (b.book_page.zfill(5), b.line_index))[:15]:
        print(f"  p.{brk.book_page or brk.pdf_page:<5} {brk.display:<24} {brk.flagged_rules}")
    if len(result.violations) > 15:
        print(f"  … and {len(result.violations) - 15} more, all listed in the spreadsheet.")
    return 0


def cmd_hyphen_word(args) -> int:
    dictionary = _dictionary(args)
    for word in args.words:
        syl = dictionary.lookup(word)
        source = {"mw": "Merriam-Webster", "override": "overrides file",
                  "tex": "TeX patterns (unverified)", "none": "not found"}[syl.source]
        points = ", ".join(str(p) for p in sorted(syl.positions)) or "none"
        print(f"{word}: {syl.display or '—'}  [{source}]  break points after character: {points}")
    dictionary.save()
    return 0


def cmd_hyphen_setup(args) -> int:
    key = args.key
    if not key:
        print("Merriam-Webster Collegiate Dictionary API key")
        print("(free from https://dictionaryapi.com/register/index — see the README)")
        try:
            key = input("Key: ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            return 1
    ok, message = config.verify_and_save(key)
    if not ok:
        print(message, file=sys.stderr)
        return 1
    print(f"{message}\nSaved to {config.CONFIG_PATH}. You will not be asked again.")
    return 0


# -- shared -----------------------------------------------------------------


def cmd_update(args) -> int:
    root = updater.project_root()
    if root is None:
        print(
            "This copy cannot update itself, because it was not installed from a "
            "project folder.\nDownload the latest version from GitHub instead.",
            file=sys.stderr,
        )
        return 1

    if args.auto:
        # What the launchers run. Says nothing when there is nothing to say.
        state = updater.auto(root)
        if state.get("installed"):
            print(state.get("message", "Updated."))
        return 0

    try:
        if args.check:
            available, newest, marker = updater.check(root, force=True)
            if available:
                current = marker.sha[:7] if marker.sha else "unknown"
                print(f"An update is available ({current} → {newest[:7]}).")
                print("It will install by itself next time you open a checker,")
                print("or run `editools update` to install it now.")
            else:
                print("Already up to date.")
            return 0

        print("Checking for updates…", file=sys.stderr)
        result = updater.run(root, force=args.force)
    except updater.UpdateError as exc:
        print(str(exc), file=sys.stderr)
        return 1

    print(result.message)
    return 0


def cmd_ui(args) -> int:
    from . import webui

    config.adopt_legacy()
    state = updater.auto() if not args.no_update else None
    return webui.serve(host=args.host, port=args.port,
                       open_browser=not args.no_browser,
                       tool=args.tool, update_state=state)


def _add_ui(sub, tool: str, help_text: str):
    parser = sub.add_parser("ui", help=help_text)
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8765)
    parser.add_argument("--no-browser", action="store_true")
    parser.add_argument("--no-update", action="store_true",
                        help="skip the check for a new version")
    parser.set_defaults(func=cmd_ui, tool=tool)
    return parser


def _add_dictionary_flags(parser):
    parser.add_argument("--key", help="Merriam-Webster API key (overrides the saved one)")
    parser.add_argument("--cache", help="path to the lookup cache file")
    parser.add_argument("--overrides", help="path to a JSON overrides file")
    parser.add_argument("--offline", action="store_true",
                        help="do not call Merriam-Webster; use TeX patterns for Rule 1")


def _add_update(sub):
    parser = sub.add_parser("update", help="install the latest version")
    parser.add_argument("--check", action="store_true",
                        help="only say whether an update is available")
    parser.add_argument("--force", action="store_true",
                        help="reinstall even if already up to date")
    parser.add_argument("--auto", action="store_true",
                        help=argparse.SUPPRESS)   # what the launchers run
    parser.set_defaults(func=cmd_update)


def _add_index_commands(sub):
    check = sub.add_parser("check", help="check an index and mark it up")
    check.add_argument("index", help="the .docx index to check")
    check.add_argument("-o", "--out", help="where to write the marked-up copy")
    check.add_argument("--dry-run", action="store_true",
                       help="report findings without writing a file")
    check.add_argument("--last-page", type=int, metavar="N",
                       help="last page of the book, to catch references past it")
    check.set_defaults(func=cmd_index_check)

    rules = sub.add_parser("rules", help="list the checks and their colours")
    rules.set_defaults(func=cmd_index_rules)

    _add_ui(sub, "index", "open the Index Checker page")


def _add_hyphen_commands(sub):
    run_parser = sub.add_parser("audit", help="check a PDF and write the spreadsheet")
    run_parser.add_argument("pdf")
    run_parser.add_argument("-o", "--output", help="where to write the .xlsx")
    run_parser.add_argument("-q", "--quiet", action="store_true")
    _add_dictionary_flags(run_parser)
    run_parser.set_defaults(func=cmd_hyphen_audit)

    word_parser = sub.add_parser("word", help="show where a word may be divided")
    word_parser.add_argument("words", nargs="+")
    _add_dictionary_flags(word_parser)
    word_parser.set_defaults(func=cmd_hyphen_word)

    setup_parser = sub.add_parser("setup", help="save and verify your MW API key")
    setup_parser.add_argument("--key", help="the key, if you would rather not be prompted")
    setup_parser.set_defaults(func=cmd_hyphen_setup)

    _add_ui(sub, "hyphen", "open the Hyphenation Checker page")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="editools",
        description="Editorial Tools: the Index Checker and the Hyphenation Checker.",
    )
    sub = parser.add_subparsers(dest="tool_name")

    index = sub.add_parser("index", help="check a book index (Word file)")
    _add_index_commands(index.add_subparsers(dest="command", required=True))

    hyphen = sub.add_parser("hyphen", help="check hyphen breaks in a proof (PDF)")
    _add_hyphen_commands(hyphen.add_subparsers(dest="command", required=True))

    _add_ui(sub, "home", "open the page both checkers are used from")
    _add_update(sub)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if not getattr(args, "func", None):
        build_parser().print_help()
        return 1
    return args.func(args)


# -- the two old commands, kept so nothing written down stops working --------


def index_main(argv: list[str] | None = None) -> int:
    """``indexcheck …`` as it was, run through the merged parser."""
    return main(["index"] + list(argv if argv is not None else sys.argv[1:]))


def hyphen_main(argv: list[str] | None = None) -> int:
    """``hyphencheck …`` as it was, run through the merged parser."""
    return main(["hyphen"] + list(argv if argv is not None else sys.argv[1:]))


if __name__ == "__main__":
    raise SystemExit(main())
