# jumble specification

How jumble behaves: its character sets, options, output, settings file, and
terminal UI. This is the first authority for behavior (AGENTS.md, *Relay
workflow*); README.md is the user guide drawn from it, and the CLI help text and
docstrings follow both. Decisions behind the rules are cited as `(DEC-n)` from
`docs/decisions.md`.

## 1. Settings

One set of settings drives every front end. The command line, the settings
file, the TUI, and `--json` output use the same names (DEC-10):

| Setting | Type | Default | Meaning |
|---|---|---|---|
| `length` | integer ≥ 1 | 16 | characters per string |
| `count` | integer ≥ 1 | 1 | how many strings |
| `charsets` | list of set names | `["lower", "upper", "digits"]` | the named sets to draw from (§2) |
| `custom` | string | `""` | extra characters, as their own set (§2.3) |
| `no_ambiguous` | boolean | false | leave out look-alike characters (§3.1) |
| `each` | boolean | false | at least one character from every chosen set (§3.3) |
| `no_repeat` | boolean | false | no character twice within a string (§3.2) |
| `unique` | boolean | false | no string twice in the output (§3.4) |

The default `charsets` apply only when no characters are chosen at all, that
is, when both `charsets` and `custom` are empty at every level (§5.2) (DEC-9).

## 2. Character sets

### 2.1 Named sets

Sets are listed here in their **canonical order**, which fixes the order of
the alphabet and decides overlaps (§2.4). Every character in every set is a
single Unicode code point that is neither a control, format, nor combining
character, so a string's length is the number of characters it shows (DEC-4).

| Name | Characters | Size |
|---|---|---|
| `lower` | `a`–`z` | 26 |
| `upper` | `A`–`Z` | 26 |
| `digits` | `0`–`9` | 10 |
| `symbols` | all ASCII punctuation, ``!"#$%&'()*+,-./:;<=>?@[\]^_`{\|}~`` (Python's `string.punctuation`) (DEC-2) | 32 |
| `space` | the space character, U+0020 | 1 |
| `chess` | U+2654–U+265F (♔…♟) | 12 |
| `cards` | the 52 standard playing cards: U+1F0A1–U+1F0AE, U+1F0B1–U+1F0BE, U+1F0C1–U+1F0CE, U+1F0D1–U+1F0DE, each range without its knight (U+1F0AC, U+1F0BC, U+1F0CC, U+1F0DC) | 52 |
| `dice` | U+2680–U+2685 (⚀…⚅) | 6 |
| `emoji-faces` | U+1F600–U+1F64F (😀…🙏) | 80 |
| `emoji-animals` | U+1F400–U+1F43E (🐀…🐾) | 63 |
| `emoji-food` | U+1F345–U+1F37B (🍅…🍻) | 55 |
| `greek` | U+0391–U+03A9 without U+03A2, then U+03B1–U+03C9 without final sigma U+03C2 (Α…Ω, α…ω) | 48 |
| `cyrillic` | U+0410–U+044F (А…я) | 64 |
| `latin-accented` | U+00C0–U+00FF without × U+00D7 and ÷ U+00F7 (À…ÿ) | 62 |
| `arrows` | U+2190–U+2199 (←…↙) | 10 |
| `math` | `±×÷∞≠≈≤≥√∑∏∫∂∆∇∈∉∩∪⊂⊃∀∃¬∧∨`, in that order | 26 |
| `currency` | `¢£¥€₹₽₩₪₺₿₫₱`, in that order | 12 |
| `box` | U+2500–U+259F, box drawing and block elements (─…▟) | 160 |

Emoji sets hold only single code points with default emoji presentation: no
skin-tone modifiers, variation selectors, or joined (ZWJ) sequences (DEC-4).
How a terminal draws wide characters is the terminal's business; jumble
counts code points.

### 2.2 Choosing sets

On the command line, `-s/--charset NAME` chooses a set; repeat it, or separate
names with commas (`-s lower,digits`). Order and repetition don't matter. An
unknown name is an error (§6), and so is an empty one (`-s lower,`). `custom`
is not a named set; custom characters come only from `--custom`.

### 2.3 Custom characters

`--custom CHARS` (the `custom` setting) adds the characters of `CHARS` as one
more set, named `custom`, placed after every named set. Repeated characters
count once and keep their first position. Each code point is one character.
A control (Unicode category `Cc`, `Cf`, `Cs`, `Co`, `Cn`) or combining (`M*`)
character in `CHARS` is an error (§6) (DEC-4).

### 2.4 Building the alphabet

From the chosen sets, in canonical order with `custom` last:

1. When `no_ambiguous` is on, remove the look-alike characters (§3.1) from
   every set.
2. Make the sets disjoint: a character that is in more than one chosen set
   stays only in the first (DEC-5).
3. If any chosen set is now empty, that is an error (§6). (Only `custom` can
   empty this way, for example `--custom abc` with `lower` chosen.)
4. The **alphabet** is the sets' characters joined in that order. Its size is
   written *A* below.

## 3. Options

Randomness, including every choice, sample, and shuffle, comes from the
`secrets` module; shuffles and samples are built on `secrets.randbelow`
(DEC-1, DEC-6).

### 3.1 No look-alikes (`-a`, `--no-ambiguous`)

Removes these characters: ``0 O o l 1 I | ` ' " ; : . , -`` (DEC-3).

### 3.2 No repeats (`-r`, `--no-repeat`)

No character appears twice within one string. Requires *length ≤ A*.

### 3.3 One from each set (`-e`, `--each`)

Every chosen set, `custom` included, contributes at least one character to
every string. Requires *length ≥* the number of chosen sets. A string is made
by drawing one character from each set, filling the rest from the whole
alphabet (without already-drawn characters when `no_repeat` is on), and
shuffling (DEC-6).

### 3.4 Unique strings (`-u`, `--unique`)

No string appears twice in the output. A string that repeats an earlier one is
drawn again. If *count* exceeds the number of possible strings (§3.5), that is
an error before anything is drawn; if `max(100000, 20 × count)` draws pass
without reaching *count* distinct strings, generation stops with an error (§6)
(DEC-7).

### 3.5 Strength

The number of possible strings, *P*, is *A^length* with repeats allowed and
*A! / (A − length)!* with `no_repeat`. Strength is *log₂ P* bits per string,
reported to one decimal place. It ignores `each`, so with `each` on it is an
upper bound and is reported as such (DEC-7).

## 4. Command line

```text
jumble                    in a terminal, open the TUI (§7); otherwise as below
jumble [options]          generate and print strings
jumble [options] tui      open the TUI, starting from these options (§7)
jumble --version          print the version
```

`jumble` with no arguments at all opens the TUI, exactly as `jumble tui`
does (§7.5), when its standard input and its standard output are both
terminals. When either is not (`jumble | pbcopy`, `$(jumble)`, a script, a
cron job), it prints as `jumble [options]` does with no options. Any argument
at all, `--no-config` or `-c 1` included, means `jumble [options]`, which
always prints; `jumble [options] tui` always opens the TUI. The arguments are
the ones `main` is given, or `sys.argv[1:]` when it is given none, the same
list argparse parses (DEC-21).

| Option | Setting / effect |
|---|---|
| `-n`, `--length N` | `length` |
| `-c`, `--count N` | `count` |
| `-s`, `--charset NAME[,NAME…]` | `charsets` (§2.2) |
| `--custom CHARS` | `custom` (§2.3) |
| `-a`, `--no-ambiguous` | `no_ambiguous` |
| `-e`, `--each` | `each` |
| `-r`, `--no-repeat` | `no_repeat` |
| `-u`, `--unique` | `unique` |
| `-o`, `--output FILE` | write to `FILE` instead of stdout (§4.1); `-` means stdout |
| `--json` | write JSON instead of lines (§4.2) |
| `--strength` | also print the strength line to stderr (§4.3) |
| `--no-config` | ignore the settings file (§5) |
| `--version` | print `jumble <version>` and exit |

`--version` writes `jumble <version>` and a newline to stdout and exits 0,
where `<version>` is the installed package's version,
`importlib.metadata.version("jumble-cli")` (DEC-24). It acts when argparse
reaches it, before any settings file is read, so a broken file doesn't stop
it: arguments after it are never looked at, while an error in one before it
(`jumble -n x --version`) is reported as usual. It is an option of `jumble`,
not of `tui`, so `jumble tui --version` is an unrecognized argument. Being an
argument, it never opens the TUI.

`-o`, `--json`, and `--strength` are errors with `tui` (§6): the message is
`OPTION can't be used with tui`, naming the first one given of `--output`,
`--json`, and `--strength`, in that order, by its long name.

### 4.1 Output

jumble generates every string before writing anything, so a failed run writes
nothing and never leaves a partial file (DEC-8). Lines output is each string
followed by `\n`. Output is UTF-8 on stdout as in a file, whatever the
locale's encoding. `-o FILE` creates or overwrites `FILE`, as shell
redirection would; `-o -` is stdout. A failed write is an error (§6); when
stdout is a pipe whose reader has closed it (`jumble -c 100000 | head -1`),
jumble stops quietly (DEC-14).

### 4.2 JSON

One object, followed by `\n`, to stdout or the `-o` file:

```json
{
  "strings": [
    "…"
  ],
  "alphabet_size": 62,
  "strength_bits": 95.3,
  "strength_is_bound": false,
  "settings": {
    "length": 16,
    "count": 1,
    "charsets": [
      "lower",
      "upper",
      "digits"
    ],
    "custom": "",
    "no_ambiguous": false,
    "each": false,
    "no_repeat": false,
    "unique": false
  }
}
```

The keys come in the order shown. `alphabet_size` is *A*; `strength_bits` is
the §3.5 strength rounded to one decimal place (Python's `round(bits, 1)`);
`strength_is_bound` is true when `each` is on. `settings` holds the effective
settings (§5.2): `charsets` lists each chosen named set once, in canonical
order (an empty list when only `custom` chooses characters), and `custom` is
the string as given, before §2.3's deduplication. The object is written with
two-space indentation and non-ASCII characters as themselves, not `\u`
escapes (Python's `json.dumps(…, indent=2, ensure_ascii=False)`). Errors are
not JSON.

### 4.3 Strength line

`62 characters · 95.3 bits per string`, or with `each` on,
`62 characters · at most 95.3 bits per string`; `1 character · …` when *A*
is 1. The bits are written with exactly one decimal place. `--strength`
writes this line and `\n` to stderr after the output is written, and only
when the run succeeds. The TUI's subtitle uses the same wording (§7.1).

## 5. Settings file

### 5.1 Location and format

`$JUMBLE_CONFIG` if set and not empty, as given (a relative path is relative
to the working directory); else `$XDG_CONFIG_HOME/jumble/config.toml` if that
variable is an absolute path; else `~/.config/jumble/config.toml`, on macOS
too (DEC-10). It is TOML with the setting names of §1 as top-level keys; every
key is optional. A missing file means built-in defaults; `--no-config` means
the file is not read at all, so not even a broken one is an error.

Reading the file stops at its first error (DEC-17), checked in this order:

1. The file exists but can't be read (a directory, no permission).
2. It is not UTF-8, or not valid TOML.
3. Then each top-level key, in the file's order: is it a setting name of §1;
   has it the setting's type; does its value pass the setting's own rule.

The types: `length` and `count` are TOML integers (a boolean or a float is the
wrong type); `charsets` is an array of strings; `custom` is a string; the
four options are booleans. The rules are §6's, for the one key alone:
`length` and `count` at least 1, every `charsets` name a known set (an empty
name is unknown, §2.2), and `custom` with no control or combining character.
Rules that relate settings to each other (`each`, `no_repeat`, `unique`, an
empty set, nothing chosen) are not file errors: they are checked on the
effective settings (§5.2), as for the command line alone. A file error stops
the command line even when the command line overrides that key; the TUI
starts without the file instead (§7.4).

The messages are in §6. `PATH` in them is the path as jumble resolved it,
written as Python's `pathlib` writes a path: `$JUMBLE_CONFIG` as given, a
relative path staying relative, except that `pathlib` drops a leading `./`
and doubled or trailing slashes (`./cfg.toml` is `cfg.toml`); or the XDG or
home path in full, `~` expanded. The TUI's toasts and settings screen show
the path the same way (§7.4).

### 5.2 Precedence

Built-in defaults, then the settings file, then the command line, each
overriding the one before (DEC-9):

- `length`, `count`, and the four booleans are taken key by key. An option
  given on the command line overrides the file even at its default value
  (`-n 16` beats the file's `length = 32`). A boolean
  flag can only turn its option on; `--no-config` is the way to start from the
  built-in defaults.
- Characters are taken as a whole: if the command line gives `-s` or
  `--custom` (even `--custom ''`), the file's `charsets` and `custom` are both
  ignored. A file that sets either key chooses its characters the same way:
  `custom = "abc"` alone means only `abc`.
- If no level chooses any characters, the default `charsets` apply.

### 5.3 Saving

The TUI saves settings (§7.4). A save writes all eight keys, changes only the
values that differ, and keeps the file's comments and layout; a save with
nothing changed leaves the file byte for byte as it was. A new file starts
from a commented template listing every key. A symlinked file is written
through the link (DEC-10).

A save takes these steps, in order (DEC-18):

1. Read the file at the §5.1 path. A missing file, or one that is not UTF-8
   or not valid TOML as §5.1 reads it, is replaced: the save starts from the
   template below (DEC-19). A file that exists but can't be read fails the
   save (§7.4).
2. Remove every top-level key that is not a setting name of §1, with its
   value.
3. For each setting of §1, in §1's order: if the file has the key and its
   value equals the saved value (same TOML type and value), leave that line
   untouched, comments and formatting included; if it has the key with
   another value or type, replace the value in place, keeping the line's
   comment; if it lacks the key, append `KEY = VALUE` at the end of the file.
4. Write the result as UTF-8 to the path, following a symlink to its target,
   creating the file's missing parent directories first. The write is in
   place, not by renaming a temporary file, so a link and the file's
   permissions stay as they were.

Values are written as tomlkit writes them: integers in decimal, `charsets` as
a one-line array of the chosen names in canonical order (an empty array when
only `custom` chooses characters), `custom` as a basic string, and booleans
as `true` or `false`.

The template, with the saved values in place of these defaults:

```toml
# jumble settings. Every key is optional; options given on the command
# line override them. See `jumble --help` for the character sets.

# Characters per string, at least 1.
length = 16
# How many strings, at least 1.
count = 1
# The named sets to draw from.
charsets = ["lower", "upper", "digits"]
# Extra characters, drawn as one more set.
custom = ""
# Leave out look-alike characters such as 0 O l 1 I.
no_ambiguous = false
# At least one character from every chosen set.
each = false
# No character twice within a string.
no_repeat = false
# No string twice in the output.
unique = false
```

## 6. Errors

Validation runs before any drawing, in the TUI as the controls change and on
the command line before output. The messages, in this order of checking:

| Condition | Message |
|---|---|
| length < 1 | `length must be at least 1` |
| count < 1 | `count must be at least 1` |
| unknown set name | `unknown character set: 'NAME'` |
| custom has a control or combining character | `custom characters can't include control or combining characters` |
| no characters chosen (TUI only; the CLI falls back to defaults) | `choose at least one character set` |
| a chosen set is empty after §2.4 | `SET has no characters left` (for `custom`: `custom characters are all left out or already chosen`) |
| `each` and length < number of sets *k* | `length must be at least K to take one character from each of K sets` |
| `no_repeat` and length > *A* | `length can't be more than A without repeats` |
| `unique` and count > *P* | `only P different strings are possible` |
| `unique` gave up (§3.4) | `gave up after D draws with N of COUNT unique strings` |

*P*, *D*, *N*, *COUNT*, *K*, and *A* are written as plain decimal integers.

Settings-file errors (§5.1), checked in that section's order, each naming the
file as `PATH` and, for a key, the key as `KEY` (DEC-17):

| Condition | Message |
|---|---|
| the file can't be read | `can't read PATH: REASON` (`REASON` as for a write, below) |
| not UTF-8 | `PATH: invalid TOML: not UTF-8` |
| not valid TOML | `PATH: invalid TOML: DETAIL`, `DETAIL` being `str()` of `tomllib`'s error |
| unknown key | `PATH: KEY: unknown setting` |
| wrong type | `PATH: KEY: must be an integer` (`a boolean`, `a string`, `a list of set names`) |
| a value its rule rejects | `PATH: KEY: MESSAGE`, `MESSAGE` being the table's message above, for example `PATH: length: length must be at least 1` |

The command line prints `jumble: error: MESSAGE` to stderr and exits 2 for any
of these, for settings-file errors, and for misused options. For the messages
above and settings-file errors that line is the whole output; for misused
options argparse's usage line comes first, as argparse prints it. A file it
cannot write is `jumble: error: can't write FILE: REASON`, exit 1, where
`FILE` is the path as given and `REASON` is the operating system's error
text (Python's `OSError.strerror`, for example `Permission denied`). A
failed write to stdout (no `-o`, or `-o -`) is
`jumble: error: can't write stdout: REASON`, exit 1, except a closed pipe
(`BrokenPipeError`), which exits 1 with nothing on stderr: no message, no
traceback, and no `Exception ignored` line at exit (DEC-14).

## 7. Terminal UI

The TUI follows corral's layout and habits: a one-line header, a controls pane
beside a results pane, an error banner shown only when needed, toasts for
outcomes, single-key actions listed in the footer, and the same behavior code
as the command line (`jumble.generate`).

It opens with `jumble tui` (with options before `tui`, §7.5), or with bare
`jumble` in a terminal (§4, DEC-21).

### 7.1 Layout

```text
          jumble 0.2.0 — 62 characters · 95.3 bits per string
 length must be at least 1                                   ← error banner, only when invalid
 Length [16      ]  Count [10    ]   │ aB3dE9fGh2JkLmN4
 Sets                                │ pQ7rStUvW8xYz3Ab
  [x] lower                          │ …
  [ ] greek  …                       │
  ΑΒΓΔΕΖΗΘΙΚΛΜΝΞΟΠΡΣΤΥΦΧΨΩαβγδεζηθ   │   ← set preview (§7.6)
  ικλμνξοπρστυφχψω                   │
 Custom [                ]           │
 [ ] No look-alikes  [ ] One from each set
 [ ] No repeats      [ ] All unique  │
 g Jumble  c Copy  a Copy all  s Save  d Save defaults  , Settings  ? Help  q Quit
```

- Header: the title `jumble <version>`, the installed package's version
  as `--version` prints it (§4), and as its dim subtitle exactly the §4.3
  line (`strength_line`) for the current controls, updated on every
  change to any control. Textual's header joins them with its own ` — `.
- Controls pane: length and count inputs, a scrollable list of every named
  set in canonical order to check or uncheck, the preview of the set under
  that list's cursor (§7.6), the custom-characters input, and the four
  options as checkboxes. A length or count input that doesn't parse
  as an integer (empty, or `-` alone) counts as 0, so it shows §6's
  `at least 1` message. In a terminal of 100 columns by 30 rows, every
  control's label shows whole, `One from each set` included (issue #12).
- Results pane: the latest strings, one per row, with a cursor, which goes to
  the first string after each jumble. It shows at most the first 1000; a
  final row then reads `… and N more (s saves all)` and can't be highlighted.
  Copy all and save always use every string (DEC-11). Changing a control
  doesn't change the results; only a jumble does.
- Error banner: the §6 message (from `validate`) while the controls are
  invalid; hidden otherwise. While they are invalid, `g` does nothing, the
  header's subtitle is empty, and copying and saving use the last result's
  strings.
- A jumble that stops with §3.4's give-up error leaves the results and the
  cursor as they were and shows the §6 message in an error toast; the
  controls stay valid, so the banner stays hidden (DEC-15).

### 7.2 Keys

| Key | Action |
|---|---|
| `g` | jumble: generate with the current controls |
| `c` | copy the string under the cursor; the toast says `Copied` |
| `a` | copy all strings, one per line; the toast says `Copied N strings` (`Copied 1 string` for one) |
| `s` | save all strings to a new file (§7.3) |
| `d` | save the current controls as the defaults (§7.4) |
| `,` | open the settings screen (§7.4) |
| `?` | open the help screen (§7.6) |
| `q` | quit |

Until a jumble has produced strings (the TUI can start with invalid
controls, §7.5), `c`, `a`, and `s` do nothing.

The TUI starts with focus on the results pane and jumbles once at start. An
input swallows letter keys, so in an input `enter` jumbles (as `g` does, so
not while the controls are invalid) and moves focus to the results pane, and
`escape` moves focus there without jumbling. There is no
Jumble button (DEC-12).

### 7.3 Saving strings

`s` writes every string, one per line, to `jumble-<epoch>-<count>.txt` in the
current directory, where `<epoch>` is Unix seconds (`int(time.time())`) and
`<count>` is the number of strings saved, which is the last result's even
while the controls are invalid. The file holds the same bytes as `jumble`'s
lines output (§4.1): UTF-8, each string followed by `\n`. The toast is
`Saved NAME`, where `NAME` is the file name as written. If that file exists it
writes nothing and the error toast is `NAME exists; nothing saved`: it never
overwrites (DEC-13), and the check and the write are one exclusive create, so
no race can replace a file. Any other failed write is the error toast
`can't save NAME: REASON`, with `REASON` as in §6, and leaves no partial file.

### 7.4 Saving defaults

Two routes write the settings file (§5.3) and confirm its path in a toast:

- `d` saves the main screen's current controls as they stand. While they are
  invalid (§7.1) it writes nothing and shows the banner's §6 message in an
  error toast, so a save never writes a file the command line would refuse.
- `,` opens a settings screen: a form with every setting of §1, filled from
  the settings file (or the built-in defaults), the file's path, and Save and
  Cancel. Save validates (§6), writes the file, closes the screen, and sets the
  main screen's controls to the saved values; Cancel and `escape` close it
  without change. Main-screen keys don't act while it is open (DEC-20):
  - The form holds the same controls as the main screen's controls pane
    (§7.1), with the same labels and the same reading of an input that
    doesn't parse. It is filled with the file's values over the built-in
    defaults, merged as §5.2 merges them with no command line: a file of
    `custom = "abc"` alone checks no set, and a file that chooses no
    characters checks the default sets. The command line's options and the
    main screen's controls play no part. If the file can't be read or is
    invalid (§5.1), the form is filled with the built-in defaults and the
    §6 message (without `jumble: error: `) shows in an error toast, as at
    start, so Save repairs the file. The path shown is the §5.1 path as it
    resolves when the screen opens, written as §5.1 says.
  - Save is the Save button, or `enter` in one of the form's inputs. It
    validates the form as the main screen's banner does (§7.1). While the
    form is invalid, Save writes nothing, keeps the screen open, and shows
    the §6 message in an error toast. A save that fails keeps the screen
    open and changes nothing on the main screen. A save that succeeds sets
    every main-screen control to the saved values, so the banner and the
    subtitle follow them; it doesn't jumble, and the results stay as they
    were (§7.1).
  - Nothing typed or chosen in the form reaches the main screen except
    through a successful Save.
  - Focus starts on the form's first control, the Length input. Its only
    key of its own is `escape`.
  - The screen is a dialog titled `Settings` holding, from the top, the
    path, the form, and Save and Cancel. The path is shown whole, wrapped
    onto as many lines as it needs when it is wider than the dialog, never
    cut short. The path and the buttons always show: when the terminal is
    too short for the whole dialog, only the form scrolls, so Save and
    Cancel never need a scroll to reach (DEC-23). When it is tall enough,
    the dialog is only as tall as its contents: Save and Cancel sit on the
    row after the form's last row, with no blank rows between, and the
    dialog stays centered. Both hold as the terminal is resized with the screen
    open (DEC-26).

Either route writes to the §5.1 path as it resolves at the time of the save,
even when the TUI was started with `--no-config`. A successful save's toast
is `Saved defaults to PATH`. A save that fails (the file exists but can't be
read, or the write fails) shows the error toast `can't save PATH: REASON`,
with `REASON` as in §6. `PATH` is written as in §5.1 (DEC-18).

When the settings file is invalid, the TUI starts from the built-in defaults
and the command line's options, as if `--no-config` were given, and shows the
§6 message (without `jumble: error: `) in an error toast; saving replaces the
invalid values (DEC-17).

### 7.5 Starting values

The TUI's controls start from the effective settings (§5.2), including any
options given before `tui` on the command line; with no `-s` and no
`--custom`, the default sets are checked, as on the command line. Before the
TUI starts, the command line rejects what the controls can't hold: an unknown
or empty `-s` name is §6's `unknown character set: 'NAME'`, exit 2, naming the
first such name as given. Any other invalid starting value starts the TUI with
the error banner shown and no strings, so `c`, `a`, and `s` do nothing until a
jumble succeeds (§7.2) (DEC-16).

### 7.6 Seeing the sets' characters

Two places show what each named set holds (DEC-22). Both show a set's
characters the same way: every character of the set as §2.1 defines it, in
its order, with nothing between them, wrapped at the width they have. The
other controls change nothing in them: `no_ambiguous` and the other chosen
sets (§2.4) remove no character, since they describe the set, and the
subtitle describes the alphabet. `space`, whose one character can't be seen,
shows `(the space character)` instead.

- **Preview.** Under the Sets list, a preview four lines tall shows the
  characters of the set under the list's cursor. It is inset one column at
  each side, so its text starts inside the left border of the Sets list and
  the Custom input around it, and has no border and no padding above or
  below, since at 100 × 30 the pane has no row to spare (§7.1, DEC-25). Four
  lines hold the largest set at the width that leaves. The cursor starts on
  the first set, `lower`, and the preview follows it as it moves, by key or
  by click; checking or unchecking a set doesn't move it. The preview is
  part of the controls (§7.1), so the settings form has one too, following
  the form's own list (§7.4). It is text only: it takes no focus and has no
  keys.
- **Help screen.** `?` opens it over the main screen: a dialog titled `Help`
  listing every named set in canonical order, each as its name and size on
  one line (`greek · 48 characters`, `space · 1 character`) with its
  characters below, then a note on each other control, one per line:

  ```text
  Length: characters per string, at least 1
  Count: how many strings, at least 1
  Custom: extra characters, drawn as one more set
  No look-alikes: leave out 0 O o l 1 I | ` ' " ; : . , -
  One from each set: at least one character from every chosen set
  No repeats: no character twice within a string
  All unique: no string twice in the output
  ```

  The look-alikes are §3.1's, in its order. The dialog scrolls with the
  arrow and page keys and the mouse wheel. `escape` or `?` closes it; it
  changes no control, and main-screen keys don't act while it is open, as
  with the settings screen (DEC-20). `?` works whether or not the controls
  are valid. In an input, `?` is typed like any other character (§7.2).
