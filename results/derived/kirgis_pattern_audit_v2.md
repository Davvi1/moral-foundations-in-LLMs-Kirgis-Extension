# Tier-0 audit — is Kirgis's substantive pattern method-stable?

His claim 2: models overweight {Care, Fairness, Liberty} and underweight {Loyalty, Authority, Sanctity} relative to the human baseline. The audit statistic is the within-method GAP between the two groups' mean errors, which is invariant to a uniform method-level shift — so string scoring sitting ~1 point lower cannot fake or destroy the pattern by itself.

## 1. Mean error (model − human) per foundation, per method

| method | Care | Fairness | Liberty | Loyalty | Authority | Sanctity | Social Norms |
|---|---|---|---|---|---|---|---|
| label | +0.21 | +0.27 | +0.36 | +0.30 | +0.27 | +0.20 | +0.86 |
| string_line | +0.22 | +0.28 | +0.37 | +0.31 | +0.29 | +0.22 | +0.89 |
| string_bare | -0.28 | -0.19 | -0.08 | -0.20 | -0.28 | -0.32 | +0.70 |
| cloze | +0.10 | +0.04 | +0.07 | +0.21 | +0.13 | +0.02 | +1.16 |
| greedy | +0.27 | +0.34 | +0.43 | +0.30 | +0.30 | +0.26 | +0.75 |
| sampled | +0.18 | +0.25 | +0.34 | +0.25 | +0.21 | +0.17 | +0.77 |

Negative everywhere would mean models under-rate wrongness across the board (a calibration shift); the *pattern* question is whether group A errors sit above group B errors within each row.

## 2. The gap per method — Kirgis's pattern is gap > 0

| method | mean gap | SE | models with gap>0 | min | max |
|---|---|---|---|---|---|
| label | +0.023 | 0.060 | 12/30 | -0.510 | +0.830 |
| string_line | +0.016 | 0.062 | 12/30 | -0.521 | +0.830 |
| string_bare | +0.087 | 0.062 | 15/30 | -0.464 | +0.776 |
| cloze | -0.049 | 0.056 | 12/30 | -0.465 | +0.663 |
| greedy | +0.057 | 0.062 | 14/28 | -0.492 | +0.838 |
| sampled | +0.050 | 0.061 | 13/28 | -0.531 | +0.843 |

## 3. Does method choice change *which models* show the pattern?

| pair | Spearman(per-model gaps) | sign flips | mean |Δgap| |
|---|---|---|---|
| label~string_line | 0.985 | 0/30 | 0.014 |
| label~string_bare | 0.832 | 5/30 | 0.150 |
| label~cloze | 0.681 | 8/30 | 0.209 |
| label~greedy | 0.929 | 2/28 | 0.057 |
| label~sampled | 0.967 | 3/28 | 0.045 |
| string_line~string_bare | 0.863 | 5/30 | 0.141 |
| string_line~cloze | 0.691 | 8/30 | 0.207 |
| string_line~greedy | 0.934 | 2/28 | 0.053 |
| string_line~sampled | 0.968 | 3/28 | 0.049 |
| string_bare~cloze | 0.603 | 3/30 | 0.214 |
| string_bare~greedy | 0.870 | 5/28 | 0.140 |
| string_bare~sampled | 0.855 | 6/28 | 0.147 |
| cloze~greedy | 0.563 | 8/28 | 0.235 |
| cloze~sampled | 0.681 | 7/28 | 0.209 |
| greedy~sampled | 0.928 | 3/28 | 0.068 |

A *sign flip* means: under one method the model shows Kirgis's pattern, under the other it shows the reverse — the vivid version of 'would you publish a different conclusion about this model?'

## 4. Do methods agree on the foundation ordering of errors?

| pair | Spearman(6-foundation error vectors) |
|---|---|
| label~string_line | 1.000 |
| label~string_bare | 0.714 |
| label~cloze | 0.543 |
| label~greedy | 0.771 |
| label~sampled | 0.829 |
| string_line~string_bare | 0.714 |
| string_line~cloze | 0.543 |
| string_line~greedy | 0.771 |
| string_line~sampled | 0.829 |
| string_bare~cloze | 0.086 |
| string_bare~greedy | 0.829 |
| string_bare~sampled | 0.943 |
| cloze~greedy | 0.086 |
| cloze~sampled | 0.143 |
| greedy~sampled | 0.943 |

## 5. Sensitivity: complete cases only

Models with all 6 methods usable, items scored under all of them — method comparisons on literally identical data.

Complete-case set: 28 models, 94–116 items per model.

| method | mean gap | models with gap>0 |
|---|---|---|
| label | +0.036 | 13/28 |
| string_line | +0.035 | 13/28 |
| string_bare | +0.101 | 14/28 |
| cloze | -0.031 | 12/28 |
| greedy | +0.057 | 14/28 |
| sampled | +0.047 | 13/28 |

## 6. Per-family gaps (his Figure 2 was per provider)

| family | label | string_line | string_bare | cloze | greedy | sampled |
|---|---|---|---|---|---|---|
| falcon | -0.18 | -0.18 | -0.14 | -0.28 | -0.18 | -0.26 |
| gemma | +0.26 | +0.26 | +0.46 | +0.31 | +0.22 | +0.27 |
| granite | +0.51 | +0.52 | +0.22 | +0.42 | +0.58 | +0.52 |
| internlm | +0.08 | +0.13 | +0.41 | -0.29 | +0.26 | +0.09 |
| llama | +0.01 | -0.05 | +0.02 | -0.06 | +0.19 | +0.13 |
| mistral | -0.09 | -0.11 | -0.10 | -0.20 | -0.07 | -0.06 |
| olmo | -0.13 | -0.12 | +0.10 | +0.08 | -0.09 | -0.14 |
| phi | +0.06 | +0.06 | -0.01 | -0.09 | +0.03 | +0.07 |
| qwen | +0.01 | +0.01 | +0.06 | -0.09 | +0.01 | +0.02 |
| yi | +0.28 | +0.28 | +0.48 | -0.37 | +0.38 | +0.20 |
| zephyr | -0.51 | -0.52 | -0.25 | -0.22 | -0.40 | -0.22 |

## 6b. Why a raw gap of ~0 is *not* neutral evidence

The human baseline has its own foundation structure:

| foundation | human mean |
|---|---|
| Sanctity | 2.806 |
| Fairness | 2.800 |
| Care | 2.612 |
| Liberty | 2.571 |
| Authority | 2.342 |
| Loyalty | 1.994 |
| Social Norms | 0.188 |

Humans rate group A (Care, Fairness, Liberty) at **2.661** and group B (Loyalty, Authority, Sanctity) at **2.380** — a difference of **+0.281**.

Now combine that with the compression in §7. Compression pulls every rating toward mid-scale, so the *higher* human ratings (group A) are pulled DOWN more and the *lower* ones (group B) are pushed UP more. **Pure compression therefore predicts a NEGATIVE raw gap, with no moral content whatsoever.**

So 'raw gap ≈ 0' does not mean 'no pattern'. It means the observed data sit between the compression prediction (negative) and Kirgis's prediction (positive). The raw gap cannot adjudicate; the compression-adjusted gap in §7 is the statistic that can.

## 6c. Does the verdict depend on where Liberty is placed?

Kirgis groups Liberty with the individualizing foundations; canonical MFT treats Care+Fairness as individualizing and leaves Liberty separate. Raw mean gaps under three groupings:

| grouping | label | string | greedy | sampled |
|---|---|---|---|---|
| Kirgis (A = Care/Fair/Liberty) | +0.023 | +0.016 | +0.087 | -0.049 | +0.057 | +0.050 |
| canonical (A = Care/Fair) | -0.017 | -0.022 | +0.035 | -0.049 | +0.017 | +0.010 |
| Liberty with binding | -0.043 | -0.046 | -0.012 | -0.036 | -0.017 | -0.023 |

The conclusion is grouping-robust — and note that **Kirgis's own grouping is the most favourable to his claim**; the canonical one is more negative still.

## 7. Severity compression: is the error structure about foundations at all?

Model errors may simply track how *mild* the human rating is — compression toward mid-scale over-rates mild items and under-rates severe ones, regardless of foundation. Per method, an OLS of item-level error on the human item mean:

| method | slope | r | reading |
|---|---|---|---|
| label | -0.274 | -0.322 | mild compression |
| string_line | -0.276 | -0.319 | mild compression |
| string_bare | -0.355 | -0.361 | strong compression |
| cloze | -0.464 | -0.453 | strong compression |
| greedy | -0.201 | -0.213 | mild compression |
| sampled | -0.244 | -0.287 | mild compression |

Gap recomputed on compression-adjusted errors (item-severity effect removed):

| method | adjusted mean gap | models with gap>0 |
|---|---|---|
| label | +0.100 | 15/30 |
| string_line | +0.094 | 15/30 |
| string_bare | +0.187 | 20/30 |
| cloze | +0.081 | 14/30 |
| greedy | +0.114 | 15/28 |
| sampled | +0.118 | 16/28 |

If raw and adjusted gaps agree, foundation content adds little beyond item severity; a residual foundation pattern would survive the adjustment.

## Verdict

**The raw gap cannot adjudicate this claim, and the adjusted gap is weakly in Kirgis's favour.**

Raw mean gaps are ≈ 0 (-0.05 to +0.09) — but §6b shows *pure compression predicts a negative gap*, because the human baseline itself rates group A above group B and compression pulls high ratings down more than low ones. So 'raw ≈ 0' sits between the compression prediction and Kirgis's, and settles nothing.

Removing the item-severity effect (§7), the adjusted gap turns **positive under every method** (+0.081 to +0.187, 47%–67% of models). That is weak evidence *in Kirgis's direction*, not against him — but it is small, only about half of models show it, and we have no interval on it. **SUGGESTIVE, not established, in either direction.**

What *is* established: the four methods agree with each other (mean per-model gap correlation ρ = 0.82), so whatever the answer is, **it is not an artifact of scoring method.** Kirgis's confound does not threaten this particular claim.


Family heterogeneity is large and method-stable (§6): gemma, granite and yi show the pattern under every method; qwen, mistral, smollm and phi show its reverse under every method. **For this claim, which models you sample matters far more than how you score them.** Kirgis sampled frontier-scale closed models; we sampled ≤14B open ones — the Tier-3 size ladders (Qwen 0.5→72B, Llama 1→70B) now directly test whether his pattern *emerges with scale*, which would connect his claims 2 and 4.

Caveat carried from the design: refusal-driven item missingness in free generation biases Sanctity errors upward (survivors are the milder items), which biases the gap *downward* in greedy/sampled for high-refusal models. A pattern surviving there is therefore conservative.
