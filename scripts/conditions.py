"""The four scoring conditions. Built on raw vLLM.

Terminology follows the MCQ scoring literature (see CLAUDE.md):

    label scoring    probability of the option label token ("0".."4") at the first
                     generated position, renormalised over the five options
    string scoring   full-sequence log-likelihood of the option TEXT ("Not at all wrong")
    free generation, greedy    decode at T=0, parse the digit
    free generation, sampled   sample at T=1, k times, parse, average

INVARIANT THIS MODULE ENFORCES: all four conditions receive a BYTE-IDENTICAL prompt.
If that ever fails, scoring method is confounded with prompt and nothing downstream is
interpretable. `render_prompt` is the single source of the string, and the harness asserts
its hash is constant across conditions.

Label and string both return a CONTINUOUS EXPECTATION over 0-4, so they differ only in what
is scored, never in how it is aggregated. Mixing an expectation with an argmax would confound
readout with aggregation -- a second confound smuggled in while removing the first.

Why not QSTN: its value is prompt construction, which config/prompt.yaml deliberately
overrides (QSTN varies the system prompt by response-generation method, which would
reintroduce the confound under audit). What remained was a parser and a logprob
space-stripper. Raw vLLM is verified working on the target GPU; QSTN end-to-end is not.
"""

from __future__ import annotations

import hashlib
import math
import re
from dataclasses import dataclass, field

# Refusal cues. Deliberately conservative -- a false positive silently drops an item from
# the free-generation arms only, which is exactly the differential-missingness confound the
# analysis plan warns about. Better to under-flag and let parse-failure catch the rest.
REFUSAL_PATTERNS = [
    r"\bi (?:can'?t|cannot|won'?t|am unable to|am not able to)\b",
    r"\bi'?m (?:sorry|unable|not able)\b",
    r"\bas an ai\b",
    r"\bi (?:don'?t|do not) (?:feel comfortable|think it'?s appropriate)\b",
    r"\bcannot (?:provide|assist|comply|engage)\b",
]
_REFUSAL_RE = re.compile("|".join(REFUSAL_PATTERNS), re.IGNORECASE)


@dataclass
class Prompt:
    """One rendered prompt, plus everything needed to prove it didn't drift."""
    text: str
    item_id: int
    style: str = "system_role"      # or "system_merged_into_user" — see render_prompt
    sha256: str = field(init=False)

    def __post_init__(self) -> None:
        self.sha256 = hashlib.sha256(self.text.encode("utf-8")).hexdigest()[:16]


def render_prompt(tokenizer, cfg: dict, question: str, item_id: int) -> Prompt:
    """The ONLY place a prompt is built. All four conditions call this.

    Some chat templates reject a system role outright — Gemma-2 raises
    "System role not supported". For those, the system text is prepended to the user turn
    instead. This preserves the invariant that MATTERS (byte-identical across the four
    conditions within a model); prompts already differ ACROSS models because chat templates
    differ, so this is one more instance of a difference the design already accommodates.
    The fallback is recorded per model in the manifest so the write-up can name which models
    used it.
    """
    user = cfg["user_template"].replace("{{QUESTION_CONTENT_PLACEHOLDER}}", question)
    system = cfg["system"]
    try:
        text = tokenizer.apply_chat_template(
            [{"role": "system", "content": system}, {"role": "user", "content": user}],
            tokenize=False, add_generation_prompt=True,
        )
        style = "system_role"
    except Exception:
        text = tokenizer.apply_chat_template(
            [{"role": "user", "content": f"{system}\n\n{user}"}],
            tokenize=False, add_generation_prompt=True,
        )
        style = "system_merged_into_user"
    p = Prompt(text=text, item_id=item_id)
    p.style = style
    return p


# ---------------------------------------------------------------------------------------
# shared helpers
# ---------------------------------------------------------------------------------------


def option_token_ids(tokenizer, options: dict) -> dict[int, list[int]]:
    """Map option label -> ALL plausible token ids the model might emit for it.

    The first version of this took the bare digit only when it was a single token, and gave
    up otherwise. On the real roster that silently produced an EMPTY candidate set for every
    SentencePiece tokenizer (Mistral, Phi-3, Yi), because there `"0"` encodes to two tokens:
    a metaspace marker plus the digit. Label scoring then scored nothing at all and returned
    a renormalised expectation over an empty set — mass 0.0000, no error raised.

    So: gather candidates from both the bare and the space-prefixed form, and in each case
    take the LAST token, which is the digit itself once any metaspace prefix is stripped.
    Duplicates collapse. Returning a list rather than a single id is the point — which form
    the model actually emits is an empirical question, resolved at scoring time.
    """
    out: dict[int, list[int]] = {}
    for k in options:
        cands: list[int] = []
        for form in (str(k), f" {k}"):
            ids = tokenizer.encode(form, add_special_tokens=False)
            if ids:
                if len(ids) == 1:
                    cands.append(ids[0])
                else:
                    cands.append(ids[-1])   # drop the SentencePiece metaspace prefix
        seen: list[int] = []
        for c in cands:
            if c not in seen:
                seen.append(c)
        out[k] = seen
    return out


def expectation(scores: dict[int, float]) -> tuple[float, float]:
    """Softmax over log-scores, then E[k]. Returns (expectation, retained mass).

    `mass` is the sum of exp(logprob) BEFORE renormalising. It is the integrity check that
    the B1 reanalysis showed to be necessary: grok-3-beta returned logprobs summing to ~0
    while claiming p=1.0 for the emitted token, and renormalisation silently masked it.
    Log the mass so the same failure cannot hide here.
    """
    if not scores:
        return math.nan, 0.0
    mx = max(scores.values())
    exps = {k: math.exp(v - mx) for k, v in scores.items()}
    tot = sum(exps.values())
    e = sum(k * v for k, v in exps.items()) / tot
    mass = sum(math.exp(v) for v in scores.values())
    return e, mass


def parse_digit(text: str) -> tuple[int | None, str]:
    """Parse the answer digit. Returns (value, strategy).

    Strategy matters and is recorded per row, because the fallback path is a known failure
    mode rather than a neutral alternative. Kirgis's equivalent scanned the whole generated
    sequence for the first all-digit token; on grok-3 that locked onto digits inside prose.
    The same regex here would score "On a scale of 0 to 4, I'd say 3" as 0.

      "anchored"  digit at the very start of the response -- the intended format, trusted
      "scan"      digit found later in prose -- RECORDED AND FLAGGED, not silently trusted
      "none"      no digit; parse failure

    Rows parsed by "scan" are counted separately so the analysis can be re-run without them.
    Treating them as equivalent to anchored parses would import exactly the artifact this
    study exists to measure.
    """
    if not text:
        return None, "none"
    m = re.match(r"\s*[*_`#\s]*([0-4])(?![0-9])", text)
    if m:
        return int(m.group(1)), "anchored"

    # Our own prompt lists "0: Not at all wrong ... 4: Extremely wrong", so a model echoing
    # the scale back ("on a scale of 0 to 4 ...") is a PREDICTABLE pattern, not a hypothetical.
    # Blank those spans before any bare-digit search, or the parser reads the scale endpoint
    # as the answer -- the same class of error that mis-scored Kirgis's grok-3 responses.
    masked = re.sub(r"\b[0-4]\s*(?:to|through|[-–—])\s*[0-4]\b", " ", text)
    masked = re.sub(r"\b(?:five|5)[-\s]?point\b", " ", masked, flags=re.I)

    # Prefer an explicit "answer: N" style statement over a bare digit in running prose.
    m = re.search(r"(?:answer|rating|score|rate|say|choose|select)\D{0,12}?([0-4])(?![0-9])",
                  masked, re.I)
    if m:
        return int(m.group(1)), "scan"
    m = re.search(r"(?<![0-9)])\b([0-4])\b(?![0-9])", masked)
    return (int(m.group(1)), "scan") if m else (None, "none")


def is_refusal(text: str) -> bool:
    return bool(text) and bool(_REFUSAL_RE.search(text))


# ---------------------------------------------------------------------------------------
# condition 1 -- label scoring
# ---------------------------------------------------------------------------------------


def run_label(llm, sampling_params_cls, prompts: list[Prompt],
              tok_ids: dict[int, list[int]], top_logprobs: int = 20,
              scan_positions: int = 4) -> list[dict]:
    """Score the option label, at the first position where the model is actually answering.

    Reading position 0 unconditionally is what the literature describes, and on this roster
    it is wrong for a third of models: Mistral emits '\\n' first, Phi-3 emits a bare
    metaspace token, Llama-3.2-1B starts prose ('I'), Ministral emits '</s>' immediately.
    Scoring position 0 there measures the probability of a newline, not of an answer.

    So we generate a few tokens and take the FIRST position whose top-k actually contains an
    option token. `label_position` records which one was used, per row, so the write-up can
    report how often position 0 was not the answer — that rate is itself a result about how
    fragile first-token label scoring is.

    If no position in the scan window contains an option token, the row is flagged
    parse_failed rather than assigned a fabricated score.
    """
    sp = sampling_params_cls(temperature=0.0, max_tokens=scan_positions,
                             logprobs=top_logprobs)
    outs = llm.generate([p.text for p in prompts], sp)
    rows = []
    for p, o in zip(prompts, outs):
        co = o.outputs[0]
        lps = co.logprobs or []
        found: dict[int, float] = {}
        used = -1
        for pos_i, pos in enumerate(lps[:scan_positions]):
            hit = {}
            for k, cands in tok_ids.items():
                best = None
                for tid in cands:
                    if tid in pos:
                        lp = pos[tid].logprob
                        best = lp if best is None else max(best, lp)
                if best is not None:
                    hit[k] = best
            if hit:
                found, used = hit, pos_i
                break
        e, mass = expectation(found)
        rows.append({
            "item_id": p.item_id, "condition": "label", "replicate": 0,
            "prompt_sha": p.sha256, "score": e, "logprob_mass": mass,
            "n_options_found": len(found),
            "label_position": used,
            "raw_output": co.text,
            "emitted_token_id": co.token_ids[0] if co.token_ids else None,
            "refusal": False, "parse_failed": len(found) == 0,
        })
    return rows


# ---------------------------------------------------------------------------------------
# condition 2 -- string scoring (the only hand-written condition; QSTN has no equivalent)
# ---------------------------------------------------------------------------------------


def run_string(llm, sampling_params_cls, tokenizer, prompts: list[Prompt],
               options: dict, length_normalise: bool = True) -> list[dict]:
    """Full-sequence log-likelihood of each option's TEXT, as a continuation of the prompt.

    A single-position readout CANNOT do this job: the probe confirmed options 0 and 1 share
    their first token ("Not"), so "Not at all wrong" and "Not too wrong" are indistinguishable
    at position 0.

    LENGTH NORMALISATION IS A REAL CHOICE, not a default -- option token lengths are unequal
    ({0:4, 1:3, 2:3, 3:2, 4:3} on Qwen), so the unnormalised sum favours short options. Both
    are computed and both are recorded; the pre-specified primary is stated in
    config/prompt.yaml.
    """
    texts, index = [], []
    for p in prompts:
        base_ids = tokenizer.encode(p.text, add_special_tokens=False)
        for k, opt in options.items():
            full = p.text + opt
            texts.append(full)
            index.append((p, k, len(base_ids)))

    sp = sampling_params_cls(temperature=0.0, max_tokens=1, prompt_logprobs=0)
    outs = llm.generate(texts, sp)

    acc: dict[int, dict] = {}
    for (p, k, n_base), o in zip(index, outs):
        plp = o.prompt_logprobs or []
        ids = o.prompt_token_ids
        # Boundary check: the option's tokens must start exactly where the prompt ended.
        # Tokenizers are not always concatenative, so verify rather than assume.
        total, n_tok, clean = 0.0, 0, True
        if len(ids) <= n_base:
            clean = False
        else:
            for i in range(n_base, len(ids)):
                entry = plp[i] if i < len(plp) else None
                if not entry or ids[i] not in entry:
                    clean = False
                    break
                total += entry[ids[i]].logprob
                n_tok += 1
        d = acc.setdefault(p.item_id, {"p": p, "sum": {}, "norm": {}, "clean": True})
        if clean and n_tok:
            d["sum"][k] = total
            d["norm"][k] = total / n_tok
        else:
            d["clean"] = False

    rows = []
    for item_id, d in acc.items():
        chosen = d["norm"] if length_normalise else d["sum"]
        e, mass = expectation(chosen)
        e_alt, _ = expectation(d["sum"] if length_normalise else d["norm"])
        rows.append({
            "item_id": item_id, "condition": "string", "replicate": 0,
            "prompt_sha": d["p"].sha256, "score": e, "logprob_mass": mass,
            "score_alt_normalisation": e_alt,
            "n_options_found": len(chosen),
            "raw_output": "", "emitted_token_id": None,
            "refusal": False,
            "parse_failed": (not d["clean"]) or len(chosen) < len(chosen),
            "token_boundary_clean": d["clean"],
        })
    return rows


# ---------------------------------------------------------------------------------------
# conditions 3 and 4 -- free generation
# ---------------------------------------------------------------------------------------


def run_free(llm, sampling_params_cls, prompts: list[Prompt], *, greedy: bool,
             k: int = 1, seeds: list[int] | None = None, max_tokens: int = 96) -> list[dict]:
    """Greedy (k=1, T=0) or sampled (k>1, T=1).

    vLLM's `n=k` is deliberately NOT used: k independent passes with distinct seeds keep each
    replicate separately identifiable, which the pre-specified Monte-Carlo error term needs.
    Prefix caching makes the repeated passes cheap in tokens.
    """
    rows = []
    seeds = seeds or list(range(k))
    for rep in range(1 if greedy else k):
        sp = (sampling_params_cls(temperature=0.0, max_tokens=max_tokens)
              if greedy else
              sampling_params_cls(temperature=1.0, top_p=1.0, max_tokens=max_tokens,
                                  seed=seeds[rep]))
        outs = llm.generate([p.text for p in prompts], sp)
        for p, o in zip(prompts, outs):
            txt = o.outputs[0].text
            d, how = parse_digit(txt)
            rows.append({
                "item_id": p.item_id,
                "condition": "greedy" if greedy else "sampled",
                "replicate": rep,
                "prompt_sha": p.sha256,
                "score": float(d) if d is not None else math.nan,
                "logprob_mass": math.nan,
                "n_options_found": 1 if d is not None else 0,
                "raw_output": txt,
                "emitted_token_id": None,
                "refusal": is_refusal(txt),
                "parse_failed": d is None,
                "parse_strategy": how,
                "seed": None if greedy else seeds[rep],
            })
    return rows
