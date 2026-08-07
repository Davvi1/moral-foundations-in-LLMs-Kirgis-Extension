"""Derive the working item files from Kirgis's committed vignette CSV.

Reads  : data/source/kirgis_vignettes_short.csv   (raw, never edited -- see PROVENANCE.md)
Writes : data/mfv_116.csv        QSTN questionnaire format
         data/mfv_116_meta.csv   foundation labels + Clifford's human means

Stdlib only, so it runs on the 3.10 laptop and on the 3.12 pod without a virtualenv.
Self-verifying: the invariants at the bottom are the ones in the plan's verification table,
so a silent change to the source file fails the build instead of quietly propagating.

Run from the repo root:  python scripts/build_items.py
"""

from __future__ import annotations

import csv
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
SRC = REPO / "data" / "source" / "kirgis_vignettes_short.csv"
OUT_ITEMS = REPO / "data" / "mfv_116.csv"
OUT_META = REPO / "data" / "mfv_116_meta.csv"

# Expected foundation counts. From Clifford's set after Kirgis drops the 16 physical-harm
# Care items; verified against the source file during the go/no-go check on 2026-08-07.
EXPECTED_FOUNDATIONS = {
    "Authority": 17,
    "Care": 16,
    "Fairness": 17,
    "Liberty": 17,
    "Loyalty": 16,
    "Sanctity": 17,
    "Social Norms": 16,
}
EXPECTED_N = 116

# Provenance string stamped onto every meta row. Deliberately verbose: this is a
# transcription of a published table, not a reconstruction, and the write-up has to be
# able to say so precisely.
SOURCE_TAG = "Clifford et al. 2015 BRM 47(4) Table 1 pp.1183-1186, via Kirgis repo fc39db0"


def parse_pct(raw: str) -> float:
    """'83 %' -> 83.0. Clifford's table stores percentages as strings with a space."""
    return float(raw.replace("%", "").strip())


def main() -> int:
    if not SRC.exists():
        sys.exit(f"missing source file: {SRC}\nSee data/source/PROVENANCE.md")

    with SRC.open(newline="", encoding="utf-8") as fh:
        rows = list(csv.DictReader(fh))

    items: list[dict[str, object]] = []
    meta: list[dict[str, object]] = []

    # IDs are 1..N in source-file order. Order carries no meaning and does not need
    # randomising: every item is administered as its own independent prompt, so
    # question-order effects are structurally impossible -- the same property Kirgis got
    # from one API call per question. Shuffling would only break reproducibility.
    for i, row in enumerate(rows, start=1):
        scenario = row["Scenario"].strip()
        items.append({"questionnaire_item_id": i, "question_content": scenario})
        meta.append(
            {
                "questionnaire_item_id": i,
                "foundation": row["Foundation"].strip(),
                "clifford_wrong_mean": float(row["Wrong"]),
                "clifford_not_wrong_pct": parse_pct(row["Not Wrong"]),
                "source": SOURCE_TAG,
            }
        )

    # ---- invariants ----------------------------------------------------------------
    # These are assertions, not logging. If the source file ever changes shape we want a
    # loud failure here rather than a subtly wrong questionnaire reaching a GPU.
    problems: list[str] = []

    if len(items) != EXPECTED_N:
        problems.append(f"expected {EXPECTED_N} items, got {len(items)}")

    counts: dict[str, int] = {}
    for m in meta:
        counts[str(m["foundation"])] = counts.get(str(m["foundation"]), 0) + 1
    if counts != EXPECTED_FOUNDATIONS:
        problems.append(f"foundation counts differ\n  expected {EXPECTED_FOUNDATIONS}\n  got      {counts}")

    texts = [str(it["question_content"]) for it in items]
    if len(set(texts)) != len(texts):
        problems.append("duplicate scenario text present")
    if any(not t for t in texts):
        problems.append("empty scenario text present")

    means = [float(m["clifford_wrong_mean"]) for m in meta]
    if not all(0.0 <= v <= 4.0 for v in means):
        problems.append(f"human means outside 0-4: min={min(means)} max={max(means)}")

    if problems:
        sys.exit("BUILD FAILED\n  - " + "\n  - ".join(problems))

    # ---- write ---------------------------------------------------------------------
    # newline="" per the csv docs; utf-8 explicitly so the pod and the laptop agree.
    with OUT_ITEMS.open("w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=["questionnaire_item_id", "question_content"])
        w.writeheader()
        w.writerows(items)

    with OUT_META.open("w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(
            fh,
            fieldnames=[
                "questionnaire_item_id",
                "foundation",
                "clifford_wrong_mean",
                "clifford_not_wrong_pct",
                "source",
            ],
        )
        w.writeheader()
        w.writerows(meta)

    print(f"wrote {OUT_ITEMS.relative_to(REPO)}  ({len(items)} items)")
    print(f"wrote {OUT_META.relative_to(REPO)}   ({len(meta)} rows)")
    print("\nfoundation counts:")
    for k in sorted(counts):
        print(f"  {k:<14} {counts[k]}")
    print(f"\nclifford_wrong_mean: min={min(means):.1f} max={max(means):.1f} "
          f"mean={sum(means) / len(means):.3f}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
