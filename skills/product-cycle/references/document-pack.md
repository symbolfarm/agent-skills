# Document pack

The recipient approaches the product twice: as a user who wants it to work,
and as a developer who wants to change it. The pack serves both. Keep it in
the repository, update it in the same merge as the change it describes, and
keep every document readable without the others open.

| Document | For | Contents |
|---|---|---|
| `README.md` | everyone | What it is in two sentences, a screenshot, quick-start commands that pass the first-touch gate, and links to the rest. |
| `docs/user-guide.md` | users | How to use every feature, what each indicator means, how to turn on debug views, known limits. |
| `docs/developer-guide.md` | developers | Architecture with a diagram, how to build, test and run in each mode, where each concern lives, and every extension point with its contract and a worked example of adding one. |
| `DECISIONS.md` | owner, developers | One entry per consequential choice: date, choice, alternatives, reason, how to reverse it, and which agent made it. Append-only; corrections are new entries. |
| `PLAN.md` | the next run | Purpose, recipient, current ranked backlog with reasons. |
| `docs/acceptance.md` | owner | Each acceptance example, how it was checked, and its result or pass rate, with evidence links. |
| `docs/security.md` | owner, developers | Threat model, scanners run, findings and actions. |
| `docs/deploy.md` | owner | How to deploy, required headers or settings, licences of shipped assets, and whether anything has been published. |
| handover (Markdown, or an interactive page) | owner | Every requirement with where it is implemented, which check covers it and whether it passes; polish scores; security findings; scorecard; what changed this run; top of the backlog. |
| `docs/retro.md` | the build process | Time, tokens and spend by phase, which agents did what, what went well, what slowed the build, and what should change for the next one. |

For a build under an hour, `README.md`, `DECISIONS.md` and a short handover
are enough. Say in the handover which documents were skipped.

Generated documents (for example a handover page built from test results)
are built by a script committed alongside them, so they can be regenerated
after any change.
