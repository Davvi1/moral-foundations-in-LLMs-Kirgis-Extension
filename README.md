# Is a language model's moral profile stable across scoring methods?

A replication-plus-audit of Kirgis, *"Differences in the Moral Foundations of Large Language
Models"* ([arXiv:2511.11790](https://arxiv.org/abs/2511.11790)), on open-weight models, with
**scoring method manipulated as a within-model treatment**.

**31 models collected · 30 analysed · 6 scoring arms · 116 vignettes · 21,576 rows · 21 logged
corrections · 322 tests**

---

## Contents

- [The question](#the-question)
- [What is and is not new](#what-is-and-is-not-new)
- [The six arms](#the-six-arms)
- [What we found](#what-we-found)
- [What we cannot claim](#what-we-cannot-claim)
- [The corrections record](#the-corrections-record)
- [Reproducing](#reproducing)
- [Repository layout](#repository-layout)
- [Licence and provenance](#licence-and-provenance)

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

This project administers the same instrument to open-weight models, where **every scoring
method can be applied to every model**, and asks whether the resulting foundation profiles and
model rankings survive the change of method.

**Primary estimand**, per foundation:

```
R_f = σ²(model × method) / σ²(model)

R < 0.25  robust · 0.25–1.0  degraded · R > 1.0  not interpretable
interval straddles a boundary → indeterminate
```

Fitted with method-specific residual variances, because the arms have structurally different
error variance and a single residual term inflates R mechanically toward the more publishable
answer. Bands and decision rule were fixed at git tag `analysis-plan-locked`, in a commit that
provably contains no `results/raw/`.

> This is a **pre-specified analysis plan, not a preregistration.** A tag in a repository the
> author controls is an internal discipline device, not independent verification. The
> distinction is small in practice and fatal in a write-up if stated the wrong way round.

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

---

## The six arms

Names follow the MCQ scoring literature, not invented terminology. The plan specified four; the
v2 harness splits string scoring into two surface forms and adds a cloze probe, because the
four-arm version could not tell "the same measurement" from "a different one"
(`docs/V1_TO_V2.md`).

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
variance ratio**: a prompt effect inside a number defined as a method effect is precisely the
error this project audits Kirgis for. Including it inflated R by 2.70× for several weeks —
`docs/CORRECTIONS.md` C15, the worst entry in the log.

**Roster:** 31 instruction-tuned open-weight models, 0.5B → 72.7B (a 145× span) across 12
families, with complete size ladders for Qwen (8 models) and Llama (4). Revisions are pinned by
SHA in `config/models.yaml`.

### Design decisions worth knowing before reading results

- **`"0"` and `" 0"` are different tokens** (`[15]` vs `[220, 15]` on Qwen), and models emit the
  bare form. Verified per tokenizer family rather than assumed.
- **Options 0 and 1 share a first token** (`'Not'`), so string scoring *must* be a full-sequence
  log-likelihood — a single-position readout cannot separate them.
- **Kirgis's Care foundation is emotional harm only.** All 16 of Clifford's physical-harm Care
  items are absent from the administered 116, so "Care" here means emotional harm throughout.
- **Social Norms is Clifford's non-moral control**, not a seventh foundation. Averaging it into
  foundation-level statistics inflated every cross-method correlation until 2026-08-10; it is
  now reported separately everywhere and the separation is enforced by tests.
- **The human baseline is not nationally representative.** Clifford recruited from a Qualtrics
  panel restricted to ages 18–40 and balanced on ideology, n ≈ 30 per vignette — so each item
  mean carries a standard error of roughly 0.2 on a 0–4 scale.

---

## What we found

Claims carry strength labels: **ESTABLISHED** (directly measured, robust to the checks we ran) ·
**SUPPORTED** (measured, resting on a contestable assumption) · **SUGGESTIVE** (visible,
underpowered or confounded) · **NOT SHOWN**.

Full treatment in `docs/FINDINGS.md`.

### 1. The interaction is real; its magnitude is not resolvable

**ESTABLISHED.** A 700-fit full-MCMC permutation null collapses to a median R of 0.0006–0.0021,
while observed R runs two to three orders of magnitude above it. Destroy the interaction by
construction and the estimator reports none.

| foundation | **R** | 95% CrI | verdict |
|---|---:|---|---|
| *Social Norms — non-moral control* | **0.133** | [0.067, 0.240] | **robust** |
| Care | 0.181 | [0.081, 0.369] | indeterminate |
| Loyalty | 0.181 | [0.089, 0.355] | indeterminate |
| Sanctity | 0.246 | [0.102, 0.527] | indeterminate |
| Liberty | 0.317 | [0.153, 0.633] | indeterminate |
| Fairness | 0.408 | [0.199, 0.810] | indeterminate |
| Authority | 0.469 | [0.231, 0.957] | indeterminate |

**Every moral foundation is `indeterminate`, which falsifies our own registered prediction P7.**
Going from 20 to 31 models resolved nothing — and the reason is more useful than the prediction
was. P7 leaned on the design simulation's "0.94 accuracy at N=30", which is the accuracy *at
R = 0.50*. Six of seven observed values land near the **0.25 band boundary, where the same
simulation puts classification accuracy at 0.51 regardless of sample size.** N was never the
binding constraint. **The estimand landed where no achievable N classifies it**, and that is the
result.

### 2. The disagreement is concentrated, twice over

**ESTABLISHED.** A single pooled R hides that the arms disagree wildly about how much they
disagree. Pairwise R, on one common block:

| tier | arms | pairwise R | mean retained mass |
|---|---|---:|---:|
| **readouts that agree** | `label`, `string_line`, `greedy`, `sampled` — all six pairs | **−0.09 to 0.20** | 0.77, 0.63 |
| **one low-mass probe** | `string_bare` vs each of the above | 0.62 to 1.33 | **0.0028** |
| **prompt-varying** | any pair including `cloze` | 2.52 to 4.32 | 0.046 |

And by model: **one model of 27 carries 34.3% of the interaction sum of squares** — 9.3× an
equal share — and dropping it moves R by −51%, the same order as C15 from one model rather than
one arm.

**These are the same finding from two directions.** The model that dominates, Mistral-7B, is the
one whose label retained mass is **0.008**. The method effect is carried by cells the design can
barely measure. A write-up quoting only the pooled R implies scoring method perturbs profiles
*generally*, when the data say it perturbs them **if you choose a readout that scores a region
the model essentially never visits**.

### 3. Kirgis's own confound is comparatively benign

**ESTABLISHED, and it must not be buried.** His two arms were top-3 logprob weighting (≈ our
`label`) and the mean of ten sampled responses (≈ our `sampled`). They rank models at
**ρ = 0.818** over the six moral foundations, with a pairwise **R of 0.081** — the top tier
above, reached by an independent route.

**The specific methodological flaw that motivated this entire project is one his conclusions can
largely survive.** Saying so is the result of the audit, not a concession.

### 4. The methodological findings — the strongest material

These do not depend on R and are reproducible from the committed data.

- **ESTABLISHED — first-token label scoring silently fails on a large minority of models.** A
  faithful v1 implementation produced meaningless output on **6 of 16 models (38%)**, from two
  independent causes: SentencePiece tokenizers encode `"0"` as two tokens, so a single-token
  lookup finds nothing; and the first generated token is often not the answer (Mistral emits
  `'\n'` 116/116 times; Ministral emits `</s>`). Neither raised an error. Both produced plausible
  numbers. **The only signal was retained probability mass.**
- **ESTABLISHED — "free generation" hides a decision that can determine whether a model answers
  at all.** Ministral-8B answers **0% of items under greedy and ~50% under sampling**, on
  byte-identical prompts. Llama-3.2-1B refuses 109/116 under greedy.
- **ESTABLISHED — refusal leaks into the logprob readout.** Greedy non-answer rate and label
  retained mass couple at **ρ = −0.54** across 31 models. **Label scoring does not avoid the
  refusal confound — it hides it**, and renormalisation then manufactures a confident score from
  whatever digit mass remains. Any logprob study on safety-relevant content should report
  retained mass; mass also doubles as a generation-free refusal detector.
- **ESTABLISHED — a multi-readout design converts an untestable missing-data assumption into a
  measured one.** Because label scoring never requires the model to speak, we hold each model's
  probability answer to the very items it refused. The hypothesis *refusal means "extremely
  wrong"* is **true for one model and false for another**. Imputing the maximum moves a model's
  greedy mean by up to **+0.965** — the size of a choice usually made silently.
- **ESTABLISHED (from Kirgis's own committed data) — provider logprob APIs cannot be assumed
  well-formed.** grok-3-beta returned structurally malformed `top_logprobs` on **51 of 116
  responses (44%)**. His renormalisation accidentally rescues these; the formula printed in his
  paper, which does not renormalise, would not. **His code and his paper disagree.**

### 5. Scale — the strongest positive extension, and the thinnest evidence here

**SUPPORTED, marginal per ladder.** The individualizing-minus-binding gap increases with model
size on both complete ladders, after removing a compression confound that would otherwise have
manufactured a third of the effect:

| ladder | n | span | slope/decade (adjusted) | p | LOO keeps sign |
|---|---:|---:|---:|---:|---:|
| qwen | 8 | 145× | +0.3243 | 0.083 | 8/8 |
| llama | 4 | 71× | +0.2609 | 0.060 | 4/4 |

**Read this with its caveats, which are load-bearing.** Neither ladder is individually
significant at 0.05; only the pooled fit is, and pooling is the weaker design because models are
not exchangeable across families. Four of six families slope positive. The registered falsifier
required a flat-or-negative slope on *both* ladders, which passes by chance about a quarter of
the time. The standalone verdict in `results/derived/kirgis_pattern_audit_v2.md` still reads
**"SUGGESTIVE, not established, in either direction"** — only 15/30 models show the adjusted
gap, and it carries no interval.

---

## What we cannot claim

Short list; full treatment in `docs/LIMITATIONS.md`, which runs to 22 numbered entries.

- **That the design resolved R.** It did not, at either N.
- **That R is a property of the roster.** One model of 27 carries a third of the interaction.
- **That our arms are independent readouts.** `label` and `string_line` correlate at ρ = 0.964
  across models and r = 0.988 at item level — under a prompt that displays the digit→phrase
  mapping they are **the same measurement**. The design has three independent probability
  readouts, not four, and no fixed prompt escapes this. Found by us, stated by us.
- **That method effects generalise beyond this prompt.** One prompt was held fixed by design.
  Whether scoring method matters more than an arbitrary wording choice is **untested** and is the
  deepest gap in the project (`docs/THE_NEXT_EXPERIMENT.md`).
- **That published logprob work is broadly wrong.** One implementation, one roster, one prompt.
- **Anything about frontier models.** 31 open models ≤ 72.7B are not the frontier, and the
  distance is post-training as much as parameter count.
- **That Kirgis's conclusions are wrong.** We did not replicate his models, prompt, or capability
  range. We show his design carries a real risk, quantify it, find it modest for his specific
  choices, and independently support two of his four claims.

---

## The corrections record

`docs/CORRECTIONS.md` logs **21 corrections** — every claim withdrawn or reversed, and how each
was caught. This is kept deliberately, and not as penance: the project's thesis is that a
plausible-looking number can be an artifact of how it was measured, so a version of it that
quietly fixed its own measurement artifacts would be making the reviewer's argument for them.

The two most instructive:

- **C15** — our primary estimand contained a prompt-confounded arm for weeks, inflating R by
  2.70×, despite three documents stating it must be excluded. **Nothing in the codebase enforced
  a design decision that existed only in prose.** The error ran in our own favour.
- **C19** — the limitations document spent five days describing completed work as outstanding,
  contradicting the findings document and, for one item, its own section 12. Every check in the
  repo pointed at *numbers*; a stale status claim has no number to re-derive.

**Not one of the twenty-one was found by looking at a result and feeling that it seemed wrong.**
Measurement artifacts do not announce themselves, and the only reliable defence is a check
specified before the number exists.

Several tests exist because something slipped past their absence, and each closes the *class*
rather than the instance:

| test | guards | exists because |
|---|---|---|
| `test_headline_numbers.py` | every ρ quoted in prose, recomputed from the data | C18 — one guarded number, five stale ones beside it |
| `test_design_commitments.py` | prose design decisions are enforced in code, across all three R-computing scripts | C15, C17 |
| `test_determinism.py` | dataset rebuilds byte-identically under two `PYTHONHASHSEED` values | C10, C11 |
| `test_artifact_provenance.py` | no committed artifact blends the two harnesses | C12 |
| `test_doc_citations.py` | every cited path exists **at the directory given** | stale signposts, which is the mechanism behind C15 |
| `test_self_description.py` | the repo's claims **about itself** — correction count, tally coverage, test count — against the repo | C19, C21 — every other guard points at the data; none pointed here, and the count went stale three times in one session |

---

## Reproducing

Everything except the GPU inference and the Bayesian fit runs on a laptop from a clean
clone. That is verified on every push by `.github/workflows/tests.yml`, which installs from
`requirements.txt`, rebuilds the analysis dataset from `results/raw/`, and asserts the
rebuild is **byte-identical** to the committed one.

```bash
git clone https://github.com/Davvi1/moral-foundations-in-LLMs-Kirgis-Extension
cd moral-foundations-in-LLMs-Kirgis-Extension
python -m pip install -r requirements.txt      # Python 3.10+; 3.12 in CI
pytest                                          # 322 tests, ~5 min, no GPU
```

| file | what it is for | where it has to run |
|---|---|---|
| `requirements.txt` | analysis, figures, deck, tests | any laptop |
| `requirements-fit.txt` | the Bayesian variance ratio and the MCMC null | Linux + C++ toolchain |
| `requirements-inference.txt` | collecting `results/raw/` | Linux + NVIDIA GPU |

**`results/raw/` is committed** — 13 MB, 62 files, one CSV and one manifest per model. It was
gitignored until 2026-08-16 on the stated grounds of being "regenerable, too big for git",
and both halves were false: it is small, and it is *not* regenerable, because greedy decoding
is measurably non-deterministic across runs (`LIMITATIONS.md` §12). A fresh clone could not
run `build_analysis_data.py` at all. Each manifest records the interpreter, package versions,
GPU and pinned revision for that model; all 31 v2 models were collected on one identical
stack (Python 3.12.3 · vLLM 0.26.0 · transformers 5.14.1 · torch 2.11.0+cu130).

### Item file

```bash
python scripts/build_items.py
```

Stdlib only, Python 3.10+. Asserts n=116 and the foundation counts (Authority 17, Care 16,
Fairness 17, Liberty 17, Loyalty 16, Sanctity 17, Social Norms 16) and fails loudly rather than
emitting a bad questionnaire.

### Tests

```bash
pytest                      # 322 tests, ~5 min, no GPU needed
```

vLLM is Linux+GPU only, so the harness is exercised against a faithful fake of the vLLM API
(`tests/fake_vllm.py`) driven by **real tokenizers** over the **real 116 items**. The suite
covers the prompt invariant, tokenization claims, all six arm runners, the manifest contract,
checkpointing, VRAM planning, and the sequence-length budget — plus the claim guards above.

Three bugs were caught this way that would each have cost GPU time:

- the manifest crashed on `yaml`'s `datetime.date` *after* all arms had run, destroying a full
  model's inference on every model;
- `Qwen2.5-14B` (28.8 GiB in bf16) does not fit a 32 GiB card and would have OOM'd after a 28 GB
  download;
- the `--help` sweep was silently reverting `config/models.yaml` from 30 models to 20 on every
  run, because two scripts had no argparse and so *ran* instead of printing usage (C9).

### Analysis

```bash
python scripts/build_analysis_data.py --suffix _v2      # raw CSVs -> analysis_long_v2.csv
python scripts/validate_results.py --suffix _v2         # QA gate; exit 0 = analysable
python scripts/analyse_controls.py                      # nulls, pairwise R, leave-one-out
python scripts/report_exclusions.py                     # what was dropped, and with/without
python scripts/analyse_scale.py                         # P5 / P6, compression-adjusted
python scripts/analyse_variance_ratio.py --data results/derived/analysis_long_v2.csv
```

Only the last needs a Linux box with a working C++ toolchain (`requirements-fit.txt`) —
PyTensor falls back to pure Python otherwise and a small fit takes over ten minutes.
Everything else runs on a laptop.

**Two scripts cannot be run from a clone, by design rather than omission:**
`audit_greedy_determinism.py` compares the v1 and v2 collections and v1 was deleted from the
tree (`docs/V1_TO_V2.md`), so its committed output is the record; `reanalyse_kirgis.py` takes
`--kirgis-repo` and needs a local clone of Kirgis's repository, which is not vendored here.

### Figures and the deck

```bash
python scripts/make_figures.py --check     # re-derive 16 values, assert, draw nothing
python scripts/make_figures.py             # figures/ (titled) + figures/deck/ (untitled)
python scripts/make_deck.py                # -> MFT-in-LLMs-presentation.pptx, 20 slides
```

Every number in a figure is **derived at runtime** from `results/derived/` and asserted
against the committed artifacts before anything is drawn — `--check` does the assertions
alone. That is not ceremony: C18 and C21 are both cases of a number surviving in prose after
its basis moved, and the check caught a real one here, a reimplementation of the
compression-adjusted gap that gave +0.279 against the artifact's +0.324. The `.pptx` is
gitignored; the source and the figures it consumes are committed, so it cannot drift from
them unnoticed.

### Pre-flight, before anything expensive

```bash
source /workspace/env.sh && python scripts/preflight.py
```

Thirty seconds. Checks env vars, packages, GPU and `sm_120` kernels, config integrity, the
memory plan for every model, that every pinned revision resolves, and that a prompt renders
within the length budget. Exit 0 means safe to start.

### Inference environment

| | |
|---|---|
| image | `runpod/pytorch:1.0.2-cu1281-torch280-ubuntu2404` |
| GPU | RTX PRO 4500 Blackwell, 32 GB (sm_120) |
| Python | 3.12.3 · vLLM 0.26.0 · transformers 5.14.1 |

```bash
pip install "qstn[vllm]"
export VLLM_USE_FLASHINFER_SAMPLER=0   # REQUIRED on sm_120
```

**`VLLM_USE_FLASHINFER_SAMPLER=0` is not optional on Blackwell.** FlashInfer's
`top_k_top_p_sampling_from_logits` crashes vLLM engine initialisation on sm_120.

---

## Repository layout

```
config/prompt.yaml               the fixed prompt; two design decisions argued in full
config/models.yaml               the roster, with pinned revision SHAs
data/source/                     raw inputs, never edited — see PROVENANCE.md
data/mfv_116.csv                 116 items, QSTN format
data/mfv_116_meta.csv            foundation labels + Clifford's per-vignette human means

scripts/build_items.py           derives the two data files from source; self-verifying
scripts/run_experiment.py        the harness: six arms, checkpointed, manifest per model
scripts/build_analysis_data.py   raw CSVs -> analysis_long_v2.csv, with exclusions
scripts/validate_results.py      methodological QA gate; run before any analysis
scripts/analyse_variance_ratio.py  the primary estimand R
scripts/analyse_controls.py      permutation null, positive control, pairwise R, leave-one-out
scripts/report_exclusions.py     what was dropped, and R with and without

results/raw/                     one CSV + manifest per model, as collected
results/derived/                 analysis-ready outputs and every derived report

docs/ANALYSIS_PLAN.md            the plan, locked before any confirmatory data existed
docs/state.md                    living record — registered predictions, verbatim
docs/FINDINGS.md                 synthesis; claims with strength labels
docs/LIMITATIONS.md              everything constraining what may be claimed
docs/CORRECTIONS.md              every claim withdrawn or reversed, and how it was caught
docs/METHODOLOGY_REVIEW.md       flaw tracker, F1–F9, with resolution status
docs/METHODS_EXPLAINER.md        how each arm is actually computed
docs/V1_TO_V2.md                 why the harness was rebuilt
docs/THE_NEXT_EXPERIMENT.md      what the design analysis says a follow-up would need
docs/references.md               every citation verified by fetching the source
```

---

## Licence and provenance

Code MIT (see `LICENSE`). The vignettes are Clifford et al. (2015); the administered subset and
Kirgis's published responses have separate provenance and redistribution considerations — see
`data/source/PROVENANCE.md`. Every citation in `docs/references.md` was verified by fetching the
source rather than recalled.
