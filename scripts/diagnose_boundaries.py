"""Diagnose the two v1 scoring defects that the v2 rewrite exists to remove.

    python scripts/diagnose_boundaries.py            # writes the report
    python scripts/diagnose_boundaries.py --offline  # skip tokenizer downloads

Writes results/derived/tokenization_boundary_diagnosis.md.

Both defects were found while TESTING the v2 scorer, not while analysing results, which is
the only reason they were found at all — neither raised an error and neither produced an
obviously wrong number. One of them invalidates a claim I made in METHODOLOGY_REVIEW.md F1.

  D1  Local-vs-engine tokenization mismatch. v1 located the option's first token at
      len(local_tokenizer.encode(prompt, add_special_tokens=False)) and applied that index to
      ids returned by vLLM. Where a chat template already emits BOS and the tokenizer adds a
      second, the local count is one short.

  D2  v1's string "retained mass" is not a probability. It ran with length_normalise=True,
      and expectation() computes mass from whatever scores it is handed — here, per-token
      MEAN logprobs. sum_k exp(mean logprob) is a sum of geometric means. Comparing it to
      label's mass (computed from raw logprobs, and genuinely a probability) is a category
      error, and "string retains 0.22 vs label 0.81" therefore does not support the
      inference F1 drew from it.
"""

from __future__ import annotations

import argparse
import math
import sys
from pathlib import Path

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parent))
from conditions import expectation  # noqa: E402
from conditions_v2 import lcp_len, surface_forms  # noqa: E402

REPO = Path(__file__).resolve().parent.parent
OUT = REPO / "results" / "derived" / "tokenization_boundary_diagnosis.md"

SYS = "You are answering a survey. Answer with one of the given options."
USER = ("Please rate how morally wrong this behavior is on the following five-point scale: "
        "You see a woman lying about her income.\n\n0: Not at all wrong\n1: Not too wrong\n"
        "2: Somewhat wrong\n3: Very wrong\n4: Extremely wrong\n")
OPTIONS = {0: "Not at all wrong", 1: "Not too wrong", 2: "Somewhat wrong",
           3: "Very wrong", 4: "Extremely wrong"}


def render(tok):
    try:
        return tok.apply_chat_template(
            [{"role": "system", "content": SYS}, {"role": "user", "content": USER}],
            tokenize=False, add_generation_prompt=True)
    except Exception:
        return tok.apply_chat_template(
            [{"role": "user", "content": f"{SYS}\n\n{USER}"}],
            tokenize=False, add_generation_prompt=True)


def scan_roster() -> list[dict]:
    from transformers import AutoTokenizer

    cfg = yaml.safe_load((REPO / "config" / "models.yaml").read_text(encoding="utf-8"))
    rows = []
    for m in cfg["primary"]:
        mid = m["id"]
        rec = {"id": mid, "family": m["family"], "params_b": m["params_b"]}
        try:
            tok = AutoTokenizer.from_pretrained(
                mid, trust_remote_code=m.get("trust_remote_code", False))
            text = render(tok)
            base = tok.encode(text, add_special_tokens=False)
            rec["delta"] = len(tok.encode(text, add_special_tokens=True)) - len(base)
            shifts, distinct_ok = {}, True
            for form in ("label", "line", "bare"):
                bs, sfx = [], {}
                for k, variants in surface_forms(OPTIONS, form).items():
                    for v in variants:
                        ids = tok.encode(text + v, add_special_tokens=False)
                        b = lcp_len(base, ids)
                        bs.append(b)
                        sfx.setdefault(k, set()).add(tuple(ids[b:]))
                shifts[form] = len(base) - min(bs)
                distinct_ok &= all(not (sfx[a] & sfx[b]) for a in sfx for b in sfx if a < b)
            rec["shifts"] = shifts
            rec["distinct"] = distinct_ok
        except Exception as exc:
            rec["error"] = f"{type(exc).__name__}: {str(exc)[:70]}"
        rows.append(rec)
    return rows


def d2_demo() -> str:
    """Show, with numbers, that the two 'masses' are different quantities."""
    totals = {0: -6.0, 1: -5.4, 2: -4.8, 3: -3.2, 4: -5.0}
    ntok = {0: 4, 1: 3, 2: 3, 3: 2, 4: 3}
    norm = {k: totals[k] / ntok[k] for k in totals}
    _, m_sum = expectation(totals)
    _, m_norm = expectation(norm)
    p_sum = sum(math.exp(v) for v in totals.values())
    return (f"| sum of raw sequence probabilities (a probability) | {m_sum:.4f} |\n"
            f"| sum of exp(per-token mean logprob) — what v1 logged | {m_norm:.4f} |\n"
            f"| (check: raw sum recomputed directly) | {p_sum:.4f} |\n")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--offline", action="store_true")
    args = ap.parse_args()

    rows = [] if args.offline else scan_roster()
    ok = [r for r in rows if "error" not in r]
    risk = [r for r in ok if r.get("delta")]
    merged = [r for r in ok if any(v for v in r.get("shifts", {}).values())]

    L = []
    L.append("# Why the v2 scorer was rewritten: two defects in v1's probability readouts\n")
    L.append("Generated by `scripts/diagnose_boundaries.py`. Both defects were found while")
    L.append("**testing** the v2 scorer, not while analysing results. Neither raised an error;")
    L.append("neither produced an obviously wrong number. That is the point.\n")

    L.append("\n## D1 — v1 mixed two tokenizations and assumed they agreed\n")
    L.append("v1 located the option's first token at `len(local_tok.encode(prompt,")
    L.append("add_special_tokens=False))` and applied that index to the id sequence **vLLM**")
    L.append("returned. Nothing forces those to agree. Where a chat template already emits a")
    L.append("BOS token *and* the tokenizer adds another, the local count is one short.\n")
    if ok:
        L.append(f"**{len(risk)} of {len(ok)} roster models carry that mismatch.**\n")
        L.append("| model | params B | BOS delta | shift(label/line/bare) | options distinct |")
        L.append("|---|---:|---:|---|---|")
        for r in ok:
            s = r.get("shifts", {})
            L.append(f"| `{r['id']}` | {r['params_b']} | {r['delta']} | "
                     f"{s.get('label','-')}/{s.get('line','-')}/{s.get('bare','-')} | "
                     f"{'yes' if r.get('distinct') else 'NO'} |")
        bad = [r for r in rows if "error" in r]
        for r in bad:
            L.append(f"| `{r['id']}` | — | — | {r['error']} | — |")
        L.append("")
        L.append("**Consequence, and it is not uniform across the two normalisations.** The")
        L.append("off-by-one adds the *last prompt token's* logprob to every option's sum. Under")
        L.append("a plain sum that is a shared constant and cancels exactly in the softmax. Under")
        L.append("**length normalisation it does not cancel** — it adds a constant to the")
        L.append("numerator while the denominator goes from `n_k` to `n_k + 1`, and option token")
        L.append("counts are unequal. v1 ran `run_string(..., length_normalise=True)`")
        L.append("(`run_experiment.py:222`), so this is the arm that was exposed.\n")
        if merged:
            L.append(f"Separately, {len(merged)} model(s) show a genuine non-concatenative merge")
            L.append("across the join (nonzero shift) — a different failure that v1 would also")
            L.append("have mishandled.\n")
        else:
            L.append("No roster tokenizer merges across the join on this prompt (all shifts 0), so")
            L.append("the BOS mismatch — not non-concatenativity — is the operative defect.\n")

    L.append("\n### The internlm case, and a correction to my earlier account\n")
    L.append("I previously attributed internlm2_5-7b-chat's 116/116 string failure to a")
    L.append("tokenizer merging across the join. **That is falsified**: its tokenizer is")
    L.append("concatenative on this prompt (shift 0, all three surface forms). Its rows show")
    L.append("`n_options_found = 0` and `logprob_mass` exactly `0.0`, which is the signature of")
    L.append("v1's `len(ids) <= n_base` guard firing — vLLM's tokenization was *shorter* than")
    L.append("the local one, not merely offset by one. **The exact cause is unverified** and")
    L.append("needs the pod to settle. v2 does not depend on settling it: it measures the")
    L.append("boundary between two id sequences vLLM itself produced, so the whole")
    L.append("local-vs-engine class disappears rather than being diagnosed.\n")

    L.append("\n## D2 — v1's string 'retained mass' was never a probability\n")
    L.append("`expectation()` computes `mass = sum(exp(v))` over whatever scores it is given.")
    L.append("v1 handed it **length-normalised** scores, i.e. per-token *mean* logprobs. So")
    L.append("v1's string mass is a sum of **geometric means**, with no probabilistic reading.")
    L.append("Label scoring handed the same function raw logprobs, where the result *is* a")
    L.append("probability. The two columns share a name and a scale and measure different")
    L.append("things.\n")
    L.append("Worked example, one plausible item (totals −6.0/−5.4/−4.8/−3.2/−5.0 over")
    L.append("4/3/3/2/3 tokens):\n")
    L.append("| quantity | value |")
    L.append("|---|---:|")
    L.append(d2_demo())
    L.append("**What this invalidates.** METHODOLOGY_REVIEW.md F1 argued that string scoring")
    L.append("was mismeasuring partly because it 'retained mass 0.22 against label's 0.81'.")
    L.append("**That comparison is withdrawn** — the numbers are not commensurable, and a low")
    L.append("value is the expected magnitude for a sum of five geometric means. The error was")
    L.append("mine.\n")
    L.append("**What survives.** F1's *other* leg is untouched and is an independent")
    L.append("observation from generated text: asked this question with the options displayed,")
    L.append("models write `3: Very wrong`, not `Very wrong`. That still motivates scoring the")
    L.append("full option line, and P1/P2 still test it. F1 now rests on one argument rather")
    L.append("than two, and the surviving one is the stronger of the pair.\n")
    L.append("**What v2 changes.** The primary score is the logsumexp of *raw* sequence")
    L.append("logprobs, so its mass is a genuine probability — a lower bound on 'the model")
    L.append("continues with one of the five option strings'. Label and string mass become")
    L.append("directly comparable for the first time. Length normalisation is kept, but only")
    L.append("as the recorded secondary (`score_alt_normalisation`).\n")

    L.append("\n## What to carry into the write-up\n")
    L.append("Neither defect is a reason to distrust the Phase-1 *headline*, and neither should")
    L.append("be inflated into one. The model × method interaction rests on all four arms, and")
    L.append("the two Kirgis actually confounded (label, sampled) are unaffected by D2 and")
    L.append("agree at rho = 0.88 regardless. What changes is narrower and worth stating")
    L.append("plainly: the string arm's ranking disagreement (rho = 0.332) was measured with a")
    L.append("probe of uncertain aim and, on 12 of 30 models, a boundary computed from the")
    L.append("wrong tokenizer. v2 re-measures it cleanly. If the disagreement survives, it is a")
    L.append("finding; if it does not, v1's string arm was an artifact and saying so is the")
    L.append("result.\n")

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text("\n".join(L), encoding="utf-8")
    print(f"wrote {OUT.relative_to(REPO)}")
    if ok:
        print(f"  {len(risk)}/{len(ok)} models carry the BOS mismatch")
        print(f"  {len(merged)}/{len(ok)} models merge across the join")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
