"""Primary analysis — the variance ratio R, per foundation.

    score ~ 0 + method + (1|model) + (1|model:method) + (1|item)
    sigma ~ 0 + method                     # method-specific residual variance

    R_f = sigma2(model x method) / sigma2(model)

Every choice here comes from state.md and was fixed before any outcome model was fitted.
Nothing in this file decides anything.

METHOD-SPECIFIC RESIDUAL VARIANCES ARE MANDATORY, not optional. The four conditions have
structurally different error variance — label and string are deterministic expectations,
greedy is discretised to integers, sampled is a mean of k=10 and so carries Monte-Carlo error
of order 1/sqrt(k). A single pooled residual misattributes that difference into
sigma2(model x method) and inflates R mechanically, biasing toward the more publishable
answer. Both are fitted and both are reported.

Runs on Linux with a working C++ toolchain. It will not run usefully on a machine without
one — PyTensor falls back to pure Python and a small fit takes over ten minutes.

    python scripts/analyse_variance_ratio.py --test          # one foundation, quick
    python scripts/analyse_variance_ratio.py                 # full run
"""

from __future__ import annotations

import argparse
import json
import warnings
from pathlib import Path

warnings.filterwarnings("ignore")

import arviz as az  # noqa: E402
import bambi as bmb  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

REPO = Path(__file__).resolve().parent.parent
LONG = REPO / "results" / "derived" / "analysis_long.csv"
OUT = REPO / "results" / "derived"

# Bands fixed in state.md, with the `indeterminate` verdict added after the B2 simulation
# showed that no feasible N resolves an R sitting on a boundary.
BANDS = [(0.0, 0.25, "robust"), (0.25, 1.0, "degraded"), (1.0, np.inf, "not interpretable")]


def verdict(lo: float, hi: float) -> str:
    """Classify by where the whole 95% interval lies, not by the point estimate."""
    for a, b, name in BANDS:
        if lo >= a and hi < b:
            return name
    return "indeterminate"


def find_sd(idata, contains: str) -> str | None:
    """Locate a group-specific SD variable; bambi's naming varies by version."""
    for v in idata.posterior.data_vars:
        n = str(v)
        if contains in n and ("sigma" in n or n.endswith("_sd")):
            return n
    return None


def fit_one(df: pd.DataFrame, heteroscedastic: bool, draws: int, tune: int,
            chains: int, seed: int):
    if heteroscedastic:
        formula = bmb.Formula(
            "score ~ 0 + method + (1|model) + (1|model:method) + (1|item)",
            "sigma ~ 0 + method")
    else:
        formula = bmb.Formula(
            "score ~ 0 + method + (1|model) + (1|model:method) + (1|item)")
    model = bmb.Model(formula, df)
    idata = model.fit(draws=draws, tune=tune, chains=chains, cores=chains,
                      random_seed=seed, progressbar=False,
                      # 0.95 rather than the 0.8 default: variance components with few
                      # groups have a funnel geometry that produces divergences at 0.8.
                      target_accept=0.95,
                      idata_kwargs={"log_likelihood": False})
    return model, idata


def extract_R(idata) -> np.ndarray | None:
    v_m = find_sd(idata, "1|model") if find_sd(idata, "1|model") else None
    # the interaction term must not be confused with the plain model term
    cands = [str(v) for v in idata.posterior.data_vars
             if "model:method" in str(v) and ("sigma" in str(v) or str(v).endswith("_sd"))]
    v_mr = cands[0] if cands else None
    plain = [str(v) for v in idata.posterior.data_vars
             if "1|model" in str(v) and "method" not in str(v)
             and ("sigma" in str(v) or str(v).endswith("_sd"))]
    v_m = plain[0] if plain else None
    if not v_m or not v_mr:
        print(f"    !! could not locate SD vars. available: "
              f"{[str(v) for v in idata.posterior.data_vars]}")
        return None
    sd_m = idata.posterior[v_m].values.ravel()
    sd_mr = idata.posterior[v_mr].values.ravel()
    return (sd_mr ** 2) / (sd_m ** 2)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--test", action="store_true", help="one foundation, short chains")
    ap.add_argument("--draws", type=int, default=1500)
    ap.add_argument("--tune", type=int, default=1500)
    ap.add_argument("--chains", type=int, default=4)
    args = ap.parse_args()
    if args.test:
        args.draws, args.tune, args.chains = 400, 400, 2

    df = pd.read_csv(LONG)
    df = df[df["score"].notna()].copy()
    df["excluded"] = df["excluded"].astype(str) == "True"

    foundations = sorted(df["foundation"].unique())
    if args.test:
        foundations = ["Care"]

    rows = []
    for fdn in foundations:
        for use_exclusions in (True, False):
            sub = df[df["foundation"] == fdn]
            if use_exclusions:
                sub = sub[~sub["excluded"]]
            sub = sub.rename(columns={"condition": "method", "item_id": "item"})
            sub = sub[["score", "model", "method", "item"]].dropna()
            sub["item"] = sub["item"].astype(str)
            if sub["method"].nunique() < 2 or sub["model"].nunique() < 3:
                print(f"  {fdn} (excl={use_exclusions}): too little data, skipped")
                continue

            for hetero in (True, False):
                tag = (f"{fdn} | excl={'yes' if use_exclusions else 'no '} | "
                       f"resid={'method-specific' if hetero else 'pooled       '}")
                try:
                    _, idata = fit_one(sub, hetero, args.draws, args.tune,
                                       args.chains, seed=abs(hash(tag)) % 10000)
                except Exception as e:
                    print(f"  {tag}: FIT FAILED {type(e).__name__}: {str(e)[:120]}")
                    continue
                R = extract_R(idata)
                if R is None:
                    continue
                lo, hi = np.percentile(R, [2.5, 97.5])
                summ = az.summary(idata, var_names=["~1|"], filter_vars="like")
                max_rhat = float(np.nanmax(summ["r_hat"].values)) if len(summ) else np.nan
                rows.append({
                    "foundation": fdn, "exclusions": use_exclusions,
                    "residual": "method-specific" if hetero else "pooled",
                    "n_obs": len(sub), "n_models": sub["model"].nunique(),
                    "n_methods": sub["method"].nunique(),
                    "R_median": float(np.median(R)), "R_q2.5": float(lo),
                    "R_q97.5": float(hi), "verdict": verdict(lo, hi),
                    "max_rhat": max_rhat,
                })
                print(f"  {tag}: R={np.median(R):.3f} [{lo:.3f}, {hi:.3f}] "
                      f"{verdict(lo, hi):<18} rhat={max_rhat:.3f}  n={len(sub)}")

    res = pd.DataFrame(rows)
    OUT.mkdir(parents=True, exist_ok=True)
    res.to_csv(OUT / ("variance_ratio_test.csv" if args.test else "variance_ratio.csv"),
               index=False)
    print(f"\nwrote {OUT / ('variance_ratio_test.csv' if args.test else 'variance_ratio.csv')}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
