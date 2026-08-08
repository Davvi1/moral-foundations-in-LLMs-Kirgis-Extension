# Tier-0 audit — is Kirgis's substantive pattern method-stable?

His claim 2: models overweight {Care, Fairness, Liberty} and underweight {Loyalty, Authority, Sanctity} relative to the human baseline. The audit statistic is the within-method GAP between the two groups' mean errors, which is invariant to a uniform method-level shift — so string scoring sitting ~1 point lower cannot fake or destroy the pattern by itself.

## 1. Mean error (model − human) per foundation, per method

| method | Care | Fairness | Liberty | Loyalty | Authority | Sanctity | Social Norms |
|---|---|---|---|---|---|---|---|
| label | +0.12 | +0.19 | +0.37 | +0.37 | +0.24 | +0.16 | +1.05 |
| string | -0.99 | -1.01 | -0.82 | -0.57 | -0.77 | -1.09 | +0.82 |
| greedy | +0.24 | +0.32 | +0.50 | +0.43 | +0.27 | +0.28 | +0.90 |
| sampled | +0.14 | +0.21 | +0.38 | +0.40 | +0.20 | +0.16 | +0.97 |

Negative everywhere would mean models under-rate wrongness across the board (a calibration shift); the *pattern* question is whether group A errors sit above group B errors within each row.

## 2. The gap per method — Kirgis's pattern is gap > 0

| method | mean gap | SE | models with gap>0 | min | max |
|---|---|---|---|---|---|
| label | -0.033 | 0.068 | 6/20 | -0.497 | +0.513 |
| string | -0.128 | 0.041 | 5/19 | -0.341 | +0.227 |
| greedy | +0.029 | 0.075 | 9/18 | -0.492 | +0.626 |
| sampled | -0.013 | 0.072 | 8/18 | -0.510 | +0.525 |

## 3. Does method choice change *which models* show the pattern?

| pair | Spearman(per-model gaps) | sign flips | mean |Δgap| |
|---|---|---|---|
| label~string | 0.667 | 4/19 | 0.164 |
| label~greedy | 0.924 | 3/18 | 0.083 |
| label~sampled | 0.979 | 2/18 | 0.033 |
| string~greedy | 0.779 | 5/17 | 0.180 |
| string~sampled | 0.723 | 4/17 | 0.170 |
| greedy~sampled | 0.957 | 1/18 | 0.067 |

A *sign flip* means: under one method the model shows Kirgis's pattern, under the other it shows the reverse — the vivid version of 'would you publish a different conclusion about this model?'

## 4. Do methods agree on the foundation ordering of errors?

| pair | Spearman(6-foundation error vectors) |
|---|---|
| label~string | 0.771 |
| label~greedy | 0.771 |
| label~sampled | 0.943 |
| string~greedy | 0.257 |
| string~sampled | 0.600 |
| greedy~sampled | 0.886 |

## 5. Sensitivity: complete cases only

Models with all four methods usable, items scored under all four — method comparisons on literally identical data.

Complete-case set: 17 models, 110–116 items per model.

| method | mean gap | models with gap>0 |
|---|---|---|
| label | -0.021 | 6/17 |
| string | -0.114 | 4/17 |
| greedy | +0.015 | 8/17 |
| sampled | -0.012 | 7/17 |

## 6. Per-family gaps (his Figure 2 was per provider)

| family | label | string | greedy | sampled |
|---|---|---|---|---|
| gemma | +0.46 | +0.02 | +0.40 | +0.40 |
| granite | +0.51 | -0.01 | +0.63 | +0.52 |
| internlm | +0.08 | — | +0.26 | +0.09 |
| llama | -0.13 | -0.17 | +0.08 | -0.04 |
| mistral | -0.17 | -0.23 | -0.24 | -0.22 |
| olmo | -0.15 | -0.04 | -0.08 | -0.16 |
| phi | -0.11 | -0.21 | -0.09 | -0.12 |
| qwen | -0.17 | -0.17 | -0.17 | -0.17 |
| smollm | -0.30 | -0.31 | -0.26 | -0.24 |
| yi | +0.27 | +0.15 | +0.38 | +0.28 |

## 7. Severity compression: is the error structure about foundations at all?

Model errors may simply track how *mild* the human rating is — compression toward mid-scale over-rates mild items and under-rates severe ones, regardless of foundation. Per method, an OLS of item-level error on the human item mean:

| method | slope | r | reading |
|---|---|---|---|
| label | -0.366 | -0.414 | strong compression |
| string | -0.713 | -0.722 | strong compression |
| greedy | -0.273 | -0.275 | mild compression |
| sampled | -0.336 | -0.372 | strong compression |

Gap recomputed on compression-adjusted errors (item-severity effect removed):

| method | adjusted mean gap | models with gap>0 |
|---|---|---|
| label | +0.070 | 9/20 |
| string | +0.073 | 11/19 |
| greedy | +0.106 | 10/18 |
| sampled | +0.081 | 8/18 |

If raw and adjusted gaps agree, foundation content adds little beyond item severity; a residual foundation pattern would survive the adjustment.

## Verdict

**The pattern is ABSENT under every method — and the methods agree.** Mean gaps are ≈ 0 (range -0.13 to +0.03); the share of models showing the pattern never exceeds 50%; yet per-model gaps correlate strongly across methods (mean ρ = 0.84). **This is a replication failure on this sample, not a method-instability result** — the four estimators concur that ≤14B open-weight models do not show the individualizing-over-binding overweight Kirgis reported for frontier models. Do not conflate the two readings: his *pattern* did not appear here; his *methods* would have agreed with each other if it had.

Family heterogeneity is large and method-stable (§6): gemma, granite and yi show the pattern under every method; qwen, mistral, smollm and phi show its reverse under every method. **For this claim, which models you sample matters far more than how you score them.** Kirgis sampled frontier-scale closed models; we sampled ≤14B open ones — the Tier-3 size ladders (Qwen 0.5→72B, Llama 1→70B) now directly test whether his pattern *emerges with scale*, which would connect his claims 2 and 4.

Caveat carried from the design: refusal-driven item missingness in free generation biases Sanctity errors upward (survivors are the milder items), which biases the gap *downward* in greedy/sampled for high-refusal models. A pattern surviving there is therefore conservative.
