# Project P0001 — full generator

- **State:** active
- **Created:** 2026-10-06
- **Ready:** 2026-10-06
- **Completed:** —
- **Decisions:** DEC-2 – DEC-13

## 1. Problem and outcome

jumble does one thing: strings of a given length from four ASCII sets, with
an optional look-alike filter, printed or shown in a small TUI. The author's
older script, `strings_aupif.py` in their `media-scripts` repo (a Textual TUI, with
the prompt-driven `random_strings.py` beside it), does more, and jumble
should replace it: a space set and custom characters, at least one character
from each set, no repeats within a string, unique strings across the output,
a count, file output, a preview, and a summary. It also draws with
`random.SystemRandom`, which jumble rules out (DEC-1).

Beyond that parity, the user asked for named Unicode sets (games, emoji,
letters, symbols), a strength readout, `--json` output, and saved defaults
edited from the TUI, both by saving the current controls and from a settings
screen. The TUI is rebuilt on the design habits of the author's `corral`
TUI: a one-line header with a dim subtitle, a controls pane beside a results
pane, an error banner shown only when needed, toasts, single-key actions in
the footer, and all behavior in shared code.

**Outcome:** everything `strings_aupif.py` does can be done with `jumble` or
`jumble tui`, under the rules of `docs/spec.md`, and a user's preferred
settings persist between runs.

It is one project because every feature rides on one settings model shared by
the command line, the TUI, the settings file, and `--json` (DEC-10); built
piecemeal, the front ends would each invent their own.

No issues existed for this work; it came straight from the user.

## 2. Boundaries

In scope: everything in `docs/spec.md` §1–§7.

Not in scope:

- Retiring or editing the scripts in `media-scripts`; that is the user's call
  once jumble covers them.
- Multi-code-point emoji (skin tones, ZWJ sequences, flags) (DEC-4).
- Word-based passphrases, pronounceable strings, or any generator other than
  characters drawn from sets.
- Publishing to PyPI or Homebrew.
- aupif's always-written output file and its "clear preview" key: output to a
  file is opt-in (`-o`, the TUI's `s`), and each jumble replaces the list.

Compatibility: pre-1.0, so breaking changes are minor bumps, but they are
marked. `symbols` widens to all ASCII punctuation (DEC-2) and `-a` removes
more characters (DEC-3), so the same command can produce strings it couldn't
before; the chunk that lands them is titled `feat!`. Existing flags (`-n`,
`-c`, `-s`, `-a`, `tui`) keep their meaning. `jumble.generate(length,
charsets, exclude_ambiguous=…)` may change shape; it has no users outside this
repo.

## 3. Design questions

| Question | Resolution | Authority / decision | State |
|---|---|---|---|
| Which look-alikes does `-a` drop? | aupif's wider set, with punctuation | spec §3.1, DEC-3 | resolved |
| What is in `symbols`? | all of `string.punctuation` | spec §2.1, DEC-2 | resolved |
| Which new sets, with which exact characters? | space, plus 13 curated Unicode sets; exact ranges listed | spec §2.1 | resolved |
| What does length count with Unicode? | code points; sets and custom exclude control, format, combining | spec §2.1, §2.3, DEC-4 | resolved |
| How are custom characters chosen and checked? | `--custom CHARS`, its own set, last; deduped; control and combining rejected | spec §2.3, DEC-4 | resolved |
| What if sets overlap or a set ends up empty? | disjoint in canonical order; an empty set is an error | spec §2.4, DEC-5 | resolved |
| How is `--each` drawn? | one per set, fill, shuffle; built on `secrets.randbelow` | spec §3.3, DEC-6 | resolved |
| How does `--unique` fail? | upfront count check, then a draw cap | spec §3.4, DEC-7 | resolved |
| How is strength computed with `--each`? | ignored; reported as an upper bound | spec §3.5, DEC-7 | resolved |
| Stream output or build first? | build every string, then write; failures write nothing | spec §4.1, DEC-8 | resolved |
| Does `-o` overwrite? Does TUI save? | `-o` overwrites; TUI save never does | spec §4.1, §7.3, DEC-13 | resolved |
| Shape of `--json`; are errors JSON? | one object with strings, alphabet size, strength, settings; errors are not JSON | spec §4.2 | resolved |
| How does the CLI show strength? | `--strength` to stderr | spec §4.3 | resolved |
| CLI flag names for the new options | `-e/--each`, `-r/--no-repeat`, `-u/--unique`, `--custom`, `-o`, `--json`, `--strength`, `--no-config`; `-s` takes commas | spec §4 | resolved |
| When do the default sets apply? | only when nothing chooses characters | spec §1, §5.2, DEC-9 | resolved |
| Settings file path, format, unknown keys | `$JUMBLE_CONFIG` or XDG path, TOML, same names; unknown key is an error | spec §5.1, DEC-10 | resolved |
| Precedence, and turning a file-set boolean off | defaults < file < CLI; characters as a whole; `--no-config` | spec §5.2, DEC-9 | resolved |
| How does saving treat the existing file? | tomlkit, keep comments, change only differences, through symlinks | spec §5.3, DEC-10 | resolved |
| Invalid settings file | CLI: error, exit 2; TUI: built-in defaults plus a toast | spec §5.1, §6, §7.4 | resolved |
| Validation messages and exit codes | fixed table, checked in order; exit 2, or 1 for write failures | spec §6 | resolved |
| TUI layout and keys | corral-style; keys g c a s d , q | spec §7.1, §7.2 | resolved |
| How are letter keys kept working? | focus on results; enter/escape leave inputs; no button | spec §7.2, DEC-12 | resolved |
| How many strings does the TUI show? | first 1000; copy all and save use all | spec §7.1, DEC-11 | resolved |
| Save defaults from the main screen, a settings screen, or both? | both: `d` and `,` | spec §7.4 | resolved |
| What does the TUI start from? | effective settings, including options before `tui` | spec §7.5 | resolved |
| Where does code live? | `generate.py` owns sets, settings type, validation, generation, strength; `config.py` owns the file | AGENTS.md Conventions, DEC-10 | resolved |

## 4. Authority changes

| Document and section | Change | Why this is the durable home |
|---|---|---|
| `docs/spec.md` (new), §1–§7 | The full behavior: settings, sets, options, CLI, settings file, errors, TUI | Behavior now spans two front ends and a file format; README is a user guide and can't carry exact ranges, messages, and precedence. It outlives the project as the first authority. |
| AGENTS.md, opening paragraph, *Workflow*, *Relay workflow → Authority* | Names `docs/spec.md` as the first authority and keeps it in step with README and help | The authority order is a relay setting. |
| AGENTS.md, *Conventions* | Module ownership: `generate.py` and new `config.py` | An implementation boundary every chunk shares. |
| AGENTS.md, *Testing notes* | TUI focus starts on the results pane; tests isolate the settings file with `$JUMBLE_CONFIG` | Every TUI and config test depends on these. |
| `docs/decisions.md`, DEC-2 – DEC-13 | The choices behind the spec | Where the docs left a real choice. |
| `docs/spec.md` §2.2, §6 (at the cut of P0001-C01) | An empty `-s` name is an error and `custom` is not a set name; §6 numbers are plain integers; the CLI's validation error is one line with no usage | Questions the C01 executor would otherwise have decided. |
| `docs/decisions.md` DEC-1 (at the review of P0001-C01) | Amended in place: draws are built on `secrets.randbelow`, not `secrets.choice` | It contradicted DEC-6 and spec §3. |
| `docs/spec.md` §4, §4.1, §4.2, §4.3, §6 (at the cut of P0001-C02) | The `tui` misuse message; UTF-8 stdout whatever the locale and `-o -`; JSON key order, rounding, `charsets`/`custom` values, and formatting; the strength line's singular, decimals, and timing; `REASON` in the write error | Questions the C02 executor would otherwise have decided. |

README.md is not changed by this planning work: it stays true to the shipped
behavior, and each chunk updates it with the behavior it lands.

## 5. Delivery plan

These are ordered outcomes, not pre-sized chunks. `/relay-next` may keep one
item in one chunk or split it where reviewability requires.

### D1 — settings model, sets, and generation options

**Build:** in `generate.py`, the shared settings type (spec §1, DEC-10), every
named set of spec §2.1 with its canonical order, custom characters (§2.3), the
alphabet build (§2.4), validation with the §6 messages and order, and
generation with `no_ambiguous`, `no_repeat`, `each`, and `unique` (§3.1–§3.4),
plus strength (§3.5). On the command line: `-s` with commas, `--custom`,
`-e`, `-r`, `-u`, and the widened `symbols` and look-alikes (DEC-2, DEC-3).
README and help text gain the sets table and the new options. The pull
request is titled `feat!`.

**Depends on:** none.

**Done when:** tests show each named set has exactly the spec's characters and
size, and none is a control, format, or combining character; overlap and empty
set rules (DEC-5) hold, including `--custom abc -s lower`; every §6 message
fires for its condition, in the stated order; `no_repeat` strings have no
repeated character and `length = A` succeeds while `A + 1` fails; `each`
strings contain a character of every set, at `length = k`, too; `unique` output
has no duplicates, the impossible count fails before drawing, and the draw cap
fails with its message (a tiny alphabet makes this testable); strength matches
*log₂ P* for both formulas; no code imports `random` (a test greps `src/`);
`jumble --custom abc` uses only `abc`.

### D2 — command-line output

**Build:** generate-then-write (§4.1, DEC-8), `-o FILE` and `-o -`, `--json`
(§4.2), `--strength` (§4.3), the exit codes of §6, and the error for `-o`,
`--json`, or `--strength` with `tui`. README and help text.

**Depends on:** D1.

**Done when:** tests show `-o` writes UTF-8 lines and overwrites; a failing
`--unique` run with `-o` leaves no file and prints nothing to stdout; `--json`
parses and has exactly the §4.2 keys, with `charsets` in canonical order and
`strength_is_bound` following `each`; `--strength` writes the §4.3 line to
stderr only; an unwritable path exits 1 with the §6 message; validation errors
exit 2.

### D3 — the rebuilt TUI

**Build:** the layout, header, controls, results pane, error banner, keys,
focus rules, and string saving of spec §7.1–§7.3 (DEC-11, DEC-12, DEC-13),
and starting values from command-line options given before `tui` (§7.5,
without the settings file yet). `d` and `,` are not built here. README's TUI
section and keys table.

**Depends on:** D1.

**Done when:** pilot tests show `g` jumbles with the controls' settings; an
invalid control shows the §6 message in the banner, empties the subtitle, and
makes `g` do nothing; the subtitle reads as §4.3 and updates on change;
`enter` in an input jumbles and focuses the results pane, `escape` only
focuses it; with count 1500 the pane has 1000 strings and the `… and 500 more`
row while copy all and save carry 1500; `s` writes the named file into a
`tmp_path` working directory and refuses when it exists; `c` copies the
highlighted string; `jumble -n 32 -s digits tui` starts with those controls.
A screenshot (`app.save_screenshot`) is attached to the pull request.

### D4 — reading the settings file

**Build:** `config.py` loading from the §5.1 path, validating keys, types, and
values (§5.1, §6), and the precedence of §5.2 (DEC-9) including `--no-config`.
The CLI and the TUI start from the effective settings; the TUI falls back to
built-in defaults with a toast on an invalid file (§7.4). README documents the
file.

**Depends on:** D1, D2, D3.

**Done when:** tests (with `$JUMBLE_CONFIG` on a `tmp_path` file) show the
path resolution order; a missing file gives built-in defaults; an unknown key,
a wrong type, and an unknown set each exit 2 naming the file and key; file
values apply, CLI values override them key by key, `-s` or `--custom` drops
both of the file's character keys, and `--no-config` ignores the file; the TUI
starts from the file's values, and from built-in defaults with a toast when
it is invalid.

### D5 — saving settings from the TUI

**Build:** saving in `config.py` per §5.3 (tomlkit, a new dependency), the
`d` key, and the `,` settings screen with Save and Cancel (§7.4). README.

**Depends on:** D4.

**Done when:** tests show a save to a new file starts from the commented
template with all eight keys; a save to a commented file changes only the
differing values and keeps the comments; a save with nothing changed leaves
the file byte-identical; a symlinked file is written through the link; `d`
writes the current controls; the settings screen loads the file, rejects an
invalid value with its §6 message, saves, closes, and updates the main
controls; Cancel and `escape` change nothing; main-screen keys do nothing
while the screen is open.

## 6. Project completion

- A parity check against `strings_aupif.py`, recorded in Closeout: each of its
  features (sets, custom, look-alikes, each, no repeats, unique, count,
  length, file output, preview, summary as strength) has a jumble route.
- README.md, `jumble --help`, and `docs/spec.md` agree; every spec section is
  covered by a delivery item's tests.
- `make check` passes on `master` after the last chunk.
- A manual run of `jumble tui` in a real terminal with an emoji set and the
  settings screen, noted in the last chunk's review.

## 7. Chunk ledger

| Chunk | Delivery items | State | Review | Integrated identity |
|---|---|---|---|---|
| P0001-C01 | D1 | accepted with follow-ups | 2026-10-06 | PR #7 |
| P0001-C02 | D2 | ready for an executor | — | — |

## 8. Closeout

Fill this only when completing or abandoning the project.

- **Outcome:** —
- **Accepted chunks:** —
- **Changelog entries:** —
- **Derived release effect:** —
- **Unfinished or deliberately excluded:** —
- **Decisions added or reopened:** —
