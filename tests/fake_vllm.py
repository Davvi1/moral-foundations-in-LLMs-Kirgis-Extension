"""A faithful fake of the vLLM API surface the harness touches.

Mirrors vLLM 0.26.0 exactly where we depend on it, verified by reading
vllm/sampling_params.py and vllm/outputs.py at tag v0.26.0:

    SamplingParams(temperature, top_p, max_tokens, logprobs, prompt_logprobs, seed, n)
    llm.generate(prompts, sampling_params) -> list[RequestOutput]
    RequestOutput.prompt_token_ids : list[int]
    RequestOutput.prompt_logprobs  : list[dict[int, Logprob] | None]   # aligned to prompt
    RequestOutput.outputs[0]       : CompletionOutput
    CompletionOutput.text, .token_ids, .logprobs : list[dict[int, Logprob]]
    Logprob.logprob, .decoded_token, .rank

If the fake and the real thing diverge, these tests are worthless — so the fake is
deliberately dumb about behaviour and precise about SHAPE. Behaviour is injected per test.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable


@dataclass
class Logprob:
    logprob: float
    rank: int | None = None
    decoded_token: str | None = None


@dataclass
class CompletionOutput:
    index: int
    text: str
    token_ids: list[int]
    logprobs: list[dict[int, Logprob]] | None = None
    finish_reason: str = "length"


@dataclass
class RequestOutput:
    request_id: str
    prompt: str
    prompt_token_ids: list[int]
    outputs: list[CompletionOutput]
    prompt_logprobs: list[dict[int, Logprob] | None] | None = None
    finished: bool = True


@dataclass
class SamplingParams:
    n: int = 1
    temperature: float = 1.0
    top_p: float = 1.0
    max_tokens: int | None = 16
    logprobs: int | None = None
    prompt_logprobs: int | None = None
    seed: int | None = None
    # Recorded so tests can assert the harness passed what it claims to pass.
    _seen: list = field(default_factory=list)


class FakeLLM:
    """Drives responses from a caller-supplied function so tests inject behaviour.

    responder(prompt, sampling_params, tokenizer) -> dict with any of:
        text            : str, the generated text
        token_ids       : list[int]
        first_logprobs  : dict[token_id -> logprob] for generation position 0
        prompt_logprobs_override : list aligned to prompt token ids
    """

    def __init__(self, tokenizer, responder: Callable):
        self.tokenizer = tokenizer
        self.responder = responder
        self.calls: list[tuple[list[str], SamplingParams]] = []

    def generate(self, prompts, sampling_params, **kwargs):
        if isinstance(prompts, str):
            prompts = [prompts]
        self.calls.append((list(prompts), sampling_params))
        outs = []
        for i, p in enumerate(prompts):
            spec = self.responder(p, sampling_params, self.tokenizer) or {}
            ptids = self.tokenizer.encode(p, add_special_tokens=False)

            plp = None
            if sampling_params.prompt_logprobs is not None:
                if "prompt_logprobs_override" in spec:
                    plp = spec["prompt_logprobs_override"]
                else:
                    # vLLM's real behaviour: index 0 is None (nothing conditions the first
                    # token), every later index is a dict containing at least the actual
                    # token. Getting this wrong is exactly the bug string scoring would hit.
                    plp = [None]
                    for tid in ptids[1:]:
                        plp.append({tid: Logprob(logprob=-0.5, decoded_token=None)})

            text = spec.get("text", "")
            tids = spec.get("token_ids")
            if tids is None:
                tids = self.tokenizer.encode(text, add_special_tokens=False)[:1] or [0]

            lps = None
            if sampling_params.logprobs is not None:
                fl = spec.get("first_logprobs")
                if fl is None:
                    fl = {tids[0]: -0.1}
                lps = [{tid: Logprob(logprob=lp,
                                     decoded_token=self.tokenizer.decode([tid]))
                        for tid, lp in fl.items()}]

            outs.append(RequestOutput(
                request_id=str(i), prompt=p, prompt_token_ids=ptids,
                prompt_logprobs=plp,
                outputs=[CompletionOutput(index=0, text=text, token_ids=list(tids),
                                          logprobs=lps)],
            ))
        return outs
