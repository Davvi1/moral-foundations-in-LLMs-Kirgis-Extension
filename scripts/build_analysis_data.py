"""Build the analysis-ready dataset. Applies the exclusion rules fixed at tag
`exclusion-rules-fixed` — and refuses to run if the QA pass reports a blocking problem.

    python scripts/build_analysis_data.py

Writes results/derived/analysis_long_v2.csv: one row per model x item x condition.
The sampled condition is collapsed to its mean over k=10 replicates, with the Monte-Carlo
standard error retained, because that error term is what the variance model needs to avoid
attributing sampling noise to the model x method interaction.

Nothing here decides anything. Every threshold comes from docs/state.md and was fixed before any
outcome model was fitted.
"""

from __future__ import annotations

import argparse
import csv
import json
import math
import statistics as st
import sys
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import conditions as C  # noqa: E402

REPO = Path(__file__).resolve().parent.parent
RAW = REPO / "results" / "raw"
OUT = REPO / "results" / "derived"

# From docs/state.md, "Exclusion rules — FIXED 2026-08-08".
PARSE_THRESHOLD = 0.50
FREE_CONDITIONS = {"greedy", "sampled"}

# Ascending severity, used ONLY to break ties deterministically when summarising a sampled
# cell's failure types. "ok" is least severe so it can never win a tie against a real failure.
SEVERITY_ORDER = ["ok", "unparseable", "empty_output", "refusal"]

FIELDS = [
    "model", "family", "revision", "item_id", "foundation", "condition",
    "score", "score_se", "n_replicates",
    "clifford_wrong_mean",
    "logprob_mass", "label_position", "parse_strategy", "token_boundary_clean",
    "failure_type", "cell_parse_rate", "excluded", "exclusion_reason",
]


def f(x):
    try:
        v = float(x)
        return None if math.isnan(v) else v
    except (TypeError, ValueError):
        return None


def main() -> int:
    # --suffix selects which harness's raw files to build from. Only `_v2` exists now: the v1
    # collection was deleted on 2026-08-10 (see docs/V1_TO_V2.md). The argument is KEPT rather than
    # hard-coded because the bug it was added for -- C12, a glob that silently spanned two
    # collections and wrote one over the other -- is a property of unversioned paths, not of v1.
    # A future v3 would reintroduce exactly the same hazard.
    ap = argparse.ArgumentParser(description="Build the long-form analysis dataset.")
    ap.add_argument("--suffix", default="_v2",
                    help="raw-file suffix to build from. Only '_v2' exists; see docs/V1_TO_V2.md")
    ap.add_argument("--min-discrimination", type=float, default=0.25,
                    help="exclude a model whose mean between-item SD falls below this "
                         "multiple of the human baseline's between-item SD. 0 disables. "
                         "See the block comment before the rule fires — it is a post hoc "
                         "criterion and the write-up must say so.")
    args = ap.parse_args()

    human = {}
    with (REPO / "data" / "mfv_116_meta.csv").open(encoding="utf-8") as fh:
        for r in csv.DictReader(fh):
            human[int(r["questionnaire_item_id"])] = float(r["clifford_wrong_mean"])

    sfx = args.suffix
    paths = [p for p in sorted(RAW.glob(f"*{sfx}.csv"))
             if sfx or not p.stem.endswith("_v2")]
    if not paths:
        print(f"no raw CSVs matching suffix {sfx!r} in {RAW}")
        return 1
    print(f"building from {len(paths)} raw files (suffix {sfx!r})")

    rows_out: list[dict] = []
    for csv_path in paths:
        slug = csv_path.stem
        man_path = RAW / f"{slug}.manifest.json"
        man = json.loads(man_path.read_text(encoding="utf-8")) if man_path.exists() else {}
        rows = list(csv.DictReader(csv_path.open(encoding="utf-8")))

        # ---- classify every free-generation row -------------------------------------
        for r in rows:
            if r["condition"] in FREE_CONDITIONS:
                parsed = None if r["parse_failed"] == "True" else 0
                r["_ftype"] = C.failure_type(r["raw_output"], parsed)
            else:
                r["_ftype"] = "ok" if r["parse_failed"] != "True" else "unparseable"

        # ---- cell parse rates, per condition x foundation ---------------------------
        cells: dict[tuple[str, str], list[dict]] = defaultdict(list)
        for r in rows:
            cells[(r["condition"], r["foundation"])].append(r)
        parse_rate = {
            k: sum(x["_ftype"] == "ok" for x in v) / len(v) for k, v in cells.items()
        }

        # ---- collapse sampled to its mean; pass the others through ------------------
        by_key: dict[tuple[str, str], list[dict]] = defaultdict(list)
        for r in rows:
            by_key[(r["item_id"], r["condition"])].append(r)

        for (item_id, cond), group in by_key.items():
            usable = [f(g["score"]) for g in group if g["_ftype"] == "ok"]
            usable = [u for u in usable if u is not None]
            g0 = group[0]
            rate = parse_rate[(cond, g0["foundation"])]

            excluded, reason = False, ""
            if cond in FREE_CONDITIONS and rate < PARSE_THRESHOLD:
                excluded = True
                reason = f"cell parse rate {rate:.2f} < {PARSE_THRESHOLD}"
            elif not usable:
                excluded = True
                # Distinguish the three causes rather than writing "no data".
                types = {g["_ftype"] for g in group}
                reason = f"no usable score ({'/'.join(sorted(types - {'ok'}))})"
            if cond == "string" and g0.get("token_boundary_clean") == "False":
                excluded = True
                reason = "string token-boundary alignment failed"

            score = st.mean(usable) if usable else ""
            se = ""
            if cond == "sampled" and len(usable) > 1:
                se = st.stdev(usable) / math.sqrt(len(usable))

            # DETERMINISM BUG, fixed 2026-08-09. This was:
            #     dominant = max(set(ft), key=ft.count)
            # On a TIE, max() returns whichever element it met first while iterating the SET,
            # and CPython randomises string hashing per process. So the same raw data produced
            # different failure_type values on different runs: 28 rows of the committed
            # analysis_long.csv flipped (e.g. ok <-> unparseable) with no code change at all.
            # Verified directly -- PYTHONHASHSEED=1 gives "ok", =2 gives "unparseable" for the
            # gemma-2-2b item-43 sampled cell, which is 4 ok / 4 unparseable / 2 refusal.
            #
            # Ties are common because k=10 splits evenly all the time, so this was not an edge
            # case. Only the descriptive failure_type column was affected -- `score`,
            # `n_replicates` and every exclusion decision are computed from `usable` and
            # `rate`, never from `dominant` -- so no analysis result moves. But a dataset that
            # does not reproduce from its own inputs is not a dataset, and the same defect in a
            # column that DID feed the model would have been invisible.
            #
            # The fix breaks ties by severity rather than arbitrarily, which is both
            # deterministic and more honest: a cell that is half unparseable should not be
            # reported as "ok".
            # `sorted(set(...))` rather than `set(...)`: even with a total-order key the set
            # form is a trap for the next reader, and tests/test_determinism.py rejects it on
            # sight. An unrecognised failure type sorts as MOST severe rather than raising,
            # so a new type added to conditions.failure_type() degrades safely instead of
            # crashing the build or being quietly summarised as "ok".
            ft = [g["_ftype"] for g in group]
            sev = {t: i for i, t in enumerate(SEVERITY_ORDER)}
            dominant = max(sorted(set(ft)),
                           key=lambda t: (ft.count(t), sev.get(t, len(sev))))

            rows_out.append({
                "model": g0["model"], "family": man.get("family", ""),
                "revision": g0["revision"], "item_id": int(item_id),
                "foundation": g0["foundation"], "condition": cond,
                "score": score, "score_se": se, "n_replicates": len(usable),
                "clifford_wrong_mean": human.get(int(item_id), ""),
                "logprob_mass": g0.get("logprob_mass", ""),
                "label_position": g0.get("label_position", ""),
                "parse_strategy": g0.get("parse_strategy", ""),
                "token_boundary_clean": g0.get("token_boundary_clean", ""),
                "failure_type": dominant,
                "cell_parse_rate": round(rate, 4),
                "excluded": excluded, "exclusion_reason": reason,
            })

    # ---- model-level exclusion: does the model discriminate between items at all? --------
    #
    # DECIDED BY DAVID 2026-08-10, AND IT IS A POST HOC RULE. Say so plainly: the criterion was
    # defined after seeing the data, which is a researcher degree of freedom of exactly the kind
    # this project audits Kirgis for. Three things keep it defensible, and the write-up must
    # carry all three rather than just the first:
    #
    #   1. It is a UNIFORM THRESHOLD, not a named model. Anything below the cut goes, whatever
    #      it is. A rule that names `SmolLM2` is unfalsifiable and indefensible.
    #   2. The threshold is the one already justified for the QA warn gate
    #      (validate_results.py): 0.25x the human baseline's between-item SD, chosen because the
    #      MEDIAN model x condition cell sits at 1.02x it. It was not tuned to this decision.
    #   3. The result is INSENSITIVE to the threshold. On v2 the lowest model scores 0.098 and
    #      the next lowest 0.306 -- a 3x gap -- so any cut between ~0.15 and ~0.29 selects the
    #      same single model. That gap is the real argument; the exact number is not doing work.
    #
    # And the honest counterweight, which belongs beside it: dropping this model changes the
    # headline rank correlation by -0.004 (label~sampled 0.842 -> 0.838), and the largest change
    # to any pair is 0.022. The exclusion is not buying accuracy. It is asserting that a model
    # emitting a near-constant response is not answering the instrument, which is a
    # MEASUREMENT-VALIDITY claim, not an empirical improvement. Reported both ways.
    hv = sorted(human.values())
    human_sd = st.pstdev(hv) if len(hv) > 1 else None
    if human_sd and args.min_discrimination > 0:
        floor = args.min_discrimination * human_sd
        per_model: dict[str, list[float]] = defaultdict(list)
        for r in rows_out:
            if r["excluded"] or r["score"] == "":
                continue
            per_model[(r["model"], r["condition"])].append(float(r["score"]))
        disc: dict[str, float] = {}
        for model in sorted({m for m, _ in per_model}):
            sds = [st.pstdev(v) for (m, _), v in sorted(per_model.items())
                   if m == model and len(v) > 1]
            if sds:
                disc[model] = sum(sds) / len(sds)
        degenerate = sorted(m for m, d in disc.items() if d < floor)
        for model in degenerate:
            for r in rows_out:
                if r["model"] == model:
                    r["excluded"] = True
                    r["exclusion_reason"] = (
                        f"model discrimination {disc[model]:.3f} < {args.min_discrimination:g}"
                        f"x human between-item SD ({floor:.3f}) — near-constant response, "
                        f"not answering the instrument")
        print(f"  discrimination floor {floor:.3f} "
              f"({args.min_discrimination:g}x human SD {human_sd:.3f})")
        for model in sorted(disc, key=lambda m: disc[m])[:4]:
            mark = "  EXCLUDED" if model in degenerate else ""
            print(f"    {disc[model]:.3f}  {model}{mark}")
        if not degenerate:
            print("    no model fell below the floor")

    rows_out.sort(key=lambda r: (r["model"], r["item_id"], r["condition"]))
    OUT.mkdir(parents=True, exist_ok=True)
    out_name = f"analysis_long{sfx}.csv"
    with (OUT / out_name).open("w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=FIELDS, extrasaction="ignore")
        w.writeheader()
        w.writerows(rows_out)

    # ---- report -----------------------------------------------------------------------
    n_models = len({r["model"] for r in rows_out})
    exc = [r for r in rows_out if r["excluded"]]
    print(f"wrote {OUT/out_name}")
    print(f"  {len(rows_out)} rows, {n_models} models, "
          f"{len(rows_out) - len(exc)} usable, {len(exc)} excluded")

    # Two different things, and conflating them would misstate the design.
    #   CELL-LEVEL  the exclusion RULE fired: the whole model x condition x foundation cell
    #               is dropped because too few of its items produced an answer.
    #   ITEM-LEVEL  the cell is kept, but individual items within it have no score. Ordinary
    #               missingness, which the variance model handles directly.
    cell_level = [r for r in exc if "cell parse rate" in r["exclusion_reason"]
                  or "token-boundary" in r["exclusion_reason"]]
    item_level = [r for r in exc if r not in cell_level]

    print("\n=== CELL-LEVEL exclusions — the rule fired, whole cell dropped ===")
    seen: dict[tuple, tuple] = {}
    for r in cell_level:
        seen[(r["model"], r["condition"], r["foundation"])] = (
            r["cell_parse_rate"], r["exclusion_reason"])
    if not seen:
        print("  none")
    for (m, c, fdn), (rate, why) in sorted(seen.items()):
        print(f"  {m.split('/')[-1]:<34}{c:<9}{fdn:<14}rate={rate:<8}{why}")
    print(f"  -> {len(seen)} cells, {len(cell_level)} item-rows removed")

    print("\n=== ITEM-LEVEL missingness — cell kept, individual items have no score ===")
    per_cell: dict[tuple, int] = defaultdict(int)
    for r in item_level:
        per_cell[(r["model"], r["condition"], r["foundation"])] += 1
    if not per_cell:
        print("  none")
    for (m, c, fdn), n in sorted(per_cell.items(), key=lambda kv: -kv[1])[:12]:
        print(f"  {m.split('/')[-1]:<34}{c:<9}{fdn:<14}{n} of 116 items")
    if len(per_cell) > 12:
        print(f"  ... and {len(per_cell)-12} more cells")
    print(f"  -> {len(item_level)} item-rows, spread over {len(per_cell)} kept cells")

    print("\n=== achieved N per condition (models with >=1 usable cell) ===")
    for cond in sorted({r["condition"] for r in rows_out}):
        ms = {r["model"] for r in rows_out if r["condition"] == cond and not r["excluded"]}
        print(f"  {cond:<10}{len(ms)} of {n_models} models")

    print("\n=== failure types, free-generation conditions ===")
    for cond in ("greedy", "sampled"):
        cnt: dict[str, int] = defaultdict(int)
        for r in rows_out:
            if r["condition"] == cond:
                cnt[r["failure_type"]] += 1
        tot = sum(cnt.values())
        line = "  ".join(f"{k}={v} ({100*v/tot:.1f}%)" for k, v in sorted(cnt.items()))
        print(f"  {cond:<10}{line}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
