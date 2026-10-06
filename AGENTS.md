# jumble

Instructions for coding agents. Codex reads this file; Claude Code reads it
through `CLAUDE.md`'s `@AGENTS.md` import.

jumble is a random string generator for personal use, with a command line
(`jumble`) and a Textual TUI (`jumble tui`). `docs/spec.md` defines its
behavior; README.md covers usage.

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

- Changes arrive through the relay workflow (below): one `chunk/<id>` branch
  and pull request per chunk for code, and `plan/<slug>` branches for planning
  and docs changes. Don't commit to `master` directly.
- Pull request titles are Conventional Commits (see *Releases*); merges are
  squashed, so the title becomes the commit on `master`. Unit commits on a
  chunk branch keep their relay titles (`P0001-C01-a: …`).
- CI must pass before a merge; don't bypass a failing required check (no
  `gh pr merge --admin`).
- Keep `docs/spec.md`, README.md, and the CLI help text in step with any
  behavior change, in the same pull request.

## Roadmap: GitHub Issues

The roadmap is the issue list on `chocs-cat/jumble`. Keep it current:

- **File ideas as issues, don't just mention them.** When you or the user
  come up with a feature, a follow-up, a bug, or a loose end you won't handle
  now, create an issue without asking first. Unplanned thoughts get the
  `idea` label; add an area label (`cli`, `tui`, `core`) and a type label
  (`bug`, `enhancement`, `question`) where one fits.
- Ideas, bugs, and follow-ups are issues. The design and delivery plan for
  anything bigger than one chunk live in a project file (`docs/projects/`),
  and each chunk in its brief (`docs/chunks/`); both link the issues they
  come from.
- Before starting work, look for an existing issue and reference it. Close
  issues from the pull request that resolves them (`Fixes #12` in its body).
- Comment on an issue when you learn something that matters to whoever picks
  it up next.

## Releases

Releases are automated with release-please, from Conventional Commits.

- **Conventional Commits** for pull request titles (CI checks them): `feat:`,
  `fix:`, `perf:`, `docs:`, `refactor:`, `test:`, `ci:`, `build:`, `chore:`,
  with a scope where useful (`fix(cli): …`). The
  type decides the version bump and the changelog entry, so choose it for the
  user-visible effect: `feat` → minor, `fix` and `perf` → patch, `feat!` or a
  `BREAKING CHANGE:` footer → major (minor while below 1.0). The other types
  release nothing on their own. Pull requests are squash-merged, so the title
  is the commit release-please reads.
- Don't edit versions or `CHANGELOG.md`; release-please owns them. It keeps a
  release pull request open, and merging it tags `vX.Y.Z` and creates the
  GitHub release; nothing goes to a registry. That merge is the maintainer's
  call.
- To force a version, add a `Release-As: X.Y.Z` footer to a commit. To fix the
  type or wording of an already-merged pull request, add a
  `BEGIN_COMMIT_OVERRIDE` … `END_COMMIT_OVERRIDE` block with the corrected
  message to its body before the release pull request merges.
- Never move or delete a pushed release tag. A bad release is fixed forward.

## Conventions

- Generation logic lives in `src/jumble/generate.py`: the character sets,
  the one settings type every front end shares, validation, generation, and
  strength (DEC-10). The settings file is read and written by
  `src/jumble/config.py`. The CLI and the TUI only gather settings and call
  these, so the front ends can't drift apart.
- Draw randomness from `secrets`, never `random` (DEC-1).

## Testing notes

- TUI tests drive the app with `App.run_test()` and its pilot; async tests
  need no marker (`asyncio_mode = "auto"`).
- A focused `Input` swallows printable keys, even over priority bindings, so
  the TUI starts focus on the results pane (DEC-12). Tests that press letter
  keys must not leave an input focused.
- Tests never touch the real settings file: point `$JUMBLE_CONFIG` at a
  `tmp_path` file (monkeypatch) in any test that loads or saves settings.

## Relay workflow

Work in this repository is built by fresh agent sessions that hand it to one
another through the files below, using the relay skills:

- `/relay-project` shapes an idea into settled design and an ordered delivery
  plan, and closes the project when its work is accepted.
- `/relay-next` reviews the chunk in flight, records the review, merges
  accepted work, and cuts the next chunk brief.
- `/relay-execute` builds the chunk in flight unit by unit on its own branch
  and draft pull request, then hands it back for review.
- `/relay-release` cuts a version by reviewing and merging release-please's
  release pull request.

Code reaches the integration branch only through a chunk pull request, so every
change gets the executor's test discipline and a CI run. The status file is the
handoff between sessions: run each skill in a fresh session.

When code and an authority doc disagree, one of them is wrong: fix it and say
which. A decided entry in the decision log is not re-litigated; where the docs
genuinely do not cover something, add an entry, update the doc that should have
said it, and cite the entry at the code site.

### Settings

- **Integration branch:** `master`. Chunk and planning pull requests
  squash-merge here.
- **Release branch:** same as the integration branch.
- **Gate:** `make check`, which runs ruff format and lint, ty, and pytest. It
  passes before every unit commit and push. CI runs these same targets.
- **CI:** `.github/workflows/ci.yml` runs the gate on pull requests, including
  drafts; pushes to `master` run it. `.github/workflows/pr-title.yml` checks
  pull request titles.
- **Releases:** release-please, as *Releases* describes: a chunk pull
  request's title is a Conventional Commit for the chunk's user-visible
  effect, and nobody edits the changelog by hand. Unit commits on a chunk
  branch keep their relay titles; only the squash commit reaches `master`.
- **Issues:** GitHub Issues, as *Roadmap* describes: review follow-ups and
  ideas are filed as issues, a project or maintenance chunk may start from
  one, and the pull request that finishes it closes it.
- **Authority:** `docs/spec.md`, then `README.md`, then the CLI help text
  and the code's own docstrings.
- **Status:** `docs/status.md`
- **Chunks:** `docs/chunks/<ID>.md`
- **Decision log:** `docs/decisions.md`, entries cited as `(DEC-n)`
- **Review checklist:** `docs/review-checklist.md`
- **Brief checklist:** `docs/brief-checklist.md`
- **Projects:** `docs/projects/` (`index.md`, `template.md`, one
  `P####-slug.md` per project)
- **Tools:** `tools/`, review aids run by hand, outside the gate and the build
- **Review extras:** none.
- **Environment:** none.
