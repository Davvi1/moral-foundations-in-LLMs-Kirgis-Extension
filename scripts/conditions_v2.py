"""v2 scoring conditions. Every probability readout becomes ONE mechanism: forced continuation.

WHY THIS EXISTS -- read this before the code, it is the argument for the whole rewrite.

v1 (`conditions.py`) implemented label scoring and string scoring as two different
machines, and each machine had a defect that the Phase-1 data exposed:

  F2, label scoring.  v1 generated a few tokens, then scanned for the first position whose
      top-20 contained an option token. Two problems. (a) TRUNCATION: if "4" is not in the
      top-20 at that position, its probability is not merely small, it is ABSENT -- the
      option silently drops out of the expectation and out of the retained mass. The number
      that comes back is an expectation over whichever options happened to make the cut.
      (b) DEGREES OF FREEDOM: "first position containing an option token" is a rule I chose
      after seeing that position 0 failed on a third of the roster. It is defensible, but it
      is mine, and a reviewer is entitled to ask what the other rules would have given.

  F1, string scoring.  v1 scored the bare option phrase ("Very wrong"), and the models' own
      greedy output shows they answer "3: Very wrong" instead -- so v1's string arm may have
      been scoring a continuation the model was never going to write. Its ranking
      disagreement with label (rho = 0.332) is therefore confounded between two readings we
      could not separate: a genuine construct difference, or a badly aimed probe.

      THE OTHER HALF OF F1's ORIGINAL EVIDENCE HAS BEEN WITHDRAWN. F1 also cited "string
      retains 0.22 probability mass against label's 0.81". That comparison was invalid and
      the error was mine. v1 ran with `length_normalise=True`, so its `mass` was
      sum_k exp(mean-per-token logprob) -- a sum of geometric means, not a probability, and
      not on the same scale as label's mass at all. See
      `results/derived/tokenization_boundary_diagnosis.md`. v2 removes the confusion by
      construction: the primary score is the logsumexp of RAW sequence logprobs, so its mass
      is a genuine probability and label and string masses become comparable for the first
      time. Length normalisation survives only as the recorded secondary.

  F8, boundaries.  v1 located the option's first token at `len(tokenize(prompt))`, computed
      with the LOCAL tokenizer, and compared it against ids returned by vLLM. Those two
      tokenizations do not have to agree, and on 12 of the 30 roster models they do not:
      the chat template already emits a BOS and the tokenizer adds a second one, so the
      local count is one short (verified locally by `test_conditions_v2.py --online`).
      Under length normalisation that off-by-one does NOT cancel -- it adds a shared
      constant to every option's sum while dividing by different token counts.

      NOTE ON internlm2_5-7b-chat, whose string arm failed 116/116. I previously attributed
      that to a tokenizer merging across the join. That is FALSIFIED: internlm's tokenizer
      is concatenative on this prompt (shift 0 for all three surface forms). Its rows show
      n_options_found = 0 and mass exactly 0.0, which is the signature of v1's
      `len(ids) <= n_base` guard firing -- i.e. vLLM's tokenization was SHORTER than the
      local one, not merely offset. The exact cause is UNVERIFIED and needs the pod to
      settle. v2 does not depend on knowing it: the boundary is measured between two id
      sequences vLLM itself produced, so the entire local-vs-engine class of mismatch is
      gone rather than diagnosed.

THE UNIFICATION. All three fixes are the same fix. Ask, for each option k:

    what is log P(the model's next tokens spell out option k | this exact prompt) ?

Answer it by APPENDING the option's text to the prompt and reading back the log-probability
the model assigns to those appended tokens. vLLM will do this with `prompt_logprobs=0`:
score the sequence, return each token's own logprob. No top-k list, so nothing can be
truncated away. No position rule, because the position is wherever the appended text lands.
And label scoring stops being a separate method -- it is this same computation with the
surface form "3" instead of "3: Very wrong". One machine, three probes.

    label   ->  "3"
    line    ->  "3: Very wrong"      (the format the prompt displays and models emit)
    bare    ->  "Very wrong"         (v1's probe, kept so v1 and v2 remain comparable)

WHAT THIS BUYS, concretely: the position-scan disappears, truncation cannot happen, the
retained mass becomes an interpretable lower bound on "the model answers in one of the five
option formats", and F1's two readings become separable -- if `line` recovers the mass that
`bare` lost AND recovers agreement with label, v1's string arm was mismeasuring; if mass
recovers and disagreement persists, the disagreement is real. That contrast is registered as
P1/P2 in docs/state.md, before this code produced a number.

WHAT IT DOES NOT BUY: free generation is unaffected. Greedy and sampled still decode text and
parse it, and they still come from `conditions.py`. This module replaces the two probability
readouts only.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field

from conditions import Prompt, expectation  # noqa: F401  (re-exported for the harness)

# ---------------------------------------------------------------------------------------
# surface forms
# ---------------------------------------------------------------------------------------

FORMS = ("label", "line", "bare")


def surface_forms(options: dict[int, str], form: str) -> dict[int, list[str]]:
    """Option key -> the surface strings we will accept as spelling that option out.

    Each option gets its text in both bare and space-prefixed form. This is not fussiness.
    Whether a model writes "3" or " 3" after the chat template's generation prompt is a
    tokenizer-and-template detail that varies across the roster, and scoring only the bare
    form would score near-zero probability on models that prefer the other one -- which is a
    measurement artifact dressed up as a low score. Both are scored and their probabilities
    are SUMMED (see `_score_options`), because "the model writes 3" and "the model writes a
    space then 3" are mutually exclusive ways for the same answer to happen.

    Applied identically to all five options, so nothing here can favour one option.
    """
    if form == "label":
        base = {k: str(k) for k in options}
    elif form == "line":
        base = {k: f"{k}: {options[k]}" for k in options}
    elif form == "bare":
        base = {k: str(options[k]) for k in options}
    else:
        raise ValueError(f"unknown surface form {form!r}; expected one of {FORMS}")
    return {k: [v, f" {v}"] for k, v in base.items()}


# ---------------------------------------------------------------------------------------
# tokenizer-agnostic boundary finding -- the F8 fix
# ---------------------------------------------------------------------------------------


def lcp_len(a, b) -> int:
    """Length of the longest common prefix of two token-id sequences."""
    n = min(len(a), len(b))
    i = 0
    while i < n and a[i] == b[i]:
        i += 1
    return i


def _logsumexp(xs: list[float]) -> float:
    xs = [x for x in xs if x > -math.inf]
    if not xs:
        return -math.inf
    m = max(xs)
    return m + math.log(sum(math.exp(x - m) for x in xs))


@dataclass
class _Seq:
    """One submitted sequence: a prompt, optionally with an option variant appended."""
    item_id: int
    option: int | None      # None marks the bare-prompt reference sequence
    variant: str
    text: str
    ids: tuple[int, ...] = field(default_factory=tuple)
    logprobs: list[float] = field(default_factory=list)


def _score_options(seqs_for_item: list[_Seq], base_ids: tuple[int, ...],
                   length_normalise: bool) -> tuple[dict[int, float], dict[int, float], dict]:
    """Turn one item's scored sequences into per-option log-probabilities.

    THE BOUNDARY PROBLEM, and why the obvious fix is not enough. We want
    log P(option text | prompt), which is the sum of token logprobs over the appended text.
    That requires knowing where the prompt ends and the option begins. v1 assumed the
    boundary sits at `len(tokenize(prompt))`. It often does not: appending text can cause the
    tokenizer to re-merge across the join, so the last prompt token changes identity and the
    two id sequences diverge BEFORE the appended text starts.

    The fix is to stop assuming and measure. Take the longest common prefix of the bare
    prompt's ids and each variant's ids. Everything after it is "what changed when we
    appended", and the sum of its logprobs is log P(that continuation | the shared prefix).

    THE SECOND HALF OF THE FIX, which is the part that is easy to miss: different options can
    have different common-prefix lengths. If option 0 conditions on 210 tokens and option 3
    conditions on 209, their log-probabilities are not on the same footing and comparing them
    is meaningless. So we take the MINIMUM common prefix across every variant of every option
    and score all of them from that single point. All five numbers then condition on a prefix
    that is byte-for-byte and token-for-token identical, which is the only thing that makes
    the softmax across options interpretable.

    Returns (log-probability per option, length-normalised score per option, diagnostics).
    """
    variants = [s for s in seqs_for_item if s.option is not None]
    if not variants:
        return {}, {}, {"boundary": -1, "shift": 0, "degenerate": []}

    boundary = min(lcp_len(base_ids, s.ids) for s in variants)
    # How far the boundary moved from the naive assumption. Nonzero means a real tokenizer
    # merge across the join -- the thing that killed internlm's string arm in v1. It is not
    # an error here, but it IS reportable, so the write-up can say how common it is.
    shift = len(base_ids) - boundary

    per_option_raw: dict[int, list[tuple[float, int]]] = {}
    seen_ids: dict[tuple[int, ...], int] = {}
    degenerate: list[str] = []

    for s in variants:
        suffix = s.ids[boundary:]
        if not suffix:
            continue
        # Deduplicate by TOKEN IDS, not by text. If two variants tokenize identically --
        # e.g. a tokenizer that strips the leading space, making "3" and " 3" the same
        # sequence -- summing both would double-count the same probability mass and inflate
        # that option. Same check across options catches a fatal degeneracy: two options that
        # are indistinguishable to the model.
        if suffix in seen_ids:
            if seen_ids[suffix] != s.option:
                degenerate.append(f"option {seen_ids[suffix]} == option {s.option}")
            continue
        seen_ids[suffix] = s.option
        lps = s.logprobs[boundary:]
        if len(lps) != len(suffix) or any(lp is None for lp in lps):
            continue
        per_option_raw.setdefault(s.option, []).append((float(sum(lps)), len(suffix)))

    lp: dict[int, float] = {}
    lp_norm: dict[int, float] = {}
    for k, cands in per_option_raw.items():
        if not cands:
            continue
        # Primary: sum the probabilities of the accepted surface variants. Stays a genuine
        # probability, so the retained mass downstream stays interpretable.
        lp[k] = _logsumexp([tot for tot, _ in cands])
        # Secondary: length normalisation. A REAL CHOICE, not a default -- option texts have
        # unequal token counts, so the unnormalised sum structurally favours short options.
        # Take the variant the model actually prefers, then divide by its length.
        best_tot, best_n = max(cands, key=lambda c: c[0])
        lp_norm[k] = best_tot / max(best_n, 1)

    diag = {
        "boundary": boundary,
        "shift": shift,
        "degenerate": sorted(set(degenerate)),
        "n_options": len(lp),
    }
    return (lp_norm if length_normalise else lp), (lp if length_normalise else lp_norm), diag


# ---------------------------------------------------------------------------------------
# the engine
# ---------------------------------------------------------------------------------------


def score_forced_continuations(llm, sampling_params_cls, prompts: list[Prompt],
                               options: dict[int, str], form: str, *,
                               condition: str | None = None,
                               length_normalise: bool = False) -> list[dict]:
    """Score every option as a forced continuation of the prompt. One `generate` call.

    Submits, per item, the bare prompt plus one sequence per (option, surface variant). The
    bare prompt is submitted rather than tokenized locally ON PURPOSE: it must be tokenized
    by the same engine, under the same settings, as the variants, or the common-prefix
    comparison is between two different tokenizations and the boundary is garbage. This costs
    one extra short sequence per item and removes an entire class of silent error.
    """
    forms = surface_forms(options, form)
    seqs: list[_Seq] = []
    for p in prompts:
        seqs.append(_Seq(item_id=p.item_id, option=None, variant="", text=p.text))
        for k, vs in forms.items():
            for v in vs:
                seqs.append(_Seq(item_id=p.item_id, option=k, variant=v, text=p.text + v))

    sp = sampling_params_cls(temperature=0.0, max_tokens=1, prompt_logprobs=0)
    outs = llm.generate([s.text for s in seqs], sp)

    for s, o in zip(seqs, outs):
        s.ids = tuple(o.prompt_token_ids)
        plp = o.prompt_logprobs or []
        # vLLM reports None for position 0 (nothing precedes it). Carry that through as
        # -inf-free bookkeeping: position 0 is always inside the shared prefix, so it is
        # never summed.
        row: list[float] = []
        for i, tid in enumerate(s.ids):
            entry = plp[i] if i < len(plp) else None
            row.append(float(entry[tid].logprob) if entry and tid in entry else None)  # type: ignore[arg-type]
        s.logprobs = row

    by_item: dict[int, list[_Seq]] = {}
    for s in seqs:
        by_item.setdefault(s.item_id, []).append(s)
    prompt_by_item = {p.item_id: p for p in prompts}

    cond = condition or f"string_{form}"
    rows = []
    for item_id, group in by_item.items():
        base = next((s for s in group if s.option is None), None)
        if base is None:
            continue
        primary, secondary, diag = _score_options(group, base.ids, length_normalise)
        e, mass = expectation(primary)
        e_alt, _ = expectation(secondary)
        p = prompt_by_item[item_id]
        rows.append({
            "item_id": item_id, "condition": cond, "replicate": 0,
            "prompt_sha": p.sha256, "score": e, "logprob_mass": mass,
            "score_alt_normalisation": e_alt,
            "n_options_found": diag["n_options"],
            "surface_form": form,
            "boundary_shift": diag["shift"],
            "degenerate_options": ";".join(diag["degenerate"]),
            "raw_output": "", "emitted_token_id": None,
            "refusal": False,
            "parse_failed": diag["n_options"] < len(options),
            "token_boundary_clean": diag["shift"] == 0,
        })
    return rows


# ---------------------------------------------------------------------------------------
# the four v2 probability conditions
# ---------------------------------------------------------------------------------------


def run_label_exact(llm, sampling_params_cls, prompts, options) -> list[dict]:
    """Label scoring, exact. Replaces v1's top-k scan (F2).

    Same estimand as v1 -- the probability the model's answer is the digit k -- but read by
    forcing each digit and taking its logprob, so all five are always present and none can be
    truncated out of the top-20. Where v1's mass was "how much of the top-20 was digits",
    this mass is "how much probability the model puts on answering with a bare digit at all".
    Those are different quantities and the v2 number is the one we actually wanted.
    """
    return score_forced_continuations(llm, sampling_params_cls, prompts, options,
                                      "label", condition="label")


def run_string_line(llm, sampling_params_cls, prompts, options) -> list[dict]:
    """String scoring against the full option line, "3: Very wrong". The F1 fix.

    This is the format the prompt displays and the format models emit unprompted. P1 predicts
    it recovers mass over the bare phrase; P2 predicts it recovers ranking agreement with
    label. P2 is the one that matters: if mass recovers and agreement does NOT, then v1's
    rho = 0.332 was a real construct difference rather than a mismeasurement, which makes the
    Phase-1 headline stronger, not weaker. Registered before this ran.
    """
    return score_forced_continuations(llm, sampling_params_cls, prompts, options,
                                      "line", condition="string_line")


def run_string_bare(llm, sampling_params_cls, prompts, options) -> list[dict]:
    """String scoring against the bare phrase, "Very wrong". v1's probe, re-implemented.

    Kept for one reason: without it, every v2-vs-v1 difference is confounded between the
    change of probe (bare -> line) and the change of machinery (boundary assumption -> LCP,
    top-k -> exact). Running the old probe on the new machinery separates them.
    """
    return score_forced_continuations(llm, sampling_params_cls, prompts, options,
                                      "bare", condition="string_bare")


def run_cloze(llm, sampling_params_cls, prompts_cloze, options) -> list[dict]:
    """Textbook cloze: bare phrase scored against a prompt that does NOT display the options.

    EXPLORATORY, AND IT BREAKS THE DESIGN'S CENTRAL INVARIANT BY CONSTRUCTION. Every other
    condition receives a byte-identical prompt; this one cannot, because "textbook cloze"
    means removing the option list, which is a different prompt. It is therefore excluded
    from the primary variance ratio -- including it would put a prompt effect inside a number
    defined as a method effect, which is the exact error this project audits Kirgis for.

    Its job is diagnostic and narrow: `config/prompt.yaml` discloses that our string scoring
    is not textbook cloze because the options are visible. This measures how much that
    matters. P4 predicts cloze tracks bare-phrase scoring more closely than it tracks label.
    Reported separately, labelled prompt-varying, never pooled.
    """
    return score_forced_continuations(llm, sampling_params_cls, prompts_cloze, options,
                                      "bare", condition="cloze")
