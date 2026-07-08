---
status: live
tags: []
tasks: [TASK-ID]
command: ".venv/bin/python -m tests.some_experiment"
verdict: supports   # supports | refutes | inconclusive
---

# [TASK-ID] Experiment title

## Hypothesis

What this experiment was designed to establish or rule out, stated
before the results.

## Setup

Enough to rerun: model/config, data, seeds, budget, and the exact
command (also in frontmatter). Note the commit SHA the numbers came
from.

## Results

The numbers that matter, with variance where measured. Tables are
fine; don't paste raw logs.

| condition | metric | value |
|---|---|---|

## Verdict

One paragraph: what this does and doesn't show, and the caveats that
bound the claim. If it refutes something, link the note whose status
flipped.

## Changelog

- YYYY-MM-DD: created (TASK-ID).
