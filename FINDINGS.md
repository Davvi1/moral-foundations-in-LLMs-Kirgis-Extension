# What we found, and what it means for Kirgis

Synthesis of the completed analysis. Written to feed the write-up, and to fix the claims
before prose makes them slippery. Each claim carries a strength label:

- **ESTABLISHED** — directly measured, robust to the sensitivity checks we ran
- **SUPPORTED** — measured, but resting on an assumption a reviewer could contest
- **SUGGESTIVE** — visible in the data, underpowered or confounded
- **NOT SHOWN** — things it would be tempting to claim and that we cannot

---

## 1. The one-paragraph version

Scoring method perturbs a language model's measured moral profile by an amount comparable to
the differences between models — but our design cannot pin down *how* comparable, and all
seven foundation-level verdicts are formally indeterminate. Three of the four methods
nevertheless agree strongly about which models are more severe; only string scoring produces
a different model ranking. **Critically, the two methods Kirgis actually confounded with
provider agree at ρ = 0.88, so his specific design flaw is far less damaging than it could
have been.** The most solid results are methodological: a standard implementation of
first-token label scoring silently produced meaningless numbers on 6 of 16 models, and
"free generation" conceals a choice that can determine whether a model answers at all.

---

## 2. The primary result

**ESTABLISHED — there is a real model × method interaction.**
The permutation null collapses to ≈ 0 (medians −0.06 to +0.01) while observed R exceeds the
null interval for **all seven foundations**. Method is not noise.

**ESTABLISHED — R is substantial.** Posterior medians, method-specific residuals, exclusions
applied, `rhat = 1.0000` across all 28 fits:

| foundation | R | 95% CrI |
|---|---|---|
| Social Norms | 0.147 | [0.062, 0.324] |
| Loyalty | 0.500 | [0.192, 1.227] |
| Authority | 0.527 | [0.207, 1.346] |
| Care | 0.615 | [0.237, 1.715] |
| Liberty | 0.778 | [0.284, 2.224] |
| Sanctity | 0.955 | [0.344, 3.115] |
| Fairness | 0.995 | [0.358, 3.293] |

R is a variance ratio, so read it on the SD scale: R ≈ 0.6 means the method-induced shift in
a model's position is about **0.8× as large as the spread between models**. Not a rounding
error.

**ESTABLISHED — but every verdict is `indeterminate`.** Every interval straddles a band
boundary. The B2 design simulation predicted this *before any data existed*: at N = 20 the
design resolves extreme R values and not middling ones. We added the `indeterminate` verdict
in advance precisely so we could not be tempted to round toward a cleaner story. **Reporting
a verdict here would be false precision.**

**ESTABLISHED — the result is robust to our analytic choices.** Exclusions move R by ≤ 0.054.
The residual specification moves it by 4–16%.

**A prediction of ours was wrong, in direction.** The analysis plan argued that pooling the
residual variance would *inflate* R. It *deflates* it, consistently. The pre-specified
correction matters, but not for the reason we gave. Report as-is.

---

## 3. The ranking result — and the part that is fair to Kirgis

**ESTABLISHED — three methods agree about model ranking; one does not.** Spearman ρ over
models, averaged across foundations:

| pair | ρ |
|---|---|
| label ~ greedy | **0.927** |
| **label ~ sampled** | **0.880** |
| greedy ~ sampled | 0.774 |
| label ~ string | **0.332** |
| string ~ greedy | 0.346 |
| string ~ sampled | 0.294 |

**ESTABLISHED — a dissociation worth its own paragraph.** String scoring agrees about which
*items* are severe (item-level ρ = 0.770 against a label~greedy ceiling of 0.851) while
disagreeing about which *models* are severe (0.332). It preserves the instrument's internal
structure and changes the between-model comparison — and the between-model comparison is
exactly what model-characterisation papers claim.

**ESTABLISHED, and this must not be buried: Kirgis's own confound is comparatively benign.**
His two arms were top-3 logprob weighting (≈ our label scoring) and the mean of ten sampled
responses (≈ our sampled). Those two rank models at **ρ = 0.880, minimum 0.765 across
foundations.** So the specific methodological flaw in his design — the one that motivated this
whole project — turns out to be one his conclusions can largely survive. Saying so is not a
concession; it is the result of the audit, and a write-up that suppressed it would be
dishonest.

---

## 4. Claim-by-claim bearing on Kirgis

| Kirgis's claim | our bearing | strength |
|---|---|---|
| 1. MFT has explanatory power for LLM moral judgment | untouched — we did not test this | — |
| 2. Models diverge from the human baseline | **split verdict (Tier-0 audit, 2026-08-08).** *Divergence*: yes, under every method — severity compression (slopes −0.27 to −0.71) plus over-moralisation of Social-Norms items (+0.8 to +1.1 error under all four methods). *His directional pattern* (overweight Care/Fairness/Liberty, underweight Loyalty/Authority/Sanctity): **absent under every method on this sample** — mean gaps ≈ 0, no method shows it for a majority of models, while methods agree with each other at mean ρ = 0.84. A replication failure on ≤14B open models, not a method artifact. Family-dependent (gemma/granite/yi show it; qwen/mistral/phi/smollm show the reverse — under every method). Baseline caveat stands. Full audit: `results/derived/kirgis_pattern_audit.md` | ESTABLISHED (as stated) |
| 3. Providers differ systematically | **the most exposed claim, but less than feared.** Method perturbation is comparable to between-model variance (R ≈ 0.5–1.0), and his method is collinear with provider for five of six providers. However his particular method pair agrees at ρ = 0.88, so the ranking is unlikely to be an artifact of *that* confound | SUGGESTIVE |
| 4. Divergence grows with capability | untested here. Our roster is capped at 14B and does not span his capability range | NOT SHOWN |

**NOT SHOWN — that Kirgis's conclusions are wrong.** We did not replicate his models, his
prompt, or his capability range. We show his design carries a risk, and that for his specific
choice of methods the risk is modest.

### 4b. Tier-0 audit (2026-08-08): what the pattern audit adds

Three points, each method-stable and therefore *not* attributable to his scoring confound:

1. **The individualizing-over-binding pattern does not appear in ≤14B open models.** All
   four methods agree (per-model gap correlations 0.67–0.98) and all four put the mean gap
   at ≈ 0. His pattern, if real, is a property of his sample — frontier-scale, heavily
   post-trained models — not of language models per se. **The Tier-3 size ladders (Qwen
   0.5→72B, Llama 1→70B) now directly test whether the pattern emerges with scale**, which
   would unify his claims 2 and 4 into "the moral-profile divergence is a capability
   phenomenon". Registered predictions P5/P6 cover this before any large-model data exists.
2. **Severity compression explains most of the error structure.** Errors track how *mild*
   the human rating is (OLS slopes −0.27 to −0.71): models over-rate mild items and
   under-rate severe ones, whatever the foundation. After removing compression, a weak
   residual in Kirgis's direction appears (+0.07 to +0.11, roughly half of models) —
   suggestive at best. Much of any Figure-2-style pattern is arithmetic about item severity
   profiles per foundation, not moral content.
3. **For his claim 2, sampling dominates scoring.** Which model families you include moves
   the observed pattern far more than which of the four methods you use. That reframes the
   original audit question: the scoring confound was the visible flaw, but the model sample
   is the larger inferential lever.

### 4c. Tier-0 audit (2026-08-08): refusal leaks into the logprob readout

Between models, greedy non-answer rate and label-scoring retained mass are strongly coupled
(ρ = −0.60, n = 20). The single differential case in the sample is the predicted signature
exactly: Llama-3.1-8B craters to mass 0.475 on Sanctity (vs 0.815 elsewhere) at 35%
behavioural refusal on precisely that foundation. **Label scoring does not avoid the refusal
confound — it hides it**, and renormalisation then manufactures a confident score from the
remaining digit mass. Two implications: logprob-based studies on safety-relevant content must
report retained mass (Kirgis's logprob arm has no such check); and, usefully, mass functions
as a graded refusal detector that needs no generation. Caveat: low mass has a second cause —
Mistral-7B answers 100% yet has mass 0.078 (format mismatch) — so mass flags problems without
identifying which one. Full audit: `results/derived/refusal_leakage_audit.md`.

---

## 5. The methodological findings — probably the strongest material

These do not depend on R and are reproducible from the committed data.

**ESTABLISHED — first-token label scoring silently fails on a large minority of models.** A
faithful implementation produced meaningless output on **6 of 16 models (38%)**, from two
independent causes:

- *Tokenization.* SentencePiece tokenizers encode `"0"` as two tokens (metaspace + digit), so
  a single-token lookup finds nothing (Mistral-7B, Phi-3-mini, Yi-1.5).
- *Position.* The first generated token is often not the answer. Mistral emits `'\n'` 116/116
  times; Phi-3 emits a bare metaspace token; Llama-3.2-1B begins prose with `'I'`; Ministral
  emits `</s>`.

Neither raised an error. Both produced plausible-looking numbers. **The only signal was
retained probability mass** — which we logged solely because the Kirgis reanalysis told us to.

**ESTABLISHED — "free generation" hides a decision that can determine whether a model answers
at all.** Ministral-8B answers 0% of items under greedy decoding and ~50% under sampling, on
byte-identical prompts. Its greedy argmax is `</s>`. This is not refusal — it never refuses,
it never speaks — and the prompt is well-formed by Mistral's own chat template.

**ESTABLISHED — refusal is foundation-dependent, exactly as predicted.** Llama-3.1-8B refuses
35% of Sanctity items under greedy and ~0% elsewhere. Differential missingness by foundation
is structurally identical to the foundation × method interaction, which is why the three
failure types are separated and never pooled.

**ESTABLISHED (from Kirgis's own committed data) — provider logprob APIs cannot be assumed
well-formed.** grok-3-beta returned structurally malformed `top_logprobs` on **51 of 116
responses (44%)**: two entries instead of three, summing to ~0 probability, while the emitted
token's own logprob reported p = 1.0. His renormalisation accidentally rescues these by
recovering the argmax; his *printed formula*, which does not renormalise, would not — grok-3's
mean collapses 1.98 → 1.20 and it drops from rank 4 to 6 of 6. **His code and his paper
disagree**, and for those items "top-3 logprob weighting" was in fact argmax. Scoring method
was therefore not uniform even *within* his logprob arm.

---

## 6. What we cannot claim

- **That the design resolved R.** It did not. All seven verdicts are indeterminate.
- **That method effects generalise beyond this prompt.** We deliberately held one prompt fixed.
  Ministral's silence in particular is likely prompt-sensitive.
- **That string scoring's disagreement is a method effect rather than an artifact.** It retains
  little probability mass (0.22 vs 0.81 for label) because our prompt *displays* the options,
  so it is not textbook cloze. Two readings survive the data and we cannot adjudicate:
  either method choice destabilises model ranking, or string scoring is simply the degraded arm.
- **That published logprob-based work is broadly wrong.** We showed one implementation failing
  on one roster. Narrow version only.
- **Anything about frontier models.** Twenty open models ≤ 14B are not the frontier, and prior
  work suggests method sensitivity is *larger* for weaker models — biggest effect, weakest
  generalisation.

---

## 7. Suggested framing

Lead with the methodological findings. They are established, reproducible, useful to anyone
doing this kind of measurement, and they do not depend on an indeterminate R.

Then the variance ratio, framed honestly: *method perturbation is comparable in magnitude to
between-model variance, we can establish that it is real, and we cannot establish how large —
here is what resolving it would take.* The B2 simulation gives the required N, which turns a
null-ish result into a constructive contribution.

Then Kirgis, fairly: his design carries a real risk, we quantified it, and **for his specific
pair of methods it is modest**. Separately, his logprob arm has a data-integrity problem he
did not detect, and his code does not implement the formula his paper prints.

Do not lead with "Kirgis is wrong". We did not show that, and the honest result is more
interesting than the overclaim.
