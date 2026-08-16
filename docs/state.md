# state.md

Living record. Sessions start without memory of prior ones — if a decision isn't written
here, it didn't happen. Update it when something is settled, not at the end.

## What this file is, after the 2026-08-11 prune

**This file's one irreplaceable job is holding the REGISTERED PREDICTIONS**, and their entire
value is that the git timestamp precedes the data. Everything under
*"Pre-specified before any results exist"* is therefore **verbatim and must stay that way** —
including the predictions that were falsified, which are the most useful ones in a write-up.

346 lines were removed: a ~360-line go/no-go session log whose conclusions live in
`references.md`, and a five-bullet limitations draft wholly superseded by `LIMITATIONS.md`.
Both are in git history. Nothing pre-specified was touched.

**The reason for pruning is not tidiness.** C15 — the worst error in this project, a
prompt-confounded arm inside the primary estimand that inflated it 2.70× — sat unnoticed
because the commitment to exclude it was buried in prose across three files. A 1,100-line
record where finding a specific commitment means reading past several hundred lines of resolved
session narrative is the same failure mode with a different surface.

Where each kind of thing now lives:

| | |
|---|---|
| registered predictions, decision rules, thresholds | **here**, verbatim |
| what a source actually says | `references.md` |
| what we got wrong and how it was caught | `CORRECTIONS.md` |
| what constrains the claims | `LIMITATIONS.md` |
| what we found | `FINDINGS.md` |
| why v1 became v2 | `V1_TO_V2.md` |

---

## Status

**Phase: ANALYSIS COMPLETE, 2026-08-09.** All collection and all pod-bound analysis are done.
What remains is the write-up.

- **v2 harness, N = 31 models** (32 pinned; Mistral-Large deliberately skipped — the
  pre-committed criterion in the plan was met, so it would not change the conclusion).
  6 conditions, 21,576 analysis rows. Primary results in `FINDINGS.md`.
- **All pod work finished.** Variance ratio at N=31, 35-fit seed audit, 700-fit MCMC null.
  Both pods stopped and verified `EXITED`. Total spend $20.04 of $60 credit ($39.96 remaining).
- **Prediction scorecard:** P1′ P2 P3 P4′ P5 P6 supported (P2 and P3 with caveats),
  **P4r and P7 falsified**. See "OUTCOMES" below.
- **22 corrections logged** in `CORRECTIONS.md`, three of them reproducibility defects found
  after the fact (C10 non-deterministic tie-break, C11 randomised MCMC seed, C12 a v2 run
  overwriting a v1 artifact). All now guarded by `tests/test_determinism.py` and
  `tests/test_artifact_provenance.py`. **331 tests pass.**
- **Still open, deliberately:** F5 (prompt as a designed factor) and a scale-augmented variance
  model. Both named in `METHODOLOGY_REVIEW.md`.

> **CORRECTED 2026-08-15 (C19).** This block said "12 corrections", "300 tests", and listed
> **the family random effect as still open** — it was fitted on 2026-08-10
> (`variance_ratio_v2_family.csv`, −2% to +5%, no verdict change). That made this the third
> document asserting undone work that the artifacts show was done, after `LIMITATIONS.md` §13
> and the `METHODOLOGY_REVIEW.md` outstanding list.
>
> **The primary is also N = 30, not the N = 31 named above**: `variance_ratio_v2.csv` was refit
> on 2026-08-11 with cloze excluded (C15) and SmolLM2 dropped (`LIMITATIONS.md` §22). The
> 700-fit MCMC null remains at N = 31 *and on a six-arm basket* (C17), disclosed rather than
> refit — a null collapses to ~0 under any basket.
>
> Nothing in the **registered predictions** below was touched; this is the status block only.

<details>
<summary>Historical status from the pre-flight phase (2026-08-07)</summary>

**Phase:** pre-flight. No code written. **Go/no-go check run 2026-08-07 — result: GO.**
See "Go / no-go findings" below. All three blocking questions answered; the instrument,
the prompt, the human baseline, and Kirgis's per-item responses are all in hand.

**Analysis plan is LOCKED as of 2026-08-07.** The variance-ratio cutoff is set at
0.25 / 1.0 with a middle band — see the primary-criterion section. No blanks remain.
Nothing about the decision rule may change once results exist.

**Three prior claims were falsified by the check**, all flagged as CORRECTION in the
findings section: (1) Kirgis's code *does* renormalise, and disagrees with his own printed
formula; (2) scoring method is *not* perfectly collinear with provider — OpenAI straddles
both arms; (3) the human baseline is not nationally representative.
**All three are now written into `references.md` and `CLAUDE.md` (2026-08-07).**

**Environment, established 2026-08-07:** no local GPU (`nvidia-smi` absent), local Python
3.10, QSTN needs ≥3.12, vLLM is Linux-only. All inference runs on rented Linux; the laptop
is analysis-only. Model roster verified — all 13 HF repo IDs resolve, but 6 are gated with
`manual` approval (3× Llama, 2× Gemma). All-open fallback roster of 9 exists if approvals
stall: Qwen2.5-{0.5,1.5,3,7,14}B-Instruct, Mistral-7B-Instruct-v0.3, Phi-3-mini-4k-instruct,
OLMo-2-1124-7B-Instruct. Prefer OLMo-2 over Qwen3-8B for the open slot — Qwen3 is a hybrid
reasoning model, and reasoning models diverge between free generation and label scoring by
construction, which manufactures the interaction being measured.

**Working plan:** `~/.claude/plans/okay-what-should-be-gleaming-possum.md`, 9 steps.
Steps 1–3 complete as of 2026-08-07.

**→ READ `FINDINGS.md` FIRST when picking this up.** It carries the audit of what is and is not
verified, the pod cheat-sheet, and the ordered sequence for the next session. The single most
important item there: **QSTN has never actually been run.** Everything on the pod so far used
raw vLLM. QSTN pins only `vllm>=0.12` and we installed 0.26.0, so its API compatibility is
untested and is the first thing to check — a 60-second test that decides whether the harness
plan survives.

</details>

### Pod, as built (Step 3, 2026-08-07)

RunPod EU-RO-1 · RTX PRO 4500 Blackwell 32 GB · $0.72/hr · 200 GB network volume `MFT_LLMs`
mounted at `/workspace` · image `runpod/pytorch:1.0.2-cu1281-torch280-ubuntu2404` ·
SSH `root@213.173.102.27 -p 38177 -i ~/.ssh/id_ed25519_runpod` (dedicated passphrase-free key;
David's personal `id_ed25519` has a passphrase and must not be used).

Installed: Python 3.12.3 (image ships it — `uv` not needed), **vllm 0.26.0**, transformers 5.14.1,
qstn. Verified `sm_120` in `torch.cuda.get_arch_list()` and a bf16 matmul on-device.

**Filesystem split, learned the hard way.** `/workspace` is FUSE/MooseFS: 1.0 GB/s bulk but
crushingly slow on many small files. Container disk `/` is overlay at 3.8 GB/s. A venv is tens
of thousands of tiny files, so **venv goes on container disk** (`/root/venv`); model weights are
few huge files, so **HF cache goes on the volume** (`/workspace/hf-cache`). First attempt put the
venv on the volume and had to be abandoned.

Container disk is **wiped on pod stop**. Recovery is `bash /workspace/bootstrap.sh` — rebuilds
the venv offline from `/workspace/pip-cache` (5.9 GB of wheels preserved on the volume). Then
`source /workspace/env.sh`. Weights in `/workspace/hf-cache` persist and never need re-downloading.

**Blackwell quirk, recorded in `/workspace/env.sh`:** `VLLM_USE_FLASHINFER_SAMPLER=0` is
REQUIRED. FlashInfer's `top_k_top_p_sampling_from_logits` crashes engine init on sm_120. Without
this, vLLM will not start at all on this card.

**`HF_TOKEN` is still broken.** RunPod silently dropped `{{ RUNPOD_SECRET_HF-read-token }}` —
hyphens break its template substitution. Fix: rename the secret to `HF_READ_TOKEN` and set
`HF_TOKEN = {{ RUNPOD_SECRET_HF_READ_TOKEN }}`. Only blocks the gated repos (3× Llama, 2× Gemma),
so it must be fixed before Step 6 but blocks nothing earlier.

### B4 — smoke test PASSED, 2026-08-07. Harness validated on real hardware.

`Qwen2.5-1.5B-Instruct`, 10 items, all four conditions, k=3. 60 rows, **0 parse failures,
0 refusals, 0 scan-parses**, 118 s wall (nearly all of it model load). Results and manifest
in `results/smoke/`. Pre-flight exited 0 and correctly flagged Qwen2.5-14B as not fitting
and OLMo-2-13B as tight — the local prediction reproduced exactly on the card.

**THE INVARIANT HOLDS.** Prompt hashes per item = {1}: every condition received a
byte-identical prompt. This is now demonstrated on real hardware, not asserted.

| condition | mean | min | max | logprob mass |
|---|---|---|---|---|
| label | 3.508 | 3.19 | 3.79 | 0.9973 |
| string | 2.620 | 2.36 | 2.81 | 0.1495 |
| greedy | 3.800 | 3.00 | 4.00 | — |
| sampled | 3.600 | 2.00 | 4.00 | — |

**The four methods disagree, and not by a little.** On the same ten items with the same
prompt, string scoring sits ~0.9 scale points below label scoring, and greedy sits above
both. If that survives to n=20 models and 116 items it is the headline. **Do not read
anything into it yet** — one model, ten items, no error bars, and the ordering could easily
be an artifact of this model or these items.

**One number to watch:** string scoring retains only **0.15** probability mass versus 0.997
for label. That is the "options are visible in the prompt" limitation from
`config/prompt.yaml` showing up quantitatively — the model is being asked to score a
continuation it was implicitly steered away from. It does not invalidate the condition (the
comparison across the five options is still internal and consistent) but it belongs in the
write-up, and the mass column is what makes it visible.

Token boundary checks came back clean, so the full-sequence alignment in string scoring
works on this tokenizer. Re-check per family.

Environment as run: vllm 0.26.0, transformers 5.14.1, torch 2.11.0+cu130, Python 3.12.3,
RTX PRO 4500 Blackwell, bf16, max_model_len 1024, enforce_eager, gpu_util 0.85.

### B1 — Kirgis reanalysis, 2026-08-07. EXPLORATORY. **My prediction was wrong.**

Full report `results/derived/kirgis_reanalysis.md`, per-row data `kirgis_rescored.csv`,
reproducible via `scripts/reanalyse_kirgis.py`. Analysis of existing public data — **label it
exploratory in the write-up**, it is not part of the pre-specified design.

**What I predicted and got wrong.** I expected the argmax-degeneracy (digit filtering leaving
one survivor) to be the headline. It is **5.6%** of responses (39/696), and it changes nothing:
Spearman between his code's model ranking and plain argmax is **1.00**. Fallback rate is **0%**,
not the unreported contamination I suspected. Both of my go/no-go hypotheses about his estimator
were, in effect, non-findings. Say so plainly rather than dressing them up.

**What is actually there, and it is better.** `grok-3-beta` — **51 of 116 responses (44%)** —
came back from the xAI API with **structurally malformed `top_logprobs`**: two entries instead
of three, summing to ~0 probability, while the emitted token's own `logprob` reports p = 1.0.
The two fields contradict each other. Every OpenAI model and grok-2 return clean data
(top_mass ≈ 1.000); grok-3-beta's mean top_mass is 0.5603.

Three consequences, ascending:
1. Those 51 scores are computed from corrupted probability data.
2. **His renormalisation accidentally rescues them.** Near-zero over near-zero recovers the
   argmax, which equals the emitted (correct) answer, so his published numbers look fine. His
   *printed formula* would not: grok-3's mean collapses 1.98 → 1.20 and it falls from rank 4 to
   rank 6 of 6. The paper-vs-code discrepancy is therefore **consequential, but only via this
   one model** — mean absolute difference is 0.13 overall and ~0.000 for four of six models.
3. **For those items "top-3 logprob weighting" is not what happened — argmax is.** Inside the
   arm he treats as one homogeneous method, one of six models is effectively scored by a
   different method for nearly half its items.

Point 3 is the one that matters here: **direct evidence from his own committed data that
scoring method was not uniform even within the logprob arm.** It strengthens the audit framing
and it generalises — provider logprob APIs cannot be assumed well-formed, and a study reading
them without an integrity check inherits their bugs. **Add a top_mass integrity check to our own
harness output.**

Not computable from his data: renormalising over all five options. The API returned only the
top 3 of the vocabulary, so logprobs for options outside it do not exist. His estimator cannot
be repaired post hoc, only re-collected — itself part of the finding.

### Tokenization probe results (Qwen2.5-0.5B-Instruct) — day-one risk #1 DISCHARGED

Full output: `results/probe_qwen2.5-0.5b.log`. Re-run per tokenizer family before trusting label
scores on a new model — these results are Qwen-specific.

- **Bare vs space-prefixed digits ARE different tokens.** `"0"` → `[15]`, `" 0"` → `[220, 15]`.
  The bare digit is a single token; the spaced form is two.
- **The model emits the BARE digit.** Greedy first token was `id=17` = `'2'`. So label scoring
  reads bare digit IDs 15–19. Prompt ends `'im_start|>assistant\n'`, i.e. no trailing space —
  which is why the bare form wins. This is exactly the hazard in arXiv:2509.15020, resolved
  empirically rather than assumed.
- **First-token collision CONFIRMED.** Options 0 and 1 both begin with token `2623` (`'Not'`).
  A single-position readout cannot separate "Not at all wrong" from "Not too wrong".
  **The design claim in `config/prompt.yaml` is verified: string scoring must be a full-sequence
  log-likelihood.**
- **Option token lengths are unequal** — {0:4, 1:3, 2:3, 3:2, 4:3} — so length normalisation is a
  genuine choice, not a default. Still to be decided in Step 5.
- All five options appeared in the top-20 with 0.9990 of the probability mass.

**Honest caveat that cuts against the project's framing, found in the probe:** on this item the
renormalised and unnormalised expectations differed by only **0.0018** (1.7794 vs 1.7776),
because top-20 captures 99.9% of the mass. **Kirgis used top-3, not top-20**, so his denominator
is much smaller and his gap will be larger — but this is a signal that the *renormalisation*
half of the audit may be a small effect. The *degeneracy* half (argmax collapse when only one
digit survives the top-3 filter) is likely the bigger finding. Step 4 measures which. Do not
pre-announce the renormalisation effect as large.

---

## Settled

- **Project:** replicate Kirgis's MFV administration on open-weight models; manipulate
  scoring method as a within-model treatment. Ask whether foundation profiles and model
  rankings are stable across methods.
- **Part 2 of the original plan (post-training a model toward global moral foundations) is
  dropped.** Not feasible in two days, and the fine-tuning stack is a genuine gap.
  Part 1 is a complete deliverable.
- **Terminology:** label scoring / string scoring / free generation (greedy) / free
  generation (sampled). Not "readout method."
- **Design template:** Alzahrani et al. arXiv:2402.01781. Same manipulation, same
  rank-agreement logic, new domain.
- **Novelty claim, exact wording (revised 2026-08-07 after QSTN check):** method effects
  on value questionnaires are established (QSTN, arXiv:2512.08646; Wang et al. ACL
  Findings 2024). This project contributes (a) the first audit of Kirgis's specific
  characterization claims against his own scoring confound, and (b) the profile-stability
  estimand: not "which method aligns with humans" (QSTN's question, a simulation
  criterion) but "is the model's measured profile and the model ranking stable across
  methods" (a measurement criterion). Nothing stronger than this.
- **Scope of the Kirgis replication:** Figures 2 and 3 yes. Figure 4 (PCA) optional.
  Figure 5 (FrameAxis on justifications) dropped — half a day minimum, and it is undefined
  for the two scoring conditions that generate no text.
- **Analysis target is an interaction, not a main effect.** A uniform severity shift across
  all models is a calibration difference and threatens nothing. What matters is
  model × scoring-method and foundation × scoring-method.
- **13th model slot = `allenai/OLMo-2-1124-7B-Instruct`, not `Qwen3-8B`** (decided 2026-08-07,
  verified against the Qwen3-8B model card, not recall). The card states "By default, Qwen3
  has thinking capabilities enabled" and emits `<think>...</think>` unless
  `enable_thinking=False`. Thinking-by-default changes free generation while being invisible
  to label scoring — that manufactures the foundation × method interaction we are trying to
  measure. OLMo-2 is non-reasoning and a different training lineage, so it adds real diversity.
- **Item files built 2026-08-07** — `data/mfv_116.csv` (QSTN format) and `data/mfv_116_meta.csv`
  (foundation + Clifford human means), derived by `scripts/build_items.py` from a pinned copy
  of Kirgis's CSV in `data/source/` with `data/source/PROVENANCE.md`. Build is self-verifying: it asserts
  n=116 and the foundation counts and fails loudly rather than propagating a bad questionnaire.
- **REVERSED 2026-08-07: the harness is built on raw vLLM, not QSTN.** The earlier
  recommendation ("build on QSTN, hand-write only string scoring") was made when QSTN looked
  like it covered three of four conditions off the shelf. Our own subsequent decisions hollowed
  that out:
  - Decision 2 in `config/prompt.yaml` **overrides QSTN's prompt construction entirely**,
    because QSTN varies the system prompt by response-generation method — which would
    reintroduce the exact confound under audit. Prompt building was its main contribution.
  - Its batching wrapper is thin; `vLLM.generate` already batches.
  - Its sampled path reads `outputs[0]`, so `n=k` is ignored regardless.
  - What remained was a parser and a logprob space-stripper — roughly sixty lines.

  Against that, **raw vLLM is verified working on the target GPU** (the tokenization probe ran
  end-to-end); QSTN end-to-end never has been. Building on vLLM removes a whole failure class
  from B4. Cost: we lose the "same framework as the closest prior work" argument, which was
  presentational rather than methodological. Harness is `scripts/conditions.py` +
  `scripts/run_experiment.py`. QSTN remains installed and can be swapped back in for parsing.

- **Prompt fixed in `config/prompt.yaml`** — one user template, one system prompt, identical
  across all four conditions. Two contestable decisions are recorded in that file and need
  sign-off: (1) Kirgis's "respond only with the code ... by itself" instruction is **dropped**,
  because it is not neutral between label and string scoring; (2) QSTN's per-method system
  prompts are **overridden with a single fixed one**, because QSTN varies the system prompt by
  response-generation method and using its defaults would reintroduce, inside our own harness,
  exactly the confound we are auditing Kirgis for. Cost of (2): free generation runs without
  JSON scaffolding, so parse-failure rates will be higher — measurable and reported, which is
  the right trade against an unmeasurable prompt confound.

## Models

**SETTLED 2026-08-07 after the B2 design simulation. Roster is `config/models.yaml`, N = 20
across 10 families, every revision SHA pinned.** Generated by `scripts/build_model_roster.py`;
all 20 IDs verified to resolve against the HF API on 2026-08-07.

Instruction-tuned only, ≤14B, **non-reasoning**. Base models are a separate question and
adding them is scope creep. Reasoning models are excluded on design grounds, not convenience:
thinking-by-default alters free generation while being invisible to label scoring, which
manufactures the very interaction being measured.

| family | n | models |
|---|---|---|
| qwen | 5 | Qwen2.5 0.5B / 1.5B / 3B / 7B / 14B-Instruct |
| llama | 3 | Llama-3.2-1B / 3.2-3B / 3.1-8B-Instruct *(gated)* |
| gemma | 2 | gemma-2-2b-it, gemma-2-9b-it *(gated)* |
| mistral | 2 | Mistral-7B-Instruct-v0.3, Ministral-8B-Instruct-2410 |
| phi | 2 | Phi-3-mini-4k-instruct, Phi-4-mini-instruct |
| olmo | 2 | OLMo-2-1124-7B / 13B-Instruct |
| smollm, granite, internlm, yi | 1 each | SmolLM2-1.7B, granite-3.1-8b, internlm2_5-7b-chat, Yi-1.5-9B-Chat |

**Why family diversity rather than more sizes.** The design simulation treats models as
exchangeable draws. Five sizes of Qwen2.5 share pretraining data and post-training recipe and
are *not* independent, so effective N sits below nominal N when one family dominates. Ten
families at N=20 buys more precision than four families at N=25. Qwen and Llama keep a size
gradient because Kirgis's fourth claim is about capability, which needs within-family scale
variation to address at all.

**Open-only fallback** if gate approvals fail: drop the 5 gated models, add Qwen2-7B-Instruct,
Phi-3.5-mini-instruct, zephyr-7b-beta, Falcon3-7B-Instruct → N = 19, zero gate risk. Also in
`config/models.yaml`.

**Weights total ~240 GB in bf16, against a 200 GB volume — so they cannot all be resident.**
Run as download → four conditions (minutes per model) → delete → next. The volume is not the
binding constraint; GPU-hours and download time are.

**Revisions are pinned and must not be regenerated after confirmatory data exists** — that
would silently change what the run manifests refer to. HF repo IDs are moving targets; without
pinning, the study is not reproducible even by its own author.

Superseded: the earlier "core eight + extension to 13" plan, and its rationale from the
Spearman critical value. B2 showed the binding constraint is the variance-ratio posterior, not
the rank statistic — and that N=13 misclassifies a genuinely degraded R about once in four.

---

## Pre-specified before any results exist

### Primary criterion — variance ratio

Fit item-level scores per foundation, with crossed random effects:

    s_mir = mu + gamma_r + u_m + w_mr + v_i + e_mir

    gamma_r  fixed effect of scoring method   (calibration shift — uninteresting)
    u_m      random model intercept            -> sigma2_model
    w_mr     random model x method             -> sigma2_model_x_method
    v_i      random item intercept             -> sigma2_item

Primary statistic, per foundation:

    R_f = sigma2_model_x_method / sigma2_model

Interpretation: R is how large the method-induced perturbation to a model's position is,
relative to how much models actually differ from one another. Kirgis's between-model and
between-provider claims presuppose R is small. If R approaches or exceeds 1, the method
perturbs a model's position as much as models differ, and those comparisons are not
interpretable regardless of what any rank correlation says.

**Mandatory model amendment (caught in review):** the four methods have structurally
different error variances — label scoring is a deterministic expectation, greedy is
discretized to integers, sampled generation carries Monte Carlo error of order 1/sqrt(k).
A single residual variance will misattribute this into sigma2_model_x_method and inflate
R mechanically, biasing toward the exciting result. Fit method-specific residual
variances e_mir ~ N(0, sigma2_r). Report R with and without this correction.

Preferred estimation: Bayesian (`bambi` / `pymc`), giving a posterior on R_f rather than a
point estimate, with the credible interval compared against the cutoff; heteroscedastic
residuals are a one-line change there. Crossed random effects are awkward in
`statsmodels`; if going frequentist, use `pymer4` or R via `rpy2`.

**Cutoff — SET 2026-08-07, before any model was downloaded. analysis plan locked.**

    R_f < 0.25          -> between-model comparisons robust to scoring method
    0.25 <= R_f <= 1.0  -> degraded; report with explicit caution, rankings not
                           to be trusted on their own
    R_f > 1.0           -> between-model comparisons not interpretable

Reasoning, one line: *R is a ratio of variances, so interpret it on the SD scale — R = 0.25
means the method moves a model half as far as models differ from each other (sqrt(0.25) = 0.5),
and R = 1 means the perturbation equals the differences being compared. The middle band exists
so that a single number does not carry the whole argument.*

**Note a slip in the earlier draft of this section, since it changes the defence:** it read
"R < 0.25 means method noise is a quarter the size of model signal." That is wrong — R is a
variance ratio, so R = 0.25 is a *quarter the variance* and therefore *half the SD*. The
0.25 line is a weaker claim than the old wording implied. Stated correctly above.

The decision rule is evaluated against the posterior credible interval on R_f, not a point
estimate. An interval straddling a band boundary is reported as straddling it, not rounded
to the nearer verdict.

**AMENDMENT 2026-08-07, after the B2 design simulation and BEFORE any confirmatory data.**
Full results: `results/derived/design_simulation.md`, reproducible via
`scripts/design_simulation.py`, calibrated to Kirgis's own observed variance components.

1. **A fourth verdict is added: `indeterminate`.** If the 95% credible interval on R_f
   straddles a band boundary, that is the reported outcome. The simulation shows no feasible
   N resolves an R sitting near 0.25 or 1.0 — this is inherent to a hard-threshold rule, not
   a power problem, so forcing a three-way call would manufacture false precision.
2. **Target roster size raised from 13 to N ≈ 20.** Interior-band classification accuracy at
   the worst simulated value: N=8 → 0.64, N=13 → 0.76, N=20 → 0.86, N=30 → 0.94. N=13
   misclassifies a genuinely "degraded" R ≈ 0.5 about once in four. Models are all ≤14B and
   weights need not be held simultaneously (download → run four conditions in minutes →
   delete), so the 200 GB volume is not the binding constraint; the cost is GPU-hours.
   **If time forces a cut, N=13 remains usable only with interval widths reported honestly
   and the indeterminate verdict used. N=8 must not carry the primary claim.**
3. **Correction to an earlier claim of mine.** I estimated analytically that the 95% interval
   would span about ×/÷2.5 at N=13. The simulation gives a multiplicative width of **~12×**
   at N=13, R=0.5. The back-of-envelope was optimistic and must not be quoted.
4. **Bayesian estimation is now required, not preferred.** The moment estimator returns
   σ̂²_model ≤ 0 — leaving R undefined — on up to 7.4% of replicates at N=8. A constrained
   posterior cannot do that.
5. **Multiplicity across the 7 fitted levels is resolved:** report all seven intervals (six
   foundations plus the non-moral control); the
   headline claim is stated at the foundation level, not aggregated into a single verdict.
   No correction is applied because no null-hypothesis test is being performed — but the
   seven verdicts are reported together, never selectively.

Calibration values used (medians across foundations of Kirgis's data): σ²_model = 0.070
(SD 0.264), σ²_item = 0.426, σ²_resid = 0.150.

### Exclusion rules — FIXED 2026-08-08, after data collection, BEFORE any variance ratio

Data collection finished first, and the QA pass exposed failures that make some cells
unanalysable. The threshold below was chosen **by David, from a menu of options with their
consequences shown, at a point where no variance ratio had been computed.** Verifiable in git:
the tag containing these rules precedes the existence of any analysis script.

**This is not a preregistered threshold** — it was set after seeing parse rates. It is
materially stronger than choosing one after seeing which value yields a publishable answer,
and materially weaker than fixing it in advance. Say exactly that; claim nothing more.

1. **Parse-success threshold = 0.50.** A model × condition × foundation cell is excluded from
   the primary analysis if fewer than half its items produced a usable answer. Applies to the
   free-generation conditions only — label and string scoring cannot parse-fail, since they
   read a distribution rather than parsing text.
2. **Everything is reported with and without the exclusions.** The excluded cells are listed
   in a table with their rates and reasons.
3. **internlm2_5-7b-chat's string condition is structurally missing**, not low-scoring:
   116/116 rows failed the token-boundary alignment check, so those log-likelihoods do not
   mean anything. The model is retained; its other three conditions are valid.
4. **`scan`-parsed rows are reported separately** and the primary analysis is repeated without
   them. A digit recovered from prose is a known error class — it is what mis-scored Kirgis's
   grok-3 responses — and must not be silently pooled with digits the model emitted as its
   answer.
5. **Achieved N is reported alongside its simulated classification accuracy**, not the headline
   N=20. Exclusions unbalance the design, and `results/derived/design_simulation.csv` says what
   any given N costs.

### Failure types are separated, not pooled — FIXED 2026-08-08

`parse_failed` conflates three phenomena with different meanings. They are split before
analysis, using the stored `raw_output`:

| flag | meaning | example |
|---|---|---|
| `empty_output` | model emitted nothing; EOS was the argmax token | Ministral-8B greedy: `''`, 116/116 |
| `refusal` | model declined in words | Llama-3.2-1B greedy: `"I can't answer this question."`, 108/116 |
| `unparseable` | model wrote text but no digit could be recovered | prose with no rating |

**Refusal is a value-laden act and is expected to correlate with foundation** — it is the
confound this design predicted. **Empty output is a decoding artifact and is not.** Reporting
"Ministral refuses everything" would be wrong: it never refuses, it never speaks. Its prompt
is well-formed by Mistral's own chat template, and it answers roughly half the time under
sampling — so the greedy silence is about decoding, not morality.

### Trial structure — why three conditions have one observation and one has ten

Label, string and greedy are **deterministic**: repeating them returns identical values, so
replication adds no information. Label and string read the probability distribution rather
than sampling from it; greedy takes the argmax at every step. Sampled is the only stochastic
condition, hence k=10, which also supplies the Monte-Carlo error term the variance model needs.
This matches Kirgis's structure exactly — one query for the logprob arm, ten for the sampled arm.

**Assumption, not verified:** greedy is deterministic in principle, but GPU floating-point
reduction order can vary with batch composition, so bit-identical output across differently
batched runs is not guaranteed. Every condition here ran as a single consistent batch. If a
pod is restarted for any other reason, re-run greedy for two or three models and diff the
output (~5 min). Until then this is stated as an assumption in the limitations.

### OUTCOMES — resolved 2026-08-09, after the v2 collection

Scored against the predictions as written below. Two failed outright; one passed for a reason
that undercuts its own interpretation. Nothing here was rewritten to fit the result — the
originals stand unedited above, with amendments dated where a prediction proved unevaluable.

| # | outcome | evidence |
|---|---|---|
| P1′ | **SUPPORTED** | `string_line` mass > `string_bare` on 31/31 models (0.626 vs 0.003) |
| P2 | **SUPPORTED, but weaker than it looks** | ρ(label, line) 0.964 vs ρ(label, bare) 0.415 *(six-foundation basis; 0.969/0.451 was the seven-pooled N=31 basis — C18)*. **However** line and label are near-identical measurements (item-level r = 0.988) because the prompt displays the digit→phrase mapping — so agreement "recovering" is partly definitional. See FINDINGS §3. |
| P3 | **SUPPORTED but thin** | ρ = −0.195 (n=20), carried by Mistral-7B (moved 0.369; high-mass models ~0.013). Report the mechanism, not the correlation. |
| P4′ | **SUPPORTED** | cloze mass > bare on 23/31 models |
| P4r | **FALSIFIED** | ρ(cloze, bare) 0.269 < ρ(cloze, label) 0.404 — predicted the reverse |
| P5 | **SUPPORTED** | qwen +0.3243 (LOO 8/8), llama +0.2609 (LOO 4/4), compression-adjusted. Raw slopes were ~⅓ confound: compression `b` runs 0.113→1.059 on the qwen ladder, slope on log-params +0.4004 (p<0.001). |
| P6 | **SUPPORTED** | all six families negative; both ladders LOO-stable. Implies R is partly a small-model artifact — qualifies our own headline. |
| P7 | **FALSIFIED** | predicted ≥2 foundations escape `indeterminate` at N≈30. **None did.** All seven still indeterminate at N=31. |

**What P7's failure means, stated rather than buried:** going 20 → 31 models resolved nothing.
The honest conclusion is the one P7 itself named in advance — this estimand is not resolvable
at any N a student project can reach, and the contribution becomes the design analysis.

**A Phase-1 finding that did not replicate.** C2 recorded that pooling the residual variance
*deflates* R by 4–16% at N=20, itself a reversal of the analysis plan's prediction. At N=31 it
*inflates* R by +0.3% to +6.6% in six of the seven levels fitted (six foundations plus the
non-moral control). The direction is not stable across
samples and the magnitude is small either way.

---

### F5 PROMPT-FACTOR PREDICTIONS — FIXED 2026-08-10, BEFORE any P01-P11 data exists

> **DEFERRED 2026-08-10, same day, by decision.** The collection was built and validated but not
> run. F5 stopped being an extension of this experiment and became a second one the moment the
> design grew a second instrument — see `THE_NEXT_EXPERIMENT.md`. These predictions stand as
> registered and carry over unchanged; the git timestamp is what makes them pre-registered, and
> deferring collection does not weaken that. Two anchors were refined the same day after the
> full texts (not just the abstracts) were read; both refinements are marked inline below and
> both make the prediction *harder* to satisfy, not easier.

Twelve prompt variants (P00 base + 11) x 5 conditions x 31 models. Analysis is **rank
correlation, not variance decomposition** — see `config/prompt.yaml` for why (it is the P7
mistake, and both comparison papers use rank/consistency metrics).

Each prediction is anchored to a **published number**, so a failure is informative rather than
just a shrug. Verifiable in git: this commit precedes every `*_f5.csv`.

- **F5-1 (transfer of the "artifact" claim).** arXiv:2509.01790 finds prompt sensitivity is
  "largely an artifact of heuristic evaluation" — on capability benchmarks, heuristic parsing
  gave mean cross-prompt ranking ρ̄ = 0.30 against 0.95 for LLM-as-judge. Transferred here:
  *(Anchor refined 2026-08-10 after reading Table 1 rather than the abstract — the abstract
  contains no numbers. 0.30 is ARC-Challenge, open-source models only. Their heuristic arm spans
  **ρ̄ = 0.15–0.59** across benchmarks: 0.15 GPQA Diamond, 0.30 ARC-C, 0.42 OpenbookQA, 0.59
  NarrativeQA. The anchor is that RANGE, not the point.)*
  **the parsing arms (greedy, sampled) will show LOWER mean cross-prompt rank correlation than
  the logprob arms (label, string_line, string_bare).**
  *Falsifier:* logprob arms equal or less prompt-stable than parsing arms. That would mean the
  artifact claim does not transfer from capability to values instruments, which is the more
  interesting outcome and the reason this is registered.

- **F5-2 (option order is the worst perturbation).** arXiv:2607.05554 reports option shuffling
  at 0.407 consistency against 0.9+ for semantic perturbations. Here: **P03_reversed and
  P04_shuffled will show the lowest cross-prompt rank agreement with P00 of any variant**,
  under every condition.
  *Falsifier:* a paraphrase or register variant (P01, P02, P08, P09) disrupts ranking more than
  either order variant.

- **F5-3 (values are more prompt-sensitive than capability).** arXiv:2607.05554 finds
  subjective instruments at 0.787 mean consistency against 0.849 objective. Here: **mean
  cross-prompt rank correlation on the MFV will be lower than the 0.95 arXiv:2509.01790
  reports for its most stable readout**, i.e. a values instrument is harder to measure stably
  than a capability benchmark.
  *Falsifier:* MFV cross-prompt stability at or above 0.95.
  *(Anchor CORRECTED 2026-08-10, and the original was comparing the wrong things. 0.95 is their
  **LLM-as-a-Judge** arm — a readout we do not have and arguably cannot have, since there is no
  ground truth for "how wrong is this vignette" for a judge to be right about. It also includes
  proprietary models; open-source only is 0.92, and their highest anywhere is 0.96 on MATH. The
  defensible comparison for us is against their **heuristic range, 0.15–0.59**, since that is
  the arm whose mechanism we share. Restated: **mean cross-prompt rank correlation on the MFV,
  under the parsing arms, will fall at or below the top of their heuristic range (0.59).** The
  old 0.95 falsifier is retained only as a weak upper check.)*

- **F5-4 (the headline comparison, and the one the project exists for).** **Cross-PROMPT rank
  correlation, averaged over conditions, will be HIGHER than cross-METHOD rank correlation
  averaged over prompts.** I.e. changing the scoring method moves the model ranking more than
  changing the prompt wording does. Reference points already in hand: ρ(label, sampled) = 0.879
  and ρ(label, string_bare) = 0.451 at fixed prompt.
  *Falsifier — and it is a real possibility, not a formality:* prompt perturbation moves the
  ranking as much as or more than method choice. **That would substantially qualify this
  project's thesis**, reframing scoring method as one facet of a broader prompt-sensitivity
  problem rather than a distinct measurement hazard. It would be reported as such.

- **F5-5 (Decision 1 was defensible).** `config/prompt.yaml` Decision 1 dropped Kirgis's
  "respond only with the code" instruction on the argument that it steers toward digits and so
  disfavours the string arms. **P05_kirgis_instruction will therefore raise label retained mass
  and LOWER string_bare retained mass relative to P00.**
  *Falsifier:* no differential effect on the two arms' mass, which would mean Decision 1 was
  solving a problem that did not exist.

- **F5-6 (free reproducibility check).** P00 is the original prompt re-run in a later session
  on different hardware. **The five fixed-prompt conditions will reproduce the v2 collection**:
  identical scores for the deterministic arms (label, string_line, string_bare, greedy) and
  within Monte-Carlo error for sampled.
  *Falsifier:* systematic drift, which would settle the greedy-determinism question left open
  in `LIMITATIONS.md` §12 — in the unwelcome direction.

  > **AMENDED 2026-08-10, BEFORE collection, because this prediction is ALREADY FALSIFIED by
  > data that existed when I registered it.** I did not look. The v1 and v2 collections ran
  > greedy on the same 20 models with a byte-identical prompt, the same GPU model and identical
  > library versions; `scripts/audit_greedy_determinism.py` shows raw text differs on **10.56%**
  > of cells and the parsed score on **2.28%** (mean |shift| 1.038). So "identical scores for
  > the deterministic arms" was wrong for greedy on the day it was written.
  >
  > **Amended prediction:** label, string_line and string_bare reproduce exactly (they never
  > generate); **greedy reproduces on ~97–98% of cells**, consistent with the v1↔v2 rate;
  > sampled within Monte-Carlo error. *Amended falsifier:* greedy drift materially above the
  > 2.28% v1↔v2 rate, which would implicate the prompt variant rather than hardware arithmetic.
  >
  > Registering an amendment is only honest if the amendment is timestamped before the data,
  > which it is — and if the reason is stated plainly, which is that the original was a claim
  > I had not checked against evidence already in the repo.

---

### Registered predictions for Phase 2 — FIXED 2026-08-08, BEFORE any Phase-2 data exists

Phase 1 is collected and analysed. Phase 2 changes the harness (v2) and expands the roster to
N=30 with size ladders to 72B. Both could be accused of being tuned to produce a result, so
the predictions are written down first. Verifiable in git: this commit precedes any Phase-2
run manifest.

**Harness v2 (measurement validity)**

- **P1.** Scoring the **full option line** (`"3: Very wrong"`) rather than the bare phrase will
  raise string-scoring retained mass substantially above the Phase-1 value of 0.22.

  > **AMENDMENT 2026-08-08, before any v2 data. The original wording above is left intact
  > deliberately — a registered prediction that gets quietly reworded is not registered.**
  > P1 as written is **not evaluable**, because its baseline is not the quantity it appears
  > to be. v1 ran `length_normalise=True`, so the 0.22 is `sum_k exp(per-token mean logprob)`
  > — a sum of geometric means — while v2's mass is a genuine probability. Comparing them
  > would be a category error in the other direction, and "v2 mass ≫ 0.22" would be trivially
  > satisfiable by the change of estimator alone rather than by the change of probe.
  >
  > **Replacement test, fixed now and equally falsifiable:** within v2, where `line` and
  > `bare` are scored by identical machinery on identical prompts, `line` mass will exceed
  > `bare` mass for a majority of models. This is a strict within-v2 contrast, so nothing
  > about the estimator can produce it. **Falsifier:** `line` mass ≤ `bare` mass for half or
  > more of the roster. Derivation: `results/derived/tokenization_boundary_diagnosis.md`.
  >
  > **P2 is unaffected** and remains the prediction that matters — it is about model
  > *ranking* agreement (ρ), never about mass.
- **P2.** With P1, string scoring's **model-ranking** agreement with label scoring will rise
  markedly from the Phase-1 ρ = 0.332. *If it does not*, the Phase-1 divergence is a genuine
  construct difference rather than a surface-form artifact — and that is the more interesting
  outcome, which is exactly why this is registered rather than decided afterwards.
- **P3.** Computing p_k **exactly** (forced continuation + `prompt_logprobs`) rather than from
  a top-20 list will change label scores little for high-mass models (Qwen, OLMo, granite) and
  materially for low-mass ones (Mistral-7B, Llama-3.2-1B, Ministral).
- **P4.** The **true-cloze** arm (options hidden from the prompt) will retain more mass than
  Phase-1 string scoring and will rank models *more* like the bare-phrase variant than like
  label scoring.

  > **AMENDMENT 2026-08-08, same defect as P1, same treatment — original text left intact.**
  > The **mass half is not evaluable as written**, for exactly the reason given under P1: its
  > baseline is Phase-1 string mass, which is a sum of geometric means rather than a
  > probability. **Replacement:** within v2, cloze mass will exceed `string_bare` mass for a
  > majority of models — same machinery both sides, so the estimator cannot manufacture it.
  > **Falsifier:** cloze mass ≤ `string_bare` mass for half or more of the roster.
  >
  > The **ranking half needs no amendment and is the substantive claim**: cloze will correlate
  > more strongly with `string_bare` than with `label` across models. If instead cloze tracks
  > `label`, then displaying the options was never what made our string arm behave unlike
  > textbook cloze, and the `config/prompt.yaml` limitation we have been disclosing is not the
  > operative one.

**Scale (Kirgis's claims 2 and 4)**

- **P5.** The individualizing-minus-binding **gap will increase with log parameter count**
  within the Qwen (0.5→72.7B) and Llama (1→70.6B) ladders. Basis: Tier-0 found the gap ≈ 0 on
  ≤14B open models while Kirgis reports it clearly at frontier scale, so the pattern is
  hypothesised to be a *capability* phenomenon. **Pre-committed falsifier:** a flat or
  negative slope on both ladders means his claim 2 does not generalise to open-weight models
  at any scale we can reach, and the "emerges with scale" story is dead.
- **P6.** The **per-model method spread** (max−min condition mean) will *decrease* with log
  parameter count. Basis: arXiv:2403.00998 reports method sensitivity is larger for weaker
  models. If true, R is partly a small-model artifact and should shrink on the Phase-2 roster
  — which would qualify our own headline, not just Kirgis's.

  > **AMENDMENT 2026-08-15 (C20) — the prediction text above is left VERBATIM, as all registered
  > predictions are; this corrects its stated BASIS, which was overstated.** The full text of
  > arXiv:2403.00998 was read on 2026-08-15 (it had only ever been read in abstract). The claim
  > is there, on p.5, but it is prefaced **"Judging from visual inspection"** — no test, no
  > effect size — it rests on **four models** (two 175B, one 7B, one 3B), and it is about models
  > that **perform worse on the task**, not models that are *smaller*. "Reports" is too strong a
  > verb, and the size-vs-performance slippage is ours.
  >
  > **The prediction and its outcome are unaffected** — P6 was tested against our own data, not
  > against theirs. What changes is how the prior is described in the write-up: *"a
  > visual-inspection remark in Tsvilodub et al. (2024), which we treated as a directional
  > prior"*, not *"a published result"*.

**Power**

- **P7.** At N=30 the credible intervals on R_f will narrow enough that at least two
  foundations escape `indeterminate`. Basis: B2 puts interior-band accuracy at 0.94 for N=30
  versus 0.86 at N=20. *If everything stays indeterminate at N=30*, the honest conclusion is
  that this estimand is not resolvable at any N a student project can reach, and the
  contribution becomes the design analysis itself.

Any prediction that fails is reported as failed. The Phase-1 record already contains one
wrong directional prediction of ours (pooled residuals were argued to inflate R; they deflate
it), which is the standard being kept.

### Secondary — rank agreement, descriptive only

Spearman rho of the model ordering under each pair of scoring methods, within each
foundation, after centring out the scoring-method main effect. Six pairs x seven
foundations = 42 values. **Report these descriptively. No pass/fail line attached** —
at this n the statistic is too blunt to carry a threshold.

### Controls

- **Permutation null:** shuffle scoring-method labels within model x item and recompute
  both statistics for a reference distribution. This will also show directly how wide the
  rho null is at your n, which is why rho is demoted.
- **Positive control:** all four methods should rank purity violations above social-norm
  violations in the same direction as Clifford's human means. If they don't, the harness is
  broken, not the world. **Fallback if Clifford's means prove unavailable:** a model-free
  ordering check needing no human data — every method must rate severe care violations
  above social-norm items. Weaker, but does not block the run.

### Committed in advance

**A null result is a real finding here** and will be reported as one. The field currently
assumes scoring-method agreement without checking. Decided now so there is no temptation
later. Disagreement is the more publishable direction and therefore the direction of drift.

---

## Go / no-go — completed 2026-08-07, session log removed 2026-08-11

The go/no-go read Kirgis's repo and paper, Clifford et al. (2015), QSTN, and
`wassname/llm-moral-foundations2`, and cleared the project to proceed. **Its ~360-line session
log has been removed from this file.** Every verified conclusion it produced lives in
`references.md`, which is the canonical record and holds each claim to the "verified by
fetching the source" standard. Keeping a second, longer copy here meant two places to check and
one of them silently going stale.

What it established, in one line each — details and citations in `references.md`:

- **Kirgis's paper and code disagree about renormalisation.** The printed formula has no
  denominator; `compute_expected_value` divides by `total_prob`. Where only one of the top three
  tokens is a digit the estimator degenerates to argmax.
- **Scoring method is collinear with provider for five of six providers**, not perfectly
  collinear — OpenAI has models in both arms. Say it the weaker way; a reviewer who checks
  Table 1 will catch the stronger one.
- **Clifford's per-vignette human means are obtainable** (Table 1, pp.1183–1186) and his
  baseline is an ideology-quota online panel of 18–40s, **not** the "nationally representative
  sample of US adults" Kirgis's discussion calls it.
- **QSTN is usable as tooling** and, later, as prior work that falsified this project's original
  novelty claim.
- **`wassname/llm-moral-foundations2` is stale** and does not occupy the territory.

The full log is in git history — `git log -p -- state.md`, or the `pre-cleaning-out-v1` tag.

---

## Open questions

- ~~Are Clifford's per-vignette human means obtainable?~~ **RESOLVED 2026-08-07: yes.**
  Clifford Table 1, pp.1183–1186, and transcribed in Kirgis's repo. See finding 4.
- ~~Which exact 116 of the MFV set does Kirgis use?~~ **RESOLVED 2026-08-07:** Clifford's
  132 minus all 16 physical-harm Care items. Care = emotional harm only. See finding 1(a).
- ~~Does the appendix inconsistency resolve in the code?~~ **RESOLVED 2026-08-07:** yes.
  The PCA matrix is 22 × 100; "16" and "129" are appendix typos. See finding 3.
- **New, open:** does the degeneracy in finding 2(b) — logprob scoring collapsing to argmax
  whenever only one of the top-3 is a digit — occur often enough in `logprob_responses.csv`
  to be worth reporting as a standalone result? Checkable on committed data, no GPU needed.
  Tempting, and adjacent to the actual deliverable. **Do not start it before the main run.**

---

## Known risks, already named

- **Tokenization eats day one.** After applying the chat template with a generation prompt,
  the first generated token may not be a bare digit; "0" and " 0" are different IDs and
  templates differ. Verify empirically per tokenizer by generating once and printing token
  IDs. Do not assume. Cite arXiv:2509.15020 for why this is a real hazard.
- **Refusals confound foundation with method (caught in review).** MFV sanctity items
  are graphic; safety-tuned instruct models will refuse some of them while never refusing
  social-norm items. Differential refusal by foundation distorts profile shape in the two
  free-generation conditions only — which masquerades as the foundation x method
  interaction, the headline estimand. Log refusal/parse rates per model x foundation x
  method and report them alongside the primary result. If refusal rates exceed ~10% on any
  foundation for any model, that model x foundation cell is flagged and the analysis is
  run with and without it.
- **Parse failure is a hidden confound.** Small models will emit unparseable text. The two
  free-generation conditions then run on a filtered subset while the two scoring conditions
  use all items. Log parse rate per model; restrict the primary analysis to models above a
  stated threshold; report the rest separately.
- **The sample sits where method sensitivity is largest.** arXiv:2403.00998 finds scoring
  method matters more for weaker models. Biggest effect, weakest generalisation to the
  frontier. State this before a reviewer does.
- **Prompt held fixed.** Prompt-phrasing sensitivity is a separate, documented problem.
  Say explicitly that scoring method is isolated with the prompt constant, or readers will
  conflate this with the perturbation literature.

---

## Limitations for the write-up

**Moved to `LIMITATIONS.md`, 2026-08-11.** This section held five bullets drafted early; all
five are now covered there at length, including the one that matters most —
**§18: this is a pre-specified plan, not a preregistration.** A tag in a repository the author
controls is an internal discipline device, not independent verification, and the stronger word
must never be used. `LIMITATIONS.md` runs to 22 entries; maintaining a five-line summary
alongside it was how a limitation goes stale without anyone noticing.
