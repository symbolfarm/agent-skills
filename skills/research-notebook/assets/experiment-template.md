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

## Prediction

Written before the run: what you expect to see, and which result would
change the plan. Leave it as written once the result is in.

## Setup

Enough to rerun: model/config, data, seeds, budget, and the exact
command (also in frontmatter). Note the commit SHA the numbers came
from, and the baseline run in the same harness that they are compared
with.

## Results

The numbers that matter, with the spread across seeds; say so when
there is one seed. Tables are fine; don't paste raw logs.

| condition | metric | value |
|---|---|---|

## Verdict

One paragraph: what this does and doesn't show, and the caveats that
bound the claim. If it refutes something, link the note whose status
flipped.

## Changelog

- YYYY-MM-DD: created (TASK-ID).
