"""Command line for the hyphenation checker."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from . import audit, config, report, update as updater
from .dictionary import Dictionary
from .model import Verdict


def _dictionary(args) -> Dictionary:
    key = config.api_key(getattr(args, "key", None))
    return Dictionary(
        api_key=key,
        cache_path=getattr(args, "cache", None) or config.CACHE_PATH,
        overrides=config.load_overrides(getattr(args, "overrides", None)),
        offline=getattr(args, "offline", False) or not key,
    )


def cmd_audit(args) -> int:
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
            "and be reported as unverified.\nRun `hyphencheck setup` to add a key.\n",
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
    for brk in sorted(result.violations, key=lambda b: (b.book_page.zfill(5), b.line_index))[:15]:
        print(f"  p.{brk.book_page or brk.pdf_page:<5} {brk.display:<24} {brk.flagged_rules}")
    if len(result.violations) > 15:
        print(f"  … and {len(result.violations) - 15} more, all listed in the spreadsheet.")
    return 0


def cmd_word(args) -> int:
    dictionary = _dictionary(args)
    for word in args.words:
        syl = dictionary.lookup(word)
        source = {"mw": "Merriam-Webster", "override": "overrides file",
                  "tex": "TeX patterns (unverified)", "none": "not found"}[syl.source]
        points = ", ".join(str(p) for p in sorted(syl.positions)) or "none"
        print(f"{word}: {syl.display or '—'}  [{source}]  break points after character: {points}")
    dictionary.save()
    return 0


def cmd_setup(args) -> int:
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


def cmd_update(args) -> int:
    root = updater.project_root()
    if root is None:
        print(
            "This copy cannot update itself, because it was not installed from a "
            "project folder.\nDownload the latest version from GitHub instead.",
            file=sys.stderr,
        )
        return 1

    try:
        if args.check:
            available, newest, marker = updater.check(root, force=True)
            if available:
                current = marker.sha[:7] if marker.sha else "unknown"
                print(f"An update is available ({current} → {newest[:7]}).")
                print("Run `hyphencheck update` to install it.")
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

    return webui.serve(host=args.host, port=args.port, open_browser=not args.no_browser)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="hyphencheck",
        description="Audit end-of-line hyphen breaks in a typeset proof.",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    def add_common(sub):
        sub.add_argument("--key", help="Merriam-Webster API key (overrides the saved one)")
        sub.add_argument("--cache", help="path to the lookup cache file")
        sub.add_argument("--overrides", help="path to a JSON overrides file")
        sub.add_argument("--offline", action="store_true",
                         help="do not call Merriam-Webster; use TeX patterns for Rule 1")

    run_parser = subparsers.add_parser("audit", help="check a PDF and write the spreadsheet")
    run_parser.add_argument("pdf")
    run_parser.add_argument("-o", "--output", help="where to write the .xlsx")
    run_parser.add_argument("-q", "--quiet", action="store_true")
    add_common(run_parser)
    run_parser.set_defaults(func=cmd_audit)

    word_parser = subparsers.add_parser("word", help="show where a word may be divided")
    word_parser.add_argument("words", nargs="+")
    add_common(word_parser)
    word_parser.set_defaults(func=cmd_word)

    setup_parser = subparsers.add_parser("setup", help="save and verify your MW API key")
    setup_parser.add_argument("--key", help="the key, if you would rather not be prompted")
    setup_parser.set_defaults(func=cmd_setup)

    update_parser = subparsers.add_parser("update", help="install the latest version")
    update_parser.add_argument("--check", action="store_true",
                               help="only say whether an update is available")
    update_parser.add_argument("--force", action="store_true",
                               help="reinstall even if already up to date")
    update_parser.set_defaults(func=cmd_update)

    ui_parser = subparsers.add_parser("ui", help="open the drag-and-drop window")
    ui_parser.add_argument("--host", default="127.0.0.1")
    ui_parser.add_argument("--port", type=int, default=8765)
    ui_parser.add_argument("--no-browser", action="store_true")
    ui_parser.set_defaults(func=cmd_ui)

    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
