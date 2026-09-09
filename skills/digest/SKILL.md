---
name: digest
description: >-
  Produce the digest a finished goal owes its reader: one dated page,
  Markdown or HTML, that carries the outcome first and descends to the mechanism
  and the implementation detail only as far as the reader needs. Use at the
  close-out of a goal that changed what someone can do or should believe, for a
  standalone task or one whose digest was requested, when asked to explain a
  result, a design, or a system, and whenever a reader has said they cannot judge
  the work from what they were given. Produces a transfer artifact; it does not
  request approval, and it does not replace maintained reference documentation.
license: MIT
metadata:
  author: symbolfarm
  version: "1"
  status: draft
  category: communication
  tags: digest, transfer, close-out, documentation, visualisation
---

# Digest

Execution produces an artifact. This skill produces the **transfer** — the thing
that moves an outcome from the agent that built it into the head of the person
who has to judge it.

Treat the transfer as a deliverable, not a courtesy. Where a work item's
completion contract states only what the artifact must do, the work is not
finished when the artifact works; it is finished when someone else can act on it.

**One page, layered.** Not a summary and a deep-dive as two documents. A single
page whose first screen carries the outcome, whose middle carries the mechanism,
and whose end carries the implementation detail — so a reader who only needs the
outcome stops early and a reader who needs to reproduce it keeps going.

**The goal bears the digest.** A goal decomposing into several tasks produces one
digest at the goal's close, not one per task. A task produces a digest only when
it is standalone — not part of any goal — or when one was explicitly requested.
Per-task digests across a busy repository train the reader to skim, and the next
one that matters gets skimmed too.

> **Substrate: unresolved, and this skill does not yet answer it.**
> How a Markdown source becomes a viewable page with working inline SVG and
> copied assets is a real decision with real candidates (a small standard-library
> builder, a static-site generator, a document converter), and this skill stays
> `status: draft` until it names one. Do not read the absence as permission to
> hand-author one-off HTML at every close-out: that is the least reproducible
> option and an unattended run cannot repeat it. Until the substrate is settled,
> follow whatever the calling project already uses, and say in the page which
> route was taken.

---

## 1. Decide whether this item owes a digest

Apply this at a **goal's** close-out, or a standalone or explicitly-requested
task's. It is owed when the work **changed what someone can do, or what they
should believe**: a result, a design decision, a new capability, a negative
finding, a system whose shape a reader must hold.

It does not for chores, dependency bumps, formatting passes, or a refactor with
no behavioural consequence. Manufacturing a digest for those trains the
reader to skim, and the next one that matters gets skimmed too.

When in doubt, ask: *could the reader make a different decision after reading
this?* If not, a close-out note is enough.

## 2. Establish the priority axis

Every work item is dominated by one of two concerns, and the axis decides what
the page owes.

| Axis | The transfer is | The page must let the reader |
|---|---|---|
| **Outcome-priority** | **use** | get their hands on the thing and judge it as a user |
| **Implementation-priority** | **comprehension** | restate the mechanism in their own words |
| **Both** | both, layered | stop after the outcome, or descend into the mechanism |

Read the axis off the item. A product feature is usually outcome-priority; a
research result is usually both; a library internal is usually
implementation-priority. If the item does not say and the difference would change
the page, say which you assumed, in the page.

**A build-passes command does not discharge an outcome transfer.** `--check`
proves the artifact compiles. It is a smoke test, not a handover. An outcome
transfer needs a running thing, a sample, a URL, or a command that shows the
behaviour the work was for.

## 3. Establish what the reader already holds

**This is the step that decides whether the page lands, and it is the one most
often skipped.** Two readers need opposite documents:

- A reader who **holds the shape** of the project needs the *delta* — what
  changed, what it means, what it cost. Give them a complete reconstruction and
  they will not find the new part in it.
- A reader who **holds nothing** needs *reconstruction* — self-contained, no
  assumed context, every term defined at first use.

A page written for the second and handed to the first is the characteristic
failure. It is not badly written; it is the wrong shape for the memory it
addresses, and it reads as *deep in the weeds* — the reader can follow every
sentence and still cannot judge the work.

State the reader in the page's declaration block, and write to that reader. When
a page must serve both, the layering in §4 is what serves them — not a compromise
altitude, which serves neither.

## 4. Structure: four moves, descending

Order the page so each move is complete before the next begins, and a reader may
stop at any boundary.

1. **What was built or tested.** The thing itself, stated plainly.
2. **What was observed.** Results, measurements, behaviour. The full surface
   including the parts that did not fit — a surprising number that gets smoothed
   out here is the most expensive omission on the page.
3. **What that could mean.** Readings, plural where the evidence supports more
   than one. Say which is best supported and why.
4. **What could be built or tested next.** Options, not a request.

**Move 3 must not collapse into move 4.** *"This could mean X, and here is what
would tell us"* leaves the reader free to answer *"neither — the interesting
thing is Y."* *"Therefore we should do X"* asks for a signature with better
manners, and the reader's most valuable response is the one it makes hardest to
give.

Under move 2, place implementation detail last and mark it as such. A heading a
reader can skip is worth more than a page that assumes they will not need it.

### Never request ratification

A digest states what was found and what it might mean. It does not ask the
reader to confirm a belief, approve a reading, or sign off on a direction. If a
decision genuinely needs the reader, name the decision plainly at the end and
leave it open — do not shape the whole page as a case for one answer.

## 5. Draw the mechanism

A finished digest normally carries at least one diagram, because the mechanism
is the part prose conveys worst.

Draw the thing the argument turns on: the path data takes, the boundary being
crossed, the two options' actual difference, the state a request moves through.
Label the arrows — an unlabelled arrow means *related somehow*. A box with a noun
in it says less than the sentence it replaced.

Where numbers carry the finding, draw them to scale and let the scale be the
argument.

Skip the diagram when a sentence is faster. A decorative figure costs the
reader's trust in the ones that are load-bearing.

## 6. Declare the page

**Where the calling project publishes a page-format convention, that convention
owns this section and this skill defers to it.** Restating a format contract in
two maintained documents guarantees they drift. The list below is the minimum for
a project that has no such convention.

Near the title, state:

- **Layer** — one immutable run, a current synthesis, or the altitude view;
- **Audience** — the reader established in §3;
- **As of** — date, and source commit where evidence is executable;
- **Status** — current, or superseded by a named page;
- **Provenance** — where claims, measurements and copied wording came from;
- any standing review caveat that applies.

**Dated, not maintained.** A reference doc describes the current interface and is
edited in place. A digest records what was understood on a day; when it goes
out of date, publish a new one and mark the old superseded. Editing a digest
until it agrees with the present destroys the record of what was believed when.

## 7. Deliver it where the reader can respond

Give a way in, not a description of one: a command, a path, a link, a running
page. Where the reader can comment, publish somewhere that supports comments —
feedback attached to the sentence that caused it is worth more than feedback
recalled later.

Prefer a format the reader can open on the device they will actually open it on.
A page that requires a desk to read gets read at a desk, eventually.

## Anti-patterns

- **Reconstruction handed to an oriented reader.** §3. The most common failure and
  the hardest to see from inside.
- **A compromise altitude.** Serving two readers by pitching between them serves
  neither; layer instead.
- **Ratification with better manners.** Move 3 collapsed into move 4.
- **`--check` as the way in.** Proves the build, transfers nothing.
- **Evenness.** A page where every finding gets equal weight has not been thought
  about. Say which part matters most and let the rest be shorter.
- **Manufactured modesty.** State the weakest point because it is true, not
  because a section demands one.
- **Editing a published digest into agreement with the present.** Supersede it.

## Checklist

- [ ] The item actually owes a digest.
- [ ] The priority axis is established, and the page discharges its transfer.
- [ ] The reader's existing context is established and stated.
- [ ] Outcome first; implementation detail last and skippable.
- [ ] Move 3 offers readings; move 4 offers options; neither asks for approval.
- [ ] At least one diagram shows a mechanism, or a sentence provably did it better.
- [ ] Layer, audience, date, status and provenance are visible.
- [ ] The reader has a way in, on a device they will use.
