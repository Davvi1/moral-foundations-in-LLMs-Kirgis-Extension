"""Design decisions written in prose must be enforced by code.

WHY THIS EXISTS — C15. `config/prompt.yaml`, `docs/METHODOLOGY_REVIEW.md` and
`audit_kirgis_pattern.py` all stated that the cloze arm is **excluded from the primary variance
ratio**, because cloze is scored against a different prompt and a method-effect estimate
containing it is confounded with prompt. `analyse_variance_ratio.py` never implemented it. Every
R the project published included cloze, and a leave-one-out check puts the inflation at roughly
+100% — an order of magnitude larger than any sensitivity we ran deliberately.

Nothing caught it for weeks. Worse, `test_artifact_provenance.py` asserted `n_methods == 6`,
which **encoded the bug as correct**.

The general failure is not "we forgot about cloze". It is that a commitment recorded only in
prose has nothing enforcing it, and prose does not fail a test run. These tests are the
enforcement for the commitments load-bearing enough that violating them would invalidate a
published number.

They are deliberately SOURCE-LEVEL where the artifact is stale. The committed R tables still
contain cloze — they predate the fix and are flagged pending refit — so asserting against the
artifacts would fail for a reason that is already known and documented. Asserting against the
code guards the fix from regression, which is the thing that can silently break again.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parent.parent
SCRIPTS = REPO / "scripts"


def _src(name: str) -> str:
    p = SCRIPTS / name
    if not p.exists():
        pytest.skip(f"{name} not present")
    return p.read_text(encoding="utf-8")


def test_variance_ratio_excludes_cloze_by_default():
    """The C15 fix must stay. Cloze is prompt-varying; R is defined as a method effect."""
    s = _src("analyse_variance_ratio.py")
    assert "include_cloze" in s, (
        "analyse_variance_ratio.py has no cloze handling at all. This is the exact state that "
        "produced C15 — R inflated ~100% by a prompt-confounded arm.")
    # The filter must be conditional on the OPT-IN flag, i.e. cloze goes unless asked for.
    assert re.search(r"if not args\.include_cloze", s), (
        "cloze is not excluded by default. The design (config/prompt.yaml:33, "
        "docs/METHODOLOGY_REVIEW.md:13) requires exclusion from the PRIMARY; including it must be "
        "an explicit opt-in, never the default.")
    assert re.search(r'!=\s*["\']cloze["\']', s), (
        "no filter dropping rows where condition == 'cloze'")


def test_including_cloze_writes_a_distinct_file():
    """If someone opts in, the result must not overwrite the primary artifact (the C12 shape)."""
    s = _src("analyse_variance_ratio.py")
    assert "_withcloze" in s, (
        "--include-cloze does not change the output filename, so a confounded fit would "
        "silently overwrite the primary R table.")


def test_the_control_category_is_labelled_in_output():
    """Social Norms is a non-moral control (Clifford 2015 p.9), not a seventh foundation.

    `docs/ANALYSIS_PLAN.md:164` requires it be "reported separately and never averaged in". Before
    2026-08-10 it was pooled into every cross-method rank correlation, inflating them by
    0.005–0.029. The output must carry the flag that makes pooling a visible choice.
    """
    s = _src("analyse_variance_ratio.py")
    assert "CONTROL_FOUNDATION" in s and "is_control" in s, (
        "the variance-ratio output does not flag the non-moral control, so a downstream "
        "consumer can average it in as a foundation — which is what happened.")


def test_the_discrimination_rule_is_a_threshold_not_a_named_model():
    """A post hoc exclusion is only defensible if it is a uniform rule.

    `docs/LIMITATIONS.md` §22 records that the criterion was defined after seeing the data. That is
    survivable because it applies to anything below the cut. Hard-coding the model that
    triggered it would make it unfalsifiable.
    """
    s = _src("build_analysis_data.py")
    assert "min_discrimination" in s, "the discrimination rule is missing"
    # Naming the model in a COMMENT is fine and in fact desirable — the reader should know
    # which model triggered the rule. What must never appear is a model name in the control
    # flow. Strip comments before checking.
    code = "\n".join(re.sub(r"#.*$", "", ln) for ln in s.splitlines())
    code = re.sub(r'""".*?"""', "", code, flags=re.S)
    for name in ("SmolLM2", "smollm"):
        assert name not in code, (
            f"build_analysis_data.py branches on the model name {name!r}. The exclusion must "
            f"be a uniform threshold applied to whatever falls below it — see docs/LIMITATIONS.md "
            f"§22, which only survives review because the rule is general.")


def test_prompt_invariant_is_asserted_not_assumed():
    """The whole design rests on one prompt across conditions. QA must verify it every run."""
    s = _src("validate_results.py")
    assert "prompt_sha" in s, "the QA pass does not check the prompt invariant"
    assert "cloze_arms" in s or "CLOZE_ARMS" in s, (
        "the QA pass does not treat cloze as the declared exception to the prompt invariant, "
        "so it would either fail on cloze or silently accept a prompt change anywhere.")
