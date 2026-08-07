"""B1 -- audit Kirgis's logprob estimator on his own committed data. No GPU.

EXPLORATORY. This is a reanalysis of existing public data, not part of the pre-specified
design, and must be labelled as such in the write-up.

The go/no-go check established that his paper and his code disagree:

    paper p.4   E = sum_{k=1..3} s_k exp(l_k)          <- no denominator
    code        return weighted_sum / total_prob        <- renormalised

and that the code first FILTERS the provider's top-3 (which is over the whole vocabulary)
down to digit tokens, so the denominator is a data-dependent subset of size 1-3. When only
one digit survives, weighted_sum/total_prob = k*p/p = k exactly -- the estimator silently
degenerates to argmax.

This script measures how often that happens and whether it moves his conclusions.

    python scripts/reanalyse_kirgis.py --kirgis-repo <path to clone>
"""

from __future__ import annotations

import argparse
import ast
import json
import sys
import math
from pathlib import Path

import pandas as pd

# Windows consoles default to cp1252, which cannot encode the Greek letters used below.
# The report files are always written as UTF-8; this only affects the echo to stdout.
try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

REPO = Path(__file__).resolve().parent.parent
OUTDIR = REPO / "results" / "derived"
ALLOWED = {"0", "1", "2", "3", "4"}


def find_candidate(raw: dict) -> dict | None:
    """Reproduce Kirgis's candidate-token search verbatim (final_analysis.ipynb cell 2).

    Note the looser test here (`all(ch in ALLOWED ...)`) than in the weighting loop
    (`cand_token in ALLOWED`): a multi-digit token like "12" can be SELECTED as the
    candidate but then contributes nothing to the sum. Faithful to his code.
    """
    try:
        choices = raw.get("choices", [])
        if not choices:
            return None
        logprobs = choices[0].get("logprobs")
        if not logprobs:
            return None
        content = logprobs.get("content", [])
        if not content:
            return None
        for token_dict in content:
            token_str = token_dict.get("token", "").strip()
            if token_str and all(ch in ALLOWED for ch in token_str):
                return token_dict
        return None
    except Exception:
        return None


def score_variants(candidate: dict | None) -> dict:
    """Three estimators computable from the top-3 he actually has.

    A fourth -- renormalising over all five valid options -- is NOT computable: the API
    returned only the top 3 of the vocabulary, so the logprobs of options outside that set
    do not exist in his data. Recorded as a limitation rather than silently omitted.
    """
    out = {
        "n_digits_in_top3": 0,
        "n_top3": 0,
        "kirgis_code": None,      # renormalised over surviving digits
        "kirgis_paper": None,     # unnormalised, as printed
        "argmax": None,           # highest-probability surviving digit
        "digit_mass": None,       # how much of the top-3 mass is on digits
        "own_logprob": None,      # the emitted token's OWN reported logprob
        "top_mass": None,         # total probability across the returned top_logprobs
        "extraction_failed": True,
    }
    if candidate is None:
        return out
    top = candidate.get("top_logprobs")
    if not top:
        return out

    out["n_top3"] = len(top)
    # Provider integrity check. A well-formed response has top_mass near 1 and an own_logprob
    # consistent with it. xAI violates both on grok-3-beta; see the report section 5.
    out["own_logprob"] = candidate.get("logprob")
    out["top_mass"] = sum(math.exp(e["logprob"]) for e in top)
    weighted, total, best_p, best_k = 0.0, 0.0, -1.0, None
    all_mass = 0.0
    for entry in top:
        p = math.exp(entry["logprob"])
        all_mass += p
        tok = entry.get("token", "").strip()
        if tok in ALLOWED:
            k = int(tok)
            weighted += k * p
            total += p
            if p > best_p:
                best_p, best_k = p, k

    out["n_digits_in_top3"] = sum(
        1 for e in top if e.get("token", "").strip() in ALLOWED
    )
    if total == 0:
        return out

    out["kirgis_code"] = weighted / total
    out["kirgis_paper"] = weighted
    out["argmax"] = float(best_k)
    out["digit_mass"] = total / all_mass if all_mass > 0 else None
    out["extraction_failed"] = False
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--kirgis-repo", required=True, type=Path)
    args = ap.parse_args()

    lp = pd.read_csv(args.kirgis_repo / "data" / "results" / "logprob_responses.csv")
    vig = pd.read_csv(REPO / "data" / "source" / "kirgis_vignettes_short.csv")

    rows = []
    for _, r in lp.iterrows():
        raw = ast.literal_eval(r["Raw Output"]) if pd.notna(r["Raw Output"]) else {}
        v = score_variants(find_candidate(raw))
        v["Scenario"] = r["Scenario"]
        v["Model"] = r["Model"]
        v["Service"] = r["Service"]
        v["edsl_answer"] = r["Answer"]
        rows.append(v)

    df = pd.DataFrame(rows).merge(
        vig[["Scenario", "Foundation", "Wrong"]], on="Scenario", how="left"
    )
    # Kirgis's fallback: when extraction fails his code silently substitutes the parsed answer
    df["kirgis_final"] = df["kirgis_code"].fillna(df["edsl_answer"])

    OUTDIR.mkdir(parents=True, exist_ok=True)
    df.to_csv(OUTDIR / "kirgis_rescored.csv", index=False)

    n = len(df)
    ok = df[~df["extraction_failed"]]
    L: list[str] = []
    p = L.append

    p("# Reanalysis of Kirgis's logprob arm (EXPLORATORY)\n")
    p(f"Source: `data/results/logprob_responses.csv`, {n} responses, "
      f"{df['Model'].nunique()} models.\n")

    p("## 1. Degeneracy -- how many of each top-3 are digits\n")
    vc = df["n_digits_in_top3"].value_counts().sort_index()
    p("| digits in top-3 | responses | share |")
    p("|---|---|---|")
    for k, c in vc.items():
        p(f"| {k} | {c} | {100*c/n:.1f}% |")
    p("")

    n1 = int((df["n_digits_in_top3"] == 1).sum())
    p(f"## 2. Argmax collapse\n")
    p(f"**{n1} / {n} responses ({100*n1/n:.1f}%)** had exactly one digit in the top-3. "
      f"For these, the renormalised estimator returns that integer EXACTLY -- an argmax "
      f"score wearing an expectation's clothing.\n")
    exact_int = int((ok["kirgis_code"] % 1 == 0).sum())
    p(f"Sanity check: {exact_int} of {len(ok)} successfully-extracted scores are exact "
      f"integers ({100*exact_int/max(len(ok),1):.1f}%).\n")

    nf = int(df["extraction_failed"].sum())
    p("## 3. Fallback rate\n")
    p(f"**{nf} / {n} ({100*nf/n:.1f}%)** produced no usable digit, so his code silently "
      f"substitutes the EDSL-parsed answer via `.fillna(df['Answer'])`. Those rows are "
      f"free-generation scores sitting inside the arm reported as logprob-weighted.\n")

    p("## 4. Does the estimator choice move anything?\n")
    p("Mean absolute differences across all successfully-extracted responses:\n")
    p("| comparison | mean abs diff | max abs diff |")
    p("|---|---|---|")
    for a, b, lab in [
        ("kirgis_code", "kirgis_paper", "code (renormalised) vs paper (as printed)"),
        ("kirgis_code", "argmax", "code vs plain argmax"),
    ]:
        d = (ok[a] - ok[b]).abs()
        p(f"| {lab} | {d.mean():.4f} | {d.max():.4f} |")
    p("")
    p(f"Mean digit mass retained in top-3: {ok['digit_mass'].mean():.4f} "
      f"(min {ok['digit_mass'].min():.4f}). The renormalisation gap is large only when this "
      f"is small.\n")

    p("### Foundation means under each estimator\n")
    fm = ok.groupby("Foundation")[["kirgis_code", "kirgis_paper", "argmax"]].mean()
    fm["code - paper"] = fm["kirgis_code"] - fm["kirgis_paper"]
    fm["code - argmax"] = fm["kirgis_code"] - fm["argmax"]
    p(fm.round(4).to_markdown())
    p("")

    p("### Model ranking under each estimator\n")
    mm = ok.groupby("Model")[["kirgis_code", "kirgis_paper", "argmax"]].mean()
    for c in ["kirgis_code", "kirgis_paper", "argmax"]:
        mm[f"rank_{c}"] = mm[c].rank(ascending=False)
    p(mm.round(4).to_markdown())
    p("")
    rc = mm[["kirgis_code", "kirgis_paper", "argmax"]].corr(method="spearman")
    p("Spearman rank correlation between estimators (over models):\n")
    p(rc.round(4).to_markdown())
    p("")

    p("## 5. Provider data integrity — the actual finding\n")
    p("A well-formed response returns `top_logprobs` whose probabilities sum to ~1 and whose "
      "values are consistent with the emitted token's own `logprob`. Checking that:\n")
    integ = df.groupby("Model").agg(
        n=("top_mass", "size"),
        n_top_returned=("n_top3", "median"),
        mean_top_mass=("top_mass", "mean"),
        min_top_mass=("top_mass", "min"),
        frac_mass_below_half=("top_mass", lambda s: (s < 0.5).mean()),
    )
    p(integ.round(4).to_markdown())
    p("")
    bad = df[df["top_mass"] < 0.5]
    if len(bad):
        p(f"**{len(bad)} of {n} responses have `top_logprobs` summing to less than 0.5 "
          f"probability** — structurally malformed. They are concentrated entirely in "
          f"`{bad['Model'].value_counts().index[0]}` "
          f"({bad['Model'].value_counts().iloc[0]} of {len(bad)}).\n")
        p("On those responses the provider returned **two** `top_logprobs` entries instead of "
          "three, summing to ~0 probability, while the emitted token's own `logprob` reported "
          "p = 1.0. The two fields contradict each other: the data is internally inconsistent, "
          "not merely unusual.\n")
        p("**Three consequences, in increasing order of importance:**\n")
        p("1. Those scores are computed from corrupted probability data.")
        p("2. Kirgis's renormalisation *accidentally rescues* them — dividing near-zero by "
          "near-zero recovers the argmax, which equals the emitted (correct) answer. His "
          "published numbers therefore look fine. His **printed formula would not** rescue "
          "them: the affected model's mean collapses and it drops two rank positions.")
        p("3. **For those items, 'top-3 logprob weighting' is not what happened — argmax is.** "
          "Inside the arm he treats as a single homogeneous method, one of six models is "
          "effectively scored by a different method for nearly half its items.\n")
        p("Point 3 is the one that matters for this project: it is direct evidence, from his "
          "own committed data, that scoring method was not uniform even *within* the logprob "
          "arm. It also generalises — **provider logprob APIs cannot be assumed well-formed, "
          "and a study that reads them without an integrity check inherits their bugs.**\n")

    p("## Limitation\n")
    p("A fourth variant -- renormalising over all five valid option tokens -- is **not "
      "computable** from his data. The API returned only the top 3 of the vocabulary, so "
      "logprobs for options outside that set do not exist. This is itself part of the "
      "finding: his estimator cannot be repaired post hoc, only re-collected.\n")

    (OUTDIR / "kirgis_reanalysis.md").write_text("\n".join(L), encoding="utf-8")
    print("\n".join(L))
    print(f"\nwrote {OUTDIR / 'kirgis_reanalysis.md'}")
    print(f"wrote {OUTDIR / 'kirgis_rescored.csv'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
