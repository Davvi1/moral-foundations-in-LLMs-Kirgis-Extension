# Pre-specified analysis plan

**Title:** Is a language model's measured moral profile stable across scoring methods?
A within-model audit of Kirgis (2025)

**Author:** David Moth (Hertie School)
**Locked:** 2026-08-07, git tag `analysis-plan-locked`, commit `75b57b2`

## Status — read this before describing the study anywhere

This plan was fixed **before any confirmatory data existed** (verifiable: the tagged commit
contains no `results/raw/`). It was deliberately **not** deposited with an external registry.

**Therefore: call this a *pre-specified analysis plan*, never a *preregistration*.** A git tag
in a repository the author controls is an internal discipline device, not independent
verification — the author could in principle have retagged. That distinction is small in
practice and fatal in a write-up if you get it the wrong way round. If the repository is later
pushed to a public host, the push timestamp becomes third-party evidence *from that date
onward*, but not before.

What this buys you is still real: the decision rule cannot drift after results arrive, because
changing it now produces a visible diff against a tagged commit. What it does not buy you is
the right to say "preregistered".

Everything below was fixed before the confirmatory run. The reanalysis of Kirgis's published
data (Section 9) is **exploratory** and is labelled so throughout.

---

## 1. Study information

### Research question

Kirgis (arXiv:2511.11790) administered the 116 Moral Foundations Vignettes to 21 closed
frontier models and reported that (a) models diverge from a US human baseline, (b) providers
differ systematically, and (c) divergence increases with capability. His scoring method was
forced to vary by provider — top-3 logprob weighting where the API exposed it, mean of ten
sampled responses otherwise — making scoring method almost entirely collinear with provider
(total for five of six providers; within OpenAI it is confounded with model identity instead).

**Question:** when scoring method is manipulated *within* model, holding the prompt fixed, are
the resulting foundation profiles and model rankings stable?

### Hypotheses

We do not predict a direction. The design is an audit, and **a null result — profiles and
rankings stable across methods — is a substantive finding and will be reported as such.** This
is committed to in advance because disagreement is the more publishable direction and therefore
the direction of drift.

Formally, for each foundation *f* we estimate

    R_f = σ²(model × method) / σ²(model)

the size of the method-induced perturbation to a model's position relative to how much models
actually differ. Kirgis's between-model and between-provider claims presuppose R is small.

---

## 2. Design

Fully crossed, within-model: **N models × 4 scoring methods × 116 items.** Every method is
applied to every model on every item. No condition is assigned; all cells are observed.

### The four conditions

Terminology follows the MCQ scoring literature.

| condition | what is scored |
|---|---|
| label scoring | probability of the option label token ("0"…"4") at the first generated position |
| string scoring | full-sequence log-likelihood of the option text ("Not at all wrong") |
| free generation, greedy | decode at T = 0, parse the digit |
| free generation, sampled | sample at T = 1, k = 10, parse, average |

Label and string scoring both yield a **continuous expectation over 0–4** so that they differ
only in *what* is scored, never in *how* it is aggregated.

### What is held fixed

The **prompt is byte-identical across all four conditions**, including the system turn. This
requires overriding QSTN's per-method default system prompts, which otherwise vary by response
generation method and would reintroduce the confound under audit. Verified by diffing the
rendered chat-templated strings; see `config/prompt.yaml`.

Kirgis held his prompt constant across both of his arms (`surveys/mft_base.py`: the same
`QuestionLinearScale` regardless of arm; only `logprobs=True` and `samples` differ). Varying
only the readout is therefore what audits *his* design.

---

## 3. Sampling plan

**Existing data:** none of the confirmatory data existed when this plan was locked.

**Units:** open-weight instruction-tuned models, ≤14B parameters, target **N ≈ 20**, minimum
N = 13. All 116 items administered to every model under every condition.

**Sample size rationale — by simulation, not convention.** R is a ratio of two variance
components, both estimated from few groups. A design simulation calibrated to Kirgis's own
observed variance components (`scripts/design_simulation.py`,
`results/derived/design_simulation.md`) gives interior-band classification accuracy of 0.64 at
N=8, 0.76 at N=13, 0.86 at N=20, 0.94 at N=30. N=13 misclassifies a genuinely "degraded"
R ≈ 0.5 about once in four. **N = 8 will not carry the primary claim.**

**Stopping rule:** all planned models, or the roster is truncated for time. Any truncation is
reported with the achieved N and its simulated accuracy.

---

## 4. Variables

**Outcome:** severity score on 0–4 per model × item × condition (× replicate for sampled).

**Manipulated:** scoring method (4 levels, within model and item).

**Classification:** moral foundation per item, from Clifford et al. (2015) — Care, Fairness,
Loyalty, Authority, Sanctity, Liberty, Social Norms. Note Kirgis's administered set retains
only the emotional-harm Care items, so **Care = emotional harm only** here.

**Human baseline:** per-vignette mean wrongness from Clifford et al. (2015) Table 1,
pp. 1183–1186. Not nationally representative — a Qualtrics panel restricted to ages 18–40 and
balanced on ideology, n ≈ 30 per vignette.

---

## 5. Analysis plan

### Primary — variance ratio

Per foundation, crossed random effects:

    s_mir = μ + γ_r + u_m + w_mr + v_i + e_mir

    γ_r    fixed effect of scoring method (calibration shift — not of interest)
    u_m    random model intercept          → σ²_model
    w_mr   random model × method           → σ²_model×method
    v_i    random item intercept           → σ²_item
    e_mir  residual, METHOD-SPECIFIC       → σ²_r

**Method-specific residual variances are mandatory.** The four methods have structurally
different error variance — label and string scoring are deterministic expectations, greedy is
discretised to integers, sampled carries Monte Carlo error of order 1/√k. A single residual
variance misattributes this into σ²_model×method and inflates R mechanically, biasing toward
the more publishable result. **R is reported with and without this correction.**

Estimation is Bayesian (`bambi` / `pymc`), giving a posterior on R_f. This is required, not
stylistic: moment estimators return σ̂²_model ≤ 0 — leaving R undefined — on up to 7.4% of
simulated replicates at N=8.

### Decision rule — fixed in advance, at the tagged commit

| interval position | verdict |
|---|---|
| 95% CrI entirely below 0.25 | between-model comparisons **robust** to scoring method |
| entirely within 0.25–1.0 | **degraded** — report with caution, rankings not trusted alone |
| entirely above 1.0 | **not interpretable** |
| straddles a boundary | **indeterminate** |

The `indeterminate` verdict exists because the simulation shows no feasible N resolves an R
sitting near a boundary. Forcing a three-way call would manufacture false precision.

**Multiplicity:** all seven foundation-level intervals are reported together, never
selectively. No correction is applied because no null-hypothesis test is performed. The
headline claim is made at foundation level and not aggregated into a single verdict.

### Secondary — rank agreement (descriptive only)

Spearman ρ of the model ordering under each pair of methods, within foundation, after centring
out the method main effect. 6 pairs × 7 foundations. **No pass/fail threshold is attached** —
at this N the statistic is too blunt to carry one.

### Controls

- **Permutation null:** shuffle method labels within model × item, recompute. Must recover
  R ≈ 0; if not, the model is misspecified rather than the world being interesting.
- **Positive control:** all four methods must rank purity violations above social-norm
  violations, in the same direction as Clifford's per-vignette human means.

### Exclusions — AMENDED 2026-08-08, after collection, before any variance ratio

The rules below were fixed once the data existed and the QA pass had run, but **before any
outcome model was fitted**. Verifiable in git: the tag carrying them precedes the first
analysis script. This is weaker than fixing them in advance and stronger than choosing them
once the answer is visible. Describe it exactly that way.

- **Parse-success threshold 0.50** per model × condition × foundation cell, free-generation
  conditions only. Label and string cannot parse-fail — they read a distribution, not text.
- Everything reported **with and without** exclusions, plus a table of what was dropped.
- **internlm2_5-7b-chat string** = structurally missing (116/116 token-boundary failures), not
  a low score. Model retained on its other three conditions.
- **`scan`-parsed rows** (digit recovered from prose) reported separately; primary analysis
  repeated without them.
- **Achieved N reported with its simulated accuracy**, never the headline N=20.
- **Three failure types separated, never pooled:** `empty_output` (EOS as argmax — a decoding
  artifact), `refusal` (declined in words — a value-laden act expected to correlate with
  foundation), `unparseable` (wrote text, no digit). Merging them would make the
  foundation × method confound uninterpretable.

### Exclusions, specified in advance

- Refusal and parse-failure rates logged per model × foundation × method.
- Any model × foundation cell with refusal rate > 10% is flagged; the analysis is run **with
  and without** it and both are reported.
- Models below a stated parse-rate threshold are reported separately from the primary analysis.
- **Provider/output integrity:** total probability mass across returned logprobs is recorded
  per response. Responses with malformed logprob output are flagged and reported. (This check
  exists because the exploratory reanalysis in Section 9 found exactly such corruption in
  published data.)

---

## 6. Known limitations, stated in advance

- Not a prompt-level replication of Kirgis — his EDSL wire format is not reproducible.
- Our string scoring shows the options in the prompt, so it is **not textbook cloze**, which
  omits them. No single prompt is optimal for both label and string scoring; a constant prompt
  is required by the estimand, so this is a design limitation rather than an implementation
  defect.
- Small instruction-tuned models are not the frontier, and prior work suggests method effects
  are larger for weaker models — biggest effect, weakest generalisation.
- Treating a token distribution as a response distribution is a construct assumption imported
  from human psychometrics. The MFV was validated on people.
- Whether scoring method is a researcher degree of freedom or part of the construct definition
  is a values question about what "a model's moral profile" means, not a technical one.

---

## 7. What would falsify the value of this study

If R is small and rank agreement is high across all foundations, Kirgis's between-model
comparisons are robust to the confound and the audit returns a clean null. That will be
reported as the result.

---

## 8. Prior work this does not claim to supersede

Method effects on value-laden questionnaires are **already established** — QSTN
(arXiv:2512.08646) compared 8 response generation methods on ANES/GLES/ATP and recommended
against token-probability methods; Wang et al. (ACL Findings 2024) showed first-token
probabilities diverge from text answers. This study's contribution is narrower: (a) the first
audit of a specific published model-characterisation claim against its own scoring confound,
and (b) a different estimand — QSTN asks which method best *aligns with human respondents*
(simulation); this asks whether the model's *own* profile and ranking are stable (measurement).
A method can win QSTN's criterion and fail this one.

---

## 9. Exploratory (outside this plan)

A reanalysis of Kirgis's published logprob responses
(`results/derived/kirgis_reanalysis.md`) found that one model, grok-3-beta, returned
structurally malformed `top_logprobs` on 44% of responses, and that his code's renormalisation
step — which differs from the formula printed in his paper — accidentally masks this. **This is
analysis of existing public data and is reported as exploratory throughout.** It motivated the
integrity check added to Section 5, which *is* part of this pre-specified plan.
