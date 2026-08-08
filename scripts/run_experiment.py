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

REPO = Path(__file__).resolve().parent.parent
RAW = REPO / "results" / "raw"

FIELDS = [
    "model", "revision", "item_id", "foundation", "condition", "replicate",
    "score", "score_alt_normalisation", "logprob_mass", "n_options_found",
    "refusal", "parse_failed", "parse_strategy", "token_boundary_clean", "emitted_token_id",
    "label_position",
    "seed", "prompt_sha", "raw_output",
]


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


def plan_memory(params_b: float, vram_gib: float | None,
                default_util: float) -> tuple[float, str]:
    """Decide gpu_memory_utilization, or refuse before anything is downloaded.

    Qwen2.5-14B is ~28.8 GiB in bf16 and does NOT fit a 32 GiB card; OLMo-2-13B at
    ~28.2 GiB fits only at high utilisation. Discovering that as an OOM *after* pulling
    28 GB of weights wastes ten minutes and reads like a mysterious crash. So: estimate,
    decide, and say so up front.

    fp8 is deliberately NOT used as an escape hatch. Quantising only the two largest models
    would make numerics differ by model, which is a confound in a study whose entire subject
    is measurement artifacts.
    """
    weights = params_b * 2 * 1.03      # bf16 + embedding/lm_head overhead
    kv_headroom = 1.5                  # short prompts, small batch
    if vram_gib is None:
        return default_util, "no GPU detected — using default utilisation"
    need = weights + kv_headroom
    if need < vram_gib * default_util:
        return default_util, "fits comfortably"
    if need < vram_gib * 0.95:
        return 0.95, f"tight ({need:.1f} of {vram_gib:.1f} GiB) — raising utilisation to 0.95"
    return -1.0, (
        f"WILL NOT FIT: needs ~{need:.1f} GiB, card has {vram_gib:.1f} GiB. "
        f"Run this model on a larger GPU (attach the same network volume to an "
        f"RTX PRO 6000 pod) rather than quantising it — quantising only the largest "
        f"models would make numerics differ by model, a confound in this study.")


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
    util, why = plan_memory(entry.get("params_b", 0.0), gpu_vram_gib(), args.gpu_util)
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

    want = set(args.conditions) if args.conditions else {"label", "string", "greedy", "sampled"}

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
                      "enforce_eager": args.eager, "dtype": "bfloat16"},
        "seeds": list(range(args.k)),
    }
    json.dumps(manifest_static, default=str)  # fail fast, before the GPU work

    llm = LLM(model=mid, revision=rev, max_model_len=args.max_model_len,
              gpu_memory_utilization=util, enforce_eager=args.eager,
              dtype="bfloat16", trust_remote_code=trc)

    rows: list[dict] = []
    if "label" in want:
        rows += C.run_label(llm, SamplingParams, prompts, tok_ids)
        print(f"  label    done ({len(rows)} rows)")
    if "string" in want:
        n = len(rows)
        rows += C.run_string(llm, SamplingParams, tok, prompts, prompt_cfg["options"],
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
        r["foundation"] = meta.get(r["item_id"], "")

    RAW.mkdir(parents=True, exist_ok=True)
    with out_csv.open("w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=FIELDS, extrasaction="ignore")
        w.writeheader()
        w.writerows(rows)

    manifest = dict(manifest_static)
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
