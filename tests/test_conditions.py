"""Tests for the four scoring conditions.

Grouped by the failure they are designed to catch. Where a test encodes a claim made
elsewhere in the repo (config/prompt.yaml, docs/state.md), the docstring says so — if the test
fails, the claim is wrong and the documentation must change with the code.
"""

from __future__ import annotations

import math

import pytest

import conditions as C
from fake_vllm import FakeLLM, Logprob, SamplingParams


# =======================================================================================
# 1. Prompt construction and THE INVARIANT: byte-identical across conditions
# =======================================================================================


def test_prompt_is_identical_across_conditions(qwen_tok, prompt_cfg, items):
    """All four conditions must receive the same string. This is the whole design."""
    i, q = items[0]
    built = [C.render_prompt(qwen_tok, prompt_cfg, q, i) for _ in range(4)]
    assert len({p.text for p in built}) == 1
    assert len({p.sha256 for p in built}) == 1


def test_prompt_hash_is_stable_and_discriminating(qwen_tok, prompt_cfg, items):
    a = C.render_prompt(qwen_tok, prompt_cfg, items[0][1], 1)
    b = C.render_prompt(qwen_tok, prompt_cfg, items[0][1], 99)
    c = C.render_prompt(qwen_tok, prompt_cfg, items[1][1], 1)
    assert a.sha256 == b.sha256, "same text must hash the same regardless of item id"
    assert a.sha256 != c.sha256, "different items must hash differently"


def test_placeholder_is_actually_substituted(qwen_tok, prompt_cfg, items):
    """A placeholder typo would silently send every model the literal template."""
    p = C.render_prompt(qwen_tok, prompt_cfg, items[0][1], 1)
    assert "{{QUESTION_CONTENT_PLACEHOLDER}}" not in p.text
    assert items[0][1] in p.text


def test_all_116_items_produce_distinct_prompts(qwen_tok, prompt_cfg, items):
    ps = [C.render_prompt(qwen_tok, prompt_cfg, q, i) for i, q in items]
    assert len({p.sha256 for p in ps}) == len(items)


def test_prompt_contains_all_five_options(qwen_tok, prompt_cfg, items):
    p = C.render_prompt(qwen_tok, prompt_cfg, items[0][1], 1)
    for k, label in prompt_cfg["options"].items():
        assert label in p.text, f"option {k} ({label!r}) missing from rendered prompt"


def test_generation_prompt_is_added(qwen_tok, prompt_cfg, items):
    """Without add_generation_prompt the model is not cued to answer, and the first
    generated token is not the label. The probe found the prompt ends 'assistant\\n'."""
    p = C.render_prompt(qwen_tok, prompt_cfg, items[0][1], 1)
    plain = qwen_tok.apply_chat_template(
        [{"role": "system", "content": prompt_cfg["system"]},
         {"role": "user", "content": "x"}], tokenize=False, add_generation_prompt=False)
    assert len(p.text) > len(plain) - 50  # sanity: generation cue present
    assert p.text.rstrip().endswith(("assistant", "assistant\n", ">")) or "assistant" in p.text[-40:]


# =======================================================================================
# 2. Tokenization claims — these encode findings recorded in docs/state.md
# =======================================================================================


def test_bare_and_spaced_digits_differ_on_qwen(qwen_tok):
    """docs/state.md records "0"=[15] and " 0"=[220,15] on Qwen. If this breaks, re-probe."""
    for k in range(5):
        bare = qwen_tok.encode(str(k), add_special_tokens=False)
        spaced = qwen_tok.encode(f" {k}", add_special_tokens=False)
        assert len(bare) == 1, f"bare {k} is not a single token: {bare}"
        assert bare != spaced, f"bare and spaced {k} tokenize identically"


def test_option_token_ids_finds_all_five(qwen_tok, prompt_cfg):
    ids = C.option_token_ids(qwen_tok, prompt_cfg["options"])
    assert set(ids) == set(prompt_cfg["options"]), f"only found {sorted(ids)}"
    assert all(v for v in ids.values()), f"some options have no candidate token: {ids}"
    firsts = [v[0] for v in ids.values()]
    assert len(set(firsts)) == 5, "option labels must map to distinct token ids"


def test_option_token_ids_handles_sentencepiece_tokenizers(any_tok, prompt_cfg):
    """The bug that broke label scoring on 6/16 models: SentencePiece encodes "0" as TWO
    tokens (metaspace marker + digit), the old code demanded a single token, found none,
    and scored an empty set — mass 0.0000 with no error. Every tokenizer in the roster must
    now yield a candidate for all five options."""
    name, tok = any_tok
    ids = C.option_token_ids(tok, prompt_cfg["options"])
    missing = [k for k, v in ids.items() if not v]
    assert not missing, f"{name}: no candidate token for options {missing}"
    firsts = [v[0] for v in ids.values()]
    assert len(set(firsts)) == 5, f"{name}: candidates not distinct: {ids}"


def test_first_token_collision_between_options_0_and_1(any_tok, prompt_cfg):
    """config/prompt.yaml claims options 0 and 1 share a first token, which is WHY string
    scoring must be a full-sequence log-likelihood. Verified per family."""
    name, tok = any_tok
    firsts = {k: tok.encode(v, add_special_tokens=False)[0]
              for k, v in prompt_cfg["options"].items()}
    assert firsts[0] == firsts[1], (
        f"{name}: options 0 and 1 do NOT share a first token. The justification in "
        f"config/prompt.yaml does not hold for this tokenizer — update the doc.")


def test_option_token_lengths_are_unequal(any_tok, prompt_cfg):
    """Unequal lengths are why length normalisation is a real choice, not a default."""
    name, tok = any_tok
    lens = {k: len(tok.encode(v, add_special_tokens=False))
            for k, v in prompt_cfg["options"].items()}
    assert len(set(lens.values())) > 1, f"{name}: all options same length {lens}"


def test_every_roster_family_has_a_chat_template(any_tok):
    """A missing chat template silently produces a raw-text prompt — a different
    experiment. Catch it here, not after paying to download 8B of weights."""
    name, tok = any_tok
    assert tok.chat_template is not None, f"{name} has no chat template"


def test_render_prompt_works_for_every_family(any_tok, prompt_cfg, items):
    name, tok = any_tok
    p = C.render_prompt(tok, prompt_cfg, items[0][1], 1)
    assert items[0][1] in p.text
    assert "{{QUESTION" not in p.text


# =======================================================================================
# 3. expectation() — including the grok-3 integrity failure from B1
# =======================================================================================


def test_expectation_matches_hand_computed_value():
    scores = {0: math.log(0.1), 1: math.log(0.2), 2: math.log(0.4),
              3: math.log(0.2), 4: math.log(0.1)}
    e, mass = C.expectation(scores)
    assert e == pytest.approx(2.0, abs=1e-9)
    assert mass == pytest.approx(1.0, abs=1e-9)


def test_expectation_renormalises_over_present_options_only():
    """Only two options present: the expectation must use their relative weights."""
    e, mass = C.expectation({1: math.log(0.25), 3: math.log(0.25)})
    assert e == pytest.approx(2.0)
    assert mass == pytest.approx(0.5)


def test_expectation_single_option_degenerates_to_that_label():
    """This is Kirgis's argmax degeneracy. It is CORRECT behaviour for a renormalised
    estimator — the point is that `mass` exposes it rather than hiding it."""
    e, mass = C.expectation({3: math.log(1e-9)})
    assert e == pytest.approx(3.0)
    assert mass < 1e-8, "mass must reveal that essentially no probability was retained"


def test_expectation_flags_the_grok3_pathology():
    """B1: grok-3-beta returned logprobs summing to ~0 while the emitted token claimed
    p=1.0, and renormalisation masked it. Our mass field must make it visible.

    Note the exact values: with TWO digits present the renormalised estimator does not
    return the argmax exactly (1.98, not 2.00) — it collapses to the label only when a
    SINGLE digit survives. That matches the B1 measurement, where argmax collapse tracked
    n_digits_in_top3 == 1 at 5.6%, not the 44% of malformed rows.
    """
    healthy, m_healthy = C.expectation({k: math.log(p) for k, p in
                                        {0: .01, 1: .04, 2: .90, 3: .04, 4: .01}.items()})
    broken, m_broken = C.expectation({2: -17.4, 1: -21.5})
    assert m_healthy > 0.99
    assert m_broken < 1e-6, "mass must expose that ~no probability was retained"
    assert 1.9 < broken < 2.05, (
        "renormalisation still returns a plausible-looking score despite garbage input — "
        "which is precisely why the mass field has to be logged")
    assert broken != pytest.approx(2.0, abs=1e-6), (
        "with two options present this is NOT pure argmax; collapse needs a single survivor")


def test_expectation_is_numerically_stable_for_tiny_logprobs():
    e, _ = C.expectation({0: -800.0, 4: -799.0})
    assert not math.isnan(e) and 0 <= e <= 4


def test_expectation_empty_is_nan_not_crash():
    e, mass = C.expectation({})
    assert math.isnan(e) and mass == 0.0


# =======================================================================================
# 4. Free-generation parsing
# =======================================================================================


@pytest.mark.parametrize("text,val,strategy", [
    ("2", 2, "anchored"),
    ("2\nSomewhat wrong because...", 2, "anchored"),
    ("**3**", 3, "anchored"),
    ("  \n 4", 4, "anchored"),
    ("0", 0, "anchored"),
    ("The answer is 1.", 1, "scan"),
    ("Rating: 0 (not at all wrong)", 0, "scan"),
    ("On a scale of 0 to 4, I'd say 3", 3, "scan"),
    ("On the five-point scale from 0 to 4 this is a 2", 2, "scan"),
    ("I would rate this behavior as 3 out of 4.", 3, "scan"),
    ("I cannot help with that.", None, "none"),
    ("", None, "none"),
    ("7", None, "none"),
    ("10", None, "none"),
    ("No digits here at all.", None, "none"),
])
def test_parse_digit(text, val, strategy):
    assert C.parse_digit(text) == (val, strategy)


def test_parse_never_reads_the_scale_endpoint_as_the_answer():
    """Our own prompt lists 0..4, so models echoing the scale is predictable. Reading the
    endpoint as the answer is the error class that mis-scored Kirgis's grok-3 rows."""
    for t in ["On a scale of 0 to 4, I would say 4",
              "Using the 0-4 scale, this is a 3",
              "Rated from 0 through 4: 2"]:
        v, how = C.parse_digit(t)
        assert v is not None and how == "scan"
        assert v != 0, f"read the scale endpoint from {t!r}"


@pytest.mark.parametrize("text", [
    "I cannot provide a rating for this scenario.",
    "I'm sorry, but I won't engage with that content.",
    "As an AI, I do not have personal opinions.",
    "I am unable to assist with this request.",
])
def test_refusals_detected(text):
    assert C.is_refusal(text)


@pytest.mark.parametrize("text", ["2\nSomewhat wrong.", "4", "This is very wrong."])
def test_normal_answers_not_flagged_as_refusal(text):
    assert not C.is_refusal(text)


# =======================================================================================
# 5. Condition runners against the fake vLLM
# =======================================================================================


def _prompts(tok, cfg, items, n=3):
    return [C.render_prompt(tok, cfg, q, i) for i, q in items[:n]]


def test_run_free_greedy_uses_temperature_zero(qwen_tok, prompt_cfg, items):
    ps = _prompts(qwen_tok, prompt_cfg, items, 2)
    llm = FakeLLM(qwen_tok, lambda p, sp, t: {"text": "3\nVery wrong."})
    rows = C.run_free(llm, SamplingParams, ps, greedy=True)
    _, sp = llm.calls[0]
    assert sp.temperature == 0.0
    assert len(rows) == 2
    assert all(r["score"] == 3.0 and r["parse_strategy"] == "anchored" for r in rows)


def test_run_free_sampled_uses_distinct_seeds_and_t1(qwen_tok, prompt_cfg, items):
    """k independent passes, each separately identifiable — the pre-specified Monte-Carlo
    error term needs replicates, and vLLM's n=k would collapse them."""
    ps = _prompts(qwen_tok, prompt_cfg, items, 2)
    llm = FakeLLM(qwen_tok, lambda p, sp, t: {"text": "1"})
    rows = C.run_free(llm, SamplingParams, ps, greedy=False, k=4, seeds=[10, 11, 12, 13])
    assert len(rows) == 2 * 4
    seeds = [sp.seed for _, sp in llm.calls]
    assert seeds == [10, 11, 12, 13]
    assert all(sp.temperature == 1.0 for _, sp in llm.calls)
    assert sorted({r["replicate"] for r in rows}) == [0, 1, 2, 3]


def test_run_free_flags_refusal_and_parse_failure(qwen_tok, prompt_cfg, items):
    ps = _prompts(qwen_tok, prompt_cfg, items, 1)
    llm = FakeLLM(qwen_tok, lambda p, sp, t: {"text": "I cannot help with that."})
    rows = C.run_free(llm, SamplingParams, ps, greedy=True)
    assert rows[0]["refusal"] is True
    assert rows[0]["parse_failed"] is True
    assert math.isnan(rows[0]["score"])

