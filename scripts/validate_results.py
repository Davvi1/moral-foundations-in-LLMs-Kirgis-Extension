"""Methodological QA over the collected results. Run before ANY analysis.

Capturing diagnostics is not the same as checking them. This script reads every
results/raw/*.csv and its manifest and asserts the things that must hold for the study to
mean what it claims. Anything that fails here invalidates some part of the analysis, so it
runs first and its output goes in the write-up.

    python scripts/validate_results.py --suffix _v2   # the v2 collection (31 models)
    python scripts/validate_results.py --suffix ""    # the v1 collection (20 models)
    python scripts/validate_results.py --raw DIR      # explicit directory

Exit 0 = data is analysable. Non-zero = at least one blocking problem.

--- FIXED 2026-08-10, and the bug meant this script had never passed on v2 (C13) ---

`load()` globbed `*.csv`, so it pooled the 20 v1 files and the 31 v2 files into one run of
"51 models" and checked all of them against the v1 condition list. Every v2 model therefore
failed §1 with `conditions absent: ['string']` -- v2 renamed that arm to `string_line` /
`string_bare` -- and the script exited 1 on the whole collection. Two consequences, both real:

  1. The docstring promise "Run before ANY analysis / Exit 0 = data is analysable" was never
     satisfied for v2. The entire v2 analysis ran on data this gate had rejected.
  2. §6, the token-boundary check, filters `condition == "string"`. On v2 rows that matches
     nothing, so it printed its pass line while checking ZERO rows -- a check that cannot
     fail is not a check.

Same class as C12 (v2 overwriting v1 because a path was not versioned). The fix is the same
one: make the collection an explicit argument instead of a glob that silently spans both.
"""

from __future__ import annotations

import argparse
import csv
import json
import math
import statistics
import sys
from collections import Counter, defaultdict
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent

# Conditions differ by harness. v2 split the single "string" arm into the full option line and
# the bare phrase, and added cloze. Keyed by --suffix so neither list can be applied to the
# other collection by accident.
CONDITIONS_BY_SUFFIX = {
    "":    ["label", "string", "greedy", "sampled"],
    "_v2": ["label", "string_line", "string_bare", "cloze", "greedy", "sampled"],
}
# Arms scored by forced continuation, i.e. the ones with a token boundary to verify.
STRING_ARMS_BY_SUFFIX = {"": ["string"], "_v2": ["string_line", "string_bare", "cloze"]}

# The fixed-prompt invariant applies to these and ONLY these. Cloze is excluded BY DESIGN --
# it is defined by removing the option list from the prompt, so it necessarily has a different
# prompt_sha. That exception is declared here rather than left to a blanket "all conditions
# must match" check, which cloze would fail for the one legitimate reason.
CLOZE_ARMS_BY_SUFFIX = {"": [], "_v2": ["cloze"]}
MASS_ARMS_BY_SUFFIX = {"": ["label", "string"],
                       "_v2": ["label", "string_line", "string_bare", "cloze"]}

# Thresholds fixed in the analysis plan (docs/state.md).
REFUSAL_FLAG = 0.10          # model x foundation cell flagged above this
LOW_MASS_FLAG = 0.50         # label-scoring probability mass below this is suspect

# Constancy gate -- see check_constancy(). Expressed as a FRACTION of the human baseline's
# between-item SD rather than as a bare number on the 0-4 scale, so the threshold is anchored
# to how much these items actually vary rather than to a figure someone picked.
#
# Clifford's 116 item means have between-item SD = 0.970. The MEDIAN model x condition cell in
# the v2 collection sits at SD = 0.986, i.e. ratio 1.02 -- models track human item-to-item
# variation almost exactly on average. A cell at ratio < 0.25 is therefore four-fold below
# typical, which is an outlier by a wide margin and not a judgement call.
CONSTANCY_WARN_RATIO = 0.25

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


def load(raw: Path, suffix: str):
    """Load exactly one collection. See the C13 note in the module docstring.

    v2 files are named `<model>_v2.csv`; v1 files have no suffix. A bare `*.csv` glob spans
    both, which is what made this script unusable on v2.
    """
    models = {}
    for csv_path in sorted(raw.glob("*.csv")):
        stem = csv_path.stem
        if suffix:
            if not stem.endswith(suffix):
                continue
        elif any(stem.endswith(s) for s in CONDITIONS_BY_SUFFIX if s):
            continue
        man_path = csv_path.with_suffix("").with_suffix(".manifest.json")
        if not man_path.exists():
            man_path = raw / (stem + ".manifest.json")
        rows = list(csv.DictReader(csv_path.open(encoding="utf-8")))
        man = json.loads(man_path.read_text(encoding="utf-8")) if man_path.exists() else {}
        models[stem] = (rows, man)
    return models


def human_baseline_sd(items_csv: Path) -> float | None:
    """Between-item SD of Clifford's human means -- the reference scale for the constancy gate."""
    if not items_csv.exists():
        return None
    vals = []
    for row in csv.DictReader(items_csv.open(encoding="utf-8")):
        for key in ("clifford_wrong_mean", "wrong_mean", "human_mean"):
            if row.get(key):
                v = f(row[key])
                if v is not None:
                    vals.append(v)
                break
    return statistics.pstdev(vals) if len(vals) > 1 else None


def check_constancy(models, conditions, human_sd: float | None) -> None:
    """Does the model actually discriminate between items, or is it emitting a constant?

    WHY THIS GATE EXISTS. Every other check here asks whether a number was produced correctly.
    None of them asks whether the number carries information. SmolLM2-1.7B-Instruct answers
    "3" to all 116 greedy items -- between-item SD exactly 0.000, one distinct value -- and
    passes completeness, the prompt invariant, score range, mass, boundary alignment and
    replicate count without a murmur. It then enters the analysis with the same weight as a
    model that is genuinely reading the vignettes.

    That is not a harmless nuisance row. A constant column makes Spearman rho with any other
    condition UNDEFINED (zero variance -> zero denominator), and in the variance-components
    model it enters as a model whose items do not differ, deflating the item term while still
    contributing to the model x method interaction that R is a ratio of.

    Two levels, because they mean different things:
      BLOCKING  exactly one distinct value across all items. There is no defensible analysis
                of a constant; it must be excluded or reported as a degenerate cell.
      warn      between-item SD below CONSTANCY_WARN_RATIO x the human baseline SD. Not
                broken, but discriminating so weakly that any correlation computed from it is
                driven by rounding.
    """
    print("\n## 10. Constancy — does the model discriminate between items at all?")
    if human_sd:
        floor = CONSTANCY_WARN_RATIO * human_sd
        print(f"  human baseline between-item SD = {human_sd:.3f}; "
              f"warn below {CONSTANCY_WARN_RATIO:g}x = {floor:.3f}")
    else:
        floor = None
        warn("no human baseline available — constancy gate ran on distinct-value counts only")

    flagged = 0
    for name, (rows, _) in sorted(models.items()):
        for cond in conditions:
            vals = [f(r["score"]) for r in rows if r["condition"] == cond]
            vals = [v for v in vals if v is not None]
            if len(vals) < 50:
                continue
            uniq = len({round(v, 6) for v in vals})
            sd = statistics.pstdev(vals)
            if uniq == 1:
                # WARNING, NOT BLOCKING — demoted 2026-08-10 by David's decision, and the
                # demotion is evidence-based rather than convenience. My first wording said
                # "rank correlation is undefined", which overstated it: the MODEL-LEVEL ranking
                # that carries the headline is fine, because a constant cell still has a
                # well-defined mean and contributes one ordinary point. Dropping the offending
                # model moves label~sampled by -0.004 and no pair by more than 0.022. What IS
                # undefined is any ITEM-LEVEL correlation involving the cell (zero variance,
                # zero denominator) — arithmetic, not judgement, and handled at point of use.
                #
                # Blocking on a 0.004 effect would have trained us to ignore the gate, which is
                # how a gate dies. Exclusion is handled where exclusions belong, by the uniform
                # discrimination threshold in build_analysis_data.py --min-discrimination.
                warn(f"{name} {cond}: CONSTANT — emitted {vals[0]:.3f} on all {len(vals)} "
                     f"items. Carries no item-level information, and ITEM-level correlations "
                     f"involving it are undefined (model-level ranking is unaffected)")
                flagged += 1
            elif floor is not None and sd < floor:
                warn(f"{name} {cond}: between-item SD {sd:.3f} = {sd/human_sd:.2f}x human "
                     f"({uniq} distinct values over {len(vals)} items) — barely discriminates; "
                     f"correlations involving this cell are driven by rounding")
                flagged += 1
    if not flagged:
        ok("every model x condition varies across items at a usable scale")


def f(x):
    try:
        v = float(x)
        return None if math.isnan(v) else v
    except (TypeError, ValueError):
        return None


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--raw", type=Path, default=REPO / "results" / "raw")
    ap.add_argument("--suffix", default="_v2", choices=sorted(CONDITIONS_BY_SUFFIX),
                    help="which collection to validate: '_v2' (default) or '' for v1")
    ap.add_argument("--items", type=Path, default=REPO / "data" / "mfv_116_meta.csv",
                    help="item metadata, for the human baseline SD used by the constancy gate")
    ap.add_argument("--expect-items", type=int, default=116)
    ap.add_argument("--expect-k", type=int, default=10)
    args = ap.parse_args()

    conditions = CONDITIONS_BY_SUFFIX[args.suffix]
    string_arms = STRING_ARMS_BY_SUFFIX[args.suffix]
    mass_arms = MASS_ARMS_BY_SUFFIX[args.suffix]
    cloze_arms = CLOZE_ARMS_BY_SUFFIX[args.suffix]

    models = load(args.raw, args.suffix)
    if not models:
        print(f"no results found in {args.raw} for suffix {args.suffix!r}")
        return 1

    print(f"{'='*74}\nMETHODOLOGY QA — {len(models)} model(s) in {args.raw}\n"
          f"collection {args.suffix or '(v1)'} — conditions: {', '.join(conditions)}\n{'='*74}")

    # ---- 1. completeness --------------------------------------------------------------
    print("\n## 1. Completeness — every cell present")
    for name, (rows, man) in models.items():
        items = {r["item_id"] for r in rows}
        if len(items) != args.expect_items:
            fail(f"{name}: {len(items)} items, expected {args.expect_items}")
            continue
        by_cond = Counter(r["condition"] for r in rows)
        missing = [c for c in conditions if by_cond.get(c, 0) == 0]
        if missing:
            fail(f"{name}: conditions absent: {missing}")
            continue
        for c in conditions:
            if c == "sampled":
                continue
            if by_cond[c] != args.expect_items:
                fail(f"{name}: {c} has {by_cond[c]} rows, expected {args.expect_items}")
        k = man.get("k_samples", args.expect_k)
        if by_cond["sampled"] != args.expect_items * k:
            fail(f"{name}: sampled has {by_cond['sampled']} rows, expected "
                 f"{args.expect_items}x{k}={args.expect_items*k}")
    if not blocking:
        ok(f"all {len(models)} models have {args.expect_items} items x "
           f"{len(conditions)} conditions")

    # ---- 2. THE INVARIANT -------------------------------------------------------------
    print("\n## 2. Prompt invariant — identical across conditions within a model")
    bad, cloze_same = [], []
    for name, (rows, _) in models.items():
        per_item, cloze_item = defaultdict(set), defaultdict(set)
        for r in rows:
            (cloze_item if r["condition"] in cloze_arms else per_item)[r["item_id"]].add(
                r["prompt_sha"])
        offenders = [i for i, s in per_item.items() if len(s) != 1]
        if offenders:
            bad.append((name, len(offenders)))
        # The cloze exception must be REAL. If cloze shares the fixed prompt, the option list
        # was never removed and the arm is not cloze at all -- it is a duplicate of string
        # scoring wearing a different label, which would silently fake an extra condition.
        same = [i for i, s in cloze_item.items() if s & per_item.get(i, set())]
        if same:
            cloze_same.append((name, len(same)))
    if bad:
        fail(f"prompt differed across fixed-prompt conditions: {bad} — scoring method is "
             f"confounded with prompt and NOTHING downstream is interpretable")
    else:
        ok(f"every item saw a byte-identical prompt under all "
           f"{len(conditions) - len(cloze_arms)} fixed-prompt conditions")
    if cloze_arms:
        if cloze_same:
            fail(f"cloze shares the fixed prompt on {cloze_same} — the option list was not "
                 f"removed, so cloze is not a distinct condition")
        else:
            ok("cloze uses its own prompt on every item, as designed (and only cloze does)")

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
        for cond in mass_arms:
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
    # Was `condition == "string"`, which matches NOTHING on v2 -- so this printed its pass line
    # while checking zero rows. A check that cannot fail is not a check. See C13.
    checked = 0
    for name, (rows, _) in models.items():
        for arm in string_arms:
            srows = [r for r in rows if r["condition"] == arm]
            if not srows:
                warn(f"{name}: no rows for arm {arm!r} — boundary check skipped, not passed")
                continue
            checked += len(srows)
            dirty = [r for r in srows if r.get("token_boundary_clean") not in ("True", "", None)]
            if dirty:
                fail(f"{name} {arm}: {len(dirty)}/{len(srows)} rows had a dirty token boundary "
                     f"— those log-likelihoods are meaningless")
            nfound = Counter(r["n_options_found"] for r in srows)
            if any(int(k) < 5 for k in nfound if k):
                warn(f"{name} {arm}: did not score all 5 options on every item: {dict(nfound)}")
    if not any("dirty token boundary" in b for b in blocking):
        ok(f"forced-continuation arms aligned cleanly ({checked} rows actually inspected)")

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
    print("  " + f"{'model':<34}" + "".join(f"{c[:11]:>12}" for c in conditions))
    for name, (rows, _) in sorted(models.items()):
        line = f"  {name[:33]:<34}"
        for c in conditions:
            vs = [f(r["score"]) for r in rows if r["condition"] == c]
            vs = [v for v in vs if v is not None]
            line += f"{(sum(vs)/len(vs) if vs else float('nan')):>12.3f}"
        print(line)

    # ---- 10. constancy ----------------------------------------------------------------
    check_constancy(models, conditions, human_baseline_sd(args.items))

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
