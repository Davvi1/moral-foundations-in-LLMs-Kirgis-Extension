# Why there was a v1, what it showed, and why it was replaced

**This file exists because the v1 artifacts were deleted on 2026-08-10.** Everything below was
true of a collection that no longer sits in the working tree. The evidence is not gone — it is
reachable at the git tag **`pre-cleaning-out-v1`** — but it is no longer underfoot, which was the
point of removing it.

Read this before wondering why `CORRECTIONS.md` keeps referring to a harness you cannot find.

---

## 1. What v1 was

The Phase-1 collection: **20 open-weight models × 116 Moral Foundations Vignettes × 4 scoring
conditions** — `label`, `string`, `greedy`, `sampled` — administered under a single fixed prompt.

It produced a complete, internally consistent analysis: a variance ratio per foundation, a
model-ranking matrix across methods, and the first version of the Kirgis audit. Several of its
numbers are still quoted in the write-up as the N=20 comparison column.

## 2. Why it was replaced

v1 was not discarded for being wrong in its conclusions. It was replaced because **two of its
four conditions were measuring something other than what they claimed**, and both failures were
found by checks rather than by the numbers looking odd.

**The `label` arm was silently broken on roughly a third of the roster.** It looked up the
probability of a single digit token at the first answer position. That assumes the label is one
token (SentencePiece tokenizers encode `"0"` as metaspace + digit, so Mistral, Phi-3 and Yi
found nothing), and that the answer sits at position one (Mistral emits `\n` first, Ministral
emits end-of-sequence, Llama-3.2-1B starts prose). Where those assumptions failed, the arm was
scoring the probability of a newline.

**The `string` arm was scoring a continuation the prompt steers away from.** It scored the bare
phrase `"Very wrong"`, while the models' own greedy output shows their natural answer format is
`"3: Very wrong"` — digit, colon, then phrase. The prompt displays numbered options, so the bare
phrase is not the string the model is trying to produce.

A third problem was found while diagnosing the second, and it is recorded as **C6**: v1's string
"mass" was computed from length-normalised scores, making it a sum of five geometric means
rather than a probability. It was never commensurable with the label arm's mass, and a
comparison built on it ("0.22 vs 0.81") was withdrawn from three documents.

## 3. What v2 changed

- **Forced-continuation scoring.** Append the option text to the prompt and read the log
  probabilities back via `prompt_logprobs`. One mechanism for both label and string arms, no
  top-k truncation, no dependence on what happens to appear in a top-20 list.
- **LCP boundary detection.** Longest-common-prefix between engine-tokenised sequences, replacing
  the assumption that `tokenize(prompt + option)` begins with `tokenize(prompt)`.
- **The string arm split in two.** `string_line` scores the full option line `"3: Very wrong"`;
  `string_bare` keeps the phrase alone as a sensitivity.
- **A cloze arm added**, scoring the options with the option list removed from the prompt. It
  deliberately breaks the fixed-prompt invariant and is therefore **excluded from the primary
  variance ratio** — a decision that was written down three times and not implemented until
  2026-08-10. See **C15**, the most serious correction in the log.
- **Roster grown to 31 models**, spanning 0.5B to 72B.

## 4. What the v1 → v2 comparison bought, and why it was worth keeping v1 alive as long as it was

The predictions below were registered in `scripts/compare_v1_v2.py` **before any v2 data
existed**, and the record is `results/derived/v1_v2_comparison.md`, which survives this cleanup.

| prediction | outcome |
|---|---|
| P1′ full option line recovers probability mass | **SUPPORTED** — line > bare on 31/31 models; means 0.6255 vs 0.0032 |
| P2 the line probe recovers agreement with label | **SUPPORTED** — ρ(label, string_line) = 0.974 against ρ(label, string_bare) = 0.401 |
| P4′ cloze recovers mass over the bare phrase | **SUPPORTED** — 23/31 models |
| P4r cloze ranks models like bare, not like label | **FALSIFIED** — ρ 0.269 vs 0.404, the reverse of the prediction |

P2 is the one that mattered: it established that v1's low label–string agreement (ρ = 0.332) was
**a badly aimed probe, not a genuine construct difference.** Had P2 failed while P1′ held, the
v1 result would have been the more interesting one and would have stood.

**And one finding that exists only because both collections were kept.** Comparing v1 and v2
greedy output on the same 20 models — byte-identical prompts asserted per item, same GPU model,
identical library versions — showed that **greedy decoding is not reproducible across runs**:
raw text differs on 10.56% of cells and the parsed score on 2.28%, mean shift 1.038 on a 0–4
scale, affecting 13 of 20 models. That retired the claim in `METHODS_EXPLAINER.md` §5 that the
non-sampled arms are "like measuring a ruler twice".

> **This finding is now frozen.** `scripts/audit_greedy_determinism.py` compares the two raw
> collections, and the v1 half no longer exists in the working tree. The report,
> `results/derived/greedy_determinism.md`, is committed and stands; regenerating it requires
> checking out the `pre-cleaning-out-v1` tag. That trade was made deliberately: the result is
> recorded, and 20 MB of superseded raw data was making the tree harder to reason about.

## 5. Where v1 numbers still legitimately appear

Deleting the files does not retract the analysis. These remain valid and cited:

- **`FINDINGS.md` §3** keeps a `v1 (N=20)` column in the ranking table — the N=20 comparison is
  what shows the headline ρ moving 0.880 → 0.818 as the roster grew and the scorer was fixed.
- **`CORRECTIONS.md` C1–C12** are largely v1-era. They are the project's record of what it got
  wrong and are load-bearing for the write-up, not historical trivia.
- **`results/derived/v1_v2_comparison.md`**, **`results/derived/string_scoring_diagnosis.md`** and
  **`results/derived/tokenization_boundary_diagnosis.md`** are retained: they are the *evidence for the
  migration*, not v1 results.

## 6. What was deleted

Raw: 20 model CSVs and manifests (`results/raw/*.csv` without the `_v2` suffix), plus
`results/raw_naive_label/` — a v1-era diagnostic collection of naive single-token label scoring.

Derived: `analysis_long.csv`, `variance_ratio.csv`, `controls.md`, `kirgis_pattern_audit.md`,
`refusal_leakage_audit.md`.

Scripts whose only purpose was v1 or a one-shot migration: `merge_labelfix.py`,
`add_phase2_models.py`, `add_phase3_models.py`, `diagnose_string_scoring.py`, `compare_v1_v2.py`.

**Kept despite looking v1-ish:** `scripts/conditions.py`. It held the v1 scorers, but the rest
of the module — `render_prompt`, `option_token_ids`, `expectation`, `parse_digit`, `is_refusal`,
`failure_type` — is shared infrastructure that v2 depends on, and `conditions_v2.py` imports
from it directly. Deleting the module would break the v2 harness. *(The dead scorers themselves
were removed in the second pass — see §7. `run_free` remains, because v2 uses it.)*

Also kept: `reanalyse_kirgis.py`, `results/derived/kirgis_reanalysis.md` and `kirgis_rescored.csv`. Those audit
**Kirgis's own published data**, not our v1 collection, and are unrelated to this cleanup.

---

## 7. Second pass, 2026-08-11 — dead code the V1 deletion left behind

Removing the v1 *data* left v1 *code* stranded. Cleared in a follow-up:

- **`conditions.py` lost `run_label` and `run_string`** — the v1 scorers, uncalled once the v1
  collection was gone. **`run_free` stays**: v2 uses it for the greedy and sampled arms.
- **`run_experiment.py` lost its `--harness v1` branch.** The `harness` *field* survives in every
  raw CSV and manifest, and the provenance tests read it, so the value is pinned to `"v2"`
  rather than deleted.
- **Ten tests exercising those scorers were removed**, and `test_harness_e2e.py` stopped
  parametrising over both harnesses.

**And the finding that made this worth doing.** `pytest.ini` sets `testpaths = tests`, so
`tests/test_conditions_v2.py` and `tests/test_harness_smoke.py` — 613 lines covering the
**live** scorer and harness — had never run in the suite, while ~800 lines thoroughly tested the
harness we had just deleted. **The test suite was inverted.** Both files moved into `tests/`.

Moving them was not sufficient. Their `check()` helper printed `PASS`/`FAIL` and returned; under
pytest that reports success no matter what the check found, so a straight move would have turned
the suite green while covering nothing. `check()` now asserts, and `test_harness_smoke.py` — which
had no `test_*` function at all and would have contributed zero collected tests — gained a real
pytest entry point. Verified by calling `check(..., False)` directly in both files and confirming
it raises.

### Deleted in the same pass

- **`scripts/pod_overnight.sh`** — drove the v2 collection, which is complete.
- **`scripts/pod_analysis_batch.sh`** — superseded by `pod_refit_batch.sh`.
  *Worth recording since the file is gone:* this is where the **verified-teardown pattern**
  originated — check the exit code of `runpodctl stop pod` rather than merely that the binary
  exists. That distinction was written after ~1h44m of idle billing leaked on 2026-08-08, and it
  is referenced in `CORRECTIONS.md`. `pod_refit_batch.sh` carries the pattern forward, plus the
  pull-before-stop guard added on 2026-08-10 after a completed run destroyed its own output.
- **`RESUME.md`** — an operational sequence last updated 2026-08-07, superseded by `FINDINGS.md`
  and by every correction since.
