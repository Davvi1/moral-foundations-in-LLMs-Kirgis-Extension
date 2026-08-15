# Is a language model's moral profile stable across scoring methods?

A replication-plus-audit of Kirgis, *"Differences in the Moral Foundations of Large Language
Models"* ([arXiv:2511.11790](https://arxiv.org/abs/2511.11790)), on open-weight models, with
**scoring method manipulated as a within-model treatment**.

---

## The question

Kirgis administered the 116 Moral Foundations Vignettes to 21 closed frontier models and
reported that models diverge from a US human baseline, that providers differ systematically,
and that divergence grows with capability.

His scoring method was **forced to vary by provider** — top-3 logprob weighting where the API
exposed it, mean of ten sampled responses everywhere else. Scoring method is therefore almost
entirely collinear with provider in his design (total for five of six providers; inside OpenAI
it is confounded with model identity instead). That is a non-identification, not something
fixable with a covariate.

This project administers the same instrument to open-weight models, where **all four scoring
methods can be applied to every model**, and asks whether the resulting foundation profiles and
model rankings survive the change of method.

### What is and is not new

That scoring method matters on value-laden questionnaires is **already established** — see QSTN
([arXiv:2512.08646](https://arxiv.org/abs/2512.08646)) and Wang et al. (ACL Findings 2024). The
contribution here is narrower and specific:

1. the first audit of a **specific published model-characterisation claim** against its own
   scoring confound; and
2. a **different estimand** — QSTN asks which method best aligns model output with human
   respondents (a *simulation* criterion); this asks whether the model's own profile and the
   model ranking are stable across methods (a *measurement* criterion). A method can win QSTN's
   criterion and fail this one.

Anything stronger than that is over-claiming.

## The six arms

Names follow the MCQ scoring literature, not invented terminology. The plan specified four;
the v2 harness splits string scoring into two surface forms and adds a cloze probe, because
the four-arm version could not tell "the same measurement" from "a different one" (see
`docs/V1_TO_V2.md`).

| arm | what is scored | fixed prompt? |
|---|---|---|
| **label scoring** | probability of the option label token (`"0"`…`"4"`) as a forced continuation | yes |
| **string scoring, line** | full-sequence log-likelihood of the whole option line (`"3: Very wrong"`) | yes |
| **string scoring, bare** | full-sequence log-likelihood of the option text alone (`"Very wrong"`) | yes |
| **free generation, greedy** | decode at T=0, parse the digit | yes |
| **free generation, sampled** | sample at T=1, k=10, parse, average | yes |
| **cloze** | option text scored with the option list *removed* from the prompt | **no — by design** |

The **prompt is byte-identical across the five fixed-prompt arms** — asserted per item by
`validate_results.py`, zero violations across 3,596 model × item cells. **Cloze deliberately
varies it**, which is what makes it cloze, and it is therefore **excluded from the primary
variance ratio**: a prompt effect inside a number defined as a method effect is the error this
project audits Kirgis for. Including it inflated R by 2.70× for several weeks — `CORRECTIONS.md`
C15, the worst entry in the log.

See `config/prompt.yaml` for the two contestable decisions the fixed prompt required, and the
limitation it forces (our string scoring shows the options in the prompt, so it is not textbook
cloze — which is why the separate cloze arm exists).

---

## Repository layout

```
config/prompt.yaml            the fixed prompt; two design decisions argued in full
config/models.yaml            the roster, with pinned revision SHAs
data/source/                  raw inputs, never edited — see PROVENANCE.md
data/mfv_116.csv              116 items, QSTN format
data/mfv_116_meta.csv         foundation labels + Clifford's per-vignette human means
scripts/build_items.py        derives the two data files from source; self-verifying
scripts/run_experiment.py     the harness: six arms, checkpointed, manifest per model
scripts/build_analysis_data.py  raw CSVs -> analysis_long_v2.csv, with exclusions
scripts/analyse_variance_ratio.py  the primary estimand R
scripts/analyse_controls.py   permutation null, positive control, pairwise R, leave-one-out
results/raw/                  one CSV + manifest per model, as collected
results/derived/              analysis-ready outputs and every derived report

docs/ANALYSIS_PLAN.md         the plan, locked before any confirmatory data existed
docs/state.md                 living record — registered predictions, verbatim
docs/FINDINGS.md              synthesis; claims with strength labels
docs/LIMITATIONS.md           everything constraining what may be claimed
docs/CORRECTIONS.md           every claim withdrawn or reversed, and how it was caught
docs/METHODOLOGY_REVIEW.md    flaw tracker, F1–F9, with resolution status
docs/METHODS_EXPLAINER.md     how each arm is actually computed
docs/V1_TO_V2.md              why the harness was rebuilt
docs/THE_NEXT_EXPERIMENT.md   what the design analysis says a follow-up would need
docs/references.md            every citation verified by fetching the source
```

## Reproducing

### Item file

```bash
python scripts/build_items.py
```

Stdlib only, runs on Python 3.10+. Asserts n=116 and the foundation counts (Authority 17,
Care 16, Fairness 17, Liberty 17, Loyalty 16, Sanctity 17, Social Norms 16) and fails loudly
rather than emitting a bad questionnaire.

### Tests

```bash
pip install pytest transformers truststore pyyaml
pytest                      # 303 tests, ~2.5 min, no GPU needed
```

vLLM is Linux+GPU only, so the harness is exercised against a faithful fake of the vLLM API
(`tests/fake_vllm.py`) driven by **real tokenizers** over the **real 116 items**. The suite
covers the prompt invariant, tokenization claims, all six arm runners, the manifest contract,
checkpointing, VRAM planning, and sequence-length budget.

It also guards the claims themselves, which matters more than it sounds: `test_headline_numbers.py`
recomputes every ρ quoted in the write-up from the committed data, `test_design_commitments.py`
asserts that design decisions written in prose are enforced in code, and
`test_determinism.py` rebuilds the analysis dataset under two `PYTHONHASHSEED` values and
requires byte-identical output. Each exists because something slipped past its absence — see
`docs/CORRECTIONS.md`.

The v2 scorer suites need network access for real tokenizers:

```bash
pytest tests/test_conditions_v2.py    # known-answer + real-tokenizer checks
pytest tests/test_harness_smoke.py    # integration checks against the fake vLLM
```

Three bugs were caught this way that would each have cost GPU time:

- the manifest crashed on `yaml`'s `datetime.date`, *after* all four conditions had run —
  destroying a full model's inference on every model;
- `Qwen2.5-14B` (28.8 GiB in bf16) does not fit a 32 GiB card and would have OOM'd after a
  28 GB download;
- the `--help` sweep itself was silently reverting `config/models.yaml` from 30 models to 20
  on every run, because two scripts had no argparse and so *ran* instead of printing usage
  (`docs/CORRECTIONS.md` C9).

### Pre-flight

Run on the pod before anything expensive:

```bash
source /workspace/env.sh && python scripts/preflight.py
```

Thirty seconds. Checks env vars, packages, GPU and `sm_120` kernels, config integrity, the
memory plan for all 20 models, that every pinned revision resolves, and that a prompt renders
within the length budget. Exit 0 means safe to start.

### Inference environment

vLLM is Linux-only and needs a GPU. Verified working configuration:

| | |
|---|---|
| image | `runpod/pytorch:1.0.2-cu1281-torch280-ubuntu2404` |
| GPU | RTX PRO 4500 Blackwell, 32 GB (sm_120) |
| Python | 3.12.3 |
| vLLM | 0.26.0 |
| transformers | 5.14.1 |

```bash
pip install "qstn[vllm]"
export VLLM_USE_FLASHINFER_SAMPLER=0   # REQUIRED on sm_120 — see below
python scripts/probe_tokenization.py --model Qwen/Qwen2.5-0.5B-Instruct
```

**`VLLM_USE_FLASHINFER_SAMPLER=0` is not optional on Blackwell.** FlashInfer's
`top_k_top_p_sampling_from_logits` crashes vLLM engine initialisation on sm_120.

## Findings that shape the design

Established during the go/no-go check and the tokenization probe; all verified against sources
rather than recalled.

- **Kirgis's code and his paper disagree.** The printed formula
  `E = Σ_{k=1..3} s_k exp(ℓ_k)` has no denominator; the code returns
  `weighted_sum / total_prob`. The code also filters the top-3 to digit tokens first, so the
  denominator is a data-dependent subset of size 1–3. When only one digit survives, the
  estimator **degenerates to argmax exactly**.
- **`"0"` and `" 0"` are different tokens** (`[15]` vs `[220, 15]` on Qwen), and the model emits
  the bare form. Verify per tokenizer family; do not assume.
- **Options 0 and 1 share a first token** (`'Not'`), so string scoring *must* be a full-sequence
  log-likelihood — a single-position readout cannot separate them.
- **Kirgis's Care foundation is emotional harm only** — all 16 of Clifford's physical-harm Care
  items are dropped from the administered 116.
- **The human baseline is not nationally representative.** Clifford recruited from a Qualtrics
  panel restricted to ages 18–40 and balanced on ideology, with n ≈ 30 per vignette.

## Pre-specified analysis plan

The analysis plan is fixed in `docs/state.md` before any confirmatory data exists. Primary statistic
is a variance ratio per foundation,

```
R_f = σ²(model × method) / σ²(model)
R < 0.25 robust · 0.25–1.0 degraded · R > 1.0 not interpretable
```

with **method-specific residual variances** (the four methods have structurally different error
variance; a single residual term inflates R mechanically toward the exciting result).

**A null result is a real finding and was committed to in advance.** Disagreement is the more
publishable direction and therefore the direction of drift.

## Status

**Collection and analysis complete. 31 models collected, 30 analysed, 21,576 rows.** What
remains is the write-up. Full results in `docs/FINDINGS.md`; everything constraining them in
`docs/LIMITATIONS.md`; every claim withdrawn or reversed in `docs/CORRECTIONS.md`.

### Headline, stated at the strength the evidence supports

- **The model × method interaction is real** — a 700-fit permutation null collapses to ≈ 0.001
  against an observed R of 0.13–0.47 — **but its magnitude was never resolved.** All seven
  verdicts are `indeterminate` and our own power prediction (P7) is falsified. The observed
  values land on the 0.25 band boundary, where the design simulation puts classification
  accuracy at 0.51 *regardless of N*. This estimand is not resolvable at any N a student
  project can reach, and saying so is the result.
- **The disagreement is concentrated, twice over.** Almost all of it comes from two low-mass
  probes — the four arms carrying real probability mass agree at pairwise R ≤ 0.20 — and **one
  model of 27 carries 34% of the interaction** (C16). Both point the same way: the method
  effect lives in cells the design can barely measure.
- **Kirgis's specific confound is survivable.** His two arms (≈ `label` and ≈ `sampled`) rank
  models at **ρ = 0.818** over the six moral foundations, pairwise R = 0.081. The flaw that
  motivated this project is one his conclusions can largely survive, and reporting that is the
  audit's result rather than a concession.
- **The strongest material is methodological**, and it is independent of R: a faithful v1
  label-scoring implementation **silently produced meaningless output on 6 of 16 models**, with
  retained probability mass the only signal; free generation hides whether a model answers at
  all (Ministral-8B: 0% under greedy, ~50% under sampling, byte-identical prompts); and a
  multi-readout design converts an untestable missing-not-at-random assumption into a measured
  one.
- **Not shown: that Kirgis is wrong.** We did not replicate his models, prompt, or capability
  range, and we independently support two of his four claims.

### Nineteen corrections, logged rather than absorbed

`docs/CORRECTIONS.md` records every withdrawn claim and how it was caught — including C15,
where our own primary estimand contained a prompt-confounded arm for weeks despite three
documents saying it must not, and C19, where the limitations document spent five days claiming
work was outstanding that had already been done. **None was found by looking at a result and
feeling it seemed wrong.** That is the project's own thesis turned on itself, and it belongs in
the write-up.

## Licence

Code MIT (see `LICENSE`). Data has separate provenance and redistribution considerations —
see `data/source/PROVENANCE.md`.
