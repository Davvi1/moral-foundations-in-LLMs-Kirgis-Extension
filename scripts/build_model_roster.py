"""Build config/models.yaml with PINNED revision SHAs.

HuggingFace repo IDs are moving targets: `Qwen/Qwen2.5-7B-Instruct` today is not necessarily
the same weights as next month. Without a pinned revision the study is not reproducible even
by its own author. This queries the HF API for each model's current commit SHA and writes a
config that the harness passes straight to vLLM as `revision=`.

Re-running overwrites the file. Do NOT re-run after the confirmatory data is collected --
that would silently change what the manifests refer to.

    python scripts/build_model_roster.py
"""

from __future__ import annotations

import json
import sys
import urllib.request
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
OUT = REPO / "config" / "models.yaml"

# Roster chosen for FAMILY DIVERSITY first, size gradient second.
#
# The design simulation (scripts/design_simulation.py) treats models as exchangeable draws.
# Five sizes of one family are not independent -- shared pretraining data and post-training
# recipe -- so effective N is below nominal N. Ten families at N=20 is worth more than four
# families at N=25. Two families (Qwen, Llama) retain a size gradient because Kirgis's fourth
# claim is about capability, which needs within-family scale variation to address.
#
# All ≤14B. None are reasoning models: thinking-by-default changes free generation while being
# invisible to label scoring, which would manufacture the interaction under measurement.
ROSTER = [
    # family, id, params_b, why
    ("qwen",     "Qwen/Qwen2.5-0.5B-Instruct",          0.5,  "size gradient"),
    ("qwen",     "Qwen/Qwen2.5-1.5B-Instruct",          1.5,  "size gradient"),
    ("qwen",     "Qwen/Qwen2.5-3B-Instruct",            3.0,  "size gradient"),
    ("qwen",     "Qwen/Qwen2.5-7B-Instruct",            7.0,  "size gradient"),
    ("qwen",     "Qwen/Qwen2.5-14B-Instruct",          14.0,  "size gradient, largest"),
    ("llama",    "meta-llama/Llama-3.2-1B-Instruct",    1.0,  "size gradient (gated)"),
    ("llama",    "meta-llama/Llama-3.2-3B-Instruct",    3.0,  "size gradient (gated)"),
    ("llama",    "meta-llama/Llama-3.1-8B-Instruct",    8.0,  "size gradient (gated)"),
    ("gemma",    "google/gemma-2-2b-it",                2.6,  "distinct family (gated)"),
    ("gemma",    "google/gemma-2-9b-it",                9.2,  "distinct family (gated)"),
    ("mistral",  "mistralai/Mistral-7B-Instruct-v0.3",  7.2,  "distinct family"),
    ("mistral",  "mistralai/Ministral-8B-Instruct-2410", 8.0, "newer Mistral lineage"),
    ("phi",      "microsoft/Phi-3-mini-4k-instruct",    3.8,  "distinct family, synthetic-heavy"),
    ("phi",      "microsoft/Phi-4-mini-instruct",       3.8,  "newer Phi lineage"),
    ("olmo",     "allenai/OLMo-2-1124-7B-Instruct",     7.3,  "fully open data/recipe"),
    ("olmo",     "allenai/OLMo-2-1124-13B-Instruct",   13.7,  "fully open, larger"),
    ("smollm",   "HuggingFaceTB/SmolLM2-1.7B-Instruct", 1.7,  "distinct small-model recipe"),
    ("granite",  "ibm-granite/granite-3.1-8b-instruct", 8.2,  "distinct family, IBM"),
    ("internlm", "internlm/internlm2_5-7b-chat",        7.7,  "distinct family, Shanghai AI Lab"),
    ("yi",       "01-ai/Yi-1.5-9B-Chat",                8.8,  "distinct family, 01.AI"),
]

# Used if gate approvals fail. Swaps the 5 gated models for open ones, keeping N high.
OPEN_FALLBACK = [
    ("qwen",    "Qwen/Qwen2-7B-Instruct",            7.6, "earlier Qwen generation"),
    ("phi",     "microsoft/Phi-3.5-mini-instruct",   3.8, "open"),
    ("zephyr",  "HuggingFaceH4/zephyr-7b-beta",      7.2, "distinct post-training (DPO)"),
    ("falcon",  "tiiuae/Falcon3-7B-Instruct",        7.0, "distinct family, TII"),
]


def fetch(model_id: str) -> dict:
    url = f"https://huggingface.co/api/models/{model_id}"
    with urllib.request.urlopen(url, timeout=30) as r:
        return json.load(r)


def rows(spec):
    out = []
    for family, mid, params, why in spec:
        try:
            meta = fetch(mid)
        except Exception as exc:
            print(f"  FAILED {mid}: {exc}", file=sys.stderr)
            continue
        out.append({
            "family": family, "id": mid, "params_b": params, "why": why,
            "revision": meta.get("sha"),
            "gated": bool(meta.get("gated")),
        })
        print(f"  {mid:<42} {meta.get('sha')}")
    return out


def emit(fh, title, items):
    fh.write(f"{title}:\n")
    for m in items:
        fh.write(f"  - id: {m['id']}\n")
        fh.write(f"    family: {m['family']}\n")
        fh.write(f"    params_b: {m['params_b']}\n")
        fh.write(f"    revision: {m['revision']}\n")
        fh.write(f"    gated: {str(m['gated']).lower()}\n")
        fh.write(f"    note: {m['why']}\n")
    fh.write("\n")


def main() -> int:
    """Regenerate config/models.yaml from ROSTER. DESTRUCTIVE — requires --write.

    THIS GUARD EXISTS BECAUSE THE ABSENCE OF IT CAUSED REAL DAMAGE (2026-08-08).

    `tests/test_scripts_are_valid.py::test_shows_help_without_a_gpu` runs every script in
    `scripts/` with `--help` to prove it can print usage on a machine with no GPU. This
    script had no argparse, so `--help` was simply an ignored argv entry and the script RAN,
    regenerating the roster from the hard-coded N=20 ROSTER list. Alphabetical order meant
    `add_phase2_models.py` (since deleted, see docs/V1_TO_V2.md) added the Phase-2 models
    moments earlier and this overwrote them,
    so every `pytest` invocation silently reverted the roster from N=30 to N=20.

    That is worse than it sounds. `rows()` fetches the CURRENT sha from the Hub, so an
    accidental regeneration also re-pins every revision. If any upstream repo had moved, the
    pinned SHAs backing the committed Phase-1 manifests would have changed underneath us and
    the archived results would have stopped being reproducible — silently, with a green test
    suite. The file's own header says "do not regenerate after confirmatory data exists"; the
    test suite was doing exactly that on every run.

    So: an explicit flag, plus a refusal to shrink the roster without --force.
    """
    import argparse

    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0] if __doc__ else None)
    ap.add_argument("--write", action="store_true",
                    help="actually overwrite config/models.yaml (required; this is "
                         "destructive and re-pins every revision SHA from the Hub)")
    ap.add_argument("--force", action="store_true",
                    help="also allow the regenerated roster to be SMALLER than the existing "
                         "one, i.e. to drop models that are currently pinned")
    args = ap.parse_args()

    # Count the existing roster WITHOUT importing yaml. This script is stdlib-only by design
    # (it runs on the pod before the analysis environment exists), and an earlier version of
    # this guard called yaml.safe_load inside a try/except — which raised NameError, was
    # swallowed, and silently reported "0 primary models", disabling the shrink refusal
    # entirely. A guard that fails open is worse than no guard, because it looks like one.
    existing_n = 0
    if OUT.exists():
        in_primary = False
        for line in OUT.read_text(encoding="utf-8").splitlines():
            if line.startswith("primary:"):
                in_primary = True
            elif line and not line[0].isspace() and not line.startswith("#"):
                in_primary = False
            elif in_primary and line.startswith("  - id:"):
                existing_n += 1

    if not args.write:
        print(f"DRY RUN — nothing written. config/models.yaml currently has "
              f"{existing_n} primary models; this script would write {len(ROSTER)}.")
        print("Pass --write to regenerate. Note that doing so re-pins every revision SHA "
              "from the Hub and will invalidate existing run manifests if any SHA moved.")
        return 0

    if existing_n > len(ROSTER) and not args.force:
        print(f"REFUSING: config/models.yaml has {existing_n} primary models and this would "
              f"write {len(ROSTER)}, dropping {existing_n - len(ROSTER)}.\n"
              f"Models added by the phase-2 roster step are not in this script's "
              f"hard-coded ROSTER list and would be lost. Pass --force if that is intended.")
        return 1

    print("primary roster:")
    primary = rows(ROSTER)
    print("open fallback:")
    fallback = rows(OPEN_FALLBACK)

    fams = {}
    for m in primary:
        fams[m["family"]] = fams.get(m["family"], 0) + 1
    total_gb = sum(m["params_b"] for m in primary) * 2  # bf16

    OUT.parent.mkdir(parents=True, exist_ok=True)
    with OUT.open("w", encoding="utf-8") as fh:
        fh.write("# Model roster, with PINNED revision SHAs. Generated by\n")
        fh.write("# scripts/build_model_roster.py -- do not hand-edit, and do not regenerate\n")
        fh.write("# after confirmatory data exists (it would invalidate the run manifests).\n")
        fh.write("#\n")
        fh.write("# Chosen for FAMILY DIVERSITY first. The design simulation treats models as\n")
        fh.write("# exchangeable draws; sizes within one family are not independent, so effective\n")
        fh.write("# N is below nominal N when a family dominates. Qwen and Llama keep a size\n")
        fh.write("# gradient because Kirgis's capability claim needs within-family scale variation.\n")
        fh.write("#\n")
        fh.write("# All instruction-tuned, <=14B, and NON-REASONING: thinking-by-default alters\n")
        fh.write("# free generation while being invisible to label scoring, which would manufacture\n")
        fh.write("# the very interaction under measurement.\n#\n")
        fh.write(f"# N = {len(primary)}; families = {len(fams)} {json.dumps(fams)}\n")
        fh.write(f"# approx bf16 weight volume = {total_gb:.0f} GB\n")
        fh.write("# Weights need NOT be held simultaneously: download -> run four conditions\n")
        fh.write("# (minutes) -> delete -> next. The 200 GB volume is not the binding constraint.\n\n")
        emit(fh, "primary", primary)
        fh.write("# Swap in for the 5 gated models if approvals fail; keeps N at 19 with zero gate risk.\n")
        emit(fh, "open_fallback", fallback)

    print(f"\nwrote {OUT}")
    print(f"N = {len(primary)}, families = {len(fams)}: {fams}")
    print(f"approx bf16 weight volume = {total_gb:.0f} GB")
    print(f"gated: {sum(m['gated'] for m in primary)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
