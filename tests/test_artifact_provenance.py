"""Every committed derived artifact must declare, and match, the sample it came from.

WHY THIS EXISTS. On 2026-08-09 the primary analysis was run with
`--data analysis_long_v2.csv` and wrote its 31-model results **over the committed 20-model
`variance_ratio.csv`** — same filename, entirely different sample, and nothing about the file
looked wrong afterwards. That is C12 in CORRECTIONS.md. It was caught by an inventory step
noticing a missing file, not by anything checking the contents.

The naming convention is: **unsuffixed = v1 (the N=20 Phase-1 harness), `_v2` = the N=31
forced-continuation harness.** Until now that convention lived only in my head and in commit
messages, which is precisely how it got violated. These tests make it structural: if an
artifact ever holds the wrong sample, or two harnesses' conditions get blended into one file,
the suite fails loudly.

If the roster legitimately changes, these numbers must be updated **deliberately**, in a
commit that says so. A test that is edited thoughtlessly to make it pass is worse than no
test — but one that forces the edit to be conscious is the point.
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest

REPO = Path(__file__).resolve().parent.parent
DERIVED = REPO / "results" / "derived"

# The two harnesses, and what each is allowed to contain.
V1_CONDITIONS = {"label", "string", "greedy", "sampled"}
V2_CONDITIONS = {"label", "string_line", "string_bare", "cloze", "greedy", "sampled"}

V1_MODELS = 20      # Phase-1 roster
V2_MODELS = 31      # Phase-2/3 roster, 32 pinned minus Mistral-Large (deliberately uncollected)


def _read(name: str):
    p = DERIVED / name
    if not p.exists():
        pytest.skip(f"{name} not present on this machine")
    return pd.read_csv(p)


# =======================================================================================
# The long-form datasets
# =======================================================================================


def test_v1_dataset_is_v1():
    d = _read("analysis_long.csv")
    assert d.model.nunique() == V1_MODELS, (
        f"analysis_long.csv holds {d.model.nunique()} models, expected {V1_MODELS}. "
        "If this is a v2 file wearing a v1 name, see CORRECTIONS.md C12.")
    assert set(d.condition.unique()) == V1_CONDITIONS, set(d.condition.unique())


def test_v2_dataset_is_v2():
    d = _read("analysis_long_v2.csv")
    assert d.model.nunique() == V2_MODELS, (
        f"analysis_long_v2.csv holds {d.model.nunique()} models, expected {V2_MODELS}.")
    assert set(d.condition.unique()) == V2_CONDITIONS, set(d.condition.unique())


# =======================================================================================
# The fitted results
# =======================================================================================


def test_v1_variance_ratio_is_v1():
    """The specific file C12 clobbered. FINDINGS.md sources its R table from this."""
    d = _read("variance_ratio.csv")
    assert set(d.n_models.unique()) == {V1_MODELS}, (
        f"variance_ratio.csv reports n_models={sorted(d.n_models.unique())}, expected "
        f"{V1_MODELS}. This file backs the R table in FINDINGS.md; if it now holds v2 "
        "results, that table is citing a sample it does not describe.")
    assert set(d.n_methods.unique()) == {len(V1_CONDITIONS)}


def test_v2_variance_ratio_is_v2():
    d = _read("variance_ratio_v2.csv")
    assert set(d.n_models.unique()) == {V2_MODELS}
    assert set(d.n_methods.unique()) == {len(V2_CONDITIONS)}


# =======================================================================================
# No file may blend the two harnesses
# =======================================================================================


@pytest.mark.parametrize("name", ["analysis_long.csv", "analysis_long_v2.csv"])
def test_no_dataset_blends_harnesses(name):
    """`build_analysis_data.py`'s glob once matched every *.csv in results/raw, which now
    holds both harnesses. Building without --suffix would have interleaved two incompatible
    condition sets into one file that still looked plausible."""
    d = _read(name)
    conds = set(d.condition.unique())
    assert conds in (V1_CONDITIONS, V2_CONDITIONS), (
        f"{name} contains conditions {sorted(conds)}, which is neither the v1 set nor the v2 "
        "set. This is a blended dataset and nothing computed from it is interpretable.")


def test_every_derived_csv_with_a_condition_column_is_internally_consistent():
    """Sweep: any derived CSV carrying conditions must hold exactly one harness's set."""
    offenders = []
    for p in sorted(DERIVED.glob("*.csv")):
        try:
            d = pd.read_csv(p, nrows=None)
        except Exception:
            continue
        if "condition" not in d.columns:
            continue
        conds = set(d.condition.dropna().unique())
        if conds and conds not in (V1_CONDITIONS, V2_CONDITIONS):
            # subsets are fine (a report may cover only the probability arms)
            if not (conds <= V1_CONDITIONS or conds <= V2_CONDITIONS):
                offenders.append(f"{p.name}: {sorted(conds)}")
    assert not offenders, "derived files mixing harnesses:\n  " + "\n  ".join(offenders)


# =======================================================================================
# The v2-only fitted artifacts must be named for it
# =======================================================================================


def test_v2_only_artifacts_carry_the_v2_suffix():
    """The seed audit and the permutation null were run on v2 only.

    Under the naming convention an unsuffixed name means v1, so leaving these unsuffixed
    asserts something false about their provenance. This is the same class of ambiguity that
    made C12 possible — a file whose sample you can only know by remembering.
    """
    for stem in ("variance_ratio_seed_audit", "mcmc_permutation_null"):
        unsuffixed = DERIVED / f"{stem}.csv"
        suffixed = DERIVED / f"{stem}_v2.csv"
        if unsuffixed.exists() and not suffixed.exists():
            pytest.fail(
                f"{stem}.csv exists without a harness suffix. It was produced from the v2 "
                f"dataset, but an unsuffixed name means v1 by convention. Rename to "
                f"{stem}_v2.csv.")
