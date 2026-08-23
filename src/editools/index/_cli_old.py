"""Command line entry point."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from . import audit, webui
from .rules import COLOURS


def _check(args) -> int:
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


def _list_rules(_args) -> int:
    """Show what gets fixed and what gets flagged."""
    from . import rules as _rules

    fixes = ["elision", "number-dash", "note-italics", "see-style",
             "quotes", "whitespace"]
    print("Fixed for you, as tracked changes:")
    for rule in fixes:
        print(f"  {rule}")
    print("\nFlagged for you, highlighted and explained in a comment:")
    for rule in sorted(set(_rules.COLOURS) - set(fixes)):
        print(f"  {rule:<20} {COLOURS[rule]}")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="indexcheck",
        description="Check a book index against FSG house style.",
    )
    sub = parser.add_subparsers(dest="command")

    check = sub.add_parser("check", help="check an index and mark it up")
    check.add_argument("index", help="the .docx index to check")
    check.add_argument("-o", "--out", help="where to write the marked-up copy")
    check.add_argument("--dry-run", action="store_true",
                       help="report findings without writing a file")
    check.add_argument("--last-page", type=int, metavar="N",
                       help="last page of the book, to catch references past it")
    check.set_defaults(func=_check)

    rules = sub.add_parser("rules", help="list the checks and their colours")
    rules.set_defaults(func=_list_rules)

    ui = sub.add_parser("ui", help="open the drag-and-drop page")
    ui.add_argument("--port", type=int, default=8766)
    ui.add_argument("--no-browser", action="store_true")
    ui.set_defaults(func=lambda a: webui.serve(port=a.port,
                                               open_browser=not a.no_browser))

    args = parser.parse_args(argv)
    if not getattr(args, "func", None):
        parser.print_help()
        return 1
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
