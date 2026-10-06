# Status

Last updated 2026-10-06 by `relay-next`.
Last review: none yet.

## Where this stands

- The relay workflow was set up on 2026-10-06.
- Project P0001 (full generator) became active on 2026-10-06; its design is in
  `docs/spec.md` and DEC-2 – DEC-13.
- P0001-C01 (D1: settings model, sets, generation options) was cut on
  2026-10-06 and is ready for an executor. D2 – D5 remain.
- **Do next:** `/relay-execute` to build P0001-C01.

## In flight

- **Chunk:** P0001-C01
- **State:** ready for an executor
- **Branch:** —
- **Pull request:** —
- **Units committed:** —

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

None yet. One line per chunk: the decision-log IDs it added.
