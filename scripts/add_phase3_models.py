"""Append the Phase-3 roster additions to config/models.yaml, with pinned revision SHAs.

    python scripts/add_phase3_models.py            # dry run
    python scripts/add_phase3_models.py --write

ADDITIVE ONLY, and pinned 2026-08-08 BEFORE any of their data is collected.

WHY THESE TWO, AND WHY NOT MORE. David asked for larger models. The design constraint is that
P5/P6 are *within-family* log-parameter slopes, so a large model from a family with no smaller
siblings does not extend any ladder — it only adds a point to the between-model regression.
That distinction decides the selection:

  microsoft/phi-4 (14.7B)
      The phi family currently contains three 3.8B models and nothing else, i.e. no ladder at
      all. This gives it a 3.9x span. Cheap (29 GB) and needs no new hardware.

  mistralai/Mistral-Large-Instruct-2407 (122.6B)
      Chosen over CohereLabs/c4ai-command-r-plus-08-2024 (103.8B) even though both are the
      same order of size, because mistral already has 7.2 / 8.0 / 23.6B. Adding 122.6B turns
      mistral into a THIRD real ladder with a 17x span, where command-r-plus would have been a
      lone high point. Same download cost, strictly more design value.

DELIBERATELY EXCLUDED: meta-llama/Llama-3.1-405B-Instruct. Verified to exist and it is the
obvious "go bigger" candidate, but 405.9B is ~812 GiB of bf16 weights, needs roughly 8 large
GPUs, and buys one more point on the llama ladder. The cost is not proportionate to a student
sprint with a $100 ceiling, and saying so is the honest call rather than a capability limit.

HARDWARE NOTE, and it is not small: Mistral-Large needs ~253 GiB of weights, so
tensor_parallel_size >= 4 on 96 GiB cards or >= 2 on 180 GiB cards. Run it as a separate pod
session; the rest of the roster does not need that hardware.
"""

from __future__ import annotations

import argparse
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
    ("phi",     "microsoft/phi-4",                        14.7,
     "phi ladder point -- the family had only 3.8B models"),
    ("mistral", "mistralai/Mistral-Large-Instruct-2407",  122.6,
     "SCALE LADDER: makes mistral 7.2->23.6->122.6B; needs tensor_parallel_size >= 4"),
]


def fetch(mid: str) -> dict:
    url = f"https://huggingface.co/api/models/{mid}"
    with urllib.request.urlopen(url, timeout=30) as r:
        return json.load(r)


def count_primary(text: str) -> int:
    n, in_primary = 0, False
    for line in text.splitlines():
        if line.startswith("primary:"):
            in_primary = True
        elif line and not line[0].isspace() and not line.startswith("#"):
            in_primary = False
        elif in_primary and line.startswith("  - id:"):
            n += 1
    return n


def main() -> int:
    ap = argparse.ArgumentParser(description="Append Phase-3 models to config/models.yaml.")
    ap.add_argument("--write", action="store_true",
                    help="actually modify config/models.yaml (required)")
    args = ap.parse_args()

    text = YAML.read_text(encoding="utf-8")
    todo = [a for a in ADDITIONS if f"id: {a[1]}\n" not in text]
    if not args.write:
        print(f"DRY RUN — nothing written. Roster has {count_primary(text)} primary models; "
              f"{len(todo)} of {len(ADDITIONS)} Phase-3 additions are missing.")
        for _, mid, pb, _ in todo:
            print(f"  would add {mid} ({pb}B, ~{pb * 2:.0f} GiB bf16)")
        return 0

    rows = []
    print("verifying and pinning:")
    for family, mid, params, note in todo:
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
        # Cross-check the parameter count against the Hub rather than trusting the constant
        # above. A wrong params_b silently mis-plans VRAM, which on a 122B model is the
        # difference between a working pod and an OOM after a 245 GB download.
        total = (meta.get("safetensors") or {}).get("total")
        if total:
            actual = total / 1e9
            if abs(actual - params) / params > 0.05:
                print(f"  [FAIL] {mid}: params_b={params} but Hub reports {actual:.1f}B",
                      file=sys.stderr)
                return 1
            print(f"  {mid:<44} {sha}  gated={gated}  {actual:.1f}B (Hub-confirmed)")
        else:
            print(f"  {mid:<44} {sha}  gated={gated}  (no Hub param count)")
        rows.append((family, mid, params, note, sha, gated))

    if not rows:
        print("nothing to add")
        return 0

    lines = [
        "  # ---- Phase-3 additions, pinned 2026-08-08 BEFORE any of their data was",
        "  # collected. Rationale in scripts/add_phase3_models.py: phi had no ladder at all,",
        "  # and Mistral-Large extends an EXISTING ladder where command-r-plus (103.8B) would",
        "  # have been a lone high point. Llama-3.1-405B deliberately excluded (~812 GiB).",
    ]
    for family, mid, params, note, sha, gated in rows:
        lines += [
            f"  - id: {mid}",
            f"    family: {family}",
            f"    params_b: {params}",
            f"    revision: {sha}",
            f"    gated: {str(gated).lower()}",
            f"    note: {json.dumps(note)}",   # quoted: notes contain colons
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
    print(f"\nroster now N = {len(cfg['primary'])}, families = {len(fams)}")
    for fam in ("qwen", "llama", "mistral", "phi", "gemma", "olmo"):
        l = sorted(m["params_b"] for m in cfg["primary"] if m["family"] == fam)
        if len(l) > 1:
            print(f"  {fam:<8} ladder {l}  span {l[-1] / l[0]:.0f}x")
    assert all(len(m.get("revision", "")) == 40 for m in cfg["primary"])
    print("all revisions pinned; existing entries untouched")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
