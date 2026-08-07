# RESUME — what to do when you come back

Written 2026-08-07 at the end of the first working session, after Steps 1–3 of
`~/.claude/plans/okay-what-should-be-gleaming-possum.md`. Read this first; `state.md` has the
decisions, this has the operational sequence.

---

## Part 1 — audit of the work so far

### Verified, hard

| claim | how it was checked |
|---|---|
| 116 items, correct foundation counts | Build script asserts it; independently re-checked 2026-08-07 |
| Item text / foundation / human means match the source **row for row** | Diffed all 116 rows against `data/source/kirgis_vignettes_short.csv`: **0 mismatches** on all three fields |
| Item IDs contiguous 1–116 and aligned between the two files | Set comparison + sort check |
| No CSV corruption | 117 raw lines for 116 items ⇒ no embedded newlines, despite 2 items containing commas |
| Source is Clifford Table 1 | 9 rows matched by eye against the published PDF, pp.1183–1186, across 4 foundations |
| Kirgis's code renormalises; his paper's formula does not | Both read verbatim; quoted in `references.md` |
| Which 116 of Clifford's 132 | Set difference: all 16 physical-harm Care items dropped |
| GPU works: sm_120, bf16 | `torch.cuda.get_arch_list()` + live matmul on device |
| vLLM runs on this card | Only with `VLLM_USE_FLASHINFER_SAMPLER=0`; verified by a completed generation |
| `"0"` vs `" 0"` are different tokens; model emits bare | Probe: `[15]` vs `[220,15]`; greedy emitted `id=17`=`'2'` |
| Options 0 and 1 share a first token | Probe: both begin with token `2623` (`'Not'`) |

### NOT verified — deal with these before trusting anything downstream

**1. QSTN has never been run. This is the biggest untested assumption in the project.**

Everything on the pod so far used **raw vLLM**, not QSTN. QSTN imports
`from vllm.sampling_params import StructuredOutputsParams` and reads
`req_output.outputs[0].logprobs[pos].values()` with `.decoded_token` / `.logprob`
(`local_inference.py:8, 540–541`). Its only pin is `vllm>=0.12` — an open upper bound — and we
installed **vllm 0.26.0**, many releases newer. vLLM breaks internal APIs regularly.

*If QSTN is broken against 0.26*, options in order of preference: (a) pin an older vLLM in the
venv, (b) patch the two or three call sites, (c) drop QSTN and use raw vLLM for all four
conditions. Option (c) costs perhaps half a day and loses the "same framework as the closest
prior work" argument, but the project survives it. **Decide this in the first 20 minutes back,
not on day two.**

**2. The probe's prompt was rendered by hand, not by QSTN.**

`scripts/probe_tokenization.py` substitutes `{{QUESTION_CONTENT_PLACEHOLDER}}` itself. So the
tokenization findings are sound for *that* string, but we have **not** confirmed QSTN builds the
same string. The byte-identical-across-conditions check in Step 5 must use QSTN's real output,
not ours. If QSTN's builder injects anything extra, the probe must be re-run.

**3. Sampled generation (T=1) untested with the native sampler.**

We disabled FlashInfer. Greedy + logprobs works. Temperature-1 sampling through vLLM's native
PyTorch sampler is untested — likely fine, but it is one of the four conditions.

**4. Tokenization findings are Qwen-specific.** Re-run the probe per tokenizer family
(Llama, Gemma, Mistral, Phi, OLMo) before trusting their label scores. Chat templates differ,
and whether the bare or spaced digit wins depends on what the template emits last.

**5. `HF_TOKEN` still broken** — blocks the 5 gated models only.

### One honest caveat found in the probe

Renormalised vs unnormalised expectation differed by **0.0018** on the probe item, because
top-20 captured 99.9% of the mass. Kirgis used **top-3**, so his gap will be larger — but this
suggests **the renormalisation half of the audit may be a small effect**, and the *degeneracy*
half (argmax collapse) is the likelier finding. Step 4 settles it. Do not pre-announce
renormalisation as the headline.

---

## Part 2 — the sequence when you return

### A. Console, ~5 min, before anything else

1. **Settings → Secrets** — create `HF_READ_TOKEN` (underscores) with your token. Delete
   `HF-read-token`. RunPod secrets can't be renamed, hence the recreate.
2. **Edit Pod** — set `HF_TOKEN = {{ RUNPOD_SECRET_HF_READ_TOKEN }}`. Do **not** create a new
   pod; the existing one keeps the volume, weights, and wheel cache.
3. Leave the pod **stopped** for now. Step 4 is local and free.

### B. Step 4 — Kirgis reanalysis. Local, $0, ~1 h. Do this before restarting the pod.

Runs on `data/source/` and the scratch clone of his repo (re-clone if the temp dir is gone:
`git -c http.sslBackend=schannel clone https://github.com/peterkirgis/llm-moral-foundations`).
Four numbers from his 696 committed logprob responses:

1. Degeneracy rate — how many of each top-3 are digits (distribution over 1/2/3).
2. Argmax-collapse rate — fraction where exactly one digit survives, so his estimator returns an
   integer exactly.
3. Fallback rate — how often extraction returns `None` and his code silently substitutes the
   EDSL-parsed answer.
4. **Does it move anything?** Recompute under his code, his printed formula, and renormalised
   over all five options; check whether foundation means or his 6-model ranking shift.

**Hard stop at one hour.** Insurance, not the deliverable.

### C. Step 5 — the integration step. Pod on, ~2 h, ~$2.

Restart pod → `bash /workspace/bootstrap.sh && source /workspace/env.sh` (offline rebuild from
the volume's wheel cache, a few minutes).

**Order matters — do the cheap kill-shot first:**

1. **60-second QSTN smoke test** before writing anything: import qstn, build a one-item
   questionnaire, run one prompt through `batch_generation`. This answers unverified-item #1.
   If it fails, stop and pick (a)/(b)/(c) above.
2. Dump QSTN's rendered prompt; diff against the probe's hand-built string (unverified #2).
3. Wire the four conditions on `Qwen2.5-1.5B-Instruct`, 10 items including Sanctity.
4. Write string scoring by hand — vLLM `prompt_logprobs`, five continuations per item.
   **Decide length normalisation explicitly and record it in `config/prompt.yaml`.**
5. **The critical check:** render all four conditions' full chat-templated prompts and confirm
   they are byte-identical. If they aren't, Decision 2 in `config/prompt.yaml` didn't apply and
   nothing downstream is interpretable.
6. Confirm label and string both return continuous expectations on 0–4, not argmax.

### D. Step 6 — core eight. Pod on, ~3 h, ~$10.

Re-run the tokenization probe per new tokenizer family first (unverified #4). Checkpoint per
model to `/workspace`. Log refusal and parse rates per model × foundation × method and **read
those tables before looking at any result** — differential Sanctity refusal in the
free-generation arms masquerades as the headline estimand.

### E. Step 7 — extension. Possibly free now.

The 32 GB card may hold Qwen2.5-14B (~28 GB bf16) directly, so the separate L40S pod the plan
budgeted may be unnecessary. Short sequences favour us. Try it; don't assume it.

### F. Step 8 — analysis. Local, $0, ~3 h.

Variance ratio with **method-specific residual variances** (mandatory), rank agreement
descriptive only, permutation null, positive control against Clifford's means. Cutoff is
preregistered and closed: **R < 0.25 robust / 0.25–1.0 degraded / R > 1.0 not interpretable.**

---

## Part 3 — pod cheat-sheet

```bash
ssh -i ~/.ssh/id_ed25519_runpod -p 38177 root@213.173.102.27     # port/IP change on restart!
bash /workspace/bootstrap.sh && source /workspace/env.sh          # after every pod stop
```

**Check the Connect panel after restarting — RunPod usually reassigns the IP and port.**

| path | survives stop? |
|---|---|
| `/workspace/mft/`, `hf-cache/`, `pip-cache/`, `env.sh`, `bootstrap.sh` | yes |
| `/root/venv`, `/root/.cache/pip` | **no** — rebuild with `bootstrap.sh` |

Required env (already in `env.sh`): `HF_HOME=/workspace/hf-cache`,
**`VLLM_USE_FLASHINFER_SAMPLER=0`** (vLLM will not start on sm_120 without it),
`PATH=/root/venv/bin:$PATH`.

Never put a venv on `/workspace` — FUSE is 1.0 GB/s bulk but collapses on many small files.
Venv on container disk, weights on the volume.

**Budget so far: well under $5.** GPU ~$0.72/hr, volume ~$0.47/day. Projected total under $15
against the $100 ceiling. Money is not the binding constraint — **the two-day time budget is.**
