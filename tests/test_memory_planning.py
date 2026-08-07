"""Pre-flight VRAM planning.

Discovering that a model does not fit is cheap here and expensive on the pod, where it
arrives as an OOM *after* pulling tens of gigabytes of weights. These tests pin the
arithmetic against the actual roster and the actual card.
"""

from __future__ import annotations

import pytest

import run_experiment as R

# RTX PRO 4500 Blackwell, from `nvidia-smi` on the pod: 32623 MiB.
PRO_4500 = 32623 / 1024
PRO_6000 = 96.0


def test_small_models_fit_comfortably():
    for params in (0.5, 1.5, 3.0, 7.0, 8.0):
        util, why = R.plan_memory(params, PRO_4500, 0.85)
        assert util == 0.85, f"{params}B should fit at the default: {why}"


def test_9b_still_fits_at_default():
    util, _ = R.plan_memory(9.2, PRO_4500, 0.85)
    assert util == 0.85


def test_13b_is_tight_and_gets_raised_utilisation():
    util, why = R.plan_memory(13.7, PRO_4500, 0.85)
    assert util == 0.95, why
    assert "tight" in why.lower()


def test_14b_is_refused_before_download():
    util, why = R.plan_memory(14.0, PRO_4500, 0.85)
    assert util < 0, "14B must be refused on a 32 GiB card, not attempted"
    assert "WILL NOT FIT" in why
    assert "RTX PRO 6000" in why, "the message must say what to do instead"


def test_14b_fits_on_the_larger_card():
    """The documented escape route must actually work."""
    util, why = R.plan_memory(14.0, PRO_6000, 0.85)
    assert util == 0.85, why


def test_no_gpu_falls_back_to_default_without_crashing():
    util, why = R.plan_memory(7.0, None, 0.85)
    assert util == 0.85
    assert "no GPU" in why


def test_roster_split_between_the_two_cards_is_as_documented():
    """Exactly two models require the larger GPU. If this changes, RESUME.md is stale."""
    _, roster, _, _ = R.load_cfg()
    refused, tight, ok = [], [], []
    for m in roster["primary"]:
        util, _ = R.plan_memory(m["params_b"], PRO_4500, 0.85)
        (refused if util < 0 else tight if util == 0.95 else ok).append(m["id"])
    assert refused == ["Qwen/Qwen2.5-14B-Instruct"], refused
    assert tight == ["allenai/OLMo-2-1124-13B-Instruct"], tight
    assert len(ok) == 18, f"expected 18 comfortable models, got {len(ok)}"


def test_everything_fits_on_the_big_card():
    """Whole roster on one RTX PRO 6000 is the fallback if pod juggling goes wrong."""
    _, roster, _, _ = R.load_cfg()
    for m in roster["primary"]:
        util, why = R.plan_memory(m["params_b"], PRO_6000, 0.85)
        assert util > 0, f"{m['id']} does not fit even on a 96 GiB card: {why}"
