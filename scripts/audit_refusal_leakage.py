"""Tier-0 audit (F7): does refusal leak into label scoring through the denominator?

Label scoring renormalises over the five option tokens, which FORCES an answer from a model
that, behaviourally, would decline. The renormalisation hides the refusal — but it cannot
hide the evidence: the retained probability mass drops, because the model's probability is
on refusal prefixes ("I", "Sorry", ...) rather than on digits.

Prediction: for model x foundation cells where the model behaviourally refuses (observable in
greedy generation), the label-scoring retained mass at that cell drops below the model's own
level elsewhere. If that correlation holds, label scoring is not refusal-free — it is
refusal-blind, and the mass column is the mandatory manipulation check.

    deficit(m, f)  =  mean mass over the model's OTHER foundations  −  mass(m, f)
    refusal(m, f)  =  share of greedy items with failure_type == "refusal"

Test: Spearman(deficit, refusal) across the model x foundation cells.

Outputs: results/derived/refusal_leakage_audit.md
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import numpy as np
import pandas as pd

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

REPO = Path(__file__).resolve().parent.parent
LONG = REPO / "results" / "derived" / "analysis_long_v2.csv"
OUT = REPO / "results" / "derived" / "refusal_leakage_audit_v2.md"


def spearman(x, y):
    rx, ry = pd.Series(x).rank(), pd.Series(y).rank()
    if rx.std() == 0 or ry.std() == 0:
        return float("nan")
    return float(np.corrcoef(rx, ry)[0, 1])


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument('--data', default=str(LONG),
                    help='long-form dataset; pass analysis_long_v2.csv for v2')
    ap.add_argument('--out', default=str(OUT))
    args = ap.parse_args()
    df = pd.read_csv(args.data)
    df["model_short"] = df["model"].str.split("/").str[-1]

    # label mass per model x foundation (label rows are never cell-excluded)
    lab = df[df.condition == "label"].copy()
    lab["logprob_mass"] = pd.to_numeric(lab["logprob_mass"], errors="coerce")
    mass = (lab.groupby(["model_short", "foundation"])["logprob_mass"]
               .mean().rename("mass").reset_index())

    # behavioural refusal from greedy (deterministic; failure_type exact per item)
    gre = df[df.condition == "greedy"].copy()
    gre["is_refusal"] = gre["failure_type"] == "refusal"
    ref = (gre.groupby(["model_short", "foundation"])["is_refusal"]
              .mean().rename("refusal").reset_index())

    cells = mass.merge(ref, on=["model_short", "foundation"], how="inner")
    # within-model deficit
    tot = cells.groupby("model_short")["mass"].transform("sum")
    n_f = cells.groupby("model_short")["mass"].transform("count")
    cells["others_mean"] = (tot - cells["mass"]) / (n_f - 1)
    cells["deficit"] = cells["others_mean"] - cells["mass"]

    # behavioural NON-ANSWER rate per model (refusal + empty + unparseable), from greedy.
    # Refusal is one way not to answer; Ministral's silent EOS is another. Both should
    # depress digit mass if the leakage hypothesis is right.
    gre["non_answer"] = gre["failure_type"].isin(["refusal", "empty_output", "unparseable"])
    model_level = (gre.groupby("model_short")["non_answer"].mean().rename("non_answer")
                      .to_frame()
                      .join(lab.groupby("model_short")["logprob_mass"].mean()
                               .rename("mean_mass")))

    L: list[str] = []
    p = L.append
    p("# Tier-0 audit — refusal leakage into label scoring\n")
    p("Label scoring forces an answer by renormalising over the five digits. The question: "
      "when a model behaviourally refuses (greedy), does its label-scoring retained mass "
      "drop at exactly those cells? If yes, label scoring is refusal-*blind*, not "
      "refusal-*free*, and the mass column is a mandatory manipulation check.\n")
    p("The test runs at two levels, because the within-model deficit has **no power for "
      "uniform refusers**: a model that declines everything has uniformly low mass and, by "
      "construction, zero deficit everywhere.\n")

    # ---- level 1: between models ----------------------------------------------------
    rho_bm = spearman(model_level["mean_mass"], model_level["non_answer"])
    p("## Level 1 — between models: does non-answering behaviour depress label mass?\n")
    p(f"Spearman(mean label mass, greedy non-answer rate) over {len(model_level)} models: "
      f"**ρ = {rho_bm:.3f}**\n")
    p("| model | greedy non-answer | mean label mass |")
    p("|---|---|---|")
    for m, r in model_level.sort_values("non_answer", ascending=False).head(8).iterrows():
        p(f"| {m} | {r.non_answer:.0%} | {r.mean_mass:.3f} |")
    p("")

    # ---- level 2: within models, where refusal is differential ----------------------
    rho_all = spearman(cells["deficit"], cells["refusal"])
    nz = cells[cells["refusal"] > 0]
    rho_nz = spearman(nz["deficit"], nz["refusal"]) if len(nz) >= 5 else float("nan")
    p("## Level 2 — within models: foundation-specific refusal vs mass crater\n")
    p(f"Cell-level Spearman over all {len(cells)} cells: ρ = {rho_all:.3f}; over the "
      f"{len(nz)} cells with any refusal: ρ = {rho_nz:.3f}. **These aggregates are "
      f"dominated by one uniform refuser (Llama-3.2-1B), for which the deficit is "
      f"uninformative** — the informative cases are the differential ones below.\n")

    p("## The cells with behavioural refusal — did label mass drop there?\n")
    p("| model | foundation | greedy refusal | label mass | model's mass elsewhere | deficit |")
    p("|---|---|---|---|---|---|")
    for _, r in nz.sort_values("refusal", ascending=False).head(15).iterrows():
        p(f"| {r.model_short} | {r.foundation} | {r.refusal:.0%} | {r['mass']:.3f} | "
          f"{r.others_mean:.3f} | {r.deficit:+.3f} |")
    p("")

    p("## Per-model mass profile (label condition)\n")
    piv = cells.pivot(index="model_short", columns="foundation", values="mass")
    order = ["Care", "Fairness", "Liberty", "Loyalty", "Authority", "Sanctity",
             "Social Norms"]
    piv = piv.reindex(columns=[c for c in order if c in piv.columns])
    p("| model | " + " | ".join(piv.columns) + " |")
    p("|---" * (len(piv.columns) + 1) + "|")
    for m, row in piv.round(3).iterrows():
        p(f"| {m} | " + " | ".join(f"{v:.3f}" for v in row) + " |")
    p("")

    p("## Verdict\n")
    # differential cases: refusal concentrated (>10%) at specific foundations of a model
    # that answers elsewhere (model-level non-answer < 50%)
    answering_models = set(model_level[model_level.non_answer < 0.5].index)
    diff_cases = nz[(nz.refusal > 0.10) & nz.model_short.isin(answering_models)]
    frac_pos = float((diff_cases["deficit"] > 0).mean()) if len(diff_cases) else float("nan")

    # The flagship case is DERIVED, not hardcoded. An earlier version of this block wrote
    # "over 20 models", "0.475 on Sanctity against 0.815", and "35% refusal" as literal text.
    # Those were the v1 numbers, and on the v2 dataset the prose asserted them anyway — a
    # generated report stating figures that contradict its own tables. Same family of defect
    # as C10/C11: a value that looks computed but is not.
    n_bm = len(model_level)
    if len(diff_cases):
        top = diff_cases.loc[diff_cases["deficit"].idxmax()]
        flagship = (f"the flagship case is exactly the predicted signature: {top.model_short} "
                    f"craters to mass {top['mass']:.3f} on {top.foundation} against "
                    f"{top.others_mean:.3f} on its other foundations, at {top.refusal:.0%} "
                    f"behavioural refusal on precisely that foundation.")
    else:
        flagship = ("no differential-refusal case clears the threshold in this sample, so the "
                    "within-model channel is untested here.")

    if rho_bm < -0.5 and (len(diff_cases) == 0 or frac_pos >= 0.5):
        p(f"**Leakage supported.** Between models, non-answering behaviour and label mass "
          f"are strongly coupled (ρ = {rho_bm:.2f} over {n_bm} models): models that decline or "
          f"fall silent in generation are largely those whose digit mass collapses in the "
          f"logprob readout. The within-model evidence is thinner — only "
          f"{len(diff_cases)} differential-refusal case(s) exist in this sample — but "
          f"{flagship}")
        p("")
        p("**Caveat, from the same table:** low mass has a second cause. Mistral-7B answers "
          "100% of greedy items yet has mass 0.078 — that is the answer-format mismatch "
          "(digits not where the readout looks), not refusal. Retained mass is therefore a "
          "*necessary* integrity check that flags problems, but it is not refusal-specific; "
          "distinguishing the causes requires the raw outputs.")
        p("")
        p("**Implications.** (1) Label scoring does not avoid the refusal confound — it "
          "hides it; renormalisation manufactures a confident score from whatever digit "
          "mass remains. Studies using logprob readouts on safety-relevant content must "
          "report retained mass; Kirgis's logprob arm has no such check. (2) The flip side "
          "is useful: retained mass is a **graded, generation-free refusal detector** — "
          "differential refusal is visible in the logprob readout without sampling a single "
          "token.")
    elif rho_bm < -0.3:
        p(f"**Between-model leakage, mixed within-model evidence** (between-model "
          f"ρ = {rho_bm:.2f}; {frac_pos:.0%} of differential cells positive). Non-answering "
          f"propensity depresses label mass overall; the foundation-specific signature is "
          f"present but thin at this cell count.")
    else:
        p(f"**No clear leakage** (between-model ρ = {rho_bm:.2f}). Label mass and "
          f"behavioural non-answering appear decoupled on this sample.")
    p("")

    Path(args.out).write_text("\n".join(L), encoding="utf-8", newline="\n")
    print("\n".join(L))
    print(f"\nwrote {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
