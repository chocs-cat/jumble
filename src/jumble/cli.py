"""The `jumble` command (docs/spec.md §4)."""

import argparse
import json
import os
import sys
from collections.abc import Mapping, Sequence
from typing import Any

from jumble.config import config_path, file_settings, load
from jumble.generate import (
    CHARSETS,
    LOOK_ALIKES,
    JumbleError,
    Settings,
    Strength,
    check_names,
    generate,
    settings_dict,
    strength,
    strength_line,
)

DEFAULTS = Settings()

# The settings a command-line flag can only turn on (§5.2, DEC-9).
BOOLEANS = ("no_ambiguous", "each", "no_repeat", "unique")


def parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="jumble", description="Generate random strings.")
    # -n, -c, and --custom default to None, so an option given at its default
    # value still overrides the settings file (§5.2).
    p.add_argument(
        "-n",
        "--length",
        type=int,
        metavar="N",
        help=f"characters per string (default {DEFAULTS.length})",
    )
    p.add_argument(
        "-c",
        "--count",
        type=int,
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
        f"(default: {', '.join(DEFAULTS.charsets)}, when neither --custom nor the "
        "settings file chooses characters)",
    )
    p.add_argument(
        "--custom",
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
    p.add_argument(
        "--no-config",
        action="store_true",
        help=f"ignore the settings file ({config_path()})",
    )
    sub = p.add_subparsers(dest="command")
    sub.add_parser(
        "tui",
        # It starts from the effective settings, the file's included (§7.5).
        help="open the interactive generator, starting from the settings file and the "
        "options before tui (not with --output, --json, or --strength)",
        description="Open the interactive generator. It starts from the settings file, "
        "and options given before tui override it, for example: jumble -n 32 -s digits tui",
    )
    return p


def settings_from(args: argparse.Namespace, file: Mapping[str, Any]) -> Settings:
    """One `Settings` from parsed arguments over the settings file's keys (§5.2, DEC-9).

    Built-in defaults, then `file` (what `config.load` returned, or `{}`), then
    the command line. `length`, `count`, and the booleans go key by key; an
    option counts when it is given, even at its default value, and a flag
    only turns its option on. The characters go as a whole: `-s` or
    `--custom` (even `--custom ''`) replaces both of the file's `charsets` and
    `custom`. The default sets apply only when no level chose any. The
    command line is laid over the file's keys and merged by
    `config.file_settings`, so there is one merge.
    """
    values = dict(file)
    for key in ("length", "count"):
        if getattr(args, key) is not None:
            values[key] = getattr(args, key)
    for key in BOOLEANS:
        if getattr(args, key):
            values[key] = True
    names = tuple(name for value in args.charset for name in value.split(","))
    if names or args.custom is not None:
        values["charsets"], values["custom"] = names, args.custom or ""
    return file_settings(values)


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
        file_error = None
        try:
            file = {} if args.no_config else load(config_path())
        except JumbleError as e:
            # The TUI starts as if --no-config were given and toasts the
            # message, so the file can be repaired from there (§7.4, DEC-17).
            file, file_error = {}, str(e)
        settings = settings_from(args, file)
        try:
            # Only a name no checkbox can hold stops the TUI; any other bad
            # value starts it with the banner shown (§7.5, DEC-16).
            check_names(settings.charsets)
        except JumbleError as e:
            print(f"jumble: error: {e}", file=sys.stderr)
            return 2
        from jumble.tui import JumbleApp

        JumbleApp(settings, file_error=file_error).run()
        return 0
    # Generate everything before opening any output, so a failed run writes
    # nothing and leaves an existing -o file as it was (§4.1, DEC-8).
    try:
        # A broken file stops the run even where the command line overrides
        # the bad key (§5.1, DEC-17); --no-config doesn't read it at all.
        file = {} if args.no_config else load(config_path())
        settings = settings_from(args, file)
        strings = generate(settings)
    except JumbleError as e:
        # The message is the whole output, with no usage line (§6).
        print(f"jumble: error: {e}", file=sys.stderr)
        return 2
    # After generate, so a failed run's error is generate's.
    st = strength(settings)
    text = json_output(strings, settings, st) if args.json else "".join(f"{s}\n" for s in strings)
    data = text.encode()
    to_stdout = args.output is None or args.output == "-"
    try:
        write_output(args.output, data)
    except OSError as e:
        if not to_stdout:
            print(f"jumble: error: can't write {args.output}: {e.strerror}", file=sys.stderr)
        elif isinstance(e, BrokenPipeError):
            # The reader closed the pipe and got what it asked for: exit quietly (§6, DEC-14).
            quiet_stdout()
        else:
            print(f"jumble: error: can't write stdout: {e.strerror}", file=sys.stderr)
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


def quiet_stdout() -> None:
    """Point fd 1 at the null device after a closed pipe (DEC-14).

    Stdout's buffer may still hold bytes; the flush at interpreter exit then
    has somewhere to go instead of printing `Exception ignored … BrokenPipeError`.
    This is the recipe in the Python `signal` docs' note on SIGPIPE.
    """
    devnull = os.open(os.devnull, os.O_WRONLY)
    os.dup2(devnull, sys.stdout.fileno())
