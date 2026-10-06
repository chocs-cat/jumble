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

With no `-s` and no `--custom`, jumble draws from `lower`, `upper`, and
`digits`. A character that is in more than one chosen set counts once, in the
first set of the table below, with `--custom` last; a choice left with no
characters of its own is an error. Each character is one Unicode code point,
so `--custom` rejects control and combining characters. Errors print
`jumble: error: …` and exit 2; a file `-o` can't write exits 1.

jumble generates every string before writing any, so a failed run prints
nothing and leaves an existing `-o` file as it was. Output is UTF-8, on stdout
as in a file, whatever the terminal's locale.

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

In the TUI, `g` jumbles again, `c` copies the result, and `q` quits.

## Development

```sh
uv sync
make check   # ruff format and lint, ty, pytest; what CI runs
make fix     # apply formatting and safe lint fixes
```

## License

MIT; see [LICENSE](LICENSE).
