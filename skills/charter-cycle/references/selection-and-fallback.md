# Selection, worked — and when to fall back

## Where priority lives

**Charters are ranked. Requirements inside a charter are not.** A charter inherits its
theme's position in the portfolio queue; within a charter, requirements are worked in
table order, honouring declared dependencies.

Two alternatives were considered and rejected when this rule was set:

- *A queue entry per workable requirement*, mirroring the `Implements:` mechanism that
  links goals to repository tasks. Rejected: it reintroduces the item-by-item attention
  charters exist to remove, and creates a second copy to keep in sync.
- *Charters run in ratification order, each declaring its own internal order.*
  Rejected: priority becomes implicit in ratification timing, so a charter ratified
  early but cared about less runs first, with no lever short of re-ratifying.

**Losing item-level ranking is the intended effect, not a regression.** The user ranks
charters and stops ranking items. Where one requirement genuinely must precede another,
the charter says so as a dependency — that is the charter's job, not the queue's.

## Worked example

```
portfolio GOALS.md
  theme T-1               (queue position 1)
    charter C-a   active, ratified
      R1  unmet                      <- selected
      R2  unmet
      R3  unmet   depends: R1
      R4  unmet
      R5  unmet   depends: R4
    charter C-b   proposed           <- not workable: no ratified: line
  theme T-2               (queue position 2)
    (no charter yet)
```

The run takes **C-a R1**. Not R3, which declares a dependency on R1. Not anything in
C-b, which is a draft: a draft is readable and never workable. Nothing in T-2, because
it has no charter, and an empty theme is not a licence to fall through to unchartered
work.

Had the user deferred R1 explicitly, the run would take **R2** — and would *not* take
R1 tomorrow on the reasoning that the deferral had aged out.

## Two ways a deferral gets broken

Both have been observed. Neither is hypothetical, and the evidence is in the portfolio's
own review log rather than here.

1. **By argument.** A later run finds the deferral's *stated reason* no longer holds —
   "the queue was long that day, and today it is short" — and treats the deferral as
   expired. It is not. The reason a deferral was given is not the deferral.
2. **By layer.** The deferred item is blocked at one level, so the work is filed a level
   down — as a repository task under a blocked requirement — where the block does not
   reach. Skipping a layer to reach deferred work is the same refusal, disobeyed.

**A deferral is lifted by the user or not at all.** If a deferral looks wrong, say so
and leave it in place.

## When to fall back to `work-cycle`

`work-cycle` is superseded, not retired, and it still runs. Fall back when the work is
not chartered at all: a repository task, a portfolio goal with no charter behind it, or
the user's own queue items.

**Falling back is a finding, not a failure.** Record it: what you reached for, why it
was not in this skill, and whether a charter should have covered it. Those records are
the evidence for whether the chain is ready to replace the queue — a decision for a
review, not for a run.

Do **not** fall back to reach work a charter's rules would have refused. That is not a
fallback; it is the layer-skipping failure above.
