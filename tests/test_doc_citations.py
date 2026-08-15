"""Every document this repo cites must actually exist at the path given.

WHY THIS EXISTS. The code is dense with citations — `docs/LIMITATIONS.md` §12, `docs/state.md`
"Exclusion rules — FIXED 2026-08-08", `config/prompt.yaml:33`. They are load-bearing: a reader
told that a threshold is pinned somewhere needs to be able to go and read it, and a reviewer
asking "where did this decision get made" is handed one of these paths.

Nothing guarded them. Three of this project's worst defects were path or reference drift:

  C12  an unversioned output path silently spanned two collections, and a 31-model run wrote
       over the committed 20-model artifact
  C13  the QA gate globbed both collections at once and had never once passed on v2
  C15  a design commitment lived in prose in three files and in code in none

Moving ten documents into `docs/` on 2026-08-11 touched 68 citations across scripts, tests and
the README. That is exactly the operation that produces a stale signpost, and a stale signpost
is how a commitment stops being findable — which is the mechanism behind C15.

This test is cheap and mechanical: extract every `*.md` / `*.yaml` path mentioned in the repo's
own source and prose, and assert the file is there.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parent.parent

# Paths that appear in text but are not repo files.
IGNORE_EXACT = {
    # deleted in the v1 cleanup and referenced only historically, by design
    "analysis_long.csv", "variance_ratio.csv", "controls.md",
    "kirgis_pattern_audit.md", "refusal_leakage_audit.md",
    "RESUME.md", "pod_overnight.sh", "pod_analysis_batch.sh",
    "compare_v1_v2.py", "merge_labelfix.py", "add_phase2_models.py",
    "add_phase3_models.py", "diagnose_string_scoring.py",
    # third-party / external
    "README.md",
}

# Paths inside SOMEONE ELSE'S repository — Kirgis's, which we read but do not vendor. They must
# never resolve here, and flagging them would train the reader to ignore this test.
EXTERNAL_PREFIXES = ("data/results/", "data/survey/", "llm_moral_foundations2/", "surveys/")
EXTERNAL_EXACT = {"logprob_responses.csv", "vignettes.csv", "vignettes_short.csv",
                  "steering.py", "mft_base.py"}

CITATION = re.compile(r"`([A-Za-z0-9_./-]+\.(?:md|yaml|yml|py|csv))`")

# Paths given with a DIRECTORY, in prose or in a runnable command block. These get a stricter
# check than CITATION: the stated directory must be right, not just the filename.
#
# WHY THE STRICTER CHECK EXISTS. Until 2026-08-15 this file checked only `.md|.yaml|.yml`, and
# `_resolve()` fell back to matching the BARE FILENAME under any of six roots. Both holes
# pointed the same way, and the README fell through them: it told the reader to run the two v2
# scorer suites from the scripts directory, when both live under tests. The commands had been
# wrong in the repo's most-read file, inside a document this test was already scanning, and the
# extractor could not see it. Turning the check on found the same error in three more places:
# V1_TO_V2.md, and each of the two suites documenting its own invocation.
#
# (Written without literal example paths on purpose — this file is scanned by its own test, and
# a wrong path quoted here as an illustration would fail it. That is the check working.)
COMMAND_PATH = re.compile(r"(?:^|[\s`(])((?:scripts|tests|config|data|results|docs)/"
                          r"[A-Za-z0-9_./-]+\.(?:py|md|yaml|yml|csv|sh))")


def _sources():
    for sub in ("scripts", "tests"):
        yield from sorted((REPO / sub).glob("*.py"))
    yield from sorted((REPO / "docs").glob("*.md"))
    for name in ("README.md", "CLAUDE.md"):
        p = REPO / name
        if p.exists():
            yield p


def _resolve(cited: str, src: Path) -> bool:
    """A citation resolves if the path exists from the repo root, from docs/, or beside the
    citing file. Documents in docs/ refer to each other by bare filename and that is correct."""
    name = Path(cited).name
    if name in IGNORE_EXACT or name in EXTERNAL_EXACT:
        return True
    if cited.startswith(EXTERNAL_PREFIXES):
        return True
    roots = (REPO, REPO / "docs", src.parent, REPO / "results" / "derived",
             REPO / "data" / "source", REPO / "config",
             # added 2026-08-15 with the .py/.csv extension: docs and tests refer to harness
             # scripts by bare name, which is correct and must resolve.
             REPO / "scripts", REPO / "tests")
    return any((root / cited).exists() or (root / name).exists() for root in roots)


def test_every_path_with_a_directory_resolves_at_that_directory():
    """A path written with a directory must exist AT that directory, not merely somewhere.

    The bare-filename fallback in `_resolve()` is right for docs/ cross-references, which name
    each other without a directory by convention. It is wrong the moment a path states its
    directory: then the directory is part of the claim, and a reader who types the command
    finds nothing. See the COMMAND_PATH comment for the instance that motivated this.
    """
    broken: list[str] = []
    checked = 0
    for src in _sources():
        text = src.read_text(encoding="utf-8", errors="replace")
        for cited in sorted(set(COMMAND_PATH.findall(text))):
            if (Path(cited).name in IGNORE_EXACT or Path(cited).name in EXTERNAL_EXACT
                    or cited.startswith(EXTERNAL_PREFIXES)):
                continue
            checked += 1
            if not (REPO / cited).exists():
                elsewhere = [str(p.relative_to(REPO)) for p in REPO.rglob(Path(cited).name)
                             if ".git" not in p.parts and "__pycache__" not in p.parts]
                hint = f" — but it exists at {elsewhere[0]}" if elsewhere else ""
                broken.append(f"{src.relative_to(REPO)} says `{cited}`{hint}")
    assert checked > 20, f"only {checked} directory-qualified paths found; extractor broken?"
    assert not broken, (
        f"{len(broken)} path(s) name a directory they are not in:\n  " + "\n  ".join(broken))


def test_every_cited_document_exists():
    broken: list[str] = []
    checked = 0
    for src in _sources():
        text = src.read_text(encoding="utf-8", errors="replace")
        for cited in set(CITATION.findall(text)):
            checked += 1
            if not _resolve(cited, src):
                broken.append(f"{src.relative_to(REPO)} cites `{cited}` — not found")
    assert checked > 50, f"only {checked} citations found; the extractor is probably broken"
    assert not broken, (
        f"{len(broken)} citation(s) point at a file that does not exist:\n  "
        + "\n  ".join(sorted(broken)))


ARXIV = re.compile(r"arXiv:(\d{4}\.\d{4,5})", re.I)

# A BAN is "do not cite … until <something is verified>". Deliberately narrow. `references.md`
# also contains "Do not cite from the abstract" (a caveat about WHICH PART to cite) and "Do not
# cite the journal entry as evidence" (a caveat about weight). Neither forbids the source, and
# a guard that treated them as bans would fire wrongly and get trained away.
BAN_PHRASE = re.compile(r"do not cite[^.]*\buntil\b", re.I)


def _banned_arxiv_ids(text: str) -> set[str]:
    """arXiv ids whose references.md entry forbids citing them pending verification.

    An entry starts at a line beginning with `**` and runs to the next such line. Its arXiv ids
    are taken from the HEADING SPAN — the first few lines — because headings in this file wrap:

        **Tsvilodub, Wang, Grosch & Franke — "Predictions from language models for multiple-
        choice tasks are not robust under variation of scoring methods." arXiv:2403.00998,
        submitted 1 Mar 2024.** Abstract fetched and verified 2026-08-10.

    A first version required the id on the *opening* line and so matched almost nothing in this
    file while appearing to work — the same shape as C13, and caught only because the guard was
    deliberately tested against a source the repo cites.
    """
    HEADING_SPAN = 4
    banned: set[str] = set()
    entries: list[list[str]] = []
    for ln in text.splitlines():
        if ln.startswith("**") or not entries:
            entries.append([ln])
        else:
            entries[-1].append(ln)
    for entry in entries:
        ids = {m.lower() for m in ARXIV.findall(" ".join(entry[:HEADING_SPAN]))}
        if ids and any(BAN_PHRASE.search(ln) for ln in entry):
            banned.update(ids)
    return banned


def test_the_do_not_cite_extractor_actually_detects_a_ban():
    """C13's lesson, applied to C20's guard: a check that cannot fail is not a check.

    Every ban in `references.md` may legitimately be lifted — as ValueBench's was on 2026-08-15
    by verifying the author list — at which point the guard below inspects nothing and passes
    for free. That is precisely the shape of C13, where the token-boundary check filtered on a
    condition matching zero rows and printed its pass line having examined none.

    So the extractor is exercised against a fixture with a known ban. If this fails, the guard
    below is decorative regardless of what references.md happens to contain today.
    """
    fixture = (
        "**Someone — \"A Paper.\" arXiv:1234.56789, submitted 1 Jan 2026.**\n"
        "Body text. **Author list NOT yet verified — do not cite until it is.**\n"
        "\n"
        "**Other — \"Another.\" arXiv:9876.54321.**\n"
        "Body text. Do not cite from the abstract; the numbers are in the body.\n"
        "\n"
        "**Third, With A Long Name — \"A Title That Wraps Across\n"
        "Several Lines Of The Heading.\" arXiv:5555.55555, submitted 2 Feb 2026.**\n"
        "Body text. Do not cite until the full text is read.\n"
    )
    got = _banned_arxiv_ids(fixture)
    assert "1234.56789" in got, "a 'do not cite until' ban was not detected"
    assert "9876.54321" not in got, (
        "'do not cite from the abstract' is a caveat about which part to cite, not a ban on "
        "the source; treating it as one would make this guard fire wrongly")
    assert "5555.55555" in got, (
        "a ban on an entry whose heading WRAPS was missed. Headings in references.md routinely "
        "wrap, so an extractor that only reads the opening line matches almost nothing while "
        "appearing to work — the C13 shape, and the first version of this had exactly that bug")


def test_no_source_under_a_do_not_cite_ban_is_cited_elsewhere():
    """C20. `references.md` can forbid citing a source until its full text is read. Nothing
    enforced that, and the ban was violated in seven places — including the registered basis of
    prediction P6 and two strings inside `analyse_scale.py`.

    The mechanism is the project's worst recurring one: a rule written in one file and obeyed
    nowhere, which is C15's shape. `references.md` exists to enforce CLAUDE.md's hardest
    standing rule (never cite from memory). It was correct, current and explicit; it simply had
    no reader.

    Contract: `references.md` is a list of entries, each opening with a bolded heading naming
    its source. If an entry's body contains 'do not cite', the arXiv id in THAT ENTRY'S HEADING
    is banned everywhere else. Lifting a ban means editing references.md deliberately — which
    is the point.

    The heading rule matters and was learned immediately: a first version banned any id within
    three lines of the phrase, which swept up a neighbouring paper mentioned in passing inside
    the ValueBench entry. A guard that fires on things it should not gets trained away.
    """
    refs = REPO / "docs" / "references.md"
    if not refs.exists():
        pytest.skip("docs/references.md missing")
    banned = _banned_arxiv_ids(refs.read_text(encoding="utf-8"))

    violations: list[str] = []
    for src in _sources():
        if src.name == "references.md":
            continue
        text = src.read_text(encoding="utf-8", errors="replace")
        for ident in sorted(banned):
            if re.search(rf"arXiv:{re.escape(ident)}", text, re.I):
                violations.append(f"{src.relative_to(REPO)} cites arXiv:{ident}")
    assert not violations, (
        "docs/references.md bans citing these sources until their full text is read, and they "
        "are cited anyway (C20):\n  " + "\n  ".join(violations)
        + "\n\nEither read the source and lift the ban in references.md, or remove the citation.")


def test_the_ten_moved_documents_are_where_the_repo_says_they_are():
    """Pins the 2026-08-11 layout. Root keeps only README, CLAUDE and LICENSE."""
    for name in ["ANALYSIS_PLAN", "CORRECTIONS", "FINDINGS", "LIMITATIONS",
                 "METHODOLOGY_REVIEW", "METHODS_EXPLAINER", "references", "state",
                 "THE_NEXT_EXPERIMENT", "V1_TO_V2"]:
        assert (REPO / "docs" / f"{name}.md").exists(), f"docs/{name}.md missing"
        assert not (REPO / f"{name}.md").exists(), (
            f"{name}.md is back at the repo root — the docs live in docs/ since 2026-08-11, and "
            f"two copies is how one of them goes stale")


def test_claude_md_stays_at_the_root():
    """Claude Code reads CLAUDE.md from the project root. In docs/ it is inert."""
    assert (REPO / "CLAUDE.md").exists(), "CLAUDE.md must stay at the repo root to be loaded"
