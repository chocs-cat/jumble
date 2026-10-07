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

### §2. A failure pinned for one branch, its sibling left open

**Shape:** the docs or the brief fix the error behavior of one branch of an
either/or (writing to a file) and say nothing about the other (writing to
stdout), though both run through the same code. The executor builds the
pinned branch, the other inherits its handler by accident, and no test drives
it.

**Check:** for every failure a brief pins, name the code path it runs
through and list that path's other branches; pin each branch's failure, or
put it in *Out of scope* by name.

**Provenance:** P0001-C02. Spec §6 and unit a pinned `can't write FILE:
REASON` for `-o FILE`; nothing covered a failed write to stdout, which then
printed `can't write None: Broken pipe` (`review-checklist §1`). DEC-14
pinned it at the review.

### §3. A test meant to catch a trap passes without the fix

**Shape:** the brief names a trap (a buffered flush, a race, an off-by-one at
a boundary) and prescribes the test that proves it is handled, but the
prescribed inputs never reach the trap, so the test passes with the fix
removed. It reads as coverage and guards nothing.

**Check:** for each *Tests* line written against a named trap, walk the
inputs through the failing path by hand, or try them against the unfixed
code, and confirm they would fail it. Name the mutation the test must catch
in the line itself.

**Provenance:** P0001-C03. Unit a's kickoff note said a closed pipe leaves
`Exception ignored … BrokenPipeError` at exit when stdout still holds bytes;
its prescribed test, `-c 200000`, overflows the buffer, so nothing stays
buffered and the test passes without `quiet_stdout()`. The executor added a
pipe closed before writing, which fails without it.

### §4. An implementation hint changes output the docs pinned

**Shape:** a *Build* line or a note suggests a convenient mechanism (a type,
a library call, a conversion) for something whose observable output an
authority section already fixes, and the mechanism alters that output in a
case the planner didn't walk. The executor follows the brief, and the
pinned wording is now false.

**Check:** for each implementation hint that touches a pinned output, run
the pinned examples and one awkward input through the hint by hand (or in a
REPL) and compare with the section's wording; where they differ, change the
hint or the doc before cutting.

**Provenance:** P0001-C05. Spec §5.1 said `PATH` is `$JUMBLE_CONFIG` "as
given"; unit a told the executor to print `str(path)` of a `Path`, which
turns `./cfg.toml` into `cfg.toml`. The executor built the brief and filed
#14; the review amended §5.1 (DEC-18).

### §5. A second component asked to judge what the docs give to one

**Shape:** the docs settle a judgement (is this valid, are these equal, how
is this written) by one component, and the brief hands the same judgement to
another one elsewhere (a second library, a second form, a second parser) on
the assumption that the two agree. They differ at the edges, and the second
accepts what the first refuses, so one front end lets through what the other
then rejects.

**Check:** for each judgement a brief assigns to a library or a new piece of
code, find the component the authority docs already use for it. Have the
brief call that one, or defer to it, rather than a look-alike; where a
second one is unavoidable, name the cases where they differ and require a
test of one.

**Provenance:** P0001-C06. Spec §5.1 judges TOML with `tomllib`; unit a's
notes told the executor to treat "tomlkit's parse error" as an unparsable
file. tomlkit reads TOML 1.1, so a save would have kept `custom = "\x41"`
as equal to `custom = "A"` and left a file the command line refuses. The
executor found it and logged DEC-19.
