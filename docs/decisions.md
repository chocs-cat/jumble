# Decisions

Settled questions, so they aren't reopened by accident. Each entry says what
was decided and why, and is cited from the docs and the code as `(DEC-n)`.

- Add new entries at the end, numbered one past the greatest existing ID,
  with the month they were settled.
- To change one, discuss it first, then edit the entry in place (don't delete
  it): say what replaced it, when, and why, and update every doc and code site
  that cites it. Never give a changed decision a new ID.

Each entry has this shape:

```markdown
## DEC-1: <short title> (YYYY-MM)

What was decided and why, in a paragraph or two: the alternatives it rules
out and the reason they lost.

*Where:* the docs that carry the rule, if any.
```

## DEC-1: Randomness comes from `secrets` (2026-10)

jumble's strings are used as passwords and tokens, so every character is drawn
with `secrets.choice`. The `random` module is ruled out even for speed or
seeding in tests: its generator is predictable, and one stray use would make
output unfit for secrets without any visible sign. Tests check lengths and
alphabets rather than exact values.

*Where:* AGENTS.md (Conventions), `src/jumble/generate.py`.

## DEC-2: `symbols` is all ASCII punctuation (2026-10)

`symbols` is Python's `string.punctuation`, all 32 characters, quotes,
backtick, and backslash included. It replaced a 28-character subset that left
those four out to be friendlier to shells; the original `strings_aupif.py`
offered the full set, and a password field takes it. Someone who wants a
narrower set leaves `symbols` out and lists the characters with `--custom`.
Added during project P0001.

*Where:* docs/spec.md §2.1, `src/jumble/generate.py`.

## DEC-3: The look-alike set includes punctuation (2026-10)

`--no-ambiguous` removes ``0 O o l 1 I | ` ' " ; : . , -``, the set
`strings_aupif.py` used. It replaced `Il1O0o`, which ignored the punctuation
that is easy to misread or drop when copying by hand once `symbols` is on.
Added during project P0001.

*Where:* docs/spec.md §3.1, `src/jumble/generate.py`.

## DEC-4: A character is one code point (2026-10)

Every named set holds only single code points that are not control, format,
or combining characters, and emoji sets hold only code points with default
emoji presentation. `--custom` rejects control and combining characters. So
`length` counts code points and that matches what the user sees, with no
grapheme-cluster library. Multi-code-point emoji (skin tones, ZWJ sequences,
flags) are left out for that reason. Added during project P0001.

*Where:* docs/spec.md §2.1, §2.3.

## DEC-5: Overlapping sets are made disjoint in canonical order (2026-10)

When chosen sets share a character, it stays only in the first set in the
spec's canonical order, with `custom` last; a set left empty is an error. The
alphabet then holds each character once, so every character is equally
likely, and `--each` counts sets that can't share a pick. Silently dropping an
empty custom set was the alternative; it would hide a choice that does
nothing. Added during project P0001.

*Where:* docs/spec.md §2.4, §6.

## DEC-6: `--each` places one per set, then shuffles (2026-10)

A string under `--each` takes one character from each set, fills the rest
from the whole alphabet, and is shuffled. This is not exactly uniform over all
strings that meet the rule, but rejection sampling (draw until every set
appears) can take an unbounded number of draws when sets are small and the
length is close to the set count. Shuffles and samples are built on
`secrets.randbelow` rather than `secrets.SystemRandom`, so DEC-1 holds
literally. Added during project P0001.

*Where:* docs/spec.md §3, §3.3, `src/jumble/generate.py`.

## DEC-7: Strength and uniqueness ignore `--each` (2026-10)

The count of possible strings is *A^length*, or *A!/(A−length)!* without
repeats; the exact count under `--each` needs inclusion–exclusion over every
subset of sets, slow with many sets and long strings, and `--each`'s
place-and-shuffle draw is not uniform anyway. So strength is reported as an
upper bound when `--each` is on, and `--unique` checks feasibility against the
same count, then gives up after `max(100000, 20 × count)` draws. Added during
project P0001.

*Where:* docs/spec.md §3.4, §3.5, §4.2, §4.3.

## DEC-8: Generate everything, then write (2026-10)

The command line builds every string before writing any, instead of
streaming. A `--unique` run that gives up, or any failure, then writes nothing
and leaves no partial `-o` file. The cost is memory proportional to the
output, which is small at any count a person would ask for. Added during
project P0001.

*Where:* docs/spec.md §4.1.

## DEC-9: Characters are chosen as a whole (2026-10)

The default sets apply only when nothing chooses any characters, and a command
line that gives `-s` or `--custom` replaces the settings file's `charsets` and
`custom` together. Merging levels would make `jumble -s digits` still include
the file's custom characters, which surprises. Boolean flags only turn options
on; `--no-config` starts from the built-in defaults, instead of a `--no-X` pair
for every option. Added during project P0001.

*Where:* docs/spec.md §1, §5.2.

## DEC-10: One settings model, one settings file (2026-10)

The command line, the settings file, the TUI, and `--json` share eight setting
names (`length`, `count`, `charsets`, `custom`, `no_ambiguous`, `each`,
`no_repeat`, `unique`), held in one type in `jumble.generate`, so the front
ends can't drift. The file is TOML at `$JUMBLE_CONFIG`, else the XDG config
path, on macOS too, as corral does. Saves use tomlkit to keep comments and
change only what differs, and write through a symlink. Added during project
P0001.

*Where:* docs/spec.md §1, §5, AGENTS.md (Conventions).

## DEC-11: The TUI lists at most 1000 strings (2026-10)

A Textual list with hundreds of thousands of rows is slow to build and
useless to scroll, so the results pane shows the first 1000 and says how many
more there are. Copy all and save use every string. Added during project
P0001.

*Where:* docs/spec.md §7.1.

## DEC-12: The TUI has no Jumble button (2026-10)

As in corral, actions are single keys shown in the footer, which is also
clickable. Focus starts on the results pane so letter keys work; in an input,
`enter` jumbles and `escape` leaves. The earlier Jumble button existed only to
hold focus away from the length input. Added during project P0001.

*Where:* docs/spec.md §7.2, AGENTS.md (Testing notes).

## DEC-13: TUI saves never overwrite; `-o` does (2026-10)

The TUI's `s` names its file `jumble-<epoch>-<count>.txt` in the current
directory, after `strings_aupif.py`'s timestamped names, and refuses if the
file exists. A collision means a second save in the same second, and silently
replacing generated secrets would lose them. `-o FILE` is an explicit path
typed by the user and overwrites, like shell redirection. Added during project
P0001.

*Where:* docs/spec.md §4.1, §7.3.
