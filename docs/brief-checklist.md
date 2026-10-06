# The brief checklist

Every class of mistake a chunk *brief* has carried at least once, kept so the
next cut looks for it by default. Each entry is a *shape*, not a rule: the
authority docs remain the authority on what the code must do. This file
records only where a planner, holding the right decisions, still handed an
executor a brief that was wrong.

It is the cut-time companion to the review checklist. The division is by
*when* the mistake is made, not by who finds it: a defect in the code an
executor wrote belongs there, a defect in the instructions the planner wrote
belongs here. Most entries are found in review, because that is when a brief's
error becomes visible; the provenance names the chunk whose brief carried it.

**How it is used.** `/relay-next` takes each draft brief through every entry
here before committing it. A fix that matches an entry cites it as
`brief-checklist §N` in the review or the chunk ledger. `/relay-execute` does
not read this file: an executor builds the brief it is given.

**How it grows.** When a review finds that the *brief* was wrong rather than
the code (a decision that reached no unit, an instruction that contradicted
itself, a *Tests* line that invented a condition), `/relay-next` adds it here
as the next numbered entry with the finding that revealed it. Entries are not
renumbered or retired.

The boundary with `/relay-next` itself: the skill keeps the *procedure* (what
to read, decide, and write, in what order). This file keeps the recurring ways
the product of that procedure has come out wrong.

---

## The catalogue

### §1. The brief contradicts a decision it cites

**Shape:** a *Kickoff notes* or *Build* line states a rule and cites two
decisions for it, while one of them says something else. The executor has to
pick a side, and whichever it picks, a cited authority is wrong.

**Check:** for every decision a brief cites, read the entry's text, not only
its title, against the sentence that cites it. When an entry disagrees with
the brief or with another entry, amend the entry in place before cutting.

**Provenance:** P0001-C01. Its kickoff notes said every draw goes through
`secrets.randbelow`, with no `secrets.choice`, citing DEC-1 and DEC-6; DEC-1
said characters are drawn "with `secrets.choice`". The executor followed
DEC-6 and reported it; DEC-1 was amended in the review.
