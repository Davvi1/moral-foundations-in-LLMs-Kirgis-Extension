# references.md

Every entry below was verified by fetching or searching the source, not recalled.
Anything added later must carry the same standard and note how it was checked.

---

## Target paper

**Kirgis, P. — "Differences in the Moral Foundations of Large Language Models."
arXiv:2511.11790, submitted 14 Nov 2025.** Full text fetched and read.

- Instrument: Moral Foundations Vignettes, 116 items, from Clifford et al. (2015).
  Severity rated 0–4.
- Models: 21, across Anthropic, DeepSeek, Google, Meta, OpenAI, xAI.
- Administration: Expected Parrot survey tool. One API call per question, so no
  question-order effects. Temperature, toplogprobs, topN left at provider defaults.
- **Scoring, the load-bearing detail:** a weighted average over the top three
  exponentiated log probabilities, described as possible only for the non-reasoning
  OpenAI models and the xAI models; every other response is a mean of ten independent
  queries.
- **Estimator vs. provider — CORRECTED 2026-08-07 (repo + paper Table 1, p.4, both read).**
  Not *perfectly* collinear. The actual split: **logprob-scored (6)** = GPT-3.5-Turbo,
  GPT-4-Turbo, GPT-4o, GPT-4.1, Grok-2, Grok-3; **sampled, mean of 10 (15)** = all 4
  Anthropic, both DeepSeek, all 4 Google, all 3 Meta, **plus GPT-4.5 and o3-Mini**. OpenAI
  therefore has models in *both* arms. Collinear for five of six providers; inside OpenAI
  the split is confounded with model identity instead, so it still identifies nothing.
  State it this way — a reviewer who checks Table 1 will catch "perfectly collinear."
- **Renormalisation — RESOLVED 2026-08-07 by reading the paper and the code. They disagree
  with each other.** This is the strongest single fact the go/no-go produced.
  - Printed formula, paper p.4, verbatim:
    `E_score = Σ_{k=1}^{3} s_k exp(ℓ_k) = Σ_{k=1}^{3} s_k p_k`
    **No denominator. Does not renormalise.** The old note was right about this half.
  - Code, `analysis/final_analysis.ipynb` cell 2, `compute_expected_value`: accumulates
    `total_prob` over allowed tokens and ends `return weighted_sum / total_prob`.
    **It does renormalise.** The old suspicion that it might not was wrong.
  - Token set: the provider's **top three of the whole vocabulary**, then filtered to
    `{"0","1","2","3","4"}`, then renormalised over whatever survived — *not* the top three
    among the five valid options. The denominator is a data-dependent subset of size 1–3.
  - **Consequence worth naming:** when only one of the top three is a digit,
    `weighted_sum / total_prob` = k·p/p = **k exactly** — the estimator silently degenerates
    to argmax. His logprob arm is a mixture of a 3-point expectation, a 2-point expectation,
    and plain argmax, decided per item per model. Checkable on his committed
    `data/results/logprob_responses.csv` with no GPU.
- Findings: (1) MFT has explanatory power for LLM moral judgment; (2) models overweight
  care/fairness/liberty and underweight loyalty/authority/sanctity vs. the human baseline;
  (3) providers vary systematically; (4) larger and more capable models move further from
  the baseline.
- Analyses: mean differences by foundation (Fig 2); Spearman rank-correlation matrix
  across foundations (Fig 3); PCA biplot of responses with foundation loadings (Fig 4);
  FrameAxis intensity analysis of justification text using eMFD + Word2Vec (Fig 5).
- Repo: github.com/peterkirgis/llm-moral-foundations (Jupyter Notebook).
- **Internal inconsistency:** main text says 116 vignettes and 21 models; Appendix A
  describes the PCA matrix as 16 responses × 100 questions, then writes the projection
  with 129 rows. Three incompatible numbers. Resolve against the repo. Detail, not argument.

---

## The design template

**Alzahrani et al. — "When Benchmarks are Targets: Revealing the Sensitivity of Large
Language Model Leaderboards." arXiv:2402.01781. ACL 2024, pp. 13787–13805.**

Minor benchmark perturbations, including the method of answer selection, shift models up
to eight leaderboard positions on MMLU. Their comparisons include answer-choice symbol
scoring vs. the cloze method, reported as Kendall's τ against the original ranking.
**This is the methodological template for this project.** Same manipulation, same
rank-agreement statistic, different domain.

**"Scoring methods for LLM predictions on multiple-choice tasks." arXiv:2403.00998.**

Compares five methods for determining an LLM's answer choice: free generation, string
scoring, label scoring, rating aggregation, embedding similarity. Also compares
goodness-of-fit to human data. Finds no single method is best across all models, and that
method choice matters more for weaker-performing models. **Closest neighbour to this
project — read before committing.** The "matters more for weak models" result is directly
relevant to a sample capped at 8B.

**"Mind the Gap: A Closer Look at Tokenization for Multiple-Choice Question Answering
with LLMs." arXiv:2509.15020.**

Documents that published studies disagree on whether the space preceding an answer label
is tokenized as its own token or together with the label. Cite this when justifying the
tokenizer verification step.

**"Look at the Text: Instruction-Tuned Language Models are More Robust Multiple Choice
Selectors than You Think." arXiv:2404.08382.** Text-based vs. probability-based extraction
of model choices.

**"Every Wrong Answer Counts: Option-Level Psychometrics for LLM Multiple-Choice
Benchmarks." arXiv:2608.02966.** Models the full distribution over answer choices with a
Nominal Response Model. Adjacent and psychometrically sophisticated.

---

## Occupied territory — check before claiming novelty on anything nearby

**"Tracing Moral Foundations in Large Language Models." arXiv:2601.05437.** 14 LLMs —
Llama-3.1 8B/70B, Qwen2.5 7B/14B/32B, Qwen3-30B-A3B, Mistral-7B v0.3, base and instruct.
Layer-wise representation analysis, sparse autoencoders, causal steering. MFQ-2 and PVQ-21
as readouts, expanded MFV-130 stimuli, MFRC for validation, MFD2 for feature anchoring.
HF Transformers, bf16, T=0.01. **This occupies the mechanistic/steering space entirely.**

**Aksoy, M. — "Whose Morality Do They Speak? Unraveling Cultural Bias in Multilingual
Language Models." arXiv:2412.18863; Natural Language Processing Journal 12:100172 (2025).**
MFQ-2 administered in Arabic, Farsi, English, Spanish, Japanese, Chinese, French, Russian
to GPT-3.5-Turbo, GPT-4o-mini, Llama 3.1, MistralNeMo. **Occupies multilingual MFT.**

**"Moral Susceptibility and Robustness under Persona Role-Play in Large Language Models."
arXiv:2511.08565.** MFQ stability within and across personas, 10 elicitations per item.
**Occupies persona × MFQ.**

**Rupprecht, Ahnert & Strohmaier — "Prompt Perturbations Reveal Human-Like Biases in LLM
Survey Responses." arXiv:2507.07188.** World Values Survey, 11 perturbations to phrasing
and answer structure, nine models, 167k simulated interviews. Consistent recency bias.
**Occupies generic prompt perturbation on normative surveys.**

**Dominguez-Olmedo, Hardt & Mendler-Dünner — "Questioning the Survey Responses of Large
Language Models." arXiv:2306.07951.** Models key on answer ordering and labelling rather
than semantics; A-bias persists under position randomisation; response entropy is high and
largely independent of the question.

**"Scaling laws for moral machine judgement in large language models." arXiv:2601.17637;
Royal Society Open Science 13(6):260202 (2026).** Mixed-effects models with model family as
random effect. **Occupies scale × moral judgment for the Moral Machine paradigm.**

**"Robustness of large language models in moral judgements." Royal Society Open Science
12(4):241229 (2025).** Replicates Takemoto and shows conclusions do not survive prompt
variants as small as relabelling "Case 1"/"Case 2" to "(A)"/"(B)". A structural model for
what a replication-plus-robustness paper looks like.

**QSTN — Kreutner, Rupprecht, Ahnert, Salem & Strohmaier. "A Modular Framework for
Robust Questionnaire Inference with Large Language Models." arXiv:2512.08646.**
Full text fetched and read 2026-08-07. Two roles for this project.

*As prior work (this falsified the original novelty claim):* their evaluation compares
8 response generation methods across 10 open-weight LLMs on ANES 2016, GLES 2017/2025,
and ATP 2021 political-attitude items — 32M simulated responses. Conclusions: the choice
of response generation method should be well-justified (significant differences exist);
token-probability methods are not recommended (misaligned responses); restricted
generation is preferred. Their criterion is alignment with human survey respondents
(simulation), not stability of the model's own profile (measurement) — that distinction
is the surviving contribution of this project. Companion paper: Ahnert, Haensch, Plank &
Strohmaier, "Survey response generation: Generating closed-ended survey responses
in-silico with large language models," arXiv:2510.11586 (citation taken from QSTN's
reference list; fetch before quoting details).

*As tooling:* MIT license, pip install qstn[vllm], instruct models only, prefix caching
and batching via vLLM. Implements token-probability, restricted, and open generation with
parsers — covers three of this project's four conditions. String scoring (sequence
log-likelihood of the full option text) is not in their method list; their "verbalized
distribution" is the model verbalizing probabilities, a different thing. Custom code
needed for string scoring either way.

**Wang, Ma, Hu, Weber-Genzel, Röttger, Kreuter, Hovy & Plank. "'My answer is C':
First-token probabilities do not match text answers in instruction-tuned language
models." Findings of ACL 2024, pp. 7407–7416.** Citation taken verbatim from QSTN's
reference list. Direct predecessor for the label-scoring vs. free-generation contrast —
engage it explicitly in the write-up.**

---

## Instruments

**Clifford, Iyengar, Cabeza & Sinnott-Armstrong (2015). "Moral foundations vignettes: a
standardized stimulus database of scenarios based on moral foundations theory."
*Behavior Research Methods* 47(4):1178–1198.** Source of the MFV. PDF read 2026-08-07
(free copies at cabezalab.org and scottaclifford.com).

- **Per-vignette human means are in Table 1, "Respondent ratings of moral scenarios,"
  pp.1183–1186 — in the main article, not supplementary material.** Columns: Scenario ·
  Foundation · classification % into each of the six foundations · Not Wrong % · **Wrong
  (mean severity)**. Kirgis's `data/survey/vignettes.csv` is a verbatim transcription of it;
  verified by exact match on 9 rows spanning Care (e), Care (p,a), Sanctity, Social Norms.
- **Scale:** 5-point, labelled *not at all wrong / not too wrong / somewhat wrong / very
  wrong / extremely wrong* — the exact five labels Kirgis reuses with codes 0–4.
- **Which 116 Kirgis uses — RESOLVED.** Clifford's full set is 132. Kirgis drops all 16
  physical-harm Care items (9 `Care (p, a)` animal + 7 `Care (p, h)` human), keeping the 16
  `Care (e)` emotional-harm items. 132 − 16 = 116. **His Care foundation is emotional harm
  only**, and anything said about "Care" inherits that.
- **The baseline is NOT nationally representative.** Study 1 recruited n = 330, 192, 94 from
  "a national online panel by Qualtrics," "limited to the age range of 18–40 (M = 35, 32,
  33)," "balanced on ideology." Kirgis's Discussion calls this "a nationally representative
  sample of US adults." It is an ideology-quota online panel of 18–40s. **Do not repeat his
  description.** Free, fully documented criticism of his headline claim.
- **n ≈ 30 per vignette** — "each vignette was rated by approximately 30 individuals." SE of
  each item mean ≈ 0.2 on a 0–4 scale. Treating them as an error-free reference, which the
  Fig 2 mean-difference plot does, understates uncertainty.

**Atari, Haidt, Graham, Koleva, Stevens & Dehghani (2023). "Morality Beyond the WEIRD:
How the Nomological Network of Morality Varies Across Cultures." *Journal of Personality
and Social Psychology* 125(5):1157–1188.** MFQ-2, six foundations, 25 populations.
Splits fairness into Equality and Proportionality. Not needed for the current design.

---

## Independent work on the same paper

**github.com/wassname/llm-moral-foundations2.** Unpublished, no paper, few stars.
Explicitly frames itself as extending Kirgis by controlling positional bias and adding
activation steering. Its research journal contains an entry noting that after
experimenting, weighted or argmax scoring worked better than ranked logprobs — an offhand,
undocumented observation that the scoring method changes results. Corroborating, and a
signal the territory is not empty.

**Movement check 2026-08-07: none.** Remote `HEAD = f05ffe1e9a87528138ea84f026ec991974383b08`,
dated **2025-09-16** — ~11 months stale. Still no paper, still a journal. The entry above is
dated 2025-08-21 and reads verbatim: *"I was using ranked logprobs for judging but after
experimenting with judgembench just using weighted or argmax is better"* — the
characterisation above is accurate. The repo has since grown steering-vector data
(`data/steering/*.json5`, `llm_moral_foundations2/steering.py`) and a "daily dilemma" strand.
Do not cite the journal entry as evidence for anything — it is one line with no method
attached — but it remains corroborating. Territory not occupied.

---

## Open, unverified

- ~~Does Kirgis's code renormalise the top-3 logprob weights?~~ **RESOLVED 2026-08-07: yes,
  and the paper's printed formula does not. They disagree.** See the target-paper entry.
- ~~Are the 116 MFV item texts, foundation labels, and his exact prompt in the repo?~~
  **RESOLVED 2026-08-07: items and labels yes** (`data/survey/vignettes_short.csv`);
  **prompt template yes** (`surveys/mft_base.py:35-40`), and the EDSL-rendered wire format
  is printed in the paper on p.4 — but it is *not* in the repo, so it cannot be reproduced
  exactly under a different framework.
- ~~Are Clifford's per-vignette human means available?~~ **RESOLVED 2026-08-07: yes,
  Clifford Table 1, pp.1183–1198.** Fig 2 replicates. See the Instruments entry.
- Current per-provider logprob exposure. Changes often; verify at time of writing.
- Overlap check against arXiv:2403.00998 still outstanding. Not blocking; do it before the
  write-up, not before the run.
