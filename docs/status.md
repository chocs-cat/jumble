# Status

Last updated 2026-10-06 by `relay-next`.
Last review: P0001-C02, 2026-10-06.

## Where this stands

- The relay workflow was set up on 2026-10-06.
- Project P0001 (full generator) became active on 2026-10-06; its design is in
  `docs/spec.md` and DEC-2 – DEC-14.
- P0001-C01 (D1: settings model, all sets, generation options) was accepted
  with follow-ups on 2026-10-06 (PR #7).
- P0001-C02 (D2: command-line output) was accepted with follow-ups on
  2026-10-06 (PR #9); its stdout write-failure fix is P0001-C03-a.
- P0001-C03 (D3, first half: TUI layout, live validation, copy keys) was cut
  on 2026-10-06 and is ready for an executor. The rest of D3 (`s`, §7.5,
  screenshot), D4, and D5 remain.
- **Do next:** `/relay-execute` to build P0001-C03.

## In flight

- **Chunk:** P0001-C03
- **State:** executing
- **Branch:** `chunk/p0001-c03`
- **Pull request:** `#10` (draft)
- **Units committed:** a

(Fixed shape. `State` ∈ `ready for an executor` · `executing` ·
`awaiting review` · `none`; `Branch`, `Pull request`, and `Units committed` are
`—` until set; the pull request carries `(draft)` or `(ready)`.
`/relay-execute` creates `chunk/<id>` from the integration branch, opens a
draft pull request, sets `executing`, updates `Units committed` per unit, and
sets `awaiting review` when its report lands; `/relay-next` reviews that pull
request on its branch, cuts the next chunk, and squash-merges. While a chunk
pull request is open, the copy of this file on its head branch is the
authoritative handoff.)

## Follow-ups not yet scheduled

Filed as GitHub issues (`gh issue list`), not kept here.

## Decisions by chunk

One line per chunk: the decision-log IDs it added.

- P0001-C01: none (DEC-1 amended at its review).
- P0001-C02: none (DEC-14 added at its review).
