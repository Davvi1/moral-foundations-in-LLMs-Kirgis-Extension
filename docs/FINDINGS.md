# What we found, and what it means for Kirgis

Synthesis of the completed analysis. **Primary results are the v2 harness: 31 models
collected, 30 analysed** (`analysis_long_v2.csv`, forced-continuation scoring). SmolLM2-1.7B is
excluded by a uniform discrimination threshold — see `LIMITATIONS.md` §22, which records that
the criterion is post hoc. **Counts of the form "n of 31" below describe the COLLECTION;
analyses run on 30.**

**Foundation counts:** the instrument has **six moral foundations plus one non-moral control**
(Social Norms). Statistics averaged "over seven foundations" pooled a control into a
foundation-level number and inflated every cross-method correlation; they have been recomputed
over the six. See §3.

The v1 harness at N = 20 is retained throughout as a comparison, never silently mixed — see
`CORRECTIONS.md` C12 for why that distinction is now enforced by tests rather than by
convention.

Each claim carries a strength label:

- **ESTABLISHED** — directly measured, robust to the sensitivity checks we ran
- **SUPPORTED** — measured, but resting on an assumption a reviewer could contest
- **SUGGESTIVE** — visible in the data, underpowered or confounded
- **NOT SHOWN** — things it would be tempting to claim and that we cannot

---

## 1. The one-paragraph version

Scoring method perturbs a language model's measured moral profile, and the perturbation is real
rather than an artifact: a 700-fit permutation
null collapses to ≈ 0.001 while observed R runs **0.18–0.47 across the six moral foundations**
(the non-moral control sits lower still, at 0.13, and is the one **`robust`** verdict). But
**the magnitude remains unresolved at N = 30 for every moral foundation**, which falsifies our
own power prediction. Method effects are **roughly a fifth to a half of between-model
variance** over the five-arm basket — not comparable to it, a claim we withdrew on 2026-08-11
when the prompt-varying cloze arm was removed from the primary (C15) — and it is concentrated
twice over: the pairwise breakdown in §2 shows **almost all of it comes from two low-mass
probes**, with the four readouts carrying real probability mass agreeing at pairwise R ≤ 0.20,
and the leave-one-model-out shows **one model of 27 carries 34% of the interaction** (C16).
Those are the same finding from two directions — the models that dominate are the ones whose
probability readouts sit on almost no retained mass. **The two methods Kirgis actually confounded with
provider agree at ρ = 0.818 over the six moral foundations**, so his specific design flaw is one
his conclusions can largely survive. The most consequential new result is about scale: **his
individualizing-over-binding pattern does appear, and it grows with model size** on both
complete ladders — which explains why a ≤14B sample found nothing, and which survives
removing a large compression confound that would otherwise have manufactured it.

---

## 2. The primary result — R at N = 30

**ESTABLISHED — there is a real model × method interaction.** The full-MCMC permutation null
(700 fits, F9, the specification the analysis plan originally named) collapses to a median R of
**0.0006–0.0021**, with every 95% interval below 0.007. Observed R exceeds its null by roughly
**two to three orders of magnitude** in every foundation. Method is not noise, and the
estimator is calibrated: destroy the interaction by construction and it reports none.

> **BASKET DISCLOSURE, added 2026-08-15 (C17).** The committed null
> (`mcmc_permutation_null_v2.csv`) was fitted on **six arms, cloze included** — the same C15
> defect, surviving in a second script because the test written in response to C15 asserted
> against `analyse_variance_ratio.py` alone. So a six-arm null is being compared against a
> five-arm observed R. **The calibration conclusion is unaffected**: a permutation null
> collapses to ~0 under any basket, which is the whole point of it, and 0.001 against 0.18 is
> not a margin a basket change can close. The script is fixed (cloze excluded by default) and
> the guard now covers every script that computes R; the artifact is **not** refit, because 700
> MCMC fits of pod time would move nothing. Stated rather than quietly corrected, because the
> project's own criticism of Kirgis is that a method effect contained something else.

**REFITTED 2026-08-11 at N = 30, WITH CLOZE EXCLUDED (C15).** The primary now matches the
design: cloze is scored against a different prompt, so a method-effect estimate containing it is
confounded with prompt. 112 fits. Primary specification: exclusions applied, method-specific
residuals.

| foundation | **R** | 95% CrI | verdict | scan-excl | +family | *with cloze* |
|---|---:|---|---|---:|---:|---:|
| *Social Norms — **NON-MORAL CONTROL*** | **0.133** | [0.067, 0.240] | **robust** | 0.137 | 0.131 | *0.439* |
| Care | 0.181 | [0.081, 0.369] | indeterminate | 0.144 | 0.183 | *0.632* |
| Loyalty | 0.181 | [0.089, 0.355] | indeterminate | 0.164 | 0.179 | *0.485* |
| Sanctity | 0.246 | [0.102, 0.527] | indeterminate | 0.208 | 0.251 | *0.545* |
| Liberty | 0.317 | [0.153, 0.633] | indeterminate | 0.294 | 0.333 | *0.756* |
| Fairness | 0.408 | [0.199, 0.810] | indeterminate | 0.356 | 0.404 | *0.957* |
| Authority | 0.469 | [0.231, 0.957] | indeterminate | 0.414 | 0.461 | *1.157* |

**A CLAIM OF OURS IS WITHDRAWN, and this is the most consequential correction in the project.**
Every R published before 2026-08-11 included the cloze arm. Including it inflates R by a mean of
**2.70×** — measured, not estimated; a moment-estimator check had put it at ~2.1× and
**understated it**. Three things follow, and the first is the one that hurts:

1. **"Method perturbation is comparable to between-model variance" is no longer supported.** That
   sentence rested on R values near and above 1. Design-conformant, R runs **0.181–0.469 across
   the six moral foundations** — method effects are roughly **a fifth to a half** of between-model
   variance, not comparable to it. The stronger claim was an artifact of a prompt-varying arm.
2. **The result is now bounded away from "not interpretable".** With cloze, **five of seven**
   upper credible bounds exceeded 1.0, so R could plausibly have been larger than between-model
   variance. Without it, **zero of seven** do. That is a cleaner result than we had, and it is
   the one the design specified.
3. **One verdict resolves.** The non-moral control is **`robust`** — [0.067, 0.240], entirely
   inside the band. Readouts agree almost perfectly on items every model rates near the floor,
   which is what a control ought to show and is the first non-`indeterminate` verdict the project
   has produced.

**The direction matters and should be stated plainly in the write-up:** the error ran in our own
favour. Including cloze made scoring method look like a bigger problem than it is, which is the
direction that most demands correction and the reason C15 is logged as the worst entry in
`CORRECTIONS.md`.

**ESTABLISHED — R depends on which arms are in the basket, and the pairwise breakdown says more
than the scalar does.** R is a variance ratio computed over whichever arms enter the fit, so its
value is a property of that *chosen set*, not of the models. C15 was one instance of that
problem; the general version is that a single number averaged over five arms cannot show that
the arms disagree wildly about how much they disagree. `results/derived/controls_v2.md` §4
therefore reports R for **every pair** of arms, on one common complete-case block, using the
same moment estimator as the permutation null. Averaged over the six moral foundations it
separates cleanly into three tiers:

| tier | arms | pairwise R | mean retained mass |
|---|---|---:|---:|
| **readouts that agree** | `label`, `string_line`, `greedy`, `sampled` — all six pairs | **−0.09 to 0.20** | 0.77, 0.63 (free generation has none) |
| **one low-mass probe** | `string_bare` against each of the four above | 0.62 to 1.33 | **0.0028** |
| **prompt-varying** | any pair including `cloze` | 2.52 to 4.32 | 0.046 |

(`string_bare ~ cloze`, the two low-mass arms against each other, is 4.32 — counted in the
bottom row.)

**The pooled R of 0.18–0.47 is a weighted average of those tiers.** Nothing here is a correction
to the fitted R — it is a correct computation of a defined quantity — but a write-up quoting only
the scalar would imply that scoring method perturbs profiles *generally*, when the data say it
perturbs them **if you choose a readout that scores a region the model essentially never
visits**. `LIMITATIONS.md` §4 already flagged those two arms as low-mass; this connects that flag
to the primary estimand, which no earlier pass had done.

**Kirgis's own pair sits in the top tier: `label ~ sampled` gives R = 0.081.** That reaches the
same conclusion as the ρ = 0.818 result by an independent route, which is worth more than either
number alone.

**ESTABLISHED — the arm-level sensitivities are now on the corrected basis, and they barely
move.** Scan-exclusion shifts R by −20% to +3%; the family random effect by −2% to +5%. Both
were previously computed on the confounded primary and have been refitted. Convergence: max
`rhat` 1.02 across all 112 fits.

**The exclusion sensitivity is larger than either, and until 2026-08-15 it was not reported
here at all.** Both fits have been in `variance_ratio_v2.csv` since the refit —
`ANALYSIS_PLAN.md:191` committed to reporting "everything **with and without** exclusions, plus
a table of what was dropped" — but no write-up document carried the pair, and the table did not
exist. Both now do (`results/derived/exclusions_v2.md`). Dropping the exclusions moves R by
**−21% to +26%**, larger than either sensitivity above. The primary remains
exclusions-applied, as pre-specified; the point is that the larger number was the unreported one.

**SUPPORTED — and this is the largest single-source dependency in the estimand: half the
interaction comes from one model.** No robustness check before 2026-08-15 ever varied the
*models* — C15's leave-one-out varied conditions, as did every other check. Varying models
(`controls_v2.md` §5) gives:

| model | share of interaction SS | R without it |
|---|---:|---:|
| **Mistral-7B-Instruct-v0.3** | **34.3%** | 0.171 (**−51%**) |
| Qwen2.5-3B-Instruct | 11.4% | 0.306 (−12%) |
| *mean of the remaining 21* | *1.6%* | — |

An equal share across 27 models would be 3.7%, so Mistral-7B is **9.3× the average
contribution**, and the effect is the same order as C15 — from one model rather than one arm.
The share of interaction *sum of squares* involves no variance-component estimator at all, so it
cannot be moment-estimator truncation; the leave-one-out on R agrees.

**This is the tier finding above, restated from the model side, and it is not a coincidence.**
Mistral-7B is the model `LIMITATIONS.md` §3 records at **label retained mass 0.008** — its
`string_bare` mean is 1.53 against `greedy` 3.45, a 1.9-point swing on a 0–4 scale. The method
effect is carried disproportionately by models whose probability readouts sit on almost no
retained mass. Logged as **C16**. A write-up quoting the pooled R without this is quoting a
roster-level number for something closer to a few-model phenomenon.

**ESTABLISHED — every verdict is still `indeterminate`, and this falsifies P7.** We predicted
that at N ≈ 30 at least two foundations would escape the indeterminate band. **None did.**
Going from 20 to 31 models resolved nothing. Reported as a failed prediction, and the honest
conclusion is the one P7 itself anticipated: this estimand is not resolvable at any N a student
project can reach, so the contribution is the design analysis rather than a resolved R.

**Achieved N, reported with its simulated classification accuracy — a commitment
(`state.md:444`) that until 2026-08-15 was never honoured here.** The rule was to report the
achieved N with what the B2 simulation says it buys, never the headline N. Achieved N = 30
analysed, and `design_simulation.csv` gives interior-band accuracy at N=30 **as a function of
where R actually lands**:

| true R | 0.10 | **0.25** | 0.50 | 1.00 | 2.00 |
|---|---:|---:|---:|---:|---:|
| P(correct band) at N=30 | 0.99 | **0.51** | 0.94 | 0.52 | 0.95 |

**This is the explanation for P7's failure, and it is more useful than the prediction was.**
P7 leaned on "0.94 at N=30", which is the accuracy *at R = 0.50*. Six of our seven observed R
values land in **0.13–0.47** — clustered around the 0.25 band boundary, where the simulation
says classification is a coin flip (0.51). Sanctity at 0.246 sits almost exactly on it. So N was
never the binding constraint: **the estimand landed where no achievable N classifies it**,
because accuracy collapses at a boundary regardless of sample size. That was foreseeable from
the simulation we already had, and we did not foresee it.

**ESTABLISHED — the numbers are reproducible, and we know what the reproducibility bug cost.**
The MCMC seed was randomised per process (C11). Refitting all seven levels (six foundations
plus the control) under five
explicit seeds moves `R_median` by **0.005–0.033**, which is **0.8%–2.2% of the credible-interval
width**, and **no verdict changes**. The bug was real; its effect on any published conclusion
was not. That is now a measured quantity rather than an assumption.

**A previous finding of ours does NOT replicate.** At N = 20 we reported that pooling the
residual variance *deflates* R by 4–16%, itself a reversal of the analysis plan's prediction
(C2). At N = 31 pooling *inflates* R, by +0.3% to +6.6% in six of the seven levels fitted
(six foundations plus the control). So the
direction is not stable across samples and the effect is small either way. The pre-specified
method-specific residual remains the primary, but the case for it is now "small and
unstable-in-sign", not "corrects a 4–16% deflation".

---

## 3. The ranking result — and the part that is fair to Kirgis

> **UPDATED 2026-08-10 — N is now 30, not 31.** SmolLM2-1.7B-Instruct is excluded by the
> `--min-discrimination` rule (mean between-item SD 0.095 against a human baseline of 0.970;
> the next-lowest model is 0.297, a 3× gap). The rule is **post hoc** — see `LIMITATIONS.md`
> §22 — so both columns are given. The effect is small enough that no verdict changes:
> label~sampled moves −0.004, and no pair moves by more than 0.022.
>
> **`variance_ratio_v2.csv` has been refitted at N=30** (§2), together with the scan-excluded
> and family-effect sensitivities. `mcmc_permutation_null_v2.csv` remains at N=31 by decision,
> not oversight: it calibrates the estimator and collapsed to 0.0006–0.0021 against an observed
> 0.44–1.16, so one model in thirty cannot close a three-order-of-magnitude margin. Re-running
> its 700 fits would have multiplied the bill to move nothing.

**ESTABLISHED — mean Spearman ρ over models. Averaged across the SIX MORAL FOUNDATIONS**, with
the non-moral control shown separately rather than folded in:

| pair | **6 foundations** | control alone | 7 pooled (old) | v1 (N=20) |
|---|---:|---:|---:|---:|
| label ~ string_line | **0.964** | 0.996 | 0.968 | — |
| label ~ greedy | 0.921 | 0.955 | 0.926 | 0.927 |
| string_line ~ greedy | 0.920 | 0.954 | 0.925 | — |
| **label ~ sampled** | **0.818** | 0.956 | 0.838 | **0.880** |
| sampled ~ string_line | 0.795 | 0.946 | 0.817 | — |
| greedy ~ sampled | 0.762 | 0.949 | 0.789 | — |
| label ~ string_bare | 0.415 | 0.620 | 0.445 | — |
| cloze ~ label | 0.374 | 0.498 | 0.392 | — |

**Pooling the control was inflating every one of these**, by 0.005 to 0.029. The reason is
mechanical and worth stating: the control items sit at the floor (human mean 0.19), every
readout agrees that nothing much is wrong, so the model ranking is near-identical across methods
— cross-method ρ of **0.95–0.996** against 0.37–0.96 for the moral foundations. That is a floor
artifact, not evidence that methods agree.

**So the headline number is ρ = 0.818, not 0.842.** The correction runs against us, and it is
five times larger than the SmolLM2 exclusion (−0.020 vs −0.004).

> **CORRECTED 2026-08-15 (C18).** Five stranded table rows stood here — a header-less remnant
> of the pre-correction version of the table above, carrying the **N = 31, control-pooled**
> values (greedy~sampled 0.788, string_bare~sampled 0.497, label~string_bare 0.451,
> label~cloze 0.404, string_bare~cloze 0.269). They have been deleted, and the two numbers
> the prose below had been quoting from them are corrected to the six-foundation basis:
> **label~string_bare 0.415** (was 0.451) and **label~cloze 0.374** (was 0.404). The scorecard
> entry for P4r in §8 is corrected on the same basis. No verdict changes.

**ESTABLISHED, and it must not be buried: Kirgis's own confound is comparatively benign.** His
two arms were top-3 logprob weighting (≈ our `label`) and the mean of ten sampled responses
(≈ our `sampled`). Those rank models at **ρ = 0.818 over the six moral foundations at N = 30**
(0.838 with the control pooled in, 0.842 before SmolLM2 was excluded), having been 0.880 at
N = 20 — now measured on 50% more models, with a corrected scorer, and with the label arm no longer
silently broken on a third of the roster. **The specific methodological flaw that motivated
this entire project is one his conclusions can largely survive.** Saying so is the result of
the audit, not a concession, and a write-up that suppressed it would be dishonest.

**ESTABLISHED — the design has three independent probability readouts, not four.** `label` and
`string_line` correlate at **ρ = 0.969** across models and **r = 0.988 at item level**, because

    log P("3: Very wrong") = log P("3") + log P(": Very wrong" | prompt + "3")

and the second term is near-constant across options *when the prompt displays the digit→phrase
mapping*. Having conditioned on the digit, the model reads the phrase off the prompt. So on any
prompt that shows numbered options, "string scoring" is either **the same measurement as label
scoring** (scoring the full line) or **a probe of a continuation the model almost never writes**
(bare phrase, mean retained mass **0.0032**). No third option exists under a fixed prompt,
because label scoring requires the digits to be visible. **This is a genuine limitation of our
design and belongs in the write-up stated by us.**

The genuinely distinct probability readouts are `string_bare` (ρ = 0.415 with label) and
`cloze` (0.374) — and they are exactly the arms that disagree about model ranking.

**ESTABLISHED — the v1 string divergence reproduces.** v1's headline oddity was `label ~ string`
at ρ = 0.332. On the corrected scorer the same probe gives **0.415**. So that divergence was
*not* an artifact of the broken token boundary or the truncated top-20; it reproduces, and v2
explains it — that arm measures a continuation carrying 0.3% of the probability mass.

**ESTABLISHED — positive control passes under all six readouts.** Every arm ranks Sanctity above
Social Norms, gaps 1.43–2.06 against a human gap of 2.62. Compression is visible in every arm
(all gaps below the human one) and is largest for `cloze` and `string_bare`, consistent with
those being the low-mass probes.

---

## 4. Scale — the most consequential new result

**SUPPORTED — the individualizing-over-binding gap increases with model size**, on both complete
ladders, robust to leave-one-out:

| ladder | span | slope per decade (adjusted) | p | LOO keeps sign |
|---|---:|---:|---:|---:|
| qwen | 145× | **+0.3243** | 0.083 | 8/8 |
| llama | 71× | **+0.2609** | 0.060 | 4/4 |
| pooled *(context only)* | 145× | +0.2455 | 0.009 | — |

Four of six families slope positive. **This resolves the Tier-0 puzzle**: the gap looked absent
in ≤14B models because we were below the scale where it appears. It unifies Kirgis's claims 2
and 4 — the moral-profile divergence is a **capability phenomenon**.

**The adjustment is the whole result, and the raw number would have been substantially an
artifact.** Compression itself changes enormously with scale: fitting `score = a + b·human`, the
Qwen ladder runs **b = 0.113 → 1.059**. The 0.5B model barely tracks the human baseline; the 72B
model tracks it almost 1:1. Slope of `b` on log-parameters, pooled: **+0.4346, p < 0.001**.
Because pure compression predicts a *negative* gap (C3), the raw gap must rise with scale even
if the moral profile never changes. The raw slopes (qwen +0.4674, llama +0.4182) are roughly a
third confound. **After adjustment neither ladder is individually significant at 0.05** — only
the pooled fit is, and pooled is the weaker design because models are not exchangeable across
families. So: supported in direction, LOO-robust, per-ladder evidence marginal.

**SUPPORTED — method spread shrinks with scale (P6), which qualifies our own headline.** All six
families slope negative; both complete ladders are LOO-stable (qwen −0.131, llama −0.587).
Individual p-values are weak (0.593, 0.119); the evidence is the consistency of sign across
every family plus pooled p = 0.043. **If method sensitivity is larger for weaker models, then R
is partly a small-model artifact** — a caveat on our result, not only on Kirgis's.

**NOT SHOWN — that this extrapolates to frontier closed models.** Our top model is 72.7B; his
are undisclosed, likely far larger, and differ in *post-training* as much as in scale. The gap
to his domain is not primarily a parameter gap. Dropping every model ≥50B moves the pooled
slope by only +0.020, so the effect is not propped up by the largest models — but neither can
two 70B models license a claim about GPT-4-class systems.

---

## 5. Claim-by-claim bearing on Kirgis

| Kirgis's claim | our bearing (v2, N=30 analysed) | strength |
|---|---|---|
| 1. MFT has explanatory power for LLM moral judgment | untouched — we did not test this | — |
| 2. Models diverge from the human baseline | **divergence: yes**, under every one of six readouts — severity compression, `b` = 0.777 after correcting for regression dilution. *(The "over-moralisation of Social-Norms items" that stood here is **withdrawn** — those items are a non-moral control at the scale floor, where any compressive measurement reads high. See §5 of `LIMITATIONS.md` and C14.)* **His directional pattern: the raw gap cannot adjudicate it** (compression predicts negative), the compression-adjusted gap is **+0.081 to +0.187** across readouts (the +0.077 to +0.179 quoted here until 2026-08-15 was the **N=31, no-exclusions** basis — C18), **and it grows with scale**. Note the standalone verdict in `kirgis_pattern_audit_v2.md` still reads *"SUGGESTIVE, not established, in either direction"*: that artifact predates P5 and was never re-run, so the upgrade to SUPPORTED rests on the scale evidence, which is marginal per ladder (`LIMITATIONS.md` §15) | divergence ESTABLISHED; pattern SUPPORTED **on the scale evidence only** |
| 3. Providers differ systematically | the most exposed claim, but less than feared. Method perturbation is **a fifth to a half** of between-model variance (**R ≈ 0.18–0.47 across the six moral foundations**), and his method is collinear with provider for five of six providers — **but his particular method pair agrees at ρ = 0.818, and its pairwise R is 0.081** (§2), so the ranking is unlikely to be an artifact of *that* confound | SUGGESTIVE |
| 4. Divergence grows with capability | **now directly supported within open-weight families** — P5, both ladders, LOO-robust, after removing the compression confound. Whether it extends to his frontier range is an extrapolation we cannot test | SUPPORTED within our range |

**NOT SHOWN — that Kirgis's conclusions are wrong.** We did not replicate his models, his
prompt, or his capability range. We show his design carries a risk, quantify it, and find it
modest for his specific choices — while independently supporting his claims 2 and 4 in a
direction he would welcome.

---

## 6. The methodological findings — probably the strongest material

These do not depend on R and are reproducible from the committed data.

**ESTABLISHED — first-token label scoring silently fails on a large minority of models.** A
faithful v1 implementation produced meaningless output on **6 of 16 models (38%)**, from two
independent causes: SentencePiece tokenizers encode `"0"` as two tokens, so a single-token
lookup finds nothing; and the first generated token is often not the answer (Mistral emits
`'\n'` 116/116 times, Ministral emits `</s>`, Llama-3.2-1B begins prose). Neither raised an
error. Both produced plausible numbers. **The only signal was retained probability mass.**

**ESTABLISHED — v2's forced continuation fixes it, and the fix is measurable.** Scoring each
option as a forced continuation gives exact p_k with no top-k truncation and no position rule.
Label retained mass on the smoke model went 0.81 → **0.997**. Boundary shift is 0 on all 31
models, all five options found on every probability row, and mass never exceeds 1.

**ESTABLISHED — "free generation" hides a decision that can determine whether a model answers at
all.** Ministral-8B answers 0% of items under greedy and ~50% under sampling, on byte-identical
prompts; its greedy argmax is `</s>`. Llama-3.2-1B refuses 109/116 under greedy. Both hold
across v1 and v2 — a stable property of those models, not a harness artifact.

**ESTABLISHED — refusal leaks into the logprob readout.** Between models, greedy non-answer rate
and label retained mass couple at **ρ = −0.54 over 31 models** (v1: −0.60 over 20). Flagship
differential case: Llama-3.1-8B craters to mass 0.481 on Sanctity against 0.829 elsewhere.
**Label scoring does not avoid the refusal confound — it hides it**, and renormalisation then
manufactures a confident score from the remaining digit mass. Two implications: logprob studies
on safety-relevant content must report retained mass (Kirgis's logprob arm has no such check);
and mass doubles as a **graded, generation-free refusal detector**. Caveat: low mass has a
second cause — Mistral-7B answered 100% of items yet had v1 mass 0.078 (format mismatch) — so
mass flags problems without identifying which.

**ESTABLISHED — a multi-readout design converts an untestable missing-data assumption into a
measured one.** Dropping refusals is missing-not-at-random. Because **label scoring never
requires the model to speak**, we hold each model's probability-based answer to the very items
it refused. Using that: the hypothesis *refusal means "extremely wrong"* is **true for one model
and false for another** — Llama-3.1-8B rates refused items 1.34 points higher (and humans rate
them 3.13 vs 2.15), while gemma-2-27b refuses items it rates *less* severely. No single
imputation rule is correct across the roster; imputing the maximum would also overshoot (even
the strongest case gives 3.4, not 4.0) and would confound safety training with moral judgement.
Magnitude of the silent choice: imputing 4.0 moves a model's greedy mean by up to **+0.965**. We
keep dropping as primary and publish the sensitivity table.

**ESTABLISHED (from Kirgis's own committed data) — provider logprob APIs cannot be assumed
well-formed.** grok-3-beta returned structurally malformed `top_logprobs` on **51 of 116
responses (44%)** — two entries instead of three, summing to ~0 probability, while the emitted
token's own logprob reported p = 1.0. His renormalisation accidentally rescues these; his
*printed formula*, which does not renormalise, would not — grok-3's mean collapses 1.98 → 1.20
and it drops from rank 4 to 6 of 6. **His code and his paper disagree**, and for those items
"top-3 logprob weighting" was in fact argmax.

---

## 7. What we cannot claim

**Full treatment in `LIMITATIONS.md`** — this is the short list.

- **That the design resolved R.** It did not, at either N. All seven verdicts are indeterminate
  and P7 is falsified — and §2 now shows why N was never the binding constraint.
- **That R is a property of the roster.** One model of 27 carries 34% of the interaction and
  dropping it halves R (C16). Quote the pairwise table and the leave-one-out alongside any
  pooled R, or the number reads as more general than it is.
- **That method effects generalise beyond this prompt.** We held one prompt fixed by design.
  Ministral's silence in particular is likely prompt-sensitive. The cloze arm varies the prompt
  but changes two things at once (options removed, scale clause removed) and cannot separate them.
- **That our four conditions are four independent readouts.** They are three. See §3.
- **That published logprob-based work is broadly wrong.** We showed one implementation failing on
  one roster. Narrow version only.
- **Anything about frontier models.** 31 open models ≤ 72.7B are not the frontier, and the gap
  is post-training as much as scale.

---

## 8. Registered-prediction scorecard

Every prediction was fixed in `state.md` before the data existed; failures are reported as
failures.

| # | prediction | outcome |
|---|---|---|
| P1′ | full option line retains more mass than bare phrase | **SUPPORTED** — 31/31 models, 0.626 vs 0.003 |
| P2 | line probe recovers ranking agreement with label | **SUPPORTED** — ρ 0.964 vs 0.415, *but see §3: the two are near-identical measurements, so this is weaker than it looks* |
| P3 | exact p_k moves low-mass models most | **SUPPORTED but thin** — ρ = −0.195, carried by Mistral-7B (moved 0.369 vs ~0.013 for high-mass models) |
| P4′ | cloze retains more mass than bare phrase | **SUPPORTED** — 23/31 models |
| P4r | cloze ranks models like bare, not like label | **FALSIFIED** — ρ 0.226 vs 0.374 (six-foundation basis; the 0.269/0.404 quoted here until 2026-08-15 was the N=31 control-pooled basis — C18. Verdict unchanged) |
| P5 | individualizing-minus-binding gap grows with scale | **SUPPORTED** — both ladders, LOO 8/8 and 4/4, after removing the compression confound |
| P6 | method spread shrinks with scale | **SUPPORTED** — all six families negative |
| P7 | ≥2 foundations escape `indeterminate` at N=30 | **FALSIFIED** — none did |

Two failed outright, one passed for a reason that undercuts its own interpretation, one is thin.
The Phase-1 record additionally contains a wrong directional prediction of ours about pooled
residuals — which, at N = 31, reverses again (§2).

---

## 9. Suggested framing

Lead with the **methodological findings**. They are established, reproducible, useful to anyone
doing this kind of measurement, and independent of the indeterminate R: label scoring silently
failing on 38% of a realistic roster; retained mass as an integrity check and as a refusal
detector; free generation concealing whether a model answers at all; and the multi-readout
design turning an MNAR assumption into a measured bias.

Then the **scale result**, which is the strongest positive finding and the one that extends
rather than merely audits Kirgis: his pattern is real and capability-dependent, which explains
why small open models show nothing — reported with the compression confound removed and the
extrapolation limit stated.

Then the **variance ratio**, framed honestly: the interaction is real and two independent nulls
confirm the estimator is calibrated; the pooled magnitude is a fifth to a half of between-model
variance and we cannot pin it down at any feasible N; and the pairwise breakdown (§2) shows the
disagreement is concentrated in two low-mass probes rather than spread across the readouts. Lead
with the pairwise table rather than the scalar — it is the more informative statement and it
needs no basket choice defending. The B2 simulation turns the unresolved magnitude into a
constructive statement about what resolving it would require.

Then **Kirgis, fairly**: his design carries a real risk, we quantified it, and for his specific
pair of methods it is modest (ρ = 0.818). Separately, his logprob arm has a data-integrity
problem he did not detect, and his code does not implement the formula his paper prints.

Do not lead with "Kirgis is wrong". We did not show that. We showed his confound is survivable,
found independent support for two of his claims, and identified a limitation in our own design
while doing it. The honest result is more interesting than the overclaim.
