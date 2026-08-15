"""Committed artifacts must be a deterministic function of their inputs.

This file exists because that was twice untrue, and neither instance was caught by anything
watching — both were found by accident while doing something else.

    C10  build_analysis_data.py     dominant = max(set(ft), key=ft.count)
    C11  analyse_variance_ratio.py  seed = abs(hash(tag)) % 10000

Both are the same root cause: **CPython randomises string hashing per process**
(PYTHONHASHSEED). `hash()` on a str differs between runs, and iteration order of a `set` of
strings differs with it, so `max()` over a set resolves ties differently run to run. C10
flipped 28 rows of a committed dataset. C11 seeded the MCMC for the primary estimand, so
`variance_ratio.csv` — every R median, every interval, every banded verdict — could not be
regenerated from its own input.

The one-line fixes do not stop the third instance. These tests do.
"""

from __future__ import annotations

import filecmp
import os
import re
import subprocess
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parent.parent
SCRIPTS = sorted((REPO / "scripts").glob("*.py"))


# =======================================================================================
# Static guards — cheap, and they fail on the defect rather than on its consequences
# =======================================================================================

# `hash(` preceded by a word char is a method/attribute (e.g. `sha256().hexdigest`), not the
# builtin. We want bare builtin calls only.
BUILTIN_HASH = re.compile(r"(?<![\w.])hash\s*\(")


@pytest.mark.parametrize("path", SCRIPTS, ids=lambda p: p.name)
def test_no_builtin_hash_on_anything_persisted(path: Path):
    """The builtin `hash()` is not stable across processes. Never use it for a seed, an id,
    a filename, or anything that reaches disk.

    `hashlib.sha256` is the correct tool and is already used at conditions.py:55 and in
    analyse_variance_ratio.stable_seed(). If a genuinely ephemeral use ever appears, add an
    explicit `# noqa: determinism` on the line and it will be skipped.
    """
    offenders = []
    for n, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        stripped = line.lstrip()
        if stripped.startswith("#") or "noqa: determinism" in line:
            continue
        # skip the docstring in this repo that *quotes* the old bad line
        if "abs(hash(tag))" in line and ("was:" in line or line.lstrip().startswith("seed=")):
            continue
        if BUILTIN_HASH.search(line):
            offenders.append(f"{path.name}:{n}: {stripped}")
    assert not offenders, (
        "builtin hash() is randomised per process (PYTHONHASHSEED) and must not decide "
        "anything persisted. Use hashlib.sha256. Offenders:\n  " + "\n  ".join(offenders))


@pytest.mark.parametrize("path", SCRIPTS, ids=lambda p: p.name)
def test_no_max_or_min_directly_over_a_set(path: Path):
    """`max(set(...))` / `min(set(...))` resolve ties by set-iteration order, which is
    hash-randomised for strings. This is exactly the C10 defect.

    A total ordering key (as in build_analysis_data.py, which keys on
    `(count, SEVERITY_ORDER.index(t))`) is fine because no tie survives it — but the safe
    pattern is not to hand `max` a set at all.
    """
    src = path.read_text(encoding="utf-8")
    offenders = []
    for n, line in enumerate(src.splitlines(), 1):
        if line.lstrip().startswith("#") or "noqa: determinism" in line:
            continue
        if re.search(r"\b(max|min)\s*\(\s*set\s*\(", line):
            offenders.append(f"{path.name}:{n}: {line.strip()}")
    assert not offenders, (
        "max()/min() over a set() ties-break on hash order. Sort, or use a total-order key. "
        "Offenders:\n  " + "\n  ".join(offenders))


def test_stable_seed_is_actually_stable():
    """The replacement for C11 must give the same seed in a fresh interpreter every time.

    Checked by SUBPROCESS with differing PYTHONHASHSEED, because importing the function into
    this process cannot detect per-process hash randomisation — the whole bug is that the
    value changes between interpreters, not within one.
    """
    code = (
        "import sys; sys.path.insert(0, r'%s');"
        "import hashlib;"
        "print(int(hashlib.sha256('Care | excl=yes | resid=method-specific'"
        ".encode('utf-8')).hexdigest()[:8], 16) %% 10000)" % (REPO / "scripts")
    )
    seen = set()
    for hs in ("0", "1", "42"):
        env = {**os.environ, "PYTHONHASHSEED": hs}
        r = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True,
                           env=env, timeout=120)
        assert r.returncode == 0, r.stderr[-500:]
        seen.add(r.stdout.strip())
    assert len(seen) == 1, f"seed differs across PYTHONHASHSEED: {seen}"


def test_builtin_hash_really_is_unstable():
    """Guard the guard.

    If a future Python made `hash()` stable, the tests above would still pass but for the
    wrong reason, and someone would eventually 'simplify' stable_seed() back to hash().
    This asserts the hazard is real on THIS interpreter, so the rationale stays visible.
    """
    code = "print(hash('Care | excl=yes | resid=method-specific'))"
    seen = set()
    for hs in ("1", "2", "3", "4", "5"):
        env = {**os.environ, "PYTHONHASHSEED": hs}
        r = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True,
                           env=env, timeout=120)
        seen.add(r.stdout.strip())
    assert len(seen) > 1, (
        "builtin hash() appears stable here, which is not what CPython guarantees. "
        "Do not take this as licence to use it for anything persisted.")


# =======================================================================================
# End-to-end — the real check: rebuild twice, compare bytes
# =======================================================================================


def _build(tmp_repo_out: Path, suffix: str, hashseed: str) -> Path:
    """Run the real builder in a subprocess with a given PYTHONHASHSEED."""
    env = {**os.environ, "PYTHONHASHSEED": hashseed}
    r = subprocess.run(
        [sys.executable, str(REPO / "scripts" / "build_analysis_data.py"), "--suffix", suffix],
        capture_output=True, text=True, cwd=REPO, env=env, timeout=900)
    assert r.returncode == 0, f"builder failed (seed {hashseed}):\n{r.stdout[-800:]}{r.stderr[-800:]}"
    produced = REPO / "results" / "derived" / f"analysis_long{suffix}.csv"
    assert produced.exists(), f"builder produced no {produced.name}"
    dest = tmp_repo_out / f"{produced.stem}_seed{hashseed}.csv"
    dest.write_bytes(produced.read_bytes())
    return dest


# Only "_v2" remains: the v1 collection was deleted 2026-08-10 (docs/V1_TO_V2.md). The parametrize
# is kept with one value rather than inlined, because the determinism guarantee is per
# COLLECTION and a future harness must be added here, not tested ad hoc.
@pytest.mark.parametrize("suffix", ["_v2"])
def test_analysis_dataset_rebuilds_identically(tmp_path, suffix):
    """THE test. Same raw inputs, two different hash seeds, byte-identical output.

    This is what failed before C10 was fixed: rebuilding flipped 28 `failure_type` values with
    no code change. Parametrised over both harnesses because they exercise different condition
    sets and different tie patterns.
    """
    raw = REPO / "results" / "raw"
    pattern = f"*{suffix}.csv" if suffix else "*.csv"
    have = [p for p in raw.glob(pattern) if suffix or not p.stem.endswith("_v2")]
    if not have:
        pytest.skip(f"no raw CSVs for suffix {suffix!r} on this machine")

    a = _build(tmp_path, suffix, "1")
    b = _build(tmp_path, suffix, "2")
    assert filecmp.cmp(a, b, shallow=False), (
        f"analysis_long{suffix}.csv differs between PYTHONHASHSEED=1 and =2. "
        "A committed dataset that does not regenerate from its inputs is not a dataset. "
        "See docs/CORRECTIONS.md C10.")
