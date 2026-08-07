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
    out_csv = RAW / f"{slug(mid)}.csv"
    if out_csv.exists() and not args.force:
        print(f"[skip] {mid} — already done")
        return

    print(f"\n{'='*70}\n{mid}  (revision {rev})\n{'='*70}")
    t0 = time.time()
    tok = AutoTokenizer.from_pretrained(mid, revision=rev)

    prompts = [C.render_prompt(tok, prompt_cfg, q, i) for i, q in items]

    # ---- THE INVARIANT ----------------------------------------------------------------
    # Every condition below is handed exactly these Prompt objects. Recording the hash set
    # here is what lets the write-up assert that scoring method was isolated with the prompt
    # held constant, rather than merely claiming it.
    shas = sorted({p.sha256 for p in prompts})
    assert len(shas) == len(prompts), "prompt hash collision — items are not distinct"
    print(f"  {len(prompts)} distinct prompts; first sha {prompts[0].sha256}")

    tok_ids = C.option_token_ids(tok, prompt_cfg["options"])
    if len(tok_ids) != len(prompt_cfg["options"]):
        print(f"  !! WARNING: only {len(tok_ids)}/{len(prompt_cfg['options'])} option labels "
              f"are single tokens on this tokenizer. Label scoring is degraded here — "
              f"re-run scripts/probe_tokenization.py for this family before trusting it.")

    llm = LLM(model=mid, revision=rev, max_model_len=args.max_model_len,
              gpu_memory_utilization=args.gpu_util, enforce_eager=args.eager,
              dtype="bfloat16")

    rows: list[dict] = []
    rows += C.run_label(llm, SamplingParams, prompts, tok_ids)
    print(f"  label    done ({len(rows)} rows)")
    n = len(rows)
    rows += C.run_string(llm, SamplingParams, tok, prompts, prompt_cfg["options"],
                         length_normalise=True)
    print(f"  string   done (+{len(rows)-n})")
    n = len(rows)
    rows += C.run_free(llm, SamplingParams, prompts, greedy=True)
    print(f"  greedy   done (+{len(rows)-n})")
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

    manifest = {
        "model": mid, "revision": rev, "family": entry.get("family"),
        "params_b": entry.get("params_b"),
        "n_items": len(items), "k_samples": args.k,
        "conditions": ["label", "string", "greedy", "sampled"],
        "prompt_sha_first": prompts[0].sha256,
        "prompt_sha_all_distinct": len(shas) == len(prompts),
        "prompt_config_sha": C.Prompt(json.dumps(prompt_cfg, sort_keys=True), -1).sha256,
        "items_file_sha": C.Prompt(
            (REPO / "data" / "mfv_116.csv").read_text(encoding="utf-8"), -1).sha256,
        "option_label_token_ids": tok_ids,
        "packages": pkg_versions(),
        "python": platform.python_version(),
        "gpu": os.popen("nvidia-smi --query-gpu=name --format=csv,noheader").read().strip(),
        "env": {kk: os.environ.get(kk) for kk in
                ("VLLM_USE_FLASHINFER_SAMPLER", "HF_HOME")},
        "vllm_args": {"max_model_len": args.max_model_len,
                      "gpu_memory_utilization": args.gpu_util,
                      "enforce_eager": args.eager, "dtype": "bfloat16"},
        "seeds": list(range(args.k)),
        "elapsed_s": round(time.time() - t0, 1),
    }
    (RAW / f"{slug(mid)}.manifest.json").write_text(
        json.dumps(manifest, indent=2), encoding="utf-8")

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
    ap.add_argument("--eager", action="store_true", default=True)
    ap.add_argument("--purge-weights", action="store_true")
    ap.add_argument("--force", action="store_true")
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
