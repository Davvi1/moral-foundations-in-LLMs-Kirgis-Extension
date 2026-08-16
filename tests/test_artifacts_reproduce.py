"""Every committed derived artifact must still reproduce from its generator.

WHY THIS EXISTS. `test_determinism.py` proves the analysis dataset rebuilds identically
under two PYTHONHASHSEED values — i.e. that the builder is deterministic. It does not
ask the different question this file asks: does what is COMMITTED still match what the
current code produces?

Those come apart silently. Two artifacts were found stale on 2026-08-16 during a
reproducibility audit: `measurement_error.md` and `social_norms_control.md` still cited
`references.md` and `FINDINGS.md` at the repository root, where their generators had
been updated to `docs/` when the ten documents moved on 2026-08-11. The numbers were
unaffected — the drift was entirely in embedded citations — but that is the C15 shape
again: `test_doc_citations.py` guards paths quoted in PROSE, and nobody had considered
that a GENERATED file also quotes paths, and goes stale the same way, and is regenerated
so rarely that nothing notices.

The failure this closes is more general than a path: an artifact whose generator has
moved on is evidence for a claim nobody can reproduce.

SCOPE, stated because the gaps are deliberate:
  - covered: everything runnable on a laptop from committed inputs (~22 s total)
  - NOT covered: variance_ratio_v2*.csv and mcmc_permutation_null_v2.csv, which need
    a C++ toolchain and hours of MCMC (requirements-fit.txt)
  - NOT covered: greedy_determinism.md, which compares v1 against v2 and v1 was
    deleted from the tree; and kirgis_rescored.csv, which needs a clone of someone
    else's repository
  - analysis_long_v2.csv is covered in CI instead, where the rebuild is compared with
    `git diff --exit-code`
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parent.parent
DERIVED = REPO / "results" / "derived"

# (script, artifact it writes). Each takes --out, so the regeneration is written to a
# temporary path and the committed file is never touched by the test.
GENERATORS = [
    ("analyse_scale.py", "scale_analysis.md"),
    ("analyse_controls.py", "controls_v2.md"),
    ("report_exclusions.py", "exclusions_v2.md"),
    ("audit_kirgis_pattern.py", "kirgis_pattern_audit_v2.md"),
    ("audit_refusal_leakage.py", "refusal_leakage_audit_v2.md"),
    ("audit_refusal_bias.py", "refusal_bias_audit.md"),
    ("analyse_social_norms.py", "social_norms_control.md"),
    ("analyse_measurement_error.py", "measurement_error.md"),
]


@pytest.mark.parametrize("script,artifact", GENERATORS,
                         ids=[a for _, a in GENERATORS])
def test_artifact_reproduces_from_its_generator(script, artifact, tmp_path):
    committed = DERIVED / artifact
    assert committed.exists(), f"{artifact} is cited but not committed"

    out = tmp_path / artifact
    r = subprocess.run([sys.executable, str(REPO / "scripts" / script),
                        "--out", str(out)],
                       cwd=REPO, capture_output=True, text=True)
    assert r.returncode == 0, f"{script} failed:\n{r.stderr[-1500:]}"
    assert out.exists(), f"{script} wrote nothing to --out"

    fresh, old = out.read_bytes(), committed.read_bytes()
    if fresh == old:
        return

    # Report the first differing line rather than a byte offset — the cause is almost
    # always a stale citation or a moved number, and both are legible as text.
    fl = fresh.decode("utf-8").splitlines()
    ol = old.decode("utf-8").splitlines()
    for i, (a, b) in enumerate(zip(ol, fl), 1):
        if a != b:
            pytest.fail(
                f"{artifact} no longer reproduces from {script}.\n"
                f"  first difference, line {i}\n"
                f"  committed: {a[:160]}\n"
                f"  regenerated: {b[:160]}\n"
                f"Re-run `python scripts/{script}` and commit the result.")
    pytest.fail(
        f"{artifact} differs from {script} in length only "
        f"({len(ol)} committed vs {len(fl)} regenerated lines).")
