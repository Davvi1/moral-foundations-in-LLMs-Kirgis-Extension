"""The headline numbers in FINDINGS.md must match what the data actually produces.

WHY THIS EXISTS. On 2026-08-10 two changes moved the project's most-quoted figure: excluding
a near-constant model (N 31 -> 30) and reclassifying Social Norms as the non-moral control it
was designed to be, rather than a seventh foundation. rho(label, sampled) went 0.842 -> 0.838
-> 0.818. Neither change was large, but the old number was quoted in five places across four
files, and finding them all took a manual sweep of exactly the kind that misses one.

`test_artifact_provenance.py` guards the *datasets* -- that a committed CSV holds the sample it
claims. This guards the *prose*: that the number in the write-up is the number the data gives.
Documentation drift is not cosmetic here. The whole project is an argument that measurement
choices move published numbers, so shipping a stale figure would be the paper refuting itself.

If a number legitimately changes, update the constant below **deliberately**, in a commit that
says why. A test edited thoughtlessly to go green is worse than no test; one that forces the
edit to be conscious is the point.
"""

from __future__ import annotations

import math
from pathlib import Path

import pandas as pd
import pytest

REPO = Path(__file__).resolve().parent.parent
DATA = REPO / "results" / "derived" / "analysis_long_v2.csv"
FINDINGS = REPO / "FINDINGS.md"

# Clifford built the Social Norms items as a non-moral CONTROL (2015, p.9, verified by fetching
# the paper). Averaging it into a foundation-level statistic inflated every cross-method
# correlation, because floor-bound items rank identically under every readout.
CONTROL = "Social Norms"
N_MORAL_FOUNDATIONS = 6
N_MODELS_ANALYSED = 30      # 31 collected; SmolLM2-1.7B excluded, see LIMITATIONS.md 22

# The Kirgis confound pair: top-3 logprob weighting (~ label) vs mean of ten samples (~ sampled).
HEADLINE_PAIR = ("label", "sampled")
HEADLINE_RHO = 0.818
TOLERANCE = 0.0005          # tight: this is a recomputation, not an approximation


def _load() -> pd.DataFrame:
    if not DATA.exists():
        pytest.skip(f"{DATA.name} not built")
    df = pd.read_csv(DATA)
    df = df[(~df["excluded"].astype(str).str.lower().isin(["true", "1"]))]
    return df.dropna(subset=["score"])


def _mean_spearman(df: pd.DataFrame, c1: str, c2: str, foundations) -> float:
    """Mean over foundations of the Spearman rho between model rankings under two conditions."""
    out = []
    for f in foundations:
        sub = df[df["foundation"] == f]
        a = sub[sub["condition"] == c1].groupby("model")["score"].mean()
        b = sub[sub["condition"] == c2].groupby("model")["score"].mean()
        common = sorted(set(a.index) & set(b.index))
        if len(common) < 3:
            continue
        out.append(a[common].rank().corr(b[common].rank()))
    return sum(out) / len(out)


def test_social_norms_is_not_counted_as_a_foundation():
    df = _load()
    founds = sorted(df["foundation"].unique())
    assert CONTROL in founds, "the control category should still be present in the data"
    moral = [f for f in founds if f != CONTROL]
    assert len(moral) == N_MORAL_FOUNDATIONS, (
        f"expected {N_MORAL_FOUNDATIONS} moral foundations plus the {CONTROL!r} control, "
        f"got {founds}")


def test_model_count_matches_the_documented_sample():
    df = _load()
    n = df["model"].nunique()
    assert n == N_MODELS_ANALYSED, (
        f"{n} models in the analysable data, but the write-up says {N_MODELS_ANALYSED}. "
        f"If the roster changed, update N_MODELS_ANALYSED and FINDINGS.md together.")


def test_headline_rho_matches_the_data():
    """rho(label, sampled) over the six MORAL foundations -- the number the write-up leads on."""
    df = _load()
    moral = [f for f in sorted(df["foundation"].unique()) if f != CONTROL]
    rho = _mean_spearman(df, *HEADLINE_PAIR, moral)
    assert math.isclose(rho, HEADLINE_RHO, abs_tol=TOLERANCE), (
        f"rho{HEADLINE_PAIR} over the six moral foundations is {rho:.4f}, but the constant "
        f"says {HEADLINE_RHO}. Recompute and update FINDINGS.md deliberately.")


def test_findings_quotes_the_current_headline_number():
    if not FINDINGS.exists():
        pytest.skip("FINDINGS.md missing")
    text = FINDINGS.read_text(encoding="utf-8")
    assert f"{HEADLINE_RHO}" in text, (
        f"FINDINGS.md does not contain the current headline rho ({HEADLINE_RHO}). "
        f"The prose has drifted from the data.")


def test_pooling_the_control_inflates_cross_method_agreement():
    """The reason the control must be reported separately, asserted rather than asserted-in-prose.

    Floor-bound items rank near-identically under every readout, so folding them into a
    foundation-level average makes methods look more agreeable than they are. If this ever
    stops being true the justification in FINDINGS.md 3 needs rewriting.
    """
    df = _load()
    founds = sorted(df["foundation"].unique())
    moral = [f for f in founds if f != CONTROL]
    rho_moral = _mean_spearman(df, *HEADLINE_PAIR, moral)
    rho_pooled = _mean_spearman(df, *HEADLINE_PAIR, founds)
    rho_control = _mean_spearman(df, *HEADLINE_PAIR, [CONTROL])
    assert rho_control > rho_moral, (
        "the control no longer shows higher cross-method agreement than the moral foundations; "
        "the floor-artifact explanation in FINDINGS.md 3 no longer holds")
    assert rho_pooled > rho_moral, "pooling the control should inflate the average"
