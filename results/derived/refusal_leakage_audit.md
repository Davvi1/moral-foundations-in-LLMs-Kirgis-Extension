# Tier-0 audit — refusal leakage into label scoring

Label scoring forces an answer by renormalising over the five digits. The question: when a model behaviourally refuses (greedy), does its label-scoring retained mass drop at exactly those cells? If yes, label scoring is refusal-*blind*, not refusal-*free*, and the mass column is a mandatory manipulation check.

The test runs at two levels, because the within-model deficit has **no power for uniform refusers**: a model that declines everything has uniformly low mass and, by construction, zero deficit everywhere.

## Level 1 — between models: does non-answering behaviour depress label mass?

Spearman(mean label mass, greedy non-answer rate) over 20 models: **ρ = -0.599**

| model | greedy non-answer | mean label mass |
|---|---|---|
| Ministral-8B-Instruct-2410 | 100% | 0.337 |
| Llama-3.2-1B-Instruct | 97% | 0.231 |
| Llama-3.1-8B-Instruct | 5% | 0.765 |
| gemma-2-2b-it | 3% | 0.645 |
| gemma-2-9b-it | 1% | 0.973 |
| Yi-1.5-9B-Chat | 1% | 0.816 |
| Llama-3.2-3B-Instruct | 0% | 0.470 |
| Mistral-7B-Instruct-v0.3 | 0% | 0.078 |

## Level 2 — within models: foundation-specific refusal vs mass crater

Cell-level Spearman over all 140 cells: ρ = 0.092; over the 12 cells with any refusal: ρ = -0.172. **These aggregates are dominated by one uniform refuser (Llama-3.2-1B), for which the deficit is uninformative** — the informative cases are the differential ones below.

## The cells with behavioural refusal — did label mass drop there?

| model | foundation | greedy refusal | label mass | model's mass elsewhere | deficit |
|---|---|---|---|---|---|
| Llama-3.2-1B-Instruct | Fairness | 100% | 0.241 | 0.230 | -0.011 |
| Llama-3.2-1B-Instruct | Sanctity | 100% | 0.156 | 0.244 | +0.088 |
| Llama-3.2-1B-Instruct | Loyalty | 100% | 0.229 | 0.232 | +0.003 |
| Llama-3.2-1B-Instruct | Liberty | 100% | 0.113 | 0.251 | +0.138 |
| Llama-3.2-1B-Instruct | Care | 94% | 0.254 | 0.228 | -0.026 |
| Llama-3.2-1B-Instruct | Social Norms | 88% | 0.336 | 0.214 | -0.122 |
| Llama-3.2-1B-Instruct | Authority | 71% | 0.293 | 0.222 | -0.071 |
| Llama-3.1-8B-Instruct | Sanctity | 35% | 0.475 | 0.815 | +0.340 |
| gemma-2-2b-it | Loyalty | 6% | 0.446 | 0.676 | +0.230 |
| Yi-1.5-9B-Chat | Liberty | 6% | 0.822 | 0.815 | -0.007 |
| gemma-2-2b-it | Sanctity | 6% | 0.635 | 0.645 | +0.010 |
| gemma-2-9b-it | Sanctity | 6% | 0.897 | 0.987 | +0.089 |

## Per-model mass profile (label condition)

| model | Care | Fairness | Liberty | Loyalty | Authority | Sanctity | Social Norms |
|---|---|---|---|---|---|---|---|
| Llama-3.1-8B-Instruct | 0.738 | 0.807 | 0.803 | 0.814 | 0.805 | 0.475 | 0.921 |
| Llama-3.2-1B-Instruct | 0.254 | 0.241 | 0.113 | 0.229 | 0.293 | 0.156 | 0.336 |
| Llama-3.2-3B-Instruct | 0.387 | 0.560 | 0.458 | 0.507 | 0.524 | 0.389 | 0.460 |
| Ministral-8B-Instruct-2410 | 0.346 | 0.357 | 0.336 | 0.331 | 0.339 | 0.333 | 0.313 |
| Mistral-7B-Instruct-v0.3 | 0.092 | 0.082 | 0.079 | 0.085 | 0.071 | 0.078 | 0.058 |
| OLMo-2-1124-13B-Instruct | 0.999 | 0.999 | 0.997 | 0.997 | 0.997 | 0.991 | 0.998 |
| OLMo-2-1124-7B-Instruct | 0.999 | 0.997 | 0.998 | 0.999 | 0.999 | 0.975 | 0.999 |
| Phi-3-mini-4k-instruct | 0.997 | 0.998 | 0.996 | 0.999 | 0.999 | 0.987 | 1.000 |
| Phi-4-mini-instruct | 0.983 | 0.990 | 0.981 | 0.962 | 0.984 | 0.970 | 0.977 |
| Qwen2.5-0.5B-Instruct | 0.999 | 0.999 | 0.998 | 0.998 | 0.999 | 0.997 | 0.999 |
| Qwen2.5-1.5B-Instruct | 0.998 | 0.998 | 0.998 | 0.997 | 0.998 | 0.997 | 0.996 |
| Qwen2.5-14B-Instruct | 1.000 | 1.000 | 0.999 | 0.999 | 1.000 | 0.998 | 1.000 |
| Qwen2.5-3B-Instruct | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 |
| Qwen2.5-7B-Instruct | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 |
| SmolLM2-1.7B-Instruct | 0.973 | 0.971 | 0.971 | 0.964 | 0.972 | 0.971 | 0.972 |
| Yi-1.5-9B-Chat | 0.812 | 0.872 | 0.822 | 0.772 | 0.818 | 0.801 | 0.815 |
| gemma-2-2b-it | 0.722 | 0.776 | 0.798 | 0.446 | 0.543 | 0.635 | 0.583 |
| gemma-2-9b-it | 0.987 | 0.985 | 0.962 | 0.992 | 0.994 | 0.897 | 0.999 |
| granite-3.1-8b-instruct | 0.994 | 0.994 | 0.993 | 0.996 | 0.994 | 0.996 | 0.998 |
| internlm2_5-7b-chat | 0.890 | 0.899 | 0.886 | 0.880 | 0.893 | 0.868 | 0.862 |

## Verdict

**Leakage supported.** Between models, non-answering behaviour and label mass are strongly coupled (ρ = -0.60 over 20 models): models that decline or fall silent in generation are largely those whose digit mass collapses in the logprob readout. The within-model evidence is thinner — only 1 differential-refusal case(s) exist in this sample — but the flagship case is exactly the predicted signature: Llama-3.1-8B-Instruct craters to mass 0.475 on Sanctity against 0.815 on its other foundations, at 35% behavioural refusal on precisely that foundation.

**Caveat, from the same table:** low mass has a second cause. Mistral-7B answers 100% of greedy items yet has mass 0.078 — that is the answer-format mismatch (digits not where the readout looks), not refusal. Retained mass is therefore a *necessary* integrity check that flags problems, but it is not refusal-specific; distinguishing the causes requires the raw outputs.

**Implications.** (1) Label scoring does not avoid the refusal confound — it hides it; renormalisation manufactures a confident score from whatever digit mass remains. Studies using logprob readouts on safety-relevant content must report retained mass; Kirgis's logprob arm has no such check. (2) The flip side is useful: retained mass is a **graded, generation-free refusal detector** — differential refusal is visible in the logprob readout without sampling a single token.
