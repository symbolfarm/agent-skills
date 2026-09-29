---
name: digest
description: Explain a meaningful result or research finding to its reader, leading with what changed, supporting evidence, uncertainty and implications. Use at meaningful findings, handover or charter closure.
license: MIT
metadata:
  version: "3"
---

# Digest

A digest helps a reader understand and act on a result. Write one when findings
change what the reader should understand or can do, including during an open
charter. Routine implementation tasks need no separate digest. At charter close,
synthesize what its requirements established together rather than repeating reports.

Establish the reader's existing context. An oriented reader needs the delta; a
new reader needs enough reconstruction to judge it. State the intended reader
and date, then lead with the most consequential change.

Answer, in the shape that suits the work:

- What changed, and why does it matter to the agreed direction?
- What evidence supports that? Link primary artifacts and distinguish measured
  observations from interpretations and assumptions.
- What remains uncertain or failed to match expectations?
- What happens next within existing authority, and does anything need the reader?

Recommendations are welcome when their reasoning and alternatives are clear.
Do not conflate a recommendation with a result or the user's endorsement.
Check important claims against their primary evidence: repeated summaries are
not independent corroboration. Passing tests only supports what those tests check.

Layer optional mechanism and reproducibility detail below the main account.
Use a diagram when it helps; a sentence may suffice. Give a working artifact,
example, command or link when handing over a capability. A build check alone is
not a demonstration of the requested behavior.

Keep dated digests as records, and correct important errors visibly. Link a
successor when understanding changes. The current research overview should
point to the best current account so readers need not replay the digest history.
A digest's existence proves an attempted explanation, not reader understanding.
Deliver it through the current conversation or an already authorized channel.

## Format

Write the digest as markdown in the repository that holds its evidence, at
`docs/digests/<charter-or-topic>-<YYYY-MM-DD>.md`, opening with this header:

```
---
title: A foundation the next lesson builds on
reader: project owner, oriented on the programme
date: 2026-09-30
charter: EX-C4
status: agent-authored; not human-reviewed
summary: One sentence that tells a reader scanning a list what changed.
supersedes: docs/digests/ex-c3-2026-09-27.md
---
```

`title`, `reader`, `date` and `status` are required; `charter`, `summary` and
`supersedes` are optional; no other keys are accepted. Relative links resolve
beside the file. Beyond ordinary markdown, tables and inline SVG, three block
components are available as fenced directives: `:reading` (a best reading and
an alternative), `:option` (options with verdicts) and `:status` (built,
designed and open rows). Their syntax is in the docstring of
`tools/build_pages.py` in the agent-skills repository.

Do not hand-write HTML and do not commit generated HTML. Readers' tools render
the markdown. From the repository root, with agent-skills checked out beside it,
`python3 ../agent-skills/tools/build_pages.py --digest docs/digests/<file>.md`
prints a standalone page. Run it before committing, because it is also the
header check. Do not create a site merely to deliver a short
explanation. Dated digests written before this format stay as they are.
