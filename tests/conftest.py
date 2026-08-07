"""Shared test fixtures.

These tests exist because vLLM is Linux+GPU only, so the harness cannot be exercised on the
development laptop against the real thing. Every hour of pod time is billed, and a harness
that fails on first contact wastes both money and the two-day budget. So: a faithful fake of
the vLLM API surface, driven against REAL tokenizers, covering the cases we know will occur.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

import pytest

# Corporate SSL interception breaks huggingface_hub's default cert chain on this machine.
# truststore routes verification through the Windows certificate store instead.
try:
    import truststore

    truststore.inject_into_ssl()
except Exception:  # pragma: no cover - not needed on the pod
    pass

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "scripts"))
sys.path.insert(0, str(Path(__file__).resolve().parent))


@pytest.fixture(scope="session")
def repo() -> Path:
    return REPO


@pytest.fixture(scope="session")
def prompt_cfg() -> dict:
    import yaml

    with (REPO / "config" / "prompt.yaml").open(encoding="utf-8") as fh:
        return yaml.safe_load(fh)


@pytest.fixture(scope="session")
def items() -> list[tuple[int, str]]:
    import csv

    with (REPO / "data" / "mfv_116.csv").open(newline="", encoding="utf-8") as fh:
        return [(int(r["questionnaire_item_id"]), r["question_content"])
                for r in csv.DictReader(fh)]


def _load_tok(model_id: str):
    from transformers import AutoTokenizer

    return AutoTokenizer.from_pretrained(model_id)


@pytest.fixture(scope="session")
def qwen_tok():
    return _load_tok("Qwen/Qwen2.5-0.5B-Instruct")


# Tokenizer families in the roster whose chat templates and digit tokenization differ.
# Gated repos (Llama, Gemma) are skipped when no HF token is present.
FAMILY_TOKENIZERS = [
    "Qwen/Qwen2.5-0.5B-Instruct",
    "mistralai/Mistral-7B-Instruct-v0.3",
    "microsoft/Phi-3-mini-4k-instruct",
    "HuggingFaceTB/SmolLM2-1.7B-Instruct",
    "allenai/OLMo-2-1124-7B-Instruct",
    "ibm-granite/granite-3.1-8b-instruct",
    "Qwen/Qwen2.5-14B-Instruct",
]


@pytest.fixture(scope="session", params=FAMILY_TOKENIZERS)
def any_tok(request):
    try:
        return request.param, _load_tok(request.param)
    except Exception as exc:
        pytest.skip(f"tokenizer unavailable ({request.param}): {type(exc).__name__}")
