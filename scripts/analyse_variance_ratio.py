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
import hashlib
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

# Clifford (2015, p.9) designed the Social Norms items as a non-moral CONTROL stimulus set,
# not a seventh foundation. It is still FITTED -- its R is informative about the readouts --
# but every output row is labelled so it can never be averaged in as a foundation.
CONTROL_FOUNDATION = "Social Norms"

# Bands fixed in state.md, with the `indeterminate` verdict added after the B2 simulation
# showed that no feasible N resolves an R sitting on a boundary.
BANDS = [(0.0, 0.25, "robust"), (0.25, 1.0, "degraded"), (1.0, np.inf, "not interpretable")]


def stable_seed(tag: str) -> int:
    """Deterministic MCMC seed from a label.

    REPRODUCIBILITY BUG, fixed 2026-08-09. This was:

        seed=abs(hash(tag)) % 10000

    CPython randomises string hashing per process (PYTHONHASHSEED), so the same tag produced a
    different MCMC seed on every run. `results/derived/variance_ratio.csv` — a COMMITTED
    artifact — therefore could not be regenerated from `analysis_long.csv`. Every posterior
    summary in it (R_median, R_q2.5, R_q97.5, max_rhat) moves with the seed, and `verdict()`
    is a banded classification that can flip when an interval sits near the 0.25 or 1.0
    boundary, which per FINDINGS.md is the case for all seven foundations.

    This is the same defect as C10 in CORRECTIONS.md, but worse: C10 touched a descriptive
    column, this one seeds the primary estimand. It was found by auditing for siblings of C10
    rather than by anything noticing on its own.

    sha256 is deterministic across processes, machines and Python versions, and is already the
    hashing used elsewhere in the tree (conditions.py). The magnitude of what the old code
    cost is measured separately by --seed-audit rather than assumed negligible.
    """
    return int(hashlib.sha256(tag.encode("utf-8")).hexdigest()[:8], 16) % 10000


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
            chains: int, seed: int, family_effect: bool = False):
    """Fit the variance-components model.

    `family_effect` adds `(1|family)`, which addresses F3: the roster contains **eight Qwen
    models, four Llama, four Phi, three OLMo, three Gemma and three Mistral**. Treating those
    as independent draws overstates the effective sample size, because models within a family
    share pretraining data, tokenizer and post-training recipe. Adding the term partials that
    shared variance out of `(1|model)`, which is the DENOMINATOR of R -- so it should widen the
    intervals, and possibly raise R. Reported as a sensitivity, not as the primary: with only
    12 families and several singletons, the family variance is itself weakly identified.
    """
    base = "score ~ 0 + method + (1|model) + (1|model:method) + (1|item)"
    if family_effect:
        base += " + (1|family)"
    if heteroscedastic:
        formula = bmb.Formula(base, "sigma ~ 0 + method")
    else:
        formula = bmb.Formula(base)
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


def seed_audit(df: pd.DataFrame, foundations: list[str], args) -> int:
    """Refit each foundation under N explicit seeds; report Monte-Carlo sensitivity.

    This exists to MEASURE what the old randomised-hash seed could have cost, rather than
    asserting it was negligible. The question that matters is not "did the seed change" — it
    demonstrably did — but "does the seed change anything a reader would act on". Two things
    are therefore reported per foundation: the spread of R_median across seeds, and whether
    `verdict` is constant. A verdict that flips means the banded classification is unstable at
    this draw count, which would be a finding about the analysis rather than about the models.

    Uses the primary specification only (exclusions applied, method-specific residuals), since
    that is the configuration the headline numbers come from.
    """
    rows = []
    for fdn in foundations:
        sub = df[(df["foundation"] == fdn) & (~df["excluded"])]
        sub = sub.rename(columns={"condition": "method", "item_id": "item"})
        sub = sub[["score", "model", "method", "item"]].dropna()
        sub["item"] = sub["item"].astype(str)
        if sub["method"].nunique() < 2 or sub["model"].nunique() < 3:
            continue
        for i in range(args.seed_audit):
            seed = 1000 + i * 7919          # arbitrary but explicit and reproducible
            try:
                _, idata = fit_one(sub, True, args.draws, args.tune, args.chains, seed=seed)
            except Exception as e:
                print(f"  {fdn} seed {seed}: FAILED {type(e).__name__}")
                continue
            R = extract_R(idata)
            if R is None:
                continue
            lo, hi = np.percentile(R, [2.5, 97.5])
            rows.append({"foundation": fdn, "seed": seed,
                         "R_median": float(np.median(R)), "R_q2.5": float(lo),
                         "R_q97.5": float(hi), "verdict": verdict(lo, hi)})
            print(f"  {fdn:<14} seed={seed:<6} R={np.median(R):.4f} "
                  f"[{lo:.4f}, {hi:.4f}] {verdict(lo, hi)}")

    res = pd.DataFrame(rows)
    OUT.mkdir(parents=True, exist_ok=True)
    # Suffix follows the input, same rule as the primary path (see C12).
    _sfx = "_v2" if "_v2" in Path(args.data).name else ""
    out_path = Path(args.out) if args.out else OUT / f"variance_ratio_seed_audit{_sfx}.csv"
    res.to_csv(out_path, index=False)

    print()
    print(f"{'foundation':<14}{'n':>3}{'R median':>11}{'spread':>10}"
          f"{'as % of CrI':>13}  verdicts")
    unstable = []
    for fdn, g in res.groupby("foundation"):
        spread = g["R_median"].max() - g["R_median"].min()
        cri = g["R_q97.5"].mean() - g["R_q2.5"].mean()
        vs = set(g["verdict"])
        if len(vs) > 1:
            unstable.append(fdn)
        print(f"{fdn:<14}{len(g):>3}{g['R_median'].median():>11.4f}{spread:>10.4f}"
              f"{100 * spread / cri if cri else float('nan'):>12.1f}%  "
              f"{'STABLE' if len(vs) == 1 else 'FLIPS: ' + '/'.join(sorted(vs))}")
    print()
    if unstable:
        print(f"!! verdict FLIPS across seeds for: {', '.join(unstable)}")
        print("   The banded classification is not stable at this draw count. Raise draws and")
        print("   report the instability -- do not pick a seed.")
    else:
        print("All verdicts stable across seeds. Monte-Carlo error moves R_median by the")
        print("spread shown, which is the figure to report alongside the R table.")
    print()
    print(f"wrote {out_path}")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", default=None,
                    help="long-form dataset (default: results/derived/analysis_long.csv). "
                         "Pass analysis_long_v2.csv for the v2 harness.")
    ap.add_argument("--out", default=None, help="output CSV (default derived from --data)")
    ap.add_argument("--seed-audit", type=int, default=0, metavar="N",
                    help="refit every foundation under N different explicit seeds and write a "
                         "Monte-Carlo sensitivity table instead of the primary analysis. This "
                         "measures what the old randomised-hash seed could have cost; see "
                         "stable_seed().")
    ap.add_argument("--test", action="store_true", help="one foundation, short chains")
    ap.add_argument("--exclude-scan", action="store_true",
                    help="drop rows whose digit was recovered by scanning prose "
                         "(parse_strategy == 'scan'). This is the sensitivity analysis "
                         "ANALYSIS_PLAN.md:192 pre-specified and that was never run "
                         "(LIMITATIONS.md 1). Affects the free-generation arms only.")
    ap.add_argument("--family-effect", action="store_true",
                    help="add (1|family) to the model. Eight Qwens are not eight independent "
                         "draws; see fit_one(). Sensitivity, not primary.")
    ap.add_argument("--draws", type=int, default=1500)
    ap.add_argument("--tune", type=int, default=1500)
    ap.add_argument("--chains", type=int, default=4)
    args = ap.parse_args()
    if args.test:
        args.draws, args.tune, args.chains = 400, 400, 2

    data_path = Path(args.data) if args.data else LONG
    df = pd.read_csv(data_path)
    df = df[df["score"].notna()].copy()
    df["excluded"] = df["excluded"].astype(str) == "True"

    if args.exclude_scan:
        before = len(df)
        df = df[df["parse_strategy"].astype(str) != "scan"].copy()
        print(f"--exclude-scan: dropped {before - len(df)} of {before} rows "
              f"({(before - len(df)) / before:.1%}) whose digit came from prose")
    if args.family_effect and "family" not in df.columns:
        print("--family-effect requested but the dataset has no `family` column")
        return 1

    foundations = sorted(df["foundation"].unique())
    if args.test:
        foundations = ["Care"]

    if args.seed_audit:
        return seed_audit(df, foundations, args)

    rows = []
    for fdn in foundations:
        for use_exclusions in (True, False):
            sub = df[df["foundation"] == fdn]
            if use_exclusions:
                sub = sub[~sub["excluded"]]
            sub = sub.rename(columns={"condition": "method", "item_id": "item"})
            cols = ["score", "model", "method", "item"]
            if args.family_effect:
                cols.append("family")
            sub = sub[cols].dropna()
            sub["item"] = sub["item"].astype(str)
            if sub["method"].nunique() < 2 or sub["model"].nunique() < 3:
                print(f"  {fdn} (excl={use_exclusions}): too little data, skipped")
                continue

            for hetero in (True, False):
                # The tag seeds the chain, so it MUST distinguish every variant -- otherwise
                # the scan-excluded and family-effect fits would silently reuse the primary
                # fit's seed and their differences would be partly seed artifacts.
                tag = (f"{fdn} | excl={'yes' if use_exclusions else 'no '} | "
                       f"resid={'method-specific' if hetero else 'pooled       '}"
                       f"{' | noscan' if args.exclude_scan else ''}"
                       f"{' | family' if args.family_effect else ''}")
                try:
                    _, idata = fit_one(sub, hetero, args.draws, args.tune,
                                       args.chains, seed=stable_seed(tag),
                                       family_effect=args.family_effect)
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
                    "foundation": fdn,
                    # Social Norms is Clifford's designed NON-MORAL CONTROL, not a seventh
                    # foundation. Carried as a column so no downstream consumer can average it
                    # into a foundation-level statistic by accident -- which is exactly what
                    # happened to the rank correlations before 2026-08-10.
                    "is_control": fdn == CONTROL_FOUNDATION,
                    "exclusions": use_exclusions,
                    "scan_excluded": args.exclude_scan,
                    "family_effect": args.family_effect,
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

    # The output name follows the INPUT. Without this, `--data analysis_long_v2.csv` wrote its
    # 31-model results over the committed 20-model `variance_ratio.csv` — which is exactly
    # what happened on the pod on 2026-08-09 before this was fixed. The v1 file is a committed
    # artifact backing FINDINGS.md; silently replacing its contents with a different sample
    # while keeping its name is the worst kind of data loss, because nothing looks wrong.
    # The VARIANT must be in the name too, for the same reason. Four fits are run in one pod
    # session (primary, scan-excluded, family-effect, and combinations); if they all resolved
    # to `variance_ratio_v2.csv` the last one would win silently and the sensitivity analyses
    # would vanish while appearing to have run.
    if args.out:
        out_path = Path(args.out)
    else:
        stem = "variance_ratio_test" if args.test else "variance_ratio"
        sfx = "_v2" if "_v2" in data_path.name else ""
        variant = ("_noscan" if args.exclude_scan else "") + \
                  ("_family" if args.family_effect else "")
        out_path = OUT / f"{stem}{sfx}{variant}.csv"
    res.to_csv(out_path, index=False)
    print()
    print(f"wrote {out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
