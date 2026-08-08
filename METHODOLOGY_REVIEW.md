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

The v1 string condition scores the bare phrase ("Very wrong") as a continuation. Three pieces
of evidence say that is the wrong surface form:

1. Retained probability mass: **0.22** for string vs 0.81 for label. The model's probability
   is not where we are looking.
2. The models' own greedy outputs show their natural answer format is **`"3: Very wrong"`** —
   digit, colon, phrase. The phrase appears *after* a digit prefix we are not conditioning on.
3. The one model where string mass is high (Mistral, 0.87) is the one whose *label* mass is
   broken (0.08) — the two readouts chase the same probability, which sits in different
   surface forms per model.

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

Our roster caps at 14B; his claim is about scale. arXiv:2403.00998 predicts method sensitivity
*shrinks* with capability — directly testable with within-family size ladders:

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
