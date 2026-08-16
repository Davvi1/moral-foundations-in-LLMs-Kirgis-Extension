"""The repository's claims ABOUT ITSELF must match the repository.

WHY THIS EXISTS. Every other guard in this project points at a number derived from
`analysis_long_v2.csv`: `test_headline_numbers.py` recomputes every ρ quoted in prose,
`test_design_commitments.py` enforces the arm basket, `test_determinism.py` rebuilds the
dataset twice. All of them are aimed at what the DATA says.

Nothing was aimed at what the PROJECT says about itself, and that is where the last three
defects came from:

  C19  `LIMITATIONS.md` spent five days describing completed work as outstanding —
       five of its seven "still outstanding" items had been done, one of them
       contradicted by a box in the same file
  C20  a "do not cite until verified" instruction was violated in seven places
  C21  `README.md` advertised 19 corrections in its header while linking to a file
       listing 20, and claimed 304 tests when the suite collected 306

C21's own fix then went stale within the hour: adding `make_figures.py` and
`make_deck.py` took the suite from 306 to 316, because `test_scripts_are_valid.py`
parametrises over `scripts/*.py`. A hand-maintained count of a thing that changes
whenever a file is added is stale by construction. That is the argument for a check
rather than a fourth manual correction.

Both assertions below are DERIVED, never hardcoded:
  - the corrections count is the number of `## C<n>` entries in `CORRECTIONS.md`
  - the test count is `len(session.items)`, i.e. what pytest actually collected on
    this run — so this test counts itself, which is correct
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parent.parent

# Files that state a count about the repository, and must agree with it.
CLAIM_FILES = ["README.md", "docs/state.md", "docs/LIMITATIONS.md"]

WORDS = {
    12: "twelve", 19: "nineteen", 20: "twenty", 21: "twenty-one",
    22: "twenty-two", 23: "twenty-three", 24: "twenty-four",
}

# A superseded count is legitimate when the sentence is explicitly retrospective —
# `state.md:55` reads *This block said "12 corrections"*, which is a record of a fixed
# defect (C19) and must not be "corrected" into a lie about what the block once said.
# Looked for in the 90 characters preceding the claim.
RETROSPECTIVE = re.compile(r"said|counted|replaces|was |previously|-era|had been", re.I)


def _text(rel: str) -> str:
    return (REPO / rel).read_text(encoding="utf-8")


def corrections_in_log() -> int:
    """Entries in CORRECTIONS.md, counted from its own headings."""
    body = _text("docs/CORRECTIONS.md")
    ids = re.findall(r"^## C(\d+)\b", body, flags=re.M)
    assert ids, "no '## C<n>' headings found — has the format changed?"
    nums = sorted(int(i) for i in ids)
    assert nums == list(range(1, len(nums) + 1)), f"C-numbers are not contiguous: {nums}"
    return len(nums)


# --------------------------------------------------------------------------- corrections
def test_corrections_count_is_consistent_everywhere():
    """Any 'N corrections' claim must equal the number of entries in the log.

    This is C21 exactly: the count was right in the file that holds the evidence and
    wrong in the file a reader reaches first.
    """
    n = corrections_in_log()
    word = WORDS.get(n)
    pattern = re.compile(
        r"(?:\*\*)?(\d+|" + "|".join(WORDS.values()) + r")(?:\*\*)?[  ]"
        r"(?:logged[  ])?corrections?\b", re.I)

    wrong: list[str] = []
    for rel in CLAIM_FILES:
        for m in pattern.finditer(_text(rel)):
            claimed = m.group(1).lower()
            ok = claimed == str(n) or (word and claimed == word)
            if not ok and not RETROSPECTIVE.search(
                    _text(rel)[max(0, m.start() - 90):m.start()]):
                wrong.append(f"{rel}: {m.group(0)!r} but CORRECTIONS.md has {n}")
    assert not wrong, (
        f"CORRECTIONS.md contains {n} entries; these disagree:\n  " + "\n  ".join(wrong))


def test_corrections_tally_table_covers_every_entry():
    """The 'how it was found' tally must account for every logged correction.

    C21 added a row; a tally that silently stops covering the log is the same class of
    defect as the count being wrong.
    """
    body = _text("docs/CORRECTIONS.md")
    tally = body[body.rindex("## Updated tally"):]
    cited = {int(x) for x in re.findall(r"\bC(\d+)\b", tally)}
    expected = set(range(1, corrections_in_log() + 1))
    missing = sorted(expected - cited)
    assert not missing, f"tally omits C{', C'.join(map(str, missing))}"


# --------------------------------------------------------------------------- deps
# Third-party import name -> the distribution that provides it.
DIST = {
    "pandas": "pandas", "numpy": "numpy", "scipy": "scipy",
    "matplotlib": "matplotlib", "yaml": "PyYAML", "pytest": "pytest",
    "transformers": "transformers", "truststore": "truststore",
    "pptx": "python-pptx", "docx": "python-docx", "PIL": "pillow",
    # requirements-fit.txt — the Bayesian stack, not installed on a laptop
    "bambi": "bambi", "pymc": "pymc", "arviz": "arviz",
    # requirements-inference.txt — Linux + GPU only
    "vllm": "vllm", "torch": "torch", "qstn": "qstn",
}
REQ_FILES = ["requirements.txt", "requirements-fit.txt", "requirements-inference.txt"]


def _declared() -> set[str]:
    out = set()
    for rel in REQ_FILES:
        for line in _text(rel).splitlines():
            line = line.split("#")[0].strip()
            if line:
                out.add(re.split(r"[<>=\[!~]", line, 1)[0].strip().lower())
    return out


def test_every_third_party_import_is_declared():
    """A requirements file is a claim; this checks it against what the code imports.

    Without this, "pip install -r requirements.txt" is prose — the same category of
    unenforced commitment as C15. Standard-library modules are excluded by asking the
    interpreter rather than by keeping a hand-written list that would itself go stale.
    """
    import sys
    stdlib = set(sys.stdlib_module_names)
    declared = _declared()

    found: dict[str, set[str]] = {}
    for py in sorted((REPO / "scripts").rglob("*.py")) + \
            sorted((REPO / "tests").rglob("*.py")):
        tree = __import__("ast").parse(py.read_text(encoding="utf-8"), str(py))
        for node in __import__("ast").walk(tree):
            if isinstance(node, __import__("ast").Import):
                names = [a.name.split(".")[0] for a in node.names]
            elif isinstance(node, __import__("ast").ImportFrom):
                names = [node.module.split(".")[0]] if node.module and not node.level else []
            else:
                continue
            for nm in names:
                if nm in stdlib or nm == "__future__":
                    continue
                # first-party: a sibling module in scripts/ or tests/
                if (REPO / "scripts" / f"{nm}.py").exists() or \
                        (REPO / "tests" / f"{nm}.py").exists():
                    continue
                found.setdefault(nm, set()).add(py.relative_to(REPO).as_posix())

    missing = {}
    for nm, where in found.items():
        dist = DIST.get(nm, nm).lower()
        if dist not in declared:
            missing[nm] = sorted(where)
    assert not missing, (
        "imported but not in any requirements file:\n  " + "\n  ".join(
            f"{k} (from {', '.join(v)})" for k, v in sorted(missing.items())))


def test_requirements_pins_match_the_installed_analysis_stack():
    """requirements.txt claims the versions the committed artifacts were built with.

    Only checks what is actually importable here, so it is meaningful on a laptop and
    on CI without demanding the GPU or Bayesian stacks be present.
    """
    import importlib.metadata as md
    wrong = []
    for line in _text("requirements.txt").splitlines():
        line = line.split("#")[0].strip()
        if "==" not in line:
            continue
        name, pin = (s.strip() for s in line.split("=="))
        try:
            have = md.version(name)
        except md.PackageNotFoundError:
            continue
        if have != pin:
            wrong.append(f"{name}: pinned {pin}, installed {have}")
    assert not wrong, (
        "requirements.txt disagrees with this environment:\n  " + "\n  ".join(wrong))


# --------------------------------------------------------------------------- tests
def test_stated_test_count_matches_collection(request):
    """'N tests' in prose must equal what pytest actually collected.

    Skipped when the run is filtered (a single file, or -k), because session.items is
    then a subset and the comparison is meaningless.
    """
    cfg = request.config
    if cfg.getoption("keyword") or cfg.getoption("markexpr"):
        pytest.skip("filtered run (-k/-m): collection is a subset")
    args = [a for a in cfg.invocation_params.args if not a.startswith("-")]
    if args:
        pytest.skip("filtered run (explicit paths): collection is a subset")

    collected = len(request.session.items)
    pattern = re.compile(r"(?:\*\*)?(\d{2,4})(?:\*\*)?[  ]tests\b")
    wrong = []
    for rel in CLAIM_FILES:
        for m in pattern.finditer(_text(rel)):
            before = _text(rel)[max(0, m.start() - 90):m.start()]
            if int(m.group(1)) != collected and not RETROSPECTIVE.search(before):
                wrong.append(f"{rel}: claims {m.group(1)}, collected {collected}")
    assert not wrong, (
        "the suite collected %d tests; these disagree:\n  %s\n"
        "Adding a script changes this count — test_scripts_are_valid.py parametrises "
        "over scripts/*.py." % (collected, "\n  ".join(wrong)))
