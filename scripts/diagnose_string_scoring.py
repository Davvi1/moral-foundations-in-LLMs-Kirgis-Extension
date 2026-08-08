"""Step 6 — decide what string scoring is actually measuring, BEFORE interpreting it.

Label and string diverge enormously on identical prompts (Qwen2.5-3B: 2.87 -> 0.54) with
retained probability mass often below 0.01. That is either the headline method effect or
evidence that string scoring is degenerate under a prompt that displays the options. The
variance ratio cannot be interpreted until we know which.

THE TEST. If string scoring measures the same construct on a shifted scale, then across the
116 items a model's string scores should rank the items much like its label scores do — high
severity items still rank high. If it measures something else, the item ranking falls apart.

Rank correlation is the right statistic because it is invariant to the level shift, which is
exactly the nuisance we want to look past.

Reference points, both computed here so the string number is judged against something:
  label vs greedy   two methods we expect to agree; the ceiling
  label vs sampled  same
  label vs string   the question

LIMITATION, recorded rather than hidden: the harness stored the EXPECTATION per item, not the
five per-option log-probabilities. The sharper test — do label and string order the five
options the same way within an item — is not computable from the saved data. Capturing
per-option scores would have cost nothing and should be added if the harness is ever re-run.

    python scripts/diagnose_string_scoring.py
"""

from __future__ import annotations

import csv
import math
from collections import defaultdict
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
LONG = REPO / "results" / "derived" / "analysis_long.csv"
OUT = REPO / "results" / "derived" / "string_scoring_diagnosis.md"


def spearman(xs, ys):
    """Rank correlation, average ranks for ties. No scipy dependency."""
    n = len(xs)
    if n < 3:
        return float("nan")

    def rank(v):
        order = sorted(range(len(v)), key=lambda i: v[i])
        r = [0.0] * len(v)
        i = 0
        while i < len(order):
            j = i
            while j + 1 < len(order) and v[order[j + 1]] == v[order[i]]:
                j += 1
            avg = (i + j) / 2 + 1
            for k in range(i, j + 1):
                r[order[k]] = avg
            i = j + 1
        return r

    rx, ry = rank(xs), rank(ys)
    mx, my = sum(rx) / n, sum(ry) / n
    num = sum((a - mx) * (b - my) for a, b in zip(rx, ry))
    den = math.sqrt(sum((a - mx) ** 2 for a in rx) * sum((b - my) ** 2 for b in ry))
    return num / den if den else float("nan")


def main() -> int:
    rows = list(csv.DictReader(LONG.open(encoding="utf-8")))
    by_model: dict[str, dict[str, dict[int, float]]] = defaultdict(lambda: defaultdict(dict))
    mass: dict[str, dict[str, list[float]]] = defaultdict(lambda: defaultdict(list))
    for r in rows:
        if r["excluded"] == "True" or r["score"] == "":
            continue
        by_model[r["model"]][r["condition"]][int(r["item_id"])] = float(r["score"])
        if r["logprob_mass"] not in ("", "nan"):
            try:
                mass[r["model"]][r["condition"]].append(float(r["logprob_mass"]))
            except ValueError:
                pass

    L: list[str] = []
    p = L.append
    p("# Step 6 — what is string scoring measuring?\n")
    p("Rank correlation across the 116 items, within each model. Rank correlation is used "
      "because it is invariant to the level shift, which is the nuisance we want to see past. "
      "`label~greedy` and `label~sampled` are reference points: methods we expect to agree.\n")
    p("| model | label~string | label~greedy | label~sampled | mean string mass | mean label mass |")
    p("|---|---|---|---|---|---|")

    rho_string, rho_greedy = [], []
    for m in sorted(by_model):
        c = by_model[m]
        def rho(a, b):
            common = sorted(set(c.get(a, {})) & set(c.get(b, {})))
            if len(common) < 10:
                return float("nan")
            return spearman([c[a][i] for i in common], [c[b][i] for i in common])
        rs, rg, rsa = rho("label", "string"), rho("label", "greedy"), rho("label", "sampled")
        if not math.isnan(rs):
            rho_string.append(rs)
        if not math.isnan(rg):
            rho_greedy.append(rg)
        sm = mass[m]["string"]
        lm = mass[m]["label"]
        p(f"| {m.split('/')[-1]} | {rs:.3f} | {rg:.3f} | {rsa:.3f} | "
          f"{(sum(sm)/len(sm) if sm else float('nan')):.4f} | "
          f"{(sum(lm)/len(lm) if lm else float('nan')):.4f} |")
    p("")

    ms = sum(rho_string) / len(rho_string)
    mg = sum(rho_greedy) / len(rho_greedy)
    p(f"**Mean label~string rank correlation: {ms:.3f}** "
      f"(min {min(rho_string):.3f}, max {max(rho_string):.3f})\n")
    p(f"**Mean label~greedy rank correlation: {mg:.3f}** — the reference ceiling.\n")

    p("## Verdict\n")
    if ms > 0.7:
        p(f"String scoring **tracks the same item ordering as label scoring** "
          f"(mean rho {ms:.3f}). The large difference in level is therefore a genuine method "
          f"effect on a shifted scale, not a sign that the condition is measuring something "
          f"unrelated. It belongs in the primary variance ratio, and the level shift is part "
          f"of the result rather than an artifact to explain away.")
    elif ms > 0.4:
        p(f"String scoring **partially tracks** label scoring (mean rho {ms:.3f}), well below "
          f"the label~greedy reference of {mg:.3f}. It is measuring something related but not "
          f"the same. Keep it in the primary analysis, but the write-up must argue for its "
          f"inclusion rather than assume it, and report this correlation.")
    else:
        p(f"String scoring **does not track** label scoring (mean rho {ms:.3f}) against a "
          f"label~greedy reference of {mg:.3f}. On this evidence it is measuring a different "
          f"construct, and including it in the primary variance ratio without argument would "
          f"inflate R by comparing incommensurable quantities. Report it as a separate "
          f"finding.")
    p("")

    p("## The probability-mass problem\n")
    allsm = [x for m in mass for x in mass[m]["string"]]
    alllm = [x for m in mass for x in mass[m]["label"]]
    p(f"Mean retained mass: **string {sum(allsm)/len(allsm):.4f}**, "
      f"label {sum(alllm)/len(alllm):.4f}.\n")
    p("Our prompt DISPLAYS the five options as numbered lines, so the model is being asked "
      "how likely it is to emit option text it has effectively been steered away from. That "
      "is why string mass is low, and it is the limitation already recorded in "
      "`config/prompt.yaml`: this is not textbook cloze, which omits the options from the "
      "prompt. The comparison across the five options remains internal and consistent, so "
      "the condition is not meaningless — but it is not comparable to published cloze "
      "numbers, and the write-up must say so.\n")

    p("## Limitation of this diagnostic\n")
    p("The harness stored the per-item EXPECTATION, not the five per-option log-probabilities. "
      "The sharper test — whether label and string order the five options identically *within* "
      "an item — is not computable from the saved data. This item-level rank correlation is "
      "the best available substitute. Capturing per-option scores costs nothing and should be "
      "added if the harness is re-run.\n")

    OUT.write_text("\n".join(L), encoding="utf-8")
    print("\n".join(L))
    print(f"\nwrote {OUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
