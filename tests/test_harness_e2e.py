"""End-to-end tests of scripts/run_experiment.py — the actual pod entry point.

vLLM and its GPU are unavailable locally, so a fake `vllm` module is injected into
sys.modules before the harness imports it. Everything else — config loading, prompt
rendering with a real tokenizer, CSV writing, manifests, checkpointing — is the real code.

These target the failures that would silently corrupt a run rather than crash it.
"""

from __future__ import annotations

import csv
import json
import math
import sys
import types
from pathlib import Path

import pytest

import conditions as C
import fake_vllm


@pytest.fixture
def fake_vllm_module(qwen_tok, monkeypatch):
    """Inject a fake `vllm` so `from vllm import LLM, SamplingParams` resolves."""
    ids = None

    class _LLM(fake_vllm.FakeLLM):
        def __init__(self, model, revision=None, **kw):
            self.model, self.revision, self.kwargs = model, revision, kw
            super().__init__(qwen_tok, _responder)

    def _responder(prompt, sp, tok):
        nonlocal ids
        if ids is None:
            ids = {k: tok.encode(str(k), add_special_tokens=False)[-1] for k in range(5)}
        return {
            "text": "2\nSomewhat wrong because it disregards others.",
            "token_ids": [ids[2]],
            "first_logprobs": {ids[k]: math.log(v) for k, v in
                               {0: .05, 1: .10, 2: .50, 3: .30, 4: .05}.items()},
        }

    mod = types.ModuleType("vllm")
    mod.LLM = _LLM
    mod.SamplingParams = fake_vllm.SamplingParams
    monkeypatch.setitem(sys.modules, "vllm", mod)
    return mod


@pytest.fixture
def harness(fake_vllm_module, tmp_path, monkeypatch):
    import run_experiment as R

    monkeypatch.setattr(R, "RAW", tmp_path)
    return R


# Both harnesses are live code and both must stay correct. v2 is what new collection uses;
# v1 still backs every committed Phase-1 CSV and its manifests pin those code paths, so a
# regression there would make the archived results unreproducible. Parametrising means every
# end-to-end guarantee below is asserted twice, once per harness, rather than the older one
# quietly rotting once it stopped being the default.
EXPECTED_CONDITIONS = {
    "v1": {"label", "string", "greedy", "sampled"},
    "v2": {"label", "string_line", "string_bare", "greedy", "sampled"},
}


@pytest.fixture(params=["v1", "v2"])
def args_ns(request):
    import argparse

    return argparse.Namespace(
        harness=request.param, cloze=False,
        limit_items=0, k=3, max_model_len=1024, gpu_util=0.85, eager=True,
        purge_weights=False, force=False, conditions=None, suffix="",
    )


# The REAL pinned revision from config/models.yaml. Using a fake SHA here would not just
# fail — it would hide the fact that the harness passes `revision` to the tokenizer as well
# as to vLLM, which is exactly the behaviour we want to guarantee.
PINNED_REV = "7ae557604adf67be50417f59c2c2f167def9a775"
ENTRY = {"id": "Qwen/Qwen2.5-0.5B-Instruct", "revision": PINNED_REV,
         "family": "qwen", "params_b": 0.5}


# =======================================================================================
# Silent-data-loss guards
# =======================================================================================


def test_every_key_produced_by_a_runner_is_in_FIELDS(qwen_tok, prompt_cfg, items):
    """csv.DictWriter(extrasaction='ignore') DROPS unknown keys silently. If a runner ever
    emits a column missing from FIELDS, that data vanishes with no error. This is the
    single most dangerous silent failure in the harness."""
    import run_experiment as R

    ps = [C.render_prompt(qwen_tok, prompt_cfg, q, i) for i, q in items[:2]]
    ids = C.option_token_ids(qwen_tok, prompt_cfg["options"])
    llm = fake_vllm.FakeLLM(qwen_tok, lambda p, sp, t: {
        "text": "2", "token_ids": [ids[2][0]], "first_logprobs": {ids[2][0]: -0.1}})

    produced: set[str] = set()
    for rows in (
        C.run_label(llm, fake_vllm.SamplingParams, ps, ids),
        C.run_string(llm, fake_vllm.SamplingParams, qwen_tok, ps, prompt_cfg["options"]),
        C.run_free(llm, fake_vllm.SamplingParams, ps, greedy=True),
        C.run_free(llm, fake_vllm.SamplingParams, ps, greedy=False, k=2, seeds=[0, 1]),
    ):
        for r in rows:
            produced |= set(r)

    missing = produced - set(R.FIELDS) - {"model", "revision", "foundation"}
    assert not missing, f"these columns would be silently dropped by DictWriter: {sorted(missing)}"


# =======================================================================================
# Full run
# =======================================================================================


def test_run_model_writes_expected_row_count(harness, prompt_cfg, items, args_ns, tmp_path):
    meta = {i: "Care" for i, _ in items}
    use = items[:6]
    harness.run_model(ENTRY, prompt_cfg, use, meta, args_ns)

    out = tmp_path / "Qwen__Qwen2.5-0.5B-Instruct.csv"
    assert out.exists()
    rows = list(csv.DictReader(out.open(encoding="utf-8")))
    n, k = len(use), args_ns.k
    # every condition contributes n rows except `sampled`, which contributes n*k
    n_single = len(EXPECTED_CONDITIONS[args_ns.harness]) - 1
    assert len(rows) == n * n_single + n * k, (
        f"harness {args_ns.harness}: expected {n * n_single + n * k}, got {len(rows)}")


def test_every_condition_present_for_every_item(harness, prompt_cfg, items, args_ns,
                                                tmp_path):
    meta = {i: "Care" for i, _ in items}
    use = items[:5]
    harness.run_model(ENTRY, prompt_cfg, use, meta, args_ns)
    rows = list(csv.DictReader(
        (tmp_path / "Qwen__Qwen2.5-0.5B-Instruct.csv").open(encoding="utf-8")))
    by_item: dict[str, set] = {}
    for r in rows:
        by_item.setdefault(r["item_id"], set()).add(r["condition"])
    assert len(by_item) == len(use)
    for item, conds in by_item.items():
        assert conds == EXPECTED_CONDITIONS[args_ns.harness], f"item {item}: {conds}"


def test_prompt_hash_identical_across_conditions_in_output(harness, prompt_cfg, items,
                                                           args_ns, tmp_path):
    """THE INVARIANT, asserted against the file that will actually be analysed."""
    meta = {i: "Care" for i, _ in items}
    harness.run_model(ENTRY, prompt_cfg, items[:5], meta, args_ns)
    rows = list(csv.DictReader(
        (tmp_path / "Qwen__Qwen2.5-0.5B-Instruct.csv").open(encoding="utf-8")))
    by_item: dict[str, set] = {}
    for r in rows:
        by_item.setdefault(r["item_id"], set()).add(r["prompt_sha"])
    for item, shas in by_item.items():
        assert len(shas) == 1, f"item {item} was scored under {len(shas)} different prompts"


def test_no_column_is_entirely_empty(harness, prompt_cfg, items, args_ns, tmp_path):
    """An always-empty column means a field is never populated — usually a typo'd key."""
    meta = {i: "Care" for i, _ in items}
    harness.run_model(ENTRY, prompt_cfg, items[:5], meta, args_ns)
    rows = list(csv.DictReader(
        (tmp_path / "Qwen__Qwen2.5-0.5B-Instruct.csv").open(encoding="utf-8")))
    # Each exemption needs a REASON. A blanket exemption list would let this test pass while
    # a real column silently stopped being written, which is the failure it exists to catch.
    exempt = {
        "seed",                     # only sampled rows carry one
        "raw_output",               # probability readouts generate no text
        "score_alt_normalisation",  # string arms only
        "token_boundary_clean",
        "emitted_token_id",
        "degenerate_options",       # populated ONLY on failure — empty is the healthy state
    }
    # Harness-specific columns. FIELDS is shared, so each harness leaves the other's
    # diagnostics blank; that is correct, and stating it here keeps the guard sharp for
    # every remaining column.
    exempt |= {"v1": {"surface_form", "boundary_shift"},   # v2-only diagnostics
               "v2": {"label_position"}}[args_ns.harness]  # v1 scanned positions; v2 does not
    for col in rows[0]:
        if col in exempt:
            continue
        assert any(r[col] not in ("", None) for r in rows), (
            f"harness {args_ns.harness}: column {col!r} is always empty")


def test_foundation_is_joined_onto_every_row(harness, prompt_cfg, items, args_ns, tmp_path):
    meta = {i: ("Care" if i % 2 else "Sanctity") for i, _ in items}
    harness.run_model(ENTRY, prompt_cfg, items[:6], meta, args_ns)
    rows = list(csv.DictReader(
        (tmp_path / "Qwen__Qwen2.5-0.5B-Instruct.csv").open(encoding="utf-8")))
    assert all(r["foundation"] in {"Care", "Sanctity"} for r in rows)


def test_sampled_replicates_are_distinguishable(harness, prompt_cfg, items, args_ns,
                                                tmp_path):
    meta = {i: "Care" for i, _ in items}
    harness.run_model(ENTRY, prompt_cfg, items[:3], meta, args_ns)
    rows = [r for r in csv.DictReader(
        (tmp_path / "Qwen__Qwen2.5-0.5B-Instruct.csv").open(encoding="utf-8"))
        if r["condition"] == "sampled"]
    reps = {r["replicate"] for r in rows}
    assert reps == {str(i) for i in range(args_ns.k)}
    assert all(r["seed"] != "" for r in rows), "sampled rows must record their seed"


# =======================================================================================
# Manifest — the reproducibility contract
# =======================================================================================


def test_manifest_records_everything_needed_to_reproduce(harness, prompt_cfg, items,
                                                         args_ns, tmp_path):
    meta = {i: "Care" for i, _ in items}
    harness.run_model(ENTRY, prompt_cfg, items[:3], meta, args_ns)
    m = json.loads((tmp_path / "Qwen__Qwen2.5-0.5B-Instruct.manifest.json")
                   .read_text(encoding="utf-8"))
    for key in ("model", "revision", "prompt_sha_first", "prompt_config_sha",
                "items_file_sha", "option_label_token_ids", "packages", "python",
                "vllm_args", "seeds", "k_samples", "conditions"):
        assert key in m, f"manifest missing {key!r}"
    assert m["revision"] == PINNED_REV, "pinned revision must be recorded"
    assert set(m["conditions"]) == EXPECTED_CONDITIONS[args_ns.harness]
    assert m["harness"] == args_ns.harness
    # D1 guard: the harness must record how the ENGINE tokenized the prompt, not just how the
    # local tokenizer did. v1 conflated the two and silently mis-placed the option boundary.
    assert "tokenization" in m and "engine_n_tokens" in m["tokenization"]
    assert len(m["option_label_token_ids"]) == 5
    # Integrity counters the analysis depends on
    for key in ("n_rows", "parse_failed", "refusals", "scan_parsed"):
        assert key in m, f"manifest missing integrity counter {key!r}"


def test_manifest_is_written_even_with_awkward_yaml_types(harness, prompt_cfg, items,
                                                          args_ns, tmp_path):
    """Regression: config/prompt.yaml has `decided: 2026-08-07`, which yaml.safe_load turns
    into a datetime.date. json.dumps refuses it, and the manifest write happens AFTER all
    four conditions — so on the pod this destroyed a full model's inference before anyone
    saw an error. The manifest is now serialise-checked before the GPU work starts."""
    import datetime

    cfg = dict(prompt_cfg)
    cfg["decided"] = datetime.date(2026, 8, 7)
    cfg["some_time"] = datetime.datetime(2026, 8, 7, 12, 0)
    harness.run_model(ENTRY, cfg, items[:2], {i: "Care" for i, _ in items}, args_ns)
    m = json.loads((tmp_path / "Qwen__Qwen2.5-0.5B-Instruct.manifest.json")
                   .read_text(encoding="utf-8"))
    assert m["prompt_config_sha"]


def test_manifest_revision_is_passed_to_the_model_loader(harness, prompt_cfg, items,
                                                         args_ns, monkeypatch):
    """A pinned revision that never reaches vLLM is worse than none — it documents a
    guarantee the run did not actually make."""
    seen = {}
    import vllm as fake

    orig = fake.LLM

    class Spy(orig):
        def __init__(self, model, revision=None, **kw):
            seen["model"], seen["revision"] = model, revision
            super().__init__(model, revision=revision, **kw)

    monkeypatch.setattr(fake, "LLM", Spy)
    harness.run_model(ENTRY, prompt_cfg, items[:2], {i: "Care" for i, _ in items}, args_ns)
    assert seen["revision"] == PINNED_REV
    assert seen["model"] == ENTRY["id"]


def test_every_pinned_revision_in_the_roster_actually_resolves(repo):
    """A bad SHA would only surface on the pod, after paying to start a download. Check all
    20 up front. Network test; skipped offline."""
    import urllib.error
    import urllib.request

    import run_experiment as R

    _, roster, _, _ = R.load_cfg()
    bad = []
    for m in roster["primary"] + roster["open_fallback"]:
        url = f"https://huggingface.co/api/models/{m['id']}/revision/{m['revision']}"
        try:
            with urllib.request.urlopen(url, timeout=30) as resp:
                if resp.status != 200:
                    bad.append((m["id"], m["revision"], resp.status))
        except urllib.error.HTTPError as e:
            if e.code in (401, 403):
                continue  # gated without a token — the SHA itself is not the problem
            bad.append((m["id"], m["revision"], e.code))
        except Exception as e:  # pragma: no cover
            pytest.skip(f"network unavailable: {type(e).__name__}")
    assert not bad, f"pinned revisions that do not resolve: {bad}"


# =======================================================================================
# Robustness: crashes must cost one model, not the run
# =======================================================================================


def test_checkpointing_skips_completed_models(harness, prompt_cfg, items, args_ns,
                                              tmp_path):
    meta = {i: "Care" for i, _ in items}
    harness.run_model(ENTRY, prompt_cfg, items[:3], meta, args_ns)
    first = (tmp_path / "Qwen__Qwen2.5-0.5B-Instruct.csv").read_text(encoding="utf-8")
    harness.run_model(ENTRY, prompt_cfg, items[:9], meta, args_ns)  # would differ if rerun
    assert (tmp_path / "Qwen__Qwen2.5-0.5B-Instruct.csv").read_text(encoding="utf-8") == first


def test_force_overrides_checkpoint(harness, prompt_cfg, items, args_ns, tmp_path):
    meta = {i: "Care" for i, _ in items}
    harness.run_model(ENTRY, prompt_cfg, items[:3], meta, args_ns)
    n1 = len(list(csv.DictReader(
        (tmp_path / "Qwen__Qwen2.5-0.5B-Instruct.csv").open(encoding="utf-8"))))
    args_ns.force = True
    harness.run_model(ENTRY, prompt_cfg, items[:6], meta, args_ns)
    n2 = len(list(csv.DictReader(
        (tmp_path / "Qwen__Qwen2.5-0.5B-Instruct.csv").open(encoding="utf-8"))))
    assert n2 > n1


def test_limit_items_is_honoured(harness, prompt_cfg, items, args_ns, tmp_path):
    meta = {i: "Care" for i, _ in items}
    harness.run_model(ENTRY, prompt_cfg, items[:10], meta, args_ns)
    rows = list(csv.DictReader(
        (tmp_path / "Qwen__Qwen2.5-0.5B-Instruct.csv").open(encoding="utf-8")))
    assert len({r["item_id"] for r in rows}) == 10


# =======================================================================================
# Config integrity — catches a broken repo before it costs GPU time
# =======================================================================================


def test_real_config_files_load_and_are_consistent(repo):
    import run_experiment as R

    prompt_cfg, roster, its, meta = R.load_cfg()
    assert len(its) == 116
    assert len(meta) == 116
    assert {i for i, _ in its} == set(meta)
    assert set(prompt_cfg["options"]) == {0, 1, 2, 3, 4}
    assert "{{QUESTION_CONTENT_PLACEHOLDER}}" in prompt_cfg["user_template"]
    assert prompt_cfg["system"]


def test_roster_is_well_formed(repo):
    import run_experiment as R

    _, roster, _, _ = R.load_cfg()
    prim = roster["primary"]
    assert len(prim) == 30, "roster is N=30 after the Phase-2 expansion"
    ids = [m["id"] for m in prim]
    assert len(set(ids)) == len(ids), "duplicate model in roster"
    for m in prim:
        assert m["revision"] and len(m["revision"]) == 40, f"{m['id']} revision not pinned"
        assert m["family"]
    fams = {m["family"] for m in prim}
    assert len(fams) >= 12, f"only {len(fams)} families — diversity argument weakens"

    # The 14B cap was lifted DELIBERATELY in Phase 2: P5/P6 need within-family scale
    # variation, and a cap of 14B makes Kirgis's capability claim untestable. The cap is
    # replaced by the structure that replaced it — assert the ladders exist, since they are
    # what those predictions rest on.
    def ladder(fam):
        return sorted(m["params_b"] for m in prim if m["family"] == fam)

    qwen, llama = ladder("qwen"), ladder("llama")
    assert len(qwen) >= 7 and qwen[0] <= 0.5 and qwen[-1] >= 70, qwen
    assert len(llama) >= 4 and llama[0] <= 1.0 and llama[-1] >= 70, llama
    # Two decades of scale on each ladder, or a log-parameter slope is fitted on nothing.
    for name, l in (("qwen", qwen), ("llama", llama)):
        assert l[-1] / l[0] >= 50, f"{name} ladder spans too little scale: {l}"


def test_foundation_counts_match_the_prespecified_instrument(repo):
    import run_experiment as R

    _, _, _, meta = R.load_cfg()
    counts: dict[str, int] = {}
    for f in meta.values():
        counts[f] = counts.get(f, 0) + 1
    assert counts == {"Authority": 17, "Care": 16, "Fairness": 17, "Liberty": 17,
                      "Loyalty": 16, "Sanctity": 17, "Social Norms": 16}
