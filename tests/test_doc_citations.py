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

CITATION = re.compile(r"`([A-Za-z0-9_./-]+\.(?:md|yaml|yml))`")


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
    if name in IGNORE_EXACT:
        return True
    roots = (REPO, REPO / "docs", src.parent, REPO / "results" / "derived",
             REPO / "data" / "source", REPO / "config")
    return any((root / cited).exists() or (root / name).exists() for root in roots)


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
