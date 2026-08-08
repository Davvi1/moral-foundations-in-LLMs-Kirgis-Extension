# Step 5 — pre-specified controls

## 1. Permutation null

Method labels shuffled within model x item, R recomputed. R must collapse toward 0: with the labels meaningless there is no model x method interaction left to find.

**Deviation, stated:** the analysis plan specified the same Bayesian model. That is ~700 MCMC fits (~12 h). The null is a calibration check, not an inferential quantity, so it uses the ANOVA moment estimator from the B2 design simulation.

| foundation | block (M x K x I) | observed R | null median | null 95% | observed above null? |
|---|---|---|---|---|---|
| Authority | 17x4x17 | 0.456 | -0.016 | [-0.079, 0.068] | **YES** |
| Care | 17x4x16 | 0.512 | -0.042 | [-0.131, 0.116] | **YES** |
| Fairness | 17x4x17 | 1.021 | 0.007 | [-0.119, 0.181] | **YES** |
| Liberty | 16x4x17 | 0.710 | -0.029 | [-0.124, 0.142] | **YES** |
| Loyalty | 16x4x16 | 0.367 | -0.018 | [-0.052, 0.041] | **YES** |
| Sanctity | 14x4x17 | 0.651 | -0.061 | [-0.161, 0.083] | **YES** |
| Social Norms | 17x4x16 | 0.133 | -0.011 | [-0.017, -0.002] | **YES** |

A null median near 0 means the pipeline is calibrated. If the observed R does not exceed the null interval, the data provide no evidence of a model x method interaction beyond what label-shuffling produces by chance.

## 2. Positive control — Sanctity above Social Norms

Clifford's human means put purity violations far above social-norm violations. Any method that fails to reproduce that ordering is not measuring moral severity.

Human baseline: Sanctity 2.81, Social Norms 0.19, gap 2.62

| method | Sanctity | Social Norms | gap | passes? |
|---|---|---|---|---|
| label | 2.967 | 1.235 | 1.733 | PASS |
| string | 1.716 | 1.010 | 0.705 | PASS |
| greedy | 3.077 | 1.087 | 1.991 | PASS |
| sampled | 2.971 | 1.159 | 1.812 | PASS |

**All four methods pass.**

## 3. Rank agreement (descriptive only — no threshold)

Spearman rho of the model ordering under each pair of methods, within foundation, after centring out the method main effect. **No pass/fail line is attached**: at this N the statistic is too blunt to carry one, as the B2 simulation showed.

| foundation | lab~str | lab~gre | lab~sam | str~gre | str~sam | gre~sam |
|---|---|---|---|---|---|---|
| Authority | 0.38 | 0.95 | 0.77 | 0.56 | 0.33 | 0.78 |
| Care | 0.37 | 0.97 | 0.85 | 0.39 | 0.28 | 0.76 |
| Fairness | 0.12 | 0.85 | 0.85 | 0.17 | 0.25 | 0.62 |
| Liberty | 0.26 | 0.86 | 0.90 | 0.21 | 0.27 | 0.70 |
| Loyalty | 0.34 | 0.97 | 0.92 | 0.39 | 0.26 | 0.82 |
| Sanctity | 0.22 | 0.94 | 0.90 | 0.28 | 0.27 | 0.77 |
| Social Norms | 0.62 | 0.95 | 0.97 | 0.41 | 0.40 | 0.97 |

Mean rho per pair across foundations:

- **label ~ string**: 0.332  (min 0.123, max 0.621, n=7)
- **label ~ greedy**: 0.927  (min 0.853, max 0.971, n=7)
- **label ~ sampled**: 0.880  (min 0.765, max 0.971, n=7)
- **string ~ greedy**: 0.346  (min 0.171, max 0.564, n=7)
- **string ~ sampled**: 0.294  (min 0.251, max 0.397, n=7)
- **greedy ~ sampled**: 0.774  (min 0.623, max 0.971, n=7)
