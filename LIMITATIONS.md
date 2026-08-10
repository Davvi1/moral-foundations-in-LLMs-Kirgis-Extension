# Limitations

Everything that constrains what this project may claim.

**Three passes, and the later ones kept finding things — which is itself worth knowing.**
Pass 1 collected what was already written down across seven files. Pass 2 re-read the source
documents adversarially and found seven more, including an unexecuted pre-specified analysis.
Pass 3 verified every claim in this file against the data and audited the harness, the analysis
scripts and the dataset itself; it found five more (§1b–1e), corrected two citation errors of
mine, and sourced two claims that had been asserted from memory.

**The honest inference is that a fourth pass would probably find more.** Nothing here should be
read as a complete enumeration.

### What pass 3 verified rather than found

Recorded because a limitations document that only lists problems gives a false picture of
where the evidence is weak:

- **37 numeric claims in this file** were re-derived from the committed artifacts. All matched.
- **The prompt invariant holds exactly**: across 3,596 model × item cells, the five
  fixed-prompt arms share one prompt hash — **zero violations** — and the cloze arm differs in
  all 3,596, as designed.
- **The design is close to balanced**: exclusions remove 2.0% of rows (43 of 1,302 cells), all
  in greedy and sampled; item counts per foundation are complete across all six conditions; no
  item is excluded in more than 5% of its rows.
- **Two claims previously asserted from memory are now sourced** by fetching Clifford et al.
  (2015) — see `references.md`. Both were correct, and one is now stronger than it was.

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

**Resolved for the ranking result, 2026-08-09.** The obvious worry was that our most-quoted
number — ρ(label, sampled) = 0.842, the Kirgis confound pair — depended on an analysis we never
ran. It does depend on it, and the dependency runs in the *reassuring* direction:

| pair | all rows | anchored only | change |
|---|---:|---:|---:|
| label ~ sampled | 0.846 | **0.879** | +0.032 |
| label ~ greedy | 0.911 | 0.925 | +0.015 |
| greedy ~ sampled | 0.790 | **0.959** | **+0.169** |
| label ~ string_line | 0.969 | 0.969 | 0.000 |

Excluding prose-derived digits, the two arms Kirgis confounded agree **more**, not less
(0.879, essentially the v1 figure of 0.880). The probability arms are untouched, as they must
be. And greedy ~ sampled jumps from 0.790 to 0.959 — scan-parsing was adding noise to both
free-generation arms, and removing it shows they agree far better than we reported.

**So the omission did not flatter our conclusions; correcting it strengthens them.** The R
refit still needs a pod and remains outstanding.

## 1b. R conflates rank reordering with scale differences between methods · EVIDENTIAL

**Found on the second verification pass; nobody had looked for it.**

R = σ²(model:method) / σ²(model). The interaction term captures each model × method cell's
deviation from that model's main effect — and that is large whenever a method **spreads models
out more**, even with *zero* rank reordering. The between-model SD is not constant across
methods:

| condition | between-model SD |
|---|---:|
| cloze | 0.560 |
| string_bare | 0.547 |
| greedy | 0.398 |
| label | 0.360 |
| string_line | 0.353 |
| sampled | 0.318 |

That is a **1.76× range**. Re-computing the interaction variance after z-scoring each method
(which removes scale differences while preserving reordering) shows how much of R is the scale
effect:

| foundation | scale share | | foundation | scale share |
|---|---:|---|---|---:|
| Liberty | 26.4% | | Sanctity | 16.1% |
| Authority | 24.0% | | Loyalty | 15.4% |
| Care | 17.5% | | Social Norms | 14.7% |
| Fairness | 14.2% | | | |

**So roughly a sixth to a quarter of R is methods disagreeing about *spread*, not about
*order*.** This explains an apparent tension in our own results: rank agreement between label
and greedy is ρ = 0.928 (very little reordering) while R is substantial. Both are true, because
they measure different things.

**Consequence for the write-up:** R and the Spearman matrix answer different questions and must
not be used interchangeably. The project's stated estimand is whether *rankings* survive a change
of method — that is the Spearman result. R is the broader "does the measured profile move",
which includes a model being uniformly more extreme under one readout. Neither is wrong; running
them together without distinguishing them would be.

## 1c. Two models do not discriminate between items under greedy · EVIDENTIAL

| model | condition | distinct scores over 116 items | SD |
|---|---|---:|---:|
| SmolLM2-1.7B-Instruct | greedy | **1** | 0.000 |
| Qwen2.5-1.5B-Instruct | greedy | **2** | 0.468 |

SmolLM2 answers **"3" to all 116 items** under greedy decoding. Its greedy "profile" is a single
constant, so it carries no item-level information at all, and its position in the greedy ranking
is determined by one number. Qwen2.5-1.5B uses two distinct values.

These cells pass every existing quality gate — they parse cleanly, they are not refusals, the
cell parse rate is 1.00 — so **no exclusion rule catches them**. They enter the variance model
as if they were informative. A constancy check belongs in the QA pass and is not there.

## 1d. Greedy is heavily saturated at the ceiling · DESIGN

Share of scores at each end of the 0–4 scale:

| condition | ≤ 0.05 | ≥ 3.95 |
|---|---:|---:|
| greedy | 7.4% | **25.1%** |
| sampled | 3.8% | 9.9% |
| label | 3.6% | 8.8% |
| string_line | 3.7% | 9.2% |
| cloze | 3.9% | 1.4% |
| string_bare | 1.7% | 4.7% |

**A quarter of all greedy responses are exactly 4**, the scale maximum — nearly three times the
rate of the probability readouts. Greedy is discretised to integers by construction, so it cannot
express intermediate confidence, and it piles up at the ceiling. Any comparison between greedy
and a continuous readout is partly a comparison between a censored and an uncensored measure.

## 1e. The refusal classifier is an unvalidated regex · PROCESS

`conditions.py` distinguishes `refusal` from `unparseable` with **five English regex patterns**
(`i can't`, `i'm sorry`, `as an ai`, `i don't feel comfortable`, `cannot provide/assist/comply`).
It is deliberately conservative — the docstring says so — but it has **never been validated
against hand-coded labels**, and there is no inter-rater check.

This matters because **F7 (ρ = −0.54) and the entire MNAR refusal-bias audit rest on that
split**. Inspecting the 900 parse-failed rows it does *not* flag turns up clear declines it
misses, e.g. *"This question requires a subjective ethical judgment, which I, as a language
model, am not capable of"*. A looser pattern would reclassify a material number of rows — though
looser patterns also produce obvious false positives, so **the true miss rate is bounded but
unmeasured**. Hand-coding a few hundred rows would settle it cheaply.

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

## 12. Greedy determinism — RESOLVED 2026-08-10, and greedy is NOT reproducible · EVIDENTIAL

> **This section is superseded by a measurement. Read this box before the history below.**
>
> The check described below as "never done" has now been done, locally and for free, by
> comparing the v1 and v2 collections — 20 models run twice, byte-identical prompt asserted
> per item, same GPU model, identical `vllm`/`transformers`/`torch`. See
> `scripts/audit_greedy_determinism.py` and `results/derived/greedy_determinism.md`.
>
> | over 2,320 comparable cells | count | share |
> |---|---:|---:|
> | raw greedy text differs | 245 | **10.56%** |
> | **parsed greedy score differs** | 53 | **2.28%** |
>
> Mean |shift| where the score moved: **1.038**, max **2.000** on a 0–4 scale. 13 of 20 models
> affected. Text drift is five times the score drift because the parser recovers the same digit
> from `"3"` and `"3: Very wrong"`.
>
> **The upgrade is from PROCESS to EVIDENTIAL.** This is no longer "we didn't check"; it is "we
> checked and one of the three arms we called deterministic isn't." Consequences:
>
> 1. `METHODS_EXPLAINER.md` §5 justified giving greedy a single observation on the grounds that
>    re-running a deterministic computation adds nothing. **That justification does not hold for
>    greedy.** Replication was warranted and we did not do it.
> 2. The effect is bounded and should not be overstated: the ranking results are computed over
>    116-item means, so 2.28% of items moving by ~1 point perturbs a model mean by roughly
>    0.02 — small against the between-model SD of ~0.97. It is a design error, not a threat to
>    the headline.
> 3. **The mechanism is not established.** v1 and v2 differ in more than batch composition, so
>    floating-point reduction order remains the documented hypothesis. Prompt, GPU model and
>    library versions are ruled out; the harness itself is not.
> 4. Registered prediction F5-6 asserted greedy would reproduce exactly. It was already false
>    when written, against data sitting in this repo. Amended in `state.md`, before collection,
>    with the reason stated.

### Original entry, retained — it was accurate when written

**Historical: greedy determinism is assumed, not verified · PROCESS**

Greedy decoding is deterministic in principle, but GPU floating-point reduction order can vary
with batch composition, so bit-identical output across differently-batched runs is not
guaranteed. `METHODOLOGY_REVIEW.md:197` lists a spot-check — "re-run two models' greedy arm, diff" —
as a to-do. **It was never done.** (An earlier draft of this file cited line 191; that was
wrong, and the error is noted here rather than silently fixed.)

Worse, **`METHODS_EXPLAINER.md:123` asserts this is "one caveat we verify rather than assume"**.
We did not verify it. That sentence is false and has been corrected.

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
