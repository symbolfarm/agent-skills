# AS-4: Point digest at the standard-library explainer builder

**Blocked by:** nothing
**Depends-on (external):** adus-intelligence G-096
**Touches:** `skills/digest/SKILL.md`

## Context

Portfolio G-087 selected a promoted, config-driven form of `adus-intelligence/site/build.py` as the common explainer substrate. G-096 builds that contract. The digest skill still calls the substrate unresolved, which would direct future goal close-outs back to one-off HTML or project-local guesswork.

## Goal

Replace the stale caveat with a concrete instruction naming the standard-library builder while preserving project ownership of page configuration, templates, styles and committed output.

## Acceptance criteria

- [ ] The digest skill names `adus-intelligence/site/build.py` and its config-driven invocation.
- [ ] The instruction says generated HTML remains committed and `--check` verifies byte reproducibility.
- [ ] The instruction preserves existing hand-authored project substrates rather than forcing migration.
- [ ] The skill no longer says the substrate is unresolved.

## Relevant files

- `skills/digest/SKILL.md`
- External contract: `/workspace/portfolio/EXPLAINERS.md`
- External implementation: `/workspace/adus-intelligence/site/build.py`

## Decisions already made

- G-087 chose the dependency-free ADUS builder contract over Pandoc, MkDocs and Jekyll.
- The common convention does not force conversion of hand-authored static sites.

## Out of scope

Implementing or testing the builder itself; G-096 lands that in `adus-intelligence` after this explicit cross-repository work order.
