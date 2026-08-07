"""Pod pre-flight. Run this FIRST, every session, before anything expensive.

Thirty seconds of checks that between them catch every failure we have actually hit or can
foresee: missing env vars, a broken HF token, unresolvable pinned revisions, models that
cannot fit the card, a tokenizer with no chat template, a prompt that does not render.

    source /workspace/env.sh && python scripts/preflight.py

Exit code 0 = safe to start the run. Non-zero = fix before spending GPU time.
"""

from __future__ import annotations

import os
import sys
import urllib.error
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

OK, WARN, FAIL = "  ok  ", " warn ", " FAIL "
problems: list[str] = []
warnings: list[str] = []


def check(name: str, ok: bool, detail: str = "", fatal: bool = True,
          ok_detail: str = "") -> bool:
    """Detail explains a FAILURE, so only show it on failure; ok_detail is for values
    worth printing when things are fine (versions, sizes)."""
    tag = OK if ok else (FAIL if fatal else WARN)
    extra = ok_detail if ok else detail
    print(f"[{tag}] {name}" + (f" — {extra}" if extra else ""))
    if not ok:
        (problems if fatal else warnings).append(f"{name}: {detail}")
    return ok


def main() -> int:
    print("=" * 74)
    print("PRE-FLIGHT")
    print("=" * 74)

    # ---- environment ------------------------------------------------------------------
    print("\n## environment")
    flash = os.environ.get("VLLM_USE_FLASHINFER_SAMPLER")
    check("VLLM_USE_FLASHINFER_SAMPLER=0", flash == "0",
          f"got {flash!r} — vLLM will not start on sm_120 without this")
    hf_home = os.environ.get("HF_HOME", "")
    check("HF_HOME points at the network volume", hf_home.startswith("/workspace"),
          f"got {hf_home!r} — weights would land on ephemeral container disk", fatal=False)
    tok_len = len(os.environ.get("HF_TOKEN", ""))
    check("HF_TOKEN present", tok_len > 0,
          "empty — gated models (3x Llama, 2x Gemma) will 401. Check the RunPod secret "
          "is named with UNDERSCORES; hyphens break its template substitution", fatal=False)

    # ---- packages ---------------------------------------------------------------------
    print("\n## packages")
    try:
        import vllm
        check("vllm importable", True, ok_detail=vllm.__version__)
        check("vllm >= 0.12", tuple(int(x) for x in vllm.__version__.split(".")[:2]) >= (0, 12),
              vllm.__version__, ok_detail=vllm.__version__)
    except Exception as e:
        check("vllm importable", False, f"{type(e).__name__}: {e}")
    for mod in ("transformers", "torch", "yaml"):
        try:
            m = __import__(mod)
            check(f"{mod} importable", True, ok_detail=getattr(m, "__version__", ""))
        except Exception as e:
            check(f"{mod} importable", False, str(e))

    # ---- GPU --------------------------------------------------------------------------
    print("\n## GPU")
    import run_experiment as R

    vram = R.gpu_vram_gib()
    check("GPU visible", vram is not None, "nvidia-smi failed",
          ok_detail=f"{vram:.1f} GiB" if vram else "")
    if vram:
        try:
            import torch
            cap = torch.cuda.get_device_capability(0)
            check("torch sees the GPU", torch.cuda.is_available(), "cuda unavailable",
                  ok_detail=f"{torch.cuda.get_device_name(0)} sm_{cap[0]}{cap[1]}")
            arch = torch.cuda.get_arch_list()
            check(f"sm_{cap[0]}{cap[1]} kernels compiled in", f"sm_{cap[0]}{cap[1]}" in arch,
                  f"arch_list={arch}")
        except Exception as e:
            check("torch GPU check", False, str(e))

    # ---- config -----------------------------------------------------------------------
    print("\n## config")
    try:
        prompt_cfg, roster, items, meta = R.load_cfg()
        check("configs load", True)
        check("116 items", len(items) == 116, f"got {len(items)}", ok_detail="116")
        check("116 foundation labels", len(meta) == 116, f"got {len(meta)}")
        check("placeholder present in template",
              "{{QUESTION_CONTENT_PLACEHOLDER}}" in prompt_cfg["user_template"])
        check("5 options", set(prompt_cfg["options"]) == {0, 1, 2, 3, 4})
        check("roster is 20 models", len(roster["primary"]) == 20,
              f"got {len(roster['primary'])}")
        check("all revisions pinned",
              all(len(m.get("revision") or "") == 40 for m in roster["primary"]))
    except Exception as e:
        check("configs load", False, f"{type(e).__name__}: {e}")
        return _summary()

    # ---- memory plan ------------------------------------------------------------------
    print("\n## memory plan")
    if vram is None:
        print(f"[{WARN}] no GPU detected — memory plan cannot be computed")
    else:
        refused, tight = [], []
        for m in roster["primary"]:
            util, _ = R.plan_memory(m["params_b"], vram, 0.85)
            if util < 0:
                refused.append(m["id"])
            elif util > 0.9:
                tight.append(m["id"])
        check(f"{len(roster['primary']) - len(refused)} of {len(roster['primary'])} models "
              f"fit on this {vram:.0f} GiB card", not refused,
              f"cannot fit: {refused} — run these on an RTX PRO 6000 pod with the same "
              f"network volume attached", fatal=False)
        if tight:
            print(f"[{WARN}] tight fit, utilisation raised to 0.95: {tight}")

    # ---- revisions resolve ------------------------------------------------------------
    print("\n## pinned revisions resolve")
    bad, gated_no_token = [], []
    for m in roster["primary"]:
        url = f"https://huggingface.co/api/models/{m['id']}/revision/{m['revision']}"
        req = urllib.request.Request(url)
        if tok_len:
            req.add_header("Authorization", f"Bearer {os.environ['HF_TOKEN']}")
        try:
            with urllib.request.urlopen(req, timeout=30):
                pass
        except urllib.error.HTTPError as e:
            (gated_no_token if e.code in (401, 403) else bad).append((m["id"], e.code))
        except Exception as e:
            bad.append((m["id"], type(e).__name__))
    check("all pinned revisions resolve", not bad, f"unresolvable: {bad}",
          ok_detail=f"{len(roster['primary'])} checked")
    # NOTE: HF exposes revision METADATA for gated repos without a token, so this proves
    # the SHA exists, not that we may download the weights. Real access is only confirmed
    # when the first gated model actually loads.
    check("no gated repo returned 401/403", not gated_no_token,
          f"{gated_no_token} — request access on the HF model page, or use --fallback "
          f"for the open-only roster of 19", fatal=False)

    # ---- prompt renders ---------------------------------------------------------------
    print("\n## prompt rendering")
    try:
        import conditions as Cnd
        from transformers import AutoTokenizer

        t = AutoTokenizer.from_pretrained(roster["primary"][0]["id"],
                                          revision=roster["primary"][0]["revision"])
        check("chat template present", t.chat_template is not None)
        p = Cnd.render_prompt(t, prompt_cfg, items[0][1], items[0][0])
        check("placeholder substituted", "{{QUESTION" not in p.text)
        check("item text present", items[0][1] in p.text)
        ids = Cnd.option_token_ids(t, prompt_cfg["options"])
        check("all 5 option labels are single tokens", len(ids) == 5,
              f"only {sorted(ids)} — label scoring degraded", fatal=False,
              ok_detail=str(sorted(ids.values())))
        n = len(t.encode(p.text, add_special_tokens=False))
        check("prompt well within max_model_len", n + 96 < 1024,
              f"{n} tokens + 96 generated exceeds 1024",
              ok_detail=f"{n} tokens + 96 generated")
    except Exception as e:
        check("prompt rendering", False, f"{type(e).__name__}: {e}")

    return _summary()


def _summary() -> int:
    print("\n" + "=" * 74)
    if problems:
        print(f"BLOCKED — {len(problems)} fatal problem(s):")
        for p in problems:
            print(f"  - {p}")
    if warnings:
        print(f"{len(warnings)} warning(s):")
        for w in warnings:
            print(f"  - {w}")
    if not problems:
        print("READY — safe to start the run.")
    print("=" * 74)
    return 1 if problems else 0


if __name__ == "__main__":
    raise SystemExit(main())
