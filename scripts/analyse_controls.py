"""Step 5 — the three pre-specified controls. Runs locally, numpy/pandas only.

1. PERMUTATION NULL. Shuffle method labels within model x item and recompute R. Under a
   correct pipeline this must collapse toward 0: with the labels meaningless there is no
   model x method interaction left to find. If it does not, the model is misspecified
   rather than the world being interesting.

   DEVIATION FROM THE ANALYSIS PLAN, stated rather than hidden. The plan said the null uses
   the same Bayesian model. That is 100 permutations x 7 foundations = 700 MCMC fits, about
   twelve hours. The null is a CALIBRATION CHECK, not an inferential quantity — it only has
   to show that R collapses when the labels carry no information — so it uses the ANOVA
   moment estimator from the B2 design simulation, which is instant. A handful of full MCMC
   fits on permuted data can be run as a spot check that the two agree.

2. POSITIVE CONTROL. All four methods must rank Sanctity above Social Norms, in the same
   direction as Clifford's per-vignette human means. If a method fails this, it is not
   measuring moral severity and no variance ratio involving it means anything.

3. RANK AGREEMENT. Spearman rho over models, per method pair, per foundation, after
   centring out the method main effect. DESCRIPTIVE ONLY — no threshold is attached,
   because at this N the statistic is too blunt to carry one.

    python scripts/analyse_controls.py
"""

from __future__ import annotations

import argparse

import math
from collections import defaultdict
from pathlib import Path

import numpy as np
import pandas as pd

REPO = Path(__file__).resolve().parent.parent
LONG = REPO / "results" / "derived" / "analysis_long_v2.csv"
OUT = REPO / "results" / "derived" / "controls_v2.md"
# Derived from the data at runtime, not hardcoded: v1 has 4 conditions, v2 has 6. A literal
# list KeyErrors on v2 (or silently analyses a subset). Fixed order for stable report output.
METHOD_ORDER = ["label", "string", "string_line", "string_bare", "cloze", "greedy", "sampled"]
METHODS: list = []           # populated in main() from the dataset actually loaded


# CLOZE IS EXCLUDED BY DEFAULT — same reason as analyse_variance_ratio.py (C15). The
# permutation control recomputes R, so a cloze-inclusive block reports a confounded observed R
# even though the CALIBRATION conclusion (observed >> null) holds either way. The control
# should calibrate the estimand we actually publish, not a different one.
CONTROL_EXCLUDED_METHODS = {"cloze"}


def methods_in(df) -> list:
    have = set(df.condition.unique()) - CONTROL_EXCLUDED_METHODS
    return [m for m in METHOD_ORDER if m in have] + sorted(have - set(METHOD_ORDER))


def spearman(x, y):
    x, y = np.asarray(x, float), np.asarray(y, float)
    if len(x) < 3:
        return float("nan")
    rx = pd.Series(x).rank().values
    ry = pd.Series(y).rank().values
    if rx.std() == 0 or ry.std() == 0:
        return float("nan")
    return float(np.corrcoef(rx, ry)[0, 1])


def moment_R(y, m_idx, k_idx, i_idx, M, K, I):
    """ANOVA moment estimator for R on a BALANCED design. Same algebra as the B2 simulation.

        E[MS_MK] = s2_e + I*s2_MR
        E[MS_M]  = s2_e + I*s2_MR + K*I*s2_M
    """
    y = np.asarray(y, float).reshape(M, K, I)
    ybar = y.mean()
    ym = y.mean(axis=(1, 2))[:, None, None]
    yr = y.mean(axis=(0, 2))[None, :, None]
    yi = y.mean(axis=(0, 1))[None, None, :]
    ymr = y.mean(axis=2)[:, :, None]

    ms_M = (K * I * ((ym - ybar) ** 2).sum()) / (M - 1)
    ms_MK = (I * ((ymr - ym - yr + ybar) ** 2).sum()) / ((M - 1) * (K - 1))
    resid = y - (ym + yr + yi - 2 * ybar) - (ymr - ym - yr + ybar)
    df_e = (M - 1) * (K - 1) * (I - 1) + (M - 1) * (I - 1) + (K - 1) * (I - 1)
    ms_e = (resid ** 2).sum() / df_e

    s2_MR = (ms_MK - ms_e) / I
    s2_M = (ms_M - ms_MK) / (K * I)
    return (s2_MR / s2_M) if s2_M > 0 else float("nan")


def balanced_block(df, fdn):
    """Largest fully-crossed model x method x item block for one foundation.

    The moment estimator needs balance. Exclusions make the real data unbalanced, so the
    null is computed on the complete-cases block and the achieved size is reported.
    """
    sub = df[(df.foundation == fdn) & (~df.excluded) & df.score.notna()]
    piv = sub.pivot_table(index=["model", "item_id"], columns="condition",
                          values="score", aggfunc="first")
    piv = piv.dropna(subset=[c for c in METHODS if c in piv.columns])
    if piv.empty:
        return None
    counts = piv.reset_index().groupby("model")["item_id"].nunique()
    items_per_model = counts.max()
    keep_models = counts[counts == items_per_model].index.tolist()
    piv = piv.reset_index()
    piv = piv[piv.model.isin(keep_models)]
    items = sorted(piv.item_id.unique())
    piv = piv[piv.item_id.isin(items)]
    if len(keep_models) < 4 or len(items) < 4:
        return None
    piv = piv.sort_values(["model", "item_id"])
    arr = np.stack([piv[m].values.reshape(len(keep_models), len(items))
                    for m in METHODS], axis=1)   # (M, K, I)
    return arr, keep_models, items


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument('--data', default=str(LONG),
                    help='long-form dataset; pass analysis_long_v2.csv for v2')
    ap.add_argument('--out', default=None)
    args = ap.parse_args()
    # Suffix follows the input so a v2 run cannot overwrite the v1 report (C12).
    _sfx = '_v2' if '_v2' in Path(args.data).name else ''
    out_path = Path(args.out) if args.out else (
        OUT.parent / f'controls{_sfx}.md')
    df = pd.read_csv(args.data)
    global METHODS
    METHODS = methods_in(df)
    df["excluded"] = df["excluded"].astype(str) == "True"
    L: list[str] = []
    p = L.append
    p("# Step 5 — pre-specified controls\n")

    # ---------------- 1. permutation null ------------------------------------------
    p("## 1. Permutation null\n")
    p("Method labels shuffled within model x item, R recomputed. R must collapse toward 0: "
      "with the labels meaningless there is no model x method interaction left to find.\n")
    p("**Deviation, stated:** the analysis plan specified the same Bayesian model. That is "
      "~700 MCMC fits (~12 h). The null is a calibration check, not an inferential quantity, "
      "so it uses the ANOVA moment estimator from the B2 design simulation.\n")
    p("| foundation | block (M x K x I) | observed R | null median | null 95% | observed above null? |")
    p("|---|---|---|---|---|---|")
    rng = np.random.default_rng(20260808)
    for fdn in sorted(df.foundation.unique()):
        blk = balanced_block(df, fdn)
        if blk is None:
            p(f"| {fdn} | — | no balanced block | | | |")
            continue
        arr, models, items = blk
        M, K, I = arr.shape
        obs = moment_R(arr.ravel(), None, None, None, M, K, I)
        nulls = []
        for _ in range(400):
            perm = arr.copy()
            for mi in range(M):
                for ii in range(I):
                    perm[mi, :, ii] = perm[mi, rng.permutation(K), ii]
            r = moment_R(perm.ravel(), None, None, None, M, K, I)
            if np.isfinite(r):
                nulls.append(r)
        nulls = np.array(nulls)
        lo, hi = np.percentile(nulls, [2.5, 97.5])
        above = "YES" if obs > hi else "no"
        p(f"| {fdn} | {M}x{K}x{I} | {obs:.3f} | {np.median(nulls):.3f} | "
          f"[{lo:.3f}, {hi:.3f}] | **{above}** |")
    p("")
    p("A null median near 0 means the pipeline is calibrated. If the observed R does not "
      "exceed the null interval, the data provide no evidence of a model x method "
      "interaction beyond what label-shuffling produces by chance.\n")

    # ---------------- 2. positive control ------------------------------------------
    p("## 2. Positive control — Sanctity above Social Norms\n")
    p("Clifford's human means put purity violations far above social-norm violations. Any "
      "method that fails to reproduce that ordering is not measuring moral severity.\n")
    hum = df.groupby("foundation")["clifford_wrong_mean"].mean()
    p(f"Human baseline: Sanctity {hum.get('Sanctity', float('nan')):.2f}, "
      f"Social Norms {hum.get('Social Norms', float('nan')):.2f}, "
      f"gap {hum.get('Sanctity', 0) - hum.get('Social Norms', 0):.2f}\n")
    p("| method | Sanctity | Social Norms | gap | passes? |")
    p("|---|---|---|---|---|")
    ok = df[(~df.excluded) & df.score.notna()]
    allpass = True
    for m in METHODS:
        s = ok[(ok.condition == m) & (ok.foundation == "Sanctity")]["score"].mean()
        n = ok[(ok.condition == m) & (ok.foundation == "Social Norms")]["score"].mean()
        good = s > n
        allpass &= bool(good)
        p(f"| {m} | {s:.3f} | {n:.3f} | {s-n:.3f} | {'PASS' if good else '**FAIL**'} |")
    p("")
    p(f"**{'All four methods pass.' if allpass else 'AT LEAST ONE METHOD FAILS — investigate before interpreting anything.'}**\n")

    # ---------------- 3. rank agreement --------------------------------------------
    p("## 3. Rank agreement (descriptive only — no threshold)\n")
    p("Spearman rho of the model ordering under each pair of methods, within foundation, "
      "after centring out the method main effect. **No pass/fail line is attached**: at this "
      "N the statistic is too blunt to carry one, as the B2 simulation showed.\n")
    cen = ok.copy()
    cen["score_c"] = cen["score"] - cen.groupby(["condition", "foundation"])["score"].transform("mean")
    per = cen.groupby(["foundation", "condition", "model"])["score_c"].mean().reset_index()
    pairs = [(a, b) for i, a in enumerate(METHODS) for b in METHODS[i+1:]]
    p("| foundation | " + " | ".join(f"{a[:3]}~{b[:3]}" for a, b in pairs) + " |")
    p("|---" * (len(pairs) + 1) + "|")
    allr = defaultdict(list)
    for fdn in sorted(per.foundation.unique()):
        cells = []
        for a, b in pairs:
            xa = per[(per.foundation == fdn) & (per.condition == a)].set_index("model")["score_c"]
            xb = per[(per.foundation == fdn) & (per.condition == b)].set_index("model")["score_c"]
            common = sorted(set(xa.index) & set(xb.index))
            r = spearman(xa[common], xb[common]) if len(common) >= 4 else float("nan")
            cells.append("—" if math.isnan(r) else f"{r:.2f}")
            if not math.isnan(r):
                allr[(a, b)].append(r)
        p(f"| {fdn} | " + " | ".join(cells) + " |")
    p("")
    p("Mean rho per pair across foundations:\n")
    for (a, b), v in allr.items():
        p(f"- **{a} ~ {b}**: {np.mean(v):.3f}  (min {min(v):.3f}, max {max(v):.3f}, n={len(v)})")
    p("")

    out_path.write_text("\n".join(L), encoding="utf-8")
    print("\n".join(L))
    print(f"\nwrote {out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
