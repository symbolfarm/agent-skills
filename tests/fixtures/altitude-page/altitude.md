# One result, two months ago.

*Fixture, not a publication.* This reproduces the structure of a private
2026-09-16 altitude page from Markdown source, to prove the three block
components can carry it. Project names, figures and the owner's name are
generalised; the published page stays hand-authored and is not converted.

This lane is trying to show that a network can *gain a capability by being built onto* rather than trained — reaching what gradient descent reaches, without touching a single existing weight, in one pass as the data arrives. It did that once, two months ago, on one synthetic task. Everything since has been about whether that result can be trusted. This page is for deciding whether that is still the right use of the next month.

> **The call this page is for.** The capability claim has **one data point**. The eight weeks since have gone into reversibility, accumulation, safety and instrument quality — all real, none of it moving the headline. The question is not whether the work was good. It is whether the *toy* is finished.

## 1 · What this lane is for, in one page

Training a network on something new moves its existing weights, so it can quietly lose what it already knew. The usual defences — replay the old data, constrain the update, keep a copy — all cost something, and none of them makes forgetting *impossible*.

**The alternative under test:** leave every existing weight alone and put the new capability in *new* parameters bolted alongside. Then forgetting is not merely unlikely; it is structurally unavailable, because nothing that held the old capability was touched.

> **The north star, and what it is not.** We are *not* trying to beat gradient descent. A tuned network already solves these tasks; that is the target, not the problem. The claim is that a **constructive** algorithm can reach the *same* capability while having two properties training lacks — it is **additive** (old weights untouched, bit-for-bit) and **online** (one pass, zero gradient steps, no retraining loop). Success is parity on three axes, none of which is "better".

<svg viewBox="0 0 900 300" role="img" aria-labelledby="cw-t cw-d"><title id="cw-t">Training versus construction</title><desc id="cw-d">Above: gradient training takes a network and new data and returns the same network with all weights changed, so old capability may be lost. Below: construction takes the same network and new data and returns the original network unchanged plus a new added block, so old capability is preserved by structure.</desc><defs><marker id="ar3" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto"><path d="M0 0L10 5L0 10z" fill="var(--accent)"/></marker><pattern id="fz3" width="8" height="8" patternUnits="userSpaceOnUse" patternTransform="rotate(45)"><rect width="8" height="8" fill="var(--frozen)"/><path d="M0 0V8" stroke="var(--line)" stroke-width="2"/></pattern></defs><g font-family="ui-sans-serif, sans-serif">
<text x="20" y="28" class="svg-soft" font-size="13" font-weight="700">GRADIENT TRAINING</text>
<rect x="20" y="42" width="120" height="62" rx="7" fill="var(--paper)" stroke="var(--line)"/><text x="80" y="70" text-anchor="middle" class="svg-ink" font-weight="700">network</text><text x="80" y="90" text-anchor="middle" class="svg-soft" font-size="12">knows A</text>
<text x="168" y="66" text-anchor="middle" class="svg-soft" font-size="13">+ data B</text><path d="M145 80H205" stroke="var(--accent)" stroke-width="2" marker-end="url(#ar3)"/>
<rect x="215" y="42" width="150" height="62" rx="7" fill="var(--warnbg)" stroke="var(--warn)" stroke-width="2"/><text x="290" y="70" text-anchor="middle" class="svg-ink" font-weight="700">all weights move</text><text x="290" y="90" text-anchor="middle" class="svg-soft" font-size="12">many gradient steps</text>
<path d="M365 73H415" stroke="var(--accent)" stroke-width="2" marker-end="url(#ar3)"/>
<rect x="425" y="42" width="150" height="62" rx="7" fill="var(--paper)" stroke="var(--line)"/><text x="500" y="70" text-anchor="middle" class="svg-ink" font-weight="700">knows B</text><text x="500" y="90" text-anchor="middle" class="svg-ink" font-size="12" font-weight="700">A is at risk</text>
<text x="600" y="68" class="svg-soft" font-size="12">defences cost data,</text><text x="600" y="86" class="svg-soft" font-size="12">compute, or a saved copy</text>
<path d="M20 140H880" stroke="var(--line)" stroke-dasharray="4 4"/>
<text x="20" y="176" class="svg-soft" font-size="13" font-weight="700">CONSTRUCTION</text>
<rect x="20" y="190" width="120" height="62" rx="7" fill="url(#fz3)" stroke="var(--line)"/><text x="80" y="218" text-anchor="middle" class="svg-ink" font-weight="700">network</text><text x="80" y="238" text-anchor="middle" class="svg-soft" font-size="12">frozen</text>
<text x="168" y="214" text-anchor="middle" class="svg-soft" font-size="13">+ data B</text><path d="M145 228H205" stroke="var(--accent)" stroke-width="2" marker-end="url(#ar3)"/>
<rect x="215" y="190" width="150" height="62" rx="7" fill="var(--pale)" stroke="var(--accent)" stroke-width="2"/><text x="290" y="218" text-anchor="middle" class="svg-ink" font-weight="700">solve, don&#8217;t train</text><text x="290" y="238" text-anchor="middle" class="svg-soft" font-size="12">one pass, zero grad steps</text>
<path d="M365 221H415" stroke="var(--accent)" stroke-width="2" marker-end="url(#ar3)"/>
<rect x="425" y="190" width="105" height="62" rx="7" fill="url(#fz3)" stroke="var(--line)"/><text x="477" y="218" text-anchor="middle" class="svg-ink" font-weight="700">unchanged</text><text x="477" y="238" text-anchor="middle" class="svg-soft" font-size="12">still knows A</text>
<rect x="538" y="190" width="105" height="62" rx="7" fill="var(--pale)" stroke="var(--accent)" stroke-width="2"/><text x="590" y="218" text-anchor="middle" class="svg-ink" font-weight="700">+ block</text><text x="590" y="238" text-anchor="middle" class="svg-soft" font-size="12">knows B</text>
<text x="665" y="214" class="svg-ink" font-size="12" font-weight="700">forgetting is structurally</text><text x="665" y="232" class="svg-ink" font-size="12" font-weight="700">unavailable, not just unlikely</text>
</g></svg>

The whole bet in one picture. The cost of the lower path is that the added block must be *addressed* correctly — the system has to know when a question belongs to the new block and when it belongs to the frozen network. That addressing problem is what most of the last two months has been about.

## 2 · Where the three axes actually stand

| Axis | Best evidence | Honest limit |
| --- | --- | --- |
| **Capability parity** — construction reaches what training reaches | Held-out composition **1.000 ± 0.000** over 10 seeds against chance 0.062, with `grad_steps = 0`, `base_weight_delta = 0`, one pass. | **One task, one tiny model, and nothing since.** 64 objects, 16 attributes, 16 bins, synthetic, character-level. |
| **Additive** — old weights untouched | Removal is exact: taking the block out restores the original model's logits bit-for-bit. A later run stacked **15 blocks / 60 facts**. | Accumulation is a *lower bound* at 15 small homogeneous blocks, and it costs ~4× forward latency and +72.5 KiB per block. |
| **Online** — one pass, no retraining | Holds in every construction experiment run so far. Zero gradient steps is asserted as a test, not claimed. | Cheap to hold on a small synthetic stream. Untested where data arrives noisy, redundant or out of order. |

> **The single most important sentence on this page.** The capability axis has not moved in eight weeks. Twenty-one experiments have run since. They are not padding — they found a real constraint and built a real safety mechanism — but if you are asking "is this getting closer to its goal?", the honest answer is that it has been getting *more certain about one result* rather than getting a second one.

## 3 · Where the effort went

<svg viewBox="0 0 980 330" role="img" aria-labelledby="tl-t tl-d"><title id="tl-t">Where experiment effort went, July to September 2026</title><desc id="tl-d">A timeline from July to September 2026. One experiment in July established capability parity. A band of experiments through August and September established the addressing constraint called the keying wall. A further band established safety properties: exact removal, accumulation, a decision gate, human approval cost and attribution. The most recent band, CR-37 through CR-43, is largely instrument quality: fixing the base training, re-reading an earlier map, calibrating a threshold and re-decomposing a refuted metric.</desc><g font-family="ui-sans-serif, sans-serif">
<line x1="60" y1="286" x2="930" y2="286" stroke="var(--line)" stroke-width="2"/>
<text x="60" y="310" class="svg-soft" font-size="12">Jul 2026</text><text x="470" y="310" text-anchor="middle" class="svg-soft" font-size="12">Aug</text><text x="930" y="310" text-anchor="end" class="svg-soft" font-size="12">16 Sep</text>
<rect x="60" y="212" width="66" height="60" rx="5" fill="var(--pale)" stroke="var(--accent)" stroke-width="2"/><text x="93" y="238" text-anchor="middle" class="svg-ink" font-size="12" font-weight="700">CR-22</text><text x="93" y="256" text-anchor="middle" class="svg-soft" font-size="11">parity</text>
<text x="60" y="202" class="svg-ink" font-size="13" font-weight="700">CAPABILITY</text>
<rect x="150" y="140" width="330" height="56" rx="5" fill="var(--paper)" stroke="var(--line)"/><text x="315" y="164" text-anchor="middle" class="svg-ink" font-size="12" font-weight="700">CR-19 &#183; 20 &#183; 21 &#183; 31 &#183; 36 &#183; 38</text><text x="315" y="182" text-anchor="middle" class="svg-soft" font-size="11">the keying wall: where the key is read decides everything</text>
<text x="150" y="128" class="svg-ink" font-size="13" font-weight="700">CONSTRAINT &#8212; 6</text>
<rect x="500" y="140" width="430" height="56" rx="5" fill="var(--paper)" stroke="var(--line)"/><text x="715" y="164" text-anchor="middle" class="svg-ink" font-size="12" font-weight="700">CR-34 &#183; 35 &#183; 39 &#183; 40 &#183; 41 &#183; 42 &#183; 43</text><text x="715" y="182" text-anchor="middle" class="svg-soft" font-size="11">removal, accumulation, the gate, the human, attribution</text>
<text x="500" y="128" class="svg-ink" font-size="13" font-weight="700">SAFETY &amp; REVERSIBILITY &#8212; 7</text>
<rect x="616" y="60" width="314" height="56" rx="5" fill="var(--warnbg)" stroke="var(--warn)" stroke-width="2"/><text x="773" y="84" text-anchor="middle" class="svg-ink" font-size="12" font-weight="700">CR-25 &#183; 26 &#183; 37 &#183; 38 &#183; 43</text><text x="773" y="102" text-anchor="middle" class="svg-soft" font-size="11">fixing and re-reading our own measurements</text>
<text x="616" y="48" class="svg-ink" font-size="13" font-weight="700">INSTRUMENT &#8212; and rising</text>
<text x="60" y="36" class="svg-soft" font-size="12">Every experiment below the capability row is on the <tspan font-weight="700">same task and the same tiny model</tspan> as CR-22.</text>
</g></svg>

Counts are by what each experiment was *for*; several appear in two bands. The pattern that matters is the top band: the most recent arc is substantially work on the measuring apparatus.

## 4 · The two things this lane found that nobody handed it

**Finding 1 — the keying wall.** The framework assumed construction adds understanding. This lane found that **where you read the address matters more than what you write**. Reading the key off raw token embeddings collapses to chance as the task gets harder; reading it after the frozen stack holds.

**Finding 2 — the right human affordance is a veto.** Measured: the *best possible* approver buys **+0.002**, because the automatic threshold is already the best constant available. But a *permissive* approver damages 26 of 72 frozen bases for +0.027 — about **30:1 against**.

## 5 · Four directions, with what each costs and buys

```:option
@option
verdict: not recommended
title: A. Harden the toy

Held-out calibration, within-seat discrimination, more seeds. **Cost:** days. **Buys:** the existing results become defensible. **Against it:** this is what the lane does by default, and it moves no axis.

@option
verdict: recommended
title: B. Graduate the substrate

Run construction on a model that was not built for it. **Cost:** weeks, and real risk of finding the keying wall is fatal at scale. **Buys:** the only second capability data point available.

**The honest risk:** everything measured so far is on a character-level model with 64 synthetic objects.

@option
verdict: strong second
title: C. Redirect to routing

A router predicts which constructed block answers a query, and "no match" is what triggers construction in the first place. **Cost:** a redesign, mostly of framing. **Buys:** the principled version of what the gate experiments stumbled into empirically.

@option
verdict: viable, and no failure
title: D. Bank it and move on

Write the keying wall and the veto finding up as constraints on the framework, and put the substrate down. **Cost:** one writing goal. **Against it:** the capability claim stays at one data point, publicly, on a toy.
```

> **My recommendation, and it is a judgement the owner should overrule freely: B, with A's one-run held-out calibration folded in first.** The reason is the timeline in §3.

## 6 · What this lane is *not* for

- **Not beating gradient descent.** Parity is the target.
- **Not a memory product.** The added block looks like a key-value store, and the point is not storage.
- **Not a continual-learning benchmark.** That is a separate repository with a separate purpose.
- **Not yet evidence about real models.** Every number comes from one synthetic task on one tiny character-level model.

## 7 · Over to you

```:reading
@best
label: The decision
title: A, B, C or D — or something this page has not thought of

You suspected a direction change before reading this. I think the timeline in §3 supports that suspicion, and I would not have volunteered it as strongly if you had not raised it first — which is worth saying out loud, because it means you should weigh my recommendation a little less than you otherwise would.

@alternative
label: If you want to go deeper
title: The layer below this one

The detailed arc is in the [synthesis digest](status.md) below this page. Individual runs are immutable records in `notebook/experiments/`.
```
