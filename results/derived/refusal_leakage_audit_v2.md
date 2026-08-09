# Tier-0 audit — refusal leakage into label scoring

Label scoring forces an answer by renormalising over the five digits. The question: when a model behaviourally refuses (greedy), does its label-scoring retained mass drop at exactly those cells? If yes, label scoring is refusal-*blind*, not refusal-*free*, and the mass column is a mandatory manipulation check.

The test runs at two levels, because the within-model deficit has **no power for uniform refusers**: a model that declines everything has uniformly low mass and, by construction, zero deficit everywhere.

## Level 1 — between models: does non-answering behaviour depress label mass?

Spearman(mean label mass, greedy non-answer rate) over 31 models: **ρ = -0.543**

| model | greedy non-answer | mean label mass |
|---|---|---|
| Ministral-8B-Instruct-2410 | 100% | 0.421 |
| Llama-3.2-1B-Instruct | 97% | 0.220 |
| gemma-2-27b-it | 19% | 0.353 |
| Llama-3.1-8B-Instruct | 5% | 0.778 |
| zephyr-7b-beta | 4% | 0.166 |
| gemma-2-2b-it | 3% | 0.645 |
| Yi-1.5-9B-Chat | 1% | 0.819 |
| gemma-2-9b-it | 1% | 0.973 |

## Level 2 — within models: foundation-specific refusal vs mass crater

Cell-level Spearman over all 217 cells: ρ = 0.075; over the 18 cells with any refusal: ρ = -0.078. **These aggregates are dominated by one uniform refuser (Llama-3.2-1B), for which the deficit is uninformative** — the informative cases are the differential ones below.

## The cells with behavioural refusal — did label mass drop there?

| model | foundation | greedy refusal | label mass | model's mass elsewhere | deficit |
|---|---|---|---|---|---|
| Llama-3.2-1B-Instruct | Liberty | 100% | 0.111 | 0.239 | +0.128 |
| Llama-3.2-1B-Instruct | Fairness | 100% | 0.231 | 0.219 | -0.012 |
| Llama-3.2-1B-Instruct | Loyalty | 100% | 0.210 | 0.223 | +0.013 |
| Llama-3.2-1B-Instruct | Sanctity | 100% | 0.156 | 0.232 | +0.075 |
| Llama-3.2-1B-Instruct | Care | 94% | 0.237 | 0.218 | -0.019 |
| Llama-3.2-1B-Instruct | Social Norms | 94% | 0.320 | 0.204 | -0.116 |
| Llama-3.2-1B-Instruct | Authority | 71% | 0.281 | 0.211 | -0.070 |
| Llama-3.1-8B-Instruct | Sanctity | 35% | 0.481 | 0.829 | +0.349 |
| gemma-2-27b-it | Sanctity | 35% | 0.382 | 0.348 | -0.034 |
| gemma-2-27b-it | Loyalty | 31% | 0.291 | 0.363 | +0.072 |
| gemma-2-27b-it | Authority | 24% | 0.306 | 0.361 | +0.055 |
| gemma-2-27b-it | Social Norms | 19% | 0.385 | 0.348 | -0.038 |
| gemma-2-2b-it | Loyalty | 6% | 0.446 | 0.676 | +0.230 |
| Yi-1.5-9B-Chat | Liberty | 6% | 0.825 | 0.817 | -0.007 |
| gemma-2-27b-it | Fairness | 6% | 0.432 | 0.340 | -0.093 |

## Per-model mass profile (label condition)

| model | Care | Fairness | Liberty | Loyalty | Authority | Sanctity | Social Norms |
|---|---|---|---|---|---|---|---|
| Falcon3-7B-Instruct | 0.986 | 0.987 | 0.982 | 0.985 | 0.984 | 0.988 | 0.961 |
| Llama-3.1-70B-Instruct | 0.920 | 0.885 | 0.893 | 0.830 | 0.861 | 0.926 | 0.990 |
| Llama-3.1-8B-Instruct | 0.760 | 0.820 | 0.819 | 0.825 | 0.821 | 0.481 | 0.931 |
| Llama-3.2-1B-Instruct | 0.237 | 0.231 | 0.111 | 0.210 | 0.281 | 0.156 | 0.320 |
| Llama-3.2-3B-Instruct | 0.400 | 0.569 | 0.453 | 0.512 | 0.527 | 0.392 | 0.466 |
| Ministral-8B-Instruct-2410 | 0.432 | 0.451 | 0.422 | 0.412 | 0.422 | 0.422 | 0.387 |
| Mistral-7B-Instruct-v0.3 | 0.010 | 0.008 | 0.009 | 0.008 | 0.009 | 0.009 | 0.006 |
| Mistral-Small-24B-Instruct-2501 | 0.782 | 0.774 | 0.745 | 0.726 | 0.752 | 0.783 | 0.741 |
| OLMo-2-0325-32B-Instruct | 0.997 | 0.998 | 0.996 | 0.996 | 0.997 | 0.993 | 0.992 |
| OLMo-2-1124-13B-Instruct | 0.998 | 0.999 | 0.997 | 0.997 | 0.997 | 0.990 | 0.999 |
| OLMo-2-1124-7B-Instruct | 0.999 | 0.997 | 0.998 | 0.999 | 0.999 | 0.977 | 0.999 |
| Phi-3-mini-4k-instruct | 0.524 | 0.528 | 0.545 | 0.513 | 0.488 | 0.527 | 0.542 |
| Phi-3.5-mini-instruct | 0.191 | 0.268 | 0.409 | 0.207 | 0.074 | 0.386 | 0.078 |
| Phi-4-mini-instruct | 0.983 | 0.989 | 0.981 | 0.959 | 0.983 | 0.969 | 0.976 |
| Qwen2-7B-Instruct | 0.999 | 0.999 | 0.996 | 0.998 | 0.997 | 0.991 | 0.991 |
| Qwen2.5-0.5B-Instruct | 0.999 | 0.999 | 0.998 | 0.998 | 0.999 | 0.997 | 0.999 |
| Qwen2.5-1.5B-Instruct | 0.998 | 0.998 | 0.998 | 0.997 | 0.998 | 0.997 | 0.996 |
| Qwen2.5-14B-Instruct | 1.000 | 1.000 | 0.999 | 1.000 | 1.000 | 0.998 | 1.000 |
| Qwen2.5-32B-Instruct | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 0.997 | 1.000 |
| Qwen2.5-3B-Instruct | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 |
| Qwen2.5-72B-Instruct | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 0.979 | 1.000 |
| Qwen2.5-7B-Instruct | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 |
| SmolLM2-1.7B-Instruct | 0.976 | 0.972 | 0.973 | 0.966 | 0.974 | 0.972 | 0.974 |
| Yi-1.5-9B-Chat | 0.817 | 0.875 | 0.825 | 0.779 | 0.820 | 0.800 | 0.812 |
| gemma-2-27b-it | 0.376 | 0.432 | 0.298 | 0.291 | 0.306 | 0.382 | 0.385 |
| gemma-2-2b-it | 0.723 | 0.776 | 0.798 | 0.446 | 0.543 | 0.635 | 0.583 |
| gemma-2-9b-it | 0.987 | 0.986 | 0.963 | 0.991 | 0.994 | 0.897 | 0.999 |
| granite-3.1-8b-instruct | 0.994 | 0.994 | 0.993 | 0.996 | 0.994 | 0.996 | 0.998 |
| internlm2_5-7b-chat | 0.889 | 0.899 | 0.889 | 0.880 | 0.894 | 0.868 | 0.859 |
| phi-4 | 0.991 | 0.998 | 0.983 | 0.955 | 0.979 | 0.792 | 0.999 |
| zephyr-7b-beta | 0.129 | 0.119 | 0.190 | 0.189 | 0.090 | 0.099 | 0.354 |

## Verdict

**Leakage supported.** Between models, non-answering behaviour and label mass are strongly coupled (ρ = -0.54 over 31 models): models that decline or fall silent in generation are largely those whose digit mass collapses in the logprob readout. The within-model evidence is thinner — only 5 differential-refusal case(s) exist in this sample — but the flagship case is exactly the predicted signature: Llama-3.1-8B-Instruct craters to mass 0.481 on Sanctity against 0.829 on its other foundations, at 35% behavioural refusal on precisely that foundation.

**Caveat, from the same table:** low mass has a second cause. Mistral-7B answers 100% of greedy items yet has mass 0.078 — that is the answer-format mismatch (digits not where the readout looks), not refusal. Retained mass is therefore a *necessary* integrity check that flags problems, but it is not refusal-specific; distinguishing the causes requires the raw outputs.

**Implications.** (1) Label scoring does not avoid the refusal confound — it hides it; renormalisation manufactures a confident score from whatever digit mass remains. Studies using logprob readouts on safety-relevant content must report retained mass; Kirgis's logprob arm has no such check. (2) The flip side is useful: retained mass is a **graded, generation-free refusal detector** — differential refusal is visible in the logprob readout without sampling a single token.
