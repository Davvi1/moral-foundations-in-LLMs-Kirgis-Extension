# The four scoring methods, from the ground up

Written for an MSc-level reader with social science and CS training. This is the reference
version; the write-up compresses it.

---

## 0. The one fact everything rests on

A decoder language model is a function. Feed it a token sequence (the *context*) and it
returns a **probability distribution over the next token** — a softmax over the whole
vocabulary, ~150,000 entries, every entry a real number, summing to 1.

That is all it computes. Longer outputs come from the **chain rule**: generate a token, append
it to the context, ask again.

    p(w_1, w_2, ..., w_T | context) = ∏_t  p(w_t | context, w_1 ... w_{t-1})

Two consequences matter for measurement:

1. **The forward pass is deterministic.** Same weights, same input → same distribution, every
   time, to floating-point precision. The model does not "decide" anything; it emits a
   distribution. Randomness enters only if *we* draw from that distribution.
2. **You can read the distribution without generating anything.** This is the open-weights
   privilege: with API models you observe behaviour (a sampled answer); with open weights you
   can observe the propensities behind the behaviour.

The survey-methods analogy: a respondent has some latent propensity across the five response
boxes. Normally you observe one tick. Here we can either read the propensities directly
(methods 1–2) or watch the tick happen (methods 3–4).

Before any of this, the **chat template** wraps our item in the model's dialogue format —
special tokens marking system/user/assistant turns — ending with the cue for the assistant's
reply. At that cut point, the model's next-token distribution is "what would I say first?"
Every method below starts from this identical, byte-identical context.

---

## 1. Label scoring — read the propensities on the digits

At the answer position, look up the probability of each label token:

    p_k = p(token = "k" | context),   k in {0,1,2,3,4}

renormalise over the five (they don't sum to 1 — mass also sits on "\n", "I", "The", …),
and take the expectation:

    p̃_k = p_k / Σ_j p_j          score = Σ_k  k · p̃_k

**What it measures:** the model's first-preference distribution over the labels, as a
forced-choice readout. Like reading a respondent's choice probabilities instead of one draw.

**Deterministic** — it evaluates the softmax; nothing is sampled.

**Assumptions, all of which failed for some model in our run:**
- *The label is one token.* SentencePiece tokenizers encode "0" as two tokens (metaspace +
  digit) — a naive single-token lookup finds nothing (Mistral, Phi-3, Yi).
- *The answer is at the first position.* Mistral emits `\n` first; Ministral emits
  end-of-sequence; Llama-3.2-1B starts prose. First-token scoring there measures the
  probability of a newline, not a judgment.
- *The renormalisation is benign.* Σp_j is the **retained mass**. If it is 0.99, fine. If it
  is 0.02 because the model mostly wants to refuse, renormalising manufactures a confident
  score out of a model that wasn't answering. Mass is logged per row for exactly this reason.

**v2 improvement:** compute p_k *exactly* by forcing each digit as a continuation and reading
`prompt_logprobs` — no top-k truncation, no dependence on what happens to appear in a top-20
list. Keep the position-scan variant as a separately-reported estimator.

---

## 2. String scoring — read the propensities on the phrases

Same idea, but the "response" is the option *text*. Score each full phrase by the chain rule:

    S_k = Σ_t  log p(w_t^{(k)} | context, w_1^{(k)} ... w_{t-1}^{(k)})

for the token sequence of "Not at all wrong", "Not too wrong", etc. Because longer phrases
mechanically accumulate more negative log-probability, we also compute the length-normalised
version (mean per token) — which of the two is "right" is a genuine researcher choice, so
both are recorded. Then softmax over the five S_k and take the expectation, as in method 1.

**Why it exists separately from label scoring:** the numeral `3` and the phrase "Very wrong"
are different objects to the model. The MCQ literature (cloze scoring) has long known these
can disagree; our Step-6 diagnostic shows they do — same item ordering, very different levels
and model rankings.

**Deterministic** — again, only evaluation.

**Where our v1 implementation deviates from what the model actually does, and why v2 changes
it:** our greedy outputs show the models' natural answer format is `"3: Very wrong"` — digit,
colon, *then* phrase. v1 scored the bare phrase, a continuation the prompt (which displays the
options as numbered lines) steers away from — hence retained mass of 0.22 vs label's 0.81.
v2 scores the **full option line** `"3: Very wrong"` as the primary string variant, keeps the
bare phrase as sensitivity, and stores the five per-option scores (v1 stored only the
expectation, which blocked the sharpest diagnostic). Registered prediction, made before any
v2 data: full-line mass will be far higher, and its model-ranking agreement with label will
rise substantially. If it doesn't, the v1 divergence is a real construct difference, not an
artifact.

Note this is still not textbook **cloze**, which hides the options from the prompt. A true
cloze arm requires a different prompt and therefore lives outside the fixed-prompt design as
an explicitly-flagged extra condition, if run at all.

---

## 3. Free generation, greedy — watch one deterministic tick

Let the model write, taking the **argmax** token at every step:

    w_t = argmax_w  p(w | context, w_1 ... w_{t-1})

then parse the digit out of the text.

**What it measures:** the model's behaviour when decoding is deterministic — the closest
thing to "just ask it" with the randomness removed. (Technical honesty: greedy is locally
optimal per step, not the globally most probable sequence; finding that is intractable and
nobody uses it.)

**Deterministic** in principle. One caveat we verify rather than assume: GPU floating-point
reduction order can vary with batch composition, so bit-identical output across differently
batched runs is not guaranteed. Within one run, one batch — stable.

**Failure modes observed:** the argmax at step 1 can be the end-of-sequence token (Ministral:
answers 0/116 — it never *says* anything), or the start of a refusal ("I can't answer this",
Llama-3.2-1B, 108/116). These are different phenomena — a decoding artifact vs a value-laden
act — and are recorded as different failure types.

---

## 4. Free generation, sampled — watch ten random ticks and average

Same as greedy, but at each step **draw** from the distribution (temperature 1):

    w_t ~ p(w | context, w_1 ... w_{t-1})

Do this k = 10 times with different seeds, parse each, average the digits.

**What it measures:** a Monte Carlo estimate of the expected *stated* answer under the model's
own output distribution — including all downstream effects: sometimes it phrases things
differently, sometimes it refuses, sometimes a low-probability answer path gets sampled.

**This is the only stochastic method**, hence the only one where "trials" add information.
k = 10 gives a Monte-Carlo standard error of roughly σ/√10 per item, which the analysis model
carries explicitly.

**Estimand subtlety worth one sentence in the write-up:** label scoring computes an
expectation over *forced first-token digits*; sampled generation approximates an expectation
over *whole behaviours*. These are different estimands that happen to agree well here
(ρ = 0.88 over model rankings) — that agreement is a finding, not a tautology.

---

## 5. Why three methods get one observation and one gets ten

Because randomness lives in exactly one place: the sampling step of method 4.

- Methods 1–2 **evaluate a function**. Re-running returns the identical number, like measuring
  a ruler twice.
- Method 3 is a deterministic function of the deterministic distributions.
- Method 4 draws from a distribution — so we replicate it, and only it.

**The deeper version of the "why no trials?" question is right, though.** Re-executing a
deterministic computation is not what a survey methodologist means by replication. The
variance that matters is over the *arbitrary presentation choices* we froze: the exact
wording of the stem, the order of the options. Those are the "trials" that would matter —
question-wording experiments, not re-measurement. Our v1 design holds the prompt at a single
fixed value, so it estimates method variance *conditional on one prompt* and says nothing
about prompt variance. The Phase-2 design adds prompt variants as a designed factor, which is
the statistically correct home for this instinct: not more draws of the same computation, but
variation over the nuisance parameters the field knows to be dangerous.
