# Step 5 — pre-specified controls

## 1. Permutation null

Method labels shuffled within model x item, R recomputed. R must collapse toward 0: with the labels meaningless there is no model x method interaction left to find.

**Deviation, stated:** the analysis plan specified the same Bayesian model. That is ~700 MCMC fits (~12 h). The null is a calibration check, not an inferential quantity, so it uses the ANOVA moment estimator from the B2 design simulation.

| foundation | block (M x K x I) | observed R | null median | null 95% | observed above null? |
|---|---|---|---|---|---|
| Authority | 28x6x17 | 0.972 | -0.051 | [-0.079, -0.016] | **YES** |
| Care | 27x6x16 | 0.626 | -0.085 | [-0.109, -0.046] | **YES** |
| Fairness | 28x6x17 | 1.299 | -0.073 | [-0.116, -0.010] | **YES** |
| Liberty | 26x6x17 | 0.769 | -0.061 | [-0.091, -0.029] | **YES** |
| Loyalty | 27x6x16 | 0.357 | -0.033 | [-0.044, -0.018] | **YES** |
| Sanctity | 24x6x17 | 0.742 | -0.138 | [-0.173, -0.094] | **YES** |
| Social Norms | 27x6x16 | 0.317 | -0.010 | [-0.019, 0.001] | **YES** |

A null median near 0 means the pipeline is calibrated. If the observed R does not exceed the null interval, the data provide no evidence of a model x method interaction beyond what label-shuffling produces by chance.

## 2. Positive control — Sanctity above Social Norms

Clifford's human means put purity violations far above social-norm violations. Any method that fails to reproduce that ordering is not measuring moral severity.

Human baseline: Sanctity 2.81, Social Norms 0.19, gap 2.62

| method | Sanctity | Social Norms | gap | passes? |
|---|---|---|---|---|
| label | 3.004 | 1.107 | 1.897 | PASS |
| string_line | 3.027 | 1.138 | 1.889 | PASS |
| string_bare | 2.526 | 0.972 | 1.553 | PASS |
| cloze | 2.826 | 1.401 | 1.426 | PASS |
| greedy | 3.065 | 1.007 | 2.058 | PASS |
| sampled | 2.977 | 1.031 | 1.945 | PASS |

**All four methods pass.**

## 3. Rank agreement (descriptive only — no threshold)

Spearman rho of the model ordering under each pair of methods, within foundation, after centring out the method main effect. **No pass/fail line is attached**: at this N the statistic is too blunt to carry one, as the B2 simulation showed.

| foundation | lab~str | lab~str | lab~clo | lab~gre | lab~sam | str~str | str~clo | str~gre | str~sam | str~clo | str~gre | str~sam | clo~gre | clo~sam | gre~sam |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| Authority | 0.87 | 0.39 | 0.30 | 0.94 | 0.80 | 0.26 | 0.35 | 0.93 | 0.75 | 0.12 | 0.36 | 0.44 | 0.18 | 0.24 | 0.73 |
| Care | 0.98 | 0.67 | 0.24 | 0.97 | 0.84 | 0.66 | 0.22 | 0.96 | 0.82 | 0.21 | 0.65 | 0.74 | 0.23 | 0.20 | 0.77 |
| Fairness | 0.96 | 0.16 | 0.20 | 0.86 | 0.77 | 0.16 | 0.23 | 0.87 | 0.74 | 0.16 | 0.16 | 0.32 | 0.27 | 0.20 | 0.67 |
| Liberty | 0.99 | 0.38 | 0.47 | 0.84 | 0.83 | 0.41 | 0.48 | 0.83 | 0.83 | 0.33 | 0.37 | 0.49 | 0.45 | 0.45 | 0.71 |
| Loyalty | 0.99 | 0.53 | 0.52 | 0.94 | 0.85 | 0.52 | 0.52 | 0.95 | 0.85 | 0.37 | 0.42 | 0.46 | 0.63 | 0.67 | 0.86 |
| Sanctity | 0.99 | 0.37 | 0.56 | 0.98 | 0.83 | 0.38 | 0.55 | 0.97 | 0.82 | 0.26 | 0.36 | 0.49 | 0.53 | 0.53 | 0.83 |
| Social Norms | 1.00 | 0.65 | 0.53 | 0.96 | 0.96 | 0.66 | 0.55 | 0.96 | 0.95 | 0.44 | 0.67 | 0.54 | 0.42 | 0.41 | 0.95 |

Mean rho per pair across foundations:

- **label ~ string_line**: 0.969  (min 0.867, max 0.997, n=7)
- **label ~ string_bare**: 0.451  (min 0.158, max 0.673, n=7)
- **label ~ cloze**: 0.404  (min 0.200, max 0.559, n=7)
- **label ~ greedy**: 0.928  (min 0.843, max 0.982, n=7)
- **label ~ sampled**: 0.842  (min 0.773, max 0.960, n=7)
- **string_line ~ string_bare**: 0.436  (min 0.158, max 0.664, n=7)
- **string_line ~ cloze**: 0.411  (min 0.216, max 0.546, n=7)
- **string_line ~ greedy**: 0.925  (min 0.835, max 0.975, n=7)
- **string_line ~ sampled**: 0.824  (min 0.744, max 0.952, n=7)
- **string_bare ~ cloze**: 0.269  (min 0.117, max 0.444, n=7)
- **string_bare ~ greedy**: 0.427  (min 0.155, max 0.667, n=7)
- **string_bare ~ sampled**: 0.496  (min 0.320, max 0.738, n=7)
- **cloze ~ greedy**: 0.389  (min 0.181, max 0.627, n=7)
- **cloze ~ sampled**: 0.385  (min 0.199, max 0.668, n=7)
- **greedy ~ sampled**: 0.789  (min 0.665, max 0.952, n=7)
