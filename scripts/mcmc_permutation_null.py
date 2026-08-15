"""F9 — the permutation null, refit with the FULL Bayesian model the analysis plan specified.

    python scripts/mcmc_permutation_null.py --test              # 1 foundation, 4 perms
    python scripts/mcmc_permutation_null.py --n-perm 100 --workers 40

WHY THIS EXISTS. `docs/ANALYSIS_PLAN.md` specified that the permutation null use the same Bayesian
model as the primary analysis. What actually ran (`analyse_controls.py`) used a cheap moment
estimator instead, because 100 permutations x 7 foundations = 700 MCMC fits was estimated at
~12 h on the hardware then available. That shortcut is currently disclosed in the write-up as
a deviation from the plan. Running the real thing DELETES that deviation — it is the whole
point of F9, which is low-severity and exists because David asked for it rather than because
anything is broken.

WHAT A PERMUTATION NULL IS FOR, since it is easy to mistake for an inferential quantity.
Shuffling the method labels within each model x item cell destroys any genuine model x method
interaction while leaving the model main effects and item effects untouched. So the null
answers: *what R does this pipeline report when, by construction, there is no interaction to
find?* If that comes back near zero, the estimator is calibrated. If it comes back large, R is
an artifact of the model or the estimator and every headline number is worthless. It is a
CALIBRATION CHECK on the machinery, not a p-value for the science.

The moment-estimator null already run becomes the cross-check: two independent estimators
agreeing that the null collapses is stronger than either alone.

PARALLELISM, and the trap in it. Each fit gets `cores=1` so PyMC runs its chains sequentially
INSIDE the worker process, and parallelism comes from many workers instead. The obvious
alternative — a pool of workers that each spawn PyMC's own multiprocessing — nests two process
pools and reliably deadlocks or oversubscribes. BLAS threads are pinned to 1 for the same
reason: 40 workers x 16 implicit BLAS threads would thrash a machine into uselessness.

Results are appended to CSV after every fit, so an interrupted run keeps its work and can be
resumed by rerunning with the same seed.
"""

from __future__ import annotations

import argparse
import os

# MUST precede numpy/pytensor import: BLAS reads these at load time, not at call time.
for _v in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS",
           "NUMEXPR_NUM_THREADS", "VECLIB_MAXIMUM_THREADS"):
    os.environ.setdefault(_v, "1")

import sys  # noqa: E402
import time  # noqa: E402
from concurrent.futures import ProcessPoolExecutor, as_completed  # noqa: E402
from pathlib import Path  # noqa: E402

import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

REPO = Path(__file__).resolve().parent.parent
DERIVED = REPO / "results" / "derived"


def permute_methods(sub: pd.DataFrame, rng: np.random.Generator) -> pd.DataFrame:
    """Shuffle method labels WITHIN each model x item cell.

    This is the exact null the analysis plan names. Permuting within the cell is what makes it
    the right null: it holds the model's overall severity and the item's difficulty fixed, and
    breaks only the association between a method and a particular model's score. Permuting
    globally would also destroy the model and item main effects and would test a far weaker,
    less interesting hypothesis.
    """
    out = sub.copy()
    methods = out["method"].to_numpy()
    for _, idx in out.groupby(["model", "item"], sort=False).indices.items():
        if len(idx) > 1:
            methods[idx] = rng.permutation(methods[idx])
    out["method"] = methods
    return out


def _fit_and_extract(args_tuple):
    """One permutation -> one R median. Runs in a worker process."""
    (records, columns, hetero, draws, tune, chains, seed, perm_id, fdn) = args_tuple
    try:
        import bambi as bmb

        sys.path.insert(0, str(Path(__file__).resolve().parent))
        from analyse_variance_ratio import extract_R

        sub = pd.DataFrame.from_records(records, columns=columns)
        rng = np.random.default_rng(seed)
        perm = permute_methods(sub, rng)

        if hetero:
            formula = bmb.Formula(
                "score ~ 0 + method + (1|model) + (1|model:method) + (1|item)",
                "sigma ~ 0 + method")
        else:
            formula = bmb.Formula(
                "score ~ 0 + method + (1|model) + (1|model:method) + (1|item)")
        model = bmb.Model(formula, perm)
        idata = model.fit(draws=draws, tune=tune, chains=chains,
                          cores=1,               # see module docstring: no nested pools
                          random_seed=seed, progressbar=False,
                          target_accept=0.95,
                          idata_kwargs={"log_likelihood": False})
        R = extract_R(idata)
        if R is None:
            return {"foundation": fdn, "perm": perm_id, "status": "no_R"}
        return {"foundation": fdn, "perm": perm_id, "status": "ok",
                "R_median": float(np.median(R)),
                "R_q2.5": float(np.percentile(R, 2.5)),
                "R_q97.5": float(np.percentile(R, 97.5))}
    except Exception as exc:                                  # noqa: BLE001
        return {"foundation": fdn, "perm": perm_id, "status": "error",
                "error": f"{type(exc).__name__}: {str(exc)[:200]}"}


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--data", default=str(DERIVED / "analysis_long_v2.csv"),
                    help="long-form analysis file (default: the v1 Phase-1 dataset)")
    ap.add_argument("--out", default=None)
    ap.add_argument("--n-perm", type=int, default=100, help="permutations per foundation")
    ap.add_argument("--workers", type=int, default=0, help="0 = auto (cpus//2, capped)")
    ap.add_argument("--draws", type=int, default=1000)
    ap.add_argument("--tune", type=int, default=1000)
    ap.add_argument("--chains", type=int, default=4)
    ap.add_argument("--seed", type=int, default=20260809)
    ap.add_argument("--include-cloze", action="store_true",
                    help="INCLUDE the cloze arm. Off by default, and the default is the "
                         "design: cloze is scored against a DIFFERENT PROMPT, so a "
                         "method-effect estimate containing it is confounded with prompt. "
                         "Mirrors analyse_variance_ratio.py. See C15/C17.")
    ap.add_argument("--pooled-residual", action="store_true",
                    help="use the pooled-residual model instead of method-specific")
    ap.add_argument("--test", action="store_true", help="1 foundation, 4 perms, short chains")
    args = ap.parse_args()

    hetero = not args.pooled_residual
    if args.test:
        args.n_perm, args.draws, args.tune, args.chains = 4, 300, 300, 2

    df = pd.read_csv(args.data)
    df = df[df["score"].notna()].copy()
    if "excluded" in df:
        df["excluded"] = df["excluded"].astype(str) == "True"
        df = df[~df["excluded"]]

    # ---- CLOZE IS NOT A FIXED-PROMPT CONDITION (C15, and C17 for this file) -------------
    # This filter was added on 2026-08-15, months after the same fix landed in
    # analyse_variance_ratio.py. The committed `mcmc_permutation_null_v2.csv` therefore has a
    # SIX-ARM basket while the published R has five, and the mismatch is disclosed in
    # docs/FINDINGS.md 2 rather than papered over: refitting 700 MCMC fits costs pod time and
    # would move nothing, because a null collapses to ~0 under any basket.
    #
    # It is fixed anyway, because the C15 lesson was NOT "we forgot about cloze" -- it was that
    # a design commitment living only in prose has nothing enforcing it. Leaving the one
    # remaining unenforced copy in place would repeat the error knowingly.
    if not args.include_cloze:
        before = len(df)
        df = df[df["condition"].astype(str) != "cloze"].copy()
        print(f"cloze EXCLUDED from the null (the design; see C15): dropped "
              f"{before - len(df)} of {before} rows. Pass --include-cloze to override.")

    df = df.rename(columns={"condition": "method", "item_id": "item"})
    df["item"] = df["item"].astype(str)

    foundations = sorted(df["foundation"].unique())
    if args.test:
        foundations = foundations[:1]

    n_cpu = os.cpu_count() or 4
    workers = args.workers or max(1, min(n_cpu // 2, 64))

    # Suffix follows the input dataset, so the artifact declares its own provenance.
    # An unsuffixed name means the v1 harness by convention; leaving a v2-derived file
    # unsuffixed asserts something false about it. See docs/CORRECTIONS.md C12.
    # The VARIANT must be in the name too, for the C12 reason: a --include-cloze run must not
    # silently overwrite the design-conformant null with a confounded one.
    _sfx = "_v2" if "_v2" in Path(args.data).name else ""
    _var = "_withcloze" if args.include_cloze else ""
    out_path = Path(args.out) if args.out else DERIVED / (
        f"mcmc_null_test{_sfx}{_var}.csv" if args.test
        else f"mcmc_permutation_null{_sfx}{_var}.csv")
    out_path.parent.mkdir(parents=True, exist_ok=True)

    print(f"data      : {args.data}")
    print(f"model     : {'method-specific' if hetero else 'pooled'} residual")
    print(f"foundations {len(foundations)} x {args.n_perm} perms = "
          f"{len(foundations) * args.n_perm} MCMC fits")
    print(f"chains    : {args.chains} x {args.draws} draws ({args.tune} tune), cores=1 per fit")
    print(f"workers   : {workers} of {n_cpu} vCPU")
    print(f"out       : {out_path}\n")

    jobs = []
    for fi, fdn in enumerate(foundations):
        sub = df[df["foundation"] == fdn][["score", "model", "method", "item"]].dropna()
        if sub["method"].nunique() < 2 or sub["model"].nunique() < 3:
            print(f"  {fdn}: too little data, skipped")
            continue
        recs = sub.to_records(index=False).tolist()
        cols = list(sub.columns)
        for p in range(args.n_perm):
            jobs.append((recs, cols, hetero, args.draws, args.tune, args.chains,
                         args.seed + fi * 10000 + p, p, fdn))

    print(f"submitting {len(jobs)} fits\n")
    t0 = time.time()
    done = 0
    results: list[dict] = []
    with ProcessPoolExecutor(max_workers=workers) as ex:
        futs = {ex.submit(_fit_and_extract, j): j[-1] for j in jobs}
        for fut in as_completed(futs):
            r = fut.result()
            results.append(r)
            done += 1
            # Append after every fit: a 700-fit run that dies at fit 690 must not lose 689.
            #
            # SORT BEFORE WRITING. `as_completed` yields in process-completion order, which
            # depends on scheduling and on `workers` (derived from os.cpu_count()), so the same
            # run on the same data would emit rows in a different order on a different host.
            # The VALUES are safe -- every job carries an explicit derived seed -- but an
            # unsorted CSV is not a reproducible artifact, which is the same class of defect as
            # C10/C11 in docs/CORRECTIONS.md.
            pd.DataFrame(results).sort_values(["foundation", "perm"]).to_csv(
                out_path, index=False)
            if done % 10 == 0 or done == len(jobs):
                el = time.time() - t0
                rate = done / el if el else 0
                eta = (len(jobs) - done) / rate / 60 if rate else float("nan")
                ok = sum(1 for x in results if x.get("status") == "ok")
                print(f"  {done}/{len(jobs)}  ok={ok}  {el/60:.1f} min elapsed, "
                      f"~{eta:.0f} min left")

    res = pd.DataFrame(results).sort_values(['foundation', 'perm']).reset_index(drop=True)
    ok = res[res["status"] == "ok"] if "status" in res else res
    print(f"\n{len(ok)}/{len(res)} fits succeeded in {(time.time()-t0)/60:.1f} min")
    if len(ok):
        print(f"\n{'foundation':<14}{'n':>4}{'null median R':>15}{'null 95%':>22}")
        for fdn, g in ok.groupby("foundation"):
            lo, hi = np.percentile(g["R_median"], [2.5, 97.5])
            print(f"{fdn:<14}{len(g):>4}{np.median(g['R_median']):>15.4f}"
                  f"   [{lo:.4f}, {hi:.4f}]")
        print("\nA null median near 0 means the estimator is calibrated: with the interaction")
        print("destroyed by construction, the pipeline correctly reports no interaction.")
        print("A large null median would mean R is an artifact and every headline is void.")
    bad = res[res["status"] != "ok"] if "status" in res else res.iloc[:0]
    if len(bad):
        print(f"\n{len(bad)} non-ok fits — first few:")
        for _, r in bad.head(3).iterrows():
            print(f"  {r.get('foundation')} perm {r.get('perm')}: "
                  f"{r.get('status')} {str(r.get('error'))[:120]}")
    print(f"\nwrote {out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
