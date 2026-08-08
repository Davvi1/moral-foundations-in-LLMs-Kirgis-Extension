"""Methodological QA over the collected results. Run before ANY analysis.

Capturing diagnostics is not the same as checking them. This script reads every
results/raw/*.csv and its manifest and asserts the things that must hold for the study to
mean what it claims. Anything that fails here invalidates some part of the analysis, so it
runs first and its output goes in the write-up.

    python scripts/validate_results.py            # all models found
    python scripts/validate_results.py --raw DIR  # explicit directory

Exit 0 = data is analysable. Non-zero = at least one blocking problem.
"""

from __future__ import annotations

import argparse
import csv
import json
import math
import sys
from collections import Counter, defaultdict
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
CONDITIONS = ["label", "string", "greedy", "sampled"]

# Thresholds fixed in the analysis plan (state.md).
REFUSAL_FLAG = 0.10          # model x foundation cell flagged above this
LOW_MASS_FLAG = 0.50         # label-scoring probability mass below this is suspect

blocking: list[str] = []
warnings: list[str] = []


def fail(msg: str) -> None:
    blocking.append(msg)
    print(f"  [FAIL] {msg}")


def warn(msg: str) -> None:
    warnings.append(msg)
    print(f"  [warn] {msg}")


def ok(msg: str) -> None:
    print(f"  [ ok ] {msg}")


def load(raw: Path):
    models = {}
    for csv_path in sorted(raw.glob("*.csv")):
        man_path = csv_path.with_suffix("").with_suffix(".manifest.json")
        if not man_path.exists():
            man_path = raw / (csv_path.stem + ".manifest.json")
        rows = list(csv.DictReader(csv_path.open(encoding="utf-8")))
        man = json.loads(man_path.read_text(encoding="utf-8")) if man_path.exists() else {}
        models[csv_path.stem] = (rows, man)
    return models


def f(x):
    try:
        v = float(x)
        return None if math.isnan(v) else v
    except (TypeError, ValueError):
        return None


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--raw", type=Path, default=REPO / "results" / "raw")
    ap.add_argument("--expect-items", type=int, default=116)
    ap.add_argument("--expect-k", type=int, default=10)
    args = ap.parse_args()

    models = load(args.raw)
    if not models:
        print(f"no results found in {args.raw}")
        return 1

    print(f"{'='*74}\nMETHODOLOGY QA — {len(models)} model(s) in {args.raw}\n{'='*74}")

    # ---- 1. completeness --------------------------------------------------------------
    print("\n## 1. Completeness — every cell present")
    for name, (rows, man) in models.items():
        items = {r["item_id"] for r in rows}
        if len(items) != args.expect_items:
            fail(f"{name}: {len(items)} items, expected {args.expect_items}")
            continue
        by_cond = Counter(r["condition"] for r in rows)
        missing = [c for c in CONDITIONS if by_cond.get(c, 0) == 0]
        if missing:
            fail(f"{name}: conditions absent: {missing}")
            continue
        for c in ("label", "string", "greedy"):
            if by_cond[c] != args.expect_items:
                fail(f"{name}: {c} has {by_cond[c]} rows, expected {args.expect_items}")
        k = man.get("k_samples", args.expect_k)
        if by_cond["sampled"] != args.expect_items * k:
            fail(f"{name}: sampled has {by_cond['sampled']} rows, expected "
                 f"{args.expect_items}x{k}={args.expect_items*k}")
    if not blocking:
        ok(f"all {len(models)} models have {args.expect_items} items x 4 conditions")

    # ---- 2. THE INVARIANT -------------------------------------------------------------
    print("\n## 2. Prompt invariant — identical across conditions within a model")
    bad = []
    for name, (rows, _) in models.items():
        per_item = defaultdict(set)
        for r in rows:
            per_item[r["item_id"]].add(r["prompt_sha"])
        offenders = [i for i, s in per_item.items() if len(s) != 1]
        if offenders:
            bad.append((name, len(offenders)))
    if bad:
        fail(f"prompt differed across conditions: {bad} — scoring method is confounded "
             f"with prompt and NOTHING downstream is interpretable")
    else:
        ok("every item saw a byte-identical prompt under all four conditions")

    # Across models the prompt SHOULD differ (different chat templates) but the prompt
    # CONFIG must not. A differing config sha means the instrument changed mid-run.
    cfg_shas = {m.get("prompt_config_sha") for _, m in models.values() if m}
    item_shas = {m.get("items_file_sha") for _, m in models.values() if m}
    if len(cfg_shas) > 1:
        fail(f"prompt config changed mid-run: {cfg_shas}")
    else:
        ok(f"prompt config identical across all models ({cfg_shas.pop() if cfg_shas else 'n/a'})")
    if len(item_shas) > 1:
        fail(f"item file changed mid-run: {item_shas}")
    else:
        ok("item file identical across all models")

    # ---- 3. reproducibility metadata --------------------------------------------------
    print("\n## 3. Reproducibility metadata")
    for name, (_, man) in models.items():
        if not man:
            fail(f"{name}: no manifest")
            continue
        if len(man.get("revision") or "") != 40:
            fail(f"{name}: revision not a pinned 40-char SHA ({man.get('revision')!r})")
        ids = man.get("option_label_token_ids", {})
        # dict[label -> list of candidate token ids] since the SentencePiece fix
        flat = {k: (v if isinstance(v, list) else [v]) for k, v in ids.items()}
        empty = [k for k, v in flat.items() if not v]
        if len(flat) != 5 or empty:
            warn(f"{name}: no candidate token for option(s) {empty or 'ALL'} — label "
                 f"scoring cannot work on this tokenizer")
        else:
            firsts = [v[0] for v in flat.values()]
            if len(set(firsts)) != 5:
                fail(f"{name}: option label token ids are not distinct: {flat}")
    vers = {json.dumps(m.get("packages"), sort_keys=True) for _, m in models.values() if m}
    if len(vers) > 1:
        warn(f"package versions differ across models ({len(vers)} distinct) — check the "
             f"manifests before pooling")
    else:
        ok("identical package versions across all models")

    # ---- 4. integrity of the scores ---------------------------------------------------
    print("\n## 4. Score integrity")
    for name, (rows, _) in models.items():
        vals = [f(r["score"]) for r in rows]
        out = [v for v in vals if v is not None and not (0.0 <= v <= 4.0)]
        if out:
            fail(f"{name}: {len(out)} scores outside [0,4], e.g. {out[:3]}")
    if not any("outside [0,4]" in b for b in blocking):
        ok("all scores within the 0-4 scale")

    # The grok-3 lesson from B1: a renormalised estimator returns a plausible number even
    # when essentially no probability mass was retained. Mass is what exposes it.
    print("\n## 5. Logprob mass — the grok-3 integrity check")
    for name, (rows, _) in models.items():
        for cond in ("label", "string"):
            ms = [f(r["logprob_mass"]) for r in rows if r["condition"] == cond]
            ms = [m for m in ms if m is not None]
            if not ms:
                continue
            low = sum(1 for m in ms if m < LOW_MASS_FLAG)
            mean = sum(ms) / len(ms)
            tag = f"{name} {cond}: mean mass {mean:.4f}, {low}/{len(ms)} below {LOW_MASS_FLAG}"
            if cond == "label" and low / len(ms) > 0.10:
                warn(tag + " — label scoring is reading a distribution that barely contains "
                          "the options; treat this model's label scores with suspicion")
            else:
                print(f"  [info] {tag}")

    # ---- 6. string scoring alignment --------------------------------------------------
    print("\n## 6. String scoring — token boundary alignment")
    for name, (rows, _) in models.items():
        srows = [r for r in rows if r["condition"] == "string"]
        dirty = [r for r in srows if r.get("token_boundary_clean") not in ("True", "", None)]
        if dirty:
            fail(f"{name}: {len(dirty)}/{len(srows)} string rows had a dirty token boundary "
                 f"— those log-likelihoods are meaningless")
        nfound = Counter(r["n_options_found"] for r in srows)
        if any(int(k) < 5 for k in nfound if k):
            warn(f"{name}: string scoring did not score all 5 options on every item: {dict(nfound)}")
    if not any("dirty token boundary" in b for b in blocking):
        ok("string scoring aligned cleanly on every model")

    # ---- 7. refusals and parse failures -----------------------------------------------
    print("\n## 7. Refusal and parse rates — the foundation x method confound")
    print(f"  {'model':<40}{'cond':<9}{'foundation':<14}{'refuse':>8}{'parse_fail':>11}{'scan':>7}")
    for name, (rows, _) in models.items():
        cells = defaultdict(list)
        for r in rows:
            if r["condition"] in ("greedy", "sampled"):
                cells[(r["condition"], r["foundation"])].append(r)
        for (cond, found), rs in sorted(cells.items()):
            ref = sum(r["refusal"] == "True" for r in rs) / len(rs)
            pf = sum(r["parse_failed"] == "True" for r in rs) / len(rs)
            sc = sum(r.get("parse_strategy") == "scan" for r in rs) / len(rs)
            if ref > REFUSAL_FLAG or pf > REFUSAL_FLAG:
                print(f"  {name[:39]:<40}{cond:<9}{found:<14}{ref:>8.1%}{pf:>11.1%}{sc:>7.1%}  <-- FLAG")
                warn(f"{name} {cond}/{found}: refusal {ref:.1%}, parse-fail {pf:.1%} — "
                     f"differential missingness by foundation masquerades as the headline "
                     f"interaction; run the analysis with and without this cell")
    ok("refusal/parse scan complete (flagged cells listed above, if any)")

    # ---- 8. sampled replicates --------------------------------------------------------
    print("\n## 8. Sampled condition — replicates and seeds")
    for name, (rows, man) in models.items():
        srows = [r for r in rows if r["condition"] == "sampled"]
        if not srows:
            continue
        k = man.get("k_samples", args.expect_k)
        per_item = Counter(r["item_id"] for r in srows)
        wrong = {i: n for i, n in per_item.items() if n != k}
        if wrong:
            fail(f"{name}: {len(wrong)} items do not have exactly {k} replicates")
        seeds = {r["seed"] for r in srows if r["seed"]}
        if len(seeds) != k:
            warn(f"{name}: {len(seeds)} distinct seeds, expected {k}")
    if not any("replicates" in b for b in blocking):
        ok("every item has the full replicate set with distinct seeds")

    # ---- 9. do the methods actually differ? -------------------------------------------
    print("\n## 9. Descriptive — condition means per model (sanity, not a result)")
    print(f"  {'model':<42}{'label':>9}{'string':>9}{'greedy':>9}{'sampled':>9}")
    for name, (rows, _) in sorted(models.items()):
        line = f"  {name[:41]:<42}"
        for c in CONDITIONS:
            vs = [f(r["score"]) for r in rows if r["condition"] == c]
            vs = [v for v in vs if v is not None]
            line += f"{(sum(vs)/len(vs) if vs else float('nan')):>9.3f}"
        print(line)

    # ---- summary ----------------------------------------------------------------------
    print("\n" + "=" * 74)
    if blocking:
        print(f"BLOCKING — {len(blocking)} problem(s) that invalidate part of the analysis:")
        for b in blocking:
            print(f"  - {b}")
    if warnings:
        print(f"{len(warnings)} warning(s) to carry into the write-up:")
        for w in warnings:
            print(f"  - {w}")
    if not blocking:
        print("PASS — data is analysable.")
    print("=" * 74)
    return 1 if blocking else 0


if __name__ == "__main__":
    raise SystemExit(main())
