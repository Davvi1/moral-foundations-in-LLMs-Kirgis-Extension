"""Every script must parse and import cleanly on the analysis machine.

This exists because `probe_tokenization.py` shipped with an f-string containing backslashes —
a syntax error before Python 3.12. It ran fine on the 3.12 pod and was undiscoverable
locally until a sweep like this one. The repo targets two Pythons (3.12 on the pod, 3.10 on
the laptop) and a script that only parses on one of them is broken.
"""

from __future__ import annotations

import ast
import re
import subprocess
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parent.parent
SCRIPTS = sorted((REPO / "scripts").glob("*.py"))
TESTS = sorted((REPO / "tests").glob("*.py"))


@pytest.mark.parametrize("path", SCRIPTS + TESTS, ids=lambda p: p.name)
def test_parses(path: Path):
    """Syntax must be valid on the running interpreter."""
    ast.parse(path.read_text(encoding="utf-8"), filename=str(path))


FSTRING_BACKSLASH = re.compile(r"""f(['"])(?:(?!\1).)*?\{[^{}]*\\""")


@pytest.mark.parametrize("path", SCRIPTS, ids=lambda p: p.name)
def test_no_backslash_inside_fstring_expression(path: Path):
    """Guard for the construct that bit us. Only backslashes INSIDE the braces are illegal
    before 3.12 — an ordinary `\\n` elsewhere in the literal is fine, so the check has to be
    targeted rather than "line contains f-quote and backslash".

    Redundant with test_parses while the suite runs on 3.10, but not if it is ever run only
    on 3.12 — which is precisely how the original bug survived.
    """
    for n, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if line.lstrip().startswith("#"):
            continue
        if FSTRING_BACKSLASH.search(line):
            pytest.fail(f"{path.name}:{n} backslash inside an f-string expression — "
                        f"invalid before Python 3.12:\n    {line.strip()}")


# preflight.py has no argparse: it runs its checks immediately and exits non-zero when the
# environment is incomplete, which is correct behaviour and exactly what it is for.
CLI_SCRIPTS = [p for p in SCRIPTS if p.name not in {"preflight.py"}]


@pytest.mark.parametrize("path", [p for p in CLI_SCRIPTS if p.name != "run_experiment.py"],
                         ids=lambda p: p.name)
def test_shows_help_without_a_gpu(path: Path):
    """--help must work on a machine with no vLLM and no GPU. A script that cannot even
    print its usage will fail confusingly on the pod.

    run_experiment.py is covered separately below; preflight.py is excluded above.
    """
    r = subprocess.run([sys.executable, str(path), "--help"],
                       capture_output=True, text=True, timeout=120, cwd=REPO)
    assert r.returncode == 0, f"{path.name} --help failed:\n{r.stderr[-1500:]}"


def test_preflight_runs_and_reports_rather_than_crashing():
    """On a machine without vLLM/GPU it must exit non-zero with a readable summary, not a
    traceback. That is the difference between a useful pre-flight and a confusing one."""
    r = subprocess.run([sys.executable, str(REPO / "scripts" / "preflight.py")],
                       capture_output=True, text=True, timeout=300, cwd=REPO)
    assert "PRE-FLIGHT" in r.stdout
    assert "Traceback" not in r.stderr, r.stderr[-1500:]
    assert ("READY" in r.stdout) or ("BLOCKED" in r.stdout)


def test_run_experiment_help_works():
    r = subprocess.run([sys.executable, str(REPO / "scripts" / "run_experiment.py"), "--help"],
                       capture_output=True, text=True, timeout=120, cwd=REPO)
    assert r.returncode == 0, r.stderr[-1500:]
    for flag in ("--models", "--all", "--limit-items", "--purge-weights", "--no-eager"):
        assert flag in r.stdout, f"{flag} missing from usage"
