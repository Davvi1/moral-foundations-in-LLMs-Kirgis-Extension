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
