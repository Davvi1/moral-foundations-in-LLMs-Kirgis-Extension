# RESUME — what to do next

Updated 2026-08-07 after completing B0, B1 and B2. `state.md` holds the decisions; this holds
the operational sequence. Working plan: `~/.claude/plans/okay-what-should-be-gleaming-possum.md`.

---

## Where things stand

| | status |
|---|---|
| **B0** version control, LICENSE, README | **done** — repo on `main`, clean tree |
| **B1** Kirgis reanalysis (exploratory) | **done** — found provider data corruption, not estimator degeneracy |
| **B2** design simulation | **done** — roster raised to N ≈ 20; `indeterminate` verdict added |
| **B3** analysis plan | **locked** in `ANALYSIS_PLAN.md`, git tag `analysis-plan-locked`. OSF deposit dropped by decision 2026-08-07 |
| **B4** QSTN smoke test + four conditions | pod work, not started |
| **B5** confirmatory run | pod work, needs `HF_TOKEN` fixed |
| **B6/B7** analysis, write-up | after B5 |

## Two things only you can do

### 1. Fix `HF_TOKEN` (5 min, console) — blocks gated models in B5

RunPod silently dropped `{{ RUNPOD_SECRET_HF-read-token }}` because hyphens break its template
substitution. Secrets cannot be renamed, so:

1. **Settings → Secrets** → create **`HF_READ_TOKEN`** (underscores) with the same token.
   Delete the old one.
2. **Edit Pod** → set `HF_TOKEN = {{ RUNPOD_SECRET_HF_READ_TOKEN }}`.
   Use the existing pod — it keeps the volume, weights and wheel cache. Do not create a new one.

Verify after restart with `echo ${#HF_TOKEN}` — should print a non-zero length.

### 2. Nothing — the analysis plan is already locked

OSF deposit was dropped by decision on 2026-08-07. The plan is fixed in `ANALYSIS_PLAN.md`
at git tag `analysis-plan-locked` (commit `75b57b2`), which provably contains no
`results/raw/`.

**Language rule, and it matters for the write-up:** call this a *pre-specified analysis
plan*, never a *preregistration*. A tag in a repo you control is an internal discipline
device, not independent verification. The discipline is still real — changing the decision
rule now shows up as a diff against a tagged commit — but the stronger word is not available.

---

## What B1 and B2 changed

**B1 falsified both of my go/no-go hypotheses about Kirgis's estimator.** Argmax degeneracy is
5.6% and changes nothing (Spearman 1.00 against his code's ranking); the silent fallback never
fires (0%). What is actually there: **grok-3-beta returned malformed `top_logprobs` on 44% of
responses** — two entries instead of three, summing to ~0 probability, while the emitted token's
own logprob says p = 1.0. His renormalisation accidentally rescues it; his *printed formula*
would not (grok-3's mean collapses 1.98 → 1.20, rank 4 → 6). So for those items "logprob
weighting" was actually argmax — **scoring method was not uniform even within his logprob arm.**

→ Consequence for us: **log total logprob mass per response** as an integrity check. Now
pre-specified.

**B2 changed the roster and the decision rule.** Interior-band classification accuracy: N=8 →
0.64, N=13 → 0.76, N=20 → 0.86, N=30 → 0.94. Target raised to **N ≈ 20**; N=8 must not carry
the primary claim. A fourth verdict, **`indeterminate`**, was added for intervals straddling a
band boundary — no feasible N resolves those, so forcing a call would be false precision. My
earlier analytic estimate of interval width (×/÷2.5 at N=13) was **optimistic by roughly a
factor of two**; the true multiplicative width is ~12×. Do not quote the old number.

---

## B4 — next pod session (~2 h, ~$2)

Restart pod → `bash /workspace/bootstrap.sh && source /workspace/env.sh`.
**Check the Connect panel — RunPod reassigns IP and port on restart.**

Cheapest kill-shot first:

1. **60-second QSTN end-to-end test.** `StructuredOutputsParams` and `prompt_logprobs` are
   confirmed present in vLLM 0.26.0, so this should pass — but it has never actually been run.
   If it fails: pin an older vLLM, patch the two or three call sites, or drop QSTN for raw vLLM
   (~half a day; the project survives).
2. Dump QSTN's rendered prompt and diff it against the probe's hand-built string. The probe
   substituted the placeholder itself, so QSTN's rendering is unverified.
3. Wire the four conditions on `Qwen2.5-1.5B-Instruct`, 10 items including Sanctity.
4. Write string scoring by hand: `SamplingParams(max_tokens=1, prompt_logprobs=0)` over five
   concatenated prompts, full-sequence log-likelihood. **Decide length normalisation explicitly**
   and record it in `config/prompt.yaml`.
5. **The critical check:** render all four conditions' chat-templated prompts and confirm they
   are **byte-identical**. If not, nothing downstream is interpretable.
6. Confirm label and string both return continuous expectations on 0–4, not argmax.

## B5 — confirmatory run (~3 h, ~$12 at N≈20)

Re-run `scripts/probe_tokenization.py` per new tokenizer family — the findings are Qwen-specific
and chat templates differ. Checkpoint per model. Save raw unparsed outputs alongside parsed
scores. Log refusal, parse-failure, and logprob-mass integrity per model × foundation × method,
and **read those tables before looking at any result.**

Weights need not be held simultaneously: download → run four conditions (minutes) → delete →
next. The 200 GB volume is not the binding constraint at N=20.

---

## Pod cheat-sheet

```bash
ssh -i ~/.ssh/id_ed25519_runpod -p <PORT> root@<IP>    # both change on restart
bash /workspace/bootstrap.sh && source /workspace/env.sh
```

| path | survives pod stop? |
|---|---|
| `/workspace/mft/`, `hf-cache/`, `pip-cache/`, `env.sh`, `bootstrap.sh` | yes |
| `/root/venv`, `/root/.cache/pip` | **no** — `bootstrap.sh` rebuilds offline from the volume |

Required env (already in `env.sh`): `HF_HOME=/workspace/hf-cache`,
**`VLLM_USE_FLASHINFER_SAMPLER=0`** — vLLM will not start on sm_120 without it.

Never put a venv on `/workspace`: FUSE gives 1.0 GB/s bulk but collapses on many small files.
Venv on container disk, weights on the volume.

**Verified environment:** `runpod/pytorch:1.0.2-cu1281-torch280-ubuntu2404`, RTX PRO 4500
Blackwell 32 GB (sm_120), Python 3.12.3, vLLM 0.26.0, transformers 5.14.1.

**Budget: under $5 spent. Projected total under $25 at N=20 against a $100 ceiling. Time, not
money, is the binding constraint.**
