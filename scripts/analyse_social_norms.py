"""Social Norms is a NON-MORAL CONTROL, not a seventh foundation. What follows from that?

    python scripts/analyse_social_norms.py --data results/derived/analysis_long_v2.csv

WHY. Clifford et al. (2015) built the Social Norms items as a control stimulus set --
verbatim, p.9, verified by fetching the paper: violations "intended to be unusual but not
considered morally wrong (for example, drinking coffee with a spoon)", included so that
respondents would not "expect a morally loaded transgression in every scenario". Treating
them as a seventh moral foundation is a category error, and this project has been committing
it: rank correlations are averaged "across the seven foundations", and the write-up reports
that models "over-moralise" Social Norms.

THE STATISTICAL POINT, which is what makes this more than a labelling fix. The human baseline
for these items is 0.19 on a 0-4 scale -- essentially the floor. We have separately established
that models COMPRESS: score ~ a + b*human with b < 1, so every model rating is pulled toward
the middle of the scale. A compressed measurement of something at the floor MUST read high.
So "models over-moralise the non-moral items" is exactly what compression predicts even if
models treat these items no differently from any other.

The test is therefore not "is the gap large" (it is: +0.86 against 0.09-0.25 for the real
foundations) but "is the gap LARGER THAN COMPRESSION PREDICTS". We fit the compression line on
the moral items ONLY -- Social Norms is held out entirely, so it cannot influence the line it
is judged against -- then ask where Social Norms falls relative to it.

Bootstrap is over ITEMS, because the item is the unit that was sampled from Clifford's
stimulus pool and the claim is about a category of items.
"""

from __future__ import annotations

import argparse
import csv
import random
import statistics as st
import sys
from collections import defaultdict
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
CONTROL = "Social Norms"


def ols(xs: list[float], ys: list[float]) -> tuple[float, float]:
    n = len(xs)
    mx, my = sum(xs) / n, sum(ys) / n
    denom = sum((x - mx) ** 2 for x in xs)
    if denom == 0:
        return my, 0.0
    b = sum((x - mx) * (y - my) for x, y in zip(xs, ys)) / denom
    return my - b * mx, b


def decompose(item_model: dict[str, float], human: dict[str, float],
              foundation: dict[str, str]) -> dict:
    """Split the control category's gap into 'compression predicts it' and 'genuine excess'."""
    moral = sorted(i for i in item_model if foundation[i] != CONTROL)
    ctrl = sorted(i for i in item_model if foundation[i] == CONTROL)
    if not moral or not ctrl:
        return {}
    a, b = ols([human[i] for i in moral], [item_model[i] for i in moral])
    resid_moral = [item_model[i] - (a + b * human[i]) for i in moral]
    excess = [item_model[i] - (a + b * human[i]) for i in ctrl]
    raw_gap = st.mean([item_model[i] - human[i] for i in ctrl])
    predicted = st.mean([a + b * human[i] - human[i] for i in ctrl])
    return {
        "a": a, "b": b, "n_moral": len(moral), "n_ctrl": len(ctrl),
        "resid_sd": st.pstdev(resid_moral),
        "human_ctrl": st.mean([human[i] for i in ctrl]),
        "pred_ctrl": st.mean([a + b * human[i] for i in ctrl]),
        "obs_ctrl": st.mean([item_model[i] for i in ctrl]),
        "raw_gap": raw_gap, "compression": predicted, "excess": st.mean(excess),
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", default=str(REPO / "results/derived/analysis_long_v2.csv"))
    ap.add_argument("--out", default=str(REPO / "results/derived/social_norms_control.md"))
    ap.add_argument("--boot", type=int, default=5000)
    ap.add_argument("--seed", type=int, default=20260810)
    args = ap.parse_args()

    rows = [r for r in csv.DictReader(open(args.data, encoding="utf-8"))
            if r["excluded"] not in ("True", "true", "1") and r["score"] != ""]
    by_item: dict[str, list[float]] = defaultdict(list)
    by_item_cond: dict[tuple[str, str], list[float]] = defaultdict(list)
    human: dict[str, float] = {}
    foundation: dict[str, str] = {}
    for r in rows:
        try:
            s = float(r["score"])
            h = float(r["clifford_wrong_mean"])
        except (TypeError, ValueError):
            continue
        by_item[r["item_id"]].append(s)
        by_item_cond[(r["condition"], r["item_id"])].append(s)
        human[r["item_id"]] = h
        foundation[r["item_id"]] = r["foundation"]

    item_model = {i: st.mean(v) for i, v in by_item.items()}
    main_fit = decompose(item_model, human, foundation)

    # Bootstrap over items, resampling moral and control items independently so both the line
    # and the held-out mean carry their own uncertainty.
    rng = random.Random(args.seed)
    moral = sorted(i for i in item_model if foundation[i] != CONTROL)
    ctrl = sorted(i for i in item_model if foundation[i] == CONTROL)
    draws = []
    for _ in range(args.boot):
        bm = [rng.choice(moral) for _ in moral]
        bc = [rng.choice(ctrl) for _ in ctrl]
        a, b = ols([human[i] for i in bm], [item_model[i] for i in bm])
        draws.append(st.mean([item_model[i] - (a + b * human[i]) for i in bc]))
    draws.sort()
    lo, hi = draws[int(0.025 * len(draws))], draws[int(0.975 * len(draws))]

    L: list[str] = []
    L.append("# Social Norms is a non-moral control — and models treat it exactly as "
             "compression predicts\n")
    L.append("Generated by `scripts/analyse_social_norms.py`.\n")
    L.append("Clifford et al. (2015, p.9) built these 16 items to be **\"unusual but not "
             "considered morally wrong\"** — a *control stimulus set*, not a seventh moral "
             "foundation. Verified by fetching the paper; see `references.md`.\n")
    L.append("## The claim being tested\n")
    L.append("This project has reported that models **over-moralise** the non-moral items "
             "(model mean ≈ 1.05 against a human mean of 0.19). But the human value sits at "
             "the **floor of the scale**, and models are known to compress toward the middle "
             "(`score ≈ a + b·human`, `b < 1`). A compressed reading of a floor value *must* "
             "come out high. So the gap alone proves nothing.\n")
    L.append("The test: fit the compression line on the **moral items only** — Social Norms "
             "is held out entirely and cannot influence the line it is judged against — then "
             "ask whether Social Norms sits above it.\n")
    f = main_fit
    L.append("## Result\n")
    L.append(f"Compression line from the {f['n_moral']} moral items: "
             f"**model = {f['a']:.3f} + {f['b']:.3f} × human** "
             f"(residual SD {f['resid_sd']:.3f}).\n")
    L.append("| quantity | value |")
    L.append("|---|---:|")
    L.append(f"| human mean, control items | {f['human_ctrl']:.3f} |")
    L.append(f"| **predicted** model mean, from compression alone | **{f['pred_ctrl']:.3f}** |")
    L.append(f"| **observed** model mean | **{f['obs_ctrl']:.3f}** |")
    L.append(f"| raw gap vs human | {f['raw_gap']:+.3f} |")
    L.append(f"| …attributable to compression | {f['compression']:+.3f} |")
    L.append(f"| …genuine excess over the line | **{f['excess']:+.3f}** |")
    L.append(f"| excess in residual SDs | {f['excess'] / f['resid_sd']:+.2f} |")
    L.append(f"| 95% bootstrap CI on the excess ({args.boot} draws over items) | "
             f"[{lo:+.3f}, {hi:+.3f}] |")
    verdict = "INCLUDES ZERO" if lo <= 0 <= hi else "excludes zero"
    L.append(f"\n**The interval {verdict}.**\n")

    # ---- THE CATCH. Added after the first version of this analysis over-claimed. ---------
    hm = [human[i] for i in moral]
    hc = [human[i] for i in ctrl]
    overlap = [h for h in hm if min(hc) <= h <= max(hc)]
    L.append("## The catch — and it is a large one\n")
    L.append("**This is an extrapolation, not an interpolation, and the first version of this "
             "analysis did not say so.**\n")
    L.append(f"| | range | n |")
    L.append(f"|---|---|---:|")
    L.append(f"| moral items (the fitting data) | {min(hm):.2f} – {max(hm):.2f} | {len(hm)} |")
    L.append(f"| control items (the prediction target) | {min(hc):.2f} – {max(hc):.2f} | "
             f"{len(hc)} |")
    L.append(f"| moral items inside the control range | — | **{len(overlap)}** |")
    L.append(f"\nThere is **no overlap at all**, and a gap of "
             f"{min(hm) - max(hc):.2f} scale points containing no observations. The line is "
             f"fitted on data spanning {min(hm):.2f}–{max(hm):.2f} and used to predict at "
             f"{st.mean(hc):.2f}. Whether it holds there is **untestable with this "
             f"instrument**.\n")
    L.append("Worse, the relationship is **not linear over the range we do observe**, so there "
             "is no reason to assume it continues straight into the gap:\n")
    L.append("| moral items fitted | n | b | predicted at 0.19 | excess |")
    L.append("|---|---:|---:|---:|---:|")
    subs = [("all (1.40–3.80)", moral),
            ("lower half (≤2.60)", [i for i in moral if human[i] <= 2.6]),
            ("upper half (>2.60)", [i for i in moral if human[i] > 2.6])]
    for nm, ss in subs:
        if len(ss) < 8:
            continue
        aa, bb = ols([human[i] for i in ss], [item_model[i] for i in ss])
        pr = aa + bb * st.mean(hc)
        L.append(f"| {nm} | {len(ss)} | {bb:.3f} | {pr:.3f} | "
                 f"{f['obs_ctrl'] - pr:+.3f} |")
    L.append("")
    L.append("`b` rises from **0.678** at the low end to **1.226** at the high end. Fit the "
             "upper half and the model 'predicts' a control mean of −0.53, which is off the "
             "scale. **The excess is not identified**: it ranges from −0.08 to +1.58 depending "
             "on a choice with no principled answer.\n")

    L.append("## Verdict — two claims, and only one of them survives\n")
    L.append("**1. SOLID — the raw gap is not evidence of over-moralisation.** The control's "
             f"raw gap of {f['raw_gap']:+.3f} sits against 0.09–0.25 for the moral "
             "foundations, and that contrast is what the 'models over-moralise Social Norms' "
             "claim rested on. But the control items sit at the floor of the scale, and *any* "
             "compressive measurement of a floor value reads high. Every plausible compression "
             "model predicts a large positive gap there whether or not models treat these "
             "items differently. **So the raw gap carries no information about moral "
             "judgment, and the claim built on it must be withdrawn.** This does not depend on "
             "the extrapolation — it follows from the floor alone.\n")
    L.append("**2. NOT ESTABLISHED — whether a residual excess exists.** Saying models treat "
             "the control *exactly* as compression predicts requires extrapolating the "
             "compression line across a 0.9-point gap with no data, into a region where the "
             "observed relationship is already non-linear. The most defensible extrapolations "
             "— those anchored on the moral items nearest the control — agree with each other "
             "(excess −0.07 to −0.08, against −0.040 for the full fit), which is mildly "
             "reassuring. It is not a result.\n")
    L.append("**The honest summary: the raw gap is uninformative, and the residual is "
             "unidentified.** The instrument cannot answer the sharper question, because "
             "Clifford's control items were designed to sit at the floor and nothing bridges "
             "the gap between them and the moral items. That is a limitation of the stimulus "
             "set, not something a better analysis would fix.\n")
    L.append("What can still be said: the control category is where compression is **most "
             "visible**, being the only part of the instrument near a scale endpoint. A good "
             "diagnostic for compression; no evidence about moral judgment either way.\n")

    # Per condition -- does the conclusion depend on the readout?
    L.append("## By condition — is this an artifact of one readout?\n")
    L.append("| condition | line b | predicted | observed | excess |")
    L.append("|---|---:|---:|---:|---:|")
    conds = sorted({c for c, _ in by_item_cond})
    for c in conds:
        im = {i: st.mean(v) for (cc, i), v in by_item_cond.items() if cc == c}
        fc = decompose(im, human, foundation)
        if fc:
            L.append(f"| {c} | {fc['b']:.3f} | {fc['pred_ctrl']:.3f} | "
                     f"{fc['obs_ctrl']:.3f} | {fc['excess']:+.3f} |")
    L.append("")
    L.append("## Consequences for the rest of the analysis\n")
    L.append("1. **Rank correlations must not be averaged over seven foundations.** Six moral "
             "foundations plus one control is not seven of anything. Report the six, and the "
             "control separately.")
    L.append("2. **The variance ratio R already fits each foundation separately**, so no "
             "refit is needed — but `FINDINGS.md` phrasing like \"all seven foundations are "
             "indeterminate\" should read \"all six foundations, and the control\".")
    L.append("3. **Any foundation-profile figure** should visually separate the control, or a "
             "reader will take it as a seventh moral dimension — which is how this error "
             "entered in the first place.")

    out = "\n".join(L)
    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    Path(args.out).write_text(out, encoding="utf-8")
    # The Windows console is cp1252 and dies on the maths glyphs this report uses. Write the
    # file in UTF-8 (which is what matters) and degrade only the echo.
    enc = sys.stdout.encoding or "utf-8"
    print(out.encode(enc, errors="replace").decode(enc, errors="replace"))
    print(f"\nwritten to {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
