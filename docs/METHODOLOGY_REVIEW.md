# Methodology review — status after the v2 collection

> **STATUS, updated 2026-08-11.** Three corrections postdate the original 2026-08-09 table and
> are folded in below: **C13** (the QA gate had never passed on v2), **C14** (an extrapolation
> reported without its range check) and **C15** (cloze inside the primary variance ratio). The
> F-numbering is unchanged so older commits still line up.
>
> **STATUS, originally 2026-08-09.** Every flaw below has now been acted on, and the outcomes are
> recorded here rather than left implied. Primary results moved to the v2 harness — **31 models
> collected, 30 analysed** after the discrimination exclusion (`LIMITATIONS.md` §22);
> see `FINDINGS.md`. Resolution status per item:
>
> | # | flaw | status |
> |---|---|---|
> | F1 | string scoring mismeasures | **RESOLVED, with a twist.** The full option line does carry the mass (P1′, 31/31 models) — but it turns out to be *the same measurement as label scoring* (ρ = 0.964, item-level r = 0.988), because the prompt displays the digit→phrase mapping. The design has **three independent probability readouts, not four**. Half F1's original evidence was withdrawn as invalid (C6). |
> | F2 | label position-scan degrees of freedom | **RESOLVED, and the headline figure is corrected.** Forced continuation gives exact p_k with no top-k truncation and no position rule. Label mass went 0.81 → 0.997 **on the smoke-test model**; across the roster it did not — 7 of 31 models sit below 0.5 and Mistral-7B is at **0.008**. This row read "Label mass 0.81 → 0.997" unqualified until 2026-08-15, which is the claim `LIMITATIONS.md` §3 exists to withdraw; the retraction reached `FINDINGS.md` and not this table. Forced continuation removed the *truncation* and *position* defects; it cannot make a model put mass on a digit it does not want to emit. |
> | F3 | underpowered by design | **ACTED ON, PREDICTION FAILED.** N raised 20 → 31. P7 predicted ≥2 foundations would escape `indeterminate`; **none did**. The estimand is not resolvable at feasible N. Family random effect remains unfitted — see "still outstanding". |
> | F4 | capability claim untested | **RESOLVED, and the strongest positive result.** Ladders to 72.7B. P5 supported on both, LOO-robust, after removing a compression confound that would have manufactured a third of the effect. |
> | F5 | everything conditional on one prompt | **NOT DONE, and this row was load-bearing in the worst way.** The cloze arm varies the prompt, changes two things at once, and *must* be excluded from the primary — this sentence was one of the three places that said so while **no code enforced it**. It was included in every published R until 2026-08-11, inflating R by **2.70×**. See **C15**. Prompt-as-designed-factor remains future work: `THE_NEXT_EXPERIMENT.md`. |
> | F6 | Kirgis's substantive finding never audited | **RESOLVED at both N** — meaning the audit now exists, *not* that the claim is established. Raw gap cannot adjudicate (compression predicts negative, C3); compression-adjusted gap **+0.081 to +0.187** across six readouts (corrected 2026-08-15 from "+0.077 to +0.179", which was the **N=31, no-exclusions** basis — C18), and it grows with scale. **The audit artifact's own verdict still reads "SUGGESTIVE, not established, in either direction"** — only 15/30 models show the adjusted gap and it carries no interval. It predates P5 and was never re-run, so `FINDINGS.md`'s SUPPORTED rests entirely on the scale evidence, which is marginal per ladder. |
> | F7 | refusal contaminates readouts | **RESOLVED and extended.** ρ = −0.54 over 31 models. Plus the MNAR audit: a multi-readout design measures the missing-data bias instead of assuming it. |
> | F8 | internlm boundary / greedy determinism | **PARTIALLY RESOLVED — this row previously said RESOLVED and overstated.** The *boundary* half is resolved: LCP computed engine-side, shift 0 on all 31 models (the original diagnosis of *why* internlm failed was falsified, C7, and the true cause remains unverified — v2 does not depend on it). The *greedy determinism* half is now **RESOLVED, and it FAILED**: greedy is not reproducible across runs — raw text differs on 10.56% of cells, the parsed score on 2.28%, mean shift 1.038. See `LIMITATIONS.md` §12 and `results/derived/greedy_determinism.md`. |
> | F9 | permutation-null deviation | **RESOLVED, on a six-arm basket — see C17.** 700/700 full-MCMC fits, null median 0.0006–0.0021. Two corrections to this row, both made 2026-08-15. **(a)** The observed range it compared against, "0.34–1.08", was the **with-cloze** basis; design-conformant it is **0.133–0.469**, so the margin is ~2 orders of magnitude rather than ~3. **(b)** "The deviation paragraph can be deleted" was wrong twice over: `controls_v2.md` §1 is *still* the moment estimator, so its deviation note is still true and stays; and the MCMC null itself was fitted on all six arms, the C15 defect surviving in a second script because the test written in response to C15 checked only `analyse_variance_ratio.py`. The script is now fixed and the guard covers every script that computes R. The **artifact is not refit** — a null collapses to ~0 under any basket, so 700 fits of pod time would move nothing. |
>
> **Found on the limitations pass 2026-08-09, RESOLVED 2026-08-10:** the `scan`-parsed
> sensitivity specified at `ANALYSIS_PLAN.md:192` had never been run. It has been:
> `variance_ratio_v2_noscan.csv`, shifting R by −20% to +3% with no verdict change, and moving
> the greedy model ranking to ρ = 0.832 against the all-rows ranking. **The family random
> effect was fitted the same day** (`variance_ratio_v2_family.csv`, −2% to +5%).
>
> **Still outstanding, deliberately:** F5 (prompt as designed factor); a scale-augmented
> variance model that lets σ(model:method) depend on log-parameters — the right version of the
> P6 follow-up, dropped from the pod batch because a naive small/large split would be
> underpowered (N≈9) and return `indeterminate` for both halves.
>
> **Added 2026-08-15 (C16), and it belongs in this table more than most rows do:** no
> robustness check in this project ever varied the **models**. Doing so shows **one model of 27
> carries 34% of the interaction sum of squares**, and dropping it halves R — the same order as
> C15, from one model rather than one arm. See `controls_v2.md` §5.


<details>
<summary>Original review, written before the v2 collection</summary>

# Methodology review — flaws, fixes, and the Phase-2 program

Requested 2026-08-08 after the first full results. Scope note, named rather than slid past:
the original constraint was a two-day sprint capped at 14B models. David has explicitly
opened both — "more models, as comprehensive as possible", "open to rerunning all the
data-collection", bigger models to test scaling. What follows is therefore a deliberate
Phase 2, not creep within the sprint. Spend to date ≈ $5 of $100.

Ranking principle: only flaws that threaten or limit the actual claims. No bickering about
trivia. Each entry: what is wrong, the evidence, the fix, what it costs.

---

## F1 — String scoring v1 mismeasures where the answer probability lives
**Severity: high — it may invalidate the single most striking result.**

The v1 string condition scores the bare phrase ("Very wrong") as a continuation. Evidence that
this is the wrong surface form:

1. ~~Retained probability mass: **0.22** for string vs 0.81 for label.~~ **WITHDRAWN
   2026-08-08 — this comparison was invalid and the error was mine.** v1 ran
   `length_normalise=True`, and `expectation()` computes mass from whatever it is handed, so
   v1's string "mass" is `sum_k exp(per-token *mean* logprob)` — a sum of five geometric
   means, not a probability, and not commensurable with label's mass (computed from raw
   logprobs, where it genuinely is one). A value near 0.2 is the *expected* magnitude for
   that quantity and implies nothing about misalignment. Full derivation and worked example:
   `results/derived/tokenization_boundary_diagnosis.md`.
2. The models' own greedy outputs show their natural answer format is **`"3: Very wrong"`** —
   digit, colon, phrase. The phrase appears *after* a digit prefix we are not conditioning on.
   **This is now the sole argument for F1**, and it is the stronger of the original pair: it
   is an independent observation from generated text rather than an artifact-prone statistic.
3. The one model where string mass is high (Mistral, 0.87) is the one whose *label* mass is
   broken (0.08) — the two readouts chase the same probability, which sits in different
   surface forms per model. (Direction survives the withdrawal, since it is a within-model
   contrast; its magnitude does not, for the reason in point 1.)

**A second, independent v1 defect found while testing v2 (see F8).** The option boundary was
computed with the *local* tokenizer and applied to ids returned by *vLLM*. On **12 of 30**
roster models the chat template already emits BOS and the tokenizer adds another, so the local
count is one short. Under a plain sum that off-by-one cancels in the softmax; **under length
normalisation — which is what v1 used — it does not.** So the v1 string arm was exposed on
those models by a second route entirely.

The headline-looking result — string scoring produces a different model ranking (ρ ≈ 0.33 vs
0.77–0.93 for every other pair) — is therefore confounded: genuine construct difference and
measurement misalignment are indistinguishable in v1.

**Fix (v2):**
- Primary string variant scores the **full option line** `"k: <phrase>"`; bare phrase kept as
  sensitivity.
- Store the **five per-option log-probabilities**, not just the expectation (v1's biggest
  data-design miss — it blocked the within-item ordering diagnostic).
- **Registered prediction, before any v2 data:** full-line mass ≫ phrase mass, and full-line's
  model-ranking agreement with label rises substantially. If it does not, the v1 divergence
  is a real construct difference — either way we learn something.
- Optional: a true-cloze condition (options removed from the prompt). Explicitly
  prompt-varying, analysed outside the fixed-prompt primary.

Cost: harness edit + re-run (folded into any re-collection).

## F2 — Label scoring's fix introduced its own researcher degrees of freedom
**Severity: medium-high.**

The position-scan (up to 4 positions, first whose top-20 contains an option token) rescued six
models but is ad hoc: top-20 truncation means p_k is censored when an option falls outside
the list, and "first position containing a digit" is one imputation choice among several for
models that do not lead with the answer.

**Fix (v2):** compute p_k **exactly** by forcing each digit as a one-token continuation and
reading `prompt_logprobs` — the same machinery string scoring already uses. No truncation, no
top-k dependence. Report **strict position-0** (exact) as the primary label estimator and the
scan variant as secondary; the gap between them is itself a fragility measurement. Also report
retained mass by model × foundation: for safety-tuned models, mass collapsing on Sanctity is
refusal leaking into a "can't-refuse" readout — a construct contamination v1 logged but never
analysed (see F7).

## F3 — The primary analysis was underpowered by design, and we knew
**Severity: high for the headline, fully anticipated.**

All seven verdicts indeterminate; B2 predicted exactly this at N=20 for mid-range R. Two
fixes, both straightforward:

- **More models: N ≈ 30.** B2's interior-band accuracy: 0.86 → 0.94. Candidate additions
  (verify IDs at roster-build time, per standing rule): Qwen2-7B, Phi-3.5-mini, zephyr-7b-beta,
  Falcon3-7B (all verified open earlier); mid-size on a 96 GB card: Mistral-Small-24B,
  gemma-2-27b, Qwen2.5-32B, OLMo-2-32B.
- **Analysis upgrades:** (a) add a **family random effect** — five Qwens are not independent
  draws, and the current model pretends they are, overstating effective N; (b) a **joint
  hierarchical fit** partially pooling the seven foundation-level interaction variances
  (custom PyMC), reported as secondary — borrows strength across foundations, should tighten
  every interval.

## F4 — Kirgis's capability claim (claim 4) is untested, and David wants it tested
**Severity: medium; opportunity: high.**

Our roster caps at 14B; his claim is about scale. arXiv:2403.00998 *suggests* method
sensitivity shrinks with task performance — a visual-inspection remark over four models, not a
measured result (C20) — and it is directly testable with within-family size ladders:

- **Llama-3.1: 1B → 3B → 8B → 70B** (3.1-70B likely covered by the existing 3.1 grant)
- **Qwen2.5: 0.5 → 1.5 → 3 → 7 → 14 → 32 → 72B**

The 70B-class pair needs a bigger GPU (bf16 ≈ 140 GB): one B200 (180 GB, $6.79/hr) or
2× RTX PRO 6000. Weights dominate cost; the runs themselves are minutes. **No quantization** —
quantizing only the large models would make numerics differ by model, a confound in a study
about measurement artifacts.

New analysis: per-model method-spread (and R contribution) vs log parameter count. This turns
"NOT SHOWN" into a real scaling result either way.

## F5 — Everything is conditional on one prompt — the correct home for the "trials" instinct
**Severity: conceptually the deepest limitation; opportunity: the strongest extension.**

The design estimates method variance *given one fixed prompt*. The perturbation literature
(Alzahrani; Rupprecht et al.; Dominguez-Olmedo) shows presentation choices — wording, option
order — move results a lot. A critic can say: your σ²(method) may be small next to
σ²(wording), so who cares which scoring method I use?

**Fix: make prompt a designed factor.** Four cells: base + two stem paraphrases + one
reversed option order (4…0 — targets the documented order/recency biases). Crossed with the
four methods, this identifies:

    σ²(model × method)  vs  σ²(model × prompt)  vs  σ²(model × method × prompt)

— i.e. **which researcher degree of freedom perturbs model rankings more, scoring method or
prompt wording?** To our knowledge the crossed decomposition on a values instrument has not
been done — **NOVELTY CHECK REQUIRED before the write-up claims this** (standing rule: search
first; QSTN did methods, Rupprecht did perturbations, the crossed design is the gap to
verify).

This is also the statistically correct answer to "why no trials": replication belongs on
nuisance parameters, not on re-executing deterministic computations. METHODS_EXPLAINER.md §5.

## F6 — We never audited Kirgis's substantive finding — zero new data needed
**Severity: embarrassing to have missed; cost: an afternoon, $0.**

His headline empirical pattern (claim 2): models overweight individualizing foundations
(care/fairness/liberty) and underweight binding ones (loyalty/authority/sanctity) relative to
the human baseline. We have everything needed to test whether *that pattern* is method-stable:
per-method foundation-level (model − Clifford) errors — his Figure 2, four times over.

- Pattern holds under all four methods → his claim 2 is method-robust: the second
  fair-to-Kirgis result, and a strong one.
- Pattern flips under some methods → the confound bites his actual conclusion, not just his
  design on paper.

Either outcome is a direct, publishable audit. Highest value per unit effort on this list.

## F7 — Refusal mass contaminates the scoring readouts differently per method
**Severity: medium; analysis-only.**

Label scoring renormalises away whatever mass the model puts on refusing — it *forces* an
answer from a model that, behaviourally, declines. Free generation lets the refusal happen
and loses the item. So on Sanctity, label-vs-generation differences partly measure **refusal
propensity**, not moral severity. The mass column contains the evidence; v1 logged it and
never analysed it by foundation. Fix: mass by model × foundation table + sensitivity excluding
low-mass items. Frame as forced-choice vs voluntary-response measurement — a familiar survey
distinction.

## F8 — Hygiene items
- **internlm string boundary:** fix token alignment by suffix-matching (tokenize prompt and
  prompt+option jointly; the option's tokens are the suffix after the longest common prefix)
  instead of assuming concatenative tokenizers. Recovers the one structurally-missing cell.
- **Greedy determinism:** spot-check on the re-run (re-run two models' greedy arm, diff).
  Converts a stated assumption into a verified fact.

## F9 — The permutation-null deviation can simply be removed
**Severity: low; David asked for it.**

Run the full-MCMC null as specified in the plan. On the 48-vCPU box, 700 fits at 4 chains
each ≈ 12 concurrent fits ≈ **1–2 h wall, ~$1–2** — not the overnight $9 originally feared.
The moment-estimator null already run becomes the cross-check. Deviation paragraph deleted
from the write-up.

---

## What we are deliberately NOT treating as flaws

- The indeterminate verdicts themselves — that is the design being honest, not failing.
- The prompt not matching Kirgis's EDSL wire format — unfixable, documented.
- The pre-specified-not-preregistered status — settled, language locked.
- Letter labels (A–E) as another perturbation axis — real but out of scope; numeric parsing
  infrastructure doesn't transfer, and the option-order cell already probes presentation.

---

## The Phase-2 program, priced

| tier | contents | new spend | wall time |
|---|---|---|---|
| 0 | F6 Kirgis-pattern audit, F7 mass analysis (laptop) + F9 full null (pod CPU) | ~$2 | afternoon |
| 1 | v2 harness (F1, F2, F8) + re-run current 20 models, base prompt | ~$10 | ~2 h GPU |
| 2 | roster → ~30 models ≤32B (F3), incl. 24–32B on a 96 GB card | +$10–15 | +2–3 h |
| 3 | 70B-class pair on B200 (F4) | +$10–15 | +1–2 h |
| 4 | prompt-perturbation factor, 4 cells × full roster (F5); 70Bs on 2 cells only | +$15–20 | +4–6 h |
| — | analysis re-runs incl. family effect + joint model (F3) | ~$2 | 2–3 h |

Full program ≈ **$50–55 total against the remaining ~$95.** Every tier is independently
useful; each later tier strengthens a different claim (measurement validity → power → scale →
generality).

Recommendation: all tiers. Tier 0 starts immediately and is free.

</details>
