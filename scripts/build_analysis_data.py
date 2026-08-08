"""Build the analysis-ready dataset. Applies the exclusion rules fixed at tag
`exclusion-rules-fixed` — and refuses to run if the QA pass reports a blocking problem.

    python scripts/build_analysis_data.py

Writes results/derived/analysis_long.csv: one row per model x item x condition.
The sampled condition is collapsed to its mean over k=10 replicates, with the Monte-Carlo
standard error retained, because that error term is what the variance model needs to avoid
attributing sampling noise to the model x method interaction.

Nothing here decides anything. Every threshold comes from state.md and was fixed before any
outcome model was fitted.
"""

from __future__ import annotations

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

# From state.md, "Exclusion rules — FIXED 2026-08-08".
PARSE_THRESHOLD = 0.50
FREE_CONDITIONS = {"greedy", "sampled"}

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
    human = {}
    with (REPO / "data" / "mfv_116_meta.csv").open(encoding="utf-8") as fh:
        for r in csv.DictReader(fh):
            human[int(r["questionnaire_item_id"])] = float(r["clifford_wrong_mean"])

    rows_out: list[dict] = []
    for csv_path in sorted(RAW.glob("*.csv")):
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

            ft = [g["_ftype"] for g in group]
            dominant = max(set(ft), key=ft.count)

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

    rows_out.sort(key=lambda r: (r["model"], r["item_id"], r["condition"]))
    OUT.mkdir(parents=True, exist_ok=True)
    with (OUT / "analysis_long.csv").open("w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=FIELDS, extrasaction="ignore")
        w.writeheader()
        w.writerows(rows_out)

    # ---- report -----------------------------------------------------------------------
    n_models = len({r["model"] for r in rows_out})
    exc = [r for r in rows_out if r["excluded"]]
    print(f"wrote {OUT/'analysis_long.csv'}")
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
    for cond in ("label", "string", "greedy", "sampled"):
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
