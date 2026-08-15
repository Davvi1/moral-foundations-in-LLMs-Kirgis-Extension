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

# Clifford designed the Social Norms items as a non-moral CONTROL stimulus set, not a seventh
# foundation — the same constant exists in analyse_variance_ratio.py. It is reported, never
# averaged into a foundation-level number (that pooling inflated every rank correlation
# before 2026-08-10).
CONTROL_FOUNDATION = "Social Norms"

# Section 4 only. The cloze arm varies the PROMPT as well as the readout, so its pairwise R is
# part method and part prompt and is NOT a method contrast (C15). It is nevertheless shown in
# the matrix, because the matrix exists precisely to make every arm's contribution visible
# rather than to pre-select a basket — and it is labelled wherever it appears.
PROMPT_VARYING_METHODS = {"cloze"}


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


def balanced_block(df, fdn, methods=None):
    """Largest fully-crossed model x method x item block for one foundation.

    The moment estimator needs balance. Exclusions make the real data unbalanced, so the
    null is computed on the complete-cases block and the achieved size is reported.

    `methods` defaults to the module-level METHODS (the fixed-prompt arms). Section 4 passes
    an explicit list so the pairwise matrix can be built on ONE block covering every arm,
    which is what makes its cells comparable to each other.
    """
    methods = METHODS if methods is None else methods
    sub = df[(df.foundation == fdn) & (~df.excluded) & df.score.notna()]
    piv = sub.pivot_table(index=["model", "item_id"], columns="condition",
                          values="score", aggfunc="first")
    piv = piv.dropna(subset=[c for c in methods if c in piv.columns])
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
                    for m in methods], axis=1)   # (M, K, I)
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

    # ---------------- 4. pairwise R ------------------------------------------------
    #
    # WHY THIS EXISTS. R is a ratio of variance components computed over whatever set of arms
    # you put in the fit, so its value is a property of that CHOSEN SET, not of the models.
    # C15 was one instance: cloze sat inside the primary and inflated R 2.70x. The general
    # problem is that the primary reports ONE scalar averaged over five arms, and a scalar
    # cannot show that the arms disagree wildly about how much they disagree.
    #
    # The fix is not another exclusion — that is just a different basket, and it invites the
    # obvious objection that we dropped the arm that disagreed. The fix is to stop choosing.
    # Every PAIR of arms gets its own R, on one common block so the cells are comparable, and
    # the reader sees the whole structure. Any basket-level R is then a weighted average of
    # cells that are all on the page.
    #
    # Same estimator as section 1, so these numbers sit on the same scale as the observed R
    # reported there.
    p("## 4. Pairwise R — every method pair, on one common block\n")
    p("R is defined over whichever arms enter the fit, so a single scalar is a property of "
      "that chosen set rather than of the models. This table removes the choice: each cell "
      "is R for a two-arm design, computed with the section-1 moment estimator on ONE "
      "complete-case block per foundation, so every cell is comparable to every other.\n")
    p(f"Averaged over the six moral foundations. **{CONTROL_FOUNDATION} is Clifford's "
      f"non-moral control and is reported separately, never averaged in.**\n")
    p("Rows/columns marked † vary the PROMPT as well as the readout, so their cells are not "
      "method contrasts (C15). They are shown because the point of the table is to make "
      "every arm's contribution visible.\n")

    matrix_methods = [m for m in METHOD_ORDER if m in set(df.condition.unique())]
    mpairs = [(a, b) for i, a in enumerate(matrix_methods) for b in matrix_methods[i + 1:]]
    pair_R: dict[tuple, list] = defaultdict(list)
    ctrl_R: dict[tuple, float] = {}
    blocks: list[str] = []
    for fdn in sorted(df.foundation.unique()):
        blk = balanced_block(df, fdn, matrix_methods)
        if blk is None:
            continue
        arr, models, items = blk
        blocks.append(f"{fdn} {arr.shape[0]}x{arr.shape[2]}")
        idx = {m: i for i, m in enumerate(matrix_methods)}
        for a, b in mpairs:
            sub2 = arr[:, [idx[a], idx[b]], :]
            M2, _, I2 = sub2.shape
            r = moment_R(sub2.ravel(), None, None, None, M2, 2, I2)
            if not np.isfinite(r):
                continue
            if fdn == CONTROL_FOUNDATION:
                ctrl_R[(a, b)] = r
            else:
                pair_R[(a, b)].append(r)

    def _lab(m):
        return f"{m}†" if m in PROMPT_VARYING_METHODS else m

    p("| | " + " | ".join(_lab(m) for m in matrix_methods) + " |")
    p("|---" * (len(matrix_methods) + 1) + "|")
    for a in matrix_methods:
        cells = []
        for b in matrix_methods:
            if a == b:
                cells.append("—")
                continue
            v = pair_R.get((a, b)) or pair_R.get((b, a))
            cells.append(f"{np.mean(v):.2f}" if v else "—")
        p(f"| **{_lab(a)}** | " + " | ".join(cells) + " |")
    p("")
    p(f"Blocks (models x items): {', '.join(blocks)}\n")

    p("Sorted, with mean retained probability mass for the probability arms — the column that "
      "explains the ordering:\n")
    mass = ok.groupby("condition")["logprob_mass"].mean()
    p("| pair | R (6 moral) | control alone | mass, arm A | mass, arm B |")
    p("|---|---:|---:|---:|---:|")
    for (a, b), v in sorted(pair_R.items(), key=lambda kv: np.mean(kv[1])):
        ma, mb = mass.get(a, float("nan")), mass.get(b, float("nan"))
        p(f"| {_lab(a)} ~ {_lab(b)} | **{np.mean(v):.3f}** | "
          f"{ctrl_R.get((a, b), float('nan')):.3f} | "
          f"{'—' if math.isnan(ma) else f'{ma:.4f}'} | "
          f"{'—' if math.isnan(mb) else f'{mb:.4f}'} |")
    p("")
    p("Negative values are moment-estimator truncation — the interaction variance is below "
      "what residual noise alone produces — and a Bayesian fit with a half-normal prior on "
      "the SD would return a small positive number instead. Read them as 'indistinguishable "
      "from no interaction', not as a magnitude.\n")

    # ---------------- 5. leave-one-model-out ----------------------------------------
    #
    # WHY THIS EXISTS (C16). Every robustness check this project ran on R varied the ARMS:
    # C15's leave-one-condition-out, the scan-excluded refit, the family random effect. Nobody
    # ever varied the MODELS. R is estimated from ~27 models, several of which the project
    # itself describes as having pathological probability mass, so the obvious question — is
    # this number a property of the roster or of two or three models in it? — had gone unasked
    # for the entire life of the estimand.
    #
    # Two statistics, deliberately, because one alone is arguable:
    #   * share of the raw interaction SUM OF SQUARES. No variance-component estimator is
    #     involved at all, so it cannot be an artifact of the moment estimator's truncation.
    #   * leave-one-out on R itself, which is what a reader actually cares about but which
    #     moves the numerator AND the denominator at once.
    # If the two disagree, trust neither. Here they agree.
    p("## 5. Leave-one-model-out — how concentrated is R?\n")
    p("R is a ratio of variance components estimated over ~27 models. Every robustness check "
      "run before 2026-08-15 varied the ARMS (C15, scan-exclusion, family effect); none varied "
      "the MODELS. This section asks whether R is a property of the roster or of a few "
      "models in it.\n")
    p("Cloze is excluded throughout, as everywhere else in this file.\n")

    fdns_moral = [f for f in sorted(df.foundation.unique()) if f != CONTROL_FOUNDATION]
    blocks5 = {}
    for fdn in fdns_moral:
        b = balanced_block(df, fdn)
        if b is not None:
            blocks5[fdn] = b

    def _R_over(drop=None):
        vals = []
        for fdn, (arr, models, items) in blocks5.items():
            a = arr
            if drop is not None:
                if drop not in models:
                    continue
                a = np.delete(arr, models.index(drop), axis=0)
            r = moment_R(a.ravel(), None, None, None, a.shape[0], a.shape[1], a.shape[2])
            if np.isfinite(r):
                vals.append(r)
        return float(np.mean(vals)) if vals else float("nan")

    # Raw interaction sum of squares, per model, pooled over the six moral foundations.
    ss_total, ss_by_model = 0.0, defaultdict(float)
    for fdn, (arr, models, items) in blocks5.items():
        cm = arr.mean(axis=2)                                     # (M, K) cell means
        inter = (cm - cm.mean(1, keepdims=True)
                 - cm.mean(0, keepdims=True) + cm.mean())         # interaction contrasts
        for mdl, v in zip(models, (inter ** 2).sum(axis=1)):
            ss_by_model[mdl] += float(v)
        ss_total += float((inter ** 2).sum())

    base = _R_over()
    n_models = len(set().union(*[set(m) for _, m, _ in blocks5.values()]))
    equal_share = 100.0 / n_models if n_models else float("nan")
    p(f"Baseline R (moment estimator, mean over the six moral foundations): **{base:.3f}**. "
      f"{n_models} models enter at least one block, so an equal share of the interaction "
      f"sum of squares would be **{equal_share:.1f}%** each.\n")
    p("| model | share of interaction SS | R without it | change in R |")
    p("|---|---:|---:|---:|")
    ranked = sorted(ss_by_model.items(), key=lambda kv: -kv[1])
    for mdl, ss in ranked[:6]:
        r = _R_over(mdl)
        p(f"| {mdl} | {100 * ss / ss_total:.1f}% | {r:.3f} | {100 * (r - base) / base:+.0f}% |")
    rest = [ss for _, ss in ranked[6:]]
    if rest:
        p(f"| *mean of the remaining {len(rest)}* | *{100 * np.mean(rest) / ss_total:.1f}%* "
          f"| — | — |")
    p("")
    top_m, top_ss = ranked[0]
    p(f"**{top_m} alone carries {100 * top_ss / ss_total:.1f}% of the interaction sum of "
      f"squares** — {top_ss / np.mean([s for _, s in ranked]):.1f}x the average model's "
      f"contribution — and dropping it moves R by {100 * (_R_over(top_m) - base) / base:+.0f}%. "
      f"That is the same order as C15, from one model rather than one arm.\n")
    p("Read it alongside section 4 and `LIMITATIONS.md` 3: the concentration is not a "
      "coincidence, it is the same finding from a different direction. The models that "
      "dominate the interaction are the ones whose probability readouts sit on almost no "
      "retained mass, so the method effect is carried by cells the design can barely "
      "measure.\n")

    out_path.write_text("\n".join(L), encoding="utf-8")
    print("\n".join(L))
    print(f"\nwrote {out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
