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

## Standing note for the write-up

Seven of these twelve were found by a check that was **built in advance** — a validation
simulation (C1), a pre-specified sensitivity analysis (C2), known-answer unit tests (C6, C7),
or a registered falsifier (C8). One (C3) was found only because the author asked for a
double-check. **C9 and C10 were found by luck** — a test failing for what looked like an unrelated
reason — which is exactly the point: nothing was watching for it. **None were found by looking at a result and feeling that it seemed wrong.**

That asymmetry is worth a sentence in the discussion, because it is the project's own thesis
turned on itself: measurement artifacts do not announce themselves, and the only reliable
defence is a check specified before the number exists.
