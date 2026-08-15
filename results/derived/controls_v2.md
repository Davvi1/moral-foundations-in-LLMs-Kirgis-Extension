# Step 5 — pre-specified controls

## 1. Permutation null

Method labels shuffled within model x item, R recomputed. R must collapse toward 0: with the labels meaningless there is no model x method interaction left to find.

**Deviation, stated:** the analysis plan specified the same Bayesian model. That is ~700 MCMC fits (~12 h). The null is a calibration check, not an inferential quantity, so it uses the ANOVA moment estimator from the B2 design simulation.

| foundation | block (M x K x I) | observed R | null median | null 95% | observed above null? |
|---|---|---|---|---|---|
| Authority | 27x5x17 | 0.401 | -0.071 | [-0.100, -0.030] | **YES** |
| Care | 26x5x16 | 0.199 | -0.091 | [-0.112, -0.060] | **YES** |
| Fairness | 27x5x17 | 0.589 | -0.066 | [-0.096, -0.021] | **YES** |
| Liberty | 25x5x17 | 0.354 | -0.074 | [-0.099, -0.033] | **YES** |
| Loyalty | 26x5x16 | 0.153 | -0.048 | [-0.059, -0.032] | **YES** |
| Sanctity | 23x5x17 | 0.391 | -0.151 | [-0.184, -0.098] | **YES** |
| Social Norms | 26x5x16 | 0.101 | -0.019 | [-0.024, -0.013] | **YES** |

A null median near 0 means the pipeline is calibrated. If the observed R does not exceed the null interval, the data provide no evidence of a model x method interaction beyond what label-shuffling produces by chance.

## 2. Positive control — Sanctity above Social Norms

Clifford's human means put purity violations far above social-norm violations. Any method that fails to reproduce that ordering is not measuring moral severity.

Human baseline: Sanctity 2.81, Social Norms 0.19, gap 2.62

| method | Sanctity | Social Norms | gap | passes? |
|---|---|---|---|---|
| label | 3.004 | 1.049 | 1.955 | PASS |
| string_line | 3.022 | 1.076 | 1.947 | PASS |
| string_bare | 2.489 | 0.886 | 1.603 | PASS |
| greedy | 3.067 | 0.934 | 2.133 | PASS |
| sampled | 2.973 | 0.960 | 2.013 | PASS |

**All four methods pass.**

## 3. Rank agreement (descriptive only — no threshold)

Spearman rho of the model ordering under each pair of methods, within foundation, after centring out the method main effect. **No pass/fail line is attached**: at this N the statistic is too blunt to carry one, as the B2 simulation showed.

| foundation | lab~str | lab~str | lab~gre | lab~sam | str~str | str~gre | str~sam | str~gre | str~sam | gre~sam |
|---|---|---|---|---|---|---|---|---|---|---|
| Authority | 0.85 | 0.35 | 0.94 | 0.79 | 0.20 | 0.93 | 0.74 | 0.32 | 0.38 | 0.72 |
| Care | 0.98 | 0.68 | 0.97 | 0.84 | 0.65 | 0.96 | 0.82 | 0.66 | 0.73 | 0.77 |
| Fairness | 0.96 | 0.19 | 0.87 | 0.77 | 0.17 | 0.87 | 0.73 | 0.19 | 0.33 | 0.66 |
| Liberty | 1.00 | 0.38 | 0.85 | 0.83 | 0.39 | 0.85 | 0.83 | 0.41 | 0.49 | 0.72 |
| Loyalty | 0.99 | 0.50 | 0.94 | 0.84 | 0.49 | 0.94 | 0.84 | 0.38 | 0.41 | 0.86 |
| Sanctity | 0.99 | 0.39 | 0.98 | 0.83 | 0.37 | 0.98 | 0.82 | 0.39 | 0.50 | 0.82 |
| Social Norms | 1.00 | 0.62 | 0.96 | 0.96 | 0.63 | 0.95 | 0.95 | 0.63 | 0.49 | 0.95 |

Mean rho per pair across foundations:

- **label ~ string_line**: 0.968  (min 0.855, max 0.996, n=7)
- **label ~ string_bare**: 0.445  (min 0.192, max 0.675, n=7)
- **label ~ greedy**: 0.927  (min 0.846, max 0.982, n=7)
- **label ~ sampled**: 0.838  (min 0.771, max 0.956, n=7)
- **string_line ~ string_bare**: 0.413  (min 0.168, max 0.649, n=7)
- **string_line ~ greedy**: 0.927  (min 0.852, max 0.981, n=7)
- **string_line ~ sampled**: 0.817  (min 0.731, max 0.946, n=7)
- **string_bare ~ greedy**: 0.425  (min 0.190, max 0.660, n=7)
- **string_bare ~ sampled**: 0.474  (min 0.330, max 0.727, n=7)
- **greedy ~ sampled**: 0.786  (min 0.659, max 0.947, n=7)

## 4. Pairwise R — every method pair, on one common block

R is defined over whichever arms enter the fit, so a single scalar is a property of that chosen set rather than of the models. This table removes the choice: each cell is R for a two-arm design, computed with the section-1 moment estimator on ONE complete-case block per foundation, so every cell is comparable to every other.

Averaged over the six moral foundations. **Social Norms is Clifford's non-moral control and is reported separately, never averaged in.**

Rows/columns marked † vary the PROMPT as well as the readout, so their cells are not method contrasts (C15). They are shown because the point of the table is to make every arm's contribution visible.

| | label | string_line | string_bare | cloze† | greedy | sampled |
|---|---|---|---|---|---|---|
| **label** | — | -0.09 | 1.21 | 2.72 | -0.07 | 0.08 |
| **string_line** | -0.09 | — | 1.33 | 2.52 | -0.07 | 0.12 |
| **string_bare** | 1.21 | 1.33 | — | 4.32 | 1.26 | 0.62 |
| **cloze†** | 2.72 | 2.52 | 4.32 | — | 2.61 | 4.32 |
| **greedy** | -0.07 | -0.07 | 1.26 | 2.61 | — | 0.20 |
| **sampled** | 0.08 | 0.12 | 0.62 | 4.32 | 0.20 | — |

Blocks (models x items): Authority 27x17, Care 26x16, Fairness 27x17, Liberty 25x17, Loyalty 26x16, Sanctity 23x17, Social Norms 26x16

Sorted, with mean retained probability mass for the probability arms — the column that explains the ordering:

| pair | R (6 moral) | control alone | mass, arm A | mass, arm B |
|---|---:|---:|---:|---:|
| label ~ string_line | **-0.086** | -0.021 | 0.7680 | 0.6278 |
| string_line ~ greedy | **-0.067** | 0.004 | 0.6278 | — |
| label ~ greedy | **-0.067** | 0.007 | 0.7680 | — |
| label ~ sampled | **0.081** | -0.009 | 0.7680 | — |
| string_line ~ sampled | **0.117** | 0.001 | 0.6278 | — |
| greedy ~ sampled | **0.197** | 0.006 | — | — |
| string_bare ~ sampled | **0.623** | 0.386 | 0.0028 | — |
| label ~ string_bare | **1.212** | 0.366 | 0.7680 | 0.0028 |
| string_bare ~ greedy | **1.263** | 0.328 | 0.0028 | — |
| string_line ~ string_bare | **1.326** | 0.338 | 0.6278 | 0.0028 |
| string_line ~ cloze† | **2.523** | 1.026 | 0.6278 | 0.0462 |
| cloze† ~ greedy | **2.606** | 1.394 | 0.0462 | — |
| label ~ cloze† | **2.721** | 1.084 | 0.7680 | 0.0462 |
| string_bare ~ cloze† | **4.317** | 1.625 | 0.0028 | 0.0462 |
| cloze† ~ sampled | **4.321** | 1.275 | 0.0462 | — |

Negative values are moment-estimator truncation — the interaction variance is below what residual noise alone produces — and a Bayesian fit with a half-normal prior on the SD would return a small positive number instead. Read them as 'indistinguishable from no interaction', not as a magnitude.

## 5. Leave-one-model-out — how concentrated is R?

R is a ratio of variance components estimated over ~27 models. Every robustness check run before 2026-08-15 varied the ARMS (C15, scan-exclusion, family effect); none varied the MODELS. This section asks whether R is a property of the roster or of a few models in it.

Cloze is excluded throughout, as everywhere else in this file.

Baseline R (moment estimator, mean over the six moral foundations): **0.348**. 27 models enter at least one block, so an equal share of the interaction sum of squares would be **3.7%** each.

| model | share of interaction SS | R without it | change in R |
|---|---:|---:|---:|
| mistralai/Mistral-7B-Instruct-v0.3 | 34.3% | 0.171 | -51% |
| Qwen/Qwen2.5-3B-Instruct | 11.4% | 0.306 | -12% |
| Qwen/Qwen2-7B-Instruct | 5.9% | 0.320 | -8% |
| google/gemma-2-9b-it | 5.2% | 0.315 | -10% |
| microsoft/Phi-3-mini-4k-instruct | 5.1% | 0.325 | -7% |
| HuggingFaceH4/zephyr-7b-beta | 4.5% | 0.368 | +6% |
| *mean of the remaining 21* | *1.6%* | — | — |

**mistralai/Mistral-7B-Instruct-v0.3 alone carries 34.3% of the interaction sum of squares** — 9.3x the average model's contribution — and dropping it moves R by -51%. That is the same order as C15, from one model rather than one arm.

Read it alongside section 4 and `LIMITATIONS.md` 3: the concentration is not a coincidence, it is the same finding from a different direction. The models that dominate the interaction are the ones whose probability readouts sit on almost no retained mass, so the method effect is carried by cells the design can barely measure.
