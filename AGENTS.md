# jumble

Instructions for coding agents. Codex reads this file; Claude Code reads it
through `CLAUDE.md`'s `@AGENTS.md` import.

jumble is a random string generator for personal use, with a command line
(`jumble`) and a Textual TUI (`jumble tui`). README.md covers usage.

## Before you start

- Read `docs/decisions.md`. Those questions are settled: don't reopen one
  unless the user asks. When the user settles a new one, add an entry.
- Check the roadmap: `gh issue list`.

## Commands

- `uv sync`: set up a fresh checkout.
- `make check`: everything CI checks (ruff format and lint, ty, pytest). Run
  it before every push.
- `make fix`: apply formatting and safe lint fixes.
- `uv run pytest tests/test_tui.py`: one test file, for the loop while working.

## Workflow

- One branch and pull request per change. Don't commit to `master` directly.
- Conventional Commits (`feat:`, `fix:`, `docs:`, `chore:`, …) for commit
  messages and pull request titles; merges are squashed, so the title becomes
  the commit on `master`.
- CI must pass before a merge; don't bypass a failing required check (no
  `gh pr merge --admin`).
- Keep README.md and the CLI help text in step with any behavior change, in
  the same pull request.

## Roadmap: GitHub Issues

The roadmap is the issue list on `chocs-cat/jumble`. Keep it current:

- **File ideas as issues, don't just mention them.** When you or the user
  come up with a feature, a follow-up, a bug, or a loose end you won't handle
  now, create an issue without asking first. Unplanned thoughts get the
  `idea` label; add an area label (`cli`, `tui`, `core`) and a type label
  (`bug`, `enhancement`, `question`) where one fits.
- Before starting work, look for an existing issue and reference it. Close
  issues from the pull request that resolves them (`Fixes #12` in its body).
- Comment on an issue when you learn something that matters to whoever picks
  it up next.

## Conventions

- Generation logic lives in `src/jumble/generate.py`; `cli.py` and `tui.py`
  only gather options and call it, so the two front ends can't drift apart.
- Draw randomness from `secrets`, never `random` (DEC-1).

## Testing notes

- TUI tests drive the app with `App.run_test()` and its pilot; async tests
  need no marker (`asyncio_mode = "auto"`).
- A focused `Input` swallows printable keys, even over priority bindings, so
  the TUI starts focus on the Jumble button. Tests that press letter keys must
  not leave an input focused.
