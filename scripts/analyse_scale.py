"""P5 and P6 — does anything change with model scale?

    python scripts/analyse_scale.py --data results/derived/analysis_long_v2.csv

Writes results/derived/scale_analysis.md

The two predictions were registered in docs/state.md BEFORE any model above 14B was collected, each
with a pre-committed falsifier. They are evaluated here exactly as written.

  P5  The individualizing-minus-binding GAP increases with log parameter count, within the
      Qwen (0.5 -> 72.7B) and Llama (1 -> 70.6B) ladders.
      FALSIFIER: a flat or negative slope on BOTH ladders. That kills the "Kirgis's pattern
      emerges with capability" story for open-weight models at any scale we can reach.

  P6  The per-model METHOD SPREAD (max - min condition mean) DECREASES with log parameters.
      Basis: arXiv:2403.00998 -- but see C20. Its full text was read 2026-08-15 and the claim
      is a VISUAL-INSPECTION remark (p.5, "Judging from visual inspection"), over four models,
      about models that PERFORM WORSE rather than models that are SMALLER. A directional prior,
      not a published result. If true, R is partly a small-model artifact -- which qualifies
      OUR OWN headline, not just Kirgis's.

      READ P6's OUTCOME WITH ONE MORE CAVEAT, added 2026-08-15. The spread is computed over
      PROB = label, string_line, string_bare -- and label ~ string_line correlate at 0.964, so
      the spread is |label - string_bare| at r = 0.989. P6 is therefore substantially a
      statement about the BARE-PHRASE probe, whose mean retained mass is 0.0028, and not about
      method sensitivity in general. See docs/FINDINGS.md 2 and docs/LIMITATIONS.md 4.

TWO THINGS THIS SCRIPT REFUSES TO DO, both of which would be easy and wrong:

1. It does not pool all 31 models into one regression and call that the scale test. Models are
   not exchangeable draws across families -- five Qwens share a pretraining recipe, and a
   between-family slope mostly measures which families happen to be big. P5 is explicitly a
   WITHIN-LADDER prediction, so the within-family slope is the primary and the pooled slope is
   reported only as context, clearly labelled.
2. It does not report a slope without a leave-one-out check. With 4-8 points per ladder, one
   model can carry the sign. The pre-committed criterion in the plan is that a "clear" result
   needs a consistent sign across both complete ladders AND survival of dropping any single
   model. Both are computed and both are printed.
"""

from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np
import pandas as pd
import yaml
from scipy import stats

REPO = Path(__file__).resolve().parent.parent
OUT = REPO / "results" / "derived"

# Kirgis's grouping, as used in audit_kirgis_pattern.py. Liberty sits with individualizing,
# which the F6 grouping-robustness check found to be the arrangement most favourable to his
# claim -- so using it here is the conservative choice for a test of HIS hypothesis.
GROUP_A = ["Care", "Fairness", "Liberty"]      # individualizing
GROUP_B = ["Loyalty", "Authority", "Sanctity"]  # binding

# The probability readouts only. Free generation loses whole models to refusal and empty
# output (Ministral answers 0% under greedy), and a scale slope computed over a set of models
# that changes with the condition would confound scale with which models survived.
PROB = ["label", "string_line", "string_bare"]


def load_params() -> dict[str, float]:
    cfg = yaml.safe_load((REPO / "config" / "models.yaml").read_text(encoding="utf-8"))
    return {m["id"]: float(m["params_b"]) for m in cfg["primary"]}


def gap_per_model(df: pd.DataFrame) -> pd.DataFrame:
    """Individualizing-minus-binding gap per model, RAW and COMPRESSION-ADJUSTED.

    THE ADJUSTED COLUMN IS THE PRIMARY, and the reason is the single most important
    methodological point in this project — it is correction C3, applied a second time.

    Models compress toward mid-scale: fitting score = a + b*human gives b < 1. Then
    error = score - human = a - (1-b)*human, so the error is more negative wherever the human
    rating is higher. Humans rate group A above group B (2.661 vs 2.380), therefore
    **pure compression predicts a negative raw gap with no moral content whatsoever**.

    For a SCALE analysis that becomes an outright confound, not merely a bias: compression
    itself changes enormously with scale. On the Qwen ladder b runs 0.113 -> 1.059, i.e. the
    0.5B model barely tracks the human baseline at all while the 72B model tracks it almost
    1:1. As b -> 1 the compression term -(1-b)*human vanishes, so the raw gap rises with scale
    **even if the model's moral profile never changes**. Reporting the raw slope as evidence
    for "Kirgis's pattern emerges with capability" would be measuring the disappearance of
    compression and calling it morality.

    The adjustment regresses each model's scores on the human baseline and takes the residual,
    so each model is compared against its OWN severity calibration. Both are returned; the
    verdicts use the adjusted one.
    """
    d = df[df.condition.isin(PROB)].copy()
    d["error"] = d.score - d.clifford_wrong_mean

    rows = []
    for m, gm in d.groupby("model"):
        # One compression fit per model, pooled over the probability conditions, so the
        # adjustment does not itself vary by condition.
        fit = stats.linregress(gm.clifford_wrong_mean, gm.score)
        resid = gm.score - (fit.intercept + fit.slope * gm.clifford_wrong_mean)
        gm = gm.assign(_resid=resid)

        per_cond = []
        for c, gc in gm.groupby("condition"):
            fe = gc.groupby("foundation")["error"].mean()
            fr = gc.groupby("foundation")["_resid"].mean()
            a_r = [fe[f] for f in GROUP_A if f in fe]
            b_r = [fe[f] for f in GROUP_B if f in fe]
            a_a = [fr[f] for f in GROUP_A if f in fr]
            b_a = [fr[f] for f in GROUP_B if f in fr]
            if len(a_r) >= 2 and len(b_r) >= 2:
                per_cond.append((float(np.mean(a_r) - np.mean(b_r)),
                                 float(np.mean(a_a) - np.mean(b_a))))
        if per_cond:
            rows.append({"model": m,
                         "gap_raw": float(np.mean([p[0] for p in per_cond])),
                         "gap": float(np.mean([p[1] for p in per_cond])),
                         "compression_b": float(fit.slope)})
    return pd.DataFrame(rows)


def spread_per_model(df: pd.DataFrame) -> pd.DataFrame:
    """Method spread = max - min over condition means, per model. P6's outcome."""
    d = df[df.condition.isin(PROB)]
    cm = d.groupby(["model", "condition"])["score"].mean().reset_index()
    out = (cm.groupby("model")["score"].agg(lambda s: s.max() - s.min())
             .rename("spread").reset_index())
    return out


def slope(x: np.ndarray, y: np.ndarray) -> tuple[float, float, int]:
    """OLS slope of y on x, plus p-value. Returns (slope, p, n).

    Guards degenerate x. The phi family is three 3.8B models and one 14.7B, so a
    leave-one-out refit that drops the 14.7B leaves all x identical and `linregress` raises.
    That is a real property of the roster (phi has almost no scale span), not an error — the
    right response is an undefined slope, which the LOO counter then treats as not preserving
    the sign, correctly penalising a ladder that rests on one point.
    """
    if len(x) < 3 or np.ptp(x) == 0:
        return float("nan"), float("nan"), len(x)
    r = stats.linregress(x, y)
    return float(r.slope), float(r.pvalue), len(x)


def loo_signs(x: np.ndarray, y: np.ndarray) -> tuple[int, int]:
    """Leave-one-out: how many of the n refits keep the full-sample sign?"""
    full, _, n = slope(x, y)
    if not np.isfinite(full) or n < 4:
        return 0, 0
    keep = 0
    for i in range(n):
        m = np.ones(n, bool)
        m[i] = False
        s, _, _ = slope(x[m], y[m])
        if np.isfinite(s) and np.sign(s) == np.sign(full):
            keep += 1
    return keep, n


def analyse(name: str, per_model: pd.DataFrame, value_col: str, params: dict,
            families: dict, predicted: str, L: list) -> dict:
    """Run the within-ladder and pooled slopes for one outcome."""
    pm = per_model.copy()
    pm["params_b"] = pm.model.map(params)
    pm = pm.dropna(subset=["params_b", value_col])
    pm["logp"] = np.log10(pm.params_b)
    pm["family"] = pm.model.map(families)

    L.append(f"\n### {name}\n")
    L.append(f"Predicted direction: **{predicted}**\n")
    L.append("| ladder | n | span | slope per decade | p | LOO keeps sign | direction |")
    L.append("|---|---:|---:|---:|---:|---:|---|")

    results = {}
    for fam in ("qwen", "llama", "gemma", "olmo", "phi", "mistral"):
        g = pm[pm.family == fam].sort_values("logp")
        if len(g) < 3:
            continue
        s, p, n = slope(g.logp.values, g[value_col].values)
        keep, tot = loo_signs(g.logp.values, g[value_col].values)
        span = g.params_b.max() / g.params_b.min()
        direction = "increases" if s > 0 else "decreases"
        results[fam] = {"slope": s, "p": p, "n": n, "loo": (keep, tot), "span": span}
        L.append(f"| {fam} | {n} | {span:.0f}x | {s:+.4f} | {p:.3f} | "
                 f"{keep}/{tot} | {direction} |")

    s, p, n = slope(pm.logp.values, pm[value_col].values)
    L.append(f"| *(pooled, context only)* | {n} | "
             f"{pm.params_b.max()/pm.params_b.min():.0f}x | {s:+.4f} | {p:.3f} | — | "
             f"{'increases' if s > 0 else 'decreases'} |")
    results["_pooled"] = {"slope": s, "p": p, "n": n}
    L.append("\nThe pooled row mixes families and is **not** the test — models are not "
             "exchangeable draws, and a between-family slope largely measures which families "
             "happen to be large. The within-ladder rows are the prediction.\n")
    return results


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", default=str(OUT / "analysis_long_v2.csv"))
    ap.add_argument("--out", default=str(OUT / "scale_analysis.md"))
    args = ap.parse_args()

    df = pd.read_csv(args.data)
    df = df[df.score.notna()]
    df = df[df.excluded.astype(str) != "True"]
    params = load_params()
    cfg = yaml.safe_load((REPO / "config" / "models.yaml").read_text(encoding="utf-8"))
    families = {m["id"]: m["family"] for m in cfg["primary"]}

    L = ["# Scale analysis — P5 and P6\n"]
    L.append(f"Generated by `scripts/analyse_scale.py` from `{Path(args.data).name}`.")
    L.append("Both predictions were registered in `docs/state.md` with pre-committed falsifiers, "
             "before any model above 14B was collected.\n")
    L.append("Probability readouts only (`label`, `string_line`, `string_bare`). Free "
             "generation loses whole models to refusal and empty output, so a scale slope "
             "over it would confound scale with which models happened to survive.\n")

    gaps = gap_per_model(df)
    spreads = spread_per_model(df)

    L.append("")
    L.append("## The compression confound, and why the primary is the adjusted gap")
    L.append("")
    L.append("Compression itself changes with scale, and enormously. Fitting")
    L.append("`score = a + b * human` per model, the Qwen ladder runs **b = 0.113 -> 1.059**:")
    L.append("the 0.5B model barely tracks the human baseline, the 72B model tracks it almost")
    L.append("1:1. Because pure compression predicts a NEGATIVE raw gap (correction C3), the")
    L.append("raw gap rises with scale **even if the moral profile never changes**. Reporting")
    L.append("the raw slope as evidence for the capability story would be measuring the")
    L.append("disappearance of compression and calling it morality.")
    L.append("")
    cb = gaps.merge(pd.DataFrame({"model": list(params), "p": list(params.values())}),
                    on="model", how="left")
    cb = cb.dropna(subset=["p"])
    rr = stats.linregress(np.log10(cb.p), cb.compression_b)
    L.append(f"Slope of `b` on log-parameters, pooled: **{rr.slope:+.4f}** "
             f"(p = {rr.pvalue:.4f}, n = {len(cb)}). That is the confound, measured.")
    L.append("")

    analyse("P5 (context only) — RAW gap vs scale", gaps, "gap_raw",
            params, families, "INCREASES (uncorrected — see confound above)", L)
    r5 = analyse("P5 — COMPRESSION-ADJUSTED gap vs scale [PRIMARY]", gaps, "gap",
                 params, families, "INCREASES with log params", L)
    r6 = analyse("P6 — method spread vs scale", spreads, "spread",
                 params, families, "DECREASES with log params", L)

    # ---- verdicts against the pre-committed falsifiers --------------------------------
    L.append("\n## Verdicts\n")

    def verdict_for(res, want_positive, pname, falsifier):
        ladders = {k: v for k, v in res.items()
                   if k in ("qwen", "llama") and v["n"] >= 4}
        if len(ladders) < 2:
            return f"**{pname}: NOT EVALUABLE** — both complete ladders are required."
        signs = {k: np.sign(v["slope"]) for k, v in ladders.items()}
        want = 1 if want_positive else -1
        agree = all(s == want for s in signs.values())
        robust = all(v["loo"][0] == v["loo"][1] for v in ladders.values())
        detail = ", ".join(f"{k} {v['slope']:+.4f} (LOO {v['loo'][0]}/{v['loo'][1]})"
                           for k, v in ladders.items())
        if agree and robust:
            return (f"**{pname}: SUPPORTED.** Both ladders slope in the predicted direction "
                    f"and every leave-one-out refit keeps the sign. {detail}")
        if agree:
            return (f"**{pname}: SUPPORTED BUT FRAGILE.** Both ladders slope as predicted, but "
                    f"the sign does not survive dropping every single model. {detail}")
        if all(s != want for s in signs.values()):
            return (f"**{pname}: FALSIFIED.** {falsifier} {detail}")
        return (f"**{pname}: INDETERMINATE.** The two ladders disagree in sign, so the "
                f"prediction is neither supported nor cleanly falsified. {detail}")

    v5 = verdict_for(r5, True, "P5",
                     "The pre-committed falsifier was a flat or negative slope on both "
                     "ladders: Kirgis's claim 2 does not generalise to open-weight models at "
                     "any scale we can reach, and the 'emerges with capability' story is dead.")
    v6 = verdict_for(r6, False, "P6",
                     "The pre-committed basis was arXiv:2403.00998, a visual-inspection "
                     "remark suggesting larger method sensitivity for worse-performing "
                     "models (C20). That direction does not reproduce here.")
    L.append(v5 + "\n")
    L.append(v6 + "\n")
    L.append("\nA failed prediction is reported as failed. The Phase-1 record already contains "
             "one wrong directional prediction of ours (pooled residuals were argued to "
             "inflate R; they deflate it), which is the standard being kept.\n")

    Path(args.out).write_text("\n".join(L), encoding="utf-8", newline="\n")
    print("\n".join(L[-6:]))
    print(f"\nwrote {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
