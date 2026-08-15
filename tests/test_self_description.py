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
