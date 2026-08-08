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


def _split(card):
    """Partition the roster into (comfortable, tight, refused) on one card."""
    _, roster, _, _ = R.load_cfg()
    refused, tight, ok = [], [], []
    for m in roster["primary"]:
        util, _ = R.plan_memory(m["params_b"], card, 0.85)
        (refused if util < 0 else tight if util == 0.95 else ok).append(m["id"])
    return ok, tight, refused


def test_roster_split_on_the_small_card_is_as_documented():
    """The Phase-2 roster no longer fits one card, and that is by design.

    UPDATED 2026-08-08 with the N=30 roster. The previous version asserted the N=20 split and
    would now fail — correctly, because the roster deliberately changed. It is updated rather
    than deleted: the point of the test is that the *documented* plan matches the arithmetic,
    so when the plan moves, the assertion moves with it and stays a real check.
    """
    ok, tight, refused = _split(PRO_4500)
    assert len(ok) + len(tight) + len(refused) == 30, "roster is not N=30"
    assert tight == ["allenai/OLMo-2-1124-13B-Instruct"], tight
    assert len(refused) == 7, refused
    assert all(any(s in r for s in ("14B", "24B", "27b", "32B", "70B", "72B"))
               for r in refused), refused


def test_the_big_card_takes_everything_except_the_70B_pair():
    """96 GiB covers the roster up to 32B. The two 70B-class models are the exception.

    This is the assertion that replaces "everything fits on the big card", which the Phase-2
    roster made false ON PURPOSE — the scale ladders reach 70.6B and 72.7B specifically so
    that P5/P6 can be tested, and bf16 weights alone are ~146 GiB there. Silently relaxing
    the old test would have hidden a real planning constraint; asserting the new boundary
    keeps it visible.
    """
    ok, tight, refused = _split(PRO_6000)
    assert len(refused) == 2, refused
    assert sorted(refused) == ["Qwen/Qwen2.5-72B-Instruct",
                               "meta-llama/Llama-3.1-70B-Instruct"], refused
    assert not tight, tight
    assert len(ok) == 28


def test_the_70B_pair_is_refused_with_an_actionable_message():
    """Refusal must say what to do instead, or it reads as a mysterious crash on the pod."""
    for params in (70.6, 72.7):
        util, why = R.plan_memory(params, PRO_6000, 0.85)
        assert util < 0
        assert "WILL NOT FIT" in why
        assert "GiB" in why, "the message must quantify the shortfall"


def test_a_b200_class_card_takes_the_whole_roster():
    """The documented route for the 70B pair. If this fails, the scale ladders are unrunnable
    and P5/P6 cannot be evaluated at all — which would be a design problem, not a test bug."""
    ok, tight, refused = _split(180.0)
    assert not refused, refused
    assert len(ok) + len(tight) == 30
