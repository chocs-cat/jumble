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
jumble                        # one 16-character string of letters and digits
jumble -n 32 -c 5             # five 32-character strings
jumble -s lower -s digits -a  # lowercase and digits, without look-alikes (Il1O0o)
jumble tui                    # pick the length and character sets interactively
```

Character sets: `lower`, `upper`, `digits`, `symbols`. In the TUI, `g`
jumbles again, `c` copies the result, and `q` quits.

## Development

```sh
uv sync
make check   # ruff format and lint, ty, pytest; what CI runs
make fix     # apply formatting and safe lint fixes
```

## License

MIT; see [LICENSE](LICENSE).
