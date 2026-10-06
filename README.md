<picture>
  <source media="(prefers-color-scheme: dark)" srcset="docs/logo-dark.svg">
  <img alt="jumble" src="docs/logo-light.svg" height="64">
</picture>

jumble generates random strings — passwords, tokens, test data — from the
command line or an interactive terminal UI. It draws from Python's `secrets`
module, so the output is fit for secrets.

## Install

Needs [uv](https://docs.astral.sh/uv/). From a checkout:

```sh
uv tool install .
```

## Usage

```sh
jumble                          # one 16-character string of letters and digits
jumble -n 32 -c 5               # five 32-character strings
jumble -s lower,digits -a       # lowercase and digits, without look-alikes
jumble -s lower -s symbols -e   # at least one lowercase letter and one symbol
jumble --custom 'ACGT' -n 40    # only the characters you give
jumble -s emoji-animals -n 4 -r # four different animals
jumble -s digits -n 4 -c 20 -u  # twenty different four-digit codes
jumble tui                      # pick the length and character sets interactively
jumble -n 32 -s digits tui      # the same, starting from 32 digits
```

| Option | Effect |
|---|---|
| `-n`, `--length N` | characters per string (default 16) |
| `-c`, `--count N` | how many strings (default 1) |
| `-s`, `--charset NAME[,NAME…]` | sets to draw from; repeat or separate with commas |
| `--custom CHARS` | also draw from these characters, as one more set |
| `-a`, `--no-ambiguous` | leave out look-alikes: ``0 O o l 1 I \| ` ' " ; : . , -`` |
| `-e`, `--each` | at least one character from every chosen set |
| `-r`, `--no-repeat` | no character twice within a string |
| `-u`, `--unique` | no string twice in the output |
| `-o`, `--output FILE` | write to `FILE`, created or overwritten, instead of stdout; `-` means stdout |
| `--json` | write one JSON object instead of lines (below) |
| `--strength` | also print the alphabet size and bits per string to stderr |
| `--no-config` | ignore the settings file (below) |

With no `-s` and no `--custom`, and no characters chosen in the settings
file, jumble draws from `lower`, `upper`, and `digits`. A character that is in more than one chosen set counts once, in the
first set of the table below, with `--custom` last; a choice left with no
characters of its own is an error. Each character is one Unicode code point,
so `--custom` rejects control and combining characters. Errors print
`jumble: error: …` and exit 2; a failed write, to an `-o` file or to stdout,
exits 1. When a pipe's reader stops early (`jumble -c 100000 | head -1`),
jumble exits 1 without a message.

jumble generates every string before writing any, so a failed run prints
nothing and leaves an existing `-o` file as it was. Output is UTF-8, on stdout
as in a file, whatever the terminal's locale.

`--json` writes the strings with the alphabet size, the strength in bits
(an upper bound with `-e`), and the settings the run used:

```console
$ jumble --json -n 8 -c 2 -s digits,lower
{
  "strings": [
    "k3x9q0ba",
    "7mz2wd4e"
  ],
  "alphabet_size": 36,
  "strength_bits": 41.4,
  "strength_is_bound": false,
  "settings": {
    "length": 8,
    "count": 2,
    "charsets": [
      "lower",
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

Errors are never JSON.

`--strength` prints a line such as `62 characters · 95.3 bits per string` to
stderr once the output is written (`at most` before the bits with `-e`), so it
stays out of a pipe or `-o` file. `-o`, `--json`, and `--strength` don't go
with `tui`.

| Set | Characters | Size |
|---|---|---|
| `lower` | `a`–`z` | 26 |
| `upper` | `A`–`Z` | 26 |
| `digits` | `0`–`9` | 10 |
| `symbols` | all ASCII punctuation | 32 |
| `space` | the space character | 1 |
| `chess` | ♔…♟ | 12 |
| `cards` | the 52 standard playing cards 🂡…🃞 | 52 |
| `dice` | ⚀…⚅ | 6 |
| `emoji-faces` | 😀…🙏 | 80 |
| `emoji-animals` | 🐀…🐾 | 63 |
| `emoji-food` | 🍅…🍻 | 55 |
| `greek` | Α…Ω, α…ω | 48 |
| `cyrillic` | А…я | 64 |
| `latin-accented` | À…ÿ, without × and ÷ | 62 |
| `arrows` | ←…↙ | 10 |
| `math` | `±×÷∞≠≈≤≥√∑∏∫∂∆∇∈∉∩∪⊂⊃∀∃¬∧∨` | 26 |
| `currency` | `¢£¥€₹₽₩₪₺₿₫₱` | 12 |
| `box` | box drawing and block elements ─…▟ | 160 |

### Settings file

jumble starts from a TOML settings file, if there is one, at the first of:

- `$JUMBLE_CONFIG`, if set and not empty (a relative path is relative to the
  working directory);
- `$XDG_CONFIG_HOME/jumble/config.toml`, if that variable is an absolute path;
- `~/.config/jumble/config.toml`, on macOS too.

Its keys are the setting names `--json` shows, and every key is optional:

```toml
length = 24
count = 5
charsets = ["lower", "digits"]
custom = "!?"
no_ambiguous = true
each = true
no_repeat = false
unique = false
```

The command line overrides the file, and the file overrides the built-in
defaults. `-n` and `-c` win whenever they are given, even at their default
value (`-n 16` beats `length = 24`). A flag such as `-e` can only turn its
option on. Characters go as a whole: `-s` or `--custom` (even `--custom ''`)
replaces both the file's `charsets` and its `custom`, and a file with only
`custom = "abc"` draws from `abc` alone. `--no-config` ignores the file
entirely, so the run starts from the built-in defaults.

A broken file is an error that names the file and the key, such as
`jumble: error: /home/me/.config/jumble/config.toml: length: length must be at
least 1`, even when the command line overrides that key; fix the file or pass
`--no-config`. Rules that tie settings together are checked on the result
instead: `each = true` is fine in the file until `-n 2` asks for two
characters from three sets.

### The TUI

`jumble tui` opens the generator in the terminal. It starts from the settings
file, like the command line, and options given before `tui` override it:
`jumble -n 32 -s digits tui` opens on 32-digit strings. A broken settings file
doesn't stop the TUI: it opens from the built-in defaults and those options,
with the error in a toast. An unknown set name is an error before the TUI opens; any other value
it can't use (`-n 0`) opens it with the banner showing, to fix there.

On the left are the controls: length and count, every character set in the
table above to check or uncheck, custom characters, and the four options (No
look-alikes, One from each set, No repeats, All unique). On the right are the
strings, one per row. The header shows the alphabet size and strength for the
controls as they stand, updated as you change them. When the controls can't
produce strings, a banner under the header says why, with the same message the
command line would print, and the strength disappears until you fix them.
Changing a control leaves the strings alone; only a jumble replaces them. The
list shows the first 1000 strings and says how many more there are; copying all
and saving take every one.

The keys are listed in the footer:

| Key | Action |
|---|---|
| `g` | jumble a new batch with the current controls (not while the banner shows) |
| `c` | copy the string under the cursor |
| `a` | copy all strings, one per line |
| `s` | save all strings to a new file, `jumble-<epoch>-<count>.txt`, in the current directory |
| `q` | quit |

Focus starts on the strings, so the keys work. In a text box, `enter`
jumbles (as `g` does) and returns to the strings, and `escape` returns without
jumbling. While the banner shows, `c`, `a`, and `s` use the last batch.

`s` never overwrites: if the file exists (a second save in the same second),
it saves nothing and says so. The file holds the same bytes as `jumble`'s
output: UTF-8, one string per line.

![The jumble TUI: controls on the left, ten strings on the right](docs/tui.svg)

## Development

```sh
uv sync
make check   # ruff format and lint, ty, pytest; what CI runs
make fix     # apply formatting and safe lint fixes
```

## License

MIT; see [LICENSE](LICENSE).
