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

jumble's strings are used as passwords and tokens, so every draw, choice,
sample, and shuffle comes from the `secrets` module, built on
`secrets.randbelow` (DEC-6). The `random` module is ruled out even for speed or
seeding in tests: its generator is predictable, and one stray use would make
output unfit for secrets without any visible sign. Tests check lengths and
alphabets rather than exact values.

Amended 2026-10 at the review of P0001-C01: the first sentence named
`secrets.choice`, which contradicted DEC-6 and spec §3; the rule (`secrets`,
never `random`) is unchanged.

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

## DEC-14: A closed stdout pipe stops jumble quietly (2026-10)

When the reader of a pipe closes it early (`jumble -c 100000 | head -1`),
jumble exits 1 with nothing on stderr, as Unix tools that die of `SIGPIPE`
do; the reader got what it asked for, and a message would land in the middle
of the terminal output for no reason. Any other failed write to stdout (a full
disk behind a redirect) is `can't write stdout: REASON`, exit 1, the same
shape as a file's. Exit 141 (dying of the signal itself) was the alternative;
it needs a signal handler in Python and tells a script nothing that exit 1
doesn't. Added at the review of P0001-C02, which found the stdout path
reporting `can't write None`.

*Where:* docs/spec.md §4.1, §6.

## DEC-15: A TUI jumble that gives up is a toast, not the banner (2026-10)

`unique`'s give-up (§3.4) can't be checked before drawing, so it can happen
with controls that validate. The banner means "these controls can't produce
strings" and clears when a control changes; a give-up is the outcome of one
draw, and the same controls may succeed next time. So it is an error toast,
like corral's other outcomes, and the last result stays, so copying and saving
still have something to use. Raising it unhandled, as the first TUI did, quit
the app. Added at the review of P0001-C03.

*Where:* docs/spec.md §7.1.

## DEC-16: `jumble … tui` rejects only what the controls can't hold (2026-10)

Options before `tui` become the TUI's starting controls (§7.5). An unknown set
name has no checkbox to land on, so the command line rejects it with §6's
message and exit 2, as `jumble -s foo` would. Everything else (`-n 0`,
`--custom` with a combining character, an impossible `--unique` count) has a
control that can hold it, so the TUI starts with the banner shown and the
user fixes it there; rejecting those too would make the TUI the one place
those values can't be corrected. Added at the cut of P0001-C04.

*Where:* docs/spec.md §7.5.

## DEC-17: A settings file is checked key by key and fails whole (2026-10)

Reading the settings file stops at its first error, and the error is about
the file: the file's own syntax, or one key's name, type, or value under that
key's rule alone. Rules that relate settings to each other are checked on the
effective settings, because a file with `each = true` is fine until a command
line asks for `-n 2`. A file error stops the command line even when the
command line overrides the bad key: skipping bad keys, or ignoring them when
overridden, would let a typo sit unnoticed in the file. The TUI instead
starts as if `--no-config` were given and toasts the message, so the settings
screen can repair the file (§7.4). Messages share one shape, `PATH: KEY:
MESSAGE`, reusing §6's messages so they have one home. Collecting every error
at once was the alternative; a settings file has eight keys, and one error
at a time is what the command line does too. Added at the cut of P0001-C05.

*Where:* docs/spec.md §5.1, §5.2, §6, §7.4.

## DEC-18: A save repairs the file it writes, in place (2026-10)

A save (spec §5.3) keeps what it can of the existing file and replaces what
it can't use: unknown keys are removed, a wrong or different value is
replaced on its own line, a missing key is appended, and a file that isn't
UTF-8 or TOML is replaced by the template, since tomlkit can't keep the
layout of what it can't parse. That is how the settings screen repairs a
file the TUI started without (DEC-17). Refusing to save over a broken file
was the alternative; it would leave the TUI no way to fix one. The write is
in place, through a symlink, rather than a temporary file renamed over the
target: a rename would replace the link and reset the file's permissions,
and a settings file is small enough that a torn write is not worth that.
`d` refuses invalid controls, so a save never writes a file the command line
would then reject. Paths in messages are `pathlib`'s rendering, normalizing
`./` and doubled slashes (issue #14), so the command line, the toasts, and
the settings screen all show one form. Added at the review of P0001-C05.

*Where:* docs/spec.md §5.1, §5.3, §7.4.

## DEC-19: A save judges a file's TOML as reading does (2026-10)

A save (spec §5.3 step 1) keeps a file only when it is valid TOML to the
reader, `tomllib`, which §5.1 and §6 use; only then does tomlkit edit it.
tomlkit parses TOML 1.1, which the `tomllib` of Python 3.13 (TOML 1.0)
rejects: a file holding `custom = "\x41"` is `custom = "A"` to tomlkit, so a
save of `custom = "A"` would keep that line as equal and write a file the
command line refuses. Trusting tomlkit's parse alone was the alternative; a
save would then report success over a file that still breaks every run.
Added during P0001-C06-a.

*Where:* docs/spec.md §5.3.

## DEC-20: The settings screen edits the file, not the session (2026-10)

`d` saves the main screen's controls; `,` opens a form on the settings file
itself. So the form starts from the file's values over the built-in
defaults (spec §5.2 with no command line), not from the main screen, which
may carry options given before `tui`; filling it from the main screen
would make it `d` with extra steps. A file the TUI can't use fills the form
with the built-in defaults and shows its error, as at start, because the
form is the way to repair the file (DEC-17). The form uses the main
screen's controls and the banner's validation, so the two can't disagree
about what is valid; an invalid form is reported when Save is pressed, in
an error toast, as `d` reports invalid controls, rather than in a second
live banner. A successful Save replaces every main-screen control with the
saved values and doesn't jumble: as on the main screen, only a jumble
changes the results. `enter` in a form input saves, as a form's `enter`
submits; the main screen's keys don't act while the form is open, so
nothing reaches the main screen except through Save. Added at the cut of
P0001-C07.

*Where:* docs/spec.md §7.4.

## DEC-21: Bare `jumble` in a terminal opens the TUI (2026-10)

`jumble` typed alone at a prompt opens the TUI, because that is what a
person at a terminal with nothing more to say most likely wants; any
argument means the command line, which prints. The TUI opens only when
standard input and standard output are both terminals: the TUI needs both,
and `jumble | pbcopy`, `$(jumble)`, and scripts keep getting one printed
string, as they did. Ruled out: opening the TUI for any invocation without
output options (every printing use at a prompt would then need a flag),
opening it whenever stdout is a terminal (`echo | jumble` would start a TUI
with no keyboard), an error when piped (it would break the oldest use), and
a `--print` flag (any option already prints, `jumble -c 1` included).
`jumble tui` stays, as the way to open the TUI with starting options. Bare
`jumble` in a terminal used to print, so the change is marked breaking.
Added at the cut of P0001-C08, from issue #20.

*Where:* docs/spec.md §4, §7.

## DEC-22: The TUI shows a set's characters in a preview and a help screen (2026-10)

The TUI listed only set names, and with 18 sets, several of them Unicode
ranges, a name like `box` or `math` doesn't say what it draws (issue #18;
`strings_aupif.py` had a help panel for this). So a preview under the Sets
list shows the set under the list's cursor, with no key to press, and `?`
opens a help screen listing every set with its characters, and a note on each
other control, for reading them all at once. Both show the set as §2.1
defines it, whatever the other controls are: filtering it by `no_ambiguous`
or by overlaps with other chosen sets would make the preview change when an
unrelated control does, and the subtitle already reports the alphabet those
filters leave. Ruled out: tooltips (they need a mouse), a sample in each
list row (160 characters don't fit a 54-column pane), and the help screen
alone (a key press to learn what the cursor is already on). Added 2026-10-11, from issue #18.

*Where:* docs/spec.md §7.1, §7.2, §7.6.

## DEC-23: The settings screen pins its path and buttons (2026-10)

The settings dialog scrolled as a whole, so a path that wrapped pushed Save
and Cancel below the fold (issue #19), and the set preview (DEC-22) makes
the form taller still. Now the path and the buttons always show and only the
form scrolls. Cutting the path short from the left, to keep it on one line,
was the alternative; the path is the one thing the screen shows that the
main screen doesn't, and two deep paths can differ only in the part cut
away. Added 2026-10-11, from issue #19.

*Where:* docs/spec.md §7.4.

## DEC-24: Published as `jumble-cli` on PyPI and `jumble` in the chocs-cat tap (2026-10)

Releases go to PyPI and to the chocs-cat Homebrew tap as well as GitHub, so
`brew install chocs-cat/tap/jumble` works (issue #34), following
chocs-cat/tack: a trusted-publishing job uploads to PyPI, and a formula
built from the PyPI sdist, with each runtime dependency at the version the
release's `uv.lock` pins, goes to `chocs-cat/homebrew-tap`. The PyPI
distribution is `jumble-cli`, because `jumble` there is an unrelated 0.0.1;
the command, the import package, and the Homebrew formula stay `jumble`,
since homebrew/core has none. 0.1.0 is the first published version, so it
reaches GitHub, PyPI, and the tap together.

The build backend moves from `uv_build` to `hatchling`. Homebrew installs a
formula's resources with `pip --no-binary=:all:` and build isolation, so the
backend itself is built from source: `uv_build` is a Rust crate, `hatchling`
pure Python, and tack's and corral's formulas already install with it. The
formula's test runs `jumble --version`, which the command lacked, so it gains
one, printing the version the TUI header shows.

*Where:* docs/spec.md §4, §7.1; README.md *Install*; AGENTS.md *Releases*.

## DEC-25: The set preview is inset one column, inside the controls' borders (2026-10)

The set preview (DEC-22) began at the controls pane's left edge, under the
left border of the bordered Sets list and Custom input, so it read as
outside them (issue #31). Now one column of padding at each side starts its
text in the first column inside those borders. Insetting it to the list's
checkboxes (two columns) or to the `Sets` and `Custom` titles and the typed
custom text (three) were the alternatives; each costs more width, and the
first column inside the borders is the one edge the boxes share. A
border or vertical padding is ruled out: at 100 × 30 the pane has no spare
row. Four lines still hold `box` and `emoji-faces` at the 51 columns left on
the main screen and the 50 in the settings form. Added 2026-10-28, from
issue #31.

*Where:* docs/spec.md §7.1, §7.6.

## DEC-26: The settings dialog fits its contents on a tall terminal (2026-10)

The layout that pins the settings dialog's path and buttons (DEC-23) also
stretched the form to the terminal's height, so on a terminal taller than
the dialog needs, blank rows sat between the last option and Save and
Cancel: five at 100 × 40 with a two-line path (issue #29). Now the dialog is only as tall as its
contents, and the pinning holds when it isn't tall enough. Filling the
height was the alternative; it leaves the buttons away from the form they
act on, for no gain.

No Textual 8.2.8 stylesheet does both (#29 lists the shapes probed), so the
form's height follows its contents up to a cap the screen sets: the rows the
path and the buttons leave, recomputed on every resize. Added 2026-10-28,
from issue #29.

*Where:* docs/spec.md §7.4.
