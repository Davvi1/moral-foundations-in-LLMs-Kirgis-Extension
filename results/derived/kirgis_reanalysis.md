# Reanalysis of Kirgis's logprob arm (EXPLORATORY)

Source: `data/results/logprob_responses.csv`, 696 responses, 6 models.

## 1. Degeneracy -- how many of each top-3 are digits

| digits in top-3 | responses | share |
|---|---|---|
| 1 | 39 | 5.6% |
| 2 | 182 | 26.1% |
| 3 | 475 | 68.2% |

## 2. Argmax collapse

**39 / 696 responses (5.6%)** had exactly one digit in the top-3. For these, the renormalised estimator returns that integer EXACTLY -- an argmax score wearing an expectation's clothing.

Sanity check: 41 of 696 successfully-extracted scores are exact integers (5.9%).

## 3. Fallback rate

**0 / 696 (0.0%)** produced no usable digit, so his code silently substitutes the EDSL-parsed answer via `.fillna(df['Answer'])`. Those rows are free-generation scores sitting inside the arm reported as logprob-weighted.

## 4. Does the estimator choice move anything?

Mean absolute differences across all successfully-extracted responses:

| comparison | mean abs diff | max abs diff |
|---|---|---|
| code (renormalised) vs paper (as printed) | 0.1313 | 4.0000 |
| code vs plain argmax | 0.0790 | 0.9204 |

Mean digit mass retained in top-3: 0.9999 (min 0.9293). The renormalisation gap is large only when this is small.

### Foundation means under each estimator

| Foundation   |   kirgis_code |   kirgis_paper |   argmax |   code - paper |   code - argmax |
|:-------------|--------------:|---------------:|---------:|---------------:|----------------:|
| Authority    |        2.1167 |         1.9993 |   2.1078 |         0.1174 |          0.0088 |
| Care         |        2.4636 |         2.2046 |   2.4479 |         0.259  |          0.0157 |
| Fairness     |        2.8946 |         2.6289 |   2.8824 |         0.2657 |          0.0122 |
| Liberty      |        2.6895 |         2.5011 |   2.6863 |         0.1885 |          0.0033 |
| Loyalty      |        1.1513 |         1.1509 |   1.1354 |         0.0005 |          0.0159 |
| Sanctity     |        2.578  |         2.4982 |   2.549  |         0.0797 |          0.0289 |
| Social Norms |        0.0993 |         0.0991 |   0.0938 |         0.0002 |          0.0055 |

### Model ranking under each estimator

| Model         |   kirgis_code |   kirgis_paper |   argmax |   rank_kirgis_code |   rank_kirgis_paper |   rank_argmax |
|:--------------|--------------:|---------------:|---------:|-------------------:|--------------------:|--------------:|
| gpt-3.5-turbo |        2.3252 |         2.3239 |   2.2931 |                  1 |                   1 |             1 |
| gpt-4-turbo   |        1.999  |         1.9989 |   1.9914 |                  3 |                   3 |             3 |
| gpt-4.1       |        1.8997 |         1.8997 |   1.8879 |                  5 |                   4 |             5 |
| gpt-4o        |        1.8794 |         1.8787 |   1.8621 |                  6 |                   5 |             6 |
| grok-2-1212   |        2.0278 |         2.0278 |   2.0172 |                  2 |                   2 |             2 |
| grok-3-beta   |        1.9809 |         1.1955 |   1.9828 |                  4 |                   6 |             4 |

Spearman rank correlation between estimators (over models):

|              |   kirgis_code |   kirgis_paper |   argmax |
|:-------------|--------------:|---------------:|---------:|
| kirgis_code  |        1      |         0.8286 |   1      |
| kirgis_paper |        0.8286 |         1      |   0.8286 |
| argmax       |        1      |         0.8286 |   1      |

## 5. Provider data integrity — the actual finding

A well-formed response returns `top_logprobs` whose probabilities sum to ~1 and whose values are consistent with the emitted token's own `logprob`. Checking that:

| Model         |   n |   n_top_returned |   mean_top_mass |   min_top_mass |   frac_mass_below_half |
|:--------------|----:|-----------------:|----------------:|---------------:|-----------------------:|
| gpt-3.5-turbo | 116 |                3 |          0.9993 |         0.9908 |                 0      |
| gpt-4-turbo   | 116 |                3 |          1      |         0.999  |                 0      |
| gpt-4.1       | 116 |                3 |          1      |         1      |                 0      |
| gpt-4o        | 116 |                3 |          0.9996 |         0.9761 |                 0      |
| grok-2-1212   | 116 |                3 |          1      |         0.9999 |                 0      |
| grok-3-beta   | 116 |                3 |          0.5603 |         0      |                 0.4397 |

**51 of 696 responses have `top_logprobs` summing to less than 0.5 probability** — structurally malformed. They are concentrated entirely in `grok-3-beta` (51 of 51).

On those responses the provider returned **two** `top_logprobs` entries instead of three, summing to ~0 probability, while the emitted token's own `logprob` reported p = 1.0. The two fields contradict each other: the data is internally inconsistent, not merely unusual.

**Three consequences, in increasing order of importance:**

1. Those scores are computed from corrupted probability data.
2. Kirgis's renormalisation *accidentally rescues* them — dividing near-zero by near-zero recovers the argmax, which equals the emitted (correct) answer. His published numbers therefore look fine. His **printed formula would not** rescue them: the affected model's mean collapses and it drops two rank positions.
3. **For those items, 'top-3 logprob weighting' is not what happened — argmax is.** Inside the arm he treats as a single homogeneous method, one of six models is effectively scored by a different method for nearly half its items.

Point 3 is the one that matters for this project: it is direct evidence, from his own committed data, that scoring method was not uniform even *within* the logprob arm. It also generalises — **provider logprob APIs cannot be assumed well-formed, and a study that reads them without an integrity check inherits their bugs.**

## Limitation

A fourth variant -- renormalising over all five valid option tokens -- is **not computable** from his data. The API returned only the top 3 of the vocabulary, so logprobs for options outside that set do not exist. This is itself part of the finding: his estimator cannot be repaired post hoc, only re-collected.
