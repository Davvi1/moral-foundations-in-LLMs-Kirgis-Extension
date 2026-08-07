"""Sequence-length budget, measured on real tokenizers over all 116 real items.

`max_model_len` truncates silently in some paths. String scoring appends the option text to
an already-complete prompt, so it is the longest sequence in the study and the one most
likely to overflow. Measure it rather than assume it.
"""

from __future__ import annotations

import pytest

import conditions as C

MAX_MODEL_LEN = 1024   # the harness default
GEN_TOKENS = 96        # max_tokens for free generation


def _lengths(tok, prompt_cfg, items):
    out = []
    for i, q in items:
        p = C.render_prompt(tok, prompt_cfg, q, i)
        n = len(tok.encode(p.text, add_special_tokens=False))
        out.append(n)
    return out


def test_prompt_fits_with_room_for_generation(any_tok, prompt_cfg, items):
    name, tok = any_tok
    lens = _lengths(tok, prompt_cfg, items)
    worst = max(lens) + GEN_TOKENS
    assert worst < MAX_MODEL_LEN, (
        f"{name}: longest prompt {max(lens)} + {GEN_TOKENS} generated = {worst} "
        f">= max_model_len {MAX_MODEL_LEN}. Raise max_model_len or shorten generation.")


def test_string_scoring_sequence_fits(any_tok, prompt_cfg, items):
    """prompt + the longest option is the longest sequence we ever send."""
    name, tok = any_tok
    longest_opt = max(len(tok.encode(v, add_special_tokens=False))
                      for v in prompt_cfg["options"].values())
    worst = max(_lengths(tok, prompt_cfg, items)) + longest_opt
    assert worst < MAX_MODEL_LEN, f"{name}: string-scoring sequence {worst} exceeds budget"


def test_prompt_lengths_are_tightly_clustered(any_tok, prompt_cfg, items):
    """Items are one-sentence vignettes of controlled length (Clifford standardised them).
    A large spread would mean an item is malformed."""
    name, tok = any_tok
    lens = _lengths(tok, prompt_cfg, items)
    assert max(lens) - min(lens) < 60, (
        f"{name}: prompt length spread {min(lens)}..{max(lens)} is larger than expected "
        f"for a standardised instrument — check for a malformed item")


def test_report_budget(qwen_tok, prompt_cfg, items, capsys):
    """Not an assertion — prints the numbers so they are on the record."""
    lens = _lengths(qwen_tok, prompt_cfg, items)
    longest_opt = max(len(qwen_tok.encode(v, add_special_tokens=False))
                      for v in prompt_cfg["options"].values())
    with capsys.disabled():
        print(f"\n  Qwen prompt tokens: min={min(lens)} max={max(lens)} "
              f"mean={sum(lens)/len(lens):.1f}")
        print(f"  longest option: {longest_opt} tokens")
        print(f"  worst string-scoring sequence: {max(lens)+longest_opt} / {MAX_MODEL_LEN}")
        print(f"  worst free-generation sequence: {max(lens)+GEN_TOKENS} / {MAX_MODEL_LEN}")
