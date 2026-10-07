# Status

Last updated 2026-10-07 by `relay-next`.
Last review: P0001-C05, 2026-10-07.

## Where this stands

- The relay workflow was set up on 2026-10-06.
- Project P0001 (full generator) became active on 2026-10-06; its design is in
  `docs/spec.md` and DEC-2 – DEC-18.
- D1 – D4 are accepted (P0001-C01 – C05, PRs #7, #9, #10, #11, #13); details
  in the project ledger.
- P0001-C06 (D5's `config.save` and the `d` key) was cut on 2026-10-07 and is
  ready for an executor. What remains of D5 after it: the `,` settings
  screen, and the project's completion evidence.
- **Do next:** `/relay-execute` to build P0001-C06.

## In flight

- **Chunk:** P0001-C06
- **State:** executing
- **Branch:** `chunk/p0001-c06`
- **Pull request:** `#15` (draft)
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
- P0001-C03: DEC-15 added at its review; DEC-16 at the cut of P0001-C04.
- P0001-C04: none (DEC-17 added at the cut of P0001-C05).
- P0001-C05: none (DEC-18 added at its review).
