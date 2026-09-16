---
name: research-notebook
description: >-
  Maintain the project's research notebook — the living record of what
  we currently believe and why. Use when: recording findings or negative
  results from an experiment, writing up a session's research narrative,
  distilling a completed task's debrief into durable understanding,
  correcting or superseding an earlier claim, capturing reading notes
  on an external paper, or orienting on the project's current theory
  before starting research work. This skill defines the notebook
  substrate (layout, note types, statuses, correction discipline), while
  work-cycle records execution and distills findings at close-out and
  portfolio-cycle drives learning and planning.
metadata:
  author: symbolfarm
  version: "3"
  authored_by: agent
  status: draft
---

## Current workflow

For fresh charter work, `charter-cycle` owns execution and links generated tasks
to requirements. Historical task ledgers are reference only. Preserve the existing
notebook rather than migrating its findings. Update the experiment and affected
current understanding when a meaningful result lands; add logs/index edits only
when they aid retrieval, not as mandatory duplicate reports.

Agents may record evidence-backed conclusions, uncertainty and corrections
without human ratification. Distinguish those assessments from the user's
endorsement or strategic direction. A negative result is useful research evidence.
Digests transfer meaningful changes to readers; they do not replace current notes.

## Overview

A research project produces three distinct streams of writing, and
mixing them is what makes project docs rot:

1. **The queue** — work orders and their lifecycle. Owned by
   the fresh charter queue and its generated `.tasks/current/` briefs.
2. **The event record** — what happened, immutably. Owned by
   `work-cycle` (debriefs, git history).
3. **The current understanding** — what we presently believe is true,
   what's been ruled out, and why. Owned by **this skill**, in
   `notebook/`.

The notebook is stream 3 only. It is a *living* document set: notes
are updated in place as understanding improves, unlike debriefs
(frozen at completion) and dated log entries (append-only). A reader
should be able to open `notebook/INDEX.md` cold and reach the
project's best current understanding without replaying its history.

Everything is plain Markdown with YAML frontmatter and standard
relative links, so the `notebook/` directory renders on GitHub and
opens directly as an Obsidian vault (see "Obsidian compatibility").

Like `.tasks/`, the notebook is **per-repo**. In a multi-project
workspace each repo carries its own `notebook/`; cross-repo references
use ordinary relative links (`../../sibling-repo/notebook/...`) and
are resolved by hand.

---

## Layout

```
notebook/
  INDEX.md               # map of content — the single entry point
  log/
    2026-07-05.md        # dated lab-log entries, append-only
  notes/
    keying-wall.md       # evergreen concept/claim notes, one idea each
  experiments/
    CR-19-onehop-additivity.md   # one note per experiment, structured
  references/
    vaswani-2017-attention.md    # reading notes on external sources
```

- **`INDEX.md`** — a curated map, not an auto-listing: the north-star
  statement, the open questions, and links to the load-bearing notes
  grouped by theme. Update it whenever a note is added, retired, or
  changes status. This file replaces the sprawling "current focus"
  narrative that otherwise accretes in `TASKS.md`.
- **`log/YYYY-MM-DD.md`** — the session narrative: what was tried,
  what was observed, dead ends, hunches. One file per calendar day;
  multiple sessions the same day append sections. Append-only (see
  "Corrections and supersession").
- **`notes/<slug>.md`** — one concept, claim, or design position per
  note. Examples: a theoretical framing, a named phenomenon ("the
  keying wall"), a standing methodology decision. These are the notes
  that get *updated in place*. For a note that describes a **mechanism
  in the code**, carry concrete implementation detail — a curated code
  excerpt or tight labelled pseudocode, with `file.py:line` anchors —
  enough that a reader could reconstruct the mechanism, not just its
  gloss. This is deliberately in tension with "no wholesale dumps"
  below: paste the *load-bearing* lines (the retrieval loop, the gate,
  the solve), not the whole file. A note dense enough to reconstruct
  from is what lets the human stay aware of *what is implemented* while
  work moves fast.
- **`experiments/<id>-<slug>.md`** — one note per experiment worth
  citing later: hypothesis, setup, exact command, headline numbers,
  verdict. Named after the driving task ID where one exists
  (`CR-19-...`), otherwise a dated slug. Negative results are
  first-class — an experiment that rules something out is often the
  most valuable note in the book.
- **`references/<citekey>.md`** — one note per external source (paper,
  post, codebase), named by a citekey-style slug
  (`vaswani-2017-attention`). Bibliographic frontmatter plus *our*
  reading notes: what it claims, what we take from it, how it bears on
  our notes. Created lazily — only when a source actually informs the
  work. Theory does **not** get its own directory: our own claims and
  framings are exactly what `notes/` is for, and a `theory/` split
  would force a boundary decision on every note.

Templates for all of these live in `skills/research-notebook/assets/`.

---

## Frontmatter conventions

Every note (not log entries) carries YAML frontmatter:

```yaml
---
status: live          # live | superseded | overturned
tags: [construction, additivity]
tasks: [CR-19, CR-22] # driving/related task IDs, if any
superseded_by: notes/two-stage-chaining.md   # only when not live
---
```

- `status: live` — current best understanding.
- `status: superseded` — replaced by a better formulation; the note is
  kept for the record, `superseded_by` points at the replacement.
- `status: overturned` — the claim was *wrong*; the body gains a
  callout at the top saying what overturned it and linking to the
  evidence. Overturned notes are never deleted — knowing what was
  believed and disproven prevents re-deriving dead ends.

Experiment notes add machine-scannable result fields where they
apply (`command`, `metrics`, `verdict: supports | refutes | inconclusive`).
Reference notes add bibliographic fields (`url`, `authors`, `year`).
Keep frontmatter values simple scalars/lists — it should survive any
YAML parser and Obsidian's properties panel alike.

---

## Linking conventions

Use **standard relative Markdown links**, not `[[wikilinks]]`:

```markdown
see [the keying wall](../notes/keying-wall.md)
```

Rationale: GitHub, editors, and other agents resolve them; Obsidian
resolves them too (and can be configured to *generate* them: Settings →
Files & Links → set "Use [[Wikilinks]]" off and link format to
"Relative path to file"). Wikilinks are Obsidian-only and render as
dead text everywhere else, which breaks the "one canonical source,
many readers" property.

Link liberally in prose: task IDs to their debrief file, claims to the
experiment note that established them, corrections to what they
correct. The link graph *is* the notebook's index; `INDEX.md` is just
its curated spine.

---

## Corrections and supersession

The core discipline — the thing that makes the notebook trustworthy:

- **Log entries are append-only.** Never rewrite a past day's entry.
  When a claim in an old entry turns out wrong, append a dated
  correction callout to *that* entry pointing forward:

  ```markdown
  > **CORRECTION (2026-07-05, CR-21):** the readability probe below is
  > confounded — see [elicitation probe](../experiments/CR-21-elicitation-probe.md).
  > Trust the generation signals instead.
  ```

  …and record the correction in *today's* log entry too, so a
  chronological reader catches it either way.

- **Evergreen notes are updated in place.** Rewrite the body to the
  new best understanding, and append a one-line entry to a `Changelog`
  section at the bottom (`- 2026-07-05: corrected per CR-21 — info is
  present but object-entangled, not absent`). Readers get the current
  view; the changelog + git history preserve the trajectory.

- **When a claim dies, flip its status** (`overturned` /
  `superseded`), add the top-of-body callout, and update `INDEX.md`
  so nothing live links to it as if it were current.

When sources disagree, check the primary evidence and correction provenance.
A current-status label or recent timestamp alone does not establish truth. If you *find* a disagreement
the discipline missed, fixing it is a notebook chore — do it in the
same session and note it in today's log.

---

## Working with execution

At orientation, read the index and relevant notes. A task brief links the theory
and evidence needed by a fresh agent. At a meaningful finding, preserve the setup,
observations, interpretation, limitations and how to reproduce it; correct affected
current notes and update the index when its map changes. Avoid duplicating the same
narrative across task notes, daily logs and digests.

Chores need no research entry. Notebook-only corrections or reading notes need no
manufactured execution task. `portfolio-cycle` handles research discussion and
charter drafting; `charter-cycle` executes the resulting requirements.

---

## What does NOT go in the notebook

- Work orders, acceptance criteria, queue state → `.tasks/` + `TASKS.md`.
- Per-task completion records → debriefs. Link them; don't copy them.
- Code documentation (how to run, API contracts) → `README`/`AGENTS.md`
  or docstrings.
- Raw artefacts (checkpoints, big CSVs, plots' source data) → keep out
  of git or in the repo's data conventions; the notebook records the
  *numbers that matter* and the command to regenerate the rest.
- Anything you'd be tempted to auto-generate wholesale. The notebook
  is a curated instrument; generated dumps destroy its signal density.

---

## Obsidian compatibility

The notebook is designed to be openable as an Obsidian vault
(`Open folder as vault` → the repo root or `notebook/`) with zero
conversion, while remaining plain Markdown for everyone else. To keep
that true:

- CommonMark + YAML frontmatter + relative links only. No Obsidian
  plugins' custom syntax (Dataview queries, templater tags) in
  committed notes — they're invisible landmines for non-Obsidian
  readers and agents.
- Blockquote callouts (`> **CORRECTION...:**`) rather than Obsidian's
  `> [!note]` admonitions; both render everywhere, the former reads
  better as plain text.
- Filenames are slugs (`keying-wall.md`), lowercase, hyphenated — they
  double as stable link targets and readable Obsidian titles.
- Human edits made *in* Obsidian are ordinary edits to tracked files;
  commit them like any other change (`notebook: <what>`).

---

## Bootstrapping an existing project

For a repo that already has organic research docs (a `docs/theory/`
directory, state-of-play files, a narrative-heavy `TASKS.md`):

1. Create the `notebook/` skeleton from the templates; write `INDEX.md`
   first, as a map over the *existing* docs.
2. Migrate incrementally, not big-bang: when a task touches an old
   doc's territory, distill it into proper notes then, and leave a
   stub in the old location pointing at the new note. State-of-play
   style documents usually split into one `log/` entry (the narrative
   parts) plus several `notes/` (the durable claims).
3. Trim `TASKS.md`'s narrative down to a pointer at `INDEX.md` once
   the map covers it.
4. Treat the bootstrap itself as a filed task (it's multi-session and
   benefits from review), but each incremental migration is part of
   whatever task motivated it.
