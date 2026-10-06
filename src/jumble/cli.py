"""The `jumble` command (docs/spec.md §4)."""

import argparse
import json
import sys
from collections.abc import Sequence

from jumble.generate import (
    CHARSETS,
    LOOK_ALIKES,
    JumbleError,
    Settings,
    Strength,
    generate,
    settings_dict,
    strength,
    strength_line,
)

DEFAULTS = Settings()


def parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="jumble", description="Generate random strings.")
    p.add_argument(
        "-n",
        "--length",
        type=int,
        default=DEFAULTS.length,
        metavar="N",
        help=f"characters per string (default {DEFAULTS.length})",
    )
    p.add_argument(
        "-c",
        "--count",
        type=int,
        default=DEFAULTS.count,
        metavar="N",
        help=f"how many strings (default {DEFAULTS.count})",
    )
    # No argparse choices: validation reports unknown and empty names (§2.2, §6).
    p.add_argument(
        "-s",
        "--charset",
        action="append",
        default=[],
        metavar="NAME[,NAME...]",
        help="character sets to draw from; repeat or separate with commas. "
        f"Sets: {', '.join(CHARSETS)} "
        f"(default: {', '.join(DEFAULTS.charsets)}, when no --custom is given)",
    )
    p.add_argument(
        "--custom",
        default="",
        metavar="CHARS",
        help="also draw from these characters, as one more set",
    )
    p.add_argument(
        "-a",
        "--no-ambiguous",
        action="store_true",
        help=f"leave out look-alike characters: {' '.join(LOOK_ALIKES)}",
    )
    p.add_argument(
        "-e", "--each", action="store_true", help="at least one character from every chosen set"
    )
    p.add_argument(
        "-r", "--no-repeat", action="store_true", help="no character twice within a string"
    )
    p.add_argument("-u", "--unique", action="store_true", help="no string twice in the output")
    # Default None, so `-o -` can be told apart from no -o (§4).
    p.add_argument(
        "-o",
        "--output",
        metavar="FILE",
        help="write to FILE, created or overwritten, instead of stdout; - means stdout",
    )
    p.add_argument(
        "--json",
        action="store_true",
        help="write one JSON object with the strings, their strength, and the settings used",
    )
    p.add_argument(
        "--strength",
        action="store_true",
        help="also print the alphabet size and bits per string to stderr",
    )
    sub = p.add_subparsers(dest="command")
    sub.add_parser(
        "tui", help="open the interactive generator (not with --output, --json, or --strength)"
    )
    return p


def settings_from(args: argparse.Namespace) -> Settings:
    """One `Settings` from parsed arguments (§1, §2.2)."""
    charsets = tuple(name for value in args.charset for name in value.split(","))
    if not charsets and not args.custom:
        # Nothing chose any characters, so the default sets apply (§1, DEC-9).
        charsets = DEFAULTS.charsets
    return Settings(
        length=args.length,
        count=args.count,
        charsets=charsets,
        custom=args.custom,
        no_ambiguous=args.no_ambiguous,
        each=args.each,
        no_repeat=args.no_repeat,
        unique=args.unique,
    )


def main(argv: Sequence[str] | None = None) -> int:
    p = parser()
    args = p.parse_args(argv)
    if args.command == "tui":
        # Before the TUI starts or any file is touched; -o - counts as given (§4, §6).
        misused = (
            ("--output", args.output is not None),
            ("--json", args.json),
            ("--strength", args.strength),
        )
        for option, given in misused:
            if given:
                p.error(f"{option} can't be used with tui")
        from jumble.tui import JumbleApp

        JumbleApp().run()
        return 0
    # Generate everything before opening any output, so a failed run writes
    # nothing and leaves an existing -o file as it was (§4.1, DEC-8).
    settings = settings_from(args)
    try:
        strings = generate(settings)
    except JumbleError as e:
        # The message is the whole output, with no usage line (§6).
        print(f"jumble: error: {e}", file=sys.stderr)
        return 2
    # After generate, so a failed run's error is generate's.
    st = strength(settings)
    text = json_output(strings, settings, st) if args.json else "".join(f"{s}\n" for s in strings)
    data = text.encode()
    try:
        write_output(args.output, data)
    except OSError as e:
        print(f"jumble: error: can't write {args.output}: {e.strerror}", file=sys.stderr)
        return 1
    if args.strength:
        # After the output, and only for a run that succeeded (§4.3).
        print(strength_line(st), file=sys.stderr)
    return 0


def json_output(strings: list[str], settings: Settings, st: Strength) -> str:
    """The §4.2 object for `strings`, drawn from `settings` of strength `st`, and a newline."""
    obj = {
        "strings": strings,
        "alphabet_size": st.alphabet_size,
        "strength_bits": round(st.bits, 1),
        "strength_is_bound": st.is_bound,
        "settings": settings_dict(settings),
    }
    return json.dumps(obj, indent=2, ensure_ascii=False) + "\n"


def write_output(path: str | None, data: bytes) -> None:
    """Write `data` to stdout when `path` is None or `-`, else to the file `path` (§4.1).

    Stdout gets the bytes through its binary buffer, so output is UTF-8 whatever
    the locale's encoding.
    """
    if path is None or path == "-":
        sys.stdout.flush()
        sys.stdout.buffer.write(data)
        sys.stdout.buffer.flush()
        return
    with open(path, "wb") as f:
        f.write(data)
