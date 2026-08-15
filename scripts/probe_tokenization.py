"""Step 3 probe: does the label token survive the chat template, and as which ID?

docs/state.md lists this as day-one risk #1. The hazard (arXiv:2509.15020) is that "0" and " 0"
are DIFFERENT token IDs, chat templates differ in what they emit before the first generated
token, and published studies disagree about which one to score. Getting this wrong silently
corrupts every label-scoring number without raising an error.

So we do not assume. We render the real prompt, tokenize the real option labels, generate
once, and look at what actually came out.

Usage on the pod:
    source /workspace/env.sh
    python scripts/probe_tokenization.py --model Qwen/Qwen2.5-0.5B-Instruct
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import yaml
from transformers import AutoTokenizer

REPO = Path(__file__).resolve().parent.parent


def load_prompt() -> dict:
    with (REPO / "config" / "prompt.yaml").open(encoding="utf-8") as fh:
        return yaml.safe_load(fh)


def first_item() -> str:
    import csv

    with (REPO / "data" / "mfv_116.csv").open(newline="", encoding="utf-8") as fh:
        return next(csv.DictReader(fh))["question_content"]


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", required=True)
    ap.add_argument("--skip-generate", action="store_true",
                    help="tokenizer-only; skip loading vLLM")
    args = ap.parse_args()

    cfg = load_prompt()
    item = first_item()

    # QSTN substitutes {{QUESTION_CONTENT_PLACEHOLDER}}; do the same by hand here so the
    # probe tests the literal string we will actually administer.
    user = cfg["user_template"].replace("{{QUESTION_CONTENT_PLACEHOLDER}}", item)
    messages = [
        {"role": "system", "content": cfg["system"]},
        {"role": "user", "content": user},
    ]

    tok = AutoTokenizer.from_pretrained(args.model)

    print("=" * 78)
    print(f"MODEL: {args.model}")
    print("=" * 78)

    # ---- 1. what the model actually receives ------------------------------------------
    rendered = tok.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)
    print("\n[1] RENDERED PROMPT (repr, so trailing whitespace is visible)")
    print("-" * 78)
    print(repr(rendered))
    print("-" * 78)
    print(f"    ends with: {rendered[-40:]!r}")
    print("    ^ whatever follows the final newline is what the label token must follow.")

    # ---- 2. the tokenization hazard ---------------------------------------------------
    # For each option label, compare the bare digit against the space-prefixed digit.
    # If they differ, scoring the wrong one gives a silently wrong distribution.
    print("\n[2] LABEL TOKENIZATION -- bare vs space-prefixed")
    print("-" * 78)
    # Built with .format rather than an f-string: f-strings could not contain backslashes
    # before Python 3.12, and this script must stay runnable on the 3.10 analysis machine
    # as well as the 3.12 pod.
    print("    " + "{:<8} {:<14} {:<14} {:<7} {}".format(
        "label", "ids('N')", "ids(' N')", "same?", "single tok?"))
    for k in cfg["options"]:
        bare = tok.encode(str(k), add_special_tokens=False)
        spaced = tok.encode(f" {k}", add_special_tokens=False)
        same = "YES" if bare == spaced else "no"
        single = "yes" if len(bare) == 1 else f"NO (len {len(bare)})"
        print(f"    {k!s:<8} {str(bare):<14} {str(spaced):<14} {same:<7} {single}")
    print("    -> if 'same?' is 'no', the two are DIFFERENT tokens and we must score the")
    print("       one the model actually emits, determined empirically in [4] below.")

    # ---- 3. the option strings, for string scoring -------------------------------------
    # The design note in config/prompt.yaml claims options 0 and 1 share a first token
    # ("Not"), which is why string scoring cannot be a single-position readout. Verify.
    print("\n[3] OPTION STRINGS -- first-token collision check (string scoring)")
    print("-" * 78)
    firsts: dict[int, int] = {}
    for k, text in cfg["options"].items():
        ids = tok.encode(text, add_special_tokens=False)
        firsts[k] = ids[0]
        print(f"    {k}: {text!r:<22} n_tokens={len(ids):<3} first_id={ids[0]:<8} "
              f"first={tok.decode([ids[0]])!r}")
    collisions = [
        (a, b) for a in firsts for b in firsts if a < b and firsts[a] == firsts[b]
    ]
    if collisions:
        print(f"    -> COLLISION CONFIRMED: options {collisions} share a first token.")
        print("       A single-position readout CANNOT separate them. String scoring must")
        print("       be a full-sequence log-likelihood. This is the design claim, verified.")
    else:
        print("    -> no collision on this tokenizer. The design claim does NOT hold here;")
        print("       re-read config/prompt.yaml before relying on it.")

    # token-length spread drives the length-normalisation decision
    lens = {k: len(tok.encode(t, add_special_tokens=False)) for k, t in cfg["options"].items()}
    print(f"    token lengths: {lens}")
    print("    -> unequal lengths are why length-normalisation is a real choice, not a default.")

    if args.skip_generate:
        return 0

    # ---- 4. what the model actually emits ---------------------------------------------
    from vllm import LLM, SamplingParams

    llm = LLM(model=args.model, max_model_len=1024, gpu_memory_utilization=0.85,
              enforce_eager=True)
    out = llm.generate(
        [rendered],
        SamplingParams(temperature=0.0, max_tokens=1, logprobs=20),
    )[0].outputs[0]

    emitted_id = out.token_ids[0]
    print("\n[4] FIRST GENERATED TOKEN (greedy)")
    print("-" * 78)
    print(f"    id={emitted_id}  decoded={tok.decode([emitted_id])!r}")

    print("\n[5] TOP-20 LOGPROBS AT POSITION 0 -- what label scoring reads")
    print("-" * 78)
    pos = out.logprobs[0]
    ranked = sorted(pos.items(), key=lambda kv: kv[1].logprob, reverse=True)
    valid_ids = {}
    for k in cfg["options"]:
        for form in (str(k), f" {k}"):
            ids = tok.encode(form, add_special_tokens=False)
            if len(ids) == 1:
                valid_ids.setdefault(ids[0], (k, form))

    print(f'    {"rank":<6} {"id":<9} {"decoded":<14} {"logprob":<12} {"option?"}')
    for rank, (tid, lp) in enumerate(ranked, 1):
        tag = ""
        if tid in valid_ids:
            k, form = valid_ids[tid]
            tag = f"<-- option {k} (as {form!r})"
        print(f"    {rank:<6} {tid:<9} {tok.decode([tid])!r:<14} {lp.logprob:<12.5f} {tag}")

    # ---- 6. the estimator, and how much mass it is throwing away ------------------------
    import math

    present = {}
    for tid, lp in pos.items():
        if tid in valid_ids:
            k, _ = valid_ids[tid]
            present[k] = max(present.get(k, -math.inf), lp.logprob)

    print("\n[6] LABEL SCORING on this item")
    print("-" * 78)
    if not present:
        print("    NO option token in the top 20. Label scoring is undefined here.")
        print("    If this is common, guided decoding must constrain the output.")
    else:
        probs = {k: math.exp(v) for k, v in present.items()}
        mass = sum(probs.values())
        exp_renorm = sum(k * p for k, p in probs.items()) / mass
        exp_raw = sum(k * p for k, p in probs.items())
        print(f"    options found in top-20 : {sorted(present)} ({len(present)}/5)")
        print(f"    probability mass on them: {mass:.4f}")
        print(f"    E[score] renormalised   : {exp_renorm:.4f}   <- what we will report")
        print(f"    E[score] unnormalised   : {exp_raw:.4f}   <- Kirgis's PRINTED formula")
        print(f"    difference              : {exp_renorm - exp_raw:.4f}")
        print("    -> Kirgis's code renormalises; his paper's formula does not. That gap is")
        print("       the audit. Here it is, on one item, in one number.")
        if len(present) == 1:
            print("    -> ONLY ONE option present: a renormalised estimator returns that label")
            print("       EXACTLY. This is the argmax degeneracy from the go/no-go check.")

    print("\n" + "=" * 78)
    print(json.dumps({
        "model": args.model,
        "prompt_ends_with": rendered[-20:],
        "emitted_first_token_id": emitted_id,
        "emitted_first_token": tok.decode([emitted_id]),
        "options_in_top20": sorted(present) if present else [],
    }, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
