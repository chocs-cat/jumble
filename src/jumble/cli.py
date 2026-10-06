"""The `jumble` command."""

import argparse
from collections.abc import Sequence

from jumble.generate import CHARSETS, Settings, generate

DEFAULT_CHARSETS = ["lower", "upper", "digits"]


def parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="jumble", description="Generate random strings.")
    p.add_argument(
        "-n", "--length", type=int, default=16, help="characters per string (default 16)"
    )
    p.add_argument(
        "-c", "--count", type=int, default=1, help="how many strings to print (default 1)"
    )
    p.add_argument(
        "-s",
        "--charset",
        action="append",
        choices=sorted(CHARSETS),
        help="character set to draw from; repeat for more (default: lower, upper, digits)",
    )
    p.add_argument(
        "-a", "--no-ambiguous", action="store_true", help="leave out look-alike characters (Il1O0o)"
    )
    sub = p.add_subparsers(dest="command")
    sub.add_parser("tui", help="open the interactive generator")
    return p


def main(argv: Sequence[str] | None = None) -> int:
    args = parser().parse_args(argv)
    if args.command == "tui":
        from jumble.tui import JumbleApp

        JumbleApp().run()
        return 0
    settings = Settings(
        length=args.length,
        count=args.count,
        charsets=tuple(args.charset or DEFAULT_CHARSETS),
        no_ambiguous=args.no_ambiguous,
    )
    try:
        for line in generate(settings):
            print(line)
    except ValueError as e:
        parser().error(str(e))
    return 0
