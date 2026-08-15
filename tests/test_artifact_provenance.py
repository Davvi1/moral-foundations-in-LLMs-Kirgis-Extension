"""Every committed derived artifact must declare, and match, the sample it came from.

WHY THIS EXISTS. On 2026-08-09 the primary analysis was run with
`--data analysis_long_v2.csv` and wrote its 31-model results **over the committed 20-model
`variance_ratio.csv`** — same filename, entirely different sample, and nothing about the file
looked wrong afterwards. That is C12 in docs/CORRECTIONS.md. It was caught by an inventory step
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

V1_MODELS = 20      # Phase-1 roster. Retained as documentation only -- the v1 collection was
                    # deleted 2026-08-10 (docs/V1_TO_V2.md); nothing asserts against it any more.
V2_MODELS = 31      # Phase-2/3 roster, 32 pinned minus Mistral-Large (deliberately uncollected)
V2_MODELS_ANALYSED = 30   # 31 collected minus SmolLM2-1.7B, dropped by the discrimination
                          # threshold on 2026-08-10. See docs/LIMITATIONS.md 22 -- the criterion is
                          # post hoc and is documented as such.


def _read(name: str):
    p = DERIVED / name
    if not p.exists():
        pytest.skip(f"{name} not present on this machine")
    return pd.read_csv(p)


# =======================================================================================
# The long-form datasets
# =======================================================================================

def test_v2_dataset_is_v2():
    d = _read("analysis_long_v2.csv")
    assert d.model.nunique() == V2_MODELS, (
        f"analysis_long_v2.csv holds {d.model.nunique()} models, expected {V2_MODELS}.")
    assert set(d.condition.unique()) == V2_CONDITIONS, set(d.condition.unique())


# =======================================================================================
# The fitted results
# =======================================================================================

def test_v2_variance_ratio_is_v2():
    """Both roster sizes are expected here, and the reason is not sloppiness.

    UPDATED 2026-08-10, deliberately, as this file's docstring requires. The v2 artifact now
    reports **two** model counts and both are correct:

      30  the `exclusions=True` rows — the PRIMARY specification. SmolLM2-1.7B is dropped by
          the discrimination threshold (LIMITATIONS 22).
      31  the `exclusions=False` rows — the sensitivity arm, which by definition ignores every
          exclusion rule, so it must still contain the excluded model.

    Asserting a single value would therefore be asserting that the sensitivity arm does not do
    its job. What must hold is that the PRIMARY arm is 30 and nothing exceeds the collected
    roster of 31.
    """
    d = _read("variance_ratio_v2.csv")
    primary = d[d.exclusions.astype(str).str.lower() == "true"]
    assert set(primary.n_models.unique()) == {V2_MODELS_ANALYSED}, (
        f"primary (exclusions=True) rows report n_models="
        f"{sorted(primary.n_models.unique())}, expected {V2_MODELS_ANALYSED}. docs/FINDINGS.md 2 "
        f"sources its R table from these rows.")
    assert set(d.n_models.unique()) <= {V2_MODELS_ANALYSED, V2_MODELS}, (
        f"unexpected roster size in variance_ratio_v2.csv: {sorted(d.n_models.unique())}")
    # n_methods is FIVE, not six. Cloze is excluded from the primary because it is scored
    # against a different prompt (C15) -- and this assertion previously read
    # `== {len(V2_CONDITIONS)}`, i.e. six, which ENCODED THE BUG AS CORRECT and is why nothing
    # caught it. The confounded fit lives in variance_ratio_v2_withcloze.csv and is checked
    # separately below.
    assert set(d.n_methods.unique()) == {len(V2_CONDITIONS) - 1}, (
        f"primary R table reports n_methods={sorted(d.n_methods.unique())}; expected "
        f"{len(V2_CONDITIONS) - 1} (the six v2 conditions minus cloze). If cloze is back in "
        f"the primary, R is inflated ~2.7x by a prompt-confounded arm -- see C15.")
    # The control must be labelled, or a downstream consumer can average it in as a foundation.
    assert "is_control" in d.columns, "is_control column missing — refit with the current script"
    assert d.is_control.astype(str).str.lower().eq("true").sum() > 0, "no row flagged as control"


def test_withcloze_artifact_is_the_confounded_sensitivity():
    """The confounded fit is KEPT, deliberately, and must be distinguishable from the primary.

    R roughly triples when cloze is included. Reporting both is the honest treatment: the gap is
    the largest researcher degree of freedom in this analysis. But the two must never be
    confusable, so the sensitivity carries six methods and its own filename.
    """
    d = _read("variance_ratio_v2_withcloze.csv")
    assert set(d.n_methods.unique()) == {len(V2_CONDITIONS)}, (
        "variance_ratio_v2_withcloze.csv should contain all six conditions including cloze")


@pytest.mark.parametrize("name,scan,fam", [
    ("variance_ratio_v2_noscan.csv", "True", "False"),
    ("variance_ratio_v2_family.csv", "False", "True"),
])
def test_sensitivity_artifacts_declare_their_variant(name, scan, fam):
    """Each sensitivity refit must be a DISTINCT file that says which variant it is.

    Without this the three runs would resolve to one filename and the last would win silently
    — C12 again, one layer up.
    """
    d = _read(name)
    assert set(d.scan_excluded.astype(str)) == {scan}, f"{name}: scan_excluded should be {scan}"
    assert set(d.family_effect.astype(str)) == {fam}, f"{name}: family_effect should be {fam}"
    primary = d[d.exclusions.astype(str).str.lower() == "true"]
    assert set(primary.n_models.unique()) == {V2_MODELS_ANALYSED}


# =======================================================================================
# No file may blend the two harnesses
# =======================================================================================


@pytest.mark.parametrize("name", ["analysis_long_v2.csv"])
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
