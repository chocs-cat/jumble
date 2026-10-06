# The review checklist

Every class of bug a review has missed at least once, kept so the next review
looks for it by default. Each entry is a *shape*, not a rule: the authority
docs remain the authority on what the code must do. This file only records
where a passing test suite has failed to catch a real defect.

**How it is used.** `/relay-next` takes the whole chunk diff through every
entry here, after the per-unit checks against the cited doc sections. A finding
that matches an entry cites it as `review-checklist §N`. `/relay-execute` does
not work the whole list; instead the chunk brief's *Kickoff notes* name the
entries a given chunk is most likely to trip, and the executor reads those
before building.

**How it grows.** When a review finds a *class* of bug rather than an
instance, `/relay-next` adds it here as the next numbered entry, with the
finding that revealed it. The provenance is the point: it is the evidence that
the shape is real. Entries are not renumbered or retired: a shape that has
stopped mattering is cheaper to skim than to re-derive after it bites again.

---

## The catalogue

### §1. An error handler shared by branches speaks for only one

**Shape:** one `try` wraps a call that takes several paths (a file or stdout,
a cache or the network), and the handler's message is written for one of
them. The other path raises the same exception type, and the message then
names the wrong thing, often a `None` or a sentinel like `-`, or it reports an
expected event (a closed pipe) as a failure.

**Check:** for each `except`, list every path inside the `try` that can raise
the caught type, and read the message as each would print it. Run the
sibling path once by hand.

**Provenance:** P0001-C02. `cli.main` caught `OSError` around
`write_output`, which writes either `-o FILE` or stdout, and printed
`can't write {args.output}`; `jumble -c 200000 | head -1` printed
`jumble: error: can't write None: Broken pipe`. Spec §6 had named only the
file case (`brief-checklist §2`).

### §2. A call that passed validation can still raise

**Shape:** a function validates up front but has a failure only drawing can
reveal (a retry cap, a race, a resource running out). One caller handles its
exception; another trusts the earlier validation and calls it bare, so the
late failure escapes as a crash.

**Check:** for each function in the diff that raises after its own checks,
list every caller (`search_graph`, or grep the name) and confirm each one
catches the late error and does what the spec says with it.

**Provenance:** P0001-C03. `cli.main` caught `JumbleError` from `generate`;
`JumbleApp.action_jumble` called it only after `strength` had validated, so
`unique`'s give-up (§3.4) would quit the TUI with a traceback. Spec §7.1 had
said nothing about it (`brief-checklist §2`); DEC-15 pinned it at the review.
