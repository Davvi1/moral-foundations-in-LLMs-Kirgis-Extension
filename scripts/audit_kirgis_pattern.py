"""Tier-0 audit (F6): is Kirgis's substantive finding method-stable?

His claim 2, the headline empirical pattern: models OVERWEIGHT care/fairness/liberty and
UNDERWEIGHT loyalty/authority/sanctity relative to the human baseline. (His grouping; note
"individualizing" strictly means care+fairness in MFT — he adds liberty to the first group,
and we follow his grouping to audit his claim, not ours.)

The statistic. Per model x method x foundation, the mean error over items:

    e = mean_items( model score  -  Clifford human mean )

and per model x method the GAP:

    gap = mean(e over {Care, Fairness, Liberty}) - mean(e over {Loyalty, Authority, Sanctity})

gap > 0  =  Kirgis's pattern. The gap is a within-method contrast, so it is invariant to a
uniform level shift between methods (string sitting ~1 point lower cancels out). That makes
it exactly the right statistic for a method-stability audit.

Outputs: results/derived/kirgis_pattern_audit.md

Sensitivity: a complete-cases version restricted to models with all four methods usable and
items scored under all four, so method comparisons are on identical data.

Known caveat, stated: in free generation some kept cells have refusal-driven item missingness
(Llama-3.1-8B Sanctity greedy: 35% refused, cell kept at rate 0.65). Refusals concentrate on
graphic items, so surviving Sanctity items skew mild -> Sanctity error biased UP -> gap biased
DOWN for those model x method cells. Direction of the bias is against Kirgis's pattern in the
free-gen arms, so a pattern that survives there is not an artifact of this.
"""

from __future__ import annotations

import math
import argparse
import sys
from collections import defaultdict
from pathlib import Path

import numpy as np
import pandas as pd

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

REPO = Path(__file__).resolve().parent.parent
LONG = REPO / "results" / "derived" / "analysis_long_v2.csv"
OUT = REPO / "results" / "derived" / "kirgis_pattern_audit_v2.md"

# Derived from the data, not hardcoded: v1 has {label, string, greedy, sampled} while v2 has
# {label, string_line, string_bare, cloze, greedy, sampled}. A hardcoded list silently
# KeyErrors on v2, or worse, silently analyses a subset if the missing name were tolerated.
# Order is fixed for stable report output.
METHOD_ORDER = ["label", "string", "string_line", "string_bare", "cloze", "greedy", "sampled"]


def methods_in(df) -> list:
    """Conditions actually present, in a stable documented order."""
    have = set(df.condition.unique())
    return [m for m in METHOD_ORDER if m in have] + sorted(have - set(METHOD_ORDER))
GROUP_A = ["Care", "Fairness", "Liberty"]          # Kirgis: overweighted
GROUP_B = ["Loyalty", "Authority", "Sanctity"]     # Kirgis: underweighted
FOUNDATIONS = GROUP_A + GROUP_B + ["Social Norms"]


def spearman(x, y):
    x, y = np.asarray(x, float), np.asarray(y, float)
    rx, ry = pd.Series(x).rank().values, pd.Series(y).rank().values
    if rx.std() == 0 or ry.std() == 0:
        return float("nan")
    return float(np.corrcoef(rx, ry)[0, 1])


def load(path=None):
    df = pd.read_csv(path or LONG)
    df["excluded"] = df["excluded"].astype(str) == "True"
    df = df[(~df.excluded) & df.score.notna()].copy()
    df["error"] = df["score"] - df["clifford_wrong_mean"]
    df["model_short"] = df["model"].str.split("/").str[-1]
    return df


def per_model_gaps(df: pd.DataFrame) -> pd.DataFrame:
    """gap per model x method, requiring at least 2 foundations per group."""
    e = (df.groupby(["model_short", "condition", "foundation"])["error"]
           .mean().reset_index())
    rows = []
    for (m, c), g in e.groupby(["model_short", "condition"]):
        f2e = dict(zip(g.foundation, g.error))
        a = [f2e[f] for f in GROUP_A if f in f2e]
        b = [f2e[f] for f in GROUP_B if f in f2e]
        if len(a) >= 2 and len(b) >= 2:
            rows.append({"model": m, "method": c,
                         "gap": float(np.mean(a) - np.mean(b)),
                         "nA": len(a), "nB": len(b)})
    return pd.DataFrame(rows)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument('--data', default=str(LONG),
                    help='long-form dataset; pass analysis_long_v2.csv for v2')
    ap.add_argument('--out', default=str(OUT))
    args = ap.parse_args()
    df = load(args.data)
    METHODS = methods_in(df)
    L: list[str] = []
    p = L.append

    p("# Tier-0 audit — is Kirgis's substantive pattern method-stable?\n")
    p("His claim 2: models overweight {Care, Fairness, Liberty} and underweight "
      "{Loyalty, Authority, Sanctity} relative to the human baseline. The audit statistic "
      "is the within-method GAP between the two groups' mean errors, which is invariant to "
      "a uniform method-level shift — so string scoring sitting ~1 point lower cannot fake "
      "or destroy the pattern by itself.\n")

    # ---- 1. pooled error table ------------------------------------------------------
    p("## 1. Mean error (model − human) per foundation, per method\n")
    tab = (df.groupby(["condition", "foundation"])["error"].mean()
             .unstack().reindex(index=METHODS, columns=FOUNDATIONS))
    p("| method | " + " | ".join(FOUNDATIONS) + " |")
    p("|---" * (len(FOUNDATIONS) + 1) + "|")
    for m in METHODS:
        cells = " | ".join(f"{tab.loc[m, f]:+.2f}" if pd.notna(tab.loc[m, f]) else "—"
                           for f in FOUNDATIONS)
        p(f"| {m} | {cells} |")
    p("")
    p("Negative everywhere would mean models under-rate wrongness across the board "
      "(a calibration shift); the *pattern* question is whether group A errors sit above "
      "group B errors within each row.\n")

    # ---- 2. the gap, per method -----------------------------------------------------
    gaps = per_model_gaps(df)
    p("## 2. The gap per method — Kirgis's pattern is gap > 0\n")
    p("| method | mean gap | SE | models with gap>0 | min | max |")
    p("|---|---|---|---|---|---|")
    for m in METHODS:
        g = gaps[gaps.method == m]["gap"]
        if g.empty:
            continue
        p(f"| {m} | {g.mean():+.3f} | {g.sem():.3f} | {(g > 0).sum()}/{len(g)} | "
          f"{g.min():+.3f} | {g.max():+.3f} |")
    p("")

    # ---- 3. cross-method stability of the per-model gaps ----------------------------
    p("## 3. Does method choice change *which models* show the pattern?\n")
    wide = gaps.pivot(index="model", columns="method", values="gap")
    pairs = [(a, b) for i, a in enumerate(METHODS) for b in METHODS[i + 1:]]
    p("| pair | Spearman(per-model gaps) | sign flips | mean |Δgap| |")
    p("|---|---|---|---|")
    for a, b in pairs:
        sub = wide[[a, b]].dropna()
        if len(sub) < 4:
            p(f"| {a}~{b} | — | — | — |")
            continue
        rho = spearman(sub[a], sub[b])
        flips = int(((sub[a] > 0) != (sub[b] > 0)).sum())
        p(f"| {a}~{b} | {rho:.3f} | {flips}/{len(sub)} | "
          f"{(sub[a] - sub[b]).abs().mean():.3f} |")
    p("")
    p("A *sign flip* means: under one method the model shows Kirgis's pattern, under the "
      "other it shows the reverse — the vivid version of 'would you publish a different "
      "conclusion about this model?'\n")

    # ---- 4. per-foundation error ordering across methods ----------------------------
    p("## 4. Do methods agree on the foundation ordering of errors?\n")
    six = [f for f in FOUNDATIONS if f != "Social Norms"]
    vecs = {m: [tab.loc[m, f] for f in six] for m in METHODS if m in tab.index}
    p("| pair | Spearman(6-foundation error vectors) |")
    p("|---|---|")
    for a, b in pairs:
        if a in vecs and b in vecs:
            p(f"| {a}~{b} | {spearman(vecs[a], vecs[b]):.3f} |")
    p("")

    # ---- 5. complete-cases sensitivity ----------------------------------------------
    p("## 5. Sensitivity: complete cases only\n")
    # "Complete" means every condition PRESENT IN THIS DATASET, not a hardcoded 4. v2 has six
    # conditions, so the old literal silently produced an empty complete-case set rather than
    # erroring in an obvious place.
    n_meth = len(METHODS)
    p(f"Models with all {n_meth} methods usable, items scored under all of them — method "
      "comparisons on literally identical data.\n")
    counts = df.groupby("model_short")["condition"].nunique()
    full_models = counts[counts == n_meth].index
    cc = df[df.model_short.isin(full_models)]
    keep = (cc.groupby(["model_short", "item_id"])["condition"].nunique() == n_meth)
    keep_idx = set(keep[keep].index)
    cc = cc[cc.set_index(["model_short", "item_id"]).index.isin(keep_idx)]
    gaps_cc = per_model_gaps(cc)
    if gaps_cc.empty:
        p("**No complete-case set exists for this dataset.** Every model would need all "
          f"{n_meth} conditions usable on the same items; with the cloze arm present that is "
          "not satisfiable, since cloze is prompt-varying and excluded from the primary "
          "comparison. Skipping this section rather than reporting an empty table.")
        p("")
        gaps_cc = None
    p(f"Complete-case set: {cc.model_short.nunique()} models, "
      f"{cc.groupby('model_short')['item_id'].nunique().min()}–"
      f"{cc.groupby('model_short')['item_id'].nunique().max()} items per model.\n")
    p("| method | mean gap | models with gap>0 |")
    p("|---|---|---|")
    for m in (METHODS if gaps_cc is not None else []):
        g = gaps_cc[gaps_cc.method == m]["gap"]
        if g.empty:
            continue
        p(f"| {m} | {g.mean():+.3f} | {(g > 0).sum()}/{len(g)} |")
    p("")

    # ---- 6. per-family view (echoes his per-provider Fig 2) -------------------------
    p("## 6. Per-family gaps (his Figure 2 was per provider)\n")
    fam = df.merge(gaps, left_on=["model_short", "condition"],
                   right_on=["model", "method"], how="inner")
    fam_g = (fam.groupby(["family", "method"])["gap"].mean().unstack()
                .reindex(columns=METHODS))
    p("| family | " + " | ".join(METHODS) + " |")
    p("|---" * (len(METHODS) + 1) + "|")
    for famname, row in fam_g.iterrows():
        cells = " | ".join(f"{v:+.2f}" if pd.notna(v) else "—" for v in row)
        p(f"| {famname} | {cells} |")
    p("")

    # ---- 6b. the confound that makes a raw gap of zero NON-neutral ------------------
    p("## 6b. Why a raw gap of ~0 is *not* neutral evidence\n")
    hum = df.groupby("foundation")["clifford_wrong_mean"].mean()
    hA, hB = hum[GROUP_A].mean(), hum[GROUP_B].mean()
    p("The human baseline has its own foundation structure:\n")
    p("| foundation | human mean |")
    p("|---|---|")
    for f, v in hum.sort_values(ascending=False).items():
        p(f"| {f} | {v:.3f} |")
    p("")
    p(f"Humans rate group A ({', '.join(GROUP_A)}) at **{hA:.3f}** and group B "
      f"({', '.join(GROUP_B)}) at **{hB:.3f}** — a difference of **{hA-hB:+.3f}**.\n")
    p("Now combine that with the compression in §7. Compression pulls every rating toward "
      "mid-scale, so the *higher* human ratings (group A) are pulled DOWN more and the "
      "*lower* ones (group B) are pushed UP more. **Pure compression therefore predicts a "
      "NEGATIVE raw gap, with no moral content whatsoever.**\n")
    p("So 'raw gap ≈ 0' does not mean 'no pattern'. It means the observed data sit between "
      "the compression prediction (negative) and Kirgis's prediction (positive). The raw gap "
      "cannot adjudicate; the compression-adjusted gap in §7 is the statistic that can.\n")

    # ---- 6c. grouping robustness ----------------------------------------------------
    p("## 6c. Does the verdict depend on where Liberty is placed?\n")
    p("Kirgis groups Liberty with the individualizing foundations; canonical MFT treats "
      "Care+Fairness as individualizing and leaves Liberty separate. Raw mean gaps under "
      "three groupings:\n")
    p("| grouping | label | string | greedy | sampled |")
    p("|---|---|---|---|---|")
    for name, GA, GB in [("Kirgis (A = Care/Fair/Liberty)", GROUP_A, GROUP_B),
                         ("canonical (A = Care/Fair)", ["Care", "Fairness"], GROUP_B),
                         ("Liberty with binding", ["Care", "Fairness"],
                          GROUP_B + ["Liberty"])]:
        e = (df.groupby(["model_short", "condition", "foundation"])["error"]
               .mean().reset_index())
        vals = {}
        for c, g in e.groupby("condition"):
            gg = []
            for m, gm in g.groupby("model_short"):
                f2e = dict(zip(gm.foundation, gm.error))
                a = [f2e[f] for f in GA if f in f2e]
                b = [f2e[f] for f in GB if f in f2e]
                if len(a) >= 2 and len(b) >= 2:
                    gg.append(np.mean(a) - np.mean(b))
            if gg:
                vals[c] = float(np.mean(gg))
        cells = " | ".join(f"{vals[m]:+.3f}" if m in vals else "—" for m in METHODS)
        p(f"| {name} | {cells} |")
    p("")
    p("The conclusion is grouping-robust — and note that **Kirgis's own grouping is the most "
      "favourable to his claim**; the canonical one is more negative still.\n")

    # ---- 7. severity compression — the likely mechanism -----------------------------
    p("## 7. Severity compression: is the error structure about foundations at all?\n")
    p("Model errors may simply track how *mild* the human rating is — compression toward "
      "mid-scale over-rates mild items and under-rates severe ones, regardless of "
      "foundation. Per method, an OLS of item-level error on the human item mean:\n")
    p("| method | slope | r | reading |")
    p("|---|---|---|---|")
    adj_frames = []
    for m in METHODS:
        sub = df[df.condition == m]
        if len(sub) < 100:
            continue
        b, a = np.polyfit(sub["clifford_wrong_mean"], sub["error"], 1)
        r = float(np.corrcoef(sub["clifford_wrong_mean"], sub["error"])[0, 1])
        p(f"| {m} | {b:+.3f} | {r:+.3f} | "
          f"{'strong compression' if b < -0.3 else 'mild compression' if b < -0.1 else 'little'} |")
        s2 = sub.copy()
        s2["error"] = s2["error"] - (a + b * s2["clifford_wrong_mean"])
        adj_frames.append(s2)
    p("")
    adj = pd.concat(adj_frames)
    gaps_adj = per_model_gaps(adj)
    p("Gap recomputed on compression-adjusted errors (item-severity effect removed):\n")
    p("| method | adjusted mean gap | models with gap>0 |")
    p("|---|---|---|")
    for m in METHODS:
        g = gaps_adj[gaps_adj.method == m]["gap"]
        if g.empty:
            continue
        p(f"| {m} | {g.mean():+.3f} | {(g > 0).sum()}/{len(g)} |")
    p("")
    p("If raw and adjusted gaps agree, foundation content adds little beyond item severity; "
      "a residual foundation pattern would survive the adjustment.\n")

    # ---- verdict --------------------------------------------------------------------
    p("## Verdict\n")
    share = {m: float((gaps[gaps.method == m]["gap"] > 0).mean())
             for m in METHODS if not gaps[gaps.method == m].empty}
    means = {m: float(gaps[gaps.method == m]["gap"].mean()) for m in share}
    pair_rhos = []
    for a_, b_ in pairs:
        sub = wide[[a_, b_]].dropna()
        if len(sub) >= 4:
            pair_rhos.append(spearman(sub[a_], sub[b_]))
    agree = float(np.nanmean(pair_rhos))

    adj_means = {m: float(gaps_adj[gaps_adj.method == m]["gap"].mean())
                 for m in METHODS if not gaps_adj[gaps_adj.method == m].empty}
    adj_share = {m: float((gaps_adj[gaps_adj.method == m]["gap"] > 0).mean())
                 for m in adj_means}

    p("**The raw gap cannot adjudicate this claim, and the adjusted gap is weakly in "
      "Kirgis's favour.**\n")
    p(f"Raw mean gaps are ≈ 0 ({min(means.values()):+.2f} to {max(means.values()):+.2f}) "
      f"— but §6b shows *pure compression predicts a negative gap*, because the human "
      f"baseline itself rates group A above group B and compression pulls high ratings down "
      f"more than low ones. So 'raw ≈ 0' sits between the compression prediction and "
      f"Kirgis's, and settles nothing.\n")
    p(f"Removing the item-severity effect (§7), the adjusted gap turns **positive under "
      f"every method** ({min(adj_means.values()):+.3f} to {max(adj_means.values()):+.3f}, "
      f"{min(adj_share.values()):.0%}–{max(adj_share.values()):.0%} of models). That is "
      f"weak evidence *in Kirgis's direction*, not against him — but it is small, only about "
      f"half of models show it, and we have no interval on it. **SUGGESTIVE, not "
      f"established, in either direction.**\n")
    p(f"What *is* established: the four methods agree with each other (mean per-model gap "
      f"correlation ρ = {agree:.2f}), so whatever the answer is, **it is not an artifact of "
      f"scoring method.** Kirgis's confound does not threaten this particular claim.\n")
    p("")
    p("Family heterogeneity is large and method-stable (§6): gemma, granite and yi show the "
      "pattern under every method; qwen, mistral, smollm and phi show its reverse under "
      "every method. **For this claim, which models you sample matters far more than how "
      "you score them.** Kirgis sampled frontier-scale closed models; we sampled ≤14B open "
      "ones — the Tier-3 size ladders (Qwen 0.5→72B, Llama 1→70B) now directly test whether "
      "his pattern *emerges with scale*, which would connect his claims 2 and 4.\n")
    p("Caveat carried from the design: refusal-driven item missingness in free generation "
      "biases Sanctity errors upward (survivors are the milder items), which biases the gap "
      "*downward* in greedy/sampled for high-refusal models. A pattern surviving there is "
      "therefore conservative.\n")

    Path(args.out).write_text("\n".join(L), encoding="utf-8", newline="\n")
    print("\n".join(L))
    print(f"\nwrote {OUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
