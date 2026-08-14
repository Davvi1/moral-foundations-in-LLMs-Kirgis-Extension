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


def failure_type(text: str, parsed: int | None) -> str:
    """Classify WHY a free-generation row has no usable score. Never pool these.

    A single `parse_failed` flag hides three phenomena that mean entirely different things:

      "ok"           a digit was recovered; not a failure
      "empty_output" the model emitted nothing at all -- EOS was its argmax first token.
                     A DECODING artifact. Ministral-8B does this on 116/116 greedy items
                     while answering ~half the time under sampling, so it is not reticence.
      "refusal"      the model declined in words. A VALUE-LADEN act, expected to correlate
                     with foundation, and precisely the confound this design predicted.
                     Llama-3.2-1B: "I can't answer this question.", 108/116 greedy.
      "unparseable"  the model wrote something, but no digit could be recovered from it.

    Reporting refusal and empty output as one number would make both uninterpretable, and
    would let the write-up claim a model "refuses" when it never speaks at all.
    """
    if parsed is not None:
        return "ok"
    if not text or not text.strip():
        return "empty_output"
    if is_refusal(text):
        return "refusal"
    return "unparseable"


# ---------------------------------------------------------------------------------------
# condition 1 -- label scoring
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
