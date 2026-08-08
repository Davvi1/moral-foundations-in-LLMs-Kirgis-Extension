"""Evaluate the harness-v2 predictions P1'-P4 against v1. WRITTEN BEFORE ANY v2 DATA EXISTS.

    python scripts/compare_v1_v2.py

Reads  results/raw/<slug>.csv       (v1, harness column absent or "v1")
       results/raw/<slug>_v2.csv    (v2, written by  run_experiment.py --harness v2
                                     --cloze --suffix _v2)
Writes results/derived/v1_v2_comparison.md

THE POINT OF WRITING THIS FIRST. Every threshold below is arbitrary to some degree. An
arbitrary threshold fixed *before* the data is a weak but honest commitment; the same
threshold chosen *after* is not a commitment at all. Committing this file to git before the
v2 run is what makes the difference checkable rather than merely asserted — `git log` will
show this file predates every `*_v2.csv`.

Run it now, with no v2 data present: it prints the plan and exits 0. That output IS the
pre-specification.

Continuous values are reported alongside every verdict, so a reader who dislikes a threshold
can apply their own without re-running anything.
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.stats import spearmanr

REPO = Path(__file__).resolve().parent.parent
RAW = REPO / "results" / "raw"
OUT = REPO / "results" / "derived" / "v1_v2_comparison.md"

# ---------------------------------------------------------------------------------------
# Pre-committed thresholds. Fixed 2026-08-08, before any v2 row was collected.
# ---------------------------------------------------------------------------------------
MAJORITY = 0.50          # "a majority of models" in P1' and P4'
P2_MIN_GAIN = 0.20       # rho(label,line) must beat rho(label,bare) by at least this
P2_MIN_RHO = 0.60        # ...and clear this absolute level
MIN_PARSE_RATE = 0.50    # frozen Phase-1 exclusion rule, applied identically here

PROB_CONDITIONS = ("label", "string", "string_line", "string_bare", "cloze")


def short(mid: str) -> str:
    return mid.split("/")[-1]


def load(suffix: str) -> pd.DataFrame:
    """Load one harness's raw rows. Returns an empty frame if that harness has not run."""
    files = sorted(p for p in RAW.glob(f"*{suffix}.csv")
                   if (suffix != "" or not p.stem.endswith("_v2")))
    if not files:
        return pd.DataFrame()
    df = pd.concat([pd.read_csv(p) for p in files], ignore_index=True)
    df["model_short"] = df["model"].map(short)
    return df


def cell_means(df: pd.DataFrame) -> pd.DataFrame:
    """Mean score per model x condition, after the frozen exclusion rule.

    Applied identically to both harnesses. Any asymmetry here would show up as a v1-vs-v2
    difference that is really an analysis difference, which is the exact class of error this
    whole project is about.
    """
    if df.empty:
        return df
    d = df[~df["parse_failed"].astype(bool)] if "parse_failed" in df else df
    n_ok = d.groupby(["model_short", "condition"])["score"].count()
    n_all = df.groupby(["model_short", "condition"])["score"].count()
    keep = (n_ok / n_all) >= MIN_PARSE_RATE
    m = d.groupby(["model_short", "condition"])["score"].mean().rename("score")
    m = m[keep.reindex(m.index).fillna(False)]
    return m.reset_index()


def mass_by_model(df: pd.DataFrame, cond: str) -> pd.Series:
    d = df[(df["condition"] == cond) & df["logprob_mass"].notna()]
    return d.groupby("model_short")["logprob_mass"].mean()


def rho_between(means: pd.DataFrame, a: str, b: str) -> tuple[float, int]:
    """Spearman rho over models between two conditions' mean scores."""
    p = means.pivot(index="model_short", columns="condition", values="score")
    if a not in p or b not in p:
        return float("nan"), 0
    sub = p[[a, b]].dropna()
    if len(sub) < 4:
        return float("nan"), len(sub)
    return float(spearmanr(sub[a], sub[b]).statistic), len(sub)


def verdict(ok: bool | None) -> str:
    return {True: "**SUPPORTED**", False: "**FALSIFIED**", None: "not evaluable"}[ok]


def plan_text() -> list[str]:
    return [
        "| # | prediction (as amended) | statistic | supported if | falsified if |",
        "|---|---|---|---|---|",
        "| P1' | full option line recovers probability mass | mean `logprob_mass`, "
        "`string_line` vs `string_bare`, per model | line > bare for > 50% of models | "
        "line > bare for <= 50% |",
        "| P2 | the line probe recovers agreement with label | Spearman rho over models "
        "vs `label` | rho(line) - rho(bare) >= 0.20 **and** rho(line) >= 0.60 | otherwise |",
        "| P3 | exact p_k moves low-mass models most | Spearman rho between v1 label mass "
        "and abs(v2 - v1) label score change | rho < 0 | rho >= 0 |",
        "| P4' | cloze recovers mass over the bare phrase | mean `logprob_mass`, `cloze` vs "
        "`string_bare` | cloze > bare for > 50% of models | otherwise |",
        "| P4r | cloze behaves like cloze, not like label | rho(cloze, `string_bare`) vs "
        "rho(cloze, `label`) | rho(bare) > rho(label) | otherwise |",
        "",
        "P1' and P4' are **within-v2** contrasts: identical machinery on both sides, so the",
        "change of estimator cannot produce them. They replace the original P1/P4 mass tests,",
        "whose baseline was withdrawn — see `CORRECTIONS.md` C6/C8.",
    ]


def main() -> int:
    v1, v2 = load(""), load("_v2")
    L: list[str] = ["# Harness v1 vs v2: evaluating the registered predictions\n"]
    L.append("Generated by `scripts/compare_v1_v2.py`, which was committed **before any v2")
    L.append("data existed** — check `git log` on this file against the `*_v2.csv` files.\n")
    L.append("\n## Pre-specified evaluation plan\n")
    L += plan_text()

    if v2.empty:
        L.append("\n## Status\n")
        L.append("**No v2 data yet.** The plan above is the pre-specification; this file will")
        L.append("be regenerated with verdicts once `run_experiment.py --harness v2 --cloze")
        L.append("--suffix _v2` has run. Nothing below is filled in, deliberately.\n")
        OUT.parent.mkdir(parents=True, exist_ok=True)
        OUT.write_text("\n".join(L), encoding="utf-8")
        print(f"no v2 data found in {RAW} — wrote the pre-specification to "
              f"{OUT.relative_to(REPO)}")
        print(f"  v1 models present: {v1['model_short'].nunique() if not v1.empty else 0}")
        for line in plan_text()[:2] + plan_text()[2:7]:
            print("   ", line)
        return 0

    m1, m2 = cell_means(v1), cell_means(v2)
    models = sorted(set(m2["model_short"]))
    L.append(f"\n## Data\n\nv1 models: {m1['model_short'].nunique()} · "
             f"v2 models: {len(models)}\n")

    # ---- P1' ---------------------------------------------------------------------------
    line_m, bare_m = mass_by_model(v2, "string_line"), mass_by_model(v2, "string_bare")
    both = pd.concat([line_m.rename("line"), bare_m.rename("bare")], axis=1).dropna()
    p1_frac = float((both["line"] > both["bare"]).mean()) if len(both) else float("nan")
    p1_ok = None if not len(both) else bool(p1_frac > MAJORITY)
    L.append(f"\n## P1' — full option line vs bare phrase (mass)\n")
    L.append(f"`string_line` mass exceeds `string_bare` mass on "
             f"**{int((both['line'] > both['bare']).sum())}/{len(both)}** models "
             f"({p1_frac:.0%}). Means: line {both['line'].mean():.4f}, "
             f"bare {both['bare'].mean():.4f}.\n")
    L.append(f"Verdict: {verdict(p1_ok)}\n")

    # ---- P2 ----------------------------------------------------------------------------
    r_line, n_line = rho_between(m2, "label", "string_line")
    r_bare, n_bare = rho_between(m2, "label", "string_bare")
    gain = r_line - r_bare
    p2_ok = None if np.isnan(gain) else bool(gain >= P2_MIN_GAIN and r_line >= P2_MIN_RHO)
    L.append(f"\n## P2 — does the line probe recover agreement with label?\n")
    L.append(f"| pair | Spearman rho | n models |")
    L.append(f"|---|---:|---:|")
    L.append(f"| label ~ string_line | {r_line:.3f} | {n_line} |")
    L.append(f"| label ~ string_bare | {r_bare:.3f} | {n_bare} |")
    L.append(f"\nGain {gain:+.3f} against a pre-committed requirement of "
             f">= {P2_MIN_GAIN:.2f} with rho >= {P2_MIN_RHO:.2f}.\n")
    L.append(f"Verdict: {verdict(p2_ok)}\n")
    L.append("**Read this one carefully rather than as pass/fail.** If P2 is falsified while")
    L.append("P1' holds — mass recovered, agreement did not — then the Phase-1 rho = 0.332 was")
    L.append("a *genuine construct difference*, not a badly aimed probe. That is the more")
    L.append("interesting outcome and it strengthens the Phase-1 headline rather than")
    L.append("weakening it. It is registered precisely so it cannot be reframed afterwards.\n")

    # ---- P3 ----------------------------------------------------------------------------
    lab1 = m1[m1["condition"] == "label"].set_index("model_short")["score"]
    lab2 = m2[m2["condition"] == "label"].set_index("model_short")["score"]
    mass1 = mass_by_model(v1, "label")
    j = pd.concat([lab1.rename("v1"), lab2.rename("v2"), mass1.rename("mass")],
                  axis=1).dropna()
    p3_ok = None
    L.append(f"\n## P3 — does exact p_k move low-mass models most?\n")
    if len(j) >= 4:
        j["delta"] = (j["v2"] - j["v1"]).abs()
        r3 = float(spearmanr(j["mass"], j["delta"]).statistic)
        p3_ok = bool(r3 < 0)
        L.append(f"Spearman rho between v1 label retained mass and |v2 − v1| label score "
                 f"change: **{r3:+.3f}** (n = {len(j)}). Predicted negative.\n")
        worst = j.sort_values("delta", ascending=False).head(5)
        L.append("| model | v1 mass | v1 score | v2 score | abs change |")
        L.append("|---|---:|---:|---:|---:|")
        for mdl, r in worst.iterrows():
            L.append(f"| {mdl} | {r['mass']:.3f} | {r['v1']:.3f} | {r['v2']:.3f} | "
                     f"{r['delta']:.3f} |")
        L.append("")
    else:
        L.append("Too few models with both harnesses to evaluate.\n")
    L.append(f"Verdict: {verdict(p3_ok)}\n")

    # ---- P4 ----------------------------------------------------------------------------
    cl_m = mass_by_model(v2, "cloze")
    cb = pd.concat([cl_m.rename("cloze"), bare_m.rename("bare")], axis=1).dropna()
    p4_frac = float((cb["cloze"] > cb["bare"]).mean()) if len(cb) else float("nan")
    p4_ok = None if not len(cb) else bool(p4_frac > MAJORITY)
    r_cb, _ = rho_between(m2, "cloze", "string_bare")
    r_cl, _ = rho_between(m2, "cloze", "label")
    p4r_ok = None if (np.isnan(r_cb) or np.isnan(r_cl)) else bool(r_cb > r_cl)
    L.append(f"\n## P4' / P4r — the cloze arm\n")
    L.append(f"Mass: cloze > bare on **{int((cb['cloze'] > cb['bare']).sum())}/{len(cb)}** "
             f"models ({p4_frac:.0%}). Verdict: {verdict(p4_ok)}\n")
    L.append(f"Ranking: rho(cloze, string_bare) = **{r_cb:.3f}** vs "
             f"rho(cloze, label) = **{r_cl:.3f}**. Verdict: {verdict(p4r_ok)}\n")
    L.append("**Reminder that this arm is prompt-varying and excluded from the primary")
    L.append("variance ratio.** It also changes two things at once (options removed, and the")
    L.append("'five-point scale' clause removed with them), so it cannot separate")
    L.append("option-visibility from wording. Diagnostic only — see `config/prompt.yaml`.\n")

    # ---- boundary diagnostics ----------------------------------------------------------
    L.append("\n## Boundary and integrity diagnostics (v2)\n")
    if "boundary_shift" in v2:
        sh = v2[v2["boundary_shift"].fillna(0) > 0]["model_short"].nunique()
        dg = v2[v2["degenerate_options"].fillna("").astype(str) != ""]["model_short"].nunique()
        L.append(f"- models with a nonzero token-boundary shift: **{sh}**")
        L.append(f"- models with indistinguishable options: **{dg}** (any nonzero value here "
                 f"invalidates that model's arm and must be reported, not dropped)")
    prob2 = v2[v2["condition"].isin(PROB_CONDITIONS) & v2["logprob_mass"].notna()]
    if len(prob2):
        mx = float(prob2["logprob_mass"].max())
        L.append(f"- max retained mass: **{mx:.4f}** — must be <= 1.0, since the five options "
                 f"are mutually exclusive continuations of a shared prefix. A value above 1 "
                 f"means the option token sequences are not pairwise non-prefix and the "
                 f"scorer is double-counting.")
    L.append("")

    L.append("\n## Summary\n")
    L.append("| prediction | verdict |")
    L.append("|---|---|")
    for name, ok in (("P1' mass, line > bare", p1_ok), ("P2 ranking agreement", p2_ok),
                     ("P3 exact p_k moves low-mass models", p3_ok),
                     ("P4' mass, cloze > bare", p4_ok), ("P4r cloze ranks like bare", p4r_ok)):
        L.append(f"| {name} | {verdict(ok)} |")
    L.append("\nPredictions that failed are reported as failed. See `CORRECTIONS.md` for the")
    L.append("standing record of claims this project has had to withdraw.\n")

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text("\n".join(L), encoding="utf-8")
    print(f"wrote {OUT.relative_to(REPO)}")
    for name, ok in (("P1'", p1_ok), ("P2", p2_ok), ("P3", p3_ok),
                     ("P4'", p4_ok), ("P4r", p4r_ok)):
        print(f"  {name:<5} {verdict(ok)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
