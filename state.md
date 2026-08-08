# state.md

Living record. Sessions start without memory of prior ones — if a decision isn't written
here, it didn't happen. Update it when something is settled, not at the end.

---

## Status

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

**→ READ `RESUME.md` FIRST when picking this up.** It carries the audit of what is and is not
verified, the pod cheat-sheet, and the ordered sequence for the next session. The single most
important item there: **QSTN has never actually been run.** Everything on the pod so far used
raw vLLM. QSTN pins only `vllm>=0.12` and we installed 0.26.0, so its API compatibility is
untested and is the first thing to check — a 60-second test that decides whether the harness
plan survives.

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
  of Kirgis's CSV in `data/source/` with `PROVENANCE.md`. Build is self-verifying: it asserts
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
5. **Multiplicity across the 7 foundations is resolved:** report all seven intervals; the
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

## Go / no-go — blocking, do this first

1. Clone github.com/peterkirgis/llm-moral-foundations. Confirm three things exist: the 116
   MFV item texts with foundation labels, his exact prompt string, his per-item responses.
2. Read the scoring code. Does he renormalise the top-3 weights? Which token set does he
   index? Record verbatim here.
3. If items are absent, fall back to Clifford et al. (2015). If neither route works, this
   project does not run — stop and pick another.
4. Check arXiv:2403.00998 for overlap. It compares five scoring methods on MCQ tasks
   including fit to human data. If it already covers the profile-stability question, the
   contribution narrows and the framing must change.
5. RESOLVED 2026-08-07: QSTN checked (paper fetched and read). Two consequences.
   (a) Novelty: their evaluation compares 8 response generation methods on ANES/GLES/ATP
   (32M responses) and finds significant method effects — the old novelty claim was
   falsified; the revised claim above is the one to defend. (b) Harness: QSTN is MIT,
   pip-installable, vLLM-backed, supports instruct models, and covers token-probability,
   restricted, and open generation with parsers — three of four conditions. String scoring
   (sequence log-likelihood of full option text) is NOT in their method list and needs
   custom code. Evaluate building on QSTN before writing a harness from scratch.
6. Re-check github.com/wassname/llm-moral-foundations2 for movement.

**Nothing gets built before 1–3 are answered here in writing.**

**Executed 2026-08-07. Items 1, 2, 3, 5, 6 answered below. Item 4 (arXiv:2403.00998 overlap)
was NOT re-run this session — it was already scoped in references.md and is not blocking.**

---

## Go / no-go findings — 2026-08-07

Method: cloned `peterkirgis/llm-moral-foundations`, `dess-mannheim/QSTN`, and
`wassname/llm-moral-foundations2` into a scratch dir outside this repo; read the files;
fetched Kirgis arXiv:2511.11790 (PDF, 10pp) and Clifford et al. 2015 (PDF, 21pp) and read
the relevant pages directly. Everything below is quoted from a file or a page I read.

### 1. What is actually in Kirgis's repo

19 files, 5 commits, HEAD `fc39db0 add analysis`. All three things are present.

**(a) The 116 MFV item texts with foundation labels — PRESENT.**
`data/survey/vignettes_short.csv`, 116 rows. Columns: `Scenario, Foundation, Care,
Fairness, Loyalty, Authority, Sanctity, Liberty, Not Wrong, Wrong`.
Also `data/survey/vignettes.csv`, 132 rows — the full Clifford set with finer Care labels.

Foundation counts, 116-item file: Authority 17, Care 16, Fairness 17, Liberty 17,
Loyalty 16, Sanctity 17, Social Norms 16.

**This answers "which exact 116?"** He starts from Clifford's full 132 and drops all 16
`Care (p, a)` (physical harm, animals) and `Care (p, h)` (physical harm, humans) items,
keeping only the 16 `Care (e)` (emotional harm) items. 132 − 16 = 116. The dropped set is
the animal-cruelty and physical-violence vignettes (squirrel, cat, dolphin, pony, geese;
stapler, ruler, slapping, hot coffee, spanking, thumbtack). Verified by set difference.

*Consequence for your design, not his error:* his Care foundation is **emotional harm
only**. Physical harm is absent from the whole instrument as administered. Anything you
say about "Care" inherits that. Also relevant to the refusal risk already logged — the
most graphic Care items are already gone, so differential refusal will concentrate in
Sanctity, as predicted.

**(b) His exact prompt string as administered — RECOVERABLE, from two sources combined.**

The question-text template, `surveys/mft_base.py:35-40`, verbatim:

    q = QuestionLinearScale(
      question_name = "moral_judgment",
      question_text = "Please rate how morally wrong this behavior is on the following five-point scale: {{dilemma}}",
      question_options = [0,1,2,3,4],
      option_labels = {0: "Not at all wrong", 1: "Not too wrong", 2: "Somewhat wrong", 3: "Very wrong", 4: "Extremely wrong"}
    )

That is the template, not the wire format — EDSL's `QuestionLinearScale` wraps it. The
wrapper is not in the repo (it lives in `edsl==0.1.13`), **but the paper prints the
rendered result** on p.4, verbatim:

    Example Prompt (Care): Please rate how wrong this behavior is on the following five-point
    scale: You see a girl laughing at another student forgetting her lines at a school play.

    0: Not at all wrong
    1: Not too wrong
    2: Somewhat wrong
    3: Very wrong
    4: Extremely wrong

    Only 1 option may be selected.
    Respond only with the code corresponding to one of the options. E.g., "0" or "4" by itself.
    After the answer, you can put a comment explaining why you chose that option on the next line.

Consistent with `'prompt_tokens': 122` in the raw API responses.

**Discrepancy, minor:** the paper's box says "how wrong this behavior is"; the code says
"how **morally** wrong". The code is authoritative — the same string appears again at
`mft_base.py:60` as the prefix used to strip the question text back off, and the stripped
`Scenario` values in the response CSVs match. Treat the paper's box as a transcription slip.

**(c) His per-item, per-model responses — PRESENT, three files.**

| file | rows | models × items | contents |
|---|---|---|---|
| `data/results/logprob_responses.csv` | 696 | 6 × 116 | full raw API response incl. per-token top-3 logprobs |
| `data/results/sampled_responses.csv` | 1856 | 16 × 116 | full raw API response, `logprobs: None` |
| `data/results/cleaned_model_responses.csv` | 2436 | 21 × 116 | merged, scored, foundation-joined |

Every model has exactly 116 rows, no gaps. 6 + 16 = 22 raw; `llama-4-Maverick` is dropped
in the notebook, giving the 21 of the paper. Also present: `data/embeddings/{emfd,mfd,mfd_2}_scores.csv`
(the Fig 5 FrameAxis intensities — already out of scope) and the five paper figures as PNG.

### 2. The scoring code — both questions answered verbatim

File: `analysis/final_analysis.ipynb`, cell 2, function `compute_expected_value`.

**(a) Does he renormalise? — HE DOES. This is a CORRECTION.**

Code, verbatim:

        total_prob = 0.0
        weighted_sum = 0.0

        # Compute the weighted sum of the allowed token values.
        for entry in top_logprobs:
            cand_token = entry.get("token", "").strip()
            if cand_token in allowed_tokens:
                prob = math.exp(entry["logprob"])
                weighted_sum += int(cand_token) * prob
                total_prob += prob

        if total_prob == 0:
            return None

        return weighted_sum / total_prob

Paper, p.4, verbatim:

    E_score = Σ_{k=1}^{3} s_k exp(ℓ_k) = Σ_{k=1}^{3} s_k p_k

**CORRECTION to references.md line 24 and to the "Open, unverified" list.** The old note
read "Formula as printed does not renormalise... **Unverified whether the code
renormalises — check the notebook.**" Half right, and the half that was wrong matters:

- The **printed formula** does not renormalise. No denominator. **references.md was right.**
- The **code** does renormalise, and additionally filters to digit tokens. **The suspicion
  that it might not was wrong.**
- **Therefore the paper and the code disagree with each other.** That is a cleaner finding
  than either branch you were expecting, and it is the single strongest concrete fact this
  session produced. Fix references.md line 24 to say this.

**(b) Which token set? — Top 3 of the full vocabulary, filtered to digits, then
renormalised over whatever survived. Suspicion CONFIRMED, mechanism worse than suspected.**

`top_logprobs` is the provider's top-3 over the entire vocabulary (EDSL passes
`logprobs=True`; the raw data shows exactly 3 entries per token). The loop keeps only
entries in `allowed_tokens = {"0","1","2","3","4"}`. So the denominator is a
**data-dependent random subset of size 1, 2, or 3** — not the five valid options, and not
a fixed set.

**Name the consequence, because it is load-bearing for your framing:** when only one of the
top three is a digit, `weighted_sum / total_prob` = k·p / p = **k exactly**. The estimator
silently degenerates to argmax. So his "logprob" arm is not one estimator — it is a mixture
of a 3-point expectation, a 2-point expectation, and plain argmax, and which one you get is
decided per item per model by whether non-digit tokens crowd the top-3. This is stronger
than "logprob scoring vs. sampled scoring differ": his logprob condition is not internally
consistent with itself. You can demonstrate this on his own committed data without running
a single model, because `logprob_responses.csv` contains the raw top-3 for all 696 responses.

Two further things in the same cell that compound it:

    df['Expected Value Answer'] = df['Expected Value Answer'].fillna(df['Answer'])

When logprob extraction fails, it silently falls back to the EDSL-parsed integer. The
logprob arm therefore contains an unreported number of parsed free-generation answers.

    df.groupby(['Service','Foundation','Model'])['Expected Value Answer'].transform(lambda x: x.fillna(x.mean()))

Remaining missing values are mean-imputed within Service × Foundation × Model — i.e.
imputed at the cell mean before that cell's mean and SEM are computed. Harmless to the
means, but it deflates the SEM, so the 95% CIs in Figure 2 are narrower than they should
be by an unreported amount. Worth one sentence in the write-up; not worth a fight.

**CORRECTION — "perfectly collinear with provider" is an over-claim.** Paper Table 1 (p.4)
plus the two response files give the actual split:

- **Logprob-scored (6):** GPT-3.5-Turbo, GPT-4-Turbo, GPT-4o, GPT-4.1 · Grok-2, Grok-3
- **Sampled, mean of 10 (15):** all 4 Anthropic, both DeepSeek, all 4 Google, all 3 Meta,
  **plus GPT-4.5 and o3-Mini**

So OpenAI has models in **both** arms (4 logprob, 2 sampled). Scoring method is perfectly
collinear with provider for 5 of 6 providers, not all 6. The confound is still severe and
the between-provider claims are still not identified — but CLAUDE.md and the project
one-paragraph summary both say "perfectly collinear," and a reviewer who checks Table 1
will catch that. **Restate as: collinear with provider for every provider except OpenAI,
where the split is confounded with model identity instead and so still identifies nothing.**
Weaker wording, same conclusion, and it survives contact with the paper.

### 3. The appendix inconsistency — RESOLVED. Two typos, no substantive effect.

Appendix A, p.10, verbatim:

    In total, I have 16 survey responses and 100 survey questions. Thus, the dataset that I
    am performing PCA on can be written as:
        X = Responses × Questions ∈ R^{16×100}
    ...
        XV = UΣV^T V = UΣ ∈ R^{129×2}
    ...
    Originally, V ∈ R^{100×2}. For my analysis, I group questions by their foundation labels
    to produce V' ∈ R^{6×2}.

What the data and the code say:

- **100 questions — CORRECT.** The notebook drops Social Norms before the PCA. 116 − 16
  Social Norms = 100. Verified: exactly 100 unique non-Social-Norms scenarios.
- **V ∈ R^{100×2}, V' ∈ R^{6×2} — CORRECT.** 6 = the six foundations once Social Norms goes.
- **"16 survey responses" / R^{16×100} — WRONG.** Cell 10 pivots `index="Model"` over 21
  models concatenated with one `"human"` row. The matrix is **22 × 100**.
- **R^{129×2} — WRONG, and inconsistent with his own algebra.** X ∈ R^{16×100} times
  V ∈ R^{100×2} is R^{16×2} by his own notation, not R^{129×2}. It is not 22 either.
  **129 matches no count anywhere in the repo** — not 132, 116, 100, 21, 22, 16, 6, 2436,
  1856, or 696.

The only 16 in the data that could plausibly have produced "16 responses" is the model
count in `sampled_responses.csv`. **That is a guess and I am labelling it as one** — it is
not a resolution and should not be written up as one.

**Bottom line: 116 items and 21 models are both confirmed against the data; the PCA is
22 × 100. The appendix cannot be used to reconstruct his Figure 4 — cell 10 can.**
This is a detail, not an argument. Do not lead with it.

### 4. Clifford's per-vignette human means — OBTAINABLE. Definite. Figure 2 replicates.

Two independent sources, cross-verified against each other:

- **Source of truth:** Clifford et al. (2015), **Table 1, "Respondent ratings of moral
  scenarios," pages 1183–1186 — in the main article, not supplementary material.** Columns:
  Scenario · Foundation · Care/Fairness/Loyalty/Authority/Sanctity/Liberty classification %
  · Not Wrong % · **Wrong (mean severity)**. Free PDF at cabezalab.org and scottaclifford.com.
- **Already transcribed:** the `Wrong` column of Kirgis's `data/survey/vignettes.csv` (132)
  and `vignettes_short.csv` (116) is a verbatim copy of Clifford's Table 1.

Verified by exact match on 9 rows spanning Care (e), Care (p,a), Sanctity and Social Norms —
e.g. "You see a teenage boy chuckling at an amputee he passes by while on the subway" →
Care (e), 83% / 0% / 0% / 3% / 10% / 3%, Not Wrong 0%, **Wrong 3.4** in both. Social Norms
floor cases match too (rotary phone → Not Wrong 100%, Wrong 0.0). The transcription is good.

Scale matches: Clifford's Measures section reads "rate how morally wrong the behavior is on
a 5-point scale labeled *not at all wrong, not too wrong, somewhat wrong, very wrong,
extremely wrong*" — the exact five labels Kirgis reuses with codes 0–4. Observed range on
the 116-item set: min 0.0, max 3.8, mean 2.20.

**Two caveats on the baseline, both of which you should state before a reviewer does.**

**CORRECTION — the baseline is not nationally representative.** Clifford, Study 1:
respondents were "recruited in three waves (n = 330, 192, 94) from a national online panel
by Qualtrics," "limited to the age range of 18–40 (M = 35, 32, 33)," and "balanced on
ideology (to maintain an equal number of liberals, moderates, and conservatives)."
Kirgis's Discussion describes this as "a nationally representative sample of US adults."
It is an ideology-quota online panel of 18-to-40-year-olds. **Do not repeat his
description.** This is a free, fully documented criticism and it is directly relevant to
his headline claim, since "models diverge from the human baseline" is only as good as the
baseline. It costs you nothing to state and it is the kind of thing a facilitator will
reward you for catching.

**n ≈ 30 per vignette.** Clifford: "Respondents were given a random subset (14-16) of the
vignettes such that each vignette was rated by approximately 30 individuals." On a 0–4
scale that puts the standard error of each item mean around 0.2. Treating these means as a
fixed, error-free reference — which the Figure 2 mean-difference plot does — understates
uncertainty. If you replicate Fig 2, either propagate that error or say plainly that you
did not.

The positive control in the analysis plan is therefore **live**, and the weaker fallback
("severe care above social-norm items") is not needed. Keep it written down anyway.

### 5. QSTN as a foundation — VERIFIED, state.md's assertion was right. Recommendation: build on it.

MIT. `requires-python >=3.12`; deps `pandas, pydantic, openai, tiktoken, json_repair`;
`qstn[vllm]` pulls `vllm>=0.12`. Tests, docs, CI, active (HEAD `322963d update docs`).

Concrete response-generation classes exported from `qstn.inference`:
`ChoiceResponseGenerationMethod`, `LogprobResponseGenerationMethod`,
`JSONSingleResponseGenerationMethod`, `JSONReasoningResponseGenerationMethod`,
`JSONVerbalizedDistribution`.

Against the four conditions in CLAUDE.md's terminology table:

| Condition | QSTN off the shelf? | What you write |
|---|---|---|
| **label scoring** | **Yes.** `LogprobResponseGenerationMethod(token_position=0, token_limit=1, output_index_only=True)` | The expectation over 0–4, and the renormalisation decision. `_get_logprobs` hands back a raw `{token: logprob}` dict and computes nothing. ~10 lines — and it is exactly the decision you are studying, so you want it explicit anyway. |
| **free generation, greedy** | **Yes.** `JSONSingleResponseGenerationMethod` at T=0 + their parser | Nothing. |
| **free generation, sampled** | **Yes, with an operational caveat** | Nothing, but see below. |
| **string scoring** | **No.** | All of it. |

**Caveat on sampled generation.** Both output paths read `request_output.outputs[0]`
(`local_inference.py:541` and `:583`), so vLLM's `n=k` per request is not honoured — you
would silently get one sample. k samples means k passes over the questionnaire with
different `seed` values on `batch_generation`. Prefix caching makes this cheap in tokens,
but it is k batch calls, not one. Budget accordingly; it does not change the design.

**String scoring — VERIFIED absent, and the reason it cannot be faked is concrete.**
Setting `output_index_only=False` on the logprob method still reads **one token position**.
That is first-token-of-option-text scoring, not sequence log-likelihood. And on *this*
instrument that is degenerate: the five options are "Not at all wrong" / "Not too wrong" /
"Somewhat wrong" / "Very wrong" / "Extremely wrong" — **options 0 and 1 share their first
token, "Not".** First-token scoring cannot separate them. So string scoring here *must* be
a full-sequence log-likelihood, and you then face a real, nameable choice: length-normalise
or not, since the options differ in token length. Name it as a choice in the write-up;
it is a researcher degree of freedom and pretending otherwise is the kind of thing this
project exists to criticise. (`JSONVerbalizedDistribution` is the model *stating*
probabilities in JSON — a different construct entirely, not string scoring.)

**One unadvertised reason to take QSTN:** `local_inference.py:540` reads

    x.decoded_token.lstrip(space_char).lstrip(): x.logprob

That is the leading-space tokenization hazard from arXiv:2509.15020 — the top day-one risk
in the "Known risks" section below — already handled, with the comment "Strip space token
and any leading whitespace from tokenization." Their questionnaire format is
`questionnaire_item_id,question_content`, so `vignettes_short.csv` maps in with a rename.

**Recommendation: build on QSTN; hand-write string scoring only.** Reasons, in order:
(1) it removes the two things most likely to consume day one — vLLM batching/prefix caching,
and the tokenization bug; (2) the item format is trivially compatible; (3) it puts you in
the same tooling as the closest prior work, which is a defensible answer at a check-in —
"I used the framework from the paper I have to engage with, and added the one condition it
lacks"; (4) the division of labour is clean and explainable: three conditions from a
published, tested framework, one condition written by you because nobody has it.

**Risks to state honestly rather than discover:** Python ≥3.12 and vllm ≥0.12 — verify
against the rented GPU image *before* committing, this is the kind of thing that eats an
afternoon. And you inherit their prompt-construction layer, which makes the prompt a fixed
nuisance parameter you adopt rather than choose. That is acceptable — arguably better than
an ad hoc prompt, because it is documented — but say so rather than letting it pass.

**Consequence for the replication claim, now firmer.** You will not be sending Kirgis's
literal EDSL-rendered prompt. "Prompt held fixed" was already logged as a risk; it is now
a harder constraint — under QSTN you *cannot* match his wire format even if you wanted to.
This is not a prompt-level replication of Kirgis and the write-up must say so plainly.
It does not threaten the design, because scoring method is manipulated *within* your own
fixed prompt, which is the whole point.

### 6. wassname/llm-moral-foundations2 — no movement

Remote `HEAD = f05ffe1e9a87528138ea84f026ec991974383b08`, **dated 2025-09-16**, identical
to the clone. **~11 months stale as of today.** No paper, no release, still a journal.

The entry referenced in references.md is dated 2025-08-21 and reads verbatim:

    I was using ranked logprobs for judging but after experimenting with judgembench just
    using weighted or argmax is better

references.md's characterisation of it is accurate — **no correction needed there.**

The repo has grown past what references.md describes: it now carries steering-vector data
(`data/steering/*.json5`, `llm_moral_foundations2/steering.py`), a "daily dilemma" strand,
and `nbs/mcf_vignettes/01_gather_data_hf_logprobs.py`. Still an undocumented side project.
The territory is not occupied. Do not cite the journal entry as evidence for anything — it
is one line with no method attached — but it remains corroborating.

### Carried forward, not done this session

- arXiv:2403.00998 overlap check (old go/no-go item 4). Not blocking; already scoped in
  references.md. Do it before the write-up, not before the run.
- references.md line 24 needs the correction from finding 2(a) written into it.
- CLAUDE.md and the project summary need "perfectly collinear with provider" softened per
  finding 2(b).

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

## Limitations for the write-up — draft now, don't discover later

- **Not externally registered.** Decision 2026-08-07: OSF deposit dropped. The analysis plan
  is locked in `ANALYSIS_PLAN.md` at git tag `analysis-plan-locked` (commit `75b57b2`), which
  provably contains no `results/raw/`. **Call this a pre-specified analysis plan, never a
  preregistration** — a tag in a repository the author controls is an internal discipline
  device, not independent verification. The discipline is real (changing the decision rule now
  produces a visible diff against a tagged commit) but the stronger word is not available and
  using it would be exactly the kind of over-claim that sinks a write-up.

- This did not replicate Kirgis's findings. It replicated his design on a different model
  sample and manipulated something he held fixed by necessity.
- Treating a token distribution as a response distribution is a construct assumption
  imported from human psychometrics. The MFV was validated on people.
- Thirteen small instruction-tuned models are not the frontier.
- Whether scoring method is a researcher degree of freedom or part of the construct
  definition is a values question about what "a model's moral profile" means, not a
  technical one.
