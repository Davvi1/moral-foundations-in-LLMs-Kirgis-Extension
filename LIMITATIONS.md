# Limitations

Everything that constrains what this project may claim. Assembled 2026-08-09 and **substantially
expanded after a second, deliberately adversarial pass** over `ANALYSIS_PLAN.md`,
`METHODS_EXPLAINER.md`, `config/prompt.yaml`, `data/source/PROVENANCE.md`, `state.md`,
`FINDINGS.md`, `METHODOLOGY_REVIEW.md`, the derived reports **and the harness source**. The
second pass found seven limitations the first missed, including one unexecuted pre-specified
analysis and one place where I had overstated a fix.

Categories, because they should be written up differently:

- **DESIGN** — a consequence of a choice we would defend. Disclose and move on.
- **EVIDENTIAL** — the data cannot support something we would like to claim. State the limit.
- **INSTRUMENT** — inherited from the MFV, the human baseline, or Kirgis's data.
- **PROCESS** — something we said we would do and did not, or did imperfectly.

---

# The five that most constrain the write-up

## 1. A pre-specified robustness check was never run, and it would have mattered · PROCESS

`ANALYSIS_PLAN.md:192` specifies that **`scan`-parsed rows** — where the answer digit was
recovered from prose rather than found at the start of the response — be reported separately,
and that **"the primary analysis is repeated excluding them"**.

**That analysis was never run.** No script implements it, no derived report contains it, and
until this pass nothing disclosed the omission.

It is not a trivial omission. Running it descriptively now:

| condition | scan share | mean shift | max shift | rank ρ, all vs anchored-only |
|---|---:|---:|---:|---:|
| greedy | 13.7% | −0.036 | **1.121** | **0.832** |
| sampled | 14.9% | −0.037 | 0.842 | 0.917 |

**ρ = 0.832 between including and excluding scan rows is the same order as the method effects
this project exists to measure.** One model moves by 1.12 points on a 0–4 scale. This is
precisely the error class that mis-scored Kirgis's grok-3 responses — a digit picked out of
running prose — so it is the last thing we should have left unchecked.

The full version needs a pod (it is a refit of R). The descriptive version above is local and
is now on record.

## 2. The headline estimand was never resolved · EVIDENTIAL

**All seven foundations are `indeterminate` at N = 20 and again at N = 31.** Every 95% credible
interval straddles a band boundary. We can say the model × method interaction is real — two
independent nulls confirm the estimator is calibrated — and that its magnitude is comparable to
between-model variance. We cannot say how large it is.

This **falsifies our own P7**, which predicted at least two foundations would escape at N ≈ 30.
Raising the roster from 20 to 31 resolved nothing. The B2 simulation predicted this in advance,
and the `indeterminate` verdict existed before any data precisely so we could not round toward
a cleaner story. **Do not report a point estimate of R as if it settled the question.**

## 3. The v2 scoring fix is partial, and I overstated it · EVIDENTIAL

`FINDINGS.md` reports label retained mass going "0.81 → 0.997". That is true **of the smoke-test
model**. Across the roster it is not:

| model | v2 label mass |
|---|---:|
| Mistral-7B-Instruct-v0.3 | **0.008** |
| zephyr-7b-beta | 0.166 |
| Llama-3.2-1B-Instruct | 0.220 |
| Phi-3.5-mini-instruct | 0.232 |
| gemma-2-27b-it | 0.353 |

**7 of 31 models sit below 0.5; two below 0.2.** Mistral-7B's label score is a renormalisation
over **0.8%** of its next-token distribution. Forced continuation removed the *truncation* and
*position* defects, but it cannot make a model put probability on a digit it does not want to
emit. **The F7 concern — that renormalisation manufactures a confident score from whatever mass
remains — is still live in v2 for those models**, and any per-model claim about them should be
read with that in mind.

## 4. Two of the three "independent" readouts sit in the tail of the distribution · DESIGN

`string_bare` has a mean retained mass of **0.0032**, and **28 of 31 models are below 0.01**.
`cloze` averages 0.045. These are the two arms we call genuinely distinct from label scoring
(§6) — and they are distinct partly *because* they describe a region of the output distribution
the model essentially never visits.

The scores remain internally valid: the comparison across the five options is a proper relative
comparison, and the positive control passes in both arms. But "the model rates this 2.5 in a
region carrying 0.3% of its probability" is a weaker statement than it looks, and the ranking
disagreement those arms produce (ρ ≈ 0.45 and 0.40 against label) should be read as *a
disagreement about a low-probability region*, not straightforwardly as "the model has a
different profile under this method".

## 5. The largest divergence from humans is a floor effect on a control category · INSTRUMENT

Mean error by foundation, v2:

| foundation | human | model | error |
|---|---:|---:|---:|
| Sanctity | 2.81 | 2.90 | +0.095 |
| Care | 2.61 | 2.74 | +0.128 |
| Fairness | 2.80 | 2.97 | +0.169 |
| Authority | 2.34 | 2.52 | +0.174 |
| Loyalty | 1.99 | 2.22 | +0.225 |
| Liberty | 2.57 | 2.83 | +0.256 |
| **Social Norms** | **0.19** | **1.11** | **+0.924** |

Social Norms error is **four to ten times** every other foundation, and those 16 items (14% of
the instrument) carry **18.8% of total absolute error**.

Two things follow. **Social Norms is not an MFT foundation** — it is Clifford's non-moral
control category, included to show the moral items behave differently. Treating it as a seventh
foundation alongside the six is a category difference, not just another level. And the human
mean of **0.19 sits against the floor of a 0–4 scale**, so *any* model reluctance to answer "not
at all wrong" produces large positive error mechanically. The headline "models over-moralise
Social Norms" is real in the data but is substantially a floor effect, and should be reported
as such rather than as a moral finding.

---

# Design and instrument

## 6. The four conditions are three independent readouts · DESIGN

`label` and `string_line` are near-identical: **ρ = 0.969 across models, r = 0.988 at item
level**, exactly identical on the most confident models. Because

    log P("3: Very wrong") = log P("3") + log P(": Very wrong" | prompt + "3")

and the second term is near-constant across options **when the prompt displays the digit→phrase
mapping**. Conditioned on the digit, the model reads the phrase off the prompt.

**No fixed prompt escapes this**: label scoring requires the digits visible, cloze requires them
absent. The design cannot have four independent probability readouts *and* a constant prompt.
Found by us after collection; stated by us rather than left for a reviewer.

## 7. Everything is conditional on one prompt · DESIGN

Holding the prompt byte-identical is what makes scoring method the only thing varying — and the
cost is that every number is conditional on that wording. We cannot separate "method effect"
from "method effect *given this prompt*". Ministral-8B's total silence under greedy is the
sharpest case and is very likely prompt-sensitive.

The cloze arm varies the prompt but **changes two things at once** (options removed, and the
"five-point scale" clause with them), so it cannot separate option-visibility from wording.

**F5 — prompt as a designed factor — remains undone**, and it is the deepest outstanding gap:
it would decompose σ²(model×method) against σ²(model×prompt) and answer whether method choice
matters more than an arbitrary wording decision. That is the obvious sceptical response to the
whole project, and we have not answered it.

## 8. Care is emotional harm only · INSTRUMENT

Kirgis administers 116 of Clifford's 132 vignettes, dropping **all 16 physical-harm Care items**
(9 animal-harm, 7 human-harm) and keeping the 16 emotional-harm ones. **So "Care" throughout
this study means emotional harm**, not the Care foundation as Clifford validated it. Any
statement about Care — including its place in the individualizing group that drives P5 and the
Kirgis pattern audit — inherits that narrowing.

## 9. The human baseline is not what it is usually called · INSTRUMENT

Clifford et al. Study 1 recruited from "a national online panel by Qualtrics", **age-limited to
18–40**, balanced on ideology. Kirgis describes it as "a nationally representative sample of US
adults". **It is not** — it is an ideology-quota online panel of 18–40-year-olds.

And **n ≈ 30 per vignette**, so each item mean carries a standard error of roughly **0.2 on a
0–4 scale**. We treat those means as an error-free reference *everywhere*: in the error terms,
the compression regressions, the P5 adjustment, and the positive control. That understates
uncertainty throughout, and the compression slope `b` in particular is a regression on a noisy
x, which biases it toward zero (regression dilution) by an amount we have not estimated.

## 10. Monte-Carlo noise in the sampled arm is half the between-model signal · DESIGN

k = 10, matching Kirgis. The resulting standard error on a sampled cell mean is **0.163
(median), 0.177 (mean)** against a between-model SD of mean score of **0.360**. So sampling
noise is roughly **half** the signal the analysis is trying to resolve.

The method-specific residual is designed to absorb exactly this, which is why it is the primary
specification — but it makes the sampled arm the noisiest of the six and is part of why R is
hard to pin down.

## 11. Free-generation parameters are choices, and one may be truncating · DESIGN

- **`max_tokens = 96`.** About **14.2%** of free-generation responses are long enough to have
  plausibly hit that cap. Where a model reasons before answering, the digit may fall outside
  the window — so some "unparseable" outcomes are our truncation, not the model's behaviour.
- **`temperature = 1.0, top_p = 1.0`** for the sampled arm. Full-distribution sampling is a
  defensible choice but is *not* what Kirgis's providers do by default, so his sampled arm and
  ours are not the same estimator.
- **Item order is fixed** and identical for every model. No presentation-order randomisation, so
  order effects are confounded with item identity — though prefix caching and independent
  requests make this less concerning than in human administration.

## 12. Greedy determinism is assumed, not verified · PROCESS

Greedy decoding is deterministic in principle, but GPU floating-point reduction order can vary
with batch composition, so bit-identical output across differently-batched runs is not
guaranteed. `METHODOLOGY_REVIEW.md:191` lists a spot-check — re-run two models' greedy arm and
diff — as a to-do. **It was never done.**

**Correction to my own summary:** the F8 row of the `METHODOLOGY_REVIEW.md` status table marks
F8 "RESOLVED", but F8 bundled the internlm boundary *and* greedy determinism. The boundary is
resolved; the determinism check is not. That row overstates.

## 13. Models are not exchangeable, and the analysis assumes they are · EVIDENTIAL

The variance model treats models as exchangeable draws. They are not — eight Qwens and four
Llamas share pretraining recipes, so effective N is below nominal N. **The family random effect
was specified (F3) and never fitted.** Until it is, the intervals on R are narrower than they
should be, meaning the `indeterminate` verdicts are if anything *understated* — the honest
direction, but unquantified.

Likewise the scale-augmented variance model (letting σ(model:method) depend on log-parameters)
is the proper follow-up to P6 and was **deliberately not run**: a naive small/large split leaves
N ≈ 9 in the large group, where B2 puts classification accuracy at 0.64.

---

# Scope and inference

## 14. Not the frontier, and the gap is not only scale · EVIDENTIAL

Largest collected model: **72.7B**. Kirgis's are closed frontier products of undisclosed size,
several plausibly sparse MoE. **The distance is post-training as much as parameter count.**

P5's scale slope is established *within open-weight models across 145×*; whether it
**extrapolates** to his range is an assumption we state, not a result. Only **2 of 31** models
are ≥50B, so the top is thin — though dropping every model ≥50B moves the pooled slope by just
**+0.020**, so the effect is present throughout the range rather than propped up by the largest.
The llama ladder is the leveraged one: a **0.95-decade gap** between 8B and 70.6B with nothing
between.

Llama-3.1-405B was considered and declined — ~812 GiB, ~8 GPUs, and still not GPT-4-class.

## 15. The scale result depends on a correction that is itself a model · EVIDENTIAL

P5 survives only after removing a compression confound, and that removal is a modelling choice.
Compression changes enormously with scale (Qwen ladder: **b = 0.113 → 1.059**; slope of b on
log-params **+0.4346, p < 0.001**), and since pure compression predicts a *negative* gap, the raw
gap must rise with scale even with no change in moral profile.

We adjust by residualising each model's scores on the human baseline. **After adjustment neither
ladder is individually significant at 0.05** (qwen p = 0.083, llama p = 0.060); only the pooled
fit is, and pooling is the weaker design. Report P5 as *supported in direction, LOO-robust,
marginal per ladder*. Note also §9: the x in that regression is itself noisy.

## 16. Missing data in the free-generation arms is not missing at random · EVIDENTIAL

Refusals are dropped, and refusal is plainly not random. We can bound the bias because **label
scoring never requires the model to speak** — imputing the scale maximum instead of dropping
moves a model's greedy mean by up to **+0.965**. But **no rule is right across the roster**:
refusal marks *more* severe items for Llama-3.1-8B (+1.34) and *less* severe ones for
gemma-2-27b. Two models lose their greedy arm entirely, so N drops to 29 there.

## 17. Not a replication of Kirgis · DESIGN

We did not reproduce his models, prompt, or capability range. **His wire format is not
reproducible** — the EDSL rendering appended instructions not present in his repo. We also
deliberately dropped his "respond only with the code" instruction because it steers toward
digits and would bias the string arm. This replicates his *design* on a different sample with
one thing he held fixed deliberately varied: an audit and an extension, not a replication.

## 18. This is a pre-specified plan, not a preregistration · DESIGN

Locked at git tag `analysis-plan-locked` (commit `75b57b2`), which provably contains no
`results/raw/`. **Never call it a preregistration** — a tag in a repo the author controls is an
internal discipline device, not independent verification. Two thresholds (the 0.50 parse rate;
internlm's string arm as structurally missing) were fixed by the author after seeing diagnostics
but before any outcome model — weaker than external preregistration, stronger than choosing
after seeing R. Say so.

## 19. Construct assumptions imported from human psychometrics · INSTRUMENT

The MFV was validated on people. Treating a token distribution as a response distribution is an
assumption. Whether "a model's moral profile" is well defined independently of how you
interrogate it is **a values question**, and this project's framing — that method-dependence is
a *problem* — presumes one answer. We never tested Kirgis's claim 1 (that MFT has explanatory
power for LLM moral judgment); we assumed the instrument and audited the measurement.

## 20. The narrow version of the methodological findings · EVIDENTIAL

- **"Label scoring fails on 38% of models"** is one implementation, one roster, one prompt. Not
  evidence that published logprob work is broadly wrong.
- **The grok-3 finding** is from Kirgis's committed outputs; it does not generalise to xAI's API
  today.
- **Retained mass as a refusal detector** flags problems without identifying them — Mistral-7B
  answered 100% of items with v1 mass 0.078, a format mismatch rather than refusal.

## 21. Reproducibility defects found late · PROCESS

Twelve corrections in `CORRECTIONS.md`; three were defects in artifacts already committed and
cited (C10 non-deterministic tie-break, C11 randomised MCMC seed, C12 a v2 run overwriting a v1
file). None changed a published conclusion — the seed audit measured C11 at **0.8–2.2% of
credible-interval width with no verdict flips** — and all three are now guarded by tests. But
**two of twelve corrections were found by luck**, and every guard was written *after* its
defect. A reader is entitled to weigh that.

---

## What would actually change the conclusions

Ranked by leverage, so "future work" is concrete:

1. **Run the scan-excluded sensitivity analysis (§1).** Pre-specified, never executed, and
   descriptively it moves greedy rankings to ρ = 0.832. This is the cheapest and most overdue.
2. **F5 — prompt as a designed factor (§7).** Until it exists we cannot say whether scoring
   method matters more than an arbitrary wording choice.
3. **The family random effect (§13)**, which would widen the intervals on R honestly.
4. **Verify greedy determinism (§12).** Two models, one re-run, minutes of GPU time.
5. **Propagate the ±0.2 baseline standard error (§9)**, including into the compression slope
   where regression dilution is currently unestimated.
6. **A scale-augmented variance model (§13)** as the proper test of P6.
7. **Report Social Norms separately (§5)** rather than as a seventh foundation, or model the
   floor explicitly.
