"""Run all four scoring conditions for one or more models. Pod-side entry point.

    source /workspace/env.sh
    # B4 smoke test -- one model, ten items, all four conditions
    python scripts/run_experiment.py --models Qwen/Qwen2.5-1.5B-Instruct --limit-items 10

    # B5 confirmatory -- whole roster, all items, delete weights as we go
    python scripts/run_experiment.py --all --purge-weights

Writes, per model:
    results/raw/<slug>.csv       long form: one row per item x condition x replicate
    results/raw/<slug>.manifest.json

Checkpointed: a model whose CSV already exists is skipped, so a crash costs one model.
"""

from __future__ import annotations

import argparse
import csv
import json
import os
import platform
import shutil
import subprocess
import sys
import time
from pathlib import Path

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parent))
import conditions as C  # noqa: E402
import conditions_v2 as C2  # noqa: E402

REPO = Path(__file__).resolve().parent.parent
RAW = REPO / "results" / "raw"

FIELDS = [
    "model", "revision", "harness", "item_id", "foundation", "condition", "replicate",
    "score", "score_alt_normalisation", "logprob_mass", "n_options_found",
    "refusal", "parse_failed", "parse_strategy", "token_boundary_clean", "emitted_token_id",
    "label_position",
    "surface_form", "boundary_shift", "degenerate_options",
    "seed", "prompt_sha", "raw_output",
]

# v1 kept for reproducibility of the committed Phase-1 data, NOT as a live option: its
# manifests pin these code paths, and rewriting them in place would make the archived results
# unreproducible. New collection should use v2. See conditions_v2.py for what changed.
V1_CONDITIONS = ("label", "string", "greedy", "sampled")
V2_CONDITIONS = ("label", "string_line", "string_bare", "greedy", "sampled")
V2_OPTIONAL = ("cloze",)   # prompt-varying; excluded from the primary variance ratio


def tokenization_probe(llm, sampling_params_cls, tok, prompt) -> dict:
    """Ask the ENGINE how it tokenizes the prompt, and compare against the local tokenizer.

    This is the measurement that would have caught v1's D1 defect on the day it happened, and
    it costs one sequence. v1 computed the option boundary from `local.encode(text,
    add_special_tokens=False)` and applied that index to ids vLLM returned; on 12 of 30 roster
    models those differ by one, because the chat template already emits BOS and the tokenizer
    adds a second. v2 never uses the local count, so this is pure diagnostics — but it is the
    only thing that will settle WHY internlm2_5-7b-chat lost its entire v1 string arm with
    `n_options_found = 0`, which the local-only evidence could not explain.
    """
    sp = sampling_params_cls(temperature=0.0, max_tokens=1, prompt_logprobs=0)
    out = llm.generate([prompt.text], sp)[0]
    engine_n = len(out.prompt_token_ids)
    local_no = len(tok.encode(prompt.text, add_special_tokens=False))
    local_yes = len(tok.encode(prompt.text, add_special_tokens=True))
    d = {"engine_n_tokens": engine_n, "local_n_no_specials": local_no,
         "local_n_with_specials": local_yes,
         "engine_minus_local_no_specials": engine_n - local_no,
         "v1_boundary_was_correct": engine_n == local_no}
    if not d["v1_boundary_was_correct"]:
        print(f"  [tokenization] engine={engine_n} vs local(no-specials)={local_no} "
              f"-> v1's option boundary was off by {engine_n - local_no} on this model")
    return d


def slug(model_id: str) -> str:
    return model_id.replace("/", "__")


def load_cfg():
    with (REPO / "config" / "prompt.yaml").open(encoding="utf-8") as fh:
        prompt = yaml.safe_load(fh)
    with (REPO / "config" / "models.yaml").open(encoding="utf-8") as fh:
        models = yaml.safe_load(fh)
    items, meta = [], {}
    with (REPO / "data" / "mfv_116.csv").open(newline="", encoding="utf-8") as fh:
        for r in csv.DictReader(fh):
            items.append((int(r["questionnaire_item_id"]), r["question_content"]))
    with (REPO / "data" / "mfv_116_meta.csv").open(newline="", encoding="utf-8") as fh:
        for r in csv.DictReader(fh):
            meta[int(r["questionnaire_item_id"])] = r["foundation"]
    return prompt, models, items, meta


def gpu_vram_gib() -> float | None:
    """Total VRAM in GiB, or None if no GPU is visible."""
    try:
        r = subprocess.run(
            ["nvidia-smi", "--query-gpu=memory.total", "--format=csv,noheader,nounits"],
            capture_output=True, text=True, timeout=10)
        if r.returncode == 0 and r.stdout.strip():
            return float(r.stdout.strip().splitlines()[0]) / 1024.0
    except Exception:
        pass
    return None


def gpu_count() -> int:
    """How many GPUs nvidia-smi can see. 1 if it cannot tell.

    `gpu_vram_gib()` deliberately returns only the FIRST card's memory, because vLLM's
    `gpu_memory_utilization` is a PER-GPU fraction. Capacity therefore has two components and
    conflating them is how a 245 GB model gets planned against one 96 GB card.
    """
    try:
        r = subprocess.run(
            ["nvidia-smi", "--query-gpu=memory.total", "--format=csv,noheader,nounits"],
            capture_output=True, text=True, timeout=10)
        if r.returncode == 0 and r.stdout.strip():
            return len(r.stdout.strip().splitlines())
    except Exception:
        pass
    return 1


def usable_tp_size(n_gpus: int) -> int:
    """Largest power of two <= n_gpus.

    vLLM shards attention heads across the tensor-parallel group, so the group size must
    divide the head count. Head counts are powers of two on every model in this roster, and
    an odd tensor_parallel_size (a 3-GPU pod, say) fails at load time after the weights are
    already on disk. Clamping is cheaper than that error.
    """
    tp = 1
    while tp * 2 <= max(1, n_gpus):
        tp *= 2
    return tp


def plan_memory(params_b: float, vram_gib: float | None,
                default_util: float, n_gpus: int = 1) -> tuple[float, str]:
    """Decide gpu_memory_utilization, or refuse before anything is downloaded.

    Qwen2.5-14B is ~28.8 GiB in bf16 and does NOT fit a 32 GiB card; OLMo-2-13B at
    ~28.2 GiB fits only at high utilisation. Discovering that as an OOM *after* pulling
    28 GB of weights wastes ten minutes and reads like a mysterious crash. So: estimate,
    decide, and say so up front.

    fp8 is deliberately NOT used as an escape hatch. Quantising only the two largest models
    would make numerics differ by model, which is a confound in a study whose entire subject
    is measurement artifacts.

    Tensor parallelism shards the WEIGHTS across the group but the KV cache and activation
    workspace are needed on every rank, so the per-GPU requirement is weights/n + headroom,
    not total/n. `vram_gib` is per-GPU throughout, because that is what vLLM's
    `gpu_memory_utilization` is a fraction of.
    """
    weights = params_b * 2 * 1.03      # bf16 + embedding/lm_head overhead

    # KV-cache allowance MUST scale with model size. The original fixed 1.5 GiB was
    # calibrated on <=14B models and is meaningless at 70B+: KV bytes per token scale with
    # layers x kv_heads x head_dim, so a 72B model needs roughly an order of magnitude more
    # cache than a 7B one for the same batch.
    #
    # Concretely, the bug this fixes: Qwen2.5-72B on a 180 GiB B200 has 149.8 GiB of weights.
    # need = 149.8 + 1.5 = 151.3 < 179.1*0.85 = 152.2, so the old code returned "fits
    # comfortably" at util 0.85 -- leaving 2.4 GiB for KV cache. vLLM would either refuse to
    # allocate cache blocks or run one sequence at a time, AFTER downloading 145 GB.
    #
    # The scaling applies only to weights ABOVE 30 GiB, and that threshold is empirical, not
    # aesthetic. A first attempt used a flat 8% of total weights; it refused
    # OLMo-2-13B-Instruct on the 32 GiB card -- a model that had demonstrably completed all
    # four conditions on that exact card the night before. A planner that refuses a
    # configuration already observed to work is producing false negatives, so the formula was
    # wrong, not the model. Anchoring the scaling above 30 GiB keeps every previously
    # VALIDATED verdict intact (the 1.5 GiB floor still binds for the whole <=14B tier) while
    # still forcing the 70B+ tier to util 0.95.
    #
    # 10% is a safety margin, not a prediction of actual KV usage -- real usage depends on
    # kv_heads and GQA grouping, which vary by model. Erring high is cheap here: the cost of
    # over-reserving is a slightly smaller batch, the cost of under-reserving is an OOM after
    # a 145 GB download.
    kv_headroom = max(1.5, 0.10 * max(0.0, weights - 30.0))
    if vram_gib is None:
        return default_util, "no GPU detected — using default utilisation"
    n_gpus = max(1, int(n_gpus))
    need = weights / n_gpus + kv_headroom
    across = f" across {n_gpus} GPUs" if n_gpus > 1 else ""
    if need < vram_gib * default_util:
        return default_util, f"fits comfortably{across}"
    if need < vram_gib * 0.95:
        return 0.95, (f"tight ({need:.1f} of {vram_gib:.1f} GiB per GPU{across}) — "
                      f"raising utilisation to 0.95")
    # How many GPUs of this size WOULD do it? Actionable beats "does not fit".
    want = 1
    while want < 64 and (weights / want + kv_headroom) >= vram_gib * 0.95:
        want *= 2
    return -1.0, (
        f"WILL NOT FIT: needs ~{need:.1f} GiB per GPU{across}, card has {vram_gib:.1f} GiB. "
        f"~{weights:.0f} GiB of bf16 weights needs {want}x this card "
        f"(--tensor-parallel-size {want}). Use more or larger GPUs rather than quantising — "
        f"quantising only the largest models would make numerics differ by model, a confound "
        f"in this study.")


def _gpu_name() -> str:
    """Best-effort. Absent on the dev laptop; must not emit noise or raise there."""
    try:
        r = subprocess.run(
            ["nvidia-smi", "--query-gpu=name", "--format=csv,noheader"],
            capture_output=True, text=True, timeout=10)
        return r.stdout.strip() if r.returncode == 0 else ""
    except Exception:
        return ""


def pkg_versions() -> dict:
    out = {}
    for m in ("vllm", "transformers", "torch"):
        try:
            out[m] = __import__(m).__version__
        except Exception:
            out[m] = None
    return out


def run_model(entry: dict, prompt_cfg, items, meta, args) -> None:
    from transformers import AutoTokenizer
    from vllm import LLM, SamplingParams

    mid, rev = entry["id"], entry.get("revision")
    out_csv = RAW / f"{slug(mid)}{args.suffix}.csv"
    if out_csv.exists() and not args.force:
        print(f"[skip] {mid} — already done")
        return

    print(f"\n{'='*70}\n{mid}  (revision {rev})\n{'='*70}")
    t0 = time.time()

    # PRE-FLIGHT: decide memory before downloading tens of GB.
    n_gpus = usable_tp_size(gpu_count())
    tp = args.tensor_parallel_size or n_gpus
    util, why = plan_memory(entry.get("params_b", 0.0), gpu_vram_gib(), args.gpu_util,
                            n_gpus=tp)
    if entry.get("gpu_util_override"):
        util = float(entry["gpu_util_override"])
        why = (f"per-model override: utilisation {util} "
               f"(estimated need was {entry.get('params_b',0)*2*1.03+1.5:.1f} GiB)")
    print(f"  memory: {why}")
    if util < 0:
        (RAW / f"{slug(mid)}.SKIPPED.txt").write_text(why + "\n", encoding="utf-8")
        print(f"  [skip] {mid} — insufficient VRAM, nothing downloaded")
        return

    trc = bool(entry.get("trust_remote_code"))
    if trc:
        print(f"  !! trust_remote_code=True — this EXECUTES code from the model repo. "
              f"Pinned to revision {rev}, on a disposable pod.")
    tok = AutoTokenizer.from_pretrained(mid, revision=rev, trust_remote_code=trc)

    prompts = [C.render_prompt(tok, prompt_cfg, q, i) for i, q in items]

    # ---- THE INVARIANT ----------------------------------------------------------------
    # Every condition below is handed exactly these Prompt objects. Recording the hash set
    # here is what lets the write-up assert that scoring method was isolated with the prompt
    # held constant, rather than merely claiming it.
    shas = sorted({p.sha256 for p in prompts})
    assert len(shas) == len(prompts), "prompt hash collision — items are not distinct"
    print(f"  {len(prompts)} distinct prompts; first sha {prompts[0].sha256}")

    default_conditions = set(V1_CONDITIONS if args.harness == "v1" else V2_CONDITIONS)
    if args.harness == "v2" and args.cloze:
        default_conditions |= set(V2_OPTIONAL)
    want = set(args.conditions) if args.conditions else default_conditions

    # The cloze arm CANNOT share the prompt — "textbook cloze" means the options are not
    # displayed, which is a different prompt by definition. It is therefore rendered
    # separately, recorded with its own prompt_sha so the difference is visible in the data,
    # and excluded from the primary variance ratio. Putting a prompt effect inside a number
    # defined as a method effect is the exact error this project audits Kirgis for.
    prompts_cloze = []
    if "cloze" in want:
        if "user_template_cloze" not in prompt_cfg:
            raise SystemExit("cloze requested but config/prompt.yaml has no user_template_cloze")
        cloze_cfg = dict(prompt_cfg, user_template=prompt_cfg["user_template_cloze"])
        prompts_cloze = [C.render_prompt(tok, cloze_cfg, q, i) for i, q in items]
        assert prompts_cloze[0].sha256 != prompts[0].sha256, \
            "cloze prompt is identical to the primary prompt — the option list was not removed"

    tok_ids = C.option_token_ids(tok, prompt_cfg["options"])
    empty = [k for k, v in tok_ids.items() if not v]
    if empty:
        print(f"  !! WARNING: no candidate token found for option(s) {empty} — label "
              f"scoring cannot work on this tokenizer.")
    else:
        print(f"  option token candidates: "
              f"{ {k: v for k, v in sorted(tok_ids.items())} }")

    # Build and SERIALISE-CHECK the manifest skeleton BEFORE any inference. Doing this
    # afterwards once cost a full model's run: config/prompt.yaml has `decided: 2026-08-07`,
    # which YAML loads as a datetime.date that json.dumps refuses. `default=str` fixes the
    # serialisation; doing it up front means a manifest bug fails in one second rather than
    # after twenty minutes of GPU time.
    manifest_static = {
        "model": mid, "revision": rev, "family": entry.get("family"),
        "harness": args.harness,
        "params_b": entry.get("params_b"),
        "n_items": len(items), "k_samples": args.k,
        "conditions": sorted(want),
        "prompt_sha_first": prompts[0].sha256,
        "prompt_style": prompts[0].style,
        "trust_remote_code": trc,
        "prompt_sha_all_distinct": len(shas) == len(prompts),
        "prompt_config_sha": C.Prompt(
            json.dumps(prompt_cfg, sort_keys=True, default=str), -1).sha256,
        "items_file_sha": C.Prompt(
            (REPO / "data" / "mfv_116.csv").read_text(encoding="utf-8"), -1).sha256,
        "option_label_token_ids": {str(k): v for k, v in tok_ids.items()},
        "packages": pkg_versions(),
        "python": platform.python_version(),
        "gpu": _gpu_name(),
        "env": {kk: os.environ.get(kk) for kk in
                ("VLLM_USE_FLASHINFER_SAMPLER", "HF_HOME")},
        "vllm_args": {"max_model_len": args.max_model_len,
                      "gpu_memory_utilization": util,
                      "enforce_eager": args.eager, "dtype": "bfloat16",
                      "tensor_parallel_size": tp},
        "n_gpus_visible": gpu_count(),
        "seeds": list(range(args.k)),
    }
    json.dumps(manifest_static, default=str)  # fail fast, before the GPU work

    llm = LLM(model=mid, revision=rev, max_model_len=args.max_model_len,
              gpu_memory_utilization=util, enforce_eager=args.eager,
              dtype="bfloat16", trust_remote_code=trc, tensor_parallel_size=tp)

    tokdiag = tokenization_probe(llm, SamplingParams, tok, prompts[0])

    rows: list[dict] = []
    opts = prompt_cfg["options"]
    if args.harness == "v2":
        # One mechanism, three probes. `label` keeps its name because it is the same
        # estimand as v1's — the probability the answer is the digit k — read exactly
        # instead of from a truncated top-20 list at a scanned position.
        for cond, fn, ps in (("label",       C2.run_label_exact,  prompts),
                             ("string_line", C2.run_string_line,  prompts),
                             ("string_bare", C2.run_string_bare,  prompts),
                             ("cloze",       C2.run_cloze,        prompts_cloze)):
            if cond not in want:
                continue
            n = len(rows)
            rows += fn(llm, SamplingParams, ps, opts)
            new = rows[n:]
            shifted = sum(1 for r in new if r.get("boundary_shift"))
            degen = sum(1 for r in new if r.get("degenerate_options"))
            mass = [r["logprob_mass"] for r in new if r.get("logprob_mass") == r.get("logprob_mass")]
            print(f"  {cond:<12} done (+{len(new)})  mean mass="
                  f"{(sum(mass)/len(mass) if mass else float('nan')):.4f}"
                  f"  boundary_shift={shifted}  degenerate={degen}")
    else:
        if "label" in want:
            rows += C.run_label(llm, SamplingParams, prompts, tok_ids)
            print(f"  label    done ({len(rows)} rows)")
        if "string" in want:
            n = len(rows)
            rows += C.run_string(llm, SamplingParams, tok, prompts, opts,
                                 length_normalise=True)
            print(f"  string   done (+{len(rows)-n})")
    if "greedy" in want:
        n = len(rows)
        rows += C.run_free(llm, SamplingParams, prompts, greedy=True)
        print(f"  greedy   done (+{len(rows)-n})")
    if "sampled" in want:
        n = len(rows)
        rows += C.run_free(llm, SamplingParams, prompts, greedy=False, k=args.k,
                           seeds=list(range(args.k)))
        print(f"  sampled  done (+{len(rows)-n}, k={args.k})")

    for r in rows:
        r["model"] = mid
        r["revision"] = rev
        r["harness"] = args.harness
        r["foundation"] = meta.get(r["item_id"], "")

    RAW.mkdir(parents=True, exist_ok=True)
    with out_csv.open("w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=FIELDS, extrasaction="ignore")
        w.writeheader()
        w.writerows(rows)

    manifest = dict(manifest_static)
    manifest["tokenization"] = tokdiag
    manifest["boundary_shift_rows"] = sum(1 for r in rows if r.get("boundary_shift"))
    manifest["degenerate_option_rows"] = sum(1 for r in rows if r.get("degenerate_options"))
    if prompts_cloze:
        manifest["cloze_prompt_sha_first"] = prompts_cloze[0].sha256
    manifest["elapsed_s"] = round(time.time() - t0, 1)
    manifest["n_rows"] = len(rows)
    manifest["parse_failed"] = sum(1 for r in rows if r.get("parse_failed"))
    manifest["refusals"] = sum(1 for r in rows if r.get("refusal"))
    manifest["scan_parsed"] = sum(1 for r in rows if r.get("parse_strategy") == "scan")
    (RAW / f"{slug(mid)}{args.suffix}.manifest.json").write_text(
        json.dumps(manifest, indent=2, default=str), encoding="utf-8")

    fails = sum(1 for r in rows if r.get("parse_failed"))
    refus = sum(1 for r in rows if r.get("refusal"))
    print(f"  wrote {out_csv.name}  rows={len(rows)}  parse_failed={fails}  refusals={refus}"
          f"  elapsed={manifest['elapsed_s']}s")

    del llm
    try:
        import gc, torch
        gc.collect(); torch.cuda.empty_cache()
    except Exception:
        pass

    if args.purge_weights:
        # 240 GB of bf16 weights against a 200 GB volume: they cannot all be resident.
        cache = Path(os.environ.get("HF_HOME", "~/.cache/huggingface")).expanduser()
        d = cache / "hub" / f"models--{mid.replace('/', '--')}"
        if d.exists():
            shutil.rmtree(d, ignore_errors=True)
            print(f"  purged weights: {d}")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--models", nargs="*", help="explicit model ids")
    ap.add_argument("--all", action="store_true", help="whole primary roster")
    ap.add_argument("--fallback", action="store_true", help="use the open-only roster")
    ap.add_argument("--limit-items", type=int, default=0)
    ap.add_argument("--k", type=int, default=10, help="samples for the sampled condition")
    ap.add_argument("--max-model-len", type=int, default=1024)
    ap.add_argument("--gpu-util", type=float, default=0.85)
    # enforce_eager disables CUDA-graph capture. Default ON: graph capture is the part of
    # vLLM most likely to misbehave on a brand-new architecture (sm_120), and our sequences
    # are short enough that the speed cost is irrelevant. --no-eager turns it off.
    ap.add_argument("--no-eager", action="store_false", dest="eager", default=True,
                    help="enable CUDA graphs (faster, riskier on new GPUs)")
    ap.add_argument("--purge-weights", action="store_true")
    ap.add_argument("--force", action="store_true")
    ap.add_argument("--tensor-parallel-size", type=int, default=0,
                    help="shard each model across this many GPUs (0 = auto: the largest "
                         "power of two that nvidia-smi can see). Needed for models whose "
                         "bf16 weights exceed one card, e.g. Mistral-Large at ~245 GiB.")
    ap.add_argument("--harness", choices=["v1", "v2"], default="v2",
                    help="v2 (default) scores every option by forced continuation: exact p_k, "
                         "no top-k truncation, no position scan, boundary measured not assumed. "
                         "v1 reproduces the archived Phase-1 code paths and should be used only "
                         "to regenerate that data.")
    ap.add_argument("--cloze", action="store_true",
                    help="v2 only: add the exploratory cloze arm (options REMOVED from the "
                         "prompt). Prompt-varying by construction, so it is excluded from the "
                         "primary variance ratio and reported separately.")
    ap.add_argument("--conditions", nargs="*", default=None,
                    help="subset to run, e.g. --conditions label (default: all four)")
    ap.add_argument("--suffix", default="",
                    help="filename suffix, e.g. .labelfix — lets a corrected condition be "
                         "written alongside the original instead of overwriting it")
    args = ap.parse_args()

    prompt_cfg, roster, items, meta = load_cfg()
    if args.limit_items:
        items = items[: args.limit_items]

    key = "open_fallback" if args.fallback else "primary"
    entries = roster[key]
    if args.models:
        want = set(args.models)
        entries = [e for e in roster["primary"] + roster["open_fallback"]
                   if e["id"] in want]
        missing = want - {e["id"] for e in entries}
        if missing:
            sys.exit(f"not in config/models.yaml: {sorted(missing)}")
    elif not args.all:
        sys.exit("pass --models <id ...> or --all")

    print(f"{len(entries)} model(s), {len(items)} items, k={args.k}")
    for e in entries:
        try:
            run_model(e, prompt_cfg, items, meta, args)
        except Exception as exc:
            # One bad model must not cost the run. Record and continue; the write-up
            # reports achieved N, and the design simulation says what that N costs.
            print(f"  !! FAILED {e['id']}: {type(exc).__name__}: {exc}")
            (RAW / f"{slug(e['id'])}.FAILED.txt").write_text(
                f"{type(exc).__name__}: {exc}\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
