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

## The four conditions

Names follow the MCQ scoring literature, not invented terminology.

| condition | what is scored |
|---|---|
| **label scoring** | probability of the option label token (`"0"`…`"4"`) at the first generated position |
| **string scoring** | full-sequence log-likelihood of the option text ("Not at all wrong") |
| **free generation, greedy** | decode at T=0, parse the digit |
| **free generation, sampled** | sample at T=1, k=10, parse, average |

The **prompt is held fixed and byte-identical across all four**. See `config/prompt.yaml` for
the two contestable decisions this required, and the limitation it forces (our string scoring
shows the options in the prompt, so it is not textbook cloze).

---

## Repository layout

```
config/prompt.yaml          the fixed prompt; two design decisions argued in full
data/source/                raw inputs, never edited — see PROVENANCE.md
data/mfv_116.csv            116 items, QSTN format
data/mfv_116_meta.csv       foundation labels + Clifford's per-vignette human means
scripts/build_items.py      derives the two data files from source; self-verifying
scripts/probe_tokenization.py   the "0" vs " 0" hazard check, per tokenizer
results/                    probe logs and derived, analysis-ready outputs
state.md                    living record — decisions, analysis plan, findings
references.md               every citation verified by fetching the source
RESUME.md                   operational sequence + pod cheat-sheet
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
pytest                      # 124 tests, ~35s, no GPU needed
```

vLLM is Linux+GPU only, so the harness is exercised against a faithful fake of the vLLM API
(`tests/fake_vllm.py`) driven by **real tokenizers** over the **real 116 items**. The suite
covers the prompt invariant, tokenization claims, all four condition runners, the manifest
contract, checkpointing, VRAM planning, and sequence-length budget.

Two bugs were caught this way that would each have cost GPU time:

- the manifest crashed on `yaml`'s `datetime.date`, *after* all four conditions had run —
  destroying a full model's inference on every model;
- `Qwen2.5-14B` (28.8 GiB in bf16) does not fit a 32 GiB card and would have OOM'd after a
  28 GB download.

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

The analysis plan is fixed in `state.md` before any confirmatory data exists. Primary statistic
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

Environment verified, instrument built, prompt fixed, tokenization hazard discharged. Next: a
design simulation to establish whether R is estimable with useful precision at feasible N —
because R is a ratio of two variance components estimated from few groups, and the interval may
otherwise be too wide for the decision rule to be informative.

## Licence

Code MIT (see `LICENSE`). Data has separate provenance and redistribution considerations —
see `data/source/PROVENANCE.md`.
