# Corrections log

Every claim this project made and then had to withdraw or reverse, with how it was caught.
One place, in date order, so the write-up's limitations section and any facilitator question
of the form *"what did you get wrong?"* can be answered from a record rather than from memory.

**Why keep this at all.** Two reasons, and the second is the real one.

1. The corrections are scattered across commit messages, `FINDINGS.md`, `METHODOLOGY_REVIEW.md`
   and `state.md`. Scattered is the same as lost.
2. **This project's whole thesis is that a plausible-looking number can be an artifact of how
   it was measured.** A version of that project which quietly fixed its own measurement
   artifacts would be making the reviewer's argument for them. The corrections below are not
   an embarrassment to be minimised in the write-up; several are direct evidence for the
   thesis, produced by the method the thesis recommends.

Format: what was claimed → what is true → how it was caught → what it changes.

---

## C1 — Hand-rolled Gibbs sampler for the variance components
**Date:** Phase 1 · **Severity:** caught before it touched any result

**Claimed:** a hand-written Gibbs sampler could estimate the variance components without the
PyMC/PyTensor stack (which needs a compiler the Windows dev machine lacks).

**True:** it failed its own validation — returned `R = 2.8e10` on synthetic data generated at
`R = 1.0`.

**Caught by:** the validation-on-synthetic-data step, which existed because the design
simulation had already established what the right answer was.

**Changes:** sampler deleted; PyMC on the Linux pod used instead. David had asked "why are we
not just using the GPU for this analysis?" before I wrote it — that was the correct call and
should have been taken first. **Write-up value:** an argument for validating an estimator
against a known-answer simulation before pointing it at real data.

---

## C2 — Direction of the pooled-residual prediction
**Date:** Phase 1 · **Severity:** wrong prediction, reported as wrong

**Claimed:** `ANALYSIS_PLAN.md` argued that pooling the residual variance across methods would
**inflate** R, so method-specific residuals were mandatory.

**True:** pooling **deflates** R, consistently, by 4–16%.

**Caught by:** running the pre-specified sensitivity analysis both ways.

**Changes:** the pre-specified correction stands and still matters — but not for the reason
given. Reported as-is in `FINDINGS.md §2` rather than quietly re-derived. **This is the
standard the other predictions are held to.**

---

## C3 — "Kirgis's pattern is absent, so it fails to replicate"
**Date:** 2026-08-08 · **Severity:** high — this was briefly the project's headline

**Claimed:** the individualizing-over-binding pattern is **absent** in ≤14B open models; raw
mean gaps ≈ 0 (−0.13 to +0.03) under every method, so it does not replicate.

**True:** **the raw gap cannot adjudicate the claim at all.** The human baseline has its own
foundation structure — humans rate his group A at 2.661 and group B at 2.380, a **+0.281**
difference — and models compress toward mid-scale (slopes −0.27 to −0.71). Compression pulls
higher human ratings down *more* than lower ones, so **pure compression predicts a NEGATIVE
raw gap with no moral content whatsoever.** A raw gap of ≈ 0 therefore sits *between* the
compression prediction and Kirgis's, and settles nothing. Compression-adjusted, the gap is
**+0.070 to +0.106** — weakly *in his favour*.

**Caught by:** David asking for a double-check before moving on. It would not have been caught
otherwise; nothing in the automated output flagged it.

**Changes:** verdict became **SUGGESTIVE, not established, in either direction**. Also checked
grouping-robustness, which produced a point worth keeping: **Kirgis's own grouping (Liberty
with individualizing) is the most favourable to his claim**, and the canonical Care+Fairness
grouping is more negative still — so he did not gerrymander beyond what the data supports.
The method-agreement finding (ρ = 0.84) is untouched.

---

## C4 — F6's first automated verdict conflated two different failures
**Date:** 2026-08-08 · **Severity:** medium, caught within the same session

**Claimed:** the audit script printed *"the pattern is NOT uniformly method-stable... the
confound bites his conclusion."*

**True:** the four methods **agreed with each other** at ρ = 0.84. *Pattern absent* and
*pattern method-unstable* are different findings and the verdict logic had merged them.

**Caught by:** reading the numbers under the verdict instead of the verdict.

**Changes:** verdict logic rewritten to state the two readings separately. **Write-up value:**
a concrete instance of an automated summary being confidently wrong about its own data.

---

## C5 — F7's first verdict was a null by design
**Date:** 2026-08-08 · **Severity:** medium

**Claimed:** ρ = −0.17, "no clear leakage" from refusal into label-scoring mass.

**True:** the aggregate was dominated by Llama-3.2-1B, a **uniform refuser** — a model that
declines everything has uniformly low mass and therefore **zero within-model deficit by
construction**. The test had no power where it was being applied. Run between models instead:
**ρ = −0.60, n = 20.**

**Caught by:** asking why a strongly predicted effect was absent, rather than accepting the
null.

**Changes:** the audit now runs at two levels. Tempered again on a second pass after
Mistral-7B turned up with 0% non-answer but mass 0.078 — a format mismatch, not refusal — so
**mass flags problems without identifying which one**.

---

## C6 — "String scoring retains 0.22 mass against label's 0.81"
**Date:** 2026-08-08 · **Severity:** high — **withdrawn**, was half of F1's evidence

**Claimed:** v1 string scoring was mismeasuring, partly because it retained far less
probability mass than label scoring.

**True:** **the two numbers are not the same quantity.** v1 ran `length_normalise=True`, and
`expectation()` computes mass from whatever scores it is handed — here per-token *mean*
logprobs. So v1's string "mass" is `sum_k exp(mean logprob)`: a sum of five **geometric
means**, with no probabilistic reading. Label's mass came from raw logprobs and genuinely
*is* a probability. A value near 0.2 is the **expected magnitude** for a sum of five geometric
means and implies nothing about misalignment.

**Caught by:** writing known-answer tests for the v2 scorer. Not by analysis — the number had
already been through three documents.

**Changes:** comparison **withdrawn** from `METHODOLOGY_REVIEW.md`, `FINDINGS.md`,
`METHODS_EXPLAINER.md`. F1's other leg is independent and untouched — models write
`3: Very wrong` when asked — so F1 now rests on one argument instead of two, and it is the
stronger of the pair. **P1 and P4 both used the withdrawn quantity as a baseline and were
amended** (see C8). v2 fixes the underlying issue: its primary is the logsumexp of raw
sequence logprobs, so mass is a real probability and label/string masses become comparable
for the first time.

---

## C7 — "internlm's string arm failed because its tokenizer merges across the join"
**Date:** 2026-08-08 · **Severity:** medium — **falsified**

**Claimed:** internlm2_5-7b-chat lost all 116 string rows because appending the option text
caused the tokenizer to re-merge the final prompt token, breaking v1's boundary assumption.

**True:** **internlm's tokenizer is concatenative on this prompt** — longest-common-prefix
shift is 0 for all three surface forms, verified locally. So no merge occurred. Its rows show
`n_options_found = 0` and `logprob_mass` exactly `0.0`, which is the signature of v1's
`len(ids) <= n_base` guard firing, i.e. vLLM's tokenization was **shorter** than the local
one. **The exact cause remains unverified** and needs the pod; the `tokenization_probe` added
to `run_experiment.py` will settle it on the next run.

**Caught by:** the real-tokenizer arm of `test_conditions_v2.py --online`.

**Changes:** stated as unverified rather than asserted. v2 does not depend on the answer — it
measures the boundary between two id sequences vLLM itself produced, so the entire
local-vs-engine class of mismatch is gone rather than diagnosed. **Related, and separately
verified:** 12 of 30 roster models have a chat template that emits BOS *and* a tokenizer that
adds another, so v1's locally-computed boundary was off by one on those — and under length
normalisation that off-by-one does **not** cancel.

---

## C8 — Two registered predictions rested on a withdrawn quantity
**Date:** 2026-08-08 · **Severity:** procedural, and the handling is the point

**Claimed:** P1 (full option line raises string mass above the Phase-1 value of 0.22) and P4
(cloze retains more mass than Phase-1 string scoring).

**True:** both baselines are the quantity withdrawn in C6, so **neither is evaluable as
written**. Worse, both would have been **trivially satisfiable** — v2's mass is a genuine
probability, so "greater than 0.22" could be achieved by the change of estimator alone,
independent of whether the new probe is better aimed.

**Caught by:** checking, after C6, which downstream claims depended on the withdrawn number.

**Changes:** both **amended, not reworded**. Original text left intact with a dated amendment
block — a registered prediction that gets quietly edited is not registered. Replacements are
strict **within-v2** contrasts where identical machinery runs on both sides, each with an
explicit falsifier:

- **P1′** `string_line` mass > `string_bare` mass for a majority of models.
- **P4′** `cloze` mass > `string_bare` mass for a majority of models.

**P2 needed no amendment and remains the prediction that matters** — it concerns model
*ranking* (ρ), never mass. Same for P4's ranking half.

---

## C9 — The test suite was silently reverting the model roster
**Date:** 2026-08-08 · **Severity:** high — a live reproducibility threat, caught by accident

**Claimed:** implicitly, throughout — that the roster was N=30 after the Phase-2 expansion,
and that running the test suite was a read-only act.

**True:** **every `pytest` invocation reverted `config/models.yaml` from 30 models to 20.**
`test_shows_help_without_a_gpu` runs every script in `scripts/` with `--help` to prove it can
print usage without a GPU. Two scripts had no argparse, so `--help` was an ignored argv entry
and the scripts simply **ran**. `add_phase2_models.py` re-added the Phase-2 models;
`build_model_roster.py`, alphabetically later, regenerated the roster from a hard-coded N=20
list and wiped them.

**The worse half.** `build_model_roster.py` re-pins every revision SHA by fetching the
*current* one from the Hub. Had any upstream repo moved, the pins backing the committed
Phase-1 manifests would have silently changed — destroying reproducibility of the archived
results, with a green test suite and no error. The file's own header says *"do not regenerate
after confirmatory data exists (it would invalidate the run manifests)"*, and the test suite
was doing precisely that on every run.

**Caught by:** a test failing for what looked like an unrelated reason. `pytest -q` passed,
then the same suite failed moments later — the roster had shrunk between runs. The first
instinct was to blame OneDrive sync; watching the idle file for 45 seconds ruled that out and
pointed at the test run itself.

**Changes:** both scripts now take argparse and refuse to act without `--write`;
`build_model_roster.py` additionally refuses to *shrink* the roster without `--force`, since
that is the specific way the additions were being lost. Added
`test_help_sweep_does_not_modify_any_tracked_file`, which closes the **class** rather than the
instance — it asserts the `--help` sweep leaves the working tree untouched, so any future
script that forgets argparse fails there regardless of what it does.

**Write-up value:** the most concrete cautionary detail the project has. A verification step —
running the tests — was itself corrupting the artefact being verified, and it was invisible
because the corruption restored a *plausible* earlier state rather than producing garbage.
That is the same failure shape as the measurement artifacts the project studies.

---

## C10 — The analysis dataset did not reproduce from its own inputs
**Date:** 2026-08-09 · **Severity:** medium — no result moves, but reproducibility was broken

**Claimed:** implicitly, that `results/derived/analysis_long.csv` is a deterministic function
of the raw CSVs — rebuild it and you get the same file.

**True:** rebuilding it produced **28 differing rows** with no code change. The cause is one
line in `build_analysis_data.py`:

```python
dominant = max(set(ft), key=ft.count)      # summarise a sampled cell's failure types
```

On a **tie**, `max()` returns whichever element it encountered first while iterating the
**set**, and CPython randomises string hashing per process. Demonstrated directly: for the
gemma-2-2b item-43 sampled cell (4 `ok` / 4 `unparseable` / 2 `refusal`), `PYTHONHASHSEED=1`
yields `ok` while `PYTHONHASHSEED=2` yields `unparseable`. Ties are *common*, not exotic —
k=10 splits evenly all the time.

**Caught by:** parameterising the builder for v2 and noticing the v1 output no longer matched
the committed file. I had seen a smaller version of this diff earlier in the session and
**dismissed it as float-formatting noise without checking** — that dismissal was wrong, and
the second look only happened because the diff reappeared at a different size.

**Changes:** ties now break by an explicit severity order (`ok` < `unparseable` <
`empty_output` < `refusal`), which is deterministic *and* more honest — a cell that is half
unparseable should not be summarised as `ok`. Verified: five different `PYTHONHASHSEED`
values now produce a byte-identical file.

**Scope, stated precisely so this is neither over- nor under-sold.** Only the descriptive
`failure_type` column was affected. `score`, `n_replicates` and every exclusion decision come
from `usable` and `rate` and never touch `dominant`, so **no analysis result changes**. What
was actually broken was the claim that the dataset regenerates from its inputs. The reason it
still matters: the identical defect in a column that *did* feed the model would have been
completely invisible, and the near-miss was only caught by accident.

---

## C11 — The MCMC seed for the primary estimand was randomised per process
**Date:** 2026-08-09 · **Severity:** high — `variance_ratio.csv` could not be regenerated

**Claimed:** implicitly by `analyse_variance_ratio.py`'s own docstring — *"Nothing in this
file decides anything"* — and by committing `results/derived/variance_ratio.csv` as a
reproducible artifact.

**True:** the MCMC seed was `abs(hash(tag)) % 10000`. CPython randomises string hashing per
process, so **every run used different seeds**. `verdict()` does decide: it is a banded
classification of the 95% interval, and per `FINDINGS.md` all seven intervals straddle a band
boundary — exactly the configuration where a small posterior shift can flip the label. So the
committed R medians, intervals and verdicts were not a function of `analysis_long.csv` alone.

**Caught by:** auditing the codebase for siblings of C10 immediately after fixing it. Nothing
noticed on its own — and this one is worse than C10, which touched only a descriptive column.

**Changes:** seed derived with `hashlib.sha256`, matching the hashing already used in
`conditions.py`. Added `--seed-audit N`, which refits **every foundation under N explicit
seeds** and reports the spread of `R_median` plus whether `verdict` is constant. The magnitude
is being **measured, not assumed** — if any verdict flips, the bands are unstable at this draw
count and the honest response is more draws plus a stated caveat, not a chosen seed.

**Also fixed alongside:** `mcmc_permutation_null.py` wrote rows in `as_completed` order, which
depends on process scheduling and on `os.cpu_count()`. Values were seed-safe; row order was
not. Sorted before every write.

**The systemic response, which is the real fix.** `tests/test_determinism.py` now (a) rebuilds
the analysis dataset under two different `PYTHONHASHSEED` values and asserts byte-identical
output, for both harnesses; (b) statically rejects builtin `hash()` and `max(set(...))`
anywhere in `scripts/`; (c) asserts that builtin `hash()` really is unstable on this
interpreter, so nobody later "simplifies" `stable_seed()` back. **Verified by deliberately
reintroducing the C10 bug: three tests fail, and pass again on restore.** Two of eleven
corrections were found by luck; this is the check that would have caught both.

---

## C12 — The primary analysis wrote v2 results over the committed v1 file
**Date:** 2026-08-09 · **Severity:** medium — caught immediately, no published number affected

**Claimed:** that `analyse_variance_ratio.py --data analysis_long_v2.csv` would write a
v2-named output, because I said so when adding the `--data` flag.

**True:** the versioned-output patch **never applied**. A heredoc `replace()` failed to match
and I did not verify it, so the script kept an unconditional
`OUT / "variance_ratio.csv"`. On the pod the 31-model v2 run therefore **overwrote the
20-model v1 file** — same filename, completely different sample, nothing visibly wrong.

**Caught by:** the batch's own inventory step reporting `variance_ratio_v2.csv MISSING` while
the log said the fit had succeeded. Had I not written that inventory, the natural reading of a
successful log plus an existing `variance_ratio.csv` would have been "it worked".

**Changes:** output name now follows the input name, with a comment recording why. The local
v1 file was never touched (verified clean against git), so `FINDINGS.md` remains sourced from
genuine N=20 results, and the fetched v2 results were saved under the correct name.

**The pattern worth noticing.** This is the third defect in two days caused by *an edit I
believed had applied but never verified* — C10 and C11 were found by auditing, this one by an
inventory check. The lesson is not "be careful with heredocs"; it is that **a patch is not
applied until something asserts it applied.** The `--suffix`/`--data` plumbing in
`build_analysis_data.py` was verified by rebuilding and diffing; this one was not.

---

## C13 — the QA gate never passed on the v2 collection, and one of its checks inspected zero rows

**Claimed.** `scripts/validate_results.py` opens with "Methodological QA over the collected
results. **Run before ANY analysis.** … Exit 0 = data is analysable." The v2 analysis proceeded,
so the implication is that it passed.

**True.** It never passed on v2, and could not have. `load()` globbed `results/raw/*.csv`, which
spans **both** collections — the 20 v1 files and the 31 `_v2` files — and pooled them into one
run of "51 models" checked against the hard-coded v1 condition list
`["label", "string", "greedy", "sampled"]`. v2 renamed that arm to `string_line` / `string_bare`
and added `cloze`, so every one of the 31 v2 models failed §1 with
`conditions absent: ['string']` and the script exited 1 on the whole collection.

Worse than the false negative: **§6, the token-boundary check, filtered `condition == "string"`.
On v2 rows that matches nothing, so it iterated an empty list and printed its pass line having
inspected zero rows.** A check that cannot fail is not a check. The same applied to §5's mass
check, which only ever looked at `label` and `string`, and so never examined `string_bare` or
`cloze` — the two arms with ~0.3% and ~4% retained mass, i.e. exactly the arms where the
grok-3-style integrity question is sharpest.

**How caught.** Not by luck this time. While adding the constancy gate (a named debt) I read
`load()` to find where to hook in, saw the bare glob, and ran the script — which had apparently
not been run against v2 at any point.

**What it changes.** No published number moves: the analysis path (`build_analysis_data.py`)
does its own exclusion handling and was fixed separately in C12. What changes is the *evidential
status* of every v2 number — they were produced from data that the project's own gate had
rejected, and the write-up cannot claim "QA passed" without this fix. Now fixed:
`--suffix {"",_v2}` selects one collection (the C12 pattern), conditions/string-arms/mass-arms
are keyed off it, §6 reports how many rows it actually inspected, and the prompt invariant now
asserts the *structure* rather than uniformity — the five fixed-prompt conditions must share a
sha, and **cloze must not**, because a cloze arm that shares the fixed prompt is string scoring
with a different label.

Running the fixed gate on v2: §1–§9 pass; §10 (new) raises **1 blocking and 14 warnings**.

**The pattern.** Same shape as C12 — a path that silently spanned two collections because it was
never versioned. C12 was the write side, C13 the read side. Both existed simultaneously; fixing
one did not surface the other, because nothing cross-checked them.

---

## C14 — I retired one over-claim by making another, and caught it an hour later

**Claimed.** `LIMITATIONS.md` §5, `references.md` and a commit message, all written 2026-08-10:
*"models treat the non-moral control exactly as the compression line predicts"*, supported by an
excess of −0.040 with a bootstrap CI of [−0.327, +0.246]. Presented as retiring the
"models over-moralise Social Norms" claim outright — *"there is nothing left to report"*.

**True.** The number is arithmetically correct and close to meaningless. It comes from fitting
`model = a + b·human` on the 100 moral items and evaluating it at the control's human mean of
0.19. But:

- **The moral items span 1.40–3.80. The control items span 0.00–0.50. The overlap is ZERO**, with
  a 0.90-point gap containing no observations. It is an extrapolation 1.2 units past the edge of
  the data, presented as though it were a fit.
- **The relationship is not linear over the observed range.** `b` = 0.678 on the lower half,
  **1.226** on the upper half. Fit the upper half and the prediction at 0.19 is **−0.53** — off
  the scale entirely.
- So the residual excess ranges from **−0.08 to +1.58** depending on which subset you fit, a
  choice with no principled answer. **It is not identified.**

**How caught.** By doing the *next* task rather than by re-reading. Propagating the baseline
measurement error meant asking how sensitive the fitted line is, which meant looking at where
the line was being evaluated, which made the extrapolation obvious. The σ-sensitivity table was
the tell: the excess swung −0.040 → +0.546 across a plausible σ range, which is not how a stable
estimate behaves.

**What it changes.** The original claim — "models over-moralise Social Norms" — **stays
withdrawn**, and that part was never in doubt: the control sits at the floor, any compressive
measurement of a floor value reads high, and this follows from the floor alone with no
extrapolation. What is withdrawn is my *stronger converse*. The honest position is now two
statements, not one: **the raw gap is uninformative, and the residual is unidentified.** The
instrument cannot resolve the second, because Clifford designed the control items to sit at the
floor and nothing bridges the distance to the moral items.

**The pattern, and it is not the same as C1–C13.** Every previous correction was a defect in
code or process. This one is a defect in *inference*: the arithmetic was right, the diagnostic
was absent, and the write-up voice was confident. The lesson is narrow and worth keeping —
**an extrapolation should never be reported without its range check**, and "the CI contains
zero" says nothing about whether the model producing the CI applies where it was evaluated.

---

## Standing note for the write-up

*(Written when the log ran to C14. The tally below is unchanged for C1–C14; C15–C19 are
counted in the updated tally at the end of this file.)*

Seven of these twelve were found by a check that was **built in advance** — a validation
simulation (C1), a pre-specified sensitivity analysis (C2), known-answer unit tests (C6, C7),
or a registered falsifier (C8). One (C3) was found only because the author asked for a
double-check. **C9 and C10 were found by luck** — a test failing for what looked like an unrelated
reason — which is exactly the point: nothing was watching for it. **None were found by looking at a result and feeling that it seemed wrong.**

That asymmetry is worth a sentence in the discussion, because it is the project's own thesis
turned on itself: measurement artifacts do not announce themselves, and the only reliable
defence is a check specified before the number exists.

---

## C15 — the primary R included a condition the design excluded, and it roughly doubled the number

**Claimed.** `FINDINGS.md` §2 reports R — defined as `σ²(model:method) / σ²(model)`, a **method**
effect — across the six v2 conditions, and the committed artifacts record `n_methods = 6`.

**True.** One of those six is `cloze`, and **cloze is not a fixed-prompt condition.** It is
defined by removing the option list from the prompt, and the scale clause goes with it. Its
`prompt_sha` differs from the other five on every item — asserted, not assumed, by
`validate_results.py` §2, which requires exactly that difference. So cloze's contribution to the
model × method interaction is part method effect and part **prompt effect**, and nothing in the
model separates them.

**Three documents committed to excluding it, all written before any fit:**

- `config/prompt.yaml:33` — *"Excluded from the primary variance ratio, because a prompt effect
  inside a number defined as a method effect is exactly the error this project audits Kirgis
  for."*
- `METHODOLOGY_REVIEW.md:13` — *"changes two things at once and is excluded from the primary"*
- `scripts/audit_kirgis_pattern.py:196` — excludes it, and states the same reason

`analyse_variance_ratio.py` never implemented it. **Every R this project has published included
cloze.**

**Size of the error.** A moment-estimator decomposition (rough in level, reliable in ratio)
gives, on the N=30 dataset:

| foundation | with cloze | without | change |
|---|---:|---:|---:|
| Authority | 0.867 | 0.386 | **−55%** |
| Care | 0.573 | 0.249 | −57% |
| Fairness | 0.949 | 0.521 | −45% |
| Liberty | 0.680 | 0.381 | −44% |
| Loyalty | 0.402 | 0.196 | −51% |
| Sanctity | 0.594 | 0.386 | −35% |
| *Social Norms (control)* | *0.394* | *0.104* | *−74%* |

**Mean −52%. R is roughly double what the design specifies.** For scale: every sensitivity run
on the pod the same day moved R by 1–15%. This is an order of magnitude larger than all of them.

**Why cloze inflates it so much** is consistent with everything else we know about that arm: it
has the *highest* between-model SD of any condition (0.560 against label's 0.360), and the
*lowest* rank agreement with the others (ρ 0.27–0.50). It behaves least like the rest — which is
exactly what a condition carrying an extra, uncontrolled factor would do.

**How caught.** Not by any check. By a end-of-session sweep asking what had been claimed versus
what had been done — the same class of review that found C13. No test covered it, and the
`n_methods == 6` assertion in `test_artifact_provenance.py` actively **encoded the bug as
correct**.

**What it changes.** The verdicts may not survive: every interval is currently `indeterminate`,
and halving R could move the lower foundations wholly inside the `degraded` band, or move the
control into `robust`. Until a proper MCMC refit is run, **the published R values must be read as
including a prompt-confounded arm.** The fix is in the script (`--include-cloze`, off by
default); the refit is outstanding.

### Verification, run 2026-08-10 after David asked whether this was really true

Four legs, each checked against the data rather than restated:

**1. The falsification test I had NOT run.** If dropping *any* condition cut R by ~50%, the
effect would be "five cells instead of six" and blaming cloze would be wrong. Leave-one-out,
mean across the seven levels:

| dropped | mean change in R |
|---|---:|
| label | **+14%** |
| string_line | **+13%** |
| greedy | **+16%** |
| sampled | **+7%** |
| string_bare | −27% |
| **cloze** | **−52%** |

Dropping most arms *raises* R. Only two lower it, and cloze is twice the next. **Not a
cell-count artifact.**

**2. `string_bare` is not the same problem, and the contrast sharpens the point.** It shares the
fixed prompt — verified per item: `label`, `string_line`, `string_bare`, `greedy` and `sampled`
all carry one `prompt_sha`, cloze carries another. So string_bare's −27% is a *legitimate*
method effect from a genuinely different readout. Cloze's −52% is a method effect plus a prompt
effect. Only one of the two is a design violation.

**3. Cloze's prompt really does differ**, checked in the raw files across models: the cloze
`prompt_sha` never appears in the fixed-arm set on any item.

**4. Cloze really was in the fits.** `analyse_variance_ratio.py` as shipped for the 2026-08-10
refit (`41e48c8`) contains the string "cloze" **zero times** — there was no filter — and every
committed R row records `n_methods = 6`.

### RESOLVED by MCMC refit, 2026-08-11 — and the moment estimator had UNDERSTATED it

112 fits. Measured inflation from including cloze: **mean 2.70×**, against the ~2.1× the moment
estimator implied. The rough check was in the right direction and too kind.

| foundation | R, design-conformant | *with cloze* | ratio |
|---|---:|---:|---:|
| *Social Norms (control)* | **0.133** → `robust` | *0.439* | 3.30× |
| Care | 0.181 | *0.632* | 3.50× |
| Loyalty | 0.181 | *0.485* | 2.68× |
| Sanctity | 0.246 | *0.545* | 2.22× |
| Liberty | 0.317 | *0.756* | 2.39× |
| Fairness | 0.408 | *0.957* | 2.35× |
| Authority | 0.469 | *1.157* | 2.46× |

**Three consequences, and the first is a withdrawn claim.**

1. *"Method perturbation is comparable to between-model variance"* is **not supported**. Design
   conformant, R runs 0.181–0.469 across the six moral foundations — a fifth to a half of
   between-model variance. The stronger sentence was an artifact of the confounded arm.
2. **Five of seven upper credible bounds exceeded 1.0 with cloze; zero do without it.** The
   corrected result is bounded away from "not interpretable" — cleaner than what we had.
3. **The control resolves to `robust`** ([0.067, 0.240]), the project's first non-`indeterminate`
   verdict.

**The error ran in our own favour**, which is why this is the worst entry in this file. Both
numbers are now reported side by side: the gap between them is the largest researcher degree of
freedom in the analysis, and it was found in our own work.

**What remains uncertain, stated precisely.** The −52% comes from a moment-estimator
decomposition, not MCMC. It tracks the MCMC values closely in ordering but underestimates them
in level (e.g. Authority 0.867 vs 1.157). So the *direction and rough magnitude are established*;
the exact corrected R values require the refit, which is outstanding.

**The pattern, and it is the worst one in this file.** C15 is not a coding slip. The project's
central criticism of Kirgis is that he reported a method effect that was confounded with
something else. We did the same thing, in our own primary estimand, having written down three
times that we must not. **Nothing in the codebase enforced a design decision that existed only
in prose.**

---

# The 2026-08-15 sweep — C16 to C19

The four below came from one review, and they share a cause worth naming before the entries.

**Every audit this project had run checked claims against DATA.** Pass 3 of `LIMITATIONS.md`
re-derived 37 numeric claims from the artifacts and all matched. `test_doc_citations.py` checks
that cited paths resolve. `test_headline_numbers.py` guarded one number.

**Nothing checked documents against each other, or status claims against the artifact
directory.** A sentence saying "this analysis remains outstanding" contains no number to
re-derive and no path to resolve, so it is invisible to every check we had. Three of these four
are that shape. The fourth (C16) is the same blind spot in the analysis: every robustness check
varied the *arms*, none varied the *models*.

---

## C16 — half the primary estimand comes from one model, and nothing had looked
**Date:** 2026-08-15 · **Severity:** high — no published number is wrong, but the headline is far
less general than it reads

**Claimed.** `FINDINGS.md` §2 reports R as a property of the roster — "method effects are
roughly a fifth to a half of between-model variance" over 30 analysed models — supported by
sensitivities on scan-parsing (−20% to +3%), the family effect (−2% to +5%) and the arm basket
(C15).

**True.** **Mistral-7B-Instruct-v0.3 alone carries 34.3% of the interaction sum of squares**
across the six moral foundations, against an equal share of 3.7% and a remaining-model average
of 1.6% — **9.3× the average contribution**. Dropping it moves R from 0.348 to 0.171, **−51%**,
in the same order as C15 itself. Per foundation the drop runs −31% (Loyalty) to −66% (Care).

Two statistics, deliberately, because either alone is arguable:

- the **share of raw interaction sum of squares** involves no variance-component estimator, so
  it cannot be moment-estimator truncation;
- the **leave-one-out on R** moves numerator and denominator together, and confirms the numerator
  is doing the work: σ²(model:method) falls 31–66% while σ²(model) moves only +3% to +10%.

**Why it is not a coincidence, and this is the part that matters.** Mistral-7B is the model
`LIMITATIONS.md` §3 records at **label retained mass 0.008**. Its `string_bare` mean is 1.53
against `greedy` 3.45 — a 1.9-point swing on a 0–4 scale. So C16 and the pairwise-R tier
structure in `FINDINGS.md` §2 are the same finding from two directions: **the method effect is
carried by cells the design can barely measure.** The tier table says it arm-wise, C16 says it
model-wise, and neither had been connected to the other.

**Caught by:** an external review asking whether R was robust to model composition — a question
no check in this repo could have answered, because the leave-one-out machinery existed
(`controls_v2.md` §4, `moment_R`) and had only ever been pointed at conditions.

**Changes.** Leave-one-model-out is now a permanent section of `analyse_controls.py` (§5) rather
than a one-off. `FINDINGS.md` §2 and §7 carry it; §1 carries it in the one-paragraph version.
**No number is withdrawn** — R is what it always was — but any write-up quoting the pooled R
without the concentration is quoting a roster-level statistic for something closer to a
few-model phenomenon. **Write-up value:** the strongest available illustration of the project's
own thesis, since it is a case where the number is arithmetically correct and the *unit of
generalisation* is wrong.

---

## C17 — C15 survived in a second script, because the test written for it guarded only the first
**Date:** 2026-08-15 · **Severity:** medium — the conclusion holds; the enforcement claim did not

**Claimed.** `test_design_commitments.py` was written after C15, and its docstring states the
lesson: *"The general failure is not 'we forgot about cloze'. It is that a commitment recorded
only in prose has nothing enforcing it."* `METHODOLOGY_REVIEW.md` F9 marked the permutation-null
deviation **RESOLVED**.

**True.** Three scripts compute R. The test asserted against **one**. `mcmc_permutation_null.py`
had no cloze handling at all, so the 700-fit null cited in `FINDINGS.md` §2 was fitted on
**six arms** and compared against a five-arm observed R. F9 additionally quoted the observed
range as "0.34–1.08", which is the with-cloze basis; design-conformant it is 0.133–0.469.

**What it does not change.** A permutation null collapses to ~0 under *any* basket — that is
what makes it a calibration check rather than an inferential quantity — and 0.001 against 0.18 is
not a margin a basket change can close. **The calibration conclusion stands.**

**What it does change.** The claim that the C15 class was closed. It was not; it was closed for
one instance.

**Caught by:** reading the whole of `mcmc_permutation_null.py` rather than trusting the test
that existed to cover it.

**Changes.** Cloze excluded by default in `mcmc_permutation_null.py`, with `--include-cloze` and
a `_withcloze` filename variant (the C12 pattern). `test_design_commitments.py` now
**parametrises over all three scripts that compute R**, and any script added later that computes
R must be added to that list. The committed null artifact is **not** refit — 700 MCMC fits of
pod time to move nothing — and the six-arm basis is disclosed in `FINDINGS.md` §2 instead of
being silently corrected.

---

## C18 — a stranded table kept two superseded numbers in circulation for five days
**Date:** 2026-08-15 · **Severity:** low in effect, high in irony

**Claimed.** `FINDINGS.md` §3 prose described the genuinely distinct readouts as `string_bare`
(ρ = 0.451 with label) and `cloze` (0.404); §8 scored P4r as "FALSIFIED — ρ 0.269 vs 0.404"; §5
and `METHODOLOGY_REVIEW.md` F6 gave the compression-adjusted gap as +0.077 to +0.179.

**True.** All of those are **pre-correction bases**. Five header-less table rows were stranded in
§3 when the table above them was recomputed on the six moral foundations — a remnant carrying
N=31, control-pooled values — and the prose went on quoting them. On the current basis:
label~string_bare **0.415**, label~cloze **0.374**, string_bare~cloze **0.226**. The adjusted-gap
range is **+0.081 to +0.187**; the +0.077 to +0.179 figure was reproduced exactly by re-running
the audit at N=31 with no exclusions, which identifies it beyond doubt.

**A fourth instance, found 2026-08-15 while rewriting the README.** `label ~ string_line` is
quoted as **ρ = 0.969** in `FINDINGS.md` §3, `LIMITATIONS.md` §6, `METHODOLOGY_REVIEW.md` F1 and
the P2 outcome row of `state.md`. That is the seven-pooled figure; on the six-foundation basis it
is **0.964**. It supports the "three independent readouts, not four" claim, which is unaffected —
0.964 and 0.969 both mean *the same measurement* — but it is the same stale basis in four more
places, and it shows the sweep that produced C18 was not exhaustive.

**Nothing reverses.** P4r is still FALSIFIED (0.226 vs 0.374). P2 is still SUPPORTED. The
"three readouts, not four" finding is unaffected. The direction and every verdict are unchanged.

**Why it is in this file anyway.** This is the error class the project polices in others: a
number that stays in circulation because the correction reached the table and not the sentence.
The §3 main table was correct throughout; only the prose reading from the ghost was wrong.

**Caught by:** an external review recomputing every ρ in the document from
`analysis_long_v2.csv`, which is the check `test_headline_numbers.py` performed for exactly one
of them.

**Changes.** Fragment deleted. All quoted ρ corrected with the old values recorded inline.
`test_headline_numbers.py` now verifies **every cross-method ρ quoted in prose** against the
data, not just the headline — closing the class, in the C9 style.

---

## C19 — the limitations document was five-sevenths wrong about its own outstanding work
**Date:** 2026-08-15 · **Severity:** medium, and the direction is the surprising part

**Claimed.** `LIMITATIONS.md` "What would actually change the conclusions" listed seven items of
future work. §1 said *"The R refit still needs a pod and remains outstanding."* §13 said *"The
family random effect was specified (F3) and never fitted. Until it is, the intervals on R are
narrower than they should be."*

**True.** **Five of the seven were completed on 2026-08-10–11**, and `FINDINGS.md` had been
reporting their results ever since. `refit_summary.txt`, timestamped 2026-08-10T21:03:02Z, names
`variance_ratio_v2_noscan.csv` and `variance_ratio_v2_family.csv` and prints both tables. Item 4
of the list ("verify greedy determinism") was contradicted by §12 of the *same file*, which opens
with a box headed "RESOLVED 2026-08-10".

Three further pre-specified commitments were found unexecuted on the same sweep, and unlike the
scan omission — disclosed prominently as §1 — none had been disclosed at all:

| commitment | status found |
|---|---|
| `ANALYSIS_PLAN.md:191` / `state.md:435` — report with and without exclusions, **plus a table of what was dropped** | fits existed, never reported; table never produced |
| `state.md:444` — achieved N reported with its simulated classification accuracy | never stated for N=30 |
| `state.md:761` — refusal >10% cells flagged, analysis run with and without | flagging done; analysis **substituted** by the MNAR audit, substitution never declared |

**The direction is the point.** This document was **understating the work done** — the opposite
of the failure mode a reader guards against, which is exactly why nobody looked. A limitations
section that claims less than it did is still inaccurate, and a facilitator reading §13 next to
`FINDINGS.md` §2 sees two documents disagreeing about whether an analysis exists.

**Caught by:** an external review checking pre-specified commitments and status claims against
the artifact directory — a sweep this project had never run, because every prior pass checked
claims against **data** and a stale status assertion has no number to re-derive.

**Changes.** The list is rebuilt into "done since this list was written" and "genuinely still
outstanding" (four items). §1 and §13 carry dated correction boxes with the results they had been
denying. The excluded-cell table and the with/without comparison now exist
(`scripts/report_exclusions.py` → `results/derived/exclusions_v2.md`), and the with/without
sensitivity turns out to be **−21% to +26%**, larger than either sensitivity `FINDINGS.md` was
reporting as "the sensitivities". Achieved N is now reported with its simulated accuracy, which
**explains P7's failure** better than P7 did: the observed R values cluster at the 0.25 band
boundary, where B2 puts classification accuracy at 0.51 regardless of N. The refusal substitution
is declared as §15b.

**The standing lesson, and it generalises past this project.** Verification effort concentrates
where errors are expected. Every check here pointed at numbers, because numbers are where a
reviewer looks — so the errors accumulated in prose status claims, which nothing was watching.
**A document's account of what it did needs a check as much as its arithmetic does.**

---

## C20 — a "do not cite until verified" instruction was violated in seven places, including a registered prediction's basis
**Date:** 2026-08-15 · **Severity:** high — this is the project's hardest rule failing on its own record

**Claimed.** `references.md` opens: *"Every entry below was verified by fetching or searching the
source, not recalled."* On 2026-08-10 it withdrew two claims about arXiv:2403.00998 — "no single
method is best across all models" and "method choice matters more for weaker-performing models" —
because neither is in the abstract, and instructed in bold: **"do not cite either until the full
text is read."**

**True.** Both were cited anyway, in **seven places**, and the file recording the ban was the only
one observing it:

| location | what it says |
|---|---|
| `state.md:676` | **P6's registered basis** — "arXiv:2403.00998 reports method sensitivity is larger for weaker models" |
| `state.md:779` | "arXiv:2403.00998 finds scoring method matters more for weaker models" |
| `LIMITATIONS.md` §22 | "consistent with arXiv:2403.00998's result that…" |
| `METHODOLOGY_REVIEW.md` F4 | "arXiv:2403.00998 **predicts** method sensitivity *shrinks* with capability" |
| `THE_NEXT_EXPERIMENT.md` | both withdrawn claims, verbatim |
| `analyse_scale.py` ×2 | docstring and the P6 verdict string, "which **reports** larger method sensitivity for weaker models" |

**Resolved by reading the paper**, which is what should have happened on 2026-08-10. PDF fetched
and read 2026-08-15. **Both claims are in the body — and the second is far weaker than every one
of those seven citations implies.** p.5, verbatim:

> "There is no strong evidence for a single method delivering supreme results for all models…
> **Judging from visual inspection**, the choice of method (and score) seems to matter more for
> models which overall perform worse than for the best performing models."

Three things that no citation carried: it is prefaced **"Judging from visual inspection"** — no
test, no effect size, no interval; it rests on **four models** (two 175B, one 7B, one 3B); and it
concerns models that **perform worse on the task**, not models that are *smaller*. The
size-versus-performance slippage is ours, not theirs.

Claim 1 also needs care: label scoring won for three of their four models and their Discussion
calls it *"best and most stable"*, so the paper supports "no method wins universally, and label
scoring is a good default" — **not** "all methods are equally arbitrary."

**What it changes.** **P6's outcome is untouched** — it was tested against our own data, never
theirs. What changes is the write-up's description of its prior: *"a visual-inspection remark in
Tsvilodub et al. (2024), treated as a directional prior"*, not *"a published result"*. All seven
sites are corrected; `state.md`'s registered text is left verbatim with a dated amendment block,
following the C8 precedent.

**Caught by:** the document sweep, which read `references.md` and then grepped for what cited it —
the first time anyone had checked the citation record *against the citations*.

**The pattern, and it is the sharpest instance in this file.** `CLAUDE.md`'s hardest standing rule
is *never cite from memory*, and `references.md` exists to enforce it. The enforcement document
was correct, current, and explicit. It simply had no reader. **A rule written in one file and
obeyed nowhere is the same failure as C15**, which is the worst entry here — a commitment in prose
with nothing enforcing it — and it recurred in the part of the project specifically built to
prevent it.

**Incidental, and worth keeping.** The wrong title this file carried until 2026-08-10 —
*"Scoring methods for LLM predictions on multiple-choice tasks"* — turns out to be the paper's
**running page header** on pp.2–8. It was not invented; it was read off the wrong part of the
document. A plausible wrong citation can come from the source itself.

---

## C21 — the corrections count was wrong in this project's own front matter, and two pooled scale numbers were a fourth C18 instance
**Date:** 2026-08-16 · **Severity:** low in effect; it is the *location* that earns the entry

**Claimed.** Three things. (a) `README.md` header, `README.md` §"The corrections record" and
`state.md:48` gave the corrections count as **19** — while this file ran to C20 and its own tally
was headed *"twenty corrections"*. (b) `FINDINGS.md` §4 gave the pooled compression-slope
confound as **+0.4346, p < 0.001** and the pooled adjusted gap as **+0.2455, p = 0.009**;
`LIMITATIONS.md` §15 and `state.md`'s P5 row carried the same +0.4346. (c) `LIMITATIONS.md` §21
read *"two of twelve corrections were found by luck"*, a C14-era denominator.

**True.** (a) Twenty, at the time; twenty-one with this entry. (b) `results/derived/scale_analysis.md`
gives **+0.4004** and **+0.2450, p = 0.013** — verified by re-running `scripts/analyse_scale.py`,
whose output diffs byte-identically against the committed artifact except for one stale
`state.md` → `docs/state.md` path. So the artifact was current and the prose was on the **N = 31**
basis, exactly as in C18. (c) Two of twenty.

**Nothing reverses, and nothing was even close to reversing.** The pooled row is explicitly
labelled *"context only"* in both the artifact and `FINDINGS.md`, and the artifact says in terms
that the pooled fit **is not the test** — models are not exchangeable across families, so a
between-family slope largely measures which families happen to be large. The prediction P5 rests
on the two within-ladder slopes (qwen +0.3243, llama +0.2609), and **those were correct
everywhere**. The compression confound is +0.40 rather than +0.43; it remains large, remains
p < 0.001, and the "raw slopes are roughly a third confound" reading is unchanged.

**Why it is in this file anyway, and it is the same reason as C18 and C20.** The stale numbers
sat in the two documents a reader reaches first. And the count was wrong in the **front matter of
the very document that exists to say the count**: `README.md` advertised nineteen corrections in
its header line while linking to a file listing twenty. A project whose thesis is that a
plausible number can be an artifact of how it was produced had a plausible number about *itself*
in its own headline, for as long as nobody counted.

**Caught by:** a read-through of the whole repository for an external presentation — i.e. the
first time anyone had reason to state these numbers out loud to an audience. That is the same
mechanism as C19 and C20: **every defect since C16 has been found by someone with a reason to
restate the project rather than to re-derive it.** Three separate checks recompute ρ from the
data; none of them counts the entries in `CORRECTIONS.md`, and none of them reads a pooled slope.

**A fourth instance, found minutes later by running the suite the same documents describe.**
`README.md` (×2) and `state.md:51` claimed **304 tests**; `pytest --collect-only` reports
**306**. The suite passes — exit 0, no failures — so nothing about the claim's *substance* was
wrong; the number beside it had simply not been recounted since the last two tests were added.
It is the same defect as (a) in miniature, and it was found the same way: by an outsider
executing the instructions rather than trusting the sentence.

**Changes.** Count corrected to 21 in `README.md` (×3), `LIMITATIONS.md` §21 (×2) and
`state.md:48`. Pooled figures corrected to the artifact basis in `FINDINGS.md` §4,
`LIMITATIONS.md` §15 and `state.md`'s P5 row. Test count corrected to 306 in `README.md` (×2)
and `state.md:51`, and the quoted runtime raised from ~2.5 min to ~5 min to match observation.
`scale_analysis.md` regenerated so its internal path reference resolves.

### The fix went stale within the hour, which is the actual lesson

**This entry first said "no guard is added", and that sentence is now withdrawn.** It was
written on the reasoning that closing the class properly needs a check on the repository's
*self-description*, which did not exist. Then, in the same session, the two figure/deck scripts
were added — and because `test_scripts_are_valid.py` parametrises over `scripts/*.py`, the
suite went **306 → 316**, silently falsifying the "306" that had just been written into
`README.md` as a correction. Adding the guard below took it to **320**.

So the corrected count was wrong again within an hour, twice, without anyone touching a claim.
**A hand-maintained count of a quantity that changes whenever a file is added is stale by
construction**, and three manual fixes in one session is the proof. That retires the "deliberate
admission" framing: the choice was never between a guard and honest disclosure, it was between a
guard and re-breaking the same number indefinitely.

`tests/test_self_description.py` now asserts, all **derived rather than hardcoded**:

| check | source of truth |
|---|---|
| every "N corrections" claim in `README.md`, `state.md`, `LIMITATIONS.md` | count of `## C<n>` headings in this file |
| the C-numbers are contiguous | this file |
| the tally table accounts for every entry | this file |
| every "N tests" claim | `len(session.items)` — what pytest actually collected on this run |

It caught one thing on its first execution, correctly: `state.md:55` reads *This block said
"12 corrections"*, a record of C19. A retrospective statement of a superseded count is not a
defect and must not be "corrected" into a lie about what the block once said, so the guard
allows a claim preceded by explicitly retrospective wording.

**Caught by:** the guard, immediately, which is the first time in this project that a check
found the defect it was written for rather than its author finding it first.

---

## Updated tally, 2026-08-16 — twenty-one corrections

Replaces the C14-era note above, which counted twelve, and the 2026-08-15 note, which counted
twenty.

| how it was found | corrections | count |
|---|---|---:|
| a check **built in advance** | C1, C2, C6, C7, C8 | 5 |
| an audit **for siblings** of a known defect | C11, C13 | 2 |
| **luck** — a failure that looked unrelated | C9, C10 | 2 |
| the author **asking for a double-check** | C3, C5 | 2 |
| **reading the numbers under a verdict** | C4, C12, C14, C15 | 4 |
| **external review** | C16, C17, C18, C19, C20 | 5 |
| **restating the project to an outside audience** | C21 | 1 |

**Not one was found by looking at a result and feeling that it seemed wrong.** That was true at
twelve, at twenty, and it is still true at twenty-one.

**What the last five add to the lesson.** C1–C15 were found from inside the project, and the
checks that found them were all pointed at *numbers*. C16–C21 were found from outside, and four
of them are not number errors at all — they are a document's account of itself drifting from
what the repository contains. **We had built good defences against being wrong about the data
and none at all against being wrong about ourselves.**

**C21 sharpens that by one turn.** It was found not by an audit but by the ordinary act of
**restating the project for an audience** — and what it caught was a headline count that was
wrong in the header of the file linking to the evidence against it. The defences are aimed at
what the data says. Nothing is aimed at what we say we did.

The write-up should say this plainly. It is a sharper version of the project's own thesis than
any of the measurement findings: a claim is only as reliable as the check aimed at it, and we
aimed every check at the half of our claims that was easiest to verify.
