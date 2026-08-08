"""Append the Phase-2 roster additions to config/models.yaml, with pinned revision SHAs.

ADDITIVE ONLY: existing entries are never touched (their pinned revisions back the Phase-1
manifests). Additions are pinned 2026-08-08, BEFORE any of their data is collected — no
cherry-picking after results.

Selection rationale (METHODOLOGY_REVIEW.md F3/F4):
- four small open models push N toward 30 (B2: interior-band accuracy 0.86 -> 0.94)
- four 24-32B models extend the size gradient and fit a 96 GB card in bf16
- two 70B-class models complete the within-family ladders (Llama-3.1: 1->70B,
  Qwen2.5: 0.5->72B) and carry the registered scale predictions P5/P6; they need a
  B200-class card (bf16 ~141-146 GB)

    python scripts/add_phase2_models.py
"""

from __future__ import annotations

import json
import sys
import urllib.request
from pathlib import Path

try:
    import truststore

    truststore.inject_into_ssl()
except Exception:
    pass

REPO = Path(__file__).resolve().parent.parent
YAML = REPO / "config" / "models.yaml"

#            family     id                                        params_b  note
ADDITIONS = [
    ("qwen",    "Qwen/Qwen2-7B-Instruct",                 7.6,  "earlier Qwen generation (recipe contrast)"),
    ("phi",     "microsoft/Phi-3.5-mini-instruct",        3.8,  "Phi lineage midpoint"),
    ("zephyr",  "HuggingFaceH4/zephyr-7b-beta",           7.2,  "distinct post-training recipe (DPO)"),
    ("falcon",  "tiiuae/Falcon3-7B-Instruct",             7.5,  "distinct family, TII"),
    ("mistral", "mistralai/Mistral-Small-24B-Instruct-2501", 23.6, "size gradient, 96GB card"),
    ("gemma",   "google/gemma-2-27b-it",                  27.2, "size gradient (gated), 96GB card"),
    ("qwen",    "Qwen/Qwen2.5-32B-Instruct",              32.8, "Qwen ladder point, 96GB card"),
    ("olmo",    "allenai/OLMo-2-0325-32B-Instruct",       32.2, "fully open at scale, 96GB card"),
    ("llama",   "meta-llama/Llama-3.1-70B-Instruct",      70.6, "SCALE LADDER (gated); B200-class card"),
    ("qwen",    "Qwen/Qwen2.5-72B-Instruct",              72.7, "SCALE LADDER; B200-class card"),
]


def fetch(mid: str) -> dict:
    url = f"https://huggingface.co/api/models/{mid}"
    with urllib.request.urlopen(url, timeout=30) as r:
        return json.load(r)


def main() -> int:
    """Append the Phase-2 additions. MUTATES config/models.yaml — requires --write.

    Same guard, same reason as `build_model_roster.py`: the `--help` sweep in
    `tests/test_scripts_are_valid.py` executed every argparse-less script in `scripts/`, so
    this one ran on every `pytest` invocation. It is additive and idempotent, so on its own it
    did no harm — but it ran alphabetically *before* `build_model_roster.py`, which then
    regenerated the file from a hard-coded N=20 list and destroyed the additions. Making both
    explicit removes the interaction entirely.
    """
    import argparse

    ap = argparse.ArgumentParser(description="Append Phase-2 models to config/models.yaml.")
    ap.add_argument("--write", action="store_true",
                    help="actually modify config/models.yaml (required)")
    args = ap.parse_args()

    text = YAML.read_text(encoding="utf-8")
    if not args.write:
        present = sum(1 for _, mid, _, _ in ADDITIONS if f"id: {mid}\n" in text)
        print(f"DRY RUN — nothing written. {present}/{len(ADDITIONS)} Phase-2 models are "
              f"already in the roster. Pass --write to add the rest.")
        return 0
    rows = []
    print("verifying and pinning:")
    for family, mid, params, note in ADDITIONS:
        if f"id: {mid}\n" in text:
            print(f"  [skip] {mid} — already in roster")
            continue
        try:
            meta = fetch(mid)
        except Exception as exc:
            print(f"  [FAIL] {mid}: {type(exc).__name__}: {exc}", file=sys.stderr)
            return 1
        sha = meta.get("sha")
        gated = bool(meta.get("gated"))
        if not sha or len(sha) != 40:
            print(f"  [FAIL] {mid}: no usable sha ({sha!r})", file=sys.stderr)
            return 1
        rows.append((family, mid, params, note, sha, gated))
        print(f"  {mid:<44} {sha}  gated={gated}")

    if not rows:
        print("nothing to add")
        return 0

    # append inside the `primary:` list — i.e. before the open_fallback section
    lines = [
        "  # ---- Phase-2 additions, pinned 2026-08-08 BEFORE any of their data was",
        "  # collected (no cherry-picking after results). Selection rationale in",
        "  # METHODOLOGY_REVIEW.md F3/F4. 70B-class entries exceed every card below a",
        "  # B200; plan_memory() skips them automatically on smaller GPUs.",
    ]
    for family, mid, params, note, sha, gated in rows:
        lines += [
            f"  - id: {mid}",
            f"    family: {family}",
            f"    params_b: {params}",
            f"    revision: {sha}",
            f"    gated: {str(gated).lower()}",
            f"    note: {json.dumps(note)}",   # quoted: a colon in a bare
                                              # YAML scalar is a parse error
        ]
    block = "\n".join(lines) + "\n"

    marker = "# Swap in for the 5 gated models if approvals fail"
    if marker in text:
        text = text.replace(marker, block + "\n" + marker)
    else:
        text = text.rstrip() + "\n" + block
    YAML.write_text(text, encoding="utf-8")

    import yaml

    cfg = yaml.safe_load(YAML.read_text(encoding="utf-8"))
    fams: dict[str, int] = {}
    for m in cfg["primary"]:
        fams[m["family"]] = fams.get(m["family"], 0) + 1
    print(f"\nroster now N = {len(cfg['primary'])}, families = {len(fams)}: {fams}")
    assert all(len(m.get("revision", "")) == 40 for m in cfg["primary"])
    print("all revisions pinned; existing entries untouched")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
