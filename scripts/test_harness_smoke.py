"""End-to-end smoke test of the v2 harness against a fake vLLM. No GPU, no weights.

    python scripts/test_harness_smoke.py

WHY: `test_conditions_v2.py` tests the scoring LOGIC. It cannot catch integration faults —
a column missing from FIELDS, a manifest that will not serialise, a cloze prompt that never
got rendered, a condition name that no branch handles. Those fail on the pod, after weights
have been downloaded, and each one costs real money and a restart. The project has already
paid for one of them (a `datetime.date` in the manifest that `json.dumps` refused, discovered
after twenty minutes of GPU time).

So this drives the real `run_model()` with a fake engine and asserts on the artefacts it
writes. The fake deliberately mimics vLLM's tokenization behaviour — it encodes prompts WITH
special tokens, which is what produces the local-vs-engine off-by-one that defect D1 was made
of. If the v2 boundary logic were still trusting a local token count, this test would show it.
"""

from __future__ import annotations

import argparse
import json
import sys
import tempfile
import types
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

# Two models, chosen to exercise BOTH sides of defect D1. Qwen's chat template does not emit
# BOS, so local and engine token counts agree and v1's boundary happened to be right.
# Mistral-v0.3's template DOES emit <s> and its tokenizer adds another, so the counts differ
# by one — the condition that silently corrupted v1's length-normalised string scores on 12 of
# 30 roster models. v2 must be unaffected on both, and the probe must SAY which is which.
TOKENIZERS = ["Qwen/Qwen2.5-0.5B-Instruct", "mistralai/Mistral-7B-Instruct-v0.3"]
GEN_TEXT = "3: Very wrong"


class _LP:
    def __init__(self, lp):
        self.logprob = lp


def _pseudo_lp(tid: int, pos: int) -> float:
    """Deterministic pseudo-logprobs, deliberately kept SUB-NORMALIZED. Read the reason.

    The retained-mass invariant (mass <= 1) is not an accident of the scorer — it holds for a
    real model because the five option continuations are pairwise non-prefix token sequences
    from the same shared prefix, hence mutually exclusive events under a softmax that sums to
    one over the vocabulary. A fake that invents each token's logprob independently obeys no
    such constraint, and an earlier version of this file produced mass = 1.21, failing the
    test on the FAKE's arithmetic rather than on anything in `conditions_v2`.

    So the range is capped at exp(-2.5) ~ 0.082 per token. Ten submitted variants then bound
    the mass at ~0.82 < 1 by construction, and the invariant check tests the scorer instead of
    testing the mock. Widening this range will make the test fail for a reason that is not a
    bug — if that happens, fix the fake, not the assertion.
    """
    return -(((tid * 7919 + pos * 104729) % 650) / 100.0) - 2.5


class _CompOut:
    def __init__(self, text, token_ids):
        self.text = text
        self.token_ids = token_ids
        self.logprobs = None


class _Out:
    def __init__(self, ids, with_plp, gen_text):
        self.prompt_token_ids = list(ids)
        self.prompt_logprobs = (
            [None] + [{t: _LP(_pseudo_lp(t, i))} for i, t in enumerate(ids[1:], start=1)]
            if with_plp else None)
        self.outputs = [_CompOut(gen_text, [1, 2, 3])]


class FakeLLM:
    """Encodes WITH special tokens, as vLLM does. That is the whole point of the fake."""

    def __init__(self, tok):
        self.tok = tok
        self.n_seqs = 0

    def generate(self, texts, sp):
        self.n_seqs += len(texts)
        with_plp = sp.get("prompt_logprobs") is not None
        return [_Out(self.tok.encode(t, add_special_tokens=True), with_plp, GEN_TEXT)
                for t in texts]


def install_fake_vllm(tok):
    mod = types.ModuleType("vllm")
    mod.LLM = lambda **kw: FakeLLM(tok)
    mod.SamplingParams = lambda **kw: kw
    sys.modules["vllm"] = mod


RESULTS = []


def check(name, cond, detail=""):
    RESULTS.append((name, bool(cond), detail))
    print(f"  {'PASS' if cond else 'FAIL'}  {name}{('  — ' + detail) if detail else ''}")


def run_one(R, prompt_cfg, models_cfg, items, meta, model_id) -> bool:
    """Drive run_model() for one model. Returns True if it exercised the D1 mismatch path."""
    tag = model_id.split("/")[-1]

    def ck(name, cond, detail=""):
        check(f"[{tag}] {name}", cond, detail)

    with tempfile.TemporaryDirectory() as td:
        R.RAW = Path(td)
        args = argparse.Namespace(
            harness="v2", cloze=True, conditions=None, k=3, max_model_len=1024,
            tensor_parallel_size=1,
            gpu_util=0.85, eager=True, purge_weights=False, force=True, suffix="",
        )
        # Real pinned revision from config/models.yaml: run_model resolves it against the
        # Hub, so a made-up SHA fails before any of the code under test runs.
        entry = next(m for m in models_cfg["primary"] if m["id"] == model_id)
        R.run_model(entry, prompt_cfg, items, meta, args)

        csv_path = Path(td) / f"{R.slug(model_id)}.csv"
        man_path = Path(td) / f"{R.slug(model_id)}.manifest.json"
        ck("CSV written", csv_path.exists())
        ck("manifest written", man_path.exists())
        if not (csv_path.exists() and man_path.exists()):
            return False

        import csv as _csv
        rows = list(_csv.DictReader(csv_path.open(encoding="utf-8")))
        man = json.loads(man_path.read_text(encoding="utf-8"))

        conds: dict[str, int] = {}
        for r in rows:
            conds[r["condition"]] = conds.get(r["condition"], 0) + 1
        print(f"  conditions: {conds}")

        expected = {"label", "string_line", "string_bare", "cloze", "greedy", "sampled"}
        ck("all six v2 conditions present", set(conds) == expected,
           f"missing={expected - set(conds)} extra={set(conds) - expected}")
        for c in ("label", "string_line", "string_bare", "cloze", "greedy"):
            ck(f"{c}: one row per item", conds.get(c) == len(items), f"{conds.get(c)}")
        ck("sampled: k rows per item", conds.get("sampled") == len(items) * args.k,
           f"{conds.get('sampled')}")

        # No column may be silently dropped by DictWriter(extrasaction="ignore").
        for col in ("surface_form", "boundary_shift", "harness", "logprob_mass",
                    "degenerate_options"):
            ck(f"column '{col}' survives to the CSV", col in (rows[0] or {}))

        prob = [r for r in rows
                if r["condition"] in ("label", "string_line", "string_bare", "cloze")]
        masses = [float(r["logprob_mass"]) for r in prob if r["logprob_mass"]]
        scores = [float(r["score"]) for r in prob if r["score"]]
        ck("retained mass is a probability, in [0,1]",
           bool(masses) and all(0.0 <= m <= 1.0 for m in masses),
           f"max={max(masses):.4f}" if masses else "none")
        ck("scores lie on the 0-4 response scale",
           bool(scores) and all(0.0 <= s <= 4.0 for s in scores),
           f"[{min(scores):.3f}, {max(scores):.3f}]" if scores else "none")
        ck("every option found on every probability row",
           all(int(r["n_options_found"]) == 5 for r in prob),
           f"min={min(int(r['n_options_found']) for r in prob)}")
        ck("no degenerate (indistinguishable) options",
           not any(r["degenerate_options"] for r in prob))

        # The cloze arm must be visibly a DIFFERENT prompt, in the data, not just in prose.
        sha = {c: {r["prompt_sha"] for r in rows if r["condition"] == c} for c in expected}
        fixed = set().union(*(sha[c] for c in ("label", "string_line", "string_bare",
                                               "greedy", "sampled")))
        ck("the fixed-prompt arms share one prompt per item", len(fixed) == len(items),
           f"{len(fixed)} distinct sha for {len(items)} items")
        ck("cloze is recorded under a different prompt sha", not (sha["cloze"] & fixed))

        t = man["tokenization"]
        print(f"  tokenization probe: engine={t['engine_n_tokens']} "
              f"local_no_specials={t['local_n_no_specials']} "
              f"v1_boundary_was_correct={t['v1_boundary_was_correct']}")
        ck("tokenization probe recorded in the manifest", "engine_n_tokens" in t)
        ck("manifest serialises (no date/bytes leaking through)",
           isinstance(json.dumps(man), str))
        ck("harness version recorded", man.get("harness") == "v2")
        ck("cloze prompt sha recorded in manifest", "cloze_prompt_sha_first" in man)

        # THE POINT OF THE SECOND MODEL. Where the counts disagree, v1's boundary was wrong;
        # v2's must still be right — five options, valid mass, no degeneracy.
        if not t["v1_boundary_was_correct"]:
            ck("D1 path exercised: v2 unaffected by the local/engine mismatch",
               all(int(r["n_options_found"]) == 5 for r in prob)
               and all(0.0 <= float(r["logprob_mass"]) <= 1.0 for r in prob),
               f"engine-local={t['engine_minus_local_no_specials']}")
        return not t["v1_boundary_was_correct"]


def main() -> int:
    argparse.ArgumentParser().parse_args()
    from transformers import AutoTokenizer

    import run_experiment as R

    prompt_cfg, models_cfg, items, meta = R.load_cfg()
    items = items[:6]
    print("v2 harness smoke test (fake vLLM, real tokenizers, real run_model)")

    mismatch_seen = False
    for mid in TOKENIZERS:
        print(f"\n--- {mid} " + "-" * max(4, 58 - len(mid)))
        tok = AutoTokenizer.from_pretrained(mid)
        install_fake_vllm(tok)
        mismatch_seen |= run_one(R, prompt_cfg, models_cfg, items, meta, mid)

    check("at least one model exercised the D1 boundary-mismatch path", mismatch_seen,
          "otherwise this test never touches the defect it exists for")

    failed = [n for n, ok, _ in RESULTS if not ok]
    print(f"\n{len(RESULTS) - len(failed)}/{len(RESULTS)} checks passed")
    if failed:
        print("FAILED:")
        for n in failed:
            print(f"  - {n}")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
