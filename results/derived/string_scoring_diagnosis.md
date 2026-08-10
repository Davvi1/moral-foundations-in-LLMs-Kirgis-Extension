# Step 6 — what is string scoring measuring?

Rank correlation across the 116 items, within each model. Rank correlation is used because it is invariant to the level shift, which is the nuisance we want to see past. `label~greedy` and `label~sampled` are reference points: methods we expect to agree.

| model | label~string | label~greedy | label~sampled | mean string mass | mean label mass |
|---|---|---|---|---|---|
| Yi-1.5-9B-Chat | 0.899 | 0.952 | 0.963 | 0.2526 | 0.8163 |
| Qwen2.5-0.5B-Instruct | 0.548 | 0.568 | 0.580 | 0.1615 | 0.9985 |
| Qwen2.5-1.5B-Instruct | 0.735 | 0.802 | 0.856 | 0.1456 | 0.9973 |
| Qwen2.5-14B-Instruct | 0.914 | 0.977 | 0.990 | 0.0005 | 0.9995 |
| Qwen2.5-3B-Instruct | 0.455 | 0.949 | 0.977 | 0.0022 | 1.0000 |
| Qwen2.5-7B-Instruct | 0.802 | 0.927 | 0.973 | 0.0015 | 1.0000 |
| OLMo-2-1124-13B-Instruct | 0.936 | 0.909 | 0.985 | 0.1336 | 0.9968 |
| OLMo-2-1124-7B-Instruct | 0.913 | 0.902 | 0.959 | 0.1605 | 0.9951 |
| gemma-2-2b-it | 0.886 | 0.950 | 0.984 | 0.0191 | 0.6447 |
| gemma-2-9b-it | 0.978 | 0.965 | 0.987 | 0.0616 | 0.9733 |
| granite-3.1-8b-instruct | 0.929 | 0.961 | 0.977 | 0.1192 | 0.9950 |
| internlm2_5-7b-chat | nan | 0.918 | 0.973 | nan | 0.8827 |
| Llama-3.1-8B-Instruct | 0.915 | 0.937 | 0.971 | 0.3049 | 0.7645 |
| Llama-3.2-1B-Instruct | 0.279 | nan | 0.155 | 0.3628 | 0.2306 |
| Llama-3.2-3B-Instruct | 0.874 | 0.876 | 0.945 | 0.1580 | 0.4699 |
| Phi-3-mini-4k-instruct | 0.959 | 0.956 | 0.962 | 0.2467 | 0.9964 |
| Phi-4-mini-instruct | 0.819 | 0.894 | 0.946 | 0.1461 | 0.9784 |
| Ministral-8B-Instruct-2410 | 0.985 | nan | 0.627 | 0.5459 | 0.3366 |
| Mistral-7B-Instruct-v0.3 | 0.242 | 0.716 | 0.866 | 0.8664 | 0.0780 |

**Mean label~string rank correlation: 0.782** (min 0.242, max 0.985)

**Mean label~greedy rank correlation: 0.892** — the reference ceiling.

## Verdict

String scoring **tracks the same item ordering as label scoring** (mean rho 0.782). The large difference in level is therefore a genuine method effect on a shifted scale, not a sign that the condition is measuring something unrelated. It belongs in the primary variance ratio, and the level shift is part of the result rather than an artifact to explain away.

## The probability-mass problem

Mean retained mass: **string 0.2049**, label 0.7975.

Our prompt DISPLAYS the five options as numbered lines, so the model is being asked how likely it is to emit option text it has effectively been steered away from. That is why string mass is low, and it is the limitation already recorded in `config/prompt.yaml`: this is not textbook cloze, which omits the options from the prompt. The comparison across the five options remains internal and consistent, so the condition is not meaningless — but it is not comparable to published cloze numbers, and the write-up must say so.

## Limitation of this diagnostic

The harness stored the per-item EXPECTATION, not the five per-option log-probabilities. The sharper test — whether label and string order the five options identically *within* an item — is not computable from the saved data. This item-level rank correlation is the best available substitute. Capturing per-option scores costs nothing and should be added if the harness is re-run.
