# The next experiment

**Status: SCOPED, NOT STARTED. No data exists. Nothing in this file is a result.**

Written 2026-08-10, at the point where the F5 prompt-variant collection was built, validated,
and then deliberately not run.

This file exists because F5 stopped being an extension of the current experiment and became a
different experiment. That happened the moment the design grew a second instrument. Everything
below is the second study; the current repo is the first one and should be finished and written
up on its own terms.

---

## 1. Why this is deferred, and why that is the right call

The F5 machinery is built and committed. `config/prompt.yaml` holds 12 validated prompt
variants (P00 base + P01–P11); six predictions are registered in `state.md` at commit `bf629c5`,
before any data existed. Nothing here is being abandoned — it is being moved.

The reason is scope, and it is worth stating plainly because the temptation runs the other way:

- **The first experiment is not written up.** The sprint constraint is two days of full-time
  work for the experiment *excluding* write-up. Collection is done (31 models, six conditions,
  21,576 rows). The remaining obligation is prose, not GPUs.
- **The first experiment has unpaid debts** (§8). Several are free — no compute, no pod — and
  every one of them is worth more to the write-up than a new factor is.
- **Adding a second instrument changes the estimand.** With one instrument the question is
  "is this model's profile stable across scoring methods?" With several it becomes "does
  method-sensitivity depend on the instrument?" That is a generalisation claim, needs its own
  design, and cannot be bolted onto a study whose analysis is already fixed.
- **The novelty position changes too**, and not in our favour — see §4. Running F5 as a
  sub-part of experiment 1 would have quietly imported a much larger literature into a paper
  that has not engaged with it.

So: finish experiment 1 with a fixed prompt and an honest statement that it estimates method
variance *conditional on one prompt*. That limitation is already written down
(`METHODS_EXPLAINER.md` §5) and is a better sentence than a half-powered prompt factor.

---

## 2. The question the next experiment asks

Experiment 1 asks: **does the scoring method move the measured moral profile, and the model
ranking, on one instrument under one prompt?** Answer, at N=31: the variance ratio R is
indeterminate in all seven foundations (0.343–1.075), but ρ(label, sampled) = 0.842 — Kirgis's
confound is survivable for rankings, and the four conditions turn out to be three independent
readouts.

Experiment 2 asks the two questions that answer immediately raises:

> **Q1.** Is the scoring-method effect large *relative to* an arbitrary but defensible change of
> prompt wording? If a reviewer can move the ranking as much by rewording the stem as we move it
> by changing the readout, then "scoring method" is not a distinct measurement hazard — it is one
> face of general prompt sensitivity, and the framing of experiment 1 needs qualifying.
>
> **Q2.** Does the answer depend on the instrument? Method-sensitivity measured on the MFV alone
> cannot distinguish "probability readouts are unstable on value-laden items" from "the MFV in
> particular is unstable."

Q1 is F5 as already designed. Q2 is the part that makes this a new study.

**Q1 is the one that can hurt.** Prediction F5-4 in `state.md` commits, before data, to
cross-prompt rank correlation exceeding cross-method rank correlation. The falsifier is live:
if prompt perturbation moves rankings as much as method choice does, experiment 1's thesis is
substantially qualified and must be reported that way. That prediction is registered precisely
so it cannot be reframed afterwards.

---

## 3. The literature, verified

Everything in this section was verified by fetching the source on 2026-08-10 — abstract *and*,
where a number is quoted, the full text. Nothing here is from recall. This is the standard the
rest of the repo is held to and it caught a real problem: the two "template" papers' abstracts
do **not** contain the numbers the F5 predictions are anchored to. The numbers are real, but they
live in the body, and they had to be read there.

### 3.1 The two papers that set the template

**Hua, Tang, Gu, Gu, Wong & Qin — "Flaw or Artifact? Rethinking Prompt Sensitivity in
Evaluating LLMs." arXiv:2509.01790, submitted 1 Sep 2025.** Abstract + §3.2 and Table 1 read.

7 LLMs × 6 benchmarks × **12 prompt templates**, covering multiple-choice and open-ended tasks.
The claim: reported prompt sensitivity is "largely an artifact of evaluation processes" — of
"heuristic evaluation methods, including log-likelihood scoring and rigid answer matching,"
which miss semantically correct answers phrased differently. Under LLM-as-a-Judge, variance
drops and ranking correlation across prompts rises sharply.

The numbers, verified in the body (Spearman, over model rankings across prompts, Table 1):

| Benchmark | heuristic | LLM-as-a-Judge |
|---|---|---|
| ARC-Challenge | **ρ̄ = 0.30** (open-source only) | **0.95** (all 7); 0.92 (open-source only) |
| OpenbookQA | 0.42 | 0.94 |
| GPQA Diamond | 0.15 | 0.90 |
| NarrativeQA | 0.59 | 0.87 |
| MATH | — | 0.96 |
| SimpleQA | — | 0.81 |

Verbatim, §3.2: *"the average Spearman rank correlation across prompts among open-source models
increases from 0.30 (heuristics) to 0.92 (LLM-as-a-Judge), and further to 0.95 when proprietary
models are included."*

**Where our 12 templates came from.** The count is deliberately theirs, so the designs are
comparable. Our variants differ in one respect and it is a constraint they did not face:
**no variant may change the format of the option line `"k: phrase"`**, because `string_line`
scores that exact surface string. Two format variants were written and removed for this reason.
Order may change; punctuation may not.

**The caveat that matters for us:** their most stable arm is LLM-as-a-Judge, which we do not have
and arguably cannot have — there is no ground truth for "how wrong is this vignette," so there is
nothing for a judge to be right about. Their result therefore transfers to us only as a
*contrast between the heuristic arms*, not as a recommendation we can adopt. Their log-likelihood
arm is also a single category, whereas we have four distinct probability readouts, which is where
the refinement lies (§4).

**Kamal, Patwary, Marchiafava, Ray Choudhury & Sen — "Prompt Robustness Is Task-Dependent:
Comparing Objective and Belief-Style Questions in LLM Evaluation." arXiv:2607.05554,
v1 6 Jul 2026, v2 21 Jul 2026.** Abstract + §4.1, §4.2 and Table 2 read.

Opens on exactly this project's premise: *"Survey-style evaluations of large language models
often treat a prompted response as a measure of a model's values or beliefs. This assumption is
particularly fragile when responses are read as evidence of political values, social attitudes,
or beliefs."*

Four instruction-tuned model families × six datasets, split **objective** (MMLU, ARC,
CulturalBench) vs **subjective** (Political Compass Test, ValueBench, World Values Survey), with
wording, framing and format perturbations. Metric: whether the model gives the same answer across
variants. Inference: binomial GEE, with significant effects of model, dataset, prompt category,
and their interactions.

Verified numbers:

- §4.1 — mean consistency **0.849 objective vs 0.787 subjective**; instability rises from 0.151
  to 0.213.
- §4.2 — **option-order perturbation is the worst category**, mean consistency **0.407**,
  splitting **0.485 objective / 0.328 subjective**.
- Table 2 — paraphrase perturbations stay above 0.9. *(The fetched decomposition of the
  paraphrase row was internally inconsistent — an "overall" above both subgroup values — so only
  the qualitative claim is used here. Re-read that table directly before quoting a paraphrase
  figure in the write-up.)*

**This is the template for the multi-instrument half**, and it is also the paper that most
constrains us: the objective/subjective contrast is theirs, and any framing of ours that sounds
like "we show values instruments are more prompt-sensitive" is repeating their result.

### 3.2 The closest neighbour, and it is closer than either of the above

**Shen, Singh, Logeswaran, Lee, Lee & Mihalcea — "Revisiting LLM Value Probing Strategies: Are
They Robust and Expressive?" arXiv:2507.13490, submitted 17 Jul 2025.** Abstract + full text read.

This one was not in `references.md` and it should have been. It compares **three value probing
strategies** that map almost one-to-one onto our conditions:

| Shen et al. | our condition |
|---|---|
| **token logit** — softmax over valid option symbols | **label scoring** |
| **sequence perplexity** — normalised inverse perplexity over options | **string scoring**, length-normalised variant |
| **text generation** — 10 samples at T=1.0, count option selections | **free generation, sampled (k=10)** |

Instrument: World Values Survey Wave 7, 206 questions over 13 topic areas. Seven model families
(Bloomz-7B, Falcon-7B, Mistral-v0.3-7B, Llama-3.1 8B/70B, Llama-3.2-3B, Qwen2.5 3B/7B/14B/72B) —
note the overlap with our roster. Perturbations: prompt style (default / affirmative starter /
one-shot) plus selection-bias variants (reversed option order, alternative labels 0/1/2/3).
Finding: **all three methods show large variance under input perturbation.**

**Read this before writing a word of experiment 2.** The honest summary is that the *set* of
readouts we treat as our design is not novel, and neither is crossing it with prompt
perturbation on a values instrument. Shen et al. did both, a year ago, on WVS.

What they did **not** do, verified against the full text: their metrics are **mismatch rate and
Jensen-Shannon divergence** — within-model distributional agreement. No inter-method model-ranking
agreement is reported. Their Table 2 correlations (0.526–0.933, e.g. mismatch vs option
probabilities r = 0.899) are correlations *between robustness metrics*, not between methods'
model rankings. The ranking estimand is still open, and it is the same gap that survived the QSTN
check.

### 3.3 Already in `references.md`, still load-bearing

- **QSTN — Kreutner, Rupprecht, Ahnert, Salem & Strohmaier, arXiv:2512.08646.** 8 response
  generation methods × 10 open-weight LLMs on ANES/GLES/ATP; recommends against token-probability
  methods. Their criterion is *alignment with human respondents* (simulation); ours is *stability
  of the model's own profile* (measurement). That distinction is what survives, and it survives
  Shen et al. too.
- **Wang et al., Findings of ACL 2024, pp. 7407–7416** — first-token probabilities do not match
  text answers in instruction-tuned models. Direct predecessor for label vs free generation.
- **Rupprecht, Ahnert & Strohmaier, arXiv:2507.07188** — WVS, 11 perturbations, nine models, 167k
  simulated interviews, consistent recency bias. **Occupies generic prompt perturbation on
  normative surveys.**
- **Dominguez-Olmedo, Hardt & Mendler-Dünner, arXiv:2306.07951** — models key on answer ordering
  and labelling rather than semantics.
- **Alzahrani et al., arXiv:2402.01781 (ACL 2024)** — benchmark perturbations including answer
  selection method shift MMLU leaderboard position by up to eight places, reported as Kendall's τ.
  Still the methodological template for the ranking statistic.
- **arXiv:2403.00998** — five methods for determining an LLM's answer choice; no single method
  best; method choice matters more for weaker models. The outstanding overlap check
  (`references.md`, "Open, unverified") is now **blocking** for experiment 2, not deferrable.

### 3.4 Found during this check, relevant to instrument choice

- **Song, Choi, Park, Han, Lee & Jo — "Human Psychometric Questionnaires Mischaracterize LLM
  Behavior." arXiv:2509.10078, 12 Sep 2025.** Eight open-source LLMs; profiles from Likert
  self-report on **PVQ-40/21 and BFI-44/10** vs generation probabilities over value-laden
  responses to everyday queries. The two diverge substantially; within-construct item consistency
  present in questionnaire responses **disappears** in generation probabilities. Attributed to
  explicit lexical cues letting models recognise the construct and answer in a socially desirable
  way. Persona prompts shift questionnaire responses but not realistic-query responses.
  **Implication for us:** it argues the questionnaire format itself is the fragile object, which
  is a deeper challenge to the whole enterprise than the one we are running, and it should be
  cited as a limitation rather than avoided.
- **ValueBench, arXiv:2406.04214, ACL 2024 long paper** (`github.com/ValueByte-AI/ValueBench`).
  44 psychometric inventories, 453 value dimensions. Used as a subjective dataset by
  arXiv:2607.05554. *Author list not yet verified — do not cite it until it is.* Note its native
  pipeline rephrases first-person items into advice-seeking questions and scores with an
  evaluator LLM, which is **not** compatible with our fixed-prompt logprob design without
  modification.

---

## 4. The novelty position, stated narrowly

Written now, before data, so it cannot inflate later.

**Withdrawn.** The original F5 note claimed the crossed prompt × scoring-method decomposition had
not been done, and carried "NOVELTY CHECK REQUIRED". The check was run on 2026-08-09/10 and the
claim is **false**: arXiv:2509.01790 crosses 12 templates with scoring method and measures
Spearman ranking stability; arXiv:2507.13490 crosses three probing strategies with prompt and
option perturbations on WVS. Neither of those is a small overlap.

**Also withdrawn:** any suggestion that our four-condition set is a novel instrument. Three of the
four correspond directly to Shen et al.'s three strategies.

**What is actually left.** Three things, and they are modest:

1. **The ranking estimand on values instruments.** 2509.01790 measures ranking stability but on
   capability benchmarks. 2607.05554 and 2507.13490 use values instruments but measure
   within-model answer consistency (same-answer rate, mismatch rate, JS divergence), not whether
   the *ordering of models* survives. QSTN measures alignment to humans. Nobody in this set asks:
   **if you rank models by their measured value profile, does the ranking survive the readout?**
   That is the question a downstream user of a model-characterisation paper — Kirgis's readers,
   for instance — actually depends on.
2. **Resolution inside the logprob family.** 2509.01790 treats "log-likelihood scoring" as one
   arm. We have four probability readouts (label, string-line, string-bare, cloze) and can test
   whether its "heuristic methods are the problem" conclusion holds *within* that family, or
   whether one probability readout behaves like the judge arm. Experiment 1 already found
   `string_line` and `label` to be near-identical (item-level r = 0.9878) whenever the prompt
   displays the digit→phrase mapping — so the family has internal structure worth resolving.
3. **Auditing a specific published claim.** Experiment 1's spine — testing Kirgis's model
   characterisation against its own scoring confound — has no counterpart in this literature.
   It is a replication-and-audit contribution, not a methods contribution.

**This is transfer-plus-refinement. It is not a new design, and the write-up must say so in those
words.** If a reviewer reads §3.2 and concludes we re-ran Shen et al. on a different
questionnaire, we should have said it first.

---

## 5. Design sketch

Not final. Numbers here are for costing, not commitments.

**Factor A — prompt.** 12 variants, already built and validated in `config/prompt.yaml`:
P00 base, P01/P02 paraphrase, P03 reversed, P04 shuffled, P05 Kirgis instruction, P06 no scale
clause, P07 item-first, P08 terse, P09 polite, P10/P11 system-prompt variants. Constraint: option
line format is invariant.

**Factor B — scoring method.** The 5 fixed-prompt conditions (label, string-line, string-bare,
greedy, sampled k=10). Cloze is **not** crossed with prompt: it is defined by removing the
options, so it changes the prompt by construction. Crossed design is therefore 5 × 12.

**Factor C — instrument.** The new axis, and the one needing the most thought. Selection criteria,
in priority order:

1. *Same response format as the MFV where possible* — a 5-point ordinal scale with fixed labels.
   Instruments with different formats (binary agree/disagree, 7-point Likert, forced-choice
   pairs) confound "instrument" with "response format," and format is exactly what the scoring
   methods are sensitive to. **This is the single biggest design risk in experiment 2.** With
   MFV-vs-WVS alone, a difference between instruments is uninterpretable: content, format and
   scale all moved together.
2. *A human baseline at item level*, so the compression analysis (P5/P6) carries over.
3. *Not already saturated* — WVS is heavily occupied (Rupprecht et al., Shen et al.,
   Kamal et al.), so it is a comparison point, not a headline.

Candidates, with the honest objection to each:

| Instrument | For | Against |
|---|---|---|
| **MFQ-2** (Atari et al. 2023, verified) | same theory as MFV, six foundations, cross-cultural norms | self-report Likert about oneself, not third-party judgment — Song et al. is precisely about this format failing |
| **PVQ-21/40** | established, used by 2509.10078 and 2601.05437 | same self-report objection; no item-level baseline matched to our population |
| **WVS Wave 7** | direct comparability to Shen et al. and Rupprecht et al. | heavily occupied; heterogeneous formats across items |
| **Political Compass** | used by 2607.05554 | not psychometrically validated; would weaken the paper |
| **MFV physical-harm items** (the 16 Kirgis drops) | identical format and scale, free, extends Care beyond emotional harm | not a *different* instrument — a within-instrument content contrast |

**Recommendation: start with the last one and MFQ-2.** The dropped physical-harm items give a
content contrast at *zero* format confound — the cleanest possible test of "does method
sensitivity depend on content" — and MFQ-2 gives a genuine second instrument with the format
confound named up front rather than discovered. Adding a third instrument before the two-instrument
result is in hand is scope creep.

**Models.** All 31 from experiment 1. This was David's explicit call ("I want the full 31") and it
is the right one: the ranking estimand needs models on the axis, and 31 is what makes a rank
correlation worth reporting. The efficiency trick that makes it affordable is that **prompt
variants loop inside the model loop** — weights download once and serve all 12. Download, not
inference, is the cost driver, so 12× the data is not 12× the bill.

**Analysis: rank correlation, not variance decomposition.** Stated flatly because the opposite was
proposed and was wrong. Estimating σ²(model:prompt) from 12 prompt levels would repeat exactly the
error P7 falsified — variance components do not resolve at small group counts, and R is
indeterminate in all seven foundations even at N=31. Both comparison papers use rank/consistency
metrics. So do we. Primary statistic: Spearman ρ between model rankings, following 2509.01790;
Kendall's τ as sensitivity, following Alzahrani et al.

---

## 6. Predictions

Six are already registered in `state.md` at commit `bf629c5`, dated before any P01–P11 data
exists and verifiable in git history: F5-1 (parsing arms less prompt-stable than logprob arms),
F5-2 (option order is the worst perturbation), F5-3 (values less stable than capability
benchmarks), **F5-4 (cross-prompt ρ > cross-method ρ — the headline, with a live falsifier that
would qualify experiment 1's thesis)**, F5-5 (Kirgis's instruction shifts retained mass
differentially between label and string arms), F5-6 (P00 reproduces the v2 collection, which
doubles as the cross-session determinism check left open in `LIMITATIONS.md` §12).

Two refinements from the full-text verification, to be applied to `state.md`:

- **F5-1** is anchored to ARC-Challenge specifically (0.30 → 0.95). Heuristic ρ̄ ranges 0.15–0.59
  across their benchmarks, so the anchor should be a *range*, not a point.
- **F5-3** compares against "0.95, its most stable readout." Two problems: 0.95 includes
  proprietary models (open-source only is 0.92), and their highest is 0.96 on MATH. More
  importantly, 0.95 is the **LLM-as-a-Judge** arm, which we do not have — so the defensible
  comparison for us is against their *heuristic* range, and the prediction should say so.

Instrument-level predictions (Q2) must be registered **before** collection, same discipline.
Nothing about instrument effects is predicted yet, because the instruments are not chosen.

---

## 7. Cost

Experiment 1 spent well under the $100 ceiling; roughly $40 of headroom remained at the time of
writing, and the F5 collection was estimated at ~$20. The 31-model × 12-prompt × 5-condition run
is affordable *because of* the loop-inside-the-model-loop structure. Adding instruments multiplies
inference but not downloads, so a second instrument is cheap; a second *model roster* would not be.

Standing constraint, unchanged: **David creates pods. Claude may start work on an existing pod,
pull results, and stop pods — creating a pod requires an explicit instruction every time.** State
cost before any billable action.

---

## 8. Before any of this — the debts on experiment 1

None of these need a GPU except where marked. All of them improve the write-up more than a new
factor would.

- **Scan-excluded R refit.** The ranking half is done and strengthens the result; the
  variance-ratio half is outstanding. *(Needs a pod — bambi/PyMC need a C++ toolchain the Windows
  box lacks.)*
- **Family random effect** — five Qwens are not five independent draws. *(Pod.)*
- **Hand-code ~200 outputs to validate the refusal regex.** Free. The MNAR audit rests on it.
- **Constancy check in QA.** Free.
- **Social Norms treated as a control, not a seventh foundation** — verified against Clifford
  et al. as a designed non-moral control. Currently entering the variance model as a foundation.
  Free, and it changes a headline sentence: "models over-moralise Social Norms" is better stated
  as "models fail to recognise a deliberately non-moral item as non-moral."
- **Propagate the ±0.2 baseline SE.** Clifford's item means come from n ≈ 30 each; treating them
  as error-free understates uncertainty. Free.
- **Overlap check against arXiv:2403.00998** (`references.md`, "Open, unverified"). Now blocking
  for experiment 2.
- **Add arXiv:2507.13490 to `references.md`** as occupied territory. It is the closest neighbour
  and its absence was a gap in the novelty check.
- **The write-up itself.**

---

## 9. What would make this not worth doing

Recorded now so the decision is not made retrospectively.

- If the §8 overlap check shows arXiv:2403.00998 already reports cross-method **ranking**
  agreement on a values instrument, contribution 1 in §4 is gone and only the Kirgis audit
  remains — which is experiment 1, already done.
- If a second instrument cannot be found whose response format matches the MFV's, the instrument
  factor is confounded with format and Q2 is not answerable as posed. Better to run Q1 alone and
  say so than to run a confounded Q2.
- If experiment 1's write-up shows the ranking result (ρ = 0.842) is the paper's real
  contribution, then the correct next move may be **more models on one instrument**, not more
  instruments — a rank correlation is far more sensitive to N models than to N items.
