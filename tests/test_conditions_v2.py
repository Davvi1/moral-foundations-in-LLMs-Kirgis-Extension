"""Tests for the v2 forced-continuation scorer. Runs on a laptop; no GPU, no model weights.

    python scripts/test_conditions_v2.py              # offline, known-answer tests only
    python scripts/test_conditions_v2.py --online     # + real roster tokenizers (downloads
                                                      #   tokenizer files only, a few MB)

WHY THIS FILE EXISTS. v1's scoring bugs did not raise exceptions. They returned plausible
floats. Label scoring on SentencePiece models returned a renormalised expectation over an
EMPTY candidate set and reported mass 0.0000; internlm's string arm failed a boundary
assertion 116/116 times and produced a column of NaN. Both looked like data. The only reason
either was caught was that retained mass had been logged for an unrelated reason.

So the v2 scorer gets known-answer tests against a FAKE engine whose logprobs I choose,
where the correct expectation can be computed by hand. If the machinery is right, it must
reproduce the hand-computed number exactly. Each test targets one specific way v1 broke.
"""

from __future__ import annotations

import argparse
import math
import sys
from dataclasses import dataclass
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

from conditions import Prompt  # noqa: E402
from conditions_v2 import (  # noqa: E402
    lcp_len,
    score_forced_continuations,
    surface_forms,
)

OPTIONS = {0: "Not at all wrong", 1: "Not too wrong", 2: "Somewhat wrong",
           3: "Very wrong", 4: "Extremely wrong"}

NEG = math.log(1e-12)   # "this surface variant is effectively never written"


# ---------------------------------------------------------------------------------------
# a fake vLLM: we control the tokenization and every logprob
# ---------------------------------------------------------------------------------------


@dataclass
class _LP:
    logprob: float


class _Out:
    def __init__(self, ids, lps):
        self.prompt_token_ids = list(ids)
        # vLLM reports None at position 0 (nothing precedes it); mirror that exactly, since
        # mishandling it is a realistic bug and the scorer must survive it.
        self.prompt_logprobs = [None] + [{i: _LP(v)} for i, v in zip(ids[1:], lps[1:])]


class FakeLLM:
    """Maps submitted text -> (token ids, per-token logprobs). Anything unmapped is a bug."""

    def __init__(self, table):
        self.table = table
        self.seen = []

    def generate(self, texts, sp):
        self.seen = list(texts)
        missing = [t for t in texts if t not in self.table]
        if missing:
            raise AssertionError(f"engine asked for {len(missing)} unmapped text(s): {missing[:2]}")
        return [_Out(*self.table[t]) for t in texts]


def _sp(**kw):
    return kw


def build_table(prompt_text, base_ids, per_option, *, form="label",
                space_variant=None, merge_last=None):
    """Construct the fake engine's lookup table.

    per_option: {k: (suffix_ids, suffix_logprobs)} for the BARE surface variant.
    space_variant: {k: (suffix_ids, suffix_logprobs)} for the " k" variant; defaults to a
                   distinct id with negligible probability.
    merge_last: if given, the id that the final prompt token BECOMES when text is appended --
                i.e. a tokenizer that re-merges across the join. This is the internlm case.
    """
    forms = surface_forms(OPTIONS, form)
    table = {prompt_text: (base_ids, [0.0] * len(base_ids))}
    for k, variants in forms.items():
        for vi, v in enumerate(variants):
            if vi == 0:
                sfx_ids, sfx_lps = per_option[k]
            elif space_variant and k in space_variant:
                sfx_ids, sfx_lps = space_variant[k]
            else:
                sfx_ids, sfx_lps = ([900 + k], [NEG])
            head = list(base_ids)
            if merge_last is not None:
                head = head[:-1] + [merge_last]
            ids = head + list(sfx_ids)
            lps = [0.0] * len(head) + list(sfx_lps)
            if merge_last is not None:
                lps[len(head) - 1] = 0.0
            table[prompt_text + v] = (ids, lps)
    return table


def run_one(table, form="label", length_normalise=False):
    llm = FakeLLM(table)
    p = Prompt(text=next(iter(table)), item_id=1)
    rows = score_forced_continuations(llm, _sp, [p], OPTIONS, form,
                                      length_normalise=length_normalise)
    assert len(rows) == 1
    return rows[0]


# ---------------------------------------------------------------------------------------
# tests
# ---------------------------------------------------------------------------------------

RESULTS = []


def check(name, cond, detail=""):
    """Record, print, and ASSERT.

    The assert was added when these files moved into tests/ on 2026-08-11. Without it pytest
    collects the test_* functions, runs them, sees no exception and reports PASS even when
    every check inside failed — which would have been worse than leaving them uncollected,
    because the suite would have gone green while covering nothing.

    `main()` still catches the assertion per test function, so the standalone runner keeps
    printing the full report instead of stopping at the first failure.
    """
    RESULTS.append((name, bool(cond), detail))
    print(f"  {'PASS' if cond else 'FAIL'}  {name}{('  — ' + detail) if detail else ''}")
    assert cond, f"{name}{('  — ' + detail) if detail else ''}"


def test_known_answer():
    """The expectation must equal the hand-computed value, and mass must equal 1.

    Probabilities chosen so E[k] is exact in decimal:
        p = [0.1, 0.2, 0.4, 0.2, 0.1]
        E = 0(.1) + 1(.2) + 2(.4) + 3(.2) + 4(.1) = 2.000
    """
    print("\n[1] exactness — hand-computed expectation")
    probs = [0.1, 0.2, 0.4, 0.2, 0.1]
    base = [1, 2, 3]
    per_option = {k: ([10 + k], [math.log(probs[k])]) for k in range(5)}
    r = run_one(build_table("PROMPT", base, per_option))
    check("expectation is exact", abs(r["score"] - 2.0) < 1e-9, f"score={r['score']:.12f}")
    check("retained mass is 1.0", abs(r["logprob_mass"] - 1.0) < 1e-6,
          f"mass={r['logprob_mass']:.9f}")
    check("all five options present", r["n_options_found"] == 5)
    check("no boundary shift on a concatenative tokenizer", r["boundary_shift"] == 0)


def test_no_truncation():
    """F2: an option with vanishing probability must still be SCORED, not dropped.

    v1 read a top-20 list. An option outside it was absent, not small -- so the expectation
    silently became an average over a subset. Here option 4 has probability 1e-9. It must
    appear in the output with n_options_found == 5.
    """
    print("\n[2] F2 — a tiny probability is small, not missing")
    lps = [math.log(x) for x in (0.25, 0.25, 0.25, 0.25 - 1e-9, 1e-9)]
    per_option = {k: ([10 + k], [lps[k]]) for k in range(5)}
    r = run_one(build_table("PROMPT", [1, 2, 3], per_option))
    check("option 4 retained despite p=1e-9", r["n_options_found"] == 5)
    expected = sum(k * math.exp(lps[k]) for k in range(5)) / sum(math.exp(v) for v in lps)
    check("expectation matches direct computation", abs(r["score"] - expected) < 1e-9,
          f"{r['score']:.9f} vs {expected:.9f}")


def test_boundary_merge():
    """F8: the internlm case. Appending text changes the LAST prompt token.

    v1 asserted the option's tokens begin at len(tokenize(prompt)); when the tokenizer
    re-merged across the join, that assertion failed and the whole row was voided -- 116/116
    on internlm2_5-7b-chat. v2 measures the boundary instead of assuming it, so the row must
    survive AND report the shift.
    """
    print("\n[3] F8 — non-concatenative tokenizer (the internlm failure)")
    probs = [0.1, 0.2, 0.4, 0.2, 0.1]
    per_option = {k: ([10 + k], [math.log(probs[k])]) for k in range(5)}
    r = run_one(build_table("PROMPT", [1, 2, 3], per_option, merge_last=77))
    check("row survives a merge across the join", r["n_options_found"] == 5)
    check("shift is measured and reported", r["boundary_shift"] == 1,
          f"boundary_shift={r['boundary_shift']}")
    check("flagged as not-clean for the write-up", r["token_boundary_clean"] is False)
    # The merged token is shared by all five options, so it contributes an identical constant
    # to each and cancels in the softmax. The expectation must be unchanged from test [1].
    check("shared merged token cancels; expectation unchanged",
          abs(r["score"] - 2.0) < 1e-9, f"score={r['score']:.12f}")


def test_variant_dedup():
    """Two surface variants that tokenize IDENTICALLY must not be counted twice.

    If a tokenizer normalises " 3" to the same ids as "3", summing both would double that
    option's probability -- inflating whichever options the quirk happened to hit. This is
    the subtlest failure in the module and the one most likely to survive eyeballing.
    """
    print("\n[4] double-counting — identical variants collapse")
    probs = [0.1, 0.2, 0.4, 0.2, 0.1]
    per_option = {k: ([10 + k], [math.log(probs[k])]) for k in range(5)}
    # Option 2's space-variant tokenizes exactly like its bare variant.
    same = {2: ([12], [math.log(probs[2])])}
    r = run_one(build_table("PROMPT", [1, 2, 3], per_option, space_variant=same))
    check("no inflation of the duplicated option", abs(r["score"] - 2.0) < 1e-9,
          f"score={r['score']:.12f} (2.0 = undoubled)")
    check("mass still 1.0, not 1.4", abs(r["logprob_mass"] - 1.0) < 1e-6,
          f"mass={r['logprob_mass']:.9f}")


def test_variant_sum():
    """Distinct variants of the same option must SUM, being mutually exclusive events.

    Split option 2's probability evenly between "2" and " 2". P(answer is 2) is still 0.4, so
    the expectation must return to 2.0. If the code took a max instead of a sum it would come
    back with only half of option 2's mass and a different expectation.
    """
    print("\n[5] surface variants are alternative spellings of one answer")
    probs = [0.1, 0.2, 0.4, 0.2, 0.1]
    per_option = {k: ([10 + k], [math.log(probs[k] if k != 2 else 0.2)]) for k in range(5)}
    split = {2: ([912], [math.log(0.2)])}
    r = run_one(build_table("PROMPT", [1, 2, 3], per_option, space_variant=split))
    check("split spelling recombines to the same answer", abs(r["score"] - 2.0) < 1e-9,
          f"score={r['score']:.12f}")
    check("mass recovers to 1.0", abs(r["logprob_mass"] - 1.0) < 1e-6,
          f"mass={r['logprob_mass']:.9f}")


def test_unequal_boundaries():
    """Options whose boundaries differ must all be scored from the SAME point.

    If option 0 conditions on 3 tokens and option 1 on 2, their log-probabilities are not
    comparable and the softmax across options is meaningless. The scorer takes the minimum
    common prefix over every variant, so all five condition on an identical prefix.
    """
    print("\n[6] comparability — one shared conditioning prefix for all options")
    base = [1, 2, 3]
    probs = [0.1, 0.2, 0.4, 0.2, 0.1]
    table = {"PROMPT": (base, [0.0, 0.0, 0.0])}
    forms = surface_forms(OPTIONS, "label")
    for k, variants in forms.items():
        for vi, v in enumerate(variants):
            if vi == 1:
                ids, lps = base + [900 + k], [0.0] * 3 + [NEG]
            elif k == 1:
                # option 1 re-merges the final prompt token: its boundary is 2, not 3
                ids = base[:-1] + [77, 11]
                lps = [0.0, 0.0, math.log(0.5), math.log(probs[k] / 0.5)]
            else:
                ids, lps = base + [10 + k], [0.0] * 3 + [math.log(probs[k])]
            table["PROMPT" + v] = (ids, lps)
    r = run_one(table)
    check("shared boundary is the minimum (2, not 3)", r["boundary_shift"] == 1,
          f"boundary_shift={r['boundary_shift']}")
    check("all options scored from it", r["n_options_found"] == 5)
    check("expectation unchanged by the re-merge", abs(r["score"] - 2.0) < 1e-9,
          f"score={r['score']:.12f}")


def test_surface_forms():
    print("\n[7] surface forms are what we think they are")
    lab = surface_forms(OPTIONS, "label")
    line = surface_forms(OPTIONS, "line")
    bare = surface_forms(OPTIONS, "bare")
    check("label probes the digit", lab[3][0] == "3", repr(lab[3]))
    check("line probes the displayed option line", line[3][0] == "3: Very wrong", repr(line[3][0]))
    check("bare probes the phrase alone (v1's probe)", bare[3][0] == "Very wrong")
    check("every form offers a space-prefixed variant",
          all(v[1] == " " + v[0] for f in (lab, line, bare) for v in f.values()))


def test_engine_call_shape():
    """One generate call, and it must include the bare prompt as its own sequence.

    The bare prompt is submitted rather than tokenized locally so that the common-prefix
    comparison happens between two tokenizations produced by the SAME engine under the same
    settings. Comparing a local tokenization against vLLM's would reintroduce exactly the
    class of mismatch this module exists to eliminate.
    """
    print("\n[8] engine call shape")
    probs = [0.2] * 5
    per_option = {k: ([10 + k], [math.log(probs[k])]) for k in range(5)}
    table = build_table("PROMPT", [1, 2, 3], per_option)
    llm = FakeLLM(table)
    score_forced_continuations(llm, _sp, [Prompt(text="PROMPT", item_id=1)], OPTIONS, "label")
    check("bare prompt submitted for engine-side tokenization", "PROMPT" in llm.seen)
    check("one sequence per option x variant, plus the bare prompt",
          len(llm.seen) == 1 + 5 * 2, f"{len(llm.seen)} sequences")


# ---------------------------------------------------------------------------------------
# online: the real roster tokenizers
# ---------------------------------------------------------------------------------------


def test_real_tokenizers():
    """Does the LCP boundary behave on the actual roster? internlm is the one that matters.

    No GPU and no weights: tokenizer files only. This computes, per model per surface form,
    where the boundary lands and whether the naive `len(tokenize(prompt))` assumption would
    have held -- i.e. how much of the roster v1's string arm was silently at risk on.
    """
    from transformers import AutoTokenizer

    print("\n[9] real roster tokenizers (downloads tokenizer files only)")
    models = [
        ("Qwen/Qwen2.5-0.5B-Instruct", False),
        ("mistralai/Mistral-7B-Instruct-v0.3", False),
        ("microsoft/Phi-3-mini-4k-instruct", False),
        ("01-ai/Yi-1.5-9B-Chat", False),
        ("HuggingFaceTB/SmolLM2-1.7B-Instruct", False),
        ("internlm/internlm2_5-7b-chat", True),
    ]
    sysmsg = "You are answering a survey. Answer with one of the given options."
    user = ("Please rate how morally wrong this behavior is on the following five-point "
            "scale: You see a woman lie about her income.\n\n0: Not at all wrong\n"
            "1: Not too wrong\n2: Somewhat wrong\n3: Very wrong\n4: Extremely wrong\n")

    print(f"  {'model':<40} {'form':<6} {'shift':>5}  {'distinct?':>9}")
    any_shift = False
    for mid, trc in models:
        try:
            tok = AutoTokenizer.from_pretrained(mid, trust_remote_code=trc)
            try:
                text = tok.apply_chat_template(
                    [{"role": "system", "content": sysmsg}, {"role": "user", "content": user}],
                    tokenize=False, add_generation_prompt=True)
            except Exception:
                text = tok.apply_chat_template(
                    [{"role": "user", "content": f"{sysmsg}\n\n{user}"}],
                    tokenize=False, add_generation_prompt=True)
        except Exception as exc:
            print(f"  {mid:<40} SKIP  {type(exc).__name__}: {str(exc)[:60]}")
            continue

        base = tok.encode(text, add_special_tokens=False)
        for form in ("label", "line", "bare"):
            forms = surface_forms(OPTIONS, form)
            boundaries, suffixes = [], {}
            for k, variants in forms.items():
                for v in variants:
                    ids = tok.encode(text + v, add_special_tokens=False)
                    b = lcp_len(base, ids)
                    boundaries.append(b)
                    suffixes.setdefault(k, []).append(tuple(ids[b:]))
            shift = len(base) - min(boundaries)
            # Every option must remain distinguishable from every other after the boundary.
            flat = {k: set(v) for k, v in suffixes.items()}
            distinct = all(not (flat[a] & flat[b]) for a in flat for b in flat if a < b)
            any_shift = any_shift or shift > 0
            print(f"  {mid:<40} {form:<6} {shift:>5}  {str(distinct):>9}")
            check(f"{mid.split('/')[-1]}/{form}: options remain distinguishable", distinct)

    if any_shift:
        print("\n  NOTE: a nonzero shift is the v1 failure mode. v2 measures it instead of\n"
              "  asserting it away, so these models are scorable rather than voided.")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--online", action="store_true",
                    help="also check real roster tokenizers (downloads tokenizer files)")
    args = ap.parse_args()

    print("v2 forced-continuation scorer — known-answer tests")
    suite = [test_known_answer, test_no_truncation, test_boundary_merge, test_variant_dedup,
             test_variant_sum, test_unequal_boundaries, test_surface_forms,
             test_engine_call_shape]
    if args.online:
        suite.append(test_real_tokenizers)
    for fn in suite:
        # check() asserts now, so a failure would abort the run. Swallow it here ONLY: the
        # failure is already recorded in RESULTS and reported below, and the standalone
        # runner's value is showing every check, not stopping at the first bad one.
        try:
            fn()
        except AssertionError:
            pass

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
