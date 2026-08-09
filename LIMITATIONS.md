# Limitations

Everything that constrains what this project may claim, in one place, ordered by how much it
bites. Assembled 2026-08-09 by sweeping `FINDINGS.md`, `METHODOLOGY_REVIEW.md`, `state.md`,
`ANALYSIS_PLAN.md`, `CORRECTIONS.md`, `config/prompt.yaml`, `data/source/PROVENANCE.md` and the
derived reports, so that nothing lives only in one file's small print.

Three categories, and the distinction matters for how each should be written up:

- **DESIGN** — a consequence of choices we made and would defend. Disclose and move on.
- **EVIDENTIAL** — the data cannot support a claim we would like to make. State the limit.
- **INSTRUMENT** — inherited from the MFV, the human baseline, or Kirgis's own data.

---

## 1. The headline estimand was never resolved · EVIDENTIAL

**All seven foundations are `indeterminate` at N = 20 and again at N = 31.** Every 95% credible
interval straddles a band boundary. We can say the model × method interaction is real — two
independent nulls confirm the estimator is calibrated — and that its magnitude is comparable to
between-model variance. We cannot say how large it is.

This **falsifies our own P7**, which predicted at least two foundations would escape at N ≈ 30.
Raising the roster from 20 to 31 models resolved nothing.

The B2 design simulation said this in advance: at N = 20 the design resolves extreme R values
and not middling ones, and the `indeterminate` verdict was added *before* any data so we could
not be tempted to round toward a cleaner story. The honest reading is that this estimand is not
resolvable at any N a student project can reach. **Do not report a point estimate of R as if it
settled the question.**

## 2. The four conditions are three independent readouts · DESIGN

`label` and `string_line` are very nearly the same measurement: **ρ = 0.969 across models,
r = 0.988 at item level**, and exactly identical on the most confident models. The reason is
arithmetic:

    log P("3: Very wrong") = log P("3") + log P(": Very wrong" | prompt + "3")

The second term is near-constant across options **because the prompt displays the digit→phrase
mapping**. Conditioned on the digit, the model reads the phrase off the prompt.

So under a prompt that shows numbered options, "string scoring" is either the same measurement
as label scoring, or a probe of a continuation the model almost never writes (`string_bare`,
mean retained mass **0.0032**). **No fixed prompt escapes this**, because label scoring requires
the digits to be visible and cloze scoring requires them absent. The design cannot have four
independent probability readouts and a constant prompt at the same time.

We found this ourselves, after collection. It should be stated by us rather than found by a
reviewer.

## 3. Everything is conditional on one prompt · DESIGN

The design holds the prompt byte-identical across conditions, by necessity — that is what makes
scoring method the only thing varying. The cost is that **every number is conditional on that
one prompt**, and we cannot separate "method effect" from "method effect *given this wording*".

Ministral-8B's total silence under greedy decoding is the sharpest case: its argmax first token
is `</s>` on a prompt that is well-formed by Mistral's own chat template. That is very likely
prompt-sensitive and we have no way to show otherwise.

The cloze arm varies the prompt but **changes two things at once** — the option list is removed
*and* the "five-point scale" clause goes with it (keeping it would leave a dangling reference).
So cloze cannot separate option-visibility from wording. It is a diagnostic, not a factor.

**F5 — prompt as a designed factor — remains undone**, and it is the deepest outstanding gap.
It would decompose σ²(model×method) against σ²(model×prompt) and answer whether method choice
matters more or less than an arbitrary wording decision. Until then, that comparison is unmade.

## 4. Not the frontier, and the gap is not only scale · EVIDENTIAL

Our largest collected model is **72.7B**. Kirgis's are closed frontier products of undisclosed
size, several plausibly sparse MoE. **The distance to his domain is post-training as much as
parameter count** — his models are heavily RLHF'd consumer products; Qwen2.5-72B is not a small
GPT-4o.

So P5's within-family scale slope is established *within open-weight models across 145×*, and
whether it **extrapolates** to his range is an assumption we state, not a result we have.

Two honest details. Only **2 of 31** collected models are ≥50B, so the top of the range is
thin. But dropping every model ≥50B moves the pooled slope by just **+0.020**, so the effect is
not propped up by the largest models — it is present throughout the range. The llama ladder is
the leveraged one: a **0.95-decade gap** between 8B and 70.6B with nothing between.

Adding Llama-3.1-405B was considered and declined: ~812 GiB, roughly 8 GPUs, and it would still
not be GPT-4-class. Buying one more point would make the extrapolation *feel* better funded
without testing it.

## 5. The scale result depends on a correction that is itself a model · EVIDENTIAL

P5 survives only after removing a compression confound, and that removal is a modelling choice.
Compression changes enormously with scale — fitting `score = a + b·human`, the Qwen ladder runs
**b = 0.113 → 1.059** — and since pure compression predicts a *negative* gap, the raw gap must
rise with scale even with no change in moral profile. Slope of `b` on log-parameters: **+0.4346,
p < 0.001**.

We adjust by regressing each model's scores on the human baseline and taking residuals. That is
defensible and it is *a* choice. **After adjustment neither ladder is individually significant
at 0.05** (qwen p = 0.083, llama p = 0.060); only the pooled fit is, and pooling is the weaker
design because models are not exchangeable across families. Report P5 as *supported in
direction, robust to leave-one-out, marginal per ladder*.

## 6. Missing data in the free-generation arms is not missing at random · EVIDENTIAL

Refusals are dropped. Refusal is plainly not random — models refuse graphic Sanctity items and
answer mild Social-Norms ones — so the greedy and sampled means are biased by an unknown amount.

We can bound it, because **label scoring never requires the model to speak**, so we hold each
model's probability answer to the items it refused. Imputing the scale maximum instead of
dropping would move a model's greedy mean by up to **+0.965**. That is the size of a choice
currently made silently.

We keep dropping as primary because it asserts nothing about the unobserved value, and publish
the sensitivity table. But **no rule is right across the roster**: refusal marks *more* severe
items for Llama-3.1-8B (+1.34 on its own label scale) and *less* severe ones for gemma-2-27b.

Two models lose their greedy arm entirely (Ministral-8B, Llama-3.2-1B), so N drops to 29 there.

## 7. Models are not exchangeable, and the analysis pretends they are · EVIDENTIAL

The variance model treats models as exchangeable draws. **They are not** — the roster contains
eight Qwens and four Llamas sharing pretraining recipes, so effective N is below nominal N.

**The family random effect was specified in the review (F3) and never fitted.** Until it is, the
credible intervals on R are narrower than they should be, which means the `indeterminate`
verdicts are, if anything, *understated* — the honest direction, but still unquantified.

Likewise the scale-augmented variance model (letting σ(model:method) depend on log-parameters)
is the correct follow-up to P6 and was **deliberately not run**: a naive small/large split gives
N ≈ 9 in the large group, where B2 puts classification accuracy at 0.64.

## 8. This is a pre-specified plan, not a preregistration · DESIGN

The analysis plan is locked at git tag `analysis-plan-locked` (commit `75b57b2`), which provably
contains no `results/raw/`. **Call it a pre-specified analysis plan and never a
preregistration.** A tag in a repository the author controls is an internal discipline device,
not independent verification. The discipline is real — changing a decision rule now produces a
visible diff against a tagged commit — but the stronger word is not available, and using it
would be exactly the over-claim that sinks a write-up.

Two thresholds were fixed by the author after seeing diagnostics but before any outcome model:
the 0.50 parse-rate exclusion, and internlm's string arm treated as structurally missing. That
ordering is weaker than external preregistration and stronger than choosing after seeing R.
Say so.

## 9. The human baseline is not what it is usually called · INSTRUMENT

Clifford et al. Study 1 recruited from "a national online panel by Qualtrics", **age-limited to
18–40** and balanced on ideology. Kirgis's discussion describes it as "a nationally
representative sample of US adults". **It is not.** It is an ideology-quota online panel of
18–40-year-olds.

And **n ≈ 30 per vignette**, so each item mean carries a standard error of about **0.2 on a 0–4
scale**. We treat those means as an error-free reference throughout — in the error terms, the
compression regressions, and the positive control. That understates uncertainty everywhere it
appears.

## 10. Construct assumptions imported from human psychometrics · INSTRUMENT

The MFV was validated on people. Treating a token distribution as a response distribution is an
assumption, not a finding. Whether "a model's moral profile" is even well defined independently
of how you interrogate it is **a values question, not a technical one** — and this project's
entire framing (that method-dependence is a *problem*) presumes one answer to it. A reader who
thinks the readout is part of the construct would read our R differently.

We also never tested Kirgis's claim 1 (that MFT has explanatory power for LLM moral judgment).
We assumed the instrument and audited the measurement.

## 11. Not a replication of Kirgis · DESIGN

We did not reproduce his models, his prompt, or his capability range. **We cannot match his wire
format**: his EDSL rendering appended instructions ("Only 1 option may be selected", "Respond
only with the code…") that are not in his repo and are not reproducible under our harness. We
also deliberately dropped his "respond only with the code" instruction, because it explicitly
steers toward digits and would bias the string arm.

So this replicates his *design* on a different sample, with one thing he held fixed deliberately
varied. It is an audit and an extension, not a replication.

## 12. The narrow version of the methodological findings · EVIDENTIAL

- **"Label scoring fails on 38% of models"** is one implementation, on one roster, at one
  prompt. It is not evidence that published logprob-based work is broadly wrong.
- **The grok-3 data-integrity finding** is from Kirgis's own committed outputs. It shows his
  code and his printed formula disagree, and that 44% of one model's responses were malformed.
  It does not generalise to xAI's API today.
- **Retained mass as a refusal detector** flags problems without identifying them: Mistral-7B
  answered 100% of items yet had v1 mass 0.078, which was a format mismatch, not refusal.

## 13. Reproducibility defects found late, and what they imply · EVIDENTIAL

Twelve corrections are logged in `CORRECTIONS.md`. Three were defects in artifacts we had
already committed and cited:

- **C10** — a hash-order tie-break made `analysis_long.csv` non-deterministic (28 rows).
- **C11** — the MCMC seed was `hash()`-derived, so `variance_ratio.csv` could not be regenerated.
- **C12** — a v2 run overwrote the committed v1 result file.

None changed a published conclusion — the seed audit measured C11's effect at **0.8–2.2% of the
credible-interval width, with no verdict flips** — and all three are now guarded by tests. But
the honest statement is that **two of twelve corrections were found by luck rather than by a
check built in advance**, and the guards were written *after* the defects, not before. A reader
is entitled to weigh that.

---

## What would actually change the conclusions

Ordered by leverage, so the write-up's "future work" is concrete rather than decorative:

1. **F5 — prompt as a designed factor.** Decompose σ²(model×method) against σ²(model×prompt).
   Until this exists we cannot say whether scoring method matters more than an arbitrary wording
   choice, which is the obvious sceptical response to the whole project.
2. **The family random effect**, which would widen the intervals on R honestly.
3. **A scale-augmented variance model**, letting σ(model:method) depend on log-parameters — the
   proper test of P6, replacing a descriptive slope.
4. **A frontier-scale open model**, if one ever becomes reachable, to test whether P5's slope
   extrapolates rather than assuming it.
5. **Multiple human baselines**, or propagating the ±0.2 item-level standard error, so the
   reference is not treated as exact.
