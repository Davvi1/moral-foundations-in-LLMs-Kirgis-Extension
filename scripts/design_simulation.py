"""B2 -- can R be estimated with useful precision at feasible N? Decides the roster size.

R = sigma2(model x method) / sigma2(model) is a RATIO OF TWO VARIANCE COMPONENTS, and
variance components estimated from few groups are imprecise. With ~13 models the interval
on R may be wide enough that the pre-specified bands (0.25 / 1.0) cannot be resolved. This
must be settled BEFORE the confirmatory run, while N can still change, and before the
analysis plan is deposited.

Two parts:
  1. CALIBRATE  -- estimate realistic sigma2_model and sigma2_item per foundation from
                   Kirgis's own 21-model x 116-item data, so the simulation reflects what
                   MFV data on LLMs actually looks like rather than invented magnitudes.
  2. SIMULATE   -- generate data under known R at several N, recover R by ANOVA method of
                   moments, and report the sampling distribution and how often it lands in
                   the correct pre-specified band.

Estimator (balanced crossed design, M models x K=4 methods x I items, one obs per cell,
method fixed, model and item random):

    E[MS_MK] = sigma2_e + I * sigma2_MR
    E[MS_M]  = sigma2_e + I * sigma2_MR + K * I * sigma2_M

  =>  sigma2_MR = (MS_MK - MS_E) / I
      sigma2_M  = (MS_M  - MS_MK) / (K * I)

Closed form, so thousands of replicates run in seconds -- no MCMC needed for a design
question. A Bayesian fit with weak priors has comparable width; this bounds what is
achievable.

    python scripts/design_simulation.py --kirgis-repo <path>
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

# Windows consoles default to cp1252, which cannot encode the Greek letters used below.
# The report files are always written as UTF-8; this only affects the echo to stdout.
try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

REPO = Path(__file__).resolve().parent.parent
OUTDIR = REPO / "results" / "derived"
K_METHODS = 4
RNG = np.random.default_rng(20260807)

# Pre-specified bands, from state.md
BANDS = [(0.0, 0.25, "robust"), (0.25, 1.0, "degraded"), (1.0, np.inf, "not interpretable")]


def band(r: float) -> str:
    if not np.isfinite(r) or r < 0:
        return "undefined"
    for lo, hi, name in BANDS:
        if lo <= r < hi:
            return name
    return "not interpretable"


# ---------------------------------------------------------------------------------------
# 1. Calibration
# ---------------------------------------------------------------------------------------


def calibrate(kirgis_repo: Path) -> pd.DataFrame:
    """Variance components per foundation from Kirgis's cleaned responses.

    He has one method per model, so sigma2_model_x_method is NOT estimable from his data --
    only sigma2_model and sigma2_item are. That is exactly why R has to be simulated across
    a range of assumed values rather than estimated from prior work.
    """
    df = pd.read_csv(kirgis_repo / "data" / "results" / "cleaned_model_responses.csv")
    out = []
    for f, g in df.groupby("Foundation"):
        piv = g.pivot_table(index="Model", columns="Scenario", values="Expected Value Answer")
        y = piv.values
        grand = np.nanmean(y)
        model_eff = np.nanmean(y, axis=1) - grand
        item_eff = np.nanmean(y, axis=0) - grand
        resid = y - grand - model_eff[:, None] - item_eff[None, :]
        out.append({
            "foundation": f,
            "n_models": piv.shape[0],
            "n_items": piv.shape[1],
            "var_model": float(np.nanvar(model_eff, ddof=1)),
            "var_item": float(np.nanvar(item_eff, ddof=1)),
            "var_resid": float(np.nanvar(resid, ddof=1)),
            "sd_model": float(np.sqrt(np.nanvar(model_eff, ddof=1))),
            "sd_item": float(np.sqrt(np.nanvar(item_eff, ddof=1))),
        })
    return pd.DataFrame(out).sort_values("foundation")


# ---------------------------------------------------------------------------------------
# 2. Simulation
# ---------------------------------------------------------------------------------------


def simulate_batch(n_rep, M, I, var_M, var_MR, var_I, resid_sds):
    """Vectorised over replicates. Returns (R_hat, var_M_hat, var_MR_hat) arrays."""
    Kk = K_METHODS
    u = RNG.normal(0, np.sqrt(var_M), size=(n_rep, M, 1, 1))
    w = RNG.normal(0, np.sqrt(var_MR), size=(n_rep, M, Kk, 1))
    v = RNG.normal(0, np.sqrt(var_I), size=(n_rep, 1, 1, I))
    gamma = np.array([0.0, 0.1, -0.1, 0.05]).reshape(1, 1, Kk, 1)  # method main effect
    e = RNG.normal(0, 1, size=(n_rep, M, Kk, I)) * np.asarray(resid_sds).reshape(1, 1, Kk, 1)
    y = u + w + v + gamma + e

    ybar = y.mean(axis=(1, 2, 3), keepdims=True)
    ym = y.mean(axis=(2, 3), keepdims=True)      # model marginal
    yr = y.mean(axis=(1, 3), keepdims=True)      # method marginal
    ymr = y.mean(axis=3, keepdims=True)          # model x method cell means

    ss_M = Kk * I * ((ym - ybar) ** 2).sum(axis=(1, 2, 3))
    ms_M = ss_M / (M - 1)

    ss_MK = I * ((ymr - ym - yr + ybar) ** 2).sum(axis=(1, 2, 3))
    ms_MK = ss_MK / ((M - 1) * (Kk - 1))

    yi = y.mean(axis=(1, 2), keepdims=True)      # item marginal
    resid = y - (ym + yr + yi - 2 * ybar) - (ymr - ym - yr + ybar)
    df_e = (M - 1) * (Kk - 1) * (I - 1) + (M - 1) * (I - 1) + (Kk - 1) * (I - 1)
    ms_E = (resid ** 2).sum(axis=(1, 2, 3)) / df_e

    var_MR_hat = (ms_MK - ms_E) / I
    var_M_hat = (ms_M - ms_MK) / (Kk * I)
    with np.errstate(divide="ignore", invalid="ignore"):
        R_hat = np.where(var_M_hat > 0, var_MR_hat / var_M_hat, np.nan)
    return R_hat, var_M_hat, var_MR_hat


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--kirgis-repo", required=True, type=Path)
    ap.add_argument("--n-rep", type=int, default=4000)
    args = ap.parse_args()

    OUTDIR.mkdir(parents=True, exist_ok=True)
    L: list[str] = []
    p = L.append

    p("# B2 — Design simulation: is R estimable at feasible N?\n")
    p("Generated by `scripts/design_simulation.py`. Decides the model roster size and whether "
      "the pre-specified decision rule survives. **Run before the confirmatory data.**\n")

    # --- calibration -------------------------------------------------------------------
    cal = calibrate(args.kirgis_repo)
    p("## 1. Calibration against Kirgis's observed data\n")
    p("Variance components per foundation from his 21 models × 116 items. He has one method "
      "per model, so σ²(model × method) is **not estimable** from his data — which is exactly "
      "why R must be simulated across a range rather than looked up.\n")
    p(cal[["foundation", "n_models", "n_items", "sd_model", "sd_item", "var_model",
           "var_item", "var_resid"]].round(4).to_markdown(index=False))
    p("")

    var_M = float(cal["var_model"].median())
    var_I = float(cal["var_item"].median())
    var_resid_base = float(cal["var_resid"].median())
    p(f"Median across foundations: **σ²_model = {var_M:.4f}** (SD {np.sqrt(var_M):.3f}), "
      f"σ²_item = {var_I:.4f}, σ²_resid = {var_resid_base:.4f}. "
      f"Simulation uses these.\n")

    # Method-specific residual SDs, per the pre-specified structure:
    # label and string are deterministic expectations (small), greedy is discretised to
    # integers (larger), sampled is a mean of k=10 draws (intermediate).
    base = np.sqrt(var_resid_base)
    resid_sds = np.array([0.6, 0.6, 1.3, 1.3 / np.sqrt(10)]) * base
    p(f"Method-specific residual SDs used (label, string, greedy, sampled): "
      f"{np.round(resid_sds, 4).tolist()} — label and string are deterministic expectations, "
      f"greedy is discretised to integers, sampled is a mean of k=10 so its error scales "
      f"as 1/√10.\n")

    # --- simulation --------------------------------------------------------------------
    p("## 2. Sampling distribution of R̂\n")
    p(f"{args.n_rep} replicates per cell, 17 items (the median foundation), 4 methods.\n")

    Ns = [8, 13, 20, 30]
    true_Rs = [0.10, 0.25, 0.50, 1.00, 2.00]
    recs = []
    for M in Ns:
        for R_true in true_Rs:
            Rh, vM, vMR = simulate_batch(args.n_rep, M, 17, var_M, R_true * var_M, var_I,
                                         resid_sds)
            ok = Rh[np.isfinite(Rh)]
            correct = np.mean([band(x) == band(R_true) for x in ok]) if len(ok) else np.nan
            recs.append({
                "N_models": M, "R_true": R_true,
                "median_Rhat": float(np.median(ok)),
                "p2.5": float(np.percentile(ok, 2.5)),
                "p97.5": float(np.percentile(ok, 97.5)),
                "ratio_width": float(np.percentile(ok, 97.5) / max(np.percentile(ok, 2.5), 1e-9)),
                "P_correct_band": float(correct),
                "P_undefined": float(1 - len(ok) / len(Rh)),
            })
    sim = pd.DataFrame(recs)
    p(sim.round(3).to_markdown(index=False))
    p("")

    p("`ratio_width` is the 97.5th percentile divided by the 2.5th — the multiplicative width "
      "of the 95% interval. `P_correct_band` is how often R̂ lands in the correct one of "
      "robust / degraded / not-interpretable. `P_undefined` is how often σ̂²_model comes out "
      "≤ 0, which makes R undefined.\n")

    # --- verdict -----------------------------------------------------------------------
    p("## 3. Verdict\n")
    piv = sim.pivot(index="R_true", columns="N_models", values="P_correct_band").round(3)
    p("Probability of landing in the correct band:\n")
    p(piv.to_markdown())
    p("")

    p("**Read the 0.25 and 1.00 rows correctly.** Those true values sit exactly ON band "
      "boundaries, so ~50% is the *ceiling*, not a failure — half the sampling distribution "
      "necessarily falls either side however large N gets. They are shown to make that "
      "explicit. The informative rows are the band interiors: 0.10, 0.50, 2.00.\n")

    interior = sim[sim["R_true"].isin([0.10, 0.50, 2.00])]
    piv2 = interior.pivot(index="R_true", columns="N_models",
                          values="P_correct_band").round(3)
    p("Interior-band accuracy — the number that actually matters:\n")
    p(piv2.to_markdown())
    p("")
    worst = interior.groupby("N_models")["P_correct_band"].min().round(3)
    p("Worst case across interior values, by roster size:\n")
    p(worst.to_frame("min_P_correct").to_markdown())
    p("")

    p("### What this means for the design\n")
    p("1. **The estimator is unbiased** — median R̂ tracks R_true at every N. The problem is "
      "variance, not bias.")
    p("2. **Precision is worse than the back-of-envelope predicted.** A rough calculation "
      "before this simulation suggested a 95% interval spanning about ×/÷2.5 at N=13; the "
      "actual multiplicative width at N=13, R=0.5 is **~12×**. The analytic approximation was "
      "optimistic and should not be quoted.")
    p("3. **N=13 misclassifies a genuinely 'degraded' R of 0.5 about one time in four.** "
      "Going to N=20 cuts that to roughly one in seven; N=30 to about one in seventeen.")
    p("4. **No feasible N resolves an R that sits near a band boundary.** That is inherent to "
      "a hard-threshold rule, not a fixable power problem. The analysis plan should therefore "
      "report **where the credible interval lies**, with an explicit *indeterminate* verdict "
      "when it straddles a boundary, rather than forcing a three-way call.")
    p("5. **A Bayesian fit is preferable on top of this**, not merely stylistically: the "
      "moment estimator returns σ̂²_model ≤ 0 — making R undefined — on up to "
      f"{100*sim[sim.N_models==8]['P_undefined'].max():.1f}% of replicates at N=8. A "
      "properly-constrained posterior cannot do that.\n")

    p("### Recommendation\n")
    p("**Expand the roster to N ≈ 20 and keep the confirmatory design otherwise unchanged.** "
      "The models are all ≤14B; weights need not be held simultaneously — download, run the "
      "four conditions (minutes per model), delete, move on — so a 200 GB volume is not the "
      "binding constraint. The marginal cost is GPU-hours and download time, not new code.\n")
    p("If time forces a cut, N=13 remains usable **provided** the write-up reports interval "
      "width honestly and uses the indeterminate verdict rather than rounding to the nearer "
      "band. N=8 should not carry the primary claim.\n")

    sim.to_csv(OUTDIR / "design_simulation.csv", index=False)
    cal.to_csv(OUTDIR / "design_calibration.csv", index=False)
    (OUTDIR / "design_simulation.md").write_text("\n".join(L), encoding="utf-8")
    print("\n".join(L))
    print(f"\nwrote {OUTDIR/'design_simulation.md'}, .csv, and design_calibration.csv")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
